"""Sample integration helpers for MachiOS loops.

These helpers demonstrate how to emit Reflection Feed payloads from planner,
executor, and reflector loops. Adjust the structures to match the production
context objects.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, Sequence
from uuid import uuid4

from .hooks import emit_decision_log, emit_future_intent, emit_loop_eval
from .payloads import (
    build_decision_payload,
    build_future_intent_payload,
    build_loop_eval_payload,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def record_planner_decision(context, ranked_candidates: Sequence) -> None:
    """Emit a decision_log payload from the planner loop.

    The ``context`` object is expected to expose ``goal``, ``tags``, and
    ``priority_weights`` attributes. ``ranked_candidates`` should be an ordered
    sequence with ``id``, ``score``, and ``reason`` attributes.
    """

    if not ranked_candidates:
        return

    best = ranked_candidates[0]
    payload = build_decision_payload(
        decision_id=f"dl-{uuid4()}",
        timestamp=utc_now(),
        loop_id="planner",
        goal=getattr(context, "goal", "unknown"),
        tags=getattr(context, "tags", []),
        candidates=[{"task_id": c.id, "score": getattr(c, "score", 0.0)} for c in ranked_candidates],
        selected={"task_id": best.id, "reason": getattr(best, "reason", "")},
        priority_vector=getattr(context, "priority_weights", {}).copy(),
        selected_metric="expected_reward",
        trade_offs=getattr(context, "tradeoffs", []),
    )
    emit_decision_log(payload)


def record_executor_eval(task_id: str, actions: Iterable[str], outcome: dict, reflection: dict) -> None:
    payload = build_loop_eval_payload(
        eval_id=f"le-{uuid4()}",
        timestamp=utc_now(),
        loop_id="executor",
        task_id=task_id,
        actions=list(actions),
        outcome_score=outcome,
        self_eval=reflection,
    )
    emit_loop_eval(payload)


def record_future_intent(description: str, *, loop_id: str = "reflector", confidence: float | None = None) -> None:
    payload = build_future_intent_payload(
        intent_id=f"fi-{uuid4()}",
        timestamp=utc_now(),
        loop_id=loop_id,
        intent=description,
        confidence=confidence,
        expected_impact=None,
        requirements=None,
        dependencies=None,
        eta_hint=None,
    )
    emit_future_intent(payload)
