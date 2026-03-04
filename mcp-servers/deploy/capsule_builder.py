"""Utilities to build Reflection Feed capsules."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Callable, Dict, Iterable, List, Optional, TypeVar

from .schemas import Capsule, DecisionLog, FutureIntent, LoopEval

T = TypeVar("T")


def _find_nearest(
    entries: Iterable[T],
    target_ts: datetime,
    window_sec: int,
    *,
    key: Callable[[T], datetime],
) -> Optional[T]:
    window = timedelta(seconds=window_sec)
    closest: Optional[T] = None
    best_delta: Optional[timedelta] = None
    for entry in entries:
        ts = key(entry)
        delta = abs(ts - target_ts)
        if delta <= window and (best_delta is None or delta < best_delta):
            closest = entry
            best_delta = delta
    return closest


def build_capsules(
    decisions: List[DecisionLog],
    loop_evals: List[LoopEval],
    future_intents: List[FutureIntent],
    window_sec: int,
) -> List[Capsule]:
    if not decisions:
        return []

    loop_evals_sorted = sorted(loop_evals, key=lambda item: item.ts)
    future_sorted = sorted(future_intents, key=lambda item: item.ts)

    capsules: List[Capsule] = []
    for decision in decisions:
        loop_match = _find_nearest(
            loop_evals_sorted,
            decision.ts,
            window_sec,
            key=lambda entry: entry.ts,
        )
        future_match = _find_nearest(
            future_sorted,
            decision.ts,
            window_sec,
            key=lambda entry: entry.ts,
        )

        capsule_payload: Dict[str, object] = {
            "intent": decision.task_context or {},
            "decision": {
                "selected": decision.selected.dict(),
                "candidates": [candidate.dict() for candidate in decision.candidates],
                "trade_offs": decision.trade_offs,
                "priority_vector": decision.priority_vector,
                "selected_metric": decision.selected_metric,
            },
            "action": loop_match.actions if loop_match else [],
            "outcome": loop_match.outcome_score if loop_match else {},
            "reflection": loop_match.self_eval if loop_match else {},
            "next_intent": future_match.dict() if future_match else None,
        }

        capsules.append(
            Capsule(
                capsule_id=decision.id,
                capsule=capsule_payload,
                scores={
                    "priority_vector": decision.priority_vector,
                    "outcome_score": loop_match.outcome_score if loop_match else {},
                    "future_confidence": future_match.confidence if future_match else None,
                },
                decision_ts=decision.ts,
            )
        )

    capsules.sort(key=lambda entry: entry.decision_ts, reverse=True)
    return capsules
