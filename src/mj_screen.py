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

# Noms d'outils dont on veut afficher le résultat tronqué
_VERBOSE_TOOLS = {"Read", "Glob", "WebFetch", "Bash"}
# Noms d'outils pour lesquels on affiche juste le nom du fichier
_FILE_TOOLS = {"Read", "Write", "Edit"}


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

    async def handle_stream_event(self, event: dict, guild_id: str) -> None:
        """
        Traite un événement du stream JSON d'OpenCode/Claude et poste l'embed correspondant.

        Format stream-json attendu (identique à Claude CLI) :
          {"type": "assistant", "message": {"content": [{"type": "thinking", "thinking": "..."}]}}
          {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "...", "input": {...}}]}}
          {"type": "user", "message": {"content": [{"type": "tool_result", "content": "...", "is_error": false}]}}
          {"type": "result", "result": "..."}
        """
        channel = await self._get_channel(guild_id)
        if not channel:
            return

        event_type = event.get("type")

        if event_type == "assistant":
            message = event.get("message", {})
            content_blocks = message.get("content", [])
            for block in content_blocks:
                block_type = block.get("type")

                if block_type == "thinking":
                    thinking = block.get("thinking", "")
                    if len(thinking) < 50:
                        continue  # Trop court pour être utile
                    embed = discord.Embed(
                        description=_truncate(thinking, 4096),
                        color=COLORS["thinking"],
                    )
                    try:
                        await channel.send(embed=embed)
                    except discord.HTTPException as exc:
                        logger.warning("MJScreen thinking post error: %s", exc)

                elif block_type == "tool_use":
                    tool_name = block.get("name", "")
                    tool_input = block.get("input", {})

                    if tool_name in _FILE_TOOLS:
                        # Juste le nom du fichier/chemin
                        path = tool_input.get("file_path") or tool_input.get("path") or str(tool_input)
                        icons = {"Read": "📖", "Write": "✏️", "Edit": "✏️"}
                        desc = f"{icons.get(tool_name, '🔧')} `{path}`"
                    else:
                        desc = _truncate(str(tool_input), 800)

                    embed = discord.Embed(
                        title=f"🔧 {tool_name}",
                        description=desc,
                        color=COLORS["tool_call"],
                    )
                    try:
                        await channel.send(embed=embed)
                    except discord.HTTPException as exc:
                        logger.warning("MJScreen tool_call post error: %s", exc)

        elif event_type == "user":
            message = event.get("message", {})
            content_blocks = message.get("content", [])
            for block in content_blocks:
                if block.get("type") == "tool_result":
                    is_error = block.get("is_error", False)
                    result_content = block.get("content", "")
                    if isinstance(result_content, list):
                        result_content = " ".join(
                            b.get("text", "") for b in result_content if isinstance(b, dict)
                        )

                    if not result_content or len(str(result_content)) < 20:
                        continue  # Résultats vides ou triviaux

                    embed = discord.Embed(
                        description=_truncate(str(result_content), 1024),
                        color=COLORS["tool_error"] if is_error else COLORS["tool_result"],
                    )
                    try:
                        await channel.send(embed=embed)
                    except discord.HTTPException as exc:
                        logger.warning("MJScreen tool_result post error: %s", exc)
