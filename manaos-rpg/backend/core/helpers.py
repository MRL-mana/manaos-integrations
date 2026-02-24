from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _append_next_action(next_actions: list[str], msg: str) -> None:
    m = str(msg or "").strip()
    if not m:
        return
    if m in next_actions:
        return
    next_actions.append(m)


def _append_next_action_hint(
    hints: list[dict[str, Any]],
    *,
    label: str,
    action_id: str | None = None,
) -> None:
    lab = str(label or "").strip()
    if not lab:
        return
    aid = str(action_id or "").strip() or None
    key = (lab, aid)
    for h in hints:
        if not isinstance(h, dict):
            continue
        if (str(h.get("label") or "").strip(), str(h.get("action_id") or "").strip() or None) == key:
            return
    payload: dict[str, Any] = {"label": lab}
    if aid:
        payload["action_id"] = aid
    hints.append(payload)
