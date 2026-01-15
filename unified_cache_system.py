#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💾 ManaOS統一キャッシュシステム
メモリ → Redis → ディスクの3階層キャッシュ
"""

import json
import hashlib
import pickle
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path
from functools import wraps

# 統一モジュールのインポート
from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity

# ロガーの初期化
logger = get_logger(__name__)

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("UnifiedCache")

# Redisのインポート（オプション）
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None


class UnifiedCacheSystem:
    """統一キャッシュシステム（3階層）"""
    
    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0,
        default_ttl: int = 3600
    ):
        """
        初期化
        
        Args:
            cache_dir: ディスクキャッシュディレクトリ
            redis_host: Redisホスト
            redis_port: Redisポート
            redis_db: Redis DB番号
            default_ttl: デフォルトTTL（秒）
        """
        # メモリキャッシュ（L1）
        self.memory_cache: Dict[str, Dict[str, Any]] = {}
        self.memory_max_size = 1000  # 最大1000エントリ
        
        # Redisキャッシュ（L2）
        self.redis_client = None
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    db=redis_db,
                    decode_responses=False
                )
                self.redis_client.ping()
                logger.info("Redisキャッシュを有効化しました")
            except Exception as e:
                logger.warning(f"Redis接続失敗: {e}。メモリキャッシュのみ使用します。")
                self.redis_client = None
        
        # ディスクキャッシュ（L3）
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = Path.home() / ".manaos_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.default_ttl = default_ttl
        
        # 統計情報
        self.stats = {
            "memory_hits": 0,
            "redis_hits": 0,
            "disk_hits": 0,
            "misses": 0,
            "sets": 0
        }
    
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
        キャッシュから取得（3階層チェック）
        
        Args:
            cache_type: キャッシュタイプ
            *args: キャッシュキー生成用の引数
            ttl_seconds: TTL（秒）
            **kwargs: キャッシュキー生成用のキーワード引数
        
        Returns:
            キャッシュされた値（存在する場合）
        """
        cache_key = self._generate_key(cache_type, *args, **kwargs)
        
        # L1: メモリキャッシュ
        if cache_key in self.memory_cache:
            entry = self.memory_cache[cache_key]
            expires_at = datetime.fromisoformat(entry["expires_at"])
            if datetime.now() < expires_at:
                self.stats["memory_hits"] += 1
                logger.debug(f"メモリキャッシュヒット: {cache_type}")
                return entry["value"]
            else:
                # 期限切れ
                del self.memory_cache[cache_key]
        
        # L2: Redisキャッシュ
        if self.redis_client:
            try:
                cached_data = self.redis_client.get(f"manaos:cache:{cache_key}")
                if cached_data:
                    entry = json.loads(cached_data)
                    expires_at = datetime.fromisoformat(entry["expires_at"])
                    if datetime.now() < expires_at:
                        # メモリキャッシュにも追加
                        self.memory_cache[cache_key] = entry
                        if len(self.memory_cache) > self.memory_max_size:
                            # 最も古いエントリを削除
                            oldest_key = min(
                                self.memory_cache.keys(),
                                key=lambda k: self.memory_cache[k]["created_at"]
                            )
                            del self.memory_cache[oldest_key]
                        
                        self.stats["redis_hits"] += 1
                        logger.debug(f"Redisキャッシュヒット: {cache_type}")
                        return entry["value"]
            except Exception as e:
                logger.warning(f"Redis取得エラー: {e}")
        
        # L3: ディスクキャッシュ
        cache_file = self.cache_dir / f"{cache_key}.cache"
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    entry = pickle.load(f)
                expires_at = datetime.fromisoformat(entry["expires_at"])
                if datetime.now() < expires_at:
                    # メモリキャッシュにも追加
                    self.memory_cache[cache_key] = entry
                    if len(self.memory_cache) > self.memory_max_size:
                        oldest_key = min(
                            self.memory_cache.keys(),
                            key=lambda k: self.memory_cache[k]["created_at"]
                        )
                        del self.memory_cache[oldest_key]
                    
                    self.stats["disk_hits"] += 1
                    logger.debug(f"ディスクキャッシュヒット: {cache_type}")
                    return entry["value"]
                else:
                    # 期限切れ
                    cache_file.unlink()
            except Exception as e:
                logger.warning(f"ディスクキャッシュ読み込みエラー: {e}")
        
        # キャッシュミス
        self.stats["misses"] += 1
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
        キャッシュに保存（3階層に保存）
        
        Args:
            cache_type: キャッシュタイプ
            value: 保存する値
            *args: キャッシュキー生成用の引数
            ttl_seconds: TTL（秒）
            **kwargs: キャッシュキー生成用のキーワード引数
        """
        cache_key = self._generate_key(cache_type, *args, **kwargs)
        ttl = ttl_seconds or self.default_ttl
        expires_at = (datetime.now() + timedelta(seconds=ttl)).isoformat()
        created_at = datetime.now().isoformat()
        
        entry = {
            "value": value,
            "created_at": created_at,
            "expires_at": expires_at,
            "cache_type": cache_type
        }
        
        # L1: メモリキャッシュ
        self.memory_cache[cache_key] = entry
        if len(self.memory_cache) > self.memory_max_size:
            oldest_key = min(
                self.memory_cache.keys(),
                key=lambda k: self.memory_cache[k]["created_at"]
            )
            del self.memory_cache[oldest_key]
        
        # L2: Redisキャッシュ
        if self.redis_client:
            try:
                self.redis_client.setex(
                    f"manaos:cache:{cache_key}",
                    ttl,
                    json.dumps(entry, default=str)
                )
            except Exception as e:
                logger.warning(f"Redis保存エラー: {e}")
        
        # L3: ディスクキャッシュ
        try:
            cache_file = self.cache_dir / f"{cache_key}.cache"
            with open(cache_file, 'wb') as f:
                pickle.dump(entry, f)
        except Exception as e:
            logger.warning(f"ディスクキャッシュ保存エラー: {e}")
        
        self.stats["sets"] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """統計情報を取得"""
        total_hits = self.stats["memory_hits"] + self.stats["redis_hits"] + self.stats["disk_hits"]
        total_requests = total_hits + self.stats["misses"]
        
        return {
            **self.stats,
            "total_hits": total_hits,
            "total_requests": total_requests,
            "hit_rate": (total_hits / total_requests * 100) if total_requests > 0 else 0,
            "memory_cache_size": len(self.memory_cache),
            "redis_available": self.redis_client is not None
        }
    
    def clear(self, cache_type: Optional[str] = None):
        """
        キャッシュをクリア
        
        Args:
            cache_type: クリアするキャッシュタイプ（Noneの場合は全クリア）
        """
        if cache_type:
            # 特定タイプのみクリア
            keys_to_remove = [
                k for k, v in self.memory_cache.items()
                if v.get("cache_type") == cache_type
            ]
            for key in keys_to_remove:
                del self.memory_cache[key]
        else:
            # 全クリア
            self.memory_cache.clear()
        
        logger.info(f"キャッシュをクリアしました（タイプ: {cache_type or 'all'}")


# グローバルインスタンス
_unified_cache: Optional[UnifiedCacheSystem] = None


def get_unified_cache() -> UnifiedCacheSystem:
    """統一キャッシュシステムのシングルトンインスタンスを取得"""
    global _unified_cache
    if _unified_cache is None:
        _unified_cache = UnifiedCacheSystem()
    return _unified_cache


def cached(cache_type: str, ttl_seconds: int = 3600):
    """
    キャッシュデコレータ
    
    Args:
        cache_type: キャッシュタイプ
        ttl_seconds: TTL（秒）
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = get_unified_cache()
            
            # キャッシュから取得
            cached_value = cache.get(cache_type, *args, ttl_seconds=ttl_seconds, **kwargs)
            if cached_value is not None:
                return cached_value
            
            # 関数を実行
            result = func(*args, **kwargs)
            
            # キャッシュに保存
            cache.set(cache_type, result, *args, ttl_seconds=ttl_seconds, **kwargs)
            
            return result
        return wrapper
    return decorator


def main():
    """テスト用メイン関数"""
    print("ManaOS統一キャッシュシステムテスト")
    print("=" * 60)
    
    cache = get_unified_cache()
    
    # テストデータを保存
    cache.set("test", "hello", key1="value1", key2="value2", ttl_seconds=60)
    
    # テストデータを取得
    result = cache.get("test", key1="value1", key2="value2")
    print(f"取得結果: {result}")
    
    # 統計情報
    print("\n統計情報:")
    stats = cache.get_stats()
    print(json.dumps(stats, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()






















