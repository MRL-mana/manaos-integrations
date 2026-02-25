from __future__ import annotations

import os
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent  # backend/
REG = BASE.parent / "registry"
REPO_ROOT = BASE.parent.parent
STORE = BASE / "storage"
STORE.mkdir(parents=True, exist_ok=True)

STATE_FILE = STORE / "state.json"
EVENTS_FILE = STORE / "events.log"

ACTION_LAST_FILE = STORE / "last_action.json"

UNIFIED_DOCTOR_CACHE_FILE = STORE / "unified_doctor_cache.json"
UNIFIED_DOCTOR_CACHE_TTL_S = 60

DEFAULT_UNIFIED_API_BASE = os.environ.get("MANAOS_UNIFIED_API_BASE", "http://127.0.0.1:9502").rstrip("/")
DEFAULT_OLLAMA_BASE = os.environ.get("MANAOS_OLLAMA_BASE", "http://127.0.0.1:11434").rstrip("/")
DEFAULT_MRL_MEMORY_BASE = os.environ.get("MANAOS_MRL_MEMORY_BASE", "http://127.0.0.1:9507").rstrip("/")

_RPG_API_TOKEN = os.environ.get("MANAOS_RPG_API_TOKEN", "").strip()

_CORS_ORIGINS = [
    o.strip()
    for o in os.environ.get("MANAOS_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
    if o.strip()
]
