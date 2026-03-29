"""
Watchdog service — scans guild channels for new messages and reactions,
then passes them to the MJ for awareness and optional preparation.
"""

import asyncio
import logging

import discord

from . import config

logger = logging.getLogger(__name__)


class WatchdogService:
    def __init__(self, client: discord.Client, memory, runner) -> None:
        self._client = client
        self._memory = memory
        self._runner = runner
        self._running: set[str] = set()

    async def run_loop(self) -> None:
        await asyncio.sleep(120)  # 2-minute startup grace period
        while True:
            tick_start = asyncio.get_event_loop().time()
            try:
                for guild in self._client.guilds:
                    await self.run_for_guild(guild)
            except Exception as exc:
                logger.error("Watchdog loop error (will retry next cycle): %s", exc)
            elapsed = asyncio.get_event_loop().time() - tick_start
            await asyncio.sleep(max(0.0, config.WATCHDOG_INTERVAL * 60 - elapsed))

    async def run_for_guild(self, guild: discord.Guild) -> None:
        guild_id = str(guild.id)
        if guild_id in self._running:
            return
        self._running.add(guild_id)
        try:
            handled_ids = self._memory.pop_handled_message_ids()
            channels_data: list[dict] = []
            for channel in guild.text_channels:
                channel_id = str(channel.id)
                last_id = self._memory.get_watchdog_last_message_id(channel_id)

                # First run — record current position, don't process history
                if last_id is None:
                    async for msg in channel.history(limit=1):
                        self._memory.update_watchdog_last_message_id(channel_id, msg.id)
                    continue

                raw_messages: list = []
                last_seen_id = None
                async for msg in channel.history(limit=20, after=discord.Object(id=last_id)):
                    last_seen_id = msg.id
                    raw_messages.append(msg)

                # Any player message followed by an Augure reply is already handled
                bot_reply_positions = {
                    i for i, msg in enumerate(raw_messages)
                    if msg.author == self._client.user
                }
                replied_to: set[int] = set()
                for i, msg in enumerate(raw_messages):
                    if msg.author != self._client.user:
                        if any(j > i for j in bot_reply_positions):
                            replied_to.add(msg.id)

                new_messages: list[dict] = []
                for msg in raw_messages:
                    if msg.author == self._client.user:
                        continue
                    if msg.id in handled_ids or msg.id in replied_to:
                        continue
                    new_messages.append({
                        "id": str(msg.id),
                        "author": msg.author.display_name,
                        "content": msg.content,
                        "timestamp": msg.created_at.isoformat(),
                    })

                # Always advance cursor past any new messages (including bot replies)
                if last_seen_id:
                    self._memory.update_watchdog_last_message_id(channel_id, last_seen_id)

                if new_messages:
                    new_messages.reverse()
                    history = []
                    async for msg in channel.history(limit=10, before=discord.Object(id=int(last_id))):
                        history.append({
                            "author": msg.author.display_name,
                            "content": msg.content,
                        })
                    history.reverse()
                    channels_data.append({
                        "channel_name": channel.name,
                        "channel_id": channel_id,
                        "last_seen_id": last_seen_id,
                        "history": history,
                        "messages": new_messages,
                    })

            # Merge pending reactions
            channels_by_id = {ch["channel_id"]: ch for ch in channels_data}
            for channel in guild.text_channels:
                pending = self._memory.pop_pending_reactions(str(channel.id))
                if not pending:
                    continue
                if str(channel.id) in channels_by_id:
                    channels_by_id[str(channel.id)]["reactions"] = pending
                else:
                    channels_data.append({
                        "channel_name": channel.name,
                        "channel_id": str(channel.id),
                        "last_seen_id": None,
                        "messages": [],
                        "reactions": pending,
                    })

            if not channels_data:
                return

            total = sum(len(c["messages"]) for c in channels_data)
            logger.info("Watchdog %s : %d channels, %d messages", guild.name, len(channels_data), total)

            await self._runner.run(guild_id, guild.name, channels_data)

            for ch in channels_data:
                if ch.get("last_seen_id"):
                    self._memory.update_watchdog_last_message_id(ch["channel_id"], ch["last_seen_id"])
        finally:
            self._running.discard(guild_id)
