"""
NPC Invoker — appelle Ollama directement pour les sub-agents PNJ.

Les sub-agents PNJ n'utilisent pas OpenCode. Ils font un appel LLM pur
(prompt in → texte out) sans outils, sans accès fichiers.
C'est plus rapide et plus sûr que de passer par OpenCode.
"""

import logging

import aiohttp

from . import config
from .vram_arbitrator import VRAMArbitrator

logger = logging.getLogger(__name__)


class NPCInvoker:
    def __init__(self, vram: VRAMArbitrator) -> None:
        self._vram = vram
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def invoke(
        self,
        brief: str,
        max_tokens: int = 500,
    ) -> str:
        """
        Envoie le brief au LLM Ollama et retourne la réponse brute du PNJ.
        Acquiert le lock VRAM le temps de l'appel.
        """
        await self._vram.acquire_for_llm()
        try:
            return await self._call_ollama(brief, max_tokens)
        finally:
            self._vram.release()

    async def _call_ollama(self, prompt: str, max_tokens: int) -> str:
        session = await self._get_session()
        payload = {
            "model": config.OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": 0.8,
            },
        }
        try:
            async with session.post(
                f"{config.OLLAMA_URL}/api/generate",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=config.NPC_TIMEOUT),
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    logger.error("Ollama NPC error %d: %s", resp.status, body[:300])
                    return "(Le PNJ ne répond pas.)"
                data = await resp.json()
                return data.get("response", "").strip() or "(Le PNJ ne répond pas.)"
        except aiohttp.ClientError as exc:
            logger.error("Ollama NPC connection error: %s", exc)
            return "(Erreur de connexion au LLM.)"
        except Exception as exc:
            logger.error("Ollama NPC unexpected error: %s", exc)
            return "(Erreur inattendue lors de l'invocation PNJ.)"
