"""
Webhook Manager — gestion des webhooks Discord par channel RP.
Tous les messages RP sont postés via webhook pour permettre l'édition/suppression.
"""

import asyncio
import json
import logging
from pathlib import Path

import discord

from . import config
from .message_splitter import split_message

logger = logging.getLogger(__name__)

WEBHOOKS_FILE = config.MEMORY_DIR / "meta" / "webhooks.json"
WEBHOOK_NAME = "Augure"


class WebhookManager:
    def __init__(self, client: discord.Client) -> None:
        self._client = client
        # channel_id (str) -> webhook_url (str)
        self._webhooks: dict[str, str] = {}

    async def load(self) -> None:
        """Charge les webhooks persistés depuis le fichier JSON."""
        if WEBHOOKS_FILE.exists():
            with open(WEBHOOKS_FILE, encoding="utf-8") as f:
                self._webhooks = json.load(f)
        logger.info("Webhooks chargés : %d channels", len(self._webhooks))

    def _save(self) -> None:
        WEBHOOKS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(WEBHOOKS_FILE, "w", encoding="utf-8") as f:
            json.dump(self._webhooks, f, indent=2)

    async def get_or_create(self, channel: discord.TextChannel) -> discord.Webhook:
        """Retourne le webhook existant du channel, ou en crée un nouveau."""
        channel_id = str(channel.id)

        if channel_id in self._webhooks:
            try:
                wh = discord.Webhook.from_url(
                    self._webhooks[channel_id],
                    client=self._client,
                )
                return wh
            except Exception:
                logger.warning("Webhook invalide pour %s — recréation", channel.name)
                del self._webhooks[channel_id]

        wh = await channel.create_webhook(name=WEBHOOK_NAME)
        self._webhooks[channel_id] = wh.url
        self._save()
        logger.info("Webhook créé dans #%s", channel.name)
        return wh

    async def post_as_character(
        self,
        webhook: discord.Webhook,
        name: str,
        text: str,
        avatar_url: str = "",
    ) -> list[int]:
        """
        Poste du texte via webhook avec le nom et l'avatar fournis.
        Retourne la liste des IDs de messages créés.
        """
        parts = split_message(text)
        message_ids: list[int] = []

        for part in parts:
            try:
                msg = await webhook.send(
                    content=part,
                    username=name or "Personnage",
                    avatar_url=avatar_url or discord.utils.MISSING,
                    wait=True,
                )
                message_ids.append(msg.id)
                if len(parts) > 1:
                    await asyncio.sleep(0.5)
            except discord.NotFound:
                channel_id = str(webhook.channel_id) if webhook.channel_id else None
                if channel_id and channel_id in self._webhooks:
                    del self._webhooks[channel_id]
                    self._save()
                logger.warning("Webhook introuvable (supprimé ?) — cache invalidé pour %s", channel_id)
                break
            except discord.HTTPException as exc:
                logger.error("Webhook post error: %s", exc)

        return message_ids

    async def edit_messages(
        self,
        webhook: discord.Webhook,
        message_ids: list[int],
        new_text: str,
    ) -> bool:
        """
        Édite les messages webhook existants avec le nouveau texte.
        Retourne True si succès.
        """
        new_parts = split_message(new_text)

        if len(new_parts) == len(message_ids):
            for msg_id, part in zip(message_ids, new_parts):
                try:
                    await webhook.edit_message(msg_id, content=part)
                except discord.HTTPException as exc:
                    logger.error("Webhook edit error (msg %d): %s", msg_id, exc)
                    return False
            return True
        else:
            logger.warning(
                "Nombre de parties différent (%d → %d), édition impossible en place",
                len(message_ids),
                len(new_parts),
            )
            return False

    async def delete_messages(
        self,
        webhook: discord.Webhook,
        message_ids: list[int],
    ) -> None:
        for msg_id in message_ids:
            try:
                await webhook.delete_message(msg_id)
                await asyncio.sleep(0.3)
            except discord.HTTPException as exc:
                logger.warning("Could not delete message %d: %s", msg_id, exc)
