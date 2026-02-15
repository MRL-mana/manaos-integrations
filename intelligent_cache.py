#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💾 ManaOS インテリジェントキャッシュシステム
アクセスパターンに基づく動的キャッシュ最適化
"""

import time
import hashlib
import json
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import OrderedDict
from unified_logging import get_service_logger
logger = get_service_logger("intelligent-cache")


@dataclass


class CacheEntry:
    """キャッシュエントリ"""
    key: str
    value: Any
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    ttl: int = 3600  # 秒
    size: int = 0  # バイト


class IntelligentCache:
    """インテリジェントキャッシュ"""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        """
        初期化
        
        Args:
            max_size: 最大エントリ数
            default_ttl: デフォルトTTL（秒）
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.access_patterns: Dict[str, int] = {}  # キーごとのアクセス頻度
        self.hits = 0
        self.misses = 0
        self.total_size = 0
        self.max_memory_mb = 500  # 最大メモリ使用量（MB）
    
    def get(self, key: str) -> Optional[Any]:
        """キャッシュから取得"""
        if key in self.cache:
            entry = self.cache[key]
            
            # TTLチェック
            if (datetime.now() - entry.created_at).total_seconds() > entry.ttl:
                del self.cache[key]
                self.misses += 1
                return None
            
            # アクセス情報を更新
            entry.last_accessed = datetime.now()
            entry.access_count += 1
            self.access_patterns[key] = self.access_patterns.get(key, 0) + 1
            
            # LRU: 最後にアクセスしたエントリを最後に移動
            self.cache.move_to_end(key)
            
            self.hits += 1
            return entry.value
        
        self.misses += 1
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """キャッシュに設定"""
        # サイズチェック
        value_size = self._estimate_size(value)
        if value_size > self.max_memory_mb * 1024 * 1024:
            logger.warning(f"⚠️ 値が大きすぎます: {key} ({value_size / 1024 / 1024:.2f}MB)")
            return False
        
        # 既存のエントリを削除
        if key in self.cache:
            old_entry = self.cache[key]
            self.total_size -= old_entry.size
        
        # 新しいエントリを作成
        entry = CacheEntry(
            key=key,
            value=value,
            ttl=ttl or self.default_ttl,
            size=value_size
        )
        
        # メモリ制限チェック
        while self.total_size + value_size > self.max_memory_mb * 1024 * 1024:
            if not self._evict_lru():
                logger.warning("⚠️ キャッシュが満杯です")
                return False
        
        # エントリ数を制限
        while len(self.cache) >= self.max_size:
            if not self._evict_lru():
                break
        
        self.cache[key] = entry
        self.total_size += value_size
        
        return True
    
    def _evict_lru(self) -> bool:
        """LRUエントリを削除"""
        if not self.cache:
            return False
        
        # アクセス頻度が低いエントリを優先的に削除
        if self.access_patterns:
            # アクセス頻度が最も低いエントリを探す
            min_access_key = min(
                self.cache.keys(),
                key=lambda k: self.access_patterns.get(k, 0)
            )
            entry = self.cache.pop(min_access_key)
            self.total_size -= entry.size
            self.access_patterns.pop(min_access_key, None)
        else:
            # 最初のエントリを削除（FIFO）
            key, entry = self.cache.popitem(last=False)
            self.total_size -= entry.size
        
        return True
    
    def _estimate_size(self, value: Any) -> int:
        """値のサイズを推定"""
        try:
            if isinstance(value, (str, bytes)):
                return len(value)
            elif isinstance(value, dict):
                return len(json.dumps(value).encode())
            elif isinstance(value, list):
                return sum(self._estimate_size(item) for item in value)
            else:
                return len(str(value).encode())
        except Exception:
            return 1024  # デフォルトサイズ
    
    def clear(self):
        """キャッシュをクリア"""
        self.cache.clear()
        self.access_patterns.clear()
        self.total_size = 0
        self.hits = 0
        self.misses = 0
        logger.info("✅ キャッシュをクリアしました")
    
    def cleanup_expired(self):
        """期限切れエントリを削除"""
        now = datetime.now()
        expired_keys = []
        
        for key, entry in self.cache.items():
            if (now - entry.created_at).total_seconds() > entry.ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            entry = self.cache.pop(key)
            self.total_size -= entry.size
            self.access_patterns.pop(key, None)
        
        if expired_keys:
            logger.info(f"✅ {len(expired_keys)}個の期限切れエントリを削除しました")
    
    def optimize(self):
        """キャッシュを最適化"""
        # アクセス頻度に基づいてTTLを調整
        for key, entry in self.cache.items():
            access_freq = self.access_patterns.get(key, 0)
            
            # アクセス頻度が高い場合はTTLを延長
            if access_freq > 10:
                entry.ttl = min(entry.ttl * 1.5, 86400)  # 最大24時間
            # アクセス頻度が低い場合はTTLを短縮
            elif access_freq < 3:
                entry.ttl = max(entry.ttl * 0.8, 300)  # 最小5分
        
        logger.info("✅ キャッシュを最適化しました")
    
    def get_stats(self) -> Dict[str, Any]:
        """統計情報を取得"""
        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0.0
        
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
            "total_entries": len(self.cache),
            "total_size_mb": self.total_size / 1024 / 1024,
            "max_size": self.max_size,
            "max_memory_mb": self.max_memory_mb
        }
    
    def generate_cache_key(self, *args, **kwargs) -> str:
        """キャッシュキーを生成"""
        key_data = {
            "args": args,
            "kwargs": sorted(kwargs.items())
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()


# デコレータ


def cached(ttl: int = 3600, key_func: Optional[Callable] = None):
    """キャッシュデコレータ"""
    cache = IntelligentCache()
    
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            # キャッシュキーを生成
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = cache.generate_cache_key(*args, **kwargs)
            
            # キャッシュから取得
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # 関数を実行
            result = func(*args, **kwargs)
            
            # キャッシュに保存
            cache.set(cache_key, result, ttl=ttl)
            
            return result
        
        wrapper.cache = cache
        return wrapper
    return decorator


# シングルトンインスタンス
_cache: Optional[IntelligentCache] = None


def get_cache(max_size: int = 1000, default_ttl: int = 3600) -> IntelligentCache:
    """キャッシュのシングルトン取得"""
    global _cache
    if _cache is None:
        _cache = IntelligentCache(max_size=max_size, default_ttl=default_ttl)
    return _cache

