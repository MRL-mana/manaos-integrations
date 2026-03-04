"""SQLite storage backend for the Reflection Feed."""
from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

from .schemas import DecisionLog, FutureIntent, LoopEval

DDL_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS decision_log (
      id TEXT PRIMARY KEY,
      ts TEXT NOT NULL,
      loop_id TEXT,
      task_context TEXT,
      candidates TEXT,
      selected TEXT,
      priority_vector TEXT,
      selected_metric TEXT,
      trade_offs TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS loop_eval (
      id TEXT PRIMARY KEY,
      ts TEXT NOT NULL,
      loop_id TEXT,
      inputs TEXT,
      actions TEXT,
      outcome_score TEXT,
      self_eval TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS future_intents (
      id TEXT PRIMARY KEY,
      ts TEXT NOT NULL,
      loop_id TEXT,
      intent TEXT,
      confidence REAL,
      expected_impact TEXT,
      requirements TEXT,
      dependencies TEXT,
      eta_hint TEXT
    )
    """,
)


class SQLiteFeedStore:
    """Thin SQLite wrapper to persist Reflection Feed artifacts."""

    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(str(self.path), check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self._initialize()

    def _initialize(self) -> None:
        with self._connection:
            for statement in DDL_STATEMENTS:
                self._connection.execute(statement)
            self._connection.execute("PRAGMA journal_mode=WAL;")
            self._connection.execute("PRAGMA synchronous=NORMAL;")

    def close(self) -> None:
        self._connection.close()

    # ------------------------------------------------------------------
    # Insert helpers
    # ------------------------------------------------------------------

    def insert_decision_log(self, log: DecisionLog) -> None:
        payload = {
            "task_context": json.dumps(log.task_context or {}),
            "candidates": json.dumps([candidate.dict(by_alias=True) for candidate in log.candidates]),
            "selected": json.dumps(log.selected.dict(by_alias=True)),
            "priority_vector": json.dumps(log.priority_vector),
            "trade_offs": json.dumps(log.trade_offs),
        }
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT OR REPLACE INTO decision_log (
                  id, ts, loop_id, task_context, candidates, selected,
                  priority_vector, selected_metric, trade_offs
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    log.id,
                    log.ts.isoformat(),
                    log.loop_id,
                    payload["task_context"],
                    payload["candidates"],
                    payload["selected"],
                    payload["priority_vector"],
                    log.selected_metric,
                    payload["trade_offs"],
                ),
            )

    def insert_loop_eval(self, entry: LoopEval) -> None:
        payload = {
            "inputs": json.dumps(entry.inputs or {}),
            "actions": json.dumps(entry.actions or []),
            "outcome_score": json.dumps(entry.outcome_score or {}),
            "self_eval": json.dumps(entry.self_eval or {}),
        }
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT OR REPLACE INTO loop_eval (
                  id, ts, loop_id, inputs, actions, outcome_score, self_eval
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.id,
                    entry.ts.isoformat(),
                    entry.loop_id,
                    payload["inputs"],
                    payload["actions"],
                    payload["outcome_score"],
                    payload["self_eval"],
                ),
            )

    def insert_future_intent(self, intent: FutureIntent) -> None:
        payload = {
            "expected_impact": json.dumps(intent.expected_impact or {}),
            "requirements": json.dumps(intent.requirements),
            "dependencies": json.dumps(intent.dependencies),
        }
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT OR REPLACE INTO future_intents (
                  id, ts, loop_id, intent, confidence, expected_impact,
                  requirements, dependencies, eta_hint
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    intent.id,
                    intent.ts.isoformat(),
                    intent.loop_id,
                    intent.intent,
                    intent.confidence,
                    payload["expected_impact"],
                    payload["requirements"],
                    payload["dependencies"],
                    intent.eta_hint,
                ),
            )

    # ------------------------------------------------------------------
    # Fetch helpers
    # ------------------------------------------------------------------

    def fetch_decision_logs(
        self,
        limit: int,
        offset: int,
        since: Optional[datetime],
        until: Optional[datetime],
    ) -> List[DecisionLog]:
        query = ["SELECT * FROM decision_log"]
        params: List[object] = []
        clauses: List[str] = []
        if since:
            clauses.append("ts >= ?")
            params.append(since.isoformat())
        if until:
            clauses.append("ts <= ?")
            params.append(until.isoformat())
        if clauses:
            query.append("WHERE " + " AND ".join(clauses))
        query.append("ORDER BY ts DESC")
        query.append("LIMIT ? OFFSET ?")
        params.extend([limit, offset])
        statement = " ".join(query)
        rows = self._connection.execute(statement, params).fetchall()
        return [self._row_to_decision_log(row) for row in rows]

    def fetch_loop_evals_between(
        self,
        start: datetime,
        end: datetime,
    ) -> List[LoopEval]:
        rows = self._connection.execute(
            """
            SELECT * FROM loop_eval
            WHERE ts BETWEEN ? AND ?
            ORDER BY ts DESC
            """,
            (start.isoformat(), end.isoformat()),
        ).fetchall()
        return [self._row_to_loop_eval(row) for row in rows]

    def fetch_future_intents_between(
        self,
        start: datetime,
        end: datetime,
        limit: Optional[int] = None,
    ) -> List[FutureIntent]:
        statement = [
            "SELECT * FROM future_intents WHERE ts BETWEEN ? AND ? ORDER BY ts DESC",
        ]
        params: List[object] = [start.isoformat(), end.isoformat()]
        if limit is not None:
            statement.append("LIMIT ?")
            params.append(limit)
        rows = self._connection.execute(" ".join(statement), params).fetchall()
        return [self._row_to_future_intent(row) for row in rows]

    def fetch_future_intents(self, limit: int) -> List[FutureIntent]:
        rows = self._connection.execute(
            "SELECT * FROM future_intents ORDER BY ts DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [self._row_to_future_intent(row) for row in rows]

    def count_records(self, table: str) -> int:
        (count,) = self._connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        return int(count)

    def latest_timestamp(self, table: str) -> Optional[datetime]:
        row = self._connection.execute(
            f"SELECT ts FROM {table} ORDER BY ts DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return None
        return datetime.fromisoformat(row[0])

    def fetch_recent_priority_vectors(self, sample_size: int) -> List[Dict[str, float]]:
        rows = self._connection.execute(
            "SELECT priority_vector FROM decision_log ORDER BY ts DESC LIMIT ?",
            (sample_size,),
        ).fetchall()
        vectors: List[Dict[str, float]] = []
        for row in rows:
            raw = row[0]
            try:
                vectors.append(json.loads(raw) if raw else {})
            except json.JSONDecodeError:
                continue
        return vectors

    def fetch_recent_loop_eval(self, sample_size: int) -> List[LoopEval]:
        rows = self._connection.execute(
            "SELECT * FROM loop_eval ORDER BY ts DESC LIMIT ?",
            (sample_size,),
        ).fetchall()
        return [self._row_to_loop_eval(row) for row in rows]

    def fetch_loop_eval_by_ids(self, ids: Sequence[str]) -> List[LoopEval]:
        if not ids:
            return []
        placeholders = ",".join("?" for _ in ids)
        rows = self._connection.execute(
            f"SELECT * FROM loop_eval WHERE id IN ({placeholders})",
            list(ids),
        ).fetchall()
        return [self._row_to_loop_eval(row) for row in rows]

    # ------------------------------------------------------------------
    # Row decoders
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_decision_log(row: sqlite3.Row) -> DecisionLog:
        task_context = json.loads(row["task_context"]) if row["task_context"] else {}
        candidates_raw = json.loads(row["candidates"]) if row["candidates"] else []
        selected_raw = json.loads(row["selected"]) if row["selected"] else {}
        trade_offs = json.loads(row["trade_offs"]) if row["trade_offs"] else []
        priority_vector = json.loads(row["priority_vector"]) if row["priority_vector"] else {}
        return DecisionLog(
            id=row["id"],
            ts=row["ts"],
            loop_id=row["loop_id"],
            task_context=task_context,
            candidates=candidates_raw,
            selected=selected_raw,
            priority_vector=priority_vector,
            selected_metric=row["selected_metric"],
            trade_offs=trade_offs,
        )

    @staticmethod
    def _row_to_loop_eval(row: sqlite3.Row) -> LoopEval:
        return LoopEval(
            id=row["id"],
            ts=row["ts"],
            loop_id=row["loop_id"],
            inputs=json.loads(row["inputs"]) if row["inputs"] else {},
            actions=json.loads(row["actions"]) if row["actions"] else [],
            outcome_score=json.loads(row["outcome_score"]) if row["outcome_score"] else {},
            self_eval=json.loads(row["self_eval"]) if row["self_eval"] else {},
        )

    @staticmethod
    def _row_to_future_intent(row: sqlite3.Row) -> FutureIntent:
        return FutureIntent(
            id=row["id"],
            ts=row["ts"],
            loop_id=row["loop_id"],
            intent=row["intent"],
            confidence=row["confidence"],
            expected_impact=json.loads(row["expected_impact"]) if row["expected_impact"] else {},
            requirements=json.loads(row["requirements"]) if row["requirements"] else [],
            dependencies=json.loads(row["dependencies"]) if row["dependencies"] else [],
            eta_hint=row["eta_hint"],
        )
