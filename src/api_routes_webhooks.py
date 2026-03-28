"""
Internal API — webhook CRUD, reaction, and channel-management routes.
"""

import logging

import discord
from aiohttp import web

from .api_context import ApiContext, find_channel, json_response
from .emoji_utils import resolve_emoji

logger = logging.getLogger(__name__)


def register(app: web.Application, ctx: ApiContext) -> None:
    async def post_message(request):
        """Poste un message via webhook dans un channel."""
        guild_id = request.match_info["guild_id"]
        channel_name = request.match_info["channel_name"]

        try:
            body = await request.json()
        except Exception:
            return json_response({"error": "Invalid JSON body"}, 400)

        text = body.get("text", "")
        character_name = body.get("character_name", "")
        character_avatar = body.get("character_avatar", "")
        user_id = body.get("user_id", "")

        if not text or not character_name:
            return json_response({"error": "text and character_name are required"}, 400)

        channel = find_channel(ctx, guild_id, channel_name)
        if not channel:
            return json_response({"error": f"Channel #{channel_name} not found"}, 404)

        if not character_avatar and ctx.client.user and ctx.client.user.display_avatar:
            character_avatar = str(ctx.client.user.display_avatar.url)

        wh = await ctx.webhooks.get_or_create(channel)
        msg_ids = await ctx.webhooks.post_as_character(wh, character_name, text, character_avatar)

        if msg_ids:
            if user_id:
                ctx.memory.store_webhook_messages(user_id, str(channel.id), msg_ids, character_name, text)
            return json_response({"ok": True, "message_ids": msg_ids})
        else:
            return json_response({"error": "Post failed"}, 500)

    async def edit_message(request):
        """Édite le dernier message webhook d'un utilisateur dans un channel."""
        guild_id = request.match_info["guild_id"]
        channel_name = request.match_info["channel_name"]

        try:
            body = await request.json()
        except Exception:
            return json_response({"error": "Invalid JSON body"}, 400)

        user_id = body.get("user_id", "")
        new_text = body.get("text", "")

        if not user_id or not new_text:
            return json_response({"error": "user_id and text are required"}, 400)

        channel = find_channel(ctx, guild_id, channel_name)
        if not channel:
            return json_response({"error": f"Channel #{channel_name} not found"}, 404)

        msg_ids = ctx.memory.get_last_webhook_messages(user_id, str(channel.id))
        if not msg_ids:
            return json_response({"error": "No previous webhook message found"}, 404)

        wh = await ctx.webhooks.get_or_create(channel)
        success = await ctx.webhooks.edit_messages(wh, msg_ids, new_text)

        if success:
            ctx.memory.store_webhook_messages(user_id, str(channel.id), msg_ids, "", new_text)
            return json_response({"ok": True})
        else:
            return json_response({"error": "Edit failed — part count mismatch, repost instead"}, 409)

    async def delete_message(request):
        """Supprime le dernier message webhook d'un utilisateur dans un channel."""
        guild_id = request.match_info["guild_id"]
        channel_name = request.match_info["channel_name"]

        try:
            body = await request.json()
        except Exception:
            return json_response({"error": "Invalid JSON body"}, 400)

        user_id = body.get("user_id", "")
        if not user_id:
            return json_response({"error": "user_id is required"}, 400)

        channel = find_channel(ctx, guild_id, channel_name)
        if not channel:
            return json_response({"error": f"Channel #{channel_name} not found"}, 404)

        msg_ids = ctx.memory.get_last_webhook_messages(user_id, str(channel.id))
        if not msg_ids:
            return json_response({"error": "No previous webhook message found"}, 404)

        wh = await ctx.webhooks.get_or_create(channel)
        await ctx.webhooks.delete_messages(wh, msg_ids)
        return json_response({"ok": True})

    async def get_webhook_info(request):
        """Retourne les infos du dernier message webhook d'un utilisateur."""
        user_id = request.match_info["user_id"]
        guild_id = request.match_info["guild_id"]
        channel_name = request.match_info["channel_name"]

        channel = find_channel(ctx, guild_id, channel_name)
        if not channel:
            return json_response({"error": f"Channel #{channel_name} not found"}, 404)

        msg_ids = ctx.memory.get_last_webhook_messages(user_id, str(channel.id))
        last_text = ctx.memory.get_last_webhook_text(user_id, str(channel.id))

        return json_response({
            "message_ids": msg_ids,
            "text": last_text,
            "channel": channel_name,
            "guild_id": guild_id,
        })

    async def _resolve_channel(body: dict, query=None):
        guild_id = (body or {}).get("guild_id", "")
        channel_name = (body or {}).get("channel_name", "")
        user_id = (body or {}).get("user_id", "")

        if guild_id and channel_name:
            ch = find_channel(ctx, guild_id, channel_name)
            return ch, (json_response({"error": "Channel not found"}, 404) if not ch else None)
        elif user_id:
            try:
                user = await ctx.client.fetch_user(int(user_id))
                return await user.create_dm(), None
            except Exception:
                return None, json_response({"error": f"User {user_id} not found"}, 404)
        return None, json_response({"error": "Provide guild_id+channel_name or user_id"}, 400)

    async def post_react(request):
        """Ajoute une réaction emoji sur un message Discord."""
        try:
            body = await request.json()
        except Exception:
            return json_response({"error": "Invalid JSON body"}, 400)

        message_id = body.get("message_id", "")
        emoji = body.get("emoji", "")

        if not message_id or not emoji:
            return json_response({"error": "message_id and emoji are required"}, 400)

        channel, err = await _resolve_channel(body)
        if err:
            return err

        try:
            msg = await channel.fetch_message(int(message_id))
            guild = channel.guild if hasattr(channel, "guild") else None
            await msg.add_reaction(resolve_emoji(emoji, guild))
        except discord.NotFound:
            return json_response({"error": "Message not found"}, 404)
        except discord.HTTPException as e:
            return json_response({"error": str(e)}, 400)

        return json_response({"ok": True})

    async def post_unreact(request):
        """Retire une réaction emoji posée par le bot sur un message."""
        try:
            body = await request.json()
        except Exception:
            return json_response({"error": "Invalid JSON body"}, 400)

        message_id = body.get("message_id", "")
        emoji = body.get("emoji", "")

        if not message_id or not emoji:
            return json_response({"error": "message_id and emoji are required"}, 400)

        channel, err = await _resolve_channel(body)
        if err:
            return err

        try:
            msg = await channel.fetch_message(int(message_id))
            guild = channel.guild if hasattr(channel, "guild") else None
            await msg.remove_reaction(resolve_emoji(emoji, guild), ctx.client.user)
        except discord.NotFound:
            return json_response({"error": "Message not found"}, 404)
        except discord.HTTPException as e:
            return json_response({"error": str(e)}, 400)

        return json_response({"ok": True})

    async def get_reactions(request):
        """Retourne les réactions d'un message."""
        message_id = request.match_info["message_id"]
        q = request.rel_url.query
        guild_id = q.get("guild_id", "")
        channel_name = q.get("channel_name", "")
        user_id = q.get("user_id", "")

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
        except discord.NotFound:
            return json_response({"error": "Message not found"}, 404)

        result = []
        for reaction in msg.reactions:
            users_list = []
            async for user in reaction.users():
                users_list.append({
                    "id": str(user.id),
                    "name": user.name,
                    "display_name": getattr(user, "display_name", user.name),
                })
            result.append({
                "emoji": str(reaction.emoji),
                "count": reaction.count,
                "bot_reacted": reaction.me,
                "users": users_list,
            })

        return json_response(result)

    async def create_channel(request):
        """Crée un channel texte dans un serveur, ou confirme qu'il existe déjà."""
        try:
            body = await request.json()
        except Exception:
            return json_response({"error": "Invalid JSON body"}, 400)

        guild_id = body.get("guild_id", "")
        channel_name = body.get("channel_name", "")
        topic = body.get("topic", "")
        category_name = body.get("category_name", "")

        if not guild_id or not channel_name:
            return json_response({"error": "guild_id and channel_name are required"}, 400)

        existing = find_channel(ctx, guild_id, channel_name)
        if existing:
            return json_response({"ok": True, "channel_id": str(existing.id), "channel_name": existing.name, "created": False})

        guild = next((g for g in ctx.client.guilds if str(g.id) == guild_id), None)
        if not guild:
            return json_response({"error": f"Guild {guild_id} not found"}, 404)

        category = None
        if category_name:
            category = next(
                (c for c in guild.categories if c.name.lower() == category_name.lower()),
                None,
            )

        try:
            new_channel = await guild.create_text_channel(
                channel_name,
                topic=topic or None,
                category=category,
            )
        except discord.Forbidden:
            return json_response({"error": "Missing 'Manage Channels' permission"}, 403)
        except discord.HTTPException as exc:
            return json_response({"error": str(exc)}, 500)

        logger.info("Channel créé : #%s (guild %s)", new_channel.name, guild_id)
        return json_response({"ok": True, "channel_id": str(new_channel.id), "channel_name": new_channel.name, "created": True})

    app.router.add_post("/channel/{guild_id}/{channel_name}/post", post_message)
    app.router.add_post("/channel/{guild_id}/{channel_name}/edit", edit_message)
    app.router.add_post("/channel/{guild_id}/{channel_name}/delete", delete_message)
    app.router.add_get("/webhook/{user_id}/{guild_id}/{channel_name}", get_webhook_info)
    app.router.add_post("/react", post_react)
    app.router.add_post("/unreact", post_unreact)
    app.router.add_get("/reactions/{message_id}", get_reactions)
    app.router.add_post("/channel/create", create_channel)
