import re

from . import config

# Patterns de base pour protéger l'identité de l'hôte
_BASE_PATTERNS: list[str] = [
    r"[A-Z]:\\[^\s]*",             # Windows paths (C:\Users\...)
    r"/home/\w+/[^\s]*",           # Linux home paths
    r"/Users/\w+/[^\s]*",          # Mac paths
    r"\\\\[\w.]+\\[^\s]*",         # UNC paths
    r"(?i)hostname\s*[:=]\s*\S+",  # Hostname leaks
    r"(?i)username\s*[:=]\s*\S+",  # Username leaks
]


class OutputSanitizer:
    def __init__(self) -> None:
        self._compiled: list[re.Pattern] = []
        self._load_patterns()

    def _load_patterns(self) -> None:
        custom = config.load_sanitizer_patterns()
        all_patterns = _BASE_PATTERNS + custom
        self._compiled = [re.compile(p) for p in all_patterns]

    def reload(self) -> None:
        """Recharge les patterns depuis la config (utile si le fichier change)."""
        self._load_patterns()

    def sanitize(self, text: str) -> str:
        """Supprime les informations sensibles du texte."""
        for pattern in self._compiled:
            text = pattern.sub("[REDACTED]", text)
        return text

    def sanitize_response(self, response: dict) -> dict:
        """Sanitize tous les champs texte d'une réponse structurée."""
        text_fields = ("text", "image_prompt", "image_negative")
        return {
            k: self.sanitize(v) if k in text_fields and isinstance(v, str) else v
            for k, v in response.items()
        }
