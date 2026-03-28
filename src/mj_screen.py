"""
MJ Screen — parse le stream d'événements du subprocess OpenCode et poste
des embeds formatés dans #mj-screen en temps réel.
"""

import asyncio
import logging

import discord

from . import config

logger = logging.getLogger(__name__)

# Couleurs des embeds selon le type d'événement
COLORS = {
    "thinking":     0x95a5a6,  # gris
    "tool_call":    0x3498db,  # bleu
    "tool_result":  0x2ecc71,  # vert
    "tool_error":   0xe74c3c,  # rouge
    "npc_brief":    0x9b59b6,  # violet
    "npc_response": 0xf39c12,  # orange
    "decision":     0x1abc9c,  # turquoise
}

# Noms d'outils pour lesquels on affiche juste le nom du fichier (lowercase — format réel OpenCode)
_FILE_TOOLS = {"read", "write", "edit"}
_FILE_ICONS = {"read": "📖", "write": "✏️", "edit": "✏️"}


def _truncate(text: str, limit: int = 1024) -> str:
    if len(text) <= limit:
        return text
    return text[:limit - 3] + "…"


class MJScreen:
    """
    Poste les événements du raisonnement du MJ dans #mj-screen.
    Utilisé à la fois par le bridge OpenCode (stream temps réel)
    et par les routes API (briefs/réponses PNJ).
    """

    def __init__(self, client: discord.Client) -> None:
        self._client = client
        self._text_buffer: dict[str, str] = {}  # guild_id → accumulated text

    async def _get_channel(self, guild_id: str) -> discord.TextChannel | None:
        # Pas de cache — channels.yml peut être modifié à chaud par le MJ
        mj_screen_name = config.load_channels(guild_id)["mj_screen"].lower()
        for guild in self._client.guilds:
            if str(guild.id) != guild_id:
                continue
            for ch in guild.text_channels:
                if ch.name.lower() == mj_screen_name:
                    return ch
        return None

    async def post(self, guild_id: str, embed_type: str, content: str, title: str = "") -> None:
        """Poste un embed typé dans #mj-screen."""
        channel = await self._get_channel(guild_id)
        if not channel:
            return
        color = COLORS.get(embed_type, 0x95a5a6)
        embed = discord.Embed(
            title=title or None,
            description=_truncate(content, 4096),
            color=color,
        )
        try:
            await channel.send(embed=embed)
        except discord.HTTPException as exc:
            logger.warning("MJScreen.post error: %s", exc)

    async def post_npc_brief(self, guild_id: str, character_name: str, brief: str) -> None:
        await self.post(
            guild_id,
            "npc_brief",
            _truncate(brief, 4000),
            title=f"Brief PNJ — {character_name}",
        )

    async def post_npc_response(self, guild_id: str, character_name: str, response: str) -> None:
        await self.post(
            guild_id,
            "npc_response",
            _truncate(response, 4000),
            title=f"Réponse PNJ — {character_name}",
        )

    async def post_decision(self, guild_id: str, content: str) -> None:
        await self.post(guild_id, "decision", content)

    async def _flush_text(self, guild_id: str, channel: discord.TextChannel) -> None:
        """Post accumulated thinking text as an embed, then clear the buffer."""
        text = self._text_buffer.pop(guild_id, "").strip()
        if not text:
            return
        embed = discord.Embed(
            description=_truncate(text, 4096),
            color=COLORS["thinking"],
        )
        try:
            await channel.send(embed=embed)
        except discord.HTTPException as exc:
            logger.warning("MJScreen thinking post error: %s", exc)

    async def handle_stream_event(self, event: dict, guild_id: str) -> None:
        """
        Traite un événement du stream JSON d'OpenCode et poste l'embed correspondant.

        Format OpenCode (--format json) :
          {"type": "step_start", "part": {"type": "step-start"}}
          {"type": "text", "part": {"type": "text", "text": "..."}}
          {"type": "tool_use", "part": {"type": "tool-use", "tool": "Read", "input": {...}}}
          {"type": "tool_result", "part": {"type": "tool-result", "tool": "Read", "output": "...", "error": ""}}
          {"type": "step_finish", "part": {"type": "step-finish", "reason": "stop", "tokens": {...}}}
        """
        channel = await self._get_channel(guild_id)
        if not channel:
            return

        event_type = event.get("type")
        part = event.get("part", {})

        if event_type == "step_start":
            self._text_buffer[guild_id] = ""

        elif event_type in ("thinking", "reasoning"):
            text = part.get("text", "") or part.get("thinking", "")
            if text:
                embed = discord.Embed(
                    title="🧠 Thinking",
                    description=_truncate(text, 4096),
                    color=COLORS["thinking"],
                )
                try:
                    await channel.send(embed=embed)
                except discord.HTTPException as exc:
                    logger.warning("MJScreen thinking block post error: %s", exc)

        elif event_type == "text":
            text = part.get("text", "")
            if text:
                self._text_buffer.setdefault(guild_id, "")
                self._text_buffer[guild_id] += text

        elif event_type == "tool_use":
            # Flush accumulated thinking text before the tool call
            await self._flush_text(guild_id, channel)

            tool_name = part.get("tool", "")
            # Input and output are nested under part["state"] in OpenCode's actual format
            state = part.get("state", {})
            tool_input = state.get("input", part.get("input", {}))
            tool_output = state.get("output", "")
            tool_error = state.get("error", "")
            is_error = bool(tool_error)

            if tool_name in _FILE_TOOLS:
                path = (tool_input.get("filePath") or tool_input.get("file_path")
                        or tool_input.get("path") or str(tool_input))
                icon = _FILE_ICONS.get(tool_name, "🔧")
                desc = f"{icon} `{path}`"
            else:
                desc = _truncate(str(tool_input), 800)

            embed = discord.Embed(
                title=f"🔧 {tool_name}",
                description=desc,
                color=COLORS["tool_error"] if is_error else COLORS["tool_call"],
            )
            try:
                await channel.send(embed=embed)
            except discord.HTTPException as exc:
                logger.warning("MJScreen tool_call post error: %s", exc)

            # Result is bundled in the same event — post it immediately after
            result_content = tool_error if is_error else tool_output
            if result_content and len(str(result_content)) >= 20:
                result_embed = discord.Embed(
                    description=_truncate(str(result_content), 1024),
                    color=COLORS["tool_error"] if is_error else COLORS["tool_result"],
                )
                try:
                    await channel.send(embed=result_embed)
                except discord.HTTPException as exc:
                    logger.warning("MJScreen tool_result post error: %s", exc)

        elif event_type == "step_finish":
            # Flush any remaining text (final response)
            await self._flush_text(guild_id, channel)
