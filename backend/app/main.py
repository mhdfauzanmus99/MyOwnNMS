"""FastAPI application entry point.

Mounts all routers, wires startup/shutdown (DB schema, admin user, scheduler,
main event loop for the SSE bridge), and serves the built SPA in production.
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import auth, database, events, scheduler
from .routes import alerts as alerts_routes
from .routes import auth as auth_routes
from .routes import dashboard as dashboard_routes
from .routes import devices as devices_routes
from .routes import events as events_routes
from .routes import metrics as metrics_routes

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("nms")

# Built frontend bundle (production). Absent during dev (served by Vite instead).
FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_schema()
    auth.ensure_admin_user()
    events.set_main_loop(asyncio.get_running_loop())
    scheduler.start()
    logger.info("NetPulse backend ready on http://%s:%d", "127.0.0.1", 8000)
    try:
        yield
    finally:
        scheduler.stop()


app = FastAPI(title="NetPulse NMS", version="0.1.0", lifespan=lifespan)

# Allow the Vite dev server origin to carry cookies for the proxied calls.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router)
app.include_router(devices_routes.router)
app.include_router(metrics_routes.router)
app.include_router(alerts_routes.router)
app.include_router(dashboard_routes.router)
app.include_router(events_routes.router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


# --- Production SPA serving -------------------------------------------------
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        # Don't shadow API routes (they're already mounted above FastAPI checks those first).
        index = FRONTEND_DIST / "index.html"
        return FileResponse(index)
