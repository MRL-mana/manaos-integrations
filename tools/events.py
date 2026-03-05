#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ManaOS Event Log
================
配置先: tools/events.py

全サービスイベントを logs/events.jsonl に記録する共有ライブラリ。
heal.py / manaosctl.py から import して使う。

使い方:
  from tools.events import emit, EVENT_LOG

  emit("service_up",   service="llm_routing", detail="healed by heal.py")
  emit("service_down", service="comfyui",     detail="health check failed")
  emit("heal_trigger", detail="2 services DOWN")
  emit("cost_alert",   service="comfyui",     detail="cost_risk=high running")
  emit("startup",      detail="manaosctl up executed")
  emit("shutdown",     service="comfyui",     detail="stopped by manaosctl")
"""

from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path
from typing import Optional

REPO_ROOT  = Path(__file__).parent.parent
LOG_DIR    = REPO_ROOT / "logs"
EVENT_LOG  = LOG_DIR / "events.jsonl"
ROTATE_AT  = 5000   # この行数超えたら events.1.jsonl にローテーション

# イベント種別（表示色マッピング用）
EVENT_COLORS = {
    "service_up":   "\x1b[32m",   # green
    "service_down": "\x1b[31m",   # red
    "heal_trigger": "\x1b[35m",   # magenta
    "heal_ok":      "\x1b[32m",   # green
    "heal_fail":    "\x1b[31m",   # red
    "cost_alert":   "\x1b[33m",   # yellow
    "startup":      "\x1b[36m",   # cyan
    "shutdown":     "\x1b[33m",   # yellow
    "policy":       "\x1b[35m",   # magenta
}
RESET = "\x1b[0m"
DIM   = "\x1b[2m"


def _maybe_rotate() -> None:
    """EVENT_LOG が ROTATE_AT 行を超えていたら events.1.jsonl にシフト。"""
    if not EVENT_LOG.exists():
        return
    try:
        count = sum(1 for _ in EVENT_LOG.open(encoding="utf-8", errors="replace"))
    except OSError:
        return
    if count >= ROTATE_AT:
        rotated = LOG_DIR / "events.1.jsonl"
        try:
            rotated.unlink(missing_ok=True)
            EVENT_LOG.rename(rotated)
        except OSError:
            pass  # rename 失敗しても継続


def emit(
    event: str,
    service: Optional[str] = None,
    detail: Optional[str] = None,
    source: Optional[str] = None,
) -> None:
    """イベントを logs/events.jsonl に追記する。"""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    _maybe_rotate()
    record = {
        "time":    datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "event":   event,
        "service": service or "",
        "detail":  detail or "",
        "source":  source or "",
    }
    with open(EVENT_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def read_events(n: int = 50) -> list[dict]:
    """最新 n 件のイベントを返す。"""
    if not EVENT_LOG.exists():
        return []
    lines = EVENT_LOG.read_text(encoding="utf-8", errors="replace").splitlines()
    events = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return events[-n:]
