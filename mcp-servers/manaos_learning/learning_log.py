#!/usr/bin/env python3
"""
ManaOS 共通学習ログ管理システム
全ツールの学習データを一元管理
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from uuid import uuid4
import logging

logger = logging.getLogger(__name__)


class LearningLog:
    """共通学習ログ管理クラス"""

    def __init__(self, base_dir: str = "/root/manaos_learning"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)

        # JSONL形式のログファイル（追記用）
        self.jsonl_path = self.base_dir / "logs" / "learning_log.jsonl"
        self.jsonl_path.parent.mkdir(exist_ok=True)

        # SQLite（検索・集計用）
        self.db_path = self.base_dir / "logs" / "learning.db"
        self._init_database()

    def _init_database(self):
        """SQLiteデータベースを初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learning_log (
                id TEXT PRIMARY KEY,
                tool TEXT NOT NULL,
                input TEXT,
                raw_output TEXT,
                corrected_output TEXT,
                feedback TEXT,
                tags TEXT,  -- JSON配列
                timestamp TEXT NOT NULL,
                meta TEXT,  -- JSONオブジェクト
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 検索用インデックス
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tool ON learning_log(tool)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_feedback ON learning_log(feedback)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON learning_log(timestamp)
        """)

        conn.commit()
        conn.close()

    def register_correction(
        self,
        tool: str,
        input_data: str,
        raw_output: str,
        corrected_output: str,
        feedback: str = "needs_review",
        tags: Optional[List[str]] = None,
        meta: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        修正履歴を登録

        Args:
            tool: ツール名（例: "pdf_excel", "summary_bot"）
            input_data: ツールへの入力
            raw_output: ツールの生アウトプット
            corrected_output: 修正後の結果
            feedback: フィードバック（"good", "bad", "needs_review"）
            tags: タグリスト
            meta: メタデータ（ユーザー、ソース、ページ番号など）

        Returns:
            登録されたログのID
        """
        log_id = str(uuid4())
        timestamp = datetime.now().isoformat()

        log_entry = {
            "id": log_id,
            "tool": tool,
            "input": input_data,
            "raw_output": raw_output,
            "corrected_output": corrected_output,
            "feedback": feedback,
            "tags": tags or [],
            "timestamp": timestamp,
            "meta": meta or {}
        }

        # JSONLに追記
        try:
            with open(self.jsonl_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"JSONL書き込みエラー: {e}")

        # SQLiteに保存
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO learning_log
                (id, tool, input, raw_output, corrected_output, feedback, tags, timestamp, meta)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                log_id,
                tool,
                input_data,
                raw_output,
                corrected_output,
                feedback,
                json.dumps(tags or []),
                timestamp,
                json.dumps(meta or {})
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"SQLite書き込みエラー: {e}")

        logger.info(f"学習ログを登録しました: {log_id} (tool={tool})")
        return log_id

    def get_best_examples(
        self,
        tool: str,
        task: Optional[str] = None,
        limit: int = 5,
        feedback: str = "good"
    ) -> List[Dict[str, Any]]:
        """
        過去の成功事例を取得

        Args:
            tool: ツール名
            task: タスク名（タグで絞り込み）
            limit: 最大取得数
            feedback: フィードバックフィルタ（"good"推奨）

        Returns:
            成功事例のリスト
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = """
            SELECT id, input, raw_output, corrected_output, tags, meta, timestamp
            FROM learning_log
            WHERE tool = ? AND feedback = ?
        """
        params = [tool, feedback]

        if task:
            # タグにtaskが含まれるものを検索
            query += " AND tags LIKE ?"
            params.append(f'%"{task}"%')

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        results = []

        for row in cursor.fetchall():
            results.append({
                "id": row[0],
                "input": row[1],
                "raw_output": row[2],
                "corrected_output": row[3],
                "tags": json.loads(row[4]) if row[4] else [],
                "meta": json.loads(row[5]) if row[5] else {},
                "timestamp": row[6]
            })

        conn.close()
        return results

    def get_failure_patterns(
        self,
        tool: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        失敗パターンを取得

        Args:
            tool: ツール名
            limit: 最大取得数

        Returns:
            失敗事例のリスト
        """
        return self.get_best_examples(tool, limit=limit, feedback="bad")

    def search_similar_cases(
        self,
        tool: str,
        query_text: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        類似ケースを検索（簡易実装：入力テキストの部分一致）

        Args:
            tool: ツール名
            query_text: 検索クエリ
            limit: 最大取得数

        Returns:
            類似ケースのリスト
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, input, raw_output, corrected_output, tags, meta, timestamp
            FROM learning_log
            WHERE tool = ?
            AND (input LIKE ? OR raw_output LIKE ? OR corrected_output LIKE ?)
            ORDER BY timestamp DESC
            LIMIT ?
        """, (tool, f"%{query_text}%", f"%{query_text}%", f"%{query_text}%", limit))

        results = []
        for row in cursor.fetchall():
            results.append({
                "id": row[0],
                "input": row[1],
                "raw_output": row[2],
                "corrected_output": row[3],
                "tags": json.loads(row[4]) if row[4] else [],
                "meta": json.loads(row[5]) if row[5] else {},
                "timestamp": row[6]
            })

        conn.close()
        return results

    def get_statistics(self, tool: Optional[str] = None) -> Dict[str, Any]:
        """
        統計情報を取得

        Args:
            tool: ツール名（Noneの場合は全体）

        Returns:
            統計情報
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if tool:
            cursor.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN feedback = 'good' THEN 1 ELSE 0 END) as good_count,
                    SUM(CASE WHEN feedback = 'bad' THEN 1 ELSE 0 END) as bad_count,
                    SUM(CASE WHEN feedback = 'needs_review' THEN 1 ELSE 0 END) as review_count
                FROM learning_log
                WHERE tool = ?
            """, (tool,))
        else:
            cursor.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN feedback = 'good' THEN 1 ELSE 0 END) as good_count,
                    SUM(CASE WHEN feedback = 'bad' THEN 1 ELSE 0 END) as bad_count,
                    SUM(CASE WHEN feedback = 'needs_review' THEN 1 ELSE 0 END) as review_count
                FROM learning_log
            """)

        row = cursor.fetchone()
        stats = {
            "total": row[0] or 0,
            "good": row[1] or 0,
            "bad": row[2] or 0,
            "needs_review": row[3] or 0
        }

        conn.close()
        return stats


# === グローバルインスタンス ===
_global_log = None

def get_learning_log() -> LearningLog:
    """グローバルなLearningLogインスタンスを取得"""
    global _global_log
    if _global_log is None:
        _global_log = LearningLog()
    return _global_log









