"""
Internal API — NPC invocation and MJ-screen routes.

POST /npc/invoke    — Lance un sub-agent PNJ via Ollama
GET  /npc/list      — Liste les PNJ disponibles (fichiers characters/)
POST /mj-screen/post — Poste un embed custom dans #mj-screen
"""

import logging
from pathlib import Path

import discord
from aiohttp import web

from . import config
from .api_context import ApiContext, find_channel, json_response

logger = logging.getLogger(__name__)

CHARACTERS_DIR = config.MEMORY_DIR / "characters"


def register(app: web.Application, ctx: ApiContext) -> None:
    async def post_npc_invoke(request):
        """
        Lance un sub-agent PNJ.

        Body :
        {
          "character_name": "Kael",
          "brief": "Tu es Kael. [brief complet]",
          "max_tokens": 500,
          "guild_id": "...",
          "channel_name": "rp",
          "post_as_webhook": true,
          "character_avatar": "https://..."
        }
        """
        try:
            body = await request.json()
        except Exception:
            return json_response({"error": "Invalid JSON body"}, 400)

        character_name = body.get("character_name", "")
        brief = body.get("brief", "")
        max_tokens = int(body.get("max_tokens", 500))
        guild_id = body.get("guild_id", "")
        channel_name = body.get("channel_name", config.RP_CHANNEL)
        post_as_webhook = body.get("post_as_webhook", True)
        character_avatar = body.get("character_avatar", "")

        if not character_name or not brief:
            return json_response({"error": "character_name and brief are required"}, 400)
        if not guild_id:
            return json_response({"error": "guild_id is required"}, 400)

        # Poster le brief dans #mj-screen
        await ctx.mj_screen.post_npc_brief(guild_id, character_name, brief)

        # Invoquer le LLM
        response_text = await ctx.npc_invoker.invoke(brief, max_tokens=max_tokens)

        # Poster la réponse dans #mj-screen
        await ctx.mj_screen.post_npc_response(guild_id, character_name, response_text)

        message_ids: list[int] = []

        if post_as_webhook and response_text:
            channel = find_channel(ctx, guild_id, channel_name)
            if not channel:
                return json_response({"error": f"Channel #{channel_name} not found"}, 404)

            if not character_avatar and ctx.client.user and ctx.client.user.display_avatar:
                character_avatar = str(ctx.client.user.display_avatar.url)

            wh = await ctx.webhooks.get_or_create(channel)
            message_ids = await ctx.webhooks.post_as_character(
                wh, character_name, response_text, character_avatar
            )

        tokens_used = len(response_text.split()) * 2  # approximation

        return json_response({
            "ok": True,
            "text": response_text,
            "message_ids": message_ids,
            "tokens_used": tokens_used,
        })

    async def get_npc_list(request):
        """Liste tous les PNJ disponibles (fichiers dans memory/characters/)."""
        npcs = []
        if CHARACTERS_DIR.exists():
            for f in sorted(CHARACTERS_DIR.glob("*.md")):
                # Lire juste la première ligne du fichier pour le nom
                try:
                    first_line = f.read_text(encoding="utf-8").splitlines()[0]
                    name = first_line.lstrip("# ").strip() if first_line.startswith("#") else f.stem
                except Exception:
                    name = f.stem
                npcs.append({
                    "slug": f.stem,
                    "name": name,
                    "file": str(f),
                })
        return json_response({"npcs": npcs, "count": len(npcs)})

    async def post_mj_screen(request):
        """
        Poste un embed custom dans #mj-screen (décisions, notes du MJ).

        Body :
        {
          "type": "decision",
          "content": "→ Marta sert la bière. Kael observe en silence.",
          "guild_id": "...",
          "title": ""   (optionnel)
        }
        """
        try:
            body = await request.json()
        except Exception:
            return json_response({"error": "Invalid JSON body"}, 400)

        embed_type = body.get("type", "decision")
        content = body.get("content", "")
        guild_id = body.get("guild_id", "")
        title = body.get("title", "")

        if not content or not guild_id:
            return json_response({"error": "content and guild_id are required"}, 400)

        await ctx.mj_screen.post(guild_id, embed_type, content, title=title)
        return json_response({"ok": True})

    app.router.add_post("/npc/invoke", post_npc_invoke)
    app.router.add_get("/npc/list", get_npc_list)
    app.router.add_post("/mj-screen/post", post_mj_screen)
