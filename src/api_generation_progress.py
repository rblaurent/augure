"""
Generation progress tracker — posts a live embed into the conversation channel
as image/music generation proceeds.
"""

import logging
import time

import discord

logger = logging.getLogger(__name__)

_STAGE_LABELS = {
    "generating":      "🎨 Génération en cours…",
    "submitted":       "⏳ En attente de Suno…",
    "writing_lyrics":  "✍️ Écriture des paroles…",
    "composing_audio": "🎵 Composition de l'audio…",
}

_MUSIC_STAGES = ["submitted", "writing_lyrics", "composing_audio"]


class GenerationProgress:
    """
    Poste un embed de progression dans le channel courant (guild ou DM) via
    un message bot ordinaire (channel.send / message.edit) — aucune permission
    spéciale requise, fonctionne partout.
    Tous les échecs sont silencieux — la génération continue quoi qu'il arrive.
    """

    def __init__(self, channel, kind: str = "image", thumbnail_url: str = "") -> None:
        self._channel = channel
        self._kind = kind           # "image" | "music"
        self._thumbnail_url = thumbnail_url
        self._message: discord.Message | None = None
        self._start = time.monotonic()
        self._title = ""
        self._params: dict = {}

    def _elapsed(self) -> int:
        return int(time.monotonic() - self._start)

    def _build_update_embed(self, stage: str, detail: str = "") -> discord.Embed:
        elapsed = self._elapsed()
        if self._kind == "music":
            stage_dots = {"submitted": 3, "writing_lyrics": 6, "composing_audio": 9}
            filled = stage_dots.get(stage, 1)
        else:
            try:
                fraction = float(detail) if detail else None
            except ValueError:
                fraction = None
            if fraction is None:
                fraction = min(0.9, elapsed / 30.0)
            filled = max(1, round(min(fraction, 0.9) * 10))
        dots = "⬤" * filled + "○" * (10 - filled)
        desc = dots
        embed = discord.Embed(title=self._title, description=desc, color=0x5865F2)
        for k, v in self._params.items():
            if v:
                embed.add_field(name=k, value=str(v)[:1024], inline=True)
        if self._thumbnail_url:
            embed.set_thumbnail(url=self._thumbnail_url)
        return embed

    async def start(self, title: str, params: dict) -> None:
        self._title = title
        self._params = params
        embed = self._build_update_embed("preparing")
        embed.description = "⏳ Préparation…"
        try:
            self._message = await self._channel.send(embed=embed)
        except discord.HTTPException as exc:
            logger.warning("GenerationProgress.start failed: %s", exc)

    async def update(self, stage: str, detail: str = "") -> None:
        if not self._message:
            return
        embed = self._build_update_embed(stage, detail)
        try:
            await self._message.edit(embed=embed)
        except discord.HTTPException as exc:
            logger.warning("GenerationProgress.update failed: %s", exc)

    async def finish(self, embed: discord.Embed) -> None:
        if not self._message:
            return
        try:
            await self._message.edit(embed=embed)
        except discord.HTTPException as exc:
            logger.warning("GenerationProgress.finish failed: %s", exc)

    async def finish_with_file(self, embed: discord.Embed, file: discord.File) -> discord.Message | None:
        """Send a new message with file + embed attached, then delete the loading card."""
        try:
            new_msg = await self._channel.send(file=file, embed=embed)
            if self._message:
                try:
                    await self._message.delete()
                except discord.HTTPException:
                    pass
            self._message = new_msg
            return new_msg
        except discord.HTTPException as exc:
            logger.warning("GenerationProgress.finish_with_file failed: %s", exc)
            return None

    async def fail(self, reason: str) -> None:
        if not self._message:
            return
        embed = discord.Embed(
            title=self._title,
            description=f"❌ Échec : {reason}",
            color=0xED4245,
        )
        try:
            await self._message.edit(embed=embed)
        except discord.HTTPException as exc:
            logger.warning("GenerationProgress.fail failed: %s", exc)
