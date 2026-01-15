#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧠 RAG記憶進化システム v2（強化版）
セマンティック検索・記憶の関連付け・重要度の動的更新
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
import math

# 統一モジュールのインポート
from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from manaos_timeout_config import get_timeout_config

# 最適化モジュールのインポート
from database_connection_pool import get_pool
from unified_cache_system import get_unified_cache

# ロガーの初期化
logger = get_logger(__name__)

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("RAGMemoryV2")

# タイムアウト設定の取得
timeout_config = get_timeout_config()

# キャッシュシステムの取得
cache_system = get_unified_cache()


@dataclass
class MemoryEntry:
    """記憶エントリ"""
    entry_id: str
    content: str
    importance_score: float  # 0.0-1.0
    content_hash: str
    created_at: str
    updated_at: str
    access_count: int
    last_accessed_at: str
    related_entries: List[str]
    temporal_context: Dict[str, Any]
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None  # ベクトル埋め込み（新規）


class RAGMemoryEnhancedV2:
    """RAG記憶進化システム v2（強化版）"""
    
    def __init__(
        self,
        db_path: Optional[Path] = None,
        ollama_url: str = "http://localhost:11434",
        model: str = "qwen2.5:14b",
        embedding_model: str = "nomic-embed-text"
    ):
        """
        初期化
        
        Args:
            db_path: SQLiteデータベースパス
            model: 重要度判定用のモデル
            embedding_model: 埋め込みモデル
        """
        self.ollama_url = ollama_url
        self.model = model
        self.embedding_model = embedding_model
        
        # データベース初期化
        self.db_path = db_path or Path(__file__).parent / "rag_memory_v2.db"
        self.db_pool = get_pool(str(self.db_path), max_connections=10)
        self._init_database()
        
        # 重複チェック用のハッシュマップ
        self.content_hash_map: Dict[str, str] = {}
        self._load_content_hashes()
        
        logger.info(f"✅ RAG記憶進化システム v2（強化版）初期化完了")
    
    def _init_database(self):
        """データベースを初期化（埋め込みカラム追加）"""
        with self.db_pool.get_connection() as conn:
            cursor = conn.cursor()
            
            # メモリエントリテーブル（埋め込みカラム追加）
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
                    metadata TEXT,
                    embedding TEXT
                )
            """)
            
            # 埋め込みカラムが存在しない場合は追加
            try:
                cursor.execute("ALTER TABLE memory_entries ADD COLUMN embedding TEXT")
            except:
                pass  # 既に存在する場合
            
            # インデックス作成
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_importance ON memory_entries(importance_score DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_content_hash ON memory_entries(content_hash)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON memory_entries(created_at DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_access_count ON memory_entries(access_count DESC)")
            
            conn.commit()
        
        logger.info(f"✅ データベース初期化完了: {self.db_path}")
    
    def _get_embedding(self, text: str) -> Optional[List[float]]:
        """
        テキストの埋め込みベクトルを取得
        
        Args:
            text: テキスト
        
        Returns:
            埋め込みベクトル
        """
        try:
            timeout = timeout_config.get("api_call", 10.0)
            response = httpx.post(
                f"{self.ollama_url}/api/embeddings",
                json={"model": self.embedding_model, "prompt": text},
                timeout=timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("embedding")
        except Exception as e:
            logger.warning(f"埋め込み取得エラー: {e}")
        
        return None
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """コサイン類似度を計算"""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(a * a for a in vec2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    def _calculate_content_hash(self, content: str) -> str:
        """コンテンツハッシュを計算"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def _calculate_importance_score(
        self,
        content: str,
        context: Optional[Dict[str, Any]] = None,
        access_count: int = 0,
        days_since_creation: int = 0
    ) -> float:
        """
        重要度スコアを計算（動的更新対応）
        
        Args:
            content: コンテンツ
            context: コンテキスト情報
            access_count: アクセス回数
            days_since_creation: 作成からの日数
        
        Returns:
            重要度スコア (0.0-1.0)
        """
        # ベーススコア
        score = 0.5
        
        # キーワードによる重要度調整
        importance_keywords = [
            "重要", "必須", "必要", "緊急", "優先",
            "完了", "成功", "失敗", "エラー",
            "設定", "変更", "更新", "削除"
        ]
        
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
        
        # アクセス頻度による調整（動的）
        if access_count > 0:
            score += min(0.2, access_count * 0.02)
        
        # 時間経過による減衰（動的）
        if days_since_creation > 30:
            decay = min(0.2, (days_since_creation - 30) * 0.01)
            score -= decay
        
        return min(1.0, max(0.0, score))
    
    def _find_related_entries(self, entry: MemoryEntry, limit: int = 5) -> List[str]:
        """
        関連エントリを自動検出
        
        Args:
            entry: エントリ
            limit: 最大件数
        
        Returns:
            関連エントリIDのリスト
        """
        if not entry.embedding:
            return []
        
        # すべてのエントリを取得
        with self.db_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT entry_id, embedding FROM memory_entries WHERE entry_id != ?", (entry.entry_id,))
            rows = cursor.fetchall()
        
        # 類似度を計算
        similarities = []
        for row in rows:
            entry_id, embedding_json = row
            if embedding_json:
                try:
                    other_embedding = json.loads(embedding_json)
                    similarity = self._cosine_similarity(entry.embedding, other_embedding)
                    if similarity > 0.7:  # 閾値
                        similarities.append((entry_id, similarity))
                except:
                    pass
        
        # 類似度でソート
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return [entry_id for entry_id, _ in similarities[:limit]]
    
    def add_memory(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        force_importance: Optional[float] = None
    ) -> MemoryEntry:
        """
        記憶を追加（強化版）
        
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
        
        # 埋め込みベクトルを取得
        embedding = self._get_embedding(content)
        
        # 重要度スコアを計算
        if force_importance is not None:
            importance_score = force_importance
        else:
            importance_score = self._calculate_importance_score(content, metadata)
        
        # 重要度が閾値以下の場合は保存しない
        threshold = 0.6
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
            metadata=metadata or {},
            embedding=embedding
        )
        
        # 関連エントリを検出
        related_ids = self._find_related_entries(entry)
        entry.related_entries = related_ids
        
        # データベースに保存
        with self.db_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO memory_entries (
                    entry_id, content, importance_score, content_hash,
                    created_at, updated_at, access_count,
                    related_entries, temporal_context, metadata, embedding
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                json.dumps(entry.metadata),
                json.dumps(entry.embedding) if entry.embedding else None
            ))
            conn.commit()
        
        # ハッシュマップを更新
        self.content_hash_map[content_hash] = entry_id
        
        # キャッシュに保存
        cache_system.set("memory_entry", asdict(entry), entry_id=entry_id, ttl_seconds=3600)
        
        logger.info(f"✅ 記憶を追加: {entry_id} (重要度: {importance_score:.2f}, 関連: {len(related_ids)}件)")
        return entry
    
    def semantic_search(
        self,
        query: str,
        limit: int = 10,
        min_importance: float = 0.0
    ) -> List[Tuple[MemoryEntry, float]]:
        """
        セマンティック検索（強化版）
        
        Args:
            query: 検索クエリ
            limit: 最大件数
            min_importance: 最小重要度
        
        Returns:
            (MemoryEntry, 類似度)のリスト
        """
        # クエリの埋め込みを取得
        query_embedding = self._get_embedding(query)
        if not query_embedding:
            # 埋め込みが取得できない場合は通常検索にフォールバック
            return [(entry, 0.5) for entry in self._text_search(query, limit, min_importance)]
        
        # すべてのエントリを取得
        with self.db_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM memory_entries
                WHERE importance_score >= ?
            """, (min_importance,))
            rows = cursor.fetchall()
        
        # 類似度を計算
        results = []
        for row in rows:
            entry = self._row_to_entry(row)
            if entry.embedding:
                similarity = self._cosine_similarity(query_embedding, entry.embedding)
                if similarity > 0.5:  # 閾値
                    results.append((entry, similarity))
        
        # 類似度でソート
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results[:limit]
    
    def _text_search(
        self,
        query: str,
        limit: int = 10,
        min_importance: float = 0.0
    ) -> List[MemoryEntry]:
        """テキスト検索（フォールバック）"""
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
        
        return results
    
    def update_importance_scores(self):
        """重要度スコアを動的に更新"""
        with self.db_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM memory_entries")
            rows = cursor.fetchall()
            
            for row in rows:
                entry = self._row_to_entry(row)
                created_at = datetime.fromisoformat(entry.created_at)
                days_since_creation = (datetime.now() - created_at).days
                
                # 重要度を再計算
                new_importance = self._calculate_importance_score(
                    entry.content,
                    entry.metadata,
                    entry.access_count,
                    days_since_creation
                )
                
                # 更新
                if abs(new_importance - entry.importance_score) > 0.05:  # 5%以上の変化
                    cursor.execute("""
                        UPDATE memory_entries
                        SET importance_score = ?, updated_at = ?
                        WHERE entry_id = ?
                    """, (new_importance, datetime.now().isoformat(), entry.entry_id))
            
            conn.commit()
        
        logger.info("✅ 重要度スコアを更新しました")
    
    def _check_duplicate(self, content: str) -> Optional[str]:
        """重複チェック"""
        content_hash = self._calculate_content_hash(content)
        return self.content_hash_map.get(content_hash)
    
    def _merge_entries(self, existing_id: str, new_content: str, new_metadata: Dict[str, Any]):
        """エントリを統合"""
        existing = self.get_memory(existing_id)
        if existing:
            existing.access_count += 1
            existing.last_accessed_at = datetime.now().isoformat()
            existing.updated_at = datetime.now().isoformat()
            existing.metadata.update(new_metadata)
            
            # 重要度を再計算
            created_at = datetime.fromisoformat(existing.created_at)
            days_since_creation = (datetime.now() - created_at).days
            existing.importance_score = self._calculate_importance_score(
                existing.content,
                existing.metadata,
                existing.access_count,
                days_since_creation
            )
            
            # データベースを更新
            with self.db_pool.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE memory_entries
                    SET access_count = ?, last_accessed_at = ?, updated_at = ?,
                        importance_score = ?, metadata = ?
                    WHERE entry_id = ?
                """, (
                    existing.access_count,
                    existing.last_accessed_at,
                    existing.updated_at,
                    existing.importance_score,
                    json.dumps(existing.metadata),
                    existing_id
                ))
                conn.commit()
            
            # キャッシュを更新
            cache_system.set("memory_entry", asdict(existing), entry_id=existing_id, ttl_seconds=3600)
    
    def get_memory(self, entry_id: str) -> Optional[MemoryEntry]:
        """記憶を取得"""
        # キャッシュから取得
        cached_entry = cache_system.get("memory_entry", entry_id=entry_id)
        if cached_entry:
            return MemoryEntry(**cached_entry)
        
        # データベースから取得
        with self.db_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM memory_entries WHERE entry_id = ?", (entry_id,))
            row = cursor.fetchone()
            
            if row:
                entry = self._row_to_entry(row)
                # アクセス情報を更新
                entry.access_count += 1
                entry.last_accessed_at = datetime.now().isoformat()
                
                cursor.execute("""
                    UPDATE memory_entries
                    SET access_count = ?, last_accessed_at = ?
                    WHERE entry_id = ?
                """, (entry.access_count, entry.last_accessed_at, entry_id))
                conn.commit()
                
                # キャッシュに保存
                cache_system.set("memory_entry", asdict(entry), entry_id=entry_id, ttl_seconds=3600)
                return entry
        
        return None
    
    def _row_to_entry(self, row: Tuple) -> MemoryEntry:
        """データベース行をMemoryEntryに変換"""
        embedding_json = row[11] if len(row) > 11 else None
        embedding = json.loads(embedding_json) if embedding_json else None
        
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
            metadata=json.loads(row[10] or "{}"),
            embedding=embedding
        )
    
    def _get_temporal_context(self, content: str) -> Dict[str, Any]:
        """時系列コンテキストを取得"""
        return {
            "timestamp": datetime.now().isoformat(),
            "day_of_week": datetime.now().strftime("%A"),
            "hour": datetime.now().hour
        }
    
    def _load_content_hashes(self):
        """コンテンツハッシュを読み込む"""
        cached_hashes = cache_system.get("content_hashes", db_path=str(self.db_path))
        if cached_hashes:
            self.content_hash_map = cached_hashes
            return
        
        with self.db_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT entry_id, content_hash FROM memory_entries")
            for row in cursor.fetchall():
                entry_id, content_hash = row
                self.content_hash_map[content_hash] = entry_id
        
        cache_system.set("content_hashes", self.content_hash_map, db_path=str(self.db_path), ttl_seconds=3600)


def main():
    """テスト用メイン関数"""
    print("RAG記憶進化システム v2（強化版）テスト")
    print("=" * 60)
    
    memory = RAGMemoryEnhancedV2()
    
    # 記憶を追加
    entry = memory.add_memory(
        "テスト記憶",
        metadata={"type": "test"}
    )
    if entry:
        print(f"記憶を追加: {entry.entry_id}")
        
        # セマンティック検索
        results = memory.semantic_search("テスト", limit=5)
        print(f"セマンティック検索結果: {len(results)}件")


if __name__ == "__main__":
    main()






















