"""
Shared context and helpers for internal API route modules.
"""

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

import discord
from aiohttp import web

if TYPE_CHECKING:
    from .mj_screen import MJScreen
    from .npc_invoker import NPCInvoker


@dataclass
class ApiContext:
    client: discord.Client
    webhooks: object
    memory: object
    comfy: object
    suno: object | None
    mj_screen: "MJScreen"
    npc_invoker: "NPCInvoker"


def find_channel_by_id(ctx: ApiContext, channel_id: str):
    """Résout un channel (guild ou DM) par son ID depuis le cache Discord."""
    try:
        return ctx.client.get_channel(int(channel_id))
    except (ValueError, TypeError):
        return None


def find_channel(ctx: ApiContext, guild_id: str, channel_name: str):
    channel_name = channel_name.lower().lstrip("#")
    for guild in ctx.client.guilds:
        if str(guild.id) != guild_id:
            continue
        for ch in guild.text_channels:
            if ch.name.lower() == channel_name:
                return ch
    return None


def json_response(data, status: int = 200) -> web.Response:
    return web.Response(
        text=json.dumps(data, ensure_ascii=False, indent=2),
        content_type="application/json",
        status=status,
    )
