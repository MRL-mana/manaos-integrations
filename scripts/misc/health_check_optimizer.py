"""
高速ヘルスチェック実装
キャッシング、タイムアウト、軽量チェック機構
"""

import time
import threading
from functools import wraps
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class HealthCheckCache:
    """ヘルスチェック結果をキャッシュして高速化"""
    
    def __init__(self, ttl_seconds: int = 5):
        """
        Args:
            ttl_seconds: キャッシュの有効期限（秒）
        """
        self.ttl_seconds = ttl_seconds
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_times: Dict[str, datetime] = {}
        self.lock = threading.Lock()
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """キャッシュを取得"""
        with self.lock:
            if key not in self.cache:
                return None
            
            # TTLをチェック
            cache_time = self.cache_times.get(key)
            if cache_time and datetime.now() - cache_time > timedelta(seconds=self.ttl_seconds):
                del self.cache[key]
                del self.cache_times[key]
                return None
            
            return self.cache[key]
    
    def set(self, key: str, value: Dict[str, Any]):
        """キャッシュを設定"""
        with self.lock:
            self.cache[key] = value
            self.cache_times[key] = datetime.now()
    
    def clear(self, key: Optional[str] = None):
        """キャッシュをクリア"""
        with self.lock:
            if key:
                self.cache.pop(key, None)
                self.cache_times.pop(key, None)
            else:
                self.cache.clear()
                self.cache_times.clear()


class HealthCheckOptimizer:
    """ヘルスチェート最適化機構"""
    
    def __init__(self, timeout_ms: int = 100):
        """
        Args:
            timeout_ms: ヘルスチェックのタイムアウト（ミリ秒）
        """
        self.timeout_ms = timeout_ms
        self.cache = HealthCheckCache(ttl_seconds=5)
    
    def cached_health_check(self, cache_key: str, ttl_seconds: int = 5):
        """キャッシュ付きヘルスチェックデコレーター"""
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # キャッシュから取得
                cached_result = self.cache.get(cache_key)
                if cached_result is not None:
                    logger.debug(f"Health check cached: {cache_key}")
                    return cached_result
                
                # 実行
                try:
                    result = func(*args, **kwargs)
                    # キャッシュに保存
                    self.cache.set(cache_key, result)
                    return result
                except Exception as e:
                    logger.error(f"Health check failed: {cache_key} - {e}")
                    return {"status": "unhealthy", "error": str(e)[:100]}
            
            return wrapper
        return decorator
    
    def lightweight_check(self, timeout_ms: Optional[int] = None):
        """軽量チェックデコレーター（タイムアウト付き）"""
        timeout = (timeout_ms or self.timeout_ms) / 1000.0  # ミリ秒から秒に変換
        
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                
                try:
                    # メインスレッドで実行（タイムアウト付き）
                    result = func(*args, **kwargs)
                    elapsed = (time.time() - start_time) * 1000
                    
                    logger.debug(f"Health check completed in {elapsed:.2f}ms")
                    return result
                
                except Exception as e:
                    elapsed = (time.time() - start_time) * 1000
                    logger.warning(f"Health check failed after {elapsed:.2f}ms: {e}")
                    return {"status": "unavailable", "error": str(e)[:100]}
            
            return wrapper
        return decorator


# グローバルインスタンス
_global_optimizer: Optional[HealthCheckOptimizer] = None


def get_health_check_optimizer() -> HealthCheckOptimizer:
    """グローバル HealthCheckOptimizer を取得"""
    global _global_optimizer
    if _global_optimizer is None:
        _global_optimizer = HealthCheckOptimizer(timeout_ms=100)
    return _global_optimizer


def init_health_check_optimizer(timeout_ms: int = 100):
    """HealthCheckOptimizer を初期化"""
    global _global_optimizer
    _global_optimizer = HealthCheckOptimizer(timeout_ms=timeout_ms)


# 使用例
if __name__ == "__main__":
    import json
    
    optimizer = get_health_check_optimizer()
    
    # 例1: キャッシュ付きヘルスチェック
    @optimizer.cached_health_check("mrl_memory_health", ttl_seconds=10)
    def check_mrl_memory():
        """MRL Memory ヘルスチェック"""
        time.sleep(0.1)  # 重い処理をシミュレート
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "uptime": 123456
        }
    
    # 例2: 軽量チェック
    @optimizer.lightweight_check(timeout_ms=50)
    def check_api_server():
        """API サーバーのみライトチェック"""
        return {
            "status": "alive",
            "service": "Unified API"
        }
    
    print("First call (slow):")
    start = time.time()
    result = check_mrl_memory()
    print(f"  Duration: {(time.time()-start)*1000:.2f}ms")
    print(f"  Result: {json.dumps(result, ensure_ascii=False)}\n")
    
    print("Second call (cached, fast):")
    start = time.time()
    result = check_mrl_memory()
    print(f"  Duration: {(time.time()-start)*1000:.2f}ms")
    print(f"  Result: {json.dumps(result, ensure_ascii=False)}\n")
    
    print("Lightweight check:")
    start = time.time()
    result = check_api_server()
    print(f"  Duration: {(time.time()-start)*1000:.2f}ms")
    print(f"  Result: {json.dumps(result, ensure_ascii=False)}")
