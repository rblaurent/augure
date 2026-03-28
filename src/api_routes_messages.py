"""
Internal API — message & history routes.
"""

import logging

import discord
from aiohttp import web

from .api_context import ApiContext, find_channel, json_response

logger = logging.getLogger(__name__)


def _serialize_message(msg) -> dict:
    entry = {
        "author": msg.author.display_name,
        "content": msg.content,
        "timestamp": msg.created_at.isoformat(),
        "id": str(msg.id),
    }
    if msg.attachments:
        entry["attachments"] = [
            {"url": a.url, "content_type": a.content_type}
            for a in msg.attachments
            if a.content_type and a.content_type.startswith("image/")
        ]
    if msg.embeds:
        serialized = []
        for e in msg.embeds:
            obj = {}
            if e.title:
                obj["title"] = e.title
            if e.description:
                obj["description"] = e.description
            if e.url:
                obj["url"] = e.url
            if e.fields:
                obj["fields"] = [{"name": f.name, "value": f.value} for f in e.fields]
            if e.author and e.author.name:
                obj["author"] = e.author.name
            if e.footer and e.footer.text:
                obj["footer"] = e.footer.text
            if e.image and e.image.url:
                obj["image"] = e.image.url
            if e.thumbnail and e.thumbnail.url:
                obj["thumbnail"] = e.thumbnail.url
            if obj:
                serialized.append(obj)
        if serialized:
            entry["embeds"] = serialized
    return entry


def register(app: web.Application, ctx: ApiContext) -> None:
    async def get_guilds(request):
        """Liste tous les serveurs et leurs channels."""
        data = [
            {
                "id": str(g.id),
                "name": g.name,
                "channels": [
                    {
                        "name": c.name,
                        "id": str(c.id),
                        "category": c.category.name if c.category else None,
                        "category_id": str(c.category.id) if c.category else None,
                    }
                    for c in g.text_channels
                ],
            }
            for g in ctx.client.guilds
        ]
        return json_response(data)

    async def get_channel_history(request):
        """Retourne les derniers messages d'un channel."""
        guild_id = request.match_info["guild_id"]
        channel_name = request.match_info["channel_name"]
        raw_limit = int(request.rel_url.query.get("limit", "30"))
        limit = None if raw_limit == 0 else raw_limit

        channel = find_channel(ctx, guild_id, channel_name)
        if not channel:
            return json_response({"error": f"Channel #{channel_name} not found in guild {guild_id}"}, 404)

        messages = []
        async for msg in channel.history(limit=limit):
            messages.append(_serialize_message(msg))

        messages.reverse()
        return json_response({"channel": channel_name, "guild_id": guild_id, "messages": messages})

    async def get_dm_history(request):
        """Retourne les derniers messages d'un DM avec un utilisateur."""
        user_id = request.match_info["user_id"]
        raw_limit = int(request.rel_url.query.get("limit", "30"))
        limit = None if raw_limit == 0 else raw_limit

        try:
            user = await ctx.client.fetch_user(int(user_id))
        except Exception:
            return json_response({"error": f"User {user_id} not found"}, 404)

        dm = await user.create_dm()
        messages = []
        async for msg in dm.history(limit=limit):
            messages.append(_serialize_message(msg))

        messages.reverse()
        return json_response({"user_id": user_id, "messages": messages})

    async def post_send(request):
        """Envoie un message texte dans un channel ou un DM."""
        try:
            body = await request.json()
        except Exception:
            return json_response({"error": "Invalid JSON body"}, 400)

        text = body.get("text", "")
        guild_id = body.get("guild_id", "")
        channel_name = body.get("channel_name", "")
        user_id = body.get("user_id", "")

        if not text:
            return json_response({"error": "text is required"}, 400)

        if guild_id and channel_name:
            channel = find_channel(ctx, guild_id, channel_name)
            if not channel:
                return json_response({"error": "Channel not found"}, 404)
            sent = await channel.send(text)
        elif user_id:
            try:
                user = await ctx.client.fetch_user(int(user_id))
            except Exception:
                return json_response({"error": f"User {user_id} not found"}, 404)
            dm = await user.create_dm()
            sent = await dm.send(text)
        else:
            return json_response({"error": "Provide guild_id+channel_name or user_id"}, 400)

        return json_response({"ok": True, "message_id": str(sent.id)})

    async def post_delete(request):
        """Supprime un message bot dans un channel ou un DM."""
        try:
            body = await request.json()
        except Exception:
            return json_response({"error": "Invalid JSON body"}, 400)

        message_id = body.get("message_id", "")
        guild_id = body.get("guild_id", "")
        channel_name = body.get("channel_name", "")
        user_id = body.get("user_id", "")

        if not message_id:
            return json_response({"error": "message_id is required"}, 400)

        if guild_id and channel_name:
            channel = find_channel(ctx, guild_id, channel_name)
            if not channel:
                return json_response({"error": "Channel not found"}, 404)
        elif user_id:
            try:
                user = await ctx.client.fetch_user(int(user_id))
            except Exception:
                return json_response({"error": f"User {user_id} not found"}, 404)
            channel = await user.create_dm()
        else:
            return json_response({"error": "Provide guild_id+channel_name or user_id"}, 400)

        try:
            msg = await channel.fetch_message(int(message_id))
            await msg.delete()
        except discord.NotFound:
            return json_response({"error": "Message not found"}, 404)
        except discord.Forbidden:
            return json_response({"error": "Missing permission to delete this message"}, 403)
        except discord.HTTPException as e:
            return json_response({"error": str(e)}, 400)

        return json_response({"ok": True})

    async def post_edit(request):
        """Édite un message bot dans un channel ou un DM."""
        try:
            body = await request.json()
        except Exception:
            return json_response({"error": "Invalid JSON body"}, 400)

        message_id = body.get("message_id", "")
        text = body.get("text", "")
        guild_id = body.get("guild_id", "")
        channel_name = body.get("channel_name", "")
        user_id = body.get("user_id", "")

        if not message_id or not text:
            return json_response({"error": "message_id and text are required"}, 400)

        if guild_id and channel_name:
            channel = find_channel(ctx, guild_id, channel_name)
            if not channel:
                return json_response({"error": "Channel not found"}, 404)
        elif user_id:
            try:
                user = await ctx.client.fetch_user(int(user_id))
            except Exception:
                return json_response({"error": f"User {user_id} not found"}, 404)
            channel = await user.create_dm()
        else:
            return json_response({"error": "Provide guild_id+channel_name or user_id"}, 400)

        try:
            msg = await channel.fetch_message(int(message_id))
            await msg.edit(content=text)
        except discord.NotFound:
            return json_response({"error": "Message not found"}, 404)
        except discord.Forbidden:
            return json_response({"error": "Missing permission to edit this message"}, 403)
        except discord.HTTPException as e:
            return json_response({"error": str(e)}, 400)

        return json_response({"ok": True})

    app.router.add_get("/guilds", get_guilds)
    app.router.add_get("/channel/{guild_id}/{channel_name}/history", get_channel_history)
    app.router.add_get("/dm/{user_id}/history", get_dm_history)
    app.router.add_post("/send", post_send)
    app.router.add_post("/delete", post_delete)
    app.router.add_post("/edit", post_edit)
