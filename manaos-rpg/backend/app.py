"""ManaOS RPG API – slim entrypoint.

All endpoint logic lives under routers/ ; shared helpers under core/ and services/.
Start with:  uvicorn app:app --host 0.0.0.0 --port 9510
"""

from __future__ import annotations

import os
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware

from core.config import _CORS_ORIGINS
from routers import (
    actions,
    generate,
    items,
    lessons,
    ollama,
    registry,
    revenue,
    rl_anything,
    snapshot,
    unified_passthrough,
    unified_proxy,
)


def _prewarm_snapshot() -> None:
    """バックエンド起動直後にスナップショットをバックグラウンドでプリウォーム。
    初回アクセスで 15+ 秒待たされるのを防ぐ。"""
    try:
        from routers.snapshot import _snapshot_cached
        _snapshot_cached(force_refresh=True)
    except Exception:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 起動時: バックグラウンドスレッドでスナップショットをプリウォーム
    t = threading.Thread(target=_prewarm_snapshot, daemon=True, name="snapshot-prewarm")
    t.start()
    yield
    # シャットダウン時: 特になし

app = FastAPI(title="ManaOS RPG API", version="0.1", lifespan=lifespan)

_CORS_ORIGIN_REGEX = os.getenv(
    "MANAOS_CORS_ORIGIN_REGEX",
    r"^https?://(localhost|127\.0\.0\.1|100(?:\.\d{1,3}){3}|10(?:\.\d{1,3}){3}|192\.168(?:\.\d{1,3}){2}|172\.(?:1[6-9]|2\d|3[0-1])(?:\.\d{1,3}){2})(?::\d+)?$",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_origin_regex=_CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1024)

for _r in (
    snapshot,
    registry,
    unified_proxy,
    unified_passthrough,
    actions,
    ollama,
    generate,
    items,
    rl_anything,
    revenue,
    lessons,
):
    app.include_router(_r.router)

