#!/usr/bin/env python3
"""
Mana Redis Cache Optimizer
Redis統合キャッシュ最適化 - 超高速データアクセス
"""

import redis
import json
import logging
from typing import Dict, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ManaRedisCacheOptimizer:
    def __init__(self):
        try:
            self.redis_client = redis.Redis(
                host='localhost',
                port=6379,
                db=0,
                decode_responses=True
            )
            self.redis_client.ping()
            self.redis_available = True
            logger.info("✅ Redis接続成功")
        except Exception as e:
            self.redis_available = False
            logger.warning(f"⚠️ Redis接続失敗: {e}")
        
        self.config = {
            "default_ttl": 3600,  # 1時間
            "max_cache_size_mb": 100,
            "auto_cleanup": True
        }
        
        logger.info("🚀 Mana Redis Cache Optimizer 初期化完了")
    
    def cache_system_metrics(self, metrics: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """システムメトリクスをキャッシュ"""
        if not self.redis_available:
            return False
        
        try:
            key = "manaos:metrics:latest"
            value = json.dumps(metrics)
            ttl = ttl or self.config["default_ttl"]
            
            self.redis_client.setex(key, ttl, value)
            logger.info(f"✅ メトリクスキャッシュ: {key}")
            return True
            
        except Exception as e:
            logger.error(f"キャッシュ保存エラー: {e}")
            return False
    
    def get_cached_metrics(self) -> Optional[Dict[str, Any]]:
        """キャッシュされたメトリクス取得"""
        if not self.redis_available:
            return None
        
        try:
            key = "manaos:metrics:latest"
            value = self.redis_client.get(key)
            
            if value:
                return json.loads(value)
            return None
            
        except Exception as e:
            logger.error(f"キャッシュ取得エラー: {e}")
            return None
    
    def cache_service_status(self, service_id: str, status: Dict[str, Any]) -> bool:
        """サービスステータスをキャッシュ"""
        if not self.redis_available:
            return False
        
        try:
            key = f"manaos:service:{service_id}"
            value = json.dumps(status)
            
            self.redis_client.setex(key, 60, value)  # 60秒TTL
            return True
            
        except Exception as e:
            logger.error(f"サービスステータスキャッシュエラー: {e}")
            return False
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """キャッシュ統計"""
        if not self.redis_available:
            return {"available": False}
        
        try:
            info = self.redis_client.info()
            
            return {
                "available": True,
                "used_memory_mb": info.get("used_memory", 0) / (1024 * 1024),
                "total_keys": self.redis_client.dbsize(),
                "hits": info.get("keyspace_hits", 0),
                "misses": info.get("keyspace_misses", 0),
                "hit_rate": self._calculate_hit_rate(
                    info.get("keyspace_hits", 0),
                    info.get("keyspace_misses", 0)
                )
            }
            
        except Exception as e:
            logger.error(f"統計取得エラー: {e}")
            return {"available": False, "error": str(e)}
    
    def _calculate_hit_rate(self, hits: int, misses: int) -> float:
        """ヒット率計算"""
        total = hits + misses
        if total == 0:
            return 0.0
        return round(hits / total * 100, 2)
    
    def optimize_cache(self) -> Dict[str, Any]:
        """キャッシュ最適化"""
        if not self.redis_available:
            return {"available": False}
        
        try:
            # 期限切れキーを削除
            deleted = 0
            for key in self.redis_client.scan_iter(match="manaos:*"):
                ttl = self.redis_client.ttl(key)
                if ttl == -1:  # TTLなし
                    self.redis_client.expire(key, self.config["default_ttl"])
                elif ttl == -2:  # 期限切れ
                    self.redis_client.delete(key)
                    deleted += 1
            
            logger.info(f"✅ キャッシュ最適化: {deleted}キー削除")
            
            return {
                "success": True,
                "deleted_keys": deleted,
                "stats": self.get_cache_stats()
            }
            
        except Exception as e:
            logger.error(f"キャッシュ最適化エラー: {e}")
            return {"success": False, "error": str(e)}

def main():
    optimizer = ManaRedisCacheOptimizer()
    
    import sys
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "stats":
            stats = optimizer.get_cache_stats()
            print(json.dumps(stats, indent=2, ensure_ascii=False))
        
        elif command == "optimize":
            result = optimizer.optimize_cache()
            print(json.dumps(result, indent=2, ensure_ascii=False))
        
        else:
            print("Usage: mana_redis_cache_optimizer.py [stats|optimize]")
    else:
        # デフォルトは統計表示
        stats = optimizer.get_cache_stats()
        if stats.get("available"):
            print("\n📊 Redis Cache Stats:")
            print(f"  使用メモリ: {stats['used_memory_mb']:.2f}MB")
            print(f"  総キー数: {stats['total_keys']}")
            print(f"  ヒット率: {stats['hit_rate']:.2f}%")
        else:
            print("⚠️ Redis利用不可")

if __name__ == "__main__":
    main()

