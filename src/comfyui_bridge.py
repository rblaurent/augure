"""
ComfyUI Bridge — génération d'images via l'API HTTP de ComfyUI.
Progress en temps réel via WebSocket (/ws).
"""

import asyncio
import copy
import io
import json
import logging
import random
import time
import uuid
from pathlib import Path

import aiohttp

from . import config

logger = logging.getLogger(__name__)

_POLL_TIMEOUT = 300.0  # timeout total génération (5 min)


class ComfyUIBridge:
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._ws_url = self._base_url.replace("http://", "ws://").replace("https://", "wss://")
        self._workflows = config.load_workflows()
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def check_health(self) -> bool:
        """Vérifie que ComfyUI est accessible."""
        try:
            session = await self._get_session()
            async with session.get(f"{self._base_url}/system_stats", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                return resp.status == 200
        except Exception:
            return False

    async def upload_image(self, url: str) -> str:
        """
        Télécharge une image depuis `url` et l'envoie à ComfyUI via /upload/image.
        Retourne le filename attribué par ComfyUI (ex. "generated.png").
        Lève une exception en cas d'échec.
        """
        session = await self._get_session()
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Image download failed: HTTP {resp.status} for {url}")
            image_bytes = await resp.read()
            content_type = resp.headers.get("Content-Type", "image/png")

        ext = "png"
        if "jpeg" in content_type or "jpg" in content_type:
            ext = "jpg"
        elif "webp" in content_type:
            ext = "webp"
        filename = f"upload.{ext}"

        form = aiohttp.FormData()
        form.add_field("image", image_bytes, filename=filename, content_type=content_type)
        form.add_field("overwrite", "true")

        async with session.post(
            f"{self._base_url}/upload/image",
            data=form,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            if resp.status != 200:
                body = await resp.text()
                raise RuntimeError(f"ComfyUI /upload/image error {resp.status}: {body[:200]}")
            data = await resp.json()
            return data["name"]

    async def generate(
        self,
        workflow_name: str,
        prompt: str,
        negative: str = "",
        seed: int | None = None,
        progress_cb=None,
        **extra_params,
    ) -> tuple[io.BytesIO, int] | tuple[None, None]:
        """
        Génère une image via ComfyUI.
        Retourne (image_bytes, seed_utilisé) ou (None, None) en cas d'erreur.
        progress_cb: async callable(stage: str, detail: str) optionnel.
        """
        wf_config = self._workflows.get(workflow_name)
        if not wf_config:
            logger.error("Workflow inconnu : %s", workflow_name)
            return None, None

        workflow_path = config.WORKFLOWS_DIR / Path(wf_config["file"]).name
        if not workflow_path.exists():
            logger.error("Fichier workflow introuvable : %s", workflow_path)
            return None, None

        with open(workflow_path, encoding="utf-8") as f:
            workflow_json: dict = json.load(f)

        workflow_json = copy.deepcopy(workflow_json)
        # Remove meta keys (support both _augure and legacy _stasia)
        workflow_json.pop("_augure", None)
        workflow_json.pop("_stasia", None)

        neg_default = next(
            (p.get("default", "") for p in wf_config.get("parameters", []) if p["name"] == "negative"),
            "",
        )

        actual_seed = seed if seed is not None else random.randint(0, 2**32 - 1)

        workflow_json = self._inject_params(
            workflow_json,
            wf_config.get("parameters", []),
            prompt=prompt,
            negative=negative if negative else neg_default,
            seed=actual_seed,
            **extra_params,
        )

        output_node = str(wf_config.get("output_node", "9"))
        client_id = str(uuid.uuid4())

        image_data = await self._run_with_ws(workflow_json, output_node, client_id, progress_cb)
        return (image_data, actual_seed) if image_data else (None, None)

    def _inject_params(self, workflow: dict, param_defs: list[dict], **kwargs) -> dict:
        """Injecte les paramètres dans les nœuds du workflow."""
        for param in param_defs:
            name = param["name"]
            node_id = str(param["node_id"])
            field = param["field"]
            value = kwargs.get(name, param.get("default"))

            if value == "random":
                value = random.randint(0, 2**32 - 1)

            if node_id in workflow and value is not None:
                workflow[node_id]["inputs"][field] = value

        return workflow

    async def _queue_prompt(self, workflow: dict, client_id: str) -> str | None:
        """Envoie le workflow à ComfyUI et retourne le prompt_id."""
        session = await self._get_session()
        payload = {"prompt": workflow, "client_id": client_id}
        try:
            async with session.post(
                f"{self._base_url}/prompt",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    logger.error("ComfyUI /prompt error %d: %s", resp.status, body[:200])
                    return None
                data = await resp.json()
                return data.get("prompt_id")
        except Exception as exc:
            logger.error("ComfyUI queue error: %s", exc)
            return None

    async def _run_with_ws(
        self,
        workflow: dict,
        output_node: str,
        client_id: str,
        progress_cb=None,
    ) -> io.BytesIO | None:
        """
        Ouvre un WebSocket, soumet le prompt, écoute les événements de progression,
        et télécharge l'image quand execution_success arrive.
        """
        ws_url = f"{self._ws_url}/ws?clientId={client_id}"
        session = await self._get_session()

        try:
            async with session.ws_connect(
                ws_url,
                timeout=aiohttp.ClientTimeout(total=10),
                heartbeat=30.0,
            ) as ws:
                prompt_id = await self._queue_prompt(workflow, client_id)
                if not prompt_id:
                    return None

                logger.info("ComfyUI prompt soumis : %s", prompt_id)

                total_nodes = max(len(workflow), 1)
                nodes_cached = 0
                non_cached_total = total_nodes
                executing_seen = 0
                current_node_frac = 0.0
                last_dot = 0

                def _global_frac() -> float:
                    nodes_finished = max(0, executing_seen - 1)
                    return min((nodes_finished + current_node_frac) / non_cached_total, 0.95)

                async def _fire_progress() -> None:
                    nonlocal last_dot
                    if not progress_cb:
                        return
                    frac = _global_frac()
                    dot = max(1, round(frac * 10))
                    if dot != last_dot:
                        last_dot = dot
                        try:
                            await progress_cb("generating", f"{frac:.4f}")
                        except Exception:
                            pass

                deadline = time.monotonic() + _POLL_TIMEOUT

                while time.monotonic() < deadline:
                    remaining = deadline - time.monotonic()
                    try:
                        msg = await asyncio.wait_for(ws.receive(), timeout=min(remaining, 60.0))
                    except asyncio.TimeoutError:
                        logger.error("ComfyUI WS timed out after %.0fs", _POLL_TIMEOUT)
                        return None

                    if msg.type == aiohttp.WSMsgType.TEXT:
                        try:
                            data = json.loads(msg.data)
                        except Exception:
                            continue

                        msg_type = data.get("type", "")
                        msg_data = data.get("data", {})

                        if msg_type == "execution_cached":
                            if msg_data.get("prompt_id") in (prompt_id, None, ""):
                                nodes_cached += len(msg_data.get("nodes", []))
                                non_cached_total = max(total_nodes - nodes_cached, 1)
                                await _fire_progress()

                        elif msg_type == "executing":
                            if msg_data.get("prompt_id") in (prompt_id, None, ""):
                                if msg_data.get("node") is not None:
                                    executing_seen += 1
                                    current_node_frac = 0.0
                                    await _fire_progress()

                        elif msg_type == "progress":
                            if msg_data.get("prompt_id") not in (prompt_id, None, ""):
                                continue
                            value = msg_data.get("value", 0)
                            maximum = msg_data.get("max", 1)
                            if maximum > 0:
                                current_node_frac = value / maximum
                            await _fire_progress()

                        elif msg_type == "execution_success":
                            if msg_data.get("prompt_id") == prompt_id:
                                logger.info("ComfyUI execution_success : %s", prompt_id)
                                return await self._fetch_output(prompt_id, output_node)

                        elif msg_type == "execution_error":
                            if msg_data.get("prompt_id") == prompt_id:
                                logger.error(
                                    "ComfyUI execution_error: %s",
                                    msg_data.get("exception_message", "unknown"),
                                )
                                return None

                    elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                        logger.error("ComfyUI WS closed/error: %s", msg.data)
                        break

        except Exception as exc:
            logger.error("ComfyUI WS connect error: %s", exc)

        return None

    async def _fetch_output(self, prompt_id: str, output_node: str) -> io.BytesIO | None:
        """Récupère l'image générée depuis /history/{prompt_id}."""
        session = await self._get_session()
        try:
            async with session.get(
                f"{self._base_url}/history/{prompt_id}",
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status != 200:
                    logger.error("ComfyUI /history error %d", resp.status)
                    return None
                history = await resp.json()

                entry = history.get(prompt_id, {})
                outputs = entry.get("outputs", {})
                if output_node not in outputs:
                    logger.error("ComfyUI output node %s not found in history", output_node)
                    return None

                media_list = outputs[output_node].get("images") or outputs[output_node].get("gifs", [])
                if not media_list:
                    return None

                img_info = media_list[0]
                return await self._download_image(
                    filename=img_info["filename"],
                    subfolder=img_info.get("subfolder", ""),
                    img_type=img_info.get("type", "output"),
                )
        except Exception as exc:
            logger.error("ComfyUI fetch output error: %s", exc)
            return None

    async def _download_image(self, filename: str, subfolder: str, img_type: str) -> io.BytesIO | None:
        session = await self._get_session()
        params = {"filename": filename, "subfolder": subfolder, "type": img_type}
        try:
            async with session.get(
                f"{self._base_url}/view",
                params=params,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.read()
                return io.BytesIO(data)
        except Exception as exc:
            logger.error("Image download error: %s", exc)
            return None
