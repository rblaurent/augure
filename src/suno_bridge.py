"""
Suno Bridge — génération de musique via l'API Suno (sunoapi.org).
Miroir de comfyui_bridge.py : session aiohttp, poll jusqu'à completion, download.

API réelle (validée) :
  POST /api/v1/generate          → retourne taskId
  GET  /api/v1/generate/record-info?taskId=...  → poll statut
  Statuts : PENDING → TEXT_SUCCESS → SUCCESS / FAILED
"""

import asyncio
import dataclasses
import io
import logging
import re

import aiohttp

from . import config

logger = logging.getLogger(__name__)

_POLL_INTERVAL = 5.0    # secondes entre chaque poll
_POLL_TIMEOUT = 300.0   # timeout total (5 min — Suno prend ~1-2 min)

# URL placeholder pour callBackUrl (obligatoire, mais on utilise le polling)
_CALLBACK_PLACEHOLDER = "https://example.com"

# Statuts terminaux
_STATUS_DONE = {"SUCCESS"}
_STATUS_FAILED = {"FAILED"}


def _slugify(text: str) -> str:
    """Convertit un titre en nom de fichier sûr."""
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")[:50] or "musique"


@dataclasses.dataclass
class SongResult:
    clip_id: str
    title: str
    tags: str
    audio_url: str
    image_url: str
    audio_data: io.BytesIO
    filename: str


class SunoBridge:
    def __init__(self, api_key: str, base_url: str) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._session: aiohttp.ClientSession | None = None
        self._semaphore = asyncio.Semaphore(1)  # 1 génération à la fois

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={"Authorization": f"Bearer {self._api_key}"}
            )
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def generate(
        self,
        prompt: str,
        style: str = "",
        title: str = "",
        make_instrumental: bool = False,
        progress_cb=None,
    ) -> list[SongResult] | None:
        """
        Génère de la musique via Suno.
        Retourne une liste de SongResult (2 clips), ou None en cas d'erreur.
        progress_cb: async callable(stage: str, detail: str) optionnel.
        """
        if not self._api_key:
            logger.error("SUNO_API_KEY non configurée")
            return None

        async with self._semaphore:
            task_id = await self._submit(prompt, style, title, make_instrumental)
            if not task_id:
                return None

            if progress_cb:
                try:
                    await progress_cb("submitted", "")
                except Exception:
                    pass

            clips = await self._poll_until_done(task_id, progress_cb)
            if not clips:
                return None

            results = []
            for clip in clips:
                audio_url = clip.get("audioUrl", "")
                if not audio_url:
                    logger.warning("Clip %s sans audioUrl", clip.get("id"))
                    continue

                clip_title = clip.get("title") or title or "Untitled"
                clip_tags = clip.get("tags", style)
                clip_id = clip.get("id", "")
                image_url = clip.get("imageUrl", "")

                audio_data = await self._download_audio(audio_url)
                if not audio_data:
                    logger.warning("Échec téléchargement audio pour clip %s", clip_id)
                    continue

                slug = _slugify(clip_title)
                filename = f"{slug}-{clip_id[:8]}.mp3"

                results.append(SongResult(
                    clip_id=clip_id,
                    title=clip_title,
                    tags=clip_tags,
                    audio_url=audio_url,
                    image_url=image_url,
                    audio_data=audio_data,
                    filename=filename,
                ))

            return results if results else None

    async def _submit(
        self,
        prompt: str,
        style: str,
        title: str,
        make_instrumental: bool,
    ) -> str | None:
        """Soumet la demande de génération, retourne le taskId."""
        session = await self._get_session()
        payload = {
            "customMode": True,
            "model": "V4_5",
            "prompt": prompt,
            "style": style,
            "title": title,
            "instrumental": make_instrumental,
            "callBackUrl": _CALLBACK_PLACEHOLDER,
        }
        try:
            async with session.post(
                f"{self._base_url}/api/v1/generate",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    logger.error("Suno /api/v1/generate error %d: %s", resp.status, body[:300])
                    return None
                data = await resp.json()
                if data.get("code") != 200:
                    logger.error("Suno error: %s", data.get("msg", "unknown"))
                    return None
                task_id = data.get("data", {}).get("taskId")
                if not task_id:
                    logger.error("Suno response sans taskId: %s", str(data)[:200])
                    return None
                logger.info("Suno task soumis : %s", task_id)
                return task_id
        except Exception as exc:
            logger.error("Suno submit error: %s", exc)
            return None

    async def _poll_until_done(self, task_id: str, progress_cb=None) -> list[dict] | None:
        """Poll jusqu'à SUCCESS ou FAILED, retourne la liste sunoData."""
        session = await self._get_session()
        elapsed = 0.0
        _seen_text_success = False
        _seen_composing = False

        while elapsed < _POLL_TIMEOUT:
            await asyncio.sleep(_POLL_INTERVAL)
            elapsed += _POLL_INTERVAL

            try:
                async with session.get(
                    f"{self._base_url}/api/v1/generate/record-info",
                    params={"taskId": task_id},
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status != 200:
                        logger.warning("Suno poll HTTP %d", resp.status)
                        continue

                    body = await resp.json()
                    if body.get("code") != 200:
                        logger.warning("Suno poll error code: %s", body.get("msg"))
                        continue

                    task_data = body.get("data", {})
                    status = task_data.get("status", "")

                    if status in _STATUS_FAILED:
                        logger.error("Suno task échoué: %s", task_data.get("errorMessage"))
                        return None

                    if status in _STATUS_DONE:
                        suno_data = task_data.get("response", {}).get("sunoData", [])
                        if suno_data:
                            logger.info("Suno task SUCCESS : %d clips", len(suno_data))
                            return suno_data
                        logger.error("Suno SUCCESS mais sunoData vide")
                        return None

                    if progress_cb:
                        if status == "TEXT_SUCCESS" and not _seen_text_success:
                            _seen_text_success = True
                            try:
                                await progress_cb("writing_lyrics", "")
                            except Exception:
                                pass
                        elif _seen_text_success and status != "TEXT_SUCCESS" and not _seen_composing:
                            _seen_composing = True
                            try:
                                await progress_cb("composing_audio", "")
                            except Exception:
                                pass

                    logger.debug("Suno poll status=%s (%.0fs)", status, elapsed)

            except Exception as exc:
                logger.warning("Suno poll exception: %s", exc)

        logger.error("Suno generation timed out after %.0fs", _POLL_TIMEOUT)
        return None

    async def _download_audio(self, url: str) -> io.BytesIO | None:
        """Télécharge le fichier audio depuis l'URL Suno."""
        session = await self._get_session()
        try:
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=60),
            ) as resp:
                if resp.status != 200:
                    logger.error("Audio download failed: HTTP %d", resp.status)
                    return None
                data = await resp.read()
                return io.BytesIO(data)
        except Exception as exc:
            logger.error("Audio download error: %s", exc)
            return None
