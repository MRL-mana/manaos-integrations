"""
Job Queue — SQLite ベースの非同期ジョブキュー
==============================================
特徴:
  - SQLite 永続化（プロセス再起動でもジョブ保持）
  - 優先度付きキュー（Enterprise > Pro > Free）
  - 同時実行制限（GPU は 1 枚ずつが効率的）
  - デッドジョブ検出 & リカバリ
  - TTL: 24h 自動パージ

Future:
  Redis + Celery / RQ に移行可能（インターフェース互換）
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Coroutine, Dict, List, Optional

_log = logging.getLogger("manaos.image_queue")

_DB_PATH = Path(os.getenv(
    "QUEUE_DB_PATH",
    str(Path(__file__).resolve().parent.parent / "job_queue.db"),
))

_MAX_CONCURRENT = int(os.getenv("QUEUE_MAX_CONCURRENT", "1"))   # GPU は 1 枚ずつ
_DEAD_TIMEOUT_SEC = 600   # 10 分間 processing のまま → dead 判定
_TTL_HOURS = 24           # 完了後 24h で自動パージ


class QueueState(str, Enum):
    waiting = "waiting"
    processing = "processing"
    completed = "completed"
    failed = "failed"
    dead = "dead"


@contextmanager
def _get_db():
    """SQLite 接続 (WAL モード)"""
    conn = sqlite3.connect(str(_DB_PATH), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _init_db():
    """テーブル作成（べき等）"""
    with _get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS job_queue (
                job_id      TEXT PRIMARY KEY,
                priority    INTEGER NOT NULL DEFAULT 1,
                state       TEXT NOT NULL DEFAULT 'waiting',
                payload     TEXT,
                created_at  TEXT NOT NULL,
                started_at  TEXT,
                finished_at TEXT,
                result      TEXT,
                error       TEXT
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_queue_state_priority
            ON job_queue (state, priority DESC, created_at ASC)
        """)
    _log.info("JobQueue DB initialized: %s", _DB_PATH)


class JobQueue:
    """SQLite ベースの優先度付きジョブキュー"""

    def __init__(self):
        _init_db()
        self._processing_count = 0
        self._worker_task: Optional[asyncio.Task] = None
        self._handler: Optional[Callable] = None
        _log.info(
            "JobQueue initialized (sqlite, max_concurrent=%d, db=%s)",
            _MAX_CONCURRENT, _DB_PATH,
        )

    # ─── Enqueue / Dequeue ────────────────────────────

    async def enqueue(
        self,
        job_id: str,
        priority: int = 1,
        payload: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        ジョブをキューに追加。現在のキュー内位置 (0-based) を返す。
        priority: 1=low (Free), 2=medium (Pro), 3=high (Enterprise)
        """
        with _get_db() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO job_queue
                   (job_id, priority, state, payload, created_at)
                   VALUES (?, ?, 'waiting', ?, ?)""",
                (
                    job_id,
                    priority,
                    json.dumps(payload) if payload else None,
                    datetime.now().isoformat(),
                ),
            )
        pos = await self.get_position(job_id)
        _log.info("Enqueued job %s (priority=%d, position=%s)", job_id, priority, pos)
        return pos or 0

    async def dequeue(self) -> Optional[Dict[str, Any]]:
        """
        次のジョブを取り出す（priority DESC, created_at ASC）。
        同時実行制限を超えていたら None。
        """
        if self._processing_count >= _MAX_CONCURRENT:
            return None

        with _get_db() as conn:
            row = conn.execute(
                """SELECT job_id, priority, payload FROM job_queue
                   WHERE state = 'waiting'
                   ORDER BY priority DESC, created_at ASC
                   LIMIT 1""",
            ).fetchone()

            if row is None:
                return None

            conn.execute(
                """UPDATE job_queue SET state = 'processing', started_at = ?
                   WHERE job_id = ?""",
                (datetime.now().isoformat(), row["job_id"]),
            )

        self._processing_count += 1
        payload = json.loads(row["payload"]) if row["payload"] else {}
        return {
            "job_id": row["job_id"],
            "priority": row["priority"],
            "payload": payload,
        }

    async def complete(self, job_id: str, result: Optional[Dict] = None):
        """ジョブ完了を記録"""
        with _get_db() as conn:
            conn.execute(
                """UPDATE job_queue SET state = 'completed', finished_at = ?,
                   result = ? WHERE job_id = ?""",
                (
                    datetime.now().isoformat(),
                    json.dumps(result) if result else None,
                    job_id,
                ),
            )
        self._processing_count = max(0, self._processing_count - 1)
        _log.info("Job %s completed", job_id)

    async def fail(self, job_id: str, error: str):
        """ジョブ失敗を記録"""
        with _get_db() as conn:
            conn.execute(
                """UPDATE job_queue SET state = 'failed', finished_at = ?,
                   error = ? WHERE job_id = ?""",
                (datetime.now().isoformat(), error, job_id),
            )
        self._processing_count = max(0, self._processing_count - 1)
        _log.warning("Job %s failed: %s", job_id, error)

    # ─── Status ───────────────────────────────────────

    async def get_position(self, job_id: str) -> Optional[int]:
        """キュー内の位置を取得 (0 = 次に処理される)"""
        with _get_db() as conn:
            # まず対象ジョブの情報を取得
            target = conn.execute(
                "SELECT priority, created_at, state FROM job_queue WHERE job_id = ?",
                (job_id,),
            ).fetchone()
            if target is None:
                return None
            if target["state"] != "waiting":
                return None  # 処理中 or 完了済み

            # 自分より前にいるジョブ数 = position
            count = conn.execute(
                """SELECT COUNT(*) FROM job_queue
                   WHERE state = 'waiting'
                   AND (priority > ? OR (priority = ? AND created_at < ?))""",
                (target["priority"], target["priority"], target["created_at"]),
            ).fetchone()[0]
            return count

    async def get_queue_length(self) -> int:
        """waiting 状態のジョブ数"""
        with _get_db() as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM job_queue WHERE state = 'waiting'"
            ).fetchone()[0]

    async def get_processing_count(self) -> int:
        """現在処理中のジョブ数"""
        return self._processing_count

    async def get_stats(self) -> Dict[str, Any]:
        """キュー全体の統計"""
        with _get_db() as conn:
            rows = conn.execute(
                """SELECT state, COUNT(*) as cnt FROM job_queue
                   GROUP BY state"""
            ).fetchall()
            state_counts = {row["state"]: row["cnt"] for row in rows}

            total = conn.execute("SELECT COUNT(*) FROM job_queue").fetchone()[0]

            # 平均待ち時間 (最近 50 件の completed)
            avg_wait = conn.execute(
                """SELECT AVG(
                     CAST((julianday(started_at) - julianday(created_at)) * 86400 AS REAL)
                   ) FROM (
                     SELECT started_at, created_at FROM job_queue
                     WHERE state = 'completed' AND started_at IS NOT NULL
                     ORDER BY finished_at DESC LIMIT 50
                   )"""
            ).fetchone()[0]

        return {
            "total_jobs": total,
            "waiting": state_counts.get("waiting", 0),
            "processing": state_counts.get("processing", 0),
            "completed": state_counts.get("completed", 0),
            "failed": state_counts.get("failed", 0),
            "dead": state_counts.get("dead", 0),
            "max_concurrent": _MAX_CONCURRENT,
            "avg_wait_seconds": round(avg_wait, 1) if avg_wait else 0,
        }

    # ─── Worker Loop ──────────────────────────────────

    def set_handler(
        self,
        handler: Callable[[str, Dict], Coroutine[Any, Any, Optional[Dict]]],
    ):
        """
        キューワーカーのハンドラを設定。
        handler(job_id, payload) → result_dict or None
        """
        self._handler = handler

    async def start_worker(self):
        """バックグラウンドワーカーを起動"""
        if self._worker_task and not self._worker_task.done():
            _log.warning("Worker already running")
            return
        self._worker_task = asyncio.create_task(self._worker_loop())
        _log.info("Queue worker started")

    async def stop_worker(self):
        """ワーカーを停止"""
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None
            _log.info("Queue worker stopped")

    async def _worker_loop(self):
        """
        メインワーカーループ:
          1. dequeue で次のジョブを取得
          2. handler を呼び出し
          3. complete / fail を記録
          4. dead ジョブ & 期限切れをクリーンアップ
        """
        _log.info("Worker loop started (poll interval: 1s)")
        while True:
            try:
                job = await self.dequeue()
                if job is None:
                    await asyncio.sleep(1)
                    continue

                job_id = job["job_id"]
                payload = job["payload"]

                if self._handler is None:
                    _log.error("No handler set! Failing job %s", job_id)
                    await self.fail(job_id, "No handler configured")
                    continue

                try:
                    result = await self._handler(job_id, payload)
                    await self.complete(job_id, result)
                except Exception as e:
                    _log.exception("Handler failed for job %s", job_id)
                    await self.fail(job_id, str(e))

                # 定期クリーンアップ (10 ジョブごと)
                await self._cleanup_dead_jobs()
                await self._purge_old_jobs()

            except asyncio.CancelledError:
                _log.info("Worker loop cancelled")
                break
            except Exception:
                _log.exception("Worker loop error")
                await asyncio.sleep(5)

    async def _cleanup_dead_jobs(self):
        """_DEAD_TIMEOUT_SEC 以上 processing のジョブを dead に"""
        cutoff = (datetime.now() - timedelta(seconds=_DEAD_TIMEOUT_SEC)).isoformat()
        with _get_db() as conn:
            updated = conn.execute(
                """UPDATE job_queue SET state = 'dead', finished_at = ?,
                   error = 'Timed out (dead job detection)'
                   WHERE state = 'processing' AND started_at < ?""",
                (datetime.now().isoformat(), cutoff),
            ).rowcount
        if updated:
            self._processing_count = max(0, self._processing_count - updated)
            _log.warning("Marked %d dead jobs", updated)

    async def _purge_old_jobs(self):
        """TTL 超過の完了/失敗ジョブを削除"""
        cutoff = (datetime.now() - timedelta(hours=_TTL_HOURS)).isoformat()
        with _get_db() as conn:
            deleted = conn.execute(
                """DELETE FROM job_queue
                   WHERE state IN ('completed', 'failed', 'dead')
                   AND finished_at < ?""",
                (cutoff,),
            ).rowcount
        if deleted:
            _log.info("Purged %d expired jobs", deleted)
