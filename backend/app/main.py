"""Morph AI — FastAPI orchestrator."""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import CORS_ORIGINS
from .config_loader import load_config
from .database import init_db
from .mcp_client import bridge
from .routes import (
    chat_route, graph_route, health_route, init_route,
    navigate_route, stream_route,
)

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s — %(message)s")
log = logging.getLogger("morph")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    cfg = load_config()
    log.info("connecting to %d MCP server(s)…", len(cfg.mcp_servers))
    await bridge.connect_all(cfg.mcp_servers)
    for name, status in bridge.server_status.items():
        log.info("MCP[%s] = %s", name, status)
    log.info("tool registry size = %d", len(bridge.list_tools()))
    yield
    await bridge.close()


app = FastAPI(title="Morph AI", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_route.router, prefix="/api")
app.include_router(init_route.router, prefix="/api")
app.include_router(navigate_route.router, prefix="/api")
app.include_router(stream_route.router, prefix="/api")
app.include_router(graph_route.router, prefix="/api")
app.include_router(chat_route.router, prefix="/api")


# ─── Static frontend ───────────────────────────────────────────────────
# When the frontend has been built (`vite build` -> `frontend/dist`), mount
# it so the same FastAPI process serves both API + UI on a single port.
STATIC_DIR = Path(os.getenv(
    "STATIC_DIR",
    str(Path(__file__).resolve().parents[2] / "frontend" / "dist"),
))

if STATIC_DIR.exists():
    # Serve hashed asset bundles
    if (STATIC_DIR / "assets").exists():
        app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    # SPA fallback — anything that isn't /api or /assets returns index.html
    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str) -> FileResponse:
        candidate = STATIC_DIR / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(STATIC_DIR / "index.html")
else:
    @app.get("/")
    async def root() -> dict:
        return {"name": "morph-ai", "version": "0.1.0",
                "note": "frontend not built; run `npm run build` in frontend/"}
