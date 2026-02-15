#!/usr/bin/env python3
"""
💾 ManaOS レスポンスキャッシュシステム
LLM応答・意図分類・実行計画のキャッシュ
"""

import os
import json
import hashlib
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable, TypeVar
from pathlib import Path
from dataclasses import dataclass, asdict
from functools import wraps
import asyncio

# 統一モジュールのインポート
from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from manaos_timeout_config import get_timeout_config

# ロガーの初期化
logger = get_service_logger("response-cache")

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("ResponseCache")

# タイムアウト設定の取得
timeout_config = get_timeout_config()

T = TypeVar('T')


@dataclass
class CacheEntry:
    """キャッシュエントリ"""
    cache_key: str
    cache_type: str
    value: Any
    created_at: str
    expires_at: str
    hit_count: int = 0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ResponseCache:
    """レスポンスキャッシュシステム"""
    
    def __init__(
        self,
        db_path: Optional[Path] = None,
        default_ttl_seconds: int = 3600,
        max_size: int = 10000
    ):
        """
        初期化
        
        Args:
            db_path: データベースパス
            default_ttl_seconds: デフォルトTTL（秒）
            max_size: 最大キャッシュサイズ
        """
        self.default_ttl_seconds = default_ttl_seconds
        self.max_size = max_size
        
        # データベース初期化
        self.db_path = db_path or Path(__file__).parent / "response_cache.db"
        self._init_database()
        
        # メモリ内キャッシュ（高速アクセス用）
        self.memory_cache: Dict[str, CacheEntry] = {}
        
        logger.info(f"✅ Response Cache初期化完了")
    
    def _init_database(self):
        """データベースを初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # キャッシュテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cache_entries (
                cache_key TEXT PRIMARY KEY,
                cache_type TEXT NOT NULL,
                value TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                hit_count INTEGER DEFAULT 0,
                metadata TEXT
            )
        """)
        
        # インデックス作成
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_expires_at ON cache_entries(expires_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cache_type ON cache_entries(cache_type)")
        
        conn.commit()
        conn.close()
        logger.info(f"✅ キャッシュデータベース初期化完了: {self.db_path}")
    
    def _generate_key(self, cache_type: str, *args, **kwargs) -> str:
        """キャッシュキーを生成"""
        key_data = {
            "type": cache_type,
            "args": args,
            "kwargs": kwargs
        }
        key_string = json.dumps(key_data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(key_string.encode('utf-8')).hexdigest()
    
    def get(
        self,
        cache_type: str,
        *args,
        ttl_seconds: Optional[int] = None,
        **kwargs
    ) -> Optional[Any]:
        """
        キャッシュから取得
        
        Args:
            cache_type: キャッシュタイプ
            *args: キャッシュキー生成用の引数
            ttl_seconds: TTL（秒）
            **kwargs: キャッシュキー生成用のキーワード引数
        
        Returns:
            キャッシュされた値（存在する場合）
        """
        cache_key = self._generate_key(cache_type, *args, **kwargs)
        
        # メモリキャッシュから取得
        if cache_key in self.memory_cache:
            entry = self.memory_cache[cache_key]
            if datetime.fromisoformat(entry.expires_at) > datetime.now():
                entry.hit_count += 1
                logger.debug(f"✅ キャッシュヒット（メモリ）: {cache_type}")
                return entry.value
            else:
                # 期限切れ
                del self.memory_cache[cache_key]
        
        # データベースから取得
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT value, expires_at, hit_count FROM cache_entries
                WHERE cache_key = ? AND expires_at > ?
            """, (cache_key, datetime.now().isoformat()))
            
            row = cursor.fetchone()
            if row:
                value = json.loads(row[0])
                expires_at = row[1]
                hit_count = row[2] + 1
                
                # ヒット数を更新
                cursor.execute("""
                    UPDATE cache_entries SET hit_count = ? WHERE cache_key = ?
                """, (hit_count, cache_key))
                
                conn.commit()
                conn.close()
                
                # メモリキャッシュに追加
                entry = CacheEntry(
                    cache_key=cache_key,
                    cache_type=cache_type,
                    value=value,
                    created_at=datetime.now().isoformat(),
                    expires_at=expires_at,
                    hit_count=hit_count
                )
                self.memory_cache[cache_key] = entry
                
                logger.debug(f"✅ キャッシュヒット（DB）: {cache_type}")
                return value
            
            conn.close()
        
        except Exception as e:
            error = error_handler.handle_exception(
                e,
                context={"operation": "get_cache", "cache_key": cache_key},
                user_message="キャッシュの取得に失敗しました"
            )
            logger.warning(f"キャッシュ取得エラー: {error.message}")
        
        logger.debug(f"❌ キャッシュミス: {cache_type}")
        return None
    
    def set(
        self,
        cache_type: str,
        value: Any,
        *args,
        ttl_seconds: Optional[int] = None,
        **kwargs
    ):
        """
        キャッシュに保存
        
        Args:
            cache_type: キャッシュタイプ
            value: 保存する値
            *args: キャッシュキー生成用の引数
            ttl_seconds: TTL（秒）
            **kwargs: キャッシュキー生成用のキーワード引数
        """
        cache_key = self._generate_key(cache_type, *args, **kwargs)
        ttl = ttl_seconds or self.default_ttl_seconds
        created_at = datetime.now()
        expires_at = created_at + timedelta(seconds=ttl)
        
        entry = CacheEntry(
            cache_key=cache_key,
            cache_type=cache_type,
            value=value,
            created_at=created_at.isoformat(),
            expires_at=expires_at.isoformat()
        )
        
        # メモリキャッシュに追加
        self.memory_cache[cache_key] = entry
        
        # メモリキャッシュサイズ制限
        if len(self.memory_cache) > self.max_size:
            # 最も古いエントリを削除
            oldest_key = min(self.memory_cache.keys(), key=lambda k: self.memory_cache[k].created_at)
            del self.memory_cache[oldest_key]
        
        # データベースに保存
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO cache_entries
                (cache_key, cache_type, value, created_at, expires_at, hit_count, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                cache_key,
                cache_type,
                json.dumps(value, ensure_ascii=False),
                entry.created_at,
                entry.expires_at,
                entry.hit_count,
                json.dumps(entry.metadata, ensure_ascii=False) if entry.metadata else None
            ))
            
            conn.commit()
            conn.close()
            
            logger.debug(f"✅ キャッシュ保存: {cache_type}")
        
        except Exception as e:
            error = error_handler.handle_exception(
                e,
                context={"operation": "set_cache", "cache_key": cache_key},
                user_message="キャッシュの保存に失敗しました"
            )
            logger.warning(f"キャッシュ保存エラー: {error.message}")
    
    def invalidate(self, cache_type: str, *args, **kwargs):
        """
        キャッシュを無効化
        
        Args:
            cache_type: キャッシュタイプ
            *args: キャッシュキー生成用の引数
            **kwargs: キャッシュキー生成用のキーワード引数
        """
        cache_key = self._generate_key(cache_type, *args, **kwargs)
        
        # メモリキャッシュから削除
        if cache_key in self.memory_cache:
            del self.memory_cache[cache_key]
        
        # データベースから削除
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM cache_entries WHERE cache_key = ?", (cache_key,))
            
            conn.commit()
            conn.close()
            
            logger.debug(f"✅ キャッシュ無効化: {cache_type}")
        
        except Exception as e:
            error = error_handler.handle_exception(
                e,
                context={"operation": "invalidate_cache", "cache_key": cache_key},
                user_message="キャッシュの無効化に失敗しました"
            )
            logger.warning(f"キャッシュ無効化エラー: {error.message}")
    
    def cleanup_expired(self):
        """期限切れキャッシュを削除"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM cache_entries WHERE expires_at < ?", (datetime.now().isoformat(),))
            deleted_count = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            # メモリキャッシュからも削除
            expired_keys = [
                k for k, v in self.memory_cache.items()
                if datetime.fromisoformat(v.expires_at) < datetime.now()
            ]
            for key in expired_keys:
                del self.memory_cache[key]
            
            logger.info(f"✅ 期限切れキャッシュ削除完了: {deleted_count}件（DB）+ {len(expired_keys)}件（メモリ）")
            return deleted_count + len(expired_keys)
        
        except Exception as e:
            error = error_handler.handle_exception(
                e,
                context={"operation": "cleanup_expired"},
                user_message="期限切れキャッシュの削除に失敗しました"
            )
            logger.error(f"キャッシュクリーンアップエラー: {error.message}")
            return 0
    
    def cache_decorator(
        self,
        cache_type: str,
        ttl_seconds: Optional[int] = None
    ):
        """
        キャッシュデコレータ
        
        Args:
            cache_type: キャッシュタイプ
            ttl_seconds: TTL（秒）
        """
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @wraps(func)
            async def async_wrapper(*args, **kwargs) -> T:
                # キャッシュから取得を試みる
                cached_value = self.get(cache_type, *args, ttl_seconds=ttl_seconds, **kwargs)
                if cached_value is not None:
                    return cached_value
                
                # キャッシュミス - 関数を実行
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                # キャッシュに保存
                self.set(cache_type, result, *args, ttl_seconds=ttl_seconds, **kwargs)
                
                return result
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs) -> T:
                # キャッシュから取得を試みる
                cached_value = self.get(cache_type, *args, ttl_seconds=ttl_seconds, **kwargs)
                if cached_value is not None:
                    return cached_value
                
                # キャッシュミス - 関数を実行
                result = func(*args, **kwargs)
                
                # キャッシュに保存
                self.set(cache_type, result, *args, ttl_seconds=ttl_seconds, **kwargs)
                
                return result
            
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        
        return decorator


# グローバルインスタンス
response_cache = ResponseCache()

# デコレータのエクスポート
cache = response_cache.cache_decorator

