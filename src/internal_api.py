"""
Internal HTTP API — exposée uniquement sur localhost:8765 à l'intérieur du container.
Permet au MJ (via WebFetch/Bash curl) d'interagir avec Discord pendant son raisonnement.

Routes enregistrées par sous-modules :
  api_routes_messages   — historique, send, delete, edit
  api_routes_webhooks   — webhook CRUD, réactions, création de channel
  api_routes_generation — génération image (ComfyUI) et musique (Suno)
  api_routes_npc        — invocation PNJ (Ollama), liste PNJ, MJ-screen
"""

from aiohttp import web

from .api_context import ApiContext
from . import api_routes_messages, api_routes_webhooks, api_routes_generation, api_routes_npc

PORT = 8765

_ctx: ApiContext | None = None


def init(client, webhooks, memory, comfy, suno, mj_screen, npc_invoker) -> None:
    global _ctx
    _ctx = ApiContext(
        client=client,
        webhooks=webhooks,
        memory=memory,
        comfy=comfy,
        suno=suno,
        mj_screen=mj_screen,
        npc_invoker=npc_invoker,
    )


def create_app() -> web.Application:
    app = web.Application()
    api_routes_messages.register(app, _ctx)
    api_routes_webhooks.register(app, _ctx)
    api_routes_generation.register(app, _ctx)
    api_routes_npc.register(app, _ctx)
    return app


async def start(client, webhooks, memory, comfy, suno, mj_screen, npc_invoker) -> None:
    init(client, webhooks, memory, comfy, suno, mj_screen, npc_invoker)
    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", PORT)
    await site.start()
