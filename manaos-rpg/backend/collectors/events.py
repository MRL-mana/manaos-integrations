from __future__ import annotations

import json
import time
from pathlib import Path


def append_event(events_file: Path, event_type: str, message: str, data: dict | None = None) -> None:
    payload = {
        "ts": int(time.time()),
        "type": event_type,
        "message": message,
        "data": data or {},
    }
    events_file.parent.mkdir(parents=True, exist_ok=True)
    with events_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def tail_events(events_file: Path, limit: int = 100) -> list[dict]:
    if limit <= 0:
        return []
    if not events_file.exists():
        return []
    lines = events_file.read_text(encoding="utf-8", errors="replace").splitlines()
    tail = lines[-limit:]
    out: list[dict] = []
    for line in tail:
        try:
            out.append(json.loads(line))
        except Exception:
            out.append({"ts": None, "type": "parse_error", "message": line, "data": {}})
    return out
