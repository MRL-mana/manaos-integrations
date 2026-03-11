#!/usr/bin/env python3
"""
🔴 ManaOS Redis分散キャッシュシステム
Redis統合・キャッシュの共有・キャッシュの無効化
"""

import os
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path
from functools import wraps

# 統一モジュールのインポート
from manaos_logger import get_logger, get_service_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity

# ロガーの初期化
logger = get_service_logger("redis-cache")

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("RedisCache")

# Redisのインポート（オプション）
REDIS_AVAILABLE = False
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ Redisが利用できません。pip install redis でインストールしてください。")


class RedisCache:
    """Redis分散キャッシュシステム"""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        default_ttl_seconds: int = 3600
    ):
        """
        初期化
        
        Args:
            host: Redisホスト
            port: Redisポート
            db: Redisデータベース番号
            password: Redisパスワード
            default_ttl_seconds: デフォルトTTL（秒）
        """
        self.default_ttl_seconds = default_ttl_seconds
        self.redis_client = None
        
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.Redis(  # type: ignore[possibly-unbound]
                    host=host,
                    port=port,
                    db=db,
                    password=password,
                    decode_responses=True
                )
                # 接続テスト
                self.redis_client.ping()
                logger.info(f"✅ Redis接続成功: {host}:{port}")
            except Exception as e:
                error = error_handler.handle_exception(
                    e,
                    context={"host": host, "port": port},
                    user_message="Redisへの接続に失敗しました"
                )
                logger.warning(f"Redis接続エラー: {error.message}")
                self.redis_client = None
        else:
            logger.warning("⚠️ Redisが利用できません。ローカルキャッシュのみ使用します。")
    
    def _generate_key(self, cache_type: str, *args, **kwargs) -> str:
        """キャッシュキーを生成"""
        key_data = {
            "type": cache_type,
            "args": args,
            "kwargs": kwargs
        }
        key_string = json.dumps(key_data, sort_keys=True, ensure_ascii=False)
        return f"manaos:cache:{hashlib.sha256(key_string.encode('utf-8')).hexdigest()}"
    
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
        if not self.redis_client:
            return None
        
        cache_key = self._generate_key(cache_type, *args, **kwargs)
        
        try:
            value = self.redis_client.get(cache_key)
            if value:
                return json.loads(value)
        except Exception as e:
            error = error_handler.handle_exception(
                e,
                context={"operation": "get_cache", "cache_key": cache_key},
                user_message="キャッシュの取得に失敗しました"
            )
            logger.warning(f"キャッシュ取得エラー: {error.message}")
        
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
        if not self.redis_client:
            return
        
        cache_key = self._generate_key(cache_type, *args, **kwargs)
        ttl = ttl_seconds or self.default_ttl_seconds
        
        try:
            value_json = json.dumps(value, ensure_ascii=False)
            self.redis_client.setex(cache_key, ttl, value_json)
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
        if not self.redis_client:
            return
        
        cache_key = self._generate_key(cache_type, *args, **kwargs)
        
        try:
            self.redis_client.delete(cache_key)
            logger.debug(f"✅ キャッシュ無効化: {cache_type}")
        except Exception as e:
            error = error_handler.handle_exception(
                e,
                context={"operation": "invalidate_cache", "cache_key": cache_key},
                user_message="キャッシュの無効化に失敗しました"
            )
            logger.warning(f"キャッシュ無効化エラー: {error.message}")
    
    def invalidate_pattern(self, pattern: str):
        """
        パターンに一致するキャッシュを無効化
        
        Args:
            pattern: パターン（例: "manaos:cache:*")
        """
        if not self.redis_client:
            return
        
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
                logger.info(f"✅ キャッシュ無効化（パターン）: {len(keys)}件")
        except Exception as e:
            error = error_handler.handle_exception(
                e,
                context={"operation": "invalidate_pattern", "pattern": pattern},
                user_message="キャッシュの無効化に失敗しました"
            )
            logger.warning(f"キャッシュ無効化エラー: {error.message}")
    
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
        def decorator(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                # キャッシュから取得を試みる
                cached_value = self.get(cache_type, *args, ttl_seconds=ttl_seconds, **kwargs)
                if cached_value is not None:
                    return cached_value
                
                # キャッシュミス - 関数を実行
                import asyncio
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                # キャッシュに保存
                self.set(cache_type, result, *args, ttl_seconds=ttl_seconds, **kwargs)
                
                return result
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                # キャッシュから取得を試みる
                cached_value = self.get(cache_type, *args, ttl_seconds=ttl_seconds, **kwargs)
                if cached_value is not None:
                    return cached_value
                
                # キャッシュミス - 関数を実行
                result = func(*args, **kwargs)
                
                # キャッシュに保存
                self.set(cache_type, result, *args, ttl_seconds=ttl_seconds, **kwargs)
                
                return result
            
            import inspect
            if inspect.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        
        return decorator


# グローバルインスタンス
redis_cache = RedisCache(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=int(os.getenv("REDIS_DB", 0)),
    password=os.getenv("REDIS_PASSWORD")
)

# デコレータのエクスポート
redis_cache_decorator = redis_cache.cache_decorator

