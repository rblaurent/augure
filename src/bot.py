"""
Augure — Maître du Jeu autonome pour serveurs Discord de roleplay.
Point d'entrée. Le bot est une interface mince entre Discord et le MJ (OpenCode).
Le MJ lit/écrit les fichiers mémoire directement. Le bot gère uniquement
les actions Discord : détecter les messages, router, signaler les réactions.
"""

import asyncio
import logging

import discord

from . import config, internal_api
from .comfyui_bridge import ComfyUIBridge
from .memory_manager import MemoryManager
from .mj_screen import MJScreen
from .npc_invoker import NPCInvoker
from .opencode_bridge import OpenCodeQueue, OpenCodeWatchdogRunner
from .sanitizer import OutputSanitizer
from .suno_bridge import SunoBridge
from .vram_arbitrator import get_vram_arbitrator
from .watchdog import WatchdogService
from .webhook_manager import WebhookManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True
intents.dm_messages = True
intents.reactions = True

client = discord.Client(intents=intents)

# Services
vram = get_vram_arbitrator()
mj_screen = MJScreen(client)
npc_invoker = NPCInvoker(vram)
comfy = ComfyUIBridge(config.COMFYUI_URL)
suno = SunoBridge(config.SUNO_API_KEY, config.SUNO_BASE_URL)
webhooks = WebhookManager(client)
memory = MemoryManager()
sanitizer = OutputSanitizer()

mj_queue = OpenCodeQueue(vram, mj_screen)
watchdog_runner = OpenCodeWatchdogRunner(vram, mj_screen)
watchdog_svc = WatchdogService(client, memory, watchdog_runner)

_SLEEP_FILE = config.MEMORY_DIR / "meta" / "sleep.flag"


def _is_sleeping() -> bool:
    return _SLEEP_FILE.exists()


def _set_sleep(sleeping: bool) -> None:
    if sleeping:
        _SLEEP_FILE.touch()
    else:
        _SLEEP_FILE.unlink(missing_ok=True)


# ──────────────────────────────────────────────
# Events
# ──────────────────────────────────────────────

@client.event
async def on_ready() -> None:
    logger.info("Augure connecté : %s (id=%s)", client.user, client.user.id)
    await webhooks.load()
    mj_queue.start()

    await internal_api.start(client, webhooks, memory, comfy, suno, mj_screen, npc_invoker)

    # Initialiser la structure mémoire
    for guild in client.guilds:
        memory.ensure_scene_dirs(str(guild.id))

    if await comfy.check_health():
        logger.info("ComfyUI disponible : %s", config.COMFYUI_URL)
    else:
        logger.warning("ComfyUI non disponible : %s", config.COMFYUI_URL)

    if config.SUNO_API_KEY:
        logger.info("Suno configuré : %s", config.SUNO_BASE_URL)
    else:
        logger.warning("SUNO_API_KEY non définie — génération musicale désactivée")

    if _is_sleeping():
        await client.change_presence(status=discord.Status.idle)
        logger.info("Sleep mode active")
    else:
        await client.change_presence(status=discord.Status.online)

    if config.WATCHDOG_INTERVAL > 0:
        asyncio.create_task(watchdog_svc.run_loop())
        logger.info("Watchdog MJ démarré (intervalle : %d min)", config.WATCHDOG_INTERVAL)


@client.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent) -> None:
    """Enregistre les réactions music et bufferise les réactions sur messages bot."""
    if payload.user_id == client.user.id:
        return
    if memory.get_music_post(str(payload.message_id)):
        memory.record_music_reaction(
            message_id=str(payload.message_id),
            emoji=str(payload.emoji),
            user_id=str(payload.user_id),
        )

    channel = client.get_channel(payload.channel_id)
    if channel is None:
        return
    try:
        msg = await channel.fetch_message(payload.message_id)
    except discord.HTTPException:
        return
    if msg.author.id != client.user.id:
        return
    memory.add_pending_reaction(
        channel_id=str(payload.channel_id),
        message_id=str(payload.message_id),
        emoji=str(payload.emoji),
        user_id=str(payload.user_id),
        message_content=msg.content,
    )


@client.event
async def on_message(message: discord.Message) -> None:
    if message.author.bot:
        return

    if _is_sleeping():
        # Commandes admin même en sleep mode
        if _handle_admin_command(message):
            return
        return

    is_dm = isinstance(message.channel, discord.DMChannel)
    is_mention = client.user in message.mentions if hasattr(message, "mentions") else False

    # Vérifier les role mentions
    if not is_mention and not is_dm and message.role_mentions and message.guild:
        member = message.guild.get_member(client.user.id)
        if member:
            bot_role_ids = {r.id for r in member.roles}
            is_mention = any(r.id in bot_role_ids for r in message.role_mentions)

    # Commandes admin
    if _handle_admin_command(message):
        return

    # Déterminer si c'est un message RP (dans #rp)
    is_rp_channel = (
        not is_dm
        and hasattr(message.channel, "name")
        and message.channel.name.lower() == config.load_channels(str(message.guild.id))["rp"].lower()
    )

    logger.info(
        "on_message: author=%s id=%s is_dm=%s is_mention=%s is_rp=%s content=%r",
        message.author,
        message.author.id,
        is_dm,
        is_mention,
        is_rp_channel,
        message.content[:80],
    )

    # Routage :
    # 1. Message dans #rp → MJ orchestre la scène
    # 2. @mention dans n'importe quel channel → MJ répond
    # 3. DM → MJ répond
    if not is_rp_channel and not is_mention and not is_dm:
        return

    guild_id = str(message.guild.id) if message.guild else ""

    # Nettoyer la @mention si présente
    content = message.content
    if is_mention:
        content = content.replace(f"<@{client.user.id}>", "").strip()
        content = content.replace(f"<@!{client.user.id}>", "").strip()

    # Image jointe
    if message.attachments:
        attach = message.attachments[0]
        if attach.content_type and attach.content_type.startswith("image/"):
            content = f"{content}\n[IMAGE JOINTE : {attach.url}]".strip()

    if not content and not is_rp_channel:
        return
    if not content and is_rp_channel:
        content = "(action sans texte)"

    emojis = config.load_bot_settings()["emojis"]
    await message.add_reaction(emojis["processing"])
    try:
        if is_rp_channel:
            await _handle_rp_message(message, content, guild_id)
        else:
            await _handle_general_message(message, content, is_dm, guild_id)
        await message.remove_reaction(emojis["processing"], client.user)
        if emojis["success"]:
            await message.add_reaction(emojis["success"])
    except Exception:
        try:
            await message.remove_reaction(emojis["processing"], client.user)
            await message.add_reaction(emojis["error"])
        except discord.HTTPException:
            pass
        raise


def _handle_admin_command(message: discord.Message) -> bool:
    """Traite les commandes admin. Retourne True si une commande a été traitée."""
    stripped = message.content.strip().lower()
    if str(message.author.id) not in config.ADMIN_USER_IDS:
        return False

    if stripped in ("!stop", f"<@{client.user.id}> !stop"):
        asyncio.create_task(_do_stop(message))
        return True
    if stripped in ("!sleep", "!wake"):
        asyncio.create_task(_do_sleep_toggle(message, stripped == "!sleep"))
        return True
    return False


async def _do_stop(message: discord.Message) -> None:
    emojis = config.load_bot_settings()["emojis"]
    await message.add_reaction(emojis["stop"])
    logger.info("Kill switch triggered by %s", message.author)
    await client.close()


async def _do_sleep_toggle(message: discord.Message, go_sleep: bool) -> None:
    emojis = config.load_bot_settings()["emojis"]
    _set_sleep(go_sleep)
    if go_sleep:
        await client.change_presence(status=discord.Status.idle)
        await message.add_reaction(emojis["sleep"])
        logger.info("Sleep mode enabled by %s", message.author)
    else:
        await client.change_presence(status=discord.Status.online)
        await message.add_reaction(emojis["wake"])
        logger.info("Sleep mode disabled by %s", message.author)


# ──────────────────────────────────────────────
# Handlers
# ──────────────────────────────────────────────

async def _handle_rp_message(message: discord.Message, content: str, guild_id: str) -> None:
    """Message dans #rp — le MJ orchestre. Pas de réponse directe du bot."""
    ctx = {
        "is_dm": False,
        "message_id": str(message.id),
        "guild_name": message.guild.name if message.guild else None,
        "guild_id": guild_id,
        "channel_name": message.channel.name,
        "channel_id": str(message.channel.id),
        "recent_history": await _get_history(message.channel, limit=50),
    }

    req = mj_queue.enqueue(
        user_message=content,
        context=ctx,
        user_id=str(message.author.id),
        guild_id=guild_id,
        is_rp=True,
    )

    try:
        await asyncio.wait_for(req.future, timeout=config.MJ_TIMEOUT * 2)
    except asyncio.TimeoutError:
        logger.error("MJ RP request timed out for guild %s", guild_id)
    except Exception as exc:
        logger.error("MJ RP request failed: %s", exc)
    # Le MJ a posté via webhooks pendant son raisonnement — rien à envoyer ici.


async def _handle_general_message(
    message: discord.Message, content: str, is_dm: bool, guild_id: str
) -> None:
    """@mention ou DM — le MJ répond directement en texte."""
    ctx = {
        "is_dm": is_dm,
        "message_id": str(message.id),
        "guild_name": message.guild.name if message.guild else None,
        "guild_id": guild_id,
        "channel_name": None if is_dm else message.channel.name,
        "channel_id": str(message.channel.id),
        "user_guilds": [
            {
                "id": str(g.id),
                "name": g.name,
                "channels": [c.name for c in g.text_channels],
            }
            for g in client.guilds
            if message.guild is None or g.get_member(message.author.id)
        ],
        "recent_history": await _get_history(message.channel, limit=30 if is_dm else 50),
    }

    req = mj_queue.enqueue(
        user_message=content,
        context=ctx,
        user_id=str(message.author.id),
        guild_id=guild_id,
        is_rp=False,
    )

    try:
        async with message.channel.typing():
            try:
                response = await asyncio.wait_for(req.future, timeout=config.MJ_TIMEOUT * 2)
            except asyncio.TimeoutError:
                await message.channel.send("⏱️ La requête a pris trop de temps. Réessaie.")
                return
            except Exception as exc:
                logger.error("MJ general request failed: %s", exc)
                await message.channel.send("❌ Erreur lors du traitement. Réessaie.")
                return
    except discord.HTTPException:
        response = await asyncio.wait_for(req.future, timeout=config.MJ_TIMEOUT * 2)

    text = sanitizer.sanitize(response) if response else ""
    logger.info("MJ response len=%d", len(text))
    if text:
        from .message_splitter import split_message
        for part in split_message(text):
            await message.channel.send(part)


async def _get_history(channel, limit: int) -> list[dict]:
    messages = []
    async for msg in channel.history(limit=limit):
        content = msg.content
        for att in msg.attachments:
            if att.content_type and att.content_type.startswith("image/"):
                content = f"{content}\n[IMAGE : {att.url}]".strip()
        messages.append({
            "id": str(msg.id),
            "author": msg.author.display_name,
            "content": content,
            "timestamp": msg.created_at.isoformat(),
        })
    return list(reversed(messages))


def main() -> None:
    if not config.DISCORD_TOKEN:
        raise SystemExit("DISCORD_TOKEN manquant. Configure le fichier .env.")
    client.run(config.DISCORD_TOKEN, log_handler=None)


if __name__ == "__main__":
    main()
