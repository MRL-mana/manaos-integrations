"""
エピソード記憶システム（中期記憶）
=====================================
短期記憶（IntelligentCache: TTL数分〜数時間）と
長期記憶（Mem0/ChromaDB: 永続）の橋渡しとなる中期記憶層。

ライフサイクル:
  - デフォルトTTL: 24時間（1時間〜7日で設定可能）
  - セッション単位でエピソードをまとめて記録
  - 重要度スコアが閾値を超えたものを長期記憶へ昇格
  - 期限切れエントリは自動クリーンアップ

バックエンド: SQLite（data/episodic_memory.db）
"""

import os
import sqlite3
import uuid
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from pathlib import Path
from dataclasses import dataclass, asdict, field

try:
    from manaos_logger import get_service_logger
    logger = get_service_logger("episodic-memory")
except Exception:
    import logging
    logger = logging.getLogger("episodic-memory")

# デフォルト設定
DEFAULT_TTL_HOURS = int(os.getenv("EPISODIC_MEMORY_TTL_HOURS", "24"))
DEFAULT_IMPORTANCE_THRESHOLD = float(os.getenv("EPISODIC_IMPORTANCE_THRESHOLD", "0.6"))
DEFAULT_DB_PATH = os.getenv(
    "EPISODIC_MEMORY_DB_PATH",
    str(Path(__file__).parent.parent / "data" / "episodic_memory.db"),
)
MAX_SEARCH_RESULTS = 20

# --------------------------------
# データクラス
# --------------------------------

@dataclass
class EpisodicEntry:
    """中期記憶の1エントリ"""
    entry_id: str
    content: str
    session_id: str
    memory_type: str               # "conversation" | "decision" | "observation" | "learning"
    importance_score: float        # 0.0 〜 1.0
    tags: List[str]
    created_at: str
    expires_at: str
    promoted: bool = False         # 長期記憶へ昇格済みか
    promotion_id: Optional[str] = None  # 昇格後の長期記憶ID

    @classmethod
    def create(
        cls,
        content: str,
        session_id: str,
        memory_type: str = "conversation",
        importance_score: float = 0.5,
        tags: Optional[List[str]] = None,
        ttl_hours: int = DEFAULT_TTL_HOURS,
    ) -> "EpisodicEntry":
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        return cls(
            entry_id=str(uuid.uuid4()),
            content=content,
            session_id=session_id,
            memory_type=memory_type,
            importance_score=max(0.0, min(1.0, importance_score)),
            tags=tags or [],
            created_at=now.isoformat(),
            expires_at=(now + timedelta(hours=ttl_hours)).isoformat(),
            promoted=False,
            promotion_id=None,
        )

    def is_expired(self) -> bool:
        return datetime.now(timezone.utc).replace(tzinfo=None) > datetime.fromisoformat(self.expires_at)

    def to_summary(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "content_preview": self.content[:120] + ("..." if len(self.content) > 120 else ""),
            "session_id": self.session_id,
            "memory_type": self.memory_type,
            "importance_score": self.importance_score,
            "tags": self.tags,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "promoted": self.promoted,
        }


# --------------------------------
# メインクラス
# --------------------------------

class EpisodicMemory:
    """
    エピソード記憶システム（中期記憶）

    Usage:
        em = EpisodicMemory()
        em.store("ユーザーが画像生成を依頼した", session_id="sess-001", importance_score=0.7)
        results = em.recall(session_id="sess-001")
        em.cleanup_expired()
    """

    def __init__(self, db_path: Optional[str] = None):
        raw = db_path or DEFAULT_DB_PATH
        # file: URI や :memory: は Path 変換せずそのまま保持
        if raw == ":memory:" or raw.startswith("file:"):
            self.db_path = raw
            # インメモリの場合は接続を閉じるとデータが消えるため、永続接続を保持
            self._persistent_conn: Optional[sqlite3.Connection] = sqlite3.connect(
                raw, uri=True, check_same_thread=False, timeout=10
            )
            self._persistent_conn.row_factory = sqlite3.Row
        else:
            self.db_path = Path(raw)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._persistent_conn = None
        self._init_db()

    # --------------------------------
    # DB初期化
    # --------------------------------

    def _init_db(self) -> None:
        """SQLiteスキーマを初期化（べき等）"""
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS episodic_entries (
                    entry_id        TEXT PRIMARY KEY,
                    content         TEXT NOT NULL,
                    session_id      TEXT NOT NULL,
                    memory_type     TEXT NOT NULL DEFAULT 'conversation',
                    importance_score REAL NOT NULL DEFAULT 0.5,
                    tags            TEXT NOT NULL DEFAULT '[]',
                    created_at      TEXT NOT NULL,
                    expires_at      TEXT NOT NULL,
                    promoted        INTEGER NOT NULL DEFAULT 0,
                    promotion_id    TEXT
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_session ON episodic_entries(session_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_expires ON episodic_entries(expires_at)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_importance ON episodic_entries(importance_score DESC)"
            )

    def _conn(self) -> sqlite3.Connection:
        """接続を返す。インメモリの場合は永続接続を再利用。"""
        if self._persistent_conn is not None:
            return self._persistent_conn
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    # --------------------------------
    # CRUD
    # --------------------------------

    def store(
        self,
        content: str,
        session_id: str,
        memory_type: str = "conversation",
        importance_score: float = 0.5,
        tags: Optional[List[str]] = None,
        ttl_hours: int = DEFAULT_TTL_HOURS,
    ) -> EpisodicEntry:
        """
        エピソードを保存する。

        Args:
            content: 記憶する内容
            session_id: セッションID（関連エピソードをグループ化）
            memory_type: 記憶タイプ（conversation / decision / observation / learning）
            importance_score: 重要度スコア（0.0〜1.0）
            tags: タグリスト
            ttl_hours: 有効期間（時間）

        Returns:
            保存されたEpisodicEntry
        """
        entry = EpisodicEntry.create(
            content=content,
            session_id=session_id,
            memory_type=memory_type,
            importance_score=importance_score,
            tags=tags or [],
            ttl_hours=ttl_hours,
        )
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO episodic_entries
                  (entry_id, content, session_id, memory_type, importance_score,
                   tags, created_at, expires_at, promoted, promotion_id)
                VALUES (?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    entry.entry_id,
                    entry.content,
                    entry.session_id,
                    entry.memory_type,
                    entry.importance_score,
                    json.dumps(entry.tags, ensure_ascii=False),
                    entry.created_at,
                    entry.expires_at,
                    int(entry.promoted),
                    entry.promotion_id,
                ),
            )
        logger.debug(
            f"[EpisodicMemory] stored entry_id={entry.entry_id} "
            f"session={session_id} importance={importance_score:.2f}"
        )
        return entry

    def recall(
        self,
        session_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        min_importance: float = 0.0,
        include_promoted: bool = True,
        include_expired: bool = False,
        limit: int = 20,
    ) -> List[EpisodicEntry]:
        """
        条件でエピソードを取得する。

        Args:
            session_id: 絞り込むセッションID（Noneで全セッション）
            memory_type: 絞り込む記憶タイプ（Noneで全タイプ）
            min_importance: 最低重要度スコア
            include_promoted: 昇格済みエントリを含むか
            include_expired: 期限切れエントリを含むか
            limit: 最大件数

        Returns:
            EpisodicEntry のリスト（created_at降順）
        """
        conditions = ["importance_score >= ?"]
        params: list = [min_importance]

        if session_id is not None:
            conditions.append("session_id = ?")
            params.append(session_id)

        if memory_type is not None:
            conditions.append("memory_type = ?")
            params.append(memory_type)

        if not include_promoted:
            conditions.append("promoted = 0")

        if not include_expired:
            conditions.append("expires_at > ?")
            params.append(datetime.now(timezone.utc).replace(tzinfo=None).isoformat())

        where = " AND ".join(conditions)
        params.append(max(1, min(limit, MAX_SEARCH_RESULTS * 2)))

        with self._conn() as conn:
            rows = conn.execute(
                f"SELECT * FROM episodic_entries WHERE {where} ORDER BY created_at DESC LIMIT ?",
                params,
            ).fetchall()

        return [self._row_to_entry(r) for r in rows]

    def search(
        self,
        query: str,
        session_id: Optional[str] = None,
        min_importance: float = 0.0,
        limit: int = 10,
    ) -> List[EpisodicEntry]:
        """
        キーワード検索でエピソードを取得する（SQLite FTS簡易版）。

        Args:
            query: 検索文字列
            session_id: 絞り込むセッションID
            min_importance: 最低重要度スコア
            limit: 最大件数

        Returns:
            EpisodicEntry のリスト
        """
        conditions = [
            "content LIKE ?",
            "importance_score >= ?",
            "expires_at > ?",
        ]
        params: list = [
            f"%{query}%",
            min_importance,
            datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
        ]

        if session_id is not None:
            conditions.append("session_id = ?")
            params.append(session_id)

        where = " AND ".join(conditions)
        params.append(max(1, min(limit, MAX_SEARCH_RESULTS)))

        with self._conn() as conn:
            rows = conn.execute(
                f"SELECT * FROM episodic_entries WHERE {where} "
                f"ORDER BY importance_score DESC, created_at DESC LIMIT ?",
                params,
            ).fetchall()

        return [self._row_to_entry(r) for r in rows]

    def get(self, entry_id: str) -> Optional[EpisodicEntry]:
        """entry_id でエントリを1件取得。"""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM episodic_entries WHERE entry_id = ?", (entry_id,)
            ).fetchone()
        return self._row_to_entry(row) if row else None

    # --------------------------------
    # 昇格（長期記憶へ）
    # --------------------------------

    def promote_to_longterm(
        self,
        entry_id: str,
        longterm_store_fn=None,
    ) -> bool:
        """
        エントリを長期記憶へ昇格する。

        Args:
            entry_id: 昇格するエントリのID
            longterm_store_fn: 長期記憶への書き込み関数
                               fn(content: str, metadata: dict) -> str (promotion_id)
                               Noneの場合はフラグのみ更新

        Returns:
            昇格成功かどうか
        """
        entry = self.get(entry_id)
        if entry is None:
            logger.warning(f"[EpisodicMemory] promote: entry not found: {entry_id}")
            return False

        if entry.promoted:
            logger.debug(f"[EpisodicMemory] already promoted: {entry_id}")
            return True

        promotion_id = None
        if longterm_store_fn is not None:
            try:
                promotion_id = longterm_store_fn(
                    entry.content,
                    {
                        "source": "episodic_promotion",
                        "session_id": entry.session_id,
                        "memory_type": entry.memory_type,
                        "importance_score": entry.importance_score,
                        "tags": entry.tags,
                        "original_created_at": entry.created_at,
                        "original_entry_id": entry.entry_id,
                    },
                )
            except Exception as exc:
                logger.error(f"[EpisodicMemory] promotion fn error: {exc}")
                return False

        if promotion_id is None:
            promotion_id = f"episodic_promoted_{entry_id}"

        with self._conn() as conn:
            conn.execute(
                "UPDATE episodic_entries SET promoted=1, promotion_id=? WHERE entry_id=?",
                (promotion_id, entry_id),
            )

        logger.info(
            f"[EpisodicMemory] promoted entry_id={entry_id} → promotion_id={promotion_id}"
        )
        return True

    def auto_promote_high_importance(
        self,
        threshold: float = DEFAULT_IMPORTANCE_THRESHOLD,
        longterm_store_fn=None,
        session_id: Optional[str] = None,
    ) -> int:
        """
        重要度が閾値以上の未昇格エントリを自動昇格する。

        Returns:
            昇格件数
        """
        entries = self.recall(
            session_id=session_id,
            min_importance=threshold,
            include_promoted=False,
            include_expired=True,
        )
        count = 0
        for e in entries:
            if self.promote_to_longterm(e.entry_id, longterm_store_fn):
                count += 1
        if count > 0:
            logger.info(f"[EpisodicMemory] auto_promoted {count} entries (threshold={threshold})")
        return count

    # --------------------------------
    # クリーンアップ
    # --------------------------------

    def cleanup_expired(self, also_promoted: bool = False) -> int:
        """
        期限切れエントリを削除する。

        Args:
            also_promoted: 昇格済みの期限切れも削除するか（デフォルト: False、保持）

        Returns:
            削除件数
        """
        now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        with self._conn() as conn:
            if also_promoted:
                result = conn.execute(
                    "DELETE FROM episodic_entries WHERE expires_at <= ?", (now,)
                )
            else:
                result = conn.execute(
                    "DELETE FROM episodic_entries WHERE expires_at <= ? AND promoted = 0",
                    (now,),
                )
            deleted = result.rowcount
        if deleted > 0:
            logger.info(f"[EpisodicMemory] cleanup removed {deleted} expired entries")
        return deleted

    # --------------------------------
    # 統計・ユーティリティ
    # --------------------------------

    def stats(self) -> Dict[str, Any]:
        """記憶ストアの統計情報を返す。"""
        now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        with self._conn() as conn:
            total = conn.execute("SELECT COUNT(*) FROM episodic_entries").fetchone()[0]
            active = conn.execute(
                "SELECT COUNT(*) FROM episodic_entries WHERE expires_at > ?", (now,)
            ).fetchone()[0]
            promoted = conn.execute(
                "SELECT COUNT(*) FROM episodic_entries WHERE promoted = 1"
            ).fetchone()[0]
            by_type = conn.execute(
                "SELECT memory_type, COUNT(*) as cnt FROM episodic_entries GROUP BY memory_type"
            ).fetchall()
            avg_importance = conn.execute(
                "SELECT AVG(importance_score) FROM episodic_entries WHERE expires_at > ?"
                , (now,)
            ).fetchone()[0]

        return {
            "total_entries": total,
            "active_entries": active,
            "expired_entries": total - active,
            "promoted_entries": promoted,
            "by_type": {row["memory_type"]: row["cnt"] for row in by_type},
            "avg_importance_active": round(avg_importance or 0.0, 3),
            "db_path": str(self.db_path),
        }

    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """セッションのサマリーを返す。"""
        entries = self.recall(session_id=session_id, include_expired=True, limit=100)
        if not entries:
            return {"session_id": session_id, "entries": 0}
        return {
            "session_id": session_id,
            "entries": len(entries),
            "types": list({e.memory_type for e in entries}),
            "promoted": sum(1 for e in entries if e.promoted),
            "max_importance": max(e.importance_score for e in entries),
            "avg_importance": round(
                sum(e.importance_score for e in entries) / len(entries), 3
            ),
            "first_at": entries[-1].created_at,
            "last_at": entries[0].created_at,
            "previews": [e.to_summary() for e in entries[:5]],
        }

    # --------------------------------
    # 内部ヘルパー
    # --------------------------------

    def _row_to_entry(self, row: sqlite3.Row) -> EpisodicEntry:
        return EpisodicEntry(
            entry_id=row["entry_id"],
            content=row["content"],
            session_id=row["session_id"],
            memory_type=row["memory_type"],
            importance_score=row["importance_score"],
            tags=json.loads(row["tags"]),
            created_at=row["created_at"],
            expires_at=row["expires_at"],
            promoted=bool(row["promoted"]),
            promotion_id=row["promotion_id"],
        )


# --------------------------------
# モジュールレベルシングルトン
# --------------------------------

_default_instance: Optional[EpisodicMemory] = None


def get_episodic_memory(db_path: Optional[str] = None) -> EpisodicMemory:
    """デフォルトの EpisodicMemory インスタンスを取得（シングルトン）。"""
    global _default_instance
    if _default_instance is None:
        _default_instance = EpisodicMemory(db_path=db_path)
    return _default_instance
