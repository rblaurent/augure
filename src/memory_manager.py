"""
Memory Manager — comptabilité Discord que le MJ ne peut pas faire lui-même :
 - IDs des messages webhook (pour édition)
 - Timestamps last_sync (pour la maintenance/watchdog)
 - Création des répertoires mémoire
 - Logs média (images, vidéos, musique)

Le MJ lit et écrit directement les fichiers Markdown via ses outils Read/Write/Edit.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from . import config

logger = logging.getLogger(__name__)

META_DIR = config.MEMORY_DIR / "meta"

LAST_SYNC_FILE = META_DIR / "last_sync.json"
WEBHOOK_MESSAGES_FILE = META_DIR / "webhook_messages.json"
MUSIC_POSTS_FILE = META_DIR / "music_posts.json"
MUSIC_LIBRARY_FILE = META_DIR / "music_library.md"


def _load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


class MemoryManager:
    def __init__(self) -> None:
        self._webhook_messages: dict = _load_json(WEBHOOK_MESSAGES_FILE)
        self._music_posts: dict = _load_json(MUSIC_POSTS_FILE)
        self._pending_reactions: dict[str, list] = {}
        self._handled_message_ids: set[int] = set()

    # ── Webhook messages ───────────────────────────────────────────────────

    def store_webhook_messages(
        self,
        user_id: str,
        channel_id: str,
        message_ids: list[int],
        character_name: str = "",
        text: str = "",
    ) -> None:
        key = f"{user_id}:{channel_id}"
        self._webhook_messages[key] = {
            "message_ids": message_ids,
            "character_name": character_name,
            "text": text,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        _save_json(WEBHOOK_MESSAGES_FILE, self._webhook_messages)

    def get_last_webhook_text(self, user_id: str, channel_id: str) -> str:
        key = f"{user_id}:{channel_id}"
        return self._webhook_messages.get(key, {}).get("text", "")

    def get_last_webhook_messages(self, user_id: str, channel_id: str) -> list[int]:
        key = f"{user_id}:{channel_id}"
        return self._webhook_messages.get(key, {}).get("message_ids", [])

    # ── Watchdog / maintenance last-seen ──────────────────────────────────

    def get_last_sync(self, channel_id: str) -> dict:
        return _load_json(LAST_SYNC_FILE).get(channel_id, {})

    def update_last_sync(self, channel_id: str, last_message_id: int) -> None:
        data = _load_json(LAST_SYNC_FILE)
        data[channel_id] = {
            "last_message_id": last_message_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        _save_json(LAST_SYNC_FILE, data)

    def get_watchdog_last_message_id(self, channel_id: str) -> int | None:
        return _load_json(LAST_SYNC_FILE).get(f"watchdog:{channel_id}", {}).get("last_message_id")

    def update_watchdog_last_message_id(self, channel_id: str, message_id: int) -> None:
        data = _load_json(LAST_SYNC_FILE)
        data[f"watchdog:{channel_id}"] = {
            "last_message_id": message_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        _save_json(LAST_SYNC_FILE, data)

    # ── Music posts ────────────────────────────────────────────────────────

    def store_music_post(self, message_id: str, data: dict) -> None:
        self._music_posts[message_id] = data
        _save_json(MUSIC_POSTS_FILE, self._music_posts)

    def get_music_post(self, message_id: str) -> dict | None:
        return self._music_posts.get(message_id)

    def record_music_reaction(self, message_id: str, emoji: str, user_id: str) -> None:
        post = self._music_posts.get(message_id)
        if not post:
            return
        reactions = post.setdefault("reactions", {})
        users = reactions.setdefault(emoji, [])
        if user_id not in users:
            users.append(user_id)
        _save_json(MUSIC_POSTS_FILE, self._music_posts)

    def add_pending_reaction(
        self, channel_id: str, message_id: str, emoji: str,
        user_id: str, message_content: str
    ) -> None:
        self._pending_reactions.setdefault(channel_id, []).append({
            "message_id": message_id,
            "emoji": emoji,
            "user_id": user_id,
            "message_content": message_content,
        })

    def pop_pending_reactions(self, channel_id: str) -> list:
        return self._pending_reactions.pop(channel_id, [])

    # ── Handled messages (dedup with watchdog) ─────────────────────────────

    def mark_message_handled(self, message_id: int) -> None:
        self._handled_message_ids.add(message_id)

    def pop_handled_message_ids(self) -> set[int]:
        ids = self._handled_message_ids.copy()
        self._handled_message_ids.clear()
        return ids

    def append_music_library(self, data: dict) -> None:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        channel_name = data.get("channel_name", "")
        entry = (
            f"\n## {now} — #{channel_name}\n\n"
            f"- **Titre** : {data.get('title', '')}\n"
            f"- **Clip ID** : {data.get('clip_id', '')}\n"
            f"- **Message ID** : {data.get('message_id', '')}\n"
            f"- **Prompt** : {data.get('prompt', '')}\n"
            f"- **Style** : {data.get('tags', '')}\n"
            f"- **Audio URL** : {data.get('audio_url', '')}\n"
            f"- **Fichier** : {data.get('filename', '')}\n"
            f"- **Réactions** : (aucune pour l'instant)\n"
            f"- **Notes qualité** : —\n"
        )
        try:
            existing = MUSIC_LIBRARY_FILE.read_text(encoding="utf-8") if MUSIC_LIBRARY_FILE.exists() else "# Bibliothèque Musicale d'Augure\n"
            MUSIC_LIBRARY_FILE.write_text(existing + entry, encoding="utf-8")
        except Exception as exc:
            logger.error("append_music_library error: %s", exc)

    def append_image_media(self, data: dict) -> None:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        channel_info = data.get("channel_name", "")
        if data.get("guild_id"):
            channel_info = f"#{channel_info} (guild {data['guild_id']})"
        entry = (
            f"\n## {now}\n\n"
            f"- **Workflow** : {data.get('workflow', '')}\n"
            f"- **Prompt** : {data.get('prompt', '')}\n"
            f"- **Negative** : {data.get('negative', '') or '(aucun)'}\n"
            f"- **Seed** : {data.get('seed', '')}\n"
            f"- **URL** : {data.get('url', '')}\n"
            f"- **Posté dans** : {channel_info}\n"
            f"- **Message ID** : {data.get('message_id', '')}\n"
            f"- **Généré le** : {data.get('generated_at', '')}\n"
            f"- **Notes** : —\n"
        )
        image_file = config.MEMORY_DIR / "media" / "images.md"
        try:
            image_file.parent.mkdir(parents=True, exist_ok=True)
            existing = image_file.read_text(encoding="utf-8") if image_file.exists() else "# Images générées\n"
            image_file.write_text(existing + entry, encoding="utf-8")
        except Exception as exc:
            logger.error("append_image_media error: %s", exc)

    def append_video_media(self, data: dict) -> None:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        channel_info = data.get("channel_name", "")
        if data.get("guild_id"):
            channel_info = f"#{channel_info} (guild {data['guild_id']})"
        entry = (
            f"\n## {now}\n\n"
            f"- **Workflow** : {data.get('workflow', '')}\n"
            f"- **Prompt** : {data.get('prompt', '')}\n"
            f"- **Negative** : {data.get('negative', '') or '(aucun)'}\n"
            f"- **Seed** : {data.get('seed', '')}\n"
            f"- **Image source** : {data.get('source_image_url', '') or '(aucune)'}\n"
            f"- **Personnage** : {data.get('character', '') or '(non précisé)'}\n"
            f"- **URL** : {data.get('url', '')}\n"
            f"- **Posté dans** : {channel_info}\n"
            f"- **Message ID** : {data.get('message_id', '')}\n"
            f"- **Généré le** : {data.get('generated_at', '')}\n"
            f"- **Notes** : —\n"
        )
        video_file = config.MEMORY_DIR / "media" / "videos.md"
        try:
            video_file.parent.mkdir(parents=True, exist_ok=True)
            existing = video_file.read_text(encoding="utf-8") if video_file.exists() else "# Vidéos générées\n"
            video_file.write_text(existing + entry, encoding="utf-8")
        except Exception as exc:
            logger.error("append_video_media error: %s", exc)

    # ── Memory directories ─────────────────────────────────────────────────

    def ensure_scene_dirs(self, guild_id: str) -> None:
        """Crée la structure mémoire de base pour un serveur."""
        base = config.MEMORY_DIR
        dirs = [
            base / "world" / "locations",
            base / "world" / "factions",
            base / "world" / "magic",
            base / "world" / "history",
            base / "characters",
            base / "players",
            base / "scenes",
            base / "arcs" / "actifs",
            base / "arcs" / "clos",
            base / "media",
            base / "meta" / "invocation_logs",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

        # Fichiers initiaux
        files = {
            base / "scenes" / "active_scene.md": "# Scène active\n\n(Aucune scène en cours)\n",
            base / "scenes" / "scene_queue.md": "# File de scènes\n\n",
            base / "scenes" / "scene_history.md": "# Historique des scènes\n\n",
            base / "arcs" / "index.md": "# Arcs narratifs\n\n## Actifs\n\n## Clos\n\n",
            base / "arcs" / "fils_ouverts.md": "# Fils narratifs ouverts\n\n",
            base / "meta" / "mj_notes.md": "# Notes du MJ\n\n",
            base / "meta" / "mj_log.md": "# Journal du MJ\n\n",
            base / "meta" / "watchdog_log.md": "# Log Watchdog\n\n",
            base / "meta" / "missing_features.md": "# Fonctionnalités manquantes\n\n",
            base / "world" / "index.md": "# Encyclopédie du Monde\n\n",
        }
        for path, default_content in files.items():
            if not path.exists():
                path.write_text(default_content, encoding="utf-8")
