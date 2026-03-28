"""
OpenCode Bridge — exécute OpenCode en mode one-shot via subprocess.
Remplace claude_bridge.py de Stasia.

Même pattern que Stasia :
- File d'attente par utilisateur (asyncio.Queue)
- Lock VRAM global (remplace le lock Claude)
- Construction du prompt avec contexte Discord
- Parsing du stream JSON (format identique à Claude CLI)
- Logging des invocations dans /workspace/memory/meta/invocation_logs/

Stream vers #mj-screen en temps réel via MJScreen.

NOTE : les flags CLI exacts d'OpenCode sont à vérifier contre la doc ACP.
L'implémentation utilise le même pattern que Claude CLI (--print, --output-format stream-json).
"""

import asyncio
import datetime
import json
import logging
import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from . import config
from .vram_arbitrator import VRAMArbitrator

if TYPE_CHECKING:
    from .mj_screen import MJScreen

logger = logging.getLogger(__name__)

_FALLBACK_TEXT = "Une erreur est survenue. Réessaie."
_LOG_DIR = config.MEMORY_DIR / "meta" / "invocation_logs"


def _extract_result(stdout: str) -> str:
    """Extract the final text response from stream-json output."""
    last_assistant_text = ""
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        t = event.get("type")
        if t == "result":
            return event.get("result", "") or last_assistant_text or _FALLBACK_TEXT
        if t == "assistant":
            for block in event.get("message", {}).get("content", []):
                if block.get("type") == "text" and block.get("text"):
                    last_assistant_text = block["text"]
    return last_assistant_text or _FALLBACK_TEXT


def _write_invocation_log(log_path, prompt: str, stdout: str) -> None:
    """Write full invocation transcript to a .jsonl file."""
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"type": "prompt", "content": prompt}, ensure_ascii=False) + "\n")
            for line in stdout.splitlines():
                if line.strip():
                    f.write(line + "\n")
    except Exception as exc:
        logger.warning("Failed to write invocation log %s: %s", log_path, exc)


def is_mj_busy(vram: VRAMArbitrator) -> bool:
    """Return True if a MJ subprocess is currently running."""
    return vram.is_locked()


@dataclass
class MJRequest:
    user_message: str
    context: dict
    user_id: str
    guild_id: str
    is_rp: bool = False  # True = message dans #rp, False = mention/DM
    future: asyncio.Future = field(init=False)
    started: asyncio.Event = field(init=False)

    def __post_init__(self) -> None:
        loop = asyncio.get_running_loop()
        self.future = loop.create_future()
        self.started = asyncio.Event()


class OpenCodeQueue:
    """
    File d'attente par utilisateur (ou par guild pour les messages #rp).
    Même architecture que ClaudeQueue de Stasia, avec lock VRAM.
    """

    def __init__(self, vram: VRAMArbitrator, mj_screen: "MJScreen") -> None:
        self._vram = vram
        self._mj_screen = mj_screen
        self._queues: dict[str, asyncio.Queue[MJRequest]] = {}
        self._workers: dict[str, asyncio.Task] = {}
        self._system_prompts = config.load_system_prompts()

    def start(self) -> None:
        pass  # Workers créés à la demande

    def stop(self) -> None:
        for task in self._workers.values():
            task.cancel()
        self._workers.clear()
        self._queues.clear()

    def enqueue(self, user_message: str, context: dict, user_id: str, guild_id: str, is_rp: bool = False) -> MJRequest:
        """Queue a request. Pour les messages #rp, la clé est guild_id:rp pour une queue FIFO par guild."""
        queue_key = f"{guild_id}:rp" if is_rp else user_id
        if queue_key not in self._queues:
            self._queues[queue_key] = asyncio.Queue()
        worker = self._workers.get(queue_key)
        if worker is None or worker.done():
            self._workers[queue_key] = asyncio.create_task(self._worker(queue_key))
        req = MJRequest(
            user_message=user_message,
            context=context,
            user_id=user_id,
            guild_id=guild_id,
            is_rp=is_rp,
        )
        self._queues[queue_key].put_nowait(req)
        return req

    async def _worker(self, queue_key: str) -> None:
        """Traite les requêtes d'une queue une par une. S'arrête après 10min d'inactivité."""
        queue = self._queues[queue_key]
        while True:
            try:
                req: MJRequest = await asyncio.wait_for(queue.get(), timeout=600)
            except asyncio.TimeoutError:
                self._queues.pop(queue_key, None)
                self._workers.pop(queue_key, None)
                return
            try:
                async with _VRAMLLMContext(self._vram):
                    req.started.set()
                    result = await self._run_opencode_async(req)
                if not req.future.done():
                    req.future.set_result(result)
            except (TimeoutError, asyncio.TimeoutError):
                logger.error("OpenCode timed out after %ds", config.MJ_TIMEOUT)
                if not req.future.done():
                    req.future.set_result("❌ Délai dépassé — le MJ a mis trop longtemps.")
            except Exception as exc:
                logger.error("MJ request failed: %s", exc, exc_info=True)
                if not req.future.done():
                    req.future.set_result(f"❌ Erreur inattendue : {exc}")
            finally:
                queue.task_done()

    def _build_prompt(self, req: MJRequest) -> str:
        """
        Construit le prompt envoyé au MJ.
        Contexte Discord minimal — le MJ lit le reste via ses outils et la mémoire.
        """
        if req.is_rp:
            system = self._system_prompts.get("user_request", "")
        else:
            system = self._system_prompts.get("general_request",
                      self._system_prompts.get("user_request", ""))
        ctx = req.context
        lines: list[str] = [system, ""]

        lines.append("## Contexte")
        lines.append(f"- User ID : {req.user_id}")
        lines.append(f"- Type : {'message RP' if req.is_rp else ('DM' if ctx.get('is_dm') else 'mention serveur')}")
        lines.append(f"- Message ID : {ctx.get('message_id', '?')}")
        lines.append(f"- Channel ID : {ctx.get('channel_id', '?')}")
        if ctx.get("guild_name"):
            lines.append(f"- Serveur : {ctx['guild_name']} (id={ctx.get('guild_id', '?')})")
        if ctx.get("channel_name"):
            lines.append(f"- Channel : #{ctx['channel_name']}")
        lines.append("")

        if ctx.get("recent_history"):
            lines.append("## Historique récent #rp" if req.is_rp else "## Historique récent")
            for msg in ctx["recent_history"]:
                msg_id = msg.get("id", "")
                id_hint = f" (id={msg_id})" if msg_id else ""
                lines.append(f"[{msg.get('author', '?')}]{id_hint}: {msg.get('content', '')}")
            lines.append("")

        lines.append("## Message du joueur")
        lines.append(req.user_message)
        lines.append("")

        if req.is_rp:
            lines.append("Le joueur vient de poster en #rp. Orchestre la scène : narre, invoque les PNJ si pertinent, mets à jour la mémoire.")
        else:
            lines.append("Le joueur t'interpelle directement. Réponds naturellement en texte libre.")

        return "\n".join(lines)

    async def _run_opencode_async(self, req: MJRequest) -> str:
        """
        Lance OpenCode en subprocess asyncio pour le streaming temps réel.
        Parse le stream JSON ligne par ligne et poste dans #mj-screen.
        """
        prompt = self._build_prompt(req)

        # opencode run "message" --format json --dir /workspace -m ollama/model
        cmd = [
            config.OPENCODE_BIN,
            "run",
            "--format", "json",
            "--dir", str(config.WORKSPACE),
            "-m", f"ollama/{config.OLLAMA_MODEL}",
            prompt,  # message en argument positionnel
        ]

        env = {**os.environ, "HOME": "/home/botuser"}

        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_kind = "rp" if req.is_rp else "general"
        log_path = _LOG_DIR / f"{ts}_{log_kind}_{req.user_id}.jsonl"

        stdout_lines: list[str] = []

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(config.WORKSPACE),
                env=env,
            )

            # Lire stdout ligne par ligne en temps réel
            async def _read_stdout():
                assert proc.stdout
                async for raw_line in proc.stdout:
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if not line:
                        continue
                    stdout_lines.append(line)
                    # Parser et poster dans #mj-screen
                    try:
                        event = json.loads(line)
                        await self._mj_screen.handle_stream_event(event, req.guild_id)
                    except (json.JSONDecodeError, Exception):
                        pass

            # Lire stderr (silencieux sauf erreurs)
            async def _read_stderr():
                assert proc.stderr
                stderr_data = await proc.stderr.read()
                if stderr_data.strip():
                    logger.debug("OpenCode stderr: %s", stderr_data.decode()[:500])

            # Timeout global
            try:
                await asyncio.wait_for(
                    asyncio.gather(_read_stdout(), _read_stderr()),
                    timeout=config.MJ_TIMEOUT,
                )
            except asyncio.TimeoutError:
                proc.kill()
                logger.error("OpenCode timed out after %ds", config.MJ_TIMEOUT)
                raise

            await proc.wait()

        except FileNotFoundError:
            logger.error("OpenCode binary not found: %s", config.OPENCODE_BIN)
            return "OpenCode introuvable. Vérifie que le binaire est installé."
        except asyncio.TimeoutError:
            raise
        except Exception as exc:
            logger.error("OpenCode subprocess error: %s", exc, exc_info=True)
            return f"❌ Erreur subprocess : {exc}"

        # Écrire le log d'invocation
        stdout_text = "\n".join(stdout_lines)
        _write_invocation_log(log_path, prompt, stdout_text)

        return _extract_result(stdout_text)


class _VRAMLLMContext:
    """Context manager interne pour le lock VRAM LLM."""
    def __init__(self, vram: VRAMArbitrator) -> None:
        self._vram = vram

    async def __aenter__(self):
        await self._vram.acquire_for_llm()
        return self

    async def __aexit__(self, *_):
        self._vram.release()


class OpenCodeWatchdogRunner:
    """Lance le watchdog/préparation du MJ entre les sessions."""

    def __init__(self, vram: VRAMArbitrator, mj_screen: "MJScreen") -> None:
        self._vram = vram
        self._mj_screen = mj_screen
        self._system_prompts = config.load_system_prompts()

    async def run(self, guild_id: str, guild_name: str, channels_data: list[dict]) -> None:
        if self._vram.is_locked():
            logger.info("Watchdog skipped — MJ already busy")
            return
        prompt = self._build_prompt(guild_id, guild_name, channels_data)
        async with _VRAMLLMContext(self._vram):
            await self._call_opencode(prompt, guild_id)

    def _build_prompt(self, guild_id: str, guild_name: str, channels_data: list[dict]) -> str:
        system = self._system_prompts.get("watchdog", "")
        lines = [system, "", "## Contexte"]
        lines.append(f"- Serveur : {guild_name} (guild_id={guild_id})")
        lines.append("")
        lines.append("## Activité récente par channel")
        for ch in channels_data:
            lines.append(f"\n### #{ch['channel_name']} (channel_id={ch['channel_id']})")
            for msg in ch["messages"]:
                lines.append(f"[{msg['author']}] (id={msg['id']}) {msg['content']}")
            for r in ch.get("reactions", []):
                lines.append(
                    f"[RÉACTION] user_id={r['user_id']} a réagi {r['emoji']} "
                    f"sur le message id={r['message_id']}"
                )
        return "\n".join(lines)

    async def _call_opencode(self, prompt: str, guild_id: str) -> None:
        cmd = [
            config.OPENCODE_BIN,
            "run",
            "--format", "json",
            "--dir", str(config.WORKSPACE),
            "-m", f"ollama/{config.OLLAMA_MODEL}",
            prompt,
        ]
        env = {**os.environ, "HOME": "/home/botuser"}
        stdout_lines: list[str] = []
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(config.WORKSPACE),
                env=env,
            )

            async def _read_stdout():
                assert proc.stdout
                async for raw_line in proc.stdout:
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if not line:
                        continue
                    stdout_lines.append(line)
                    try:
                        event = json.loads(line)
                        await self._mj_screen.handle_stream_event(event, guild_id)
                    except Exception:
                        pass

            async def _read_stderr():
                assert proc.stderr
                await proc.stderr.read()

            await asyncio.wait_for(
                asyncio.gather(_read_stdout(), _read_stderr()),
                timeout=config.MJ_TIMEOUT,
            )
            await proc.wait()
        except asyncio.TimeoutError:
            logger.error("Watchdog OpenCode timed out")
        except Exception as exc:
            logger.error("Watchdog failed: %s", exc)
        finally:
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            stdout_text = "\n".join(stdout_lines)
            _write_invocation_log(_LOG_DIR / f"{ts}_watchdog.jsonl", prompt, stdout_text)
