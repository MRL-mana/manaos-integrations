#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧠 LessonsRecorder
==================
ユーザーからの指摘・修正パターンを記録・参照するモジュール。

Boris Cherny 式の自己改善ループ:
  ユーザーが「違う」「修正して」などと入力
      → record_lesson() で指摘を RAGv2 + EpisodicMemory に保存
      → search_lessons() で過去の失敗パターンを参照
      → 同じミスを繰り返さない

使い方:
    recorder = get_lessons_recorder()

    # 指摘を記録
    entry = recorder.record_lesson(
        instruction="テキストが長すぎた。3行以内に収めること",
        category="output_format",
    )

    # 過去の教訓を検索
    lessons = recorder.search_lessons("出力の長さ")

    # セッション開始時に全教訓を注入用テキストで取得
    ctx = recorder.get_context_text(limit=10)
"""

from __future__ import annotations

import json
import sqlite3
import hashlib
import threading
import os
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── ロガー（依存なし fallback）──────────────────────────────────────────────

try:
    from manaos_logger import get_service_logger
    _log = get_service_logger("lessons-recorder")
except Exception:
    import logging
    _log = logging.getLogger("lessons_recorder")

# ── デフォルト設定 ─────────────────────────────────────────────────────────

DEFAULT_DB_PATH = os.getenv(
    "LESSONS_DB_PATH",
    str(Path(__file__).parent.parent.parent / "data" / "lessons.db"),
)

# 指摘を検知するキーワード（記事の Boris Cherny 式）
CORRECTION_KEYWORDS: List[str] = [
    "違う", "ちがう", "違います", "異なる",
    "修正して", "直して", "やり直し", "やりなおし",
    "それじゃない", "そうじゃない", "ちがうよ",
    "間違い", "間違え", "まちがい",
    "ダメ", "だめ", "駄目",
    "not correct", "wrong", "fix this", "redo",
]

# カテゴリ一覧
CATEGORIES = [
    "output_format",  # 出力形式（長さ・構造・言語など）
    "behavior",       # 振る舞い（確認せず実行・過剰提案など）
    "technical",      # 技術的な間違い（API・コード・設定）
    "context",        # コンテキスト読み違え（要件・意図の誤解）
    "other",          # その他
]


# ── データクラス ───────────────────────────────────────────────────────────

@dataclass
class Lesson:
    """1件の教訓エントリ"""
    lesson_id: str
    instruction: str          # 教訓の内容
    category: str             # カテゴリ
    trigger_text: str         # 指摘を検知した元のテキスト（省略可）
    session_id: str           # 記録したセッションID
    created_at: str
    access_count: int = 0
    last_accessed_at: str = ""
    tags: List[str] = field(default_factory=list)

    @staticmethod
    def make_id(instruction: str) -> str:
        return hashlib.sha256(instruction.encode()).hexdigest()[:12]


# ── LessonsRecorder ────────────────────────────────────────────────────────

class LessonsRecorder:
    """
    指摘・修正パターンを SQLite に永続化するレコーダー。

    RAGv2 / EpisodicMemory との統合:
        - record_lesson() を呼ぶと SQLite に保存
        - RAGv2 に bridge する場合は record_lesson() の戻り値 (Lesson) を
          呼び元で add_memory() に渡す（疎結合）
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path or DEFAULT_DB_PATH)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        # :memory: の場合は永続接続を保持
        self._persistent_conn: Optional[sqlite3.Connection] = None
        if str(self.db_path) == ":memory:":
            self._persistent_conn = sqlite3.connect(":memory:", check_same_thread=False)
        self._init_db()

    # ── 内部: DB 接続 ──────────────────────────────────────────────────────

    @contextmanager
    def _conn(self):
        if self._persistent_conn is not None:
            yield self._persistent_conn
        else:
            conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            try:
                yield conn
                conn.commit()
            finally:
                conn.close()

    def _init_db(self):
        with self._conn() as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS lessons (
                    lesson_id       TEXT PRIMARY KEY,
                    instruction     TEXT NOT NULL,
                    category        TEXT NOT NULL DEFAULT 'other',
                    trigger_text    TEXT NOT NULL DEFAULT '',
                    session_id      TEXT NOT NULL DEFAULT '',
                    created_at      TEXT NOT NULL,
                    access_count    INTEGER NOT NULL DEFAULT 0,
                    last_accessed_at TEXT NOT NULL DEFAULT '',
                    tags            TEXT NOT NULL DEFAULT '[]'
                )
            """)
            c.execute("""
                CREATE INDEX IF NOT EXISTS idx_lessons_category
                ON lessons(category)
            """)
            c.execute("""
                CREATE INDEX IF NOT EXISTS idx_lessons_created
                ON lessons(created_at)
            """)
            if self._persistent_conn:
                self._persistent_conn.commit()

    # ── 公開 API ───────────────────────────────────────────────────────────

    def record_lesson(
        self,
        instruction: str,
        category: str = "other",
        trigger_text: str = "",
        session_id: str = "",
        tags: Optional[List[str]] = None,
    ) -> Lesson:
        """
        教訓を記録する。同一内容（instruction ハッシュ）は重複せず
        access_count をインクリメントしてマージする。

        Args:
            instruction : 教訓の内容（「3行以内にまとめよ」等）
            category    : カテゴリ (output_format / behavior / technical / context / other)
            trigger_text: 指摘を引き起こした元テキスト（省略可）
            session_id  : セッションID
            tags        : タグリスト

        Returns:
            保存・更新された Lesson
        """
        if category not in CATEGORIES:
            category = "other"

        lesson_id = Lesson.make_id(instruction)
        now = datetime.now(timezone.utc).isoformat()
        tags_json = json.dumps(tags or [], ensure_ascii=False)

        with self._lock:
            with self._conn() as c:
                existing = c.execute(
                    "SELECT * FROM lessons WHERE lesson_id = ?", (lesson_id,)
                ).fetchone()

                if existing:
                    # 重複 → access_count をインクリメント
                    c.execute(
                        "UPDATE lessons SET access_count = access_count + 1, "
                        "last_accessed_at = ? WHERE lesson_id = ?",
                        (now, lesson_id),
                    )
                    if self._persistent_conn:
                        self._persistent_conn.commit()
                    lesson = self._row_to_lesson(
                        c.execute(
                            "SELECT * FROM lessons WHERE lesson_id = ?", (lesson_id,)
                        ).fetchone()
                    )
                    _log.info(f"教訓を更新 (重複): {lesson_id} (回数: {lesson.access_count})")
                    return lesson
                else:
                    c.execute(
                        """INSERT INTO lessons
                           (lesson_id, instruction, category, trigger_text,
                            session_id, created_at, access_count, last_accessed_at, tags)
                           VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)""",
                        (lesson_id, instruction, category, trigger_text,
                         session_id, now, now, tags_json),
                    )
                    if self._persistent_conn:
                        self._persistent_conn.commit()
                    lesson = Lesson(
                        lesson_id=lesson_id,
                        instruction=instruction,
                        category=category,
                        trigger_text=trigger_text,
                        session_id=session_id,
                        created_at=now,
                        access_count=1,
                        last_accessed_at=now,
                        tags=tags or [],
                    )
                    _log.info(f"教訓を新規登録: {lesson_id} [{category}]")
                    return lesson

    def search_lessons(
        self,
        query: str = "",
        category: Optional[str] = None,
        limit: int = 20,
    ) -> List[Lesson]:
        """
        キーワードでテキスト検索。query 空の場合は全件 (access_count 降順)。

        Args:
            query   : 検索文字列
            category: カテゴリでフィルタ
            limit   : 最大件数

        Returns:
            Lesson のリスト
        """
        with self._conn() as c:
            if query and category:
                rows = c.execute(
                    "SELECT * FROM lessons WHERE category = ? AND instruction LIKE ? "
                    "ORDER BY access_count DESC, created_at DESC LIMIT ?",
                    (category, f"%{query}%", limit),
                ).fetchall()
            elif query:
                rows = c.execute(
                    "SELECT * FROM lessons WHERE instruction LIKE ? OR trigger_text LIKE ? "
                    "ORDER BY access_count DESC, created_at DESC LIMIT ?",
                    (f"%{query}%", f"%{query}%", limit),
                ).fetchall()
            elif category:
                rows = c.execute(
                    "SELECT * FROM lessons WHERE category = ? "
                    "ORDER BY access_count DESC, created_at DESC LIMIT ?",
                    (category, limit),
                ).fetchall()
            else:
                rows = c.execute(
                    "SELECT * FROM lessons ORDER BY access_count DESC, created_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        return [self._row_to_lesson(r) for r in rows]

    def get_context_text(
        self,
        limit: int = 10,
        category: Optional[str] = None,
    ) -> str:
        """
        セッション開始時にコンテキスト注入するためのテキストを生成する。

        Returns:
            フォーマット済みテキスト（空の場合は空文字列）
        """
        lessons = self.search_lessons(category=category, limit=limit)
        if not lessons:
            return ""

        lines = ["## 過去の指摘・教訓（繰り返し注意）\n"]
        for i, lesson in enumerate(lessons, 1):
            count_note = f"（{lesson.access_count}回指摘）" if lesson.access_count > 1 else ""
            lines.append(f"{i}. [{lesson.category}] {lesson.instruction}{count_note}")
        return "\n".join(lines)

    def delete_lesson(self, lesson_id: str) -> bool:
        """教訓を削除する。Returns: 削除成功かどうか"""
        with self._lock:
            with self._conn() as c:
                c.execute("DELETE FROM lessons WHERE lesson_id = ?", (lesson_id,))
                if self._persistent_conn:
                    self._persistent_conn.commit()
                return True

    def stats(self) -> Dict[str, Any]:
        """統計情報を返す"""
        with self._conn() as c:
            total = c.execute("SELECT COUNT(*) FROM lessons").fetchone()[0]
            by_cat = {
                r[0]: r[1]
                for r in c.execute(
                    "SELECT category, COUNT(*) FROM lessons GROUP BY category"
                ).fetchall()
            }
            top_repeated = c.execute(
                "SELECT lesson_id, instruction, access_count FROM lessons "
                "ORDER BY access_count DESC LIMIT 5"
            ).fetchall()
        return {
            "total": total,
            "by_category": by_cat,
            "top_repeated": [
                {"id": r[0], "instruction": r[1][:60], "count": r[2]}
                for r in top_repeated
            ],
            "db_path": str(self.db_path),
        }

    # ── ユーティリティ ─────────────────────────────────────────────────────

    @staticmethod
    def detect_correction(text: str) -> bool:
        """テキストに指摘キーワードが含まれるか判定する"""
        lower = text.lower()
        return any(kw.lower() in lower for kw in CORRECTION_KEYWORDS)

    @staticmethod
    def extract_lesson(correction_text: str) -> str:
        """
        指摘テキストから教訓文を抽出する簡易ルール。
        改行・句点で区切り最も情報量の多い文を返す。
        """
        import re
        sentences = re.split(r"[。\n\.!！?？]", correction_text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 5]
        if not sentences:
            return correction_text.strip()
        # 最長の文を教訓として採用
        return max(sentences, key=len)

    def _row_to_lesson(self, row: tuple) -> Lesson:
        return Lesson(
            lesson_id=row[0],
            instruction=row[1],
            category=row[2],
            trigger_text=row[3],
            session_id=row[4],
            created_at=row[5],
            access_count=row[6],
            last_accessed_at=row[7],
            tags=json.loads(row[8]) if row[8] else [],
        )


# ── シングルトン ────────────────────────────────────────────────────────────

_instance: Optional[LessonsRecorder] = None
_instance_lock = threading.Lock()


def get_lessons_recorder(db_path: Optional[str] = None) -> LessonsRecorder:
    """プロセス内でシングルトンを返す"""
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = LessonsRecorder(db_path)
    return _instance
