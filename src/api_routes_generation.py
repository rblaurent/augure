"""
Internal API — image and music generation routes.
"""

import logging
from datetime import datetime, timezone

import discord
from aiohttp import web

from . import config
from .api_context import ApiContext, find_channel, find_channel_by_id, json_response
from .api_generation_progress import GenerationProgress
from .vram_arbitrator import VRAMComfyUIContext

logger = logging.getLogger(__name__)


def register(app: web.Application, ctx: ApiContext) -> None:
    async def generate_image(request):
        """Génère une image via ComfyUI et la poste dans un channel ou un DM."""
        try:
            body = await request.json()
        except Exception:
            return json_response({"error": "Invalid JSON body"}, 400)

        prompt = body.get("prompt", "")
        negative = body.get("negative", "")
        workflow = body.get("workflow", "z_turbo")
        guild_id = body.get("guild_id", "")
        channel_name = body.get("channel_name", "")
        user_id = body.get("user_id", "")
        reply_channel_id = body.get("reply_channel_id", "")
        reply_user_id = body.get("reply_user_id", "")
        image_url = body.get("image_url", "")
        character = body.get("character", "")

        if not prompt:
            return json_response({"error": "prompt is required"}, 400)

        if not await ctx.comfy.check_health():
            return json_response({"error": "ComfyUI not available"}, 503)

        if guild_id and channel_name:
            destination = find_channel(ctx, guild_id, channel_name)
            if not destination:
                return json_response({"error": "Channel not found"}, 404)
        elif user_id:
            try:
                dest_user = await ctx.client.fetch_user(int(user_id))
                destination = await dest_user.create_dm()
            except Exception:
                return json_response({"error": f"User {user_id} not found"}, 404)
        else:
            return json_response({"error": "Provide guild_id+channel_name or user_id"}, 400)

        wf_cfg = ctx.comfy._workflows.get(workflow, {})
        is_video = wf_cfg.get("media_type") == "video"

        progress: GenerationProgress | None = None
        reply_ch = None
        if reply_channel_id:
            reply_ch = find_channel_by_id(ctx, reply_channel_id)
        elif reply_user_id:
            try:
                _ru = await ctx.client.fetch_user(int(reply_user_id))
                reply_ch = await _ru.create_dm()
            except Exception as exc:
                logger.warning("GenerationProgress: DM channel lookup failed: %s", exc)
        if reply_ch:
            progress = GenerationProgress(reply_ch, kind="image", thumbnail_url=image_url)
            params = {"Workflow": workflow}
            if prompt:
                params["Prompt"] = prompt[:1024]
            title = "Génération de vidéo" if is_video else "Génération d'image"
            await progress.start(title, params)

        async def progress_cb(stage: str, detail: str = "") -> None:
            if progress:
                await progress.update(stage, detail)

        extra_params: dict = {}
        if image_url:
            try:
                extra_params["image"] = await ctx.comfy.upload_image(image_url)
            except Exception as exc:
                logger.error("Image upload failed for url=%s : %s", image_url, exc)
                if progress:
                    await progress.fail(f"Échec upload image source : {exc}")
                return json_response({"error": f"Image upload failed: {exc}"}, 500)
        if character:
            extra_params["character"] = character

        # Acquérir le lock VRAM pour ComfyUI (décharge le LLM)
        from .vram_arbitrator import get_vram_arbitrator
        vram = get_vram_arbitrator()
        async with VRAMComfyUIContext(vram):
            media_data, seed = await ctx.comfy.generate(
                workflow_name=workflow,
                prompt=prompt,
                negative=negative,
                progress_cb=progress_cb if progress else None,
                **extra_params,
            )

        if not media_data:
            if progress:
                await progress.fail("Génération ComfyUI échouée")
            return json_response({"error": "Generation failed"}, 500)

        filename = "generated.mp4" if is_video else "generated.png"

        combine = progress is not None and reply_ch is not None and destination.id == reply_ch.id

        if combine:
            if is_video:
                card = discord.Embed(title="Vidéo générée", color=0x57F287)
                card.add_field(name="Workflow", value=workflow, inline=True)
                card.add_field(name="Prompt", value=prompt[:1024], inline=False)
                if image_url:
                    card.set_thumbnail(url=image_url)
            else:
                card = discord.Embed(title="Image générée", color=0x57F287)
                card.add_field(name="Workflow", value=workflow, inline=True)
                card.add_field(name="Prompt", value=prompt[:1024], inline=False)
                card.set_image(url=f"attachment://{filename}")
            sent = await progress.finish_with_file(card, discord.File(media_data, filename=filename))
            if sent is None:
                media_data.seek(0)
                sent = await destination.send(file=discord.File(media_data, filename=filename))
        else:
            sent = await destination.send(file=discord.File(media_data, filename=filename))
            if progress:
                url_for_card = sent.attachments[0].url if sent.attachments else ""
                if url_for_card:
                    if is_video:
                        card = discord.Embed(title="Vidéo générée", color=0x57F287)
                        card.add_field(name="Workflow", value=workflow, inline=True)
                        card.add_field(name="Prompt", value=prompt[:1024], inline=False)
                        if image_url:
                            card.set_thumbnail(url=image_url)
                    else:
                        card = discord.Embed(title="Image générée", color=0x57F287)
                        card.add_field(name="Workflow", value=workflow, inline=True)
                        card.add_field(name="Prompt", value=prompt[:1024], inline=False)
                        card.set_image(url=url_for_card)
                    await progress.finish(card)

        url = sent.attachments[0].url if sent and sent.attachments else ""

        now = datetime.now(timezone.utc).isoformat()
        if is_video:
            ctx.memory.append_video_media({
                "workflow": workflow,
                "prompt": prompt,
                "negative": negative,
                "seed": seed,
                "url": url,
                "source_image_url": image_url,
                "character": character,
                "channel_name": channel_name,
                "guild_id": guild_id,
                "message_id": str(sent.id),
                "generated_at": now,
            })
        else:
            ctx.memory.append_image_media({
                "workflow": workflow,
                "prompt": prompt,
                "negative": negative,
                "seed": seed,
                "url": url,
                "channel_name": channel_name,
                "guild_id": guild_id,
                "message_id": str(sent.id),
                "generated_at": now,
            })

        return json_response({"ok": True, "url": url, "message_id": str(sent.id), "seed": seed})

    async def generate_music(request):
        """Génère un morceau via Suno et le poste dans un channel Discord."""
        try:
            body = await request.json()
        except Exception:
            return json_response({"error": "Invalid JSON body"}, 400)

        prompt = body.get("prompt", "")
        style = body.get("style", "")
        title = body.get("title", "")
        guild_id = body.get("guild_id", "")
        channel_name = body.get("channel_name", "musique")
        make_instrumental = body.get("make_instrumental", False)
        post_both = body.get("post_both", False)
        reply_channel_id = body.get("reply_channel_id", "")
        reply_user_id = body.get("reply_user_id", "")

        if not prompt:
            return json_response({"error": "prompt is required"}, 400)
        if not guild_id:
            return json_response({"error": "guild_id is required"}, 400)

        if not ctx.suno or not ctx.suno._api_key:
            return json_response({"error": "Suno not configured — set SUNO_API_KEY"}, 503)

        channel = find_channel(ctx, guild_id, channel_name)
        if not channel:
            return json_response({
                "error": f"Channel #{channel_name} not found in guild {guild_id}. Create it first with POST /channel/create"
            }, 404)

        progress: GenerationProgress | None = None
        reply_ch = None
        if reply_channel_id:
            reply_ch = find_channel_by_id(ctx, reply_channel_id)
        elif reply_user_id:
            try:
                _ru = await ctx.client.fetch_user(int(reply_user_id))
                reply_ch = await _ru.create_dm()
            except Exception as exc:
                logger.warning("GenerationProgress: DM channel lookup failed: %s", exc)
        if reply_ch:
            progress = GenerationProgress(reply_ch, kind="music")
            params = {}
            if title:
                params["Titre"] = title
            if style:
                params["Style"] = style
            if prompt:
                params["Prompt"] = prompt[:200]
            await progress.start("Génération musicale", params)

        async def progress_cb(stage: str, detail: str = "") -> None:
            if progress:
                await progress.update(stage, detail)

        songs = await ctx.suno.generate(
            prompt=prompt,
            style=style,
            title=title,
            make_instrumental=make_instrumental,
            progress_cb=progress_cb if progress else None,
        )
        if not songs:
            if progress:
                await progress.fail("Génération Suno échouée")
            return json_response({"error": "Music generation failed"}, 500)

        to_post = songs if post_both else songs[:1]

        config.MUSIC_DIR.mkdir(parents=True, exist_ok=True)

        combine = progress is not None and reply_ch is not None and channel.id == reply_ch.id

        results = []
        for i, song in enumerate(to_post):
            audio_path = config.MUSIC_DIR / song.filename
            audio_path.write_bytes(song.audio_data.read())
            song.audio_data.seek(0)

            card = discord.Embed(
                title=song.title,
                description=prompt[:500] if prompt else None,
                color=0x1DB954,
            )
            if song.tags:
                card.add_field(name="Style", value=song.tags, inline=True)
            card.add_field(name="Clip ID", value=song.clip_id, inline=True)
            if song.image_url:
                card.set_thumbnail(url=song.image_url)

            if combine and i == 0:
                sent = await progress.finish_with_file(card, discord.File(song.audio_data, filename=song.filename))
                if sent is None:
                    song.audio_data.seek(0)
                    sent = await channel.send(file=discord.File(song.audio_data, filename=song.filename), embed=card)
            else:
                sent = await channel.send(file=discord.File(song.audio_data, filename=song.filename), embed=card)

            audio_message_id = str(sent.id)

            now = datetime.now(timezone.utc).isoformat()
            post_data = {
                "clip_id": song.clip_id,
                "title": song.title,
                "tags": song.tags,
                "prompt": prompt,
                "style": style,
                "audio_url": song.audio_url,
                "image_url": song.image_url,
                "filename": song.filename,
                "channel_id": str(channel.id),
                "channel_name": channel_name,
                "guild_id": guild_id,
                "generated_at": now,
                "reactions": {},
            }

            ctx.memory.store_music_post(audio_message_id, post_data)
            ctx.memory.append_music_library({**post_data, "message_id": audio_message_id})

            results.append({
                "clip_id": song.clip_id,
                "title": song.title,
                "tags": song.tags,
                "audio_url": song.audio_url,
                "image_url": song.image_url,
                "filename": song.filename,
                "message_id": audio_message_id,
            })

        if progress and results and not combine:
            first = results[0]
            first_song = next((s for s in to_post if s.clip_id == first["clip_id"]), None)
            card = discord.Embed(
                title=first["title"],
                description=prompt[:500] if prompt else None,
                color=0x1DB954,
            )
            if first_song and first_song.tags:
                card.add_field(name="Style", value=first_song.tags, inline=True)
            card.add_field(name="Clip ID", value=first["clip_id"], inline=True)
            if first_song and first_song.image_url:
                card.set_thumbnail(url=first_song.image_url)
            await progress.finish(card)

        return json_response({"ok": True, "songs": results})

    app.router.add_post("/generate", generate_image)
    app.router.add_post("/music", generate_music)
