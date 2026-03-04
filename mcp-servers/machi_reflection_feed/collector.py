"""Collector that mediates between hooks, storage, and metrics."""
from __future__ import annotations

import statistics
import time
from collections import Counter
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .capsule_builder import build_capsules
from .config import FeedConfig
from .event_stream import EventHub
from .metrics import (
    CAPSULES_TOTAL,
    FUTURE_CONFIDENCE_AVG,
    INGEST_COUNTER,
    INGEST_LATENCY,
    PRIORITY_EXPLORATION,
    PRIORITY_SPEED,
    PRIORITY_STABILITY,
)
from .notifications import NotificationManager
from .schemas import Capsule, CommentaryEntry, DecisionLog, FutureIntent, LoopEval
from .storage import SQLiteFeedStore


class ReflectionCollector:
    """High-level interface for ingesting and querying Reflection Feed data."""

    def __init__(self, config: FeedConfig, event_hub: Optional[EventHub] = None) -> None:
        self.config = config
        self.store = SQLiteFeedStore(config.store_path)
        self.notifier = NotificationManager.from_env(config.mode)
        self.event_hub = event_hub

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------

    def ingest_decision_log(self, payload: Dict[str, object]) -> DecisionLog:
        start = time.perf_counter()
        decision = DecisionLog.parse_obj(payload)
        self.store.insert_decision_log(decision)
        INGEST_COUNTER.labels("decision_log").inc()
        INGEST_LATENCY.observe((time.perf_counter() - start) * 1000)
        CAPSULES_TOTAL.inc()
        self._update_priority_gauges()
        self.notifier.notify_decision(decision)
        self._emit_timeline_update(
            kind="decision_log",
            record_id=decision.id,
            timestamp=decision.ts,
            capsule_id=decision.id,
        )
        return decision

    def ingest_loop_eval(self, payload: Dict[str, object]) -> LoopEval:
        start = time.perf_counter()
        loop_eval = LoopEval.parse_obj(payload)
        self.store.insert_loop_eval(loop_eval)
        INGEST_COUNTER.labels("loop_eval").inc()
        INGEST_LATENCY.observe((time.perf_counter() - start) * 1000)
        self._update_learning_gauge()
        self.notifier.notify_reflection(loop_eval)
        self._emit_timeline_update(
            kind="loop_eval",
            record_id=loop_eval.id,
            timestamp=loop_eval.ts,
            capsule_id=loop_eval.loop_id or None,
        )
        return loop_eval

    def ingest_future_intent(self, payload: Dict[str, object]) -> FutureIntent:
        start = time.perf_counter()
        future_intent = FutureIntent.parse_obj(payload)
        self.store.insert_future_intent(future_intent)
        INGEST_COUNTER.labels("future_intent").inc()
        INGEST_LATENCY.observe((time.perf_counter() - start) * 1000)
        self._update_future_confidence_gauge()
        self.notifier.notify_future_intent(future_intent)
        self._emit_timeline_update(
            kind="future_intent",
            record_id=future_intent.id,
            timestamp=future_intent.ts,
            capsule_id=future_intent.loop_id or None,
        )
        return future_intent

    def ingest_commentary(self, payload: Dict[str, object]) -> CommentaryEntry:
        start = time.perf_counter()
        entry = CommentaryEntry.parse_obj(payload)
        self.store.insert_commentary(entry)
        INGEST_COUNTER.labels("commentary").inc()
        INGEST_LATENCY.observe((time.perf_counter() - start) * 1000)
        self.notifier.notify_commentary(entry)
        self._emit_commentary(entry)
        return entry

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def summarize(self, since: Optional[datetime], until: Optional[datetime]) -> Dict[str, object]:
        deltas = {}
        for table in ("decision_log", "loop_eval", "future_intents"):
            count = self.store.count_records(table)
            latest = self.store.latest_timestamp(table)
            deltas[table] = {
                "count": count,
                "latest": latest.isoformat() if latest else None,
            }
        return deltas

    def fetch_capsules(
        self,
        limit: int,
        offset: int,
        since: Optional[datetime],
        until: Optional[datetime],
    ) -> List[Capsule]:
        decisions = self.store.fetch_decision_logs(
            limit=limit, offset=offset, since=since, until=until)
        if not decisions:
            return []

        window = timedelta(seconds=self.config.capsule_merge_window_sec)
        earliest = min(decision.ts for decision in decisions) - window
        latest = max(decision.ts for decision in decisions) + window

        loop_evals = self.store.fetch_loop_evals_between(earliest, latest)
        future_intents = self.store.fetch_future_intents_between(
            earliest, latest)
        capsules = build_capsules(
            decisions, loop_evals, future_intents, self.config.capsule_merge_window_sec)
        return capsules

    def fetch_future_intents(self, limit: int) -> List[FutureIntent]:
        return self.store.fetch_future_intents(limit)

    def recent_learning(self, top: int) -> List[Dict[str, object]]:
        samples = self.store.fetch_recent_loop_eval(sample_size=200)
        counter: Counter[str] = Counter()
        for sample in samples:
            what_went_well = sample.self_eval.get("what_went_well")
            if isinstance(what_went_well, list):
                for item in what_went_well:
                    if isinstance(item, str):
                        counter[item] += 1
        most_common = counter.most_common(top)
        return [
            {"pattern": pattern, "count": count}
            for pattern, count in most_common
        ]

    def priority_vector_average(self, window: int = 20) -> Dict[str, float]:
        vectors = self.store.fetch_recent_priority_vectors(window)
        if not vectors:
            return {}
        keys = set().union(*(vector.keys() for vector in vectors))
        averages: Dict[str, float] = {}
        for key in keys:
            values = [vector.get(key, 0.0) for vector in vectors]
            averages[key] = statistics.fmean(values)
        self._set_priority_gauges(averages)
        return averages

    def fetch_recent_commentary(self, limit: int) -> List[CommentaryEntry]:
        return self.store.fetch_recent_commentary(limit)

    # ------------------------------------------------------------------
    # Metrics helpers
    # ------------------------------------------------------------------

    def _set_priority_gauges(self, averages: Dict[str, float]) -> None:
        PRIORITY_STABILITY.set(averages.get("stability", 0.0))
        PRIORITY_EXPLORATION.set(averages.get("exploration", 0.0))
        PRIORITY_SPEED.set(averages.get("speed", 0.0))

    def _update_priority_gauges(self) -> None:
        self.priority_vector_average()

    def _update_future_confidence_gauge(self) -> None:
        intents = self.store.fetch_future_intents(limit=50)
        confidences = [
            intent.confidence for intent in intents if intent.confidence is not None]
        if confidences:
            FUTURE_CONFIDENCE_AVG.set(statistics.fmean(confidences))
        else:
            FUTURE_CONFIDENCE_AVG.set(0.0)

    def _update_learning_gauge(self) -> None:
        # Placeholder: currently no dedicated gauge; calling priority update keeps metrics fresh.
        pass

    def _emit_timeline_update(
        self,
        *,
        kind: str,
        record_id: str,
        timestamp: datetime,
        capsule_id: Optional[str],
    ) -> None:
        if not self.event_hub:
            return
        payload: Dict[str, object] = {
            "type": "timeline_update",
            "kind": kind,
            "record_id": record_id,
            "timestamp": timestamp.isoformat(),
        }
        if capsule_id:
            payload["capsule_id"] = capsule_id
        self.event_hub.publish(payload)

    def _emit_commentary(self, entry: CommentaryEntry) -> None:
        if not self.event_hub:
            return
        payload: Dict[str, object] = {
            "type": "commentary",
            "id": entry.id,
            "timestamp": entry.ts.isoformat(),
            "message": entry.message,
            "channel": entry.channel,
            "level": entry.level,
            "metadata": entry.metadata,
        }
        self.event_hub.publish(payload)
