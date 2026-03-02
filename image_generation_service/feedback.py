"""
User Feedback & Rating System
===============================
ユーザーからの画像評価フィードバックを収集・保存し、
品質改善ループに接続する。

テーブル:
  feedback — (id, job_id, user_id, rating 1-5, tags[], comment, created_at)

SQLite WAL mode で高速書き込み。
"""

from __future__ import annotations

import logging
import sqlite3
import json
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

_log = logging.getLogger("manaos.feedback")

_DB_PATH = Path(__file__).resolve().parent.parent / "feedback.db"


@contextmanager
def _get_db(path: Optional[Path] = None):
    conn = sqlite3.connect(str(path or _DB_PATH), timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


_SCHEMA = """
CREATE TABLE IF NOT EXISTS feedback (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id      TEXT NOT NULL,
    user_id     TEXT NOT NULL DEFAULT 'anonymous',
    api_key     TEXT NOT NULL DEFAULT 'default',
    rating      INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
    tags        TEXT DEFAULT '[]',
    comment     TEXT DEFAULT '',
    prompt      TEXT DEFAULT '',
    quality_score_overall REAL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_feedback_job ON feedback(job_id);
CREATE INDEX IF NOT EXISTS idx_feedback_user ON feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_feedback_rating ON feedback(rating);
CREATE INDEX IF NOT EXISTS idx_feedback_created ON feedback(created_at);
"""


class FeedbackManager:
    """ユーザーフィードバック管理"""

    def __init__(self, db_path: Optional[Path] = None):
        self._db_path = db_path or _DB_PATH
        self._init_db()

    def _init_db(self):
        with _get_db(self._db_path) as conn:
            conn.executescript(_SCHEMA)
            _log.info("Feedback DB initialized: %s", self._db_path)

    async def submit_feedback(
        self,
        job_id: str,
        rating: int,
        user_id: str = "anonymous",
        api_key: str = "default",
        tags: Optional[List[str]] = None,
        comment: str = "",
        prompt: str = "",
        quality_score_overall: Optional[float] = None,
    ) -> Dict[str, Any]:
        """フィードバックを保存"""
        if not 1 <= rating <= 5:
            raise ValueError("Rating must be 1-5")

        with _get_db(self._db_path) as conn:
            cursor = conn.execute(
                """INSERT INTO feedback 
                   (job_id, user_id, api_key, rating, tags, comment, prompt, quality_score_overall)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    job_id,
                    user_id,
                    api_key,
                    rating,
                    json.dumps(tags or []),
                    comment,
                    prompt,
                    quality_score_overall,
                ),
            )
            feedback_id = cursor.lastrowid

        _log.info("Feedback #%d: job=%s rating=%d user=%s", feedback_id, job_id, rating, user_id)
        return {
            "feedback_id": feedback_id,
            "job_id": job_id,
            "rating": rating,
            "status": "recorded",
        }

    async def get_feedback_for_job(self, job_id: str) -> List[Dict]:
        """特定ジョブのフィードバック一覧"""
        with _get_db(self._db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM feedback WHERE job_id = ? ORDER BY created_at DESC",
                (job_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    async def get_aggregate_stats(self, days: int = 7) -> Dict[str, Any]:
        """フィードバック集計統計"""
        with _get_db(self._db_path) as conn:
            row = conn.execute(
                """SELECT 
                     COUNT(*) AS total,
                     AVG(rating) AS avg_rating,
                     MIN(rating) AS min_rating,
                     MAX(rating) AS max_rating,
                     SUM(CASE WHEN rating >= 4 THEN 1 ELSE 0 END) AS positive,
                     SUM(CASE WHEN rating <= 2 THEN 1 ELSE 0 END) AS negative
                   FROM feedback
                   WHERE created_at >= datetime('now', ?)""",
                (f"-{days} days",),
            ).fetchone()

            # Rating 分布
            dist = conn.execute(
                """SELECT rating, COUNT(*) AS cnt
                   FROM feedback
                   WHERE created_at >= datetime('now', ?)
                   GROUP BY rating ORDER BY rating""",
                (f"-{days} days",),
            ).fetchall()

        return {
            "period_days": days,
            "total_feedback": row["total"],
            "avg_rating": round(row["avg_rating"], 2) if row["avg_rating"] else None,
            "min_rating": row["min_rating"],
            "max_rating": row["max_rating"],
            "positive_count": row["positive"],
            "negative_count": row["negative"],
            "satisfaction_rate": (
                round(row["positive"] / row["total"] * 100, 1)
                if row["total"] > 0 else None
            ),
            "distribution": {r["rating"]: r["cnt"] for r in dist},
        }

    async def get_low_rated_jobs(self, threshold: int = 2, limit: int = 20) -> List[Dict]:
        """低評価ジョブの一覧（品質改善の候補）"""
        with _get_db(self._db_path) as conn:
            rows = conn.execute(
                """SELECT job_id, rating, prompt, quality_score_overall, comment, created_at
                   FROM feedback
                   WHERE rating <= ?
                   ORDER BY created_at DESC
                   LIMIT ?""",
                (threshold, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    async def get_popular_tags(self, limit: int = 10) -> List[Dict]:
        """よく使われるフィードバックタグ"""
        with _get_db(self._db_path) as conn:
            rows = conn.execute(
                "SELECT tags FROM feedback WHERE tags != '[]'"
            ).fetchall()

        tag_counts: Dict[str, int] = {}
        for row in rows:
            try:
                tags = json.loads(row["tags"])
                for tag in tags:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
            except (json.JSONDecodeError, TypeError):
                continue

        sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
        return [{"tag": t, "count": c} for t, c in sorted_tags[:limit]]

    async def get_quality_correlation(self) -> Dict[str, Any]:
        """品質スコアとユーザー評価の相関分析"""
        with _get_db(self._db_path) as conn:
            rows = conn.execute(
                """SELECT rating, quality_score_overall
                   FROM feedback
                   WHERE quality_score_overall IS NOT NULL"""
            ).fetchall()

        if not rows:
            return {"data_points": 0, "correlation": None}

        ratings = [r["rating"] for r in rows]
        scores = [r["quality_score_overall"] for r in rows]

        # 簡易ピアソン相関
        n = len(rows)
        sum_xy = sum(r * s for r, s in zip(ratings, scores))
        sum_x = sum(ratings)
        sum_y = sum(scores)
        sum_x2 = sum(r * r for r in ratings)
        sum_y2 = sum(s * s for s in scores)

        numerator = n * sum_xy - sum_x * sum_y
        denominator_sq = (n * sum_x2 - sum_x ** 2) * (n * sum_y2 - sum_y ** 2)

        if denominator_sq <= 0:
            correlation = 0
        else:
            correlation = numerator / (denominator_sq ** 0.5)

        # Rating別の平均品質スコア
        from collections import defaultdict
        by_rating = defaultdict(list)
        for r, s in zip(ratings, scores):
            by_rating[r].append(s)

        avg_by_rating = {
            r: round(sum(vals) / len(vals), 2)
            for r, vals in sorted(by_rating.items())
        }

        return {
            "data_points": n,
            "correlation": round(correlation, 4),
            "avg_quality_by_rating": avg_by_rating,
        }
