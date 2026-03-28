import json
import os
import re
from pathlib import Path

import yaml

# Workspace paths (inside Docker container)
WORKSPACE = Path("/workspace")
MEMORY_DIR = WORKSPACE / "memory"
CONFIG_DIR = WORKSPACE / "config"
WORKFLOWS_DIR = WORKSPACE / "workflows"
SKILLS_DIR = WORKSPACE / "skills"

# Discord
DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")

# ComfyUI
COMFYUI_HOST: str = os.getenv("COMFYUI_HOST", "host.docker.internal")
COMFYUI_PORT: int = int(os.getenv("COMFYUI_PORT", "8188"))
COMFYUI_URL: str = f"http://{COMFYUI_HOST}:{COMFYUI_PORT}"

# Suno — génération musicale
SUNO_API_KEY: str = os.getenv("SUNO_API_KEY", "")
SUNO_BASE_URL: str = os.getenv("SUNO_BASE_URL", "https://api.sunoapi.org")
MUSIC_DIR: Path = WORKSPACE / "music"

# Ollama — LLM local
OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "host.docker.internal")
OLLAMA_PORT: int = int(os.getenv("OLLAMA_PORT", "11434"))
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5:32b-instruct-q6_K")
OLLAMA_URL: str = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}"

# OpenCode CLI — agent MJ principal
OPENCODE_BIN: str = os.getenv("OPENCODE_BIN", "opencode")
MJ_TIMEOUT: int = int(os.getenv("MJ_TIMEOUT", "600"))
NPC_TIMEOUT: int = int(os.getenv("NPC_TIMEOUT", "60"))

# Background tasks — intervals in minutes, 0 = disabled
WATCHDOG_INTERVAL: int = int(os.getenv("WATCHDOG_INTERVAL", "15"))
MAINTENANCE_INTERVAL: int = int(os.getenv("MAINTENANCE_INTERVAL", "60"))

# Access control — admin users only (comma-separated Discord user IDs)
ADMIN_USER_IDS: set[str] = set(
    uid.strip() for uid in os.getenv("ADMIN_USER_IDS", "").split(",") if uid.strip()
)


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def load_system_prompts() -> dict[str, str]:
    """
    Parse system_prompts.md — sections délimitées par des headers `# nom`.
    Retourne un dict {nom: contenu}.
    """
    content = _read(CONFIG_DIR / "system_prompts.md")
    result: dict[str, str] = {}
    current_key: str | None = None
    current_lines: list[str] = []

    for line in content.splitlines():
        if line.startswith("# ") and not line.startswith("## "):
            if current_key is not None:
                result[current_key] = "\n".join(current_lines).strip()
            current_key = line[2:].strip()
            current_lines = []
        elif current_key is not None:
            current_lines.append(line)

    if current_key is not None:
        result[current_key] = "\n".join(current_lines).strip()

    return result


def load_sanitizer_patterns() -> list[str]:
    """
    Parse sanitizer_patterns.md — lignes préfixées par `- `.
    """
    content = _read(CONFIG_DIR / "sanitizer_patterns.md")
    patterns: list[str] = []
    for line in content.splitlines():
        line = line.strip()
        if not line.startswith("- "):
            continue
        value = line[2:].strip().strip("`")
        if value:
            patterns.append(value)
    return patterns


def load_workflows() -> dict[str, dict]:
    """
    Scanne WORKFLOWS_DIR pour les fichiers *.json.
    Supporte les clés _augure (nouveau) et _stasia (héritage Stasia).
    Retourne un dict {nom_fichier_sans_extension: config + "file"}.
    """
    result: dict[str, dict] = {}
    if not WORKFLOWS_DIR.exists():
        return result

    for path in sorted(WORKFLOWS_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        # Support both _augure (new) and _stasia (legacy copied workflows)
        meta = data.get("_augure", data.get("_stasia", {}))
        result[path.stem] = {
            "file": path.name,
            "description": meta.get("description", ""),
            "media_type": meta.get("media_type", "image"),
            "parameters": meta.get("parameters", []),
            "output_node": str(meta.get("output_node", "9")),
        }

    return result


_CHANNEL_DEFAULTS: dict[str, str] = {
    "rp": "rp",
    "general": "général",
    "mj_screen": "mj-screen",
}


def load_bot_settings() -> dict:
    """
    Lit bot_settings.yml à chaque appel (le MJ peut modifier ce fichier à chaud).
    """
    try:
        data = yaml.safe_load((CONFIG_DIR / "bot_settings.yml").read_text(encoding="utf-8")) or {}
    except Exception:
        data = {}
    defaults: dict = {
        "emojis": {
            "queued": "⏳",
            "processing": "⚙️",
            "success": "",
            "error": "❌",
            "stop": "🛑",
            "sleep": "😴",
            "wake": "👋",
        }
    }
    return {
        "emojis": {**defaults["emojis"], **data.get("emojis", {})}
    }


def load_channels(guild_id: str | None = None) -> dict[str, str]:
    """
    Retourne les noms de channels pour un serveur donné.
    Lit channels.yml à chaque appel (le MJ peut modifier ce fichier à chaud).
    Fusionne : defaults → section "default" → section "guilds.<guild_id>".
    """
    try:
        data = yaml.safe_load((CONFIG_DIR / "channels.yml").read_text(encoding="utf-8")) or {}
    except Exception:
        data = {}

    result = {**_CHANNEL_DEFAULTS, **data.get("default", {})}
    if guild_id:
        result.update(data.get("guilds", {}).get(str(guild_id), {}))
    return result
