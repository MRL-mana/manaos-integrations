"""Helper utilities for building Reflection Feed payloads."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional


def utc_now_iso() -> str:
    """Return the current UTC timestamp in ISO8601 format with a trailing Z."""

    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def isoformat(value: datetime) -> str:
    """Format a datetime to ISO8601 with trailing Z."""

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)
    return value.isoformat().replace("+00:00", "Z")


def build_decision_payload(
    *,
    decision_id: str,
    timestamp: datetime,
    loop_id: str,
    goal: str,
    tags: Optional[Iterable[str]],
    candidates: Iterable[Dict[str, object]],
    selected: Dict[str, object],
    priority_vector: Dict[str, float],
    selected_metric: Optional[str],
    trade_offs: Optional[Iterable[str]],
) -> Dict[str, object]:
    """Create a decision_log payload following the schema contract."""

    return {
        "id": decision_id,
        "ts": isoformat(timestamp),
        "loop_id": loop_id,
        "task_context": {
            "goal": goal,
            "tags": list(tags or []),
        },
        "candidates": list(candidates),
        "selected": selected,
        "priority_vector": priority_vector,
        "selected_metric": selected_metric,
        "trade_offs": list(trade_offs or []),
    }


def build_loop_eval_payload(
    *,
    eval_id: str,
    timestamp: datetime,
    loop_id: str,
    task_id: str,
    actions: Iterable[str],
    outcome_score: Dict[str, object],
    self_eval: Dict[str, object],
) -> Dict[str, object]:
    return {
        "id": eval_id,
        "ts": isoformat(timestamp),
        "loop_id": loop_id,
        "inputs": {"task_id": task_id},
        "actions": list(actions),
        "outcome_score": outcome_score,
        "self_eval": self_eval,
    }


def build_future_intent_payload(
    *,
    intent_id: str,
    timestamp: datetime,
    loop_id: str,
    intent: str,
    confidence: Optional[float],
    expected_impact: Optional[Dict[str, object]],
    requirements: Optional[Iterable[str]],
    dependencies: Optional[Iterable[str]],
    eta_hint: Optional[datetime],
) -> Dict[str, object]:
    return {
        "id": intent_id,
        "ts": isoformat(timestamp),
        "loop_id": loop_id,
        "intent": intent,
        "confidence": confidence,
        "expected_impact": expected_impact,
        "requirements": list(requirements or []),
        "dependencies": list(dependencies or []),
        "eta_hint": isoformat(eta_hint) if eta_hint else None,
    }
