"""
MJ Screen — parse le stream d'événements du subprocess OpenCode et poste
des embeds formatés dans #mj-screen en temps réel.

Un embed est posté par step (step_start) et mis à jour au fur et à mesure
des sous-événements, puis finalisé (couleur + titre) au step_finish.
"""

import datetime
import logging
import time

import discord

from . import config

logger = logging.getLogger(__name__)

# Couleurs des embeds selon le type d'événement
COLORS = {
    "in_progress":  0xf39c12,  # orange — step en cours
    "thinking":     0x95a5a6,  # gris   — step sans tool call
    "tool_call":    0x3498db,  # bleu   — step avec tools OK
    "tool_error":   0xe74c3c,  # rouge  — step avec au moins un outil en erreur
    "tool_result":  0x2ecc71,  # vert   (conservé pour post() générique)
    "npc_brief":    0x9b59b6,  # violet
    "npc_response": 0xf39c12,  # orange
    "decision":     0x1abc9c,  # turquoise
}

# Noms d'outils pour lesquels on affiche juste le chemin (lowercase)
_FILE_TOOLS = {"read", "write", "edit"}

# Délai minimum entre deux edits Discord (rate-limit safety)
_EDIT_DEBOUNCE = 1.0  # secondes


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
        # Accumulateurs par guild pour regrouper les events d'un step
        self._step_events:     dict[str, list[dict]]                    = {}
        self._step_count:      dict[str, int]                           = {}
        self._step_messages:   dict[str, discord.Message|None]          = {}
        self._step_last_edit:  dict[str, float]                         = {}
        self._step_started_at: dict[str, datetime.datetime]             = {}

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

    @staticmethod
    def _ts(dt: datetime.datetime | None = None) -> str:
        """Format a datetime as HH:MM:SS (local time)."""
        t = (dt or datetime.datetime.now()).astimezone()
        return t.strftime("%H:%M:%S")

    def _build_step_embed(self, events: list[dict], step_n: int, *, in_progress: bool, started_at: datetime.datetime | None = None) -> discord.Embed:
        """Construit l'embed d'un step (live ou final)."""
        has_error = any(e["is_error"] for e in events if e["etype"] == "tool")
        has_tools = any(e["etype"] == "tool" for e in events)

        if in_progress:
            color = COLORS["in_progress"]
            title = f"⏳ Step {step_n}"
        elif has_error:
            color = COLORS["tool_error"]
            title = f"Step {step_n}"
        elif has_tools:
            color = COLORS["tool_call"]
            title = f"Step {step_n}"
        else:
            color = COLORS["thinking"]
            title = f"Step {step_n}"

        lines: list[str] = [f"`{self._ts(started_at)}` ▶ début"]
        for e in events:
            ts = f"`{e['ts']}`"
            if e["etype"] == "thinking":
                lines.append(f"{ts} 🧠 *{_truncate(e['text'], 200)}*")
            elif e["etype"] == "tool":
                icon = "❌" if e["is_error"] else "🔧"
                lines.append(f"{ts} {icon} **{e['tool']}** → {e['desc']}")
                if e["is_error"] and e["error"]:
                    lines.append(f"  ↳ `{_truncate(str(e['error']), 150)}`")
            elif e["etype"] == "text":
                lines.append(f"{ts} 💬 {_truncate(e['text'], 400)}")

        if not in_progress:
            lines.append(f"`{self._ts()}` ✅ fin")

        desc = "\n".join(lines)
        return discord.Embed(
            title=title,
            description=_truncate(desc, 4096),
            color=color,
        )

    async def _refresh_step(self, guild_id: str, *, final: bool) -> None:
        """Edit le message live du step en cours (debounced sauf si final)."""
        msg = self._step_messages.get(guild_id)
        if not msg:
            return

        now = time.monotonic()
        if not final:
            last = self._step_last_edit.get(guild_id, 0.0)
            if now - last < _EDIT_DEBOUNCE:
                return  # trop tôt, on skip cet update

        evs = self._step_events.get(guild_id, [])
        step_n = self._step_count.get(guild_id, 1)
        started_at = self._step_started_at.get(guild_id)
        embed = self._build_step_embed(evs, step_n, in_progress=not final, started_at=started_at)
        try:
            await msg.edit(embed=embed)
            self._step_last_edit[guild_id] = time.monotonic()
        except discord.HTTPException as exc:
            logger.warning("MJScreen step edit error: %s", exc)

    async def handle_stream_event(self, event: dict, guild_id: str) -> None:
        """
        Traite un événement du stream JSON d'OpenCode.
        Poste un embed au step_start et l'édite à chaque sous-événement,
        puis finalise la couleur au step_finish.

        Format OpenCode (--format json) :
          {"type": "step_start",  "part": {"type": "step-start"}}
          {"type": "text",        "part": {"type": "text", "text": "..."}}
          {"type": "thinking",    "part": {"type": "thinking", "thinking": "..."}}
          {"type": "tool_use",    "part": {"type": "tool-use", "tool": "Read", ...}}
          {"type": "step_finish", "part": {"type": "step-finish", "reason": "stop", ...}}
        """
        event_type = event.get("type")
        part = event.get("part", {})

        if event_type == "step_start":
            self._step_events[guild_id] = []
            self._step_count[guild_id] = self._step_count.get(guild_id, 0) + 1
            self._step_last_edit.pop(guild_id, None)
            self._step_started_at[guild_id] = datetime.datetime.now(datetime.timezone.utc)

            channel = await self._get_channel(guild_id)
            if not channel:
                self._step_messages[guild_id] = None
                return

            step_n = self._step_count[guild_id]
            embed = self._build_step_embed([], step_n, in_progress=True, started_at=self._step_started_at[guild_id])
            try:
                msg = await channel.send(embed=embed)
                self._step_messages[guild_id] = msg
            except discord.HTTPException as exc:
                logger.warning("MJScreen step_start post error: %s", exc)
                self._step_messages[guild_id] = None

        elif event_type in ("thinking", "reasoning"):
            text = part.get("text", "") or part.get("thinking", "")
            if text:
                self._step_events.setdefault(guild_id, []).append(
                    {"etype": "thinking", "text": text, "ts": self._ts()}
                )
                await self._refresh_step(guild_id, final=False)

        elif event_type == "text":
            text = part.get("text", "")
            if text:
                evs = self._step_events.setdefault(guild_id, [])
                # Fusionner avec le dernier bloc texte pour éviter la fragmentation
                if evs and evs[-1]["etype"] == "text":
                    evs[-1]["text"] += text  # keep original timestamp
                else:
                    evs.append({"etype": "text", "text": text, "ts": self._ts()})
                await self._refresh_step(guild_id, final=False)

        elif event_type == "tool_use":
            tool_name = part.get("tool", "")
            state = part.get("state", {})
            tool_input = state.get("input", part.get("input", {}))
            tool_error = state.get("error", "")
            is_error = bool(tool_error)

            if tool_name.lower() in _FILE_TOOLS:
                path = (tool_input.get("filePath") or tool_input.get("file_path")
                        or tool_input.get("path") or str(tool_input))
                desc = f"`{path}`"
            else:
                desc = _truncate(str(tool_input), 300)

            self._step_events.setdefault(guild_id, []).append({
                "etype": "tool",
                "tool": tool_name,
                "desc": desc,
                "is_error": is_error,
                "error": tool_error,
                "ts": self._ts(),
            })
            # Tool calls sont des événements discrets — toujours rafraîchir
            await self._refresh_step(guild_id, final=False)

        elif event_type == "step_finish":
            await self._refresh_step(guild_id, final=True)
            self._step_messages.pop(guild_id, None)
