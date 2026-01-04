#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧠 RAG記憶進化システム（最適化版）
データベース接続プールとキャッシュシステムを使用
"""

import os
import json
import httpx
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from collections import defaultdict

# 統一モジュールのインポート
from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from manaos_timeout_config import get_timeout_config
from manaos_config_validator import ConfigValidator

# 最適化モジュールのインポート
from database_connection_pool import get_pool
from unified_cache_system import get_unified_cache

# ロガーの初期化
logger = get_logger(__name__)

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("RAGMemory")

# タイムアウト設定の取得
timeout_config = get_timeout_config()

# 設定ファイル検証の初期化
config_validator = ConfigValidator("RAGMemory")

# キャッシュシステムの取得
cache_system = get_unified_cache()


@dataclass
class MemoryEntry:
    """記憶エントリ"""
    entry_id: str
    content: str
    importance_score: float  # 0.0-1.0
    content_hash: str  # 重複チェック用
    created_at: str
    updated_at: str
    access_count: int
    last_accessed_at: str
    related_entries: List[str]  # 関連エントリID
    temporal_context: Dict[str, Any]  # 時系列コンテキスト
    metadata: Dict[str, Any]


class RAGMemoryOptimized:
    """RAG記憶進化システム（最適化版）"""
    
    def __init__(
        self,
        db_path: Optional[Path] = None,
        ollama_url: str = "http://localhost:11434",
        model: str = "qwen2.5:14b",
        config_path: Optional[Path] = None
    ):
        """
        初期化
        
        Args:
            db_path: SQLiteデータベースパス
            model: 重要度判定用のモデル
            config_path: 設定ファイルのパス
        """
        self.ollama_url = ollama_url
        self.model = model
        self.config_path = config_path or Path(__file__).parent / "rag_memory_config.json"
        self.config = self._load_config()
        
        # データベース初期化
        self.db_path = db_path or Path(__file__).parent / "rag_memory.db"
        
        # データベース接続プールを使用
        self.db_pool = get_pool(str(self.db_path), max_connections=10)
        self._init_database()
        
        # 重複チェック用のハッシュマップ（キャッシュから読み込み）
        self.content_hash_map: Dict[str, str] = {}
        self._load_content_hashes()
        
        logger.info(f"✅ RAG記憶進化システム（最適化版）初期化完了")
    
    def _load_config(self) -> Dict[str, Any]:
        """設定を読み込む（config_cacheを使用）"""
        from config_cache import get_config_cache
        config_cache = get_config_cache()
        
        return config_cache.get_config(
            str(self.config_path),
            default=self._get_default_config()
        )
    
    def _get_default_config(self) -> Dict[str, Any]:
        """デフォルト設定"""
        return {
            "ollama_url": "http://localhost:11434",
            "model": "qwen2.5:14b",
            "importance_threshold": 0.6,
            "duplicate_threshold": 0.9,
            "temporal_window_days": 30,
            "max_entries": 10000
        }
    
    def _init_database(self):
        """データベースを初期化（接続プール使用）"""
        with self.db_pool.get_connection() as conn:
            cursor = conn.cursor()
            
            # メモリエントリテーブル
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memory_entries (
                    entry_id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    importance_score REAL NOT NULL,
                    content_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    access_count INTEGER DEFAULT 0,
                    last_accessed_at TEXT,
                    related_entries TEXT,
                    temporal_context TEXT,
                    metadata TEXT
                )
            """)
            
            # インデックス作成
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_importance ON memory_entries(importance_score DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_content_hash ON memory_entries(content_hash)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON memory_entries(created_at DESC)")
            
            conn.commit()
        
        logger.info(f"✅ データベース初期化完了: {self.db_path}")
    
    def _load_content_hashes(self):
        """コンテンツハッシュを読み込む（接続プール使用）"""
        # キャッシュから読み込み
        cached_hashes = cache_system.get("content_hashes", db_path=str(self.db_path))
        if cached_hashes:
            self.content_hash_map = cached_hashes
            logger.info(f"✅ コンテンツハッシュ読み込み完了（キャッシュ）: {len(self.content_hash_map)}件")
            return
        
        # データベースから読み込み
        with self.db_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT entry_id, content_hash FROM memory_entries")
            for row in cursor.fetchall():
                entry_id, content_hash = row
                self.content_hash_map[content_hash] = entry_id
        
        # キャッシュに保存
        cache_system.set("content_hashes", self.content_hash_map, db_path=str(self.db_path), ttl_seconds=3600)
        logger.info(f"✅ コンテンツハッシュ読み込み完了: {len(self.content_hash_map)}件")
    
    def _calculate_content_hash(self, content: str) -> str:
        """コンテンツハッシュを計算"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def _calculate_importance_score(self, content: str, context: Optional[Dict[str, Any]] = None) -> float:
        """
        重要度スコアを計算
        
        Args:
            content: コンテンツ
            context: コンテキスト情報
        
        Returns:
            float: 重要度スコア (0.0-1.0)
        """
        # ルールベースの重要度判定
        importance_keywords = [
            "重要", "必須", "必要", "緊急", "優先",
            "完了", "成功", "失敗", "エラー",
            "設定", "変更", "更新", "削除"
        ]
        
        score = 0.5  # ベーススコア
        
        # キーワードによる重要度調整
        content_lower = content.lower()
        for keyword in importance_keywords:
            if keyword in content_lower:
                score += 0.1
        
        # コンテキストによる調整
        if context:
            if context.get("priority") == "high":
                score += 0.2
            if context.get("type") == "error":
                score += 0.15
        
        return min(1.0, max(0.0, score))
    
    def get_memory(self, entry_id: str) -> Optional[MemoryEntry]:
        """
        記憶を取得（キャッシュ使用）
        
        Args:
            entry_id: エントリID
        
        Returns:
            MemoryEntry（存在する場合）、None（存在しない場合）
        """
        # キャッシュから取得
        cached_entry = cache_system.get("memory_entry", entry_id=entry_id)
        if cached_entry:
            return MemoryEntry(**cached_entry)
        
        # データベースから取得
        with self.db_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM memory_entries WHERE entry_id = ?",
                (entry_id,)
            )
            row = cursor.fetchone()
            
            if row:
                entry = self._row_to_entry(row)
                # キャッシュに保存
                cache_system.set("memory_entry", asdict(entry), entry_id=entry_id, ttl_seconds=3600)
                return entry
        
        return None
    
    def _row_to_entry(self, row: Tuple) -> MemoryEntry:
        """データベース行をMemoryEntryに変換"""
        return MemoryEntry(
            entry_id=row[0],
            content=row[1],
            importance_score=row[2],
            content_hash=row[3],
            created_at=row[4],
            updated_at=row[5],
            access_count=row[6],
            last_accessed_at=row[7] or "",
            related_entries=json.loads(row[8] or "[]"),
            temporal_context=json.loads(row[9] or "{}"),
            metadata=json.loads(row[10] or "{}")
        )
    
    def add_memory(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        force_importance: Optional[float] = None
    ) -> MemoryEntry:
        """
        記憶を追加（最適化版）
        
        Args:
            content: 記憶するコンテンツ
            metadata: メタデータ
            force_importance: 強制的な重要度スコア
        
        Returns:
            MemoryEntry: 記憶エントリ
        """
        # 重複チェック
        duplicate_id = self._check_duplicate(content)
        if duplicate_id:
            logger.info(f"⚠️ 重複エントリ検出: {duplicate_id}")
            self._merge_entries(duplicate_id, content, metadata or {})
            return self.get_memory(duplicate_id)
        
        # 重要度スコアを計算
        if force_importance is not None:
            importance_score = force_importance
        else:
            importance_score = self._calculate_importance_score(content, metadata)
        
        # 重要度が閾値以下の場合は保存しない
        threshold = self.config.get("importance_threshold", 0.6)
        if importance_score < threshold:
            logger.info(f"重要度が低いため保存しません: {importance_score:.2f} < {threshold}")
            return None
        
        # エントリを作成
        entry_id = hashlib.sha256(f"{content}{datetime.now().isoformat()}".encode()).hexdigest()[:16]
        content_hash = self._calculate_content_hash(content)
        now = datetime.now().isoformat()
        
        entry = MemoryEntry(
            entry_id=entry_id,
            content=content,
            importance_score=importance_score,
            content_hash=content_hash,
            created_at=now,
            updated_at=now,
            access_count=0,
            last_accessed_at="",
            related_entries=[],
            temporal_context=self._get_temporal_context(content),
            metadata=metadata or {}
        )
        
        # データベースに保存（接続プール使用）
        with self.db_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO memory_entries (
                    entry_id, content, importance_score, content_hash,
                    created_at, updated_at, access_count,
                    related_entries, temporal_context, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry.entry_id,
                entry.content,
                entry.importance_score,
                entry.content_hash,
                entry.created_at,
                entry.updated_at,
                entry.access_count,
                json.dumps(entry.related_entries),
                json.dumps(entry.temporal_context),
                json.dumps(entry.metadata)
            ))
            conn.commit()
        
        # ハッシュマップを更新
        self.content_hash_map[content_hash] = entry_id
        
        # キャッシュに保存
        cache_system.set("memory_entry", asdict(entry), entry_id=entry_id, ttl_seconds=3600)
        cache_system.set("content_hashes", self.content_hash_map, db_path=str(self.db_path), ttl_seconds=3600)
        
        logger.info(f"✅ 記憶を追加: {entry_id} (重要度: {importance_score:.2f})")
        return entry
    
    def _check_duplicate(self, content: str) -> Optional[str]:
        """重複チェック"""
        content_hash = self._calculate_content_hash(content)
        return self.content_hash_map.get(content_hash)
    
    def _merge_entries(self, existing_id: str, new_content: str, new_metadata: Dict[str, Any]):
        """エントリを統合"""
        existing = self.get_memory(existing_id)
        if existing:
            # アクセス数を増やす
            existing.access_count += 1
            existing.last_accessed_at = datetime.now().isoformat()
            existing.updated_at = datetime.now().isoformat()
            
            # メタデータをマージ
            existing.metadata.update(new_metadata)
            
            # データベースを更新
            with self.db_pool.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE memory_entries
                    SET access_count = ?, last_accessed_at = ?, updated_at = ?, metadata = ?
                    WHERE entry_id = ?
                """, (
                    existing.access_count,
                    existing.last_accessed_at,
                    existing.updated_at,
                    json.dumps(existing.metadata),
                    existing_id
                ))
                conn.commit()
            
            # キャッシュを更新
            cache_system.set("memory_entry", asdict(existing), entry_id=existing_id, ttl_seconds=3600)
    
    def _get_temporal_context(self, content: str) -> Dict[str, Any]:
        """時系列コンテキストを取得"""
        return {
            "timestamp": datetime.now().isoformat(),
            "day_of_week": datetime.now().strftime("%A"),
            "hour": datetime.now().hour
        }
    
    def search_memories(
        self,
        query: str,
        limit: int = 10,
        min_importance: float = 0.0
    ) -> List[MemoryEntry]:
        """
        記憶を検索（最適化版）
        
        Args:
            query: 検索クエリ
            limit: 最大件数
            min_importance: 最小重要度
        
        Returns:
            記憶エントリのリスト
        """
        # キャッシュから取得
        cache_key = f"search:{query}:{limit}:{min_importance}"
        cached_results = cache_system.get("memory_search", cache_key=cache_key)
        if cached_results:
            return [MemoryEntry(**e) for e in cached_results]
        
        # データベースから検索
        with self.db_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM memory_entries
                WHERE importance_score >= ? AND content LIKE ?
                ORDER BY importance_score DESC, access_count DESC
                LIMIT ?
            """, (min_importance, f"%{query}%", limit))
            
            results = []
            for row in cursor.fetchall():
                results.append(self._row_to_entry(row))
        
        # キャッシュに保存
        cache_system.set("memory_search", [asdict(e) for e in results], cache_key=cache_key, ttl_seconds=300)
        
        return results


def main():
    """テスト用メイン関数"""
    print("RAG記憶進化システム（最適化版）テスト")
    print("=" * 60)
    
    memory = RAGMemoryOptimized()
    
    # 記憶を追加
    entry = memory.add_memory(
        "テスト記憶",
        metadata={"type": "test"}
    )
    print(f"記憶を追加: {entry.entry_id}")
    
    # 記憶を検索
    results = memory.search_memories("テスト", limit=5)
    print(f"検索結果: {len(results)}件")


if __name__ == "__main__":
    main()

