"""ManaOS RPG API – slim entrypoint.

All endpoint logic lives under routers/ ; shared helpers under core/ and services/.
Start with:  uvicorn app:app --host 0.0.0.0 --port 9510
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import _CORS_ORIGINS
from routers import (
    actions,
    generate,
    items,
    ollama,
    registry,
    revenue,
    rl_anything,
    snapshot,
    unified_passthrough,
    unified_proxy,
)

app = FastAPI(title="ManaOS RPG API", version="0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
):
    app.include_router(_r.router)

