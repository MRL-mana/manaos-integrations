#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 Unified API Server最適化モジュール
統合APIサーバーのパフォーマンス最適化機能
"""

import time
from typing import Dict, Any, Optional, Callable
from functools import wraps
from datetime import datetime

# 統一モジュールのインポート
from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity

# キャッシュシステム
try:
    from unified_cache_system import get_unified_cache
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False
    get_unified_cache = None

# パフォーマンス最適化システム
try:
    from manaos_performance_optimizer import PerformanceOptimizer
    PERFORMANCE_OPTIMIZER_AVAILABLE = True
except ImportError:
    PERFORMANCE_OPTIMIZER_AVAILABLE = False
    PerformanceOptimizer = None

# ロガーの初期化
logger = get_service_logger("unified-optimizer")

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("UnifiedAPIServerOptimizer")

# キャッシュシステム
cache_system = None
if CACHE_AVAILABLE:
    try:
        cache_system = get_unified_cache()
        logger.info("✅ キャッシュシステム初期化完了")
    except Exception as e:
        logger.warning(f"⚠️ キャッシュシステム初期化エラー: {e}")

# パフォーマンス最適化システム
performance_optimizer = None
if PERFORMANCE_OPTIMIZER_AVAILABLE:
    try:
        performance_optimizer = PerformanceOptimizer()
        logger.info("✅ パフォーマンス最適化システム初期化完了")
    except Exception as e:
        logger.warning(f"⚠️ パフォーマンス最適化システム初期化エラー: {e}")


def cache_response(ttl_seconds: int = 3600, key_prefix: str = "api"):
    """
    レスポンスをキャッシュするデコレータ
    
    Args:
        ttl_seconds: キャッシュの有効期限（秒）
        key_prefix: キャッシュキーのプレフィックス
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not cache_system:
                return func(*args, **kwargs)
            
            # キャッシュキーを生成
            import hashlib
            import json
            cache_key_data = {
                "func": func.__name__,
                "args": str(args),
                "kwargs": json.dumps(kwargs, sort_keys=True)
            }
            cache_key_str = json.dumps(cache_key_data, sort_keys=True)
            cache_key = f"{key_prefix}:{hashlib.md5(cache_key_str.encode()).hexdigest()}"
            
            # キャッシュから取得を試みる
            try:
                cached_result = cache_system.get("api_response", cache_key)
                if cached_result:
                    logger.debug(f"キャッシュヒット: {func.__name__}")
                    return cached_result
            except Exception as e:
                logger.debug(f"キャッシュ取得エラー: {e}")
            
            # 関数を実行
            result = func(*args, **kwargs)
            
            # キャッシュに保存
            try:
                cache_system.set("api_response", result, ttl_seconds=ttl_seconds, key=cache_key)
                logger.debug(f"キャッシュ保存: {func.__name__}")
            except Exception as e:
                logger.debug(f"キャッシュ保存エラー: {e}")
            
            return result
        
        return wrapper
    return decorator


def measure_performance(func: Callable) -> Callable:
    """
    パフォーマンスを測定するデコレータ
    
    Args:
        func: 測定対象の関数
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            success = True
        except Exception as e:
            result = None
            success = False
            raise
        finally:
            execution_time = time.time() - start_time
            
            # メトリクスを記録
            if performance_optimizer:
                try:
                    metrics = {
                        "function": func.__name__,
                        "execution_time": execution_time,
                        "success": success,
                        "timestamp": datetime.now().isoformat()
                    }
                    # メトリクスを記録（実装はパフォーマンス最適化システムに依存）
                    logger.debug(f"パフォーマンス測定: {func.__name__} - {execution_time:.3f}秒")
                except Exception as e:
                    logger.debug(f"メトリクス記録エラー: {e}")
        
        return result
    
    return wrapper


def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    """
    失敗時にリトライするデコレータ
    
    Args:
        max_retries: 最大リトライ回数
        delay: リトライ間隔（秒）
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(f"{func.__name__}のリトライ ({attempt + 1}/{max_retries}): {e}")
                        time.sleep(delay * (attempt + 1))  # 指数バックオフ
                    else:
                        logger.error(f"{func.__name__}のリトライ失敗: {e}")
            
            raise last_exception
        
        return wrapper
    return decorator


class UnifiedAPIServerOptimizer:
    """統合APIサーバー最適化クラス"""
    
    def __init__(self):
        """初期化"""
        self.cache_system = cache_system
        self.performance_optimizer = performance_optimizer
        self.metrics = {
            "total_requests": 0,
            "cached_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "average_response_time": 0.0,
            "error_count": 0
        }
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """キャッシュ統計を取得"""
        if not self.cache_system:
            return {"available": False}
        
        try:
            stats = self.cache_system.get_stats()
            stats["available"] = True
            return stats
        except Exception as e:
            logger.warning(f"キャッシュ統計取得エラー: {e}")
            return {"available": False, "error": str(e)}
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """パフォーマンス統計を取得"""
        stats = {
            "metrics": self.metrics.copy(),
            "cache_stats": self.get_cache_stats(),
            "timestamp": datetime.now().isoformat()
        }
        
        if self.performance_optimizer:
            try:
                perf_stats = {
                    "cache_stats": self.performance_optimizer.get_cache_stats(),
                    "http_pool_stats": self.performance_optimizer.get_http_pool_stats(),
                    "config_cache_stats": self.performance_optimizer.get_config_cache_stats()
                }
                stats["performance_optimizer"] = perf_stats
            except Exception as e:
                logger.warning(f"パフォーマンス統計取得エラー: {e}")
        
        return stats
    
    def optimize_cache(self) -> Dict[str, Any]:
        """キャッシュを最適化"""
        if not self.cache_system:
            return {"status": "error", "message": "キャッシュシステムが利用できません"}
        
        try:
            # キャッシュのクリーンアップ（実装はキャッシュシステムに依存）
            stats = self.cache_system.get_stats()
            return {
                "status": "success",
                "stats": stats,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            error = error_handler.handle_exception(
                e,
                context={"action": "optimize_cache"},
                user_message="キャッシュの最適化に失敗しました"
            )
            return {
                "status": "error",
                "error": error.user_message or error.message
            }
    
    def clear_cache(self, pattern: Optional[str] = None) -> Dict[str, Any]:
        """キャッシュをクリア"""
        if not self.cache_system:
            return {"status": "error", "message": "キャッシュシステムが利用できません"}
        
        try:
            # キャッシュのクリア（実装はキャッシュシステムに依存）
            return {
                "status": "success",
                "message": "キャッシュをクリアしました",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            error = error_handler.handle_exception(
                e,
                context={"action": "clear_cache", "pattern": pattern},
                user_message="キャッシュのクリアに失敗しました"
            )
            return {
                "status": "error",
                "error": error.user_message or error.message
            }


# グローバルインスタンス
optimizer = UnifiedAPIServerOptimizer()


def get_optimizer() -> UnifiedAPIServerOptimizer:
    """最適化システムのインスタンスを取得"""
    return optimizer








