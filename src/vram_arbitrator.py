"""
VRAM Arbitrator — verrou exclusif entre le LLM (Ollama) et ComfyUI.

État par défaut : LLM chargé en VRAM.
Avant chaque job ComfyUI : décharge le LLM, attend, exécute, relâche.
Le prochain appel LLM rechargera le modèle automatiquement (~5-10s).
"""

import asyncio
import logging

import aiohttp

from . import config

logger = logging.getLogger(__name__)

# Singleton global
_instance: "VRAMArbitrator | None" = None


def get_vram_arbitrator() -> "VRAMArbitrator":
    global _instance
    if _instance is None:
        _instance = VRAMArbitrator()
    return _instance


class VRAMArbitrator:
    """
    Lock asyncio exclusif entre LLM et ComfyUI.
    Un seul acquéreur à la fois sur le GPU.
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def acquire_for_llm(self) -> None:
        """Acquiert le lock pour un appel LLM. Attend si ComfyUI tourne."""
        await self._lock.acquire()
        logger.debug("VRAM lock acquis (LLM)")

    async def acquire_for_comfyui(self) -> None:
        """Acquiert le lock pour ComfyUI. Décharge le LLM avant de procéder."""
        await self._lock.acquire()
        logger.debug("VRAM lock acquis (ComfyUI) — déchargement LLM")
        await self._unload_llm()

    def release(self) -> None:
        """Relâche le lock VRAM."""
        try:
            self._lock.release()
            logger.debug("VRAM lock relâché")
        except RuntimeError:
            logger.warning("Tentative de relâcher un lock VRAM non acquis")

    async def _unload_llm(self) -> None:
        """
        Demande à Ollama de décharger le modèle (keep_alive=0).
        Le modèle sera rechargé automatiquement au prochain appel.
        """
        session = await self._get_session()
        payload = {
            "model": config.OLLAMA_MODEL,
            "keep_alive": 0,
        }
        try:
            async with session.post(
                f"{config.OLLAMA_URL}/api/generate",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status == 200:
                    logger.info("LLM déchargé de la VRAM")
                else:
                    body = await resp.text()
                    logger.warning("Ollama unload error %d: %s", resp.status, body[:200])
        except Exception as exc:
            logger.warning("Échec déchargement LLM : %s", exc)

    def is_locked(self) -> bool:
        return self._lock.locked()


class VRAMLLMContext:
    """Context manager pour les appels LLM."""

    def __init__(self, arbitrator: VRAMArbitrator) -> None:
        self._arb = arbitrator

    async def __aenter__(self):
        await self._arb.acquire_for_llm()
        return self

    async def __aexit__(self, *_):
        self._arb.release()


class VRAMComfyUIContext:
    """Context manager pour les jobs ComfyUI."""

    def __init__(self, arbitrator: VRAMArbitrator) -> None:
        self._arb = arbitrator

    async def __aenter__(self):
        await self._arb.acquire_for_comfyui()
        return self

    async def __aexit__(self, *_):
        self._arb.release()
