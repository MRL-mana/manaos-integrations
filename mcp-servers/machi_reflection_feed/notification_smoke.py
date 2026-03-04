#!/usr/bin/env python3
"""Smoke-test helper for the Reflection Feed notification manager."""
from __future__ import annotations

import argparse
import logging
import os
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PACKAGE_ROOT.parent
for candidate in (str(REPO_ROOT), str(PACKAGE_ROOT)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from machi_reflection_feed.notifications import NotificationManager
from machi_reflection_feed.schemas import CommentaryEntry, DecisionLog, FutureIntent, LoopEval

logging.basicConfig(level=logging.INFO)


def build_manager(args: argparse.Namespace) -> NotificationManager:
    manager = NotificationManager.from_env(mode=args.mode)
    if args.dry_run is not None:
        manager.dry_run = args.dry_run
        if manager.dry_run and not manager.enabled:
            manager.enabled = True
            manager.logger.info("Enabling notifications for dry-run override.")
    return manager


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def trigger_decision(manager: NotificationManager) -> None:
    decision = DecisionLog.model_validate(  # type: ignore[arg-type]
        {
            "id": "dec-smoke",
            "ts": _now(),
            "selected": {
                "task_id": "task-123",
                "reason": "smoke-test",
            },
            "priority_vector": {"impact": 0.8, "effort": 0.2},
            "selected_metric": "impact",
            "trade_offs": ["speed vs quality"],
        }
    )
    manager.notify_decision(decision)


def trigger_future(manager: NotificationManager) -> None:
    intent = FutureIntent.model_validate(  # type: ignore[arg-type]
        {
            "id": "future-smoke",
            "ts": _now(),
            "intent": "Ship onboarding flow",
            "dependencies": ["design", "QA"],
            "confidence": 0.9,
            "eta_hint": "2025-12-01",
        }
    )
    manager.notify_future_intent(intent)


def trigger_reflection(manager: NotificationManager) -> None:
    loop_eval = LoopEval.model_validate(  # type: ignore[arg-type]
        {
            "id": "loop-smoke",
            "ts": _now(),
            "inputs": {"task_id": "task-987"},
            "self_eval": {"issues": ["blocked on infra"]},
        }
    )
    manager.notify_reflection(loop_eval)


def trigger_commentary(manager: NotificationManager) -> None:
    entry = CommentaryEntry.model_validate(  # type: ignore[arg-type]
        {
            "id": "commentary-smoke",
            "ts": _now(),
            "channel": "daily",
            "message": "Smoke test message",
            "metadata": {"user": "mana"},
        }
    )
    manager.notify_commentary(entry)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "event",
        choices=["decision", "future", "reflection", "commentary"],
        help="Which notification to emit",
    )
    parser.add_argument(
        "--mode",
        default=os.getenv("MACHI_FEED_MODE", "expressive"),
        help="Feed mode passed into NotificationManager.from_env()",
    )
    parser.add_argument(
        "--dry-run",
        dest="dry_run",
        action=argparse.BooleanOptionalAction,
        help="Override dry-run flag regardless of environment",
    )
    args = parser.parse_args(argv)

    manager = build_manager(args)
    logging.info("NotificationManager channel config: %s", asdict(manager.channel))

    mapping: dict[str, Callable[[NotificationManager], None]] = {
        "decision": trigger_decision,
        "future": trigger_future,
        "reflection": trigger_reflection,
        "commentary": trigger_commentary,
    }
    mapping[args.event](manager)

    if manager.dry_run:
        logging.info("Dry-run payloads: %s", manager._dry_run_log)  # noqa: SLF001

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
