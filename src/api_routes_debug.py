"""
Debug routes — validate mj-screen plumbing and fake stream mode.

POST /debug/mj-screen        — fire a test sequence of all embed types
POST /debug/fake-stream/on   — enable fake stream mode (any message → fake events)
POST /debug/fake-stream/off  — disable fake stream mode
"""

import asyncio
import logging

from aiohttp import web

from .api_context import ApiContext, json_response
from . import opencode_bridge

logger = logging.getLogger(__name__)

# Fake stream: a sequence of events that exercises all embed types
_FAKE_EVENTS = [
    {"type": "step_start", "part": {"type": "step-start"}},
    {"type": "text", "part": {"type": "text", "text": "Je réfléchis à ta demande... voici mon raisonnement initial."}},
    {"type": "text", "part": {"type": "text", "text": " J'ai besoin de consulter quelques fichiers."}},
    {"type": "tool_use", "part": {"type": "tool-use", "tool": "Read", "input": {"file_path": "/workspace/config/identity.md"}}},
    {"type": "tool_result", "part": {"type": "tool-result", "tool": "Read", "output": "# Identité\nJe suis Augure, Maître du Jeu omniscient et légèrement sardonique.", "error": ""}},
    {"type": "tool_use", "part": {"type": "tool-use", "tool": "Bash", "input": {"command": "curl -s http://127.0.0.1:8765/guilds"}}},
    {"type": "tool_result", "part": {"type": "tool-result", "tool": "Bash", "output": '[{"id":"1234","name":"Augure","channels":[]}]', "error": ""}},
    {"type": "text", "part": {"type": "text", "text": "Voilà ma réponse finale, après avoir consulté les fichiers et l'API."}},
    {"type": "step_finish", "part": {"type": "step-finish", "reason": "stop", "cost": 0, "tokens": {"total": 42, "input": 40, "output": 2}}},
]


def register(app: web.Application, ctx: ApiContext) -> None:

    async def post_debug_mj_screen(request):
        """Fire a test sequence of all embed types into #mj-screen."""
        body = await request.json()
        guild_id = body.get("guild_id", "")
        if not guild_id:
            # Auto-detect first guild
            for g in ctx.client.guilds:
                guild_id = str(g.id)
                break
        if not guild_id:
            return json_response({"ok": False, "error": "no guild found"}, status=400)

        for event in _FAKE_EVENTS:
            await ctx.mj_screen.handle_stream_event(event, guild_id)
            await asyncio.sleep(0.3)

        return json_response({"ok": True, "events_sent": len(_FAKE_EVENTS)})

    async def post_fake_stream_on(request):
        opencode_bridge.set_fake_stream(True)
        logger.info("Fake stream mode ENABLED")
        return json_response({"ok": True, "fake_stream": True})

    async def post_fake_stream_off(request):
        opencode_bridge.set_fake_stream(False)
        logger.info("Fake stream mode DISABLED")
        return json_response({"ok": True, "fake_stream": False})

    app.router.add_post("/debug/mj-screen", post_debug_mj_screen)
    app.router.add_post("/debug/fake-stream/on", post_fake_stream_on)
    app.router.add_post("/debug/fake-stream/off", post_fake_stream_off)
