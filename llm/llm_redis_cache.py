"""
Redis統合キャッシュシステム
分散キャッシュと永続化対応
"""

import json
from manaos_logger import get_logger, get_service_logger
import hashlib
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

logger = get_service_logger("llm-redis-cache")

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.debug("Redisが利用できません。通常のキャッシュを使用します。")


class RedisCache:
    """Redis統合キャッシュクラス"""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        ttl_hours: int = 24,
        enable: bool = True
    ):
        """
        初期化
        
        Args:
            host: Redisホスト
            port: Redisポート
            db: Redisデータベース番号
            password: Redisパスワード
            ttl_hours: TTL（時間）
            enable: キャッシュを有効にするか
        """
        self.enable = enable
        self.ttl_seconds = ttl_hours * 3600
        
        if not enable:
            self.redis_client = None
            return
        
        if not REDIS_AVAILABLE:
            logger.debug("Redisが利用できません。キャッシュは無効化されます。")
            self.redis_client = None
            return
        
        try:
            self.redis_client = redis.Redis(  # type: ignore[possibly-unbound]
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=True,
                socket_connect_timeout=5
            )
            # 接続テスト
            self.redis_client.ping()
            logger.info(f"✅ Redisキャッシュ接続成功: {host}:{port}")
        except Exception as e:
            logger.warning(f"⚠️ Redis接続失敗: {e}。キャッシュは無効化されます。")
            self.redis_client = None
    
    def _get_cache_key(self, prompt: str, model: str, task_type: str = "rag") -> str:
        """キャッシュキーを生成"""
        key_string = f"{task_type}:{model}:{prompt}"
        return hashlib.sha256(key_string.encode()).hexdigest()
    
    def get(self, prompt: str, model: str, task_type: str = "rag") -> Optional[Dict[str, Any]]:
        """
        キャッシュから取得
        
        Args:
            prompt: プロンプト
            model: モデル名
            task_type: タスクタイプ
            
        Returns:
            キャッシュされた結果、またはNone
        """
        if not self.enable or not self.redis_client:
            return None
        
        try:
            cache_key = self._get_cache_key(prompt, model, task_type)
            cached_data = self.redis_client.get(cache_key)
            
            if cached_data:
                result = json.loads(cached_data)
                logger.debug(f"✅ Redisキャッシュヒット: {cache_key[:16]}...")
                return result
            
            return None
        except Exception as e:
            logger.warning(f"⚠️ Redis取得エラー: {e}")
            return None
    
    def set(
        self,
        prompt: str,
        model: str,
        result: Dict[str, Any],
        task_type: str = "rag"
    ) -> bool:
        """
        キャッシュに保存
        
        Args:
            prompt: プロンプト
            model: モデル名
            result: 結果データ
            task_type: タスクタイプ
            
        Returns:
            成功したかどうか
        """
        if not self.enable or not self.redis_client:
            return False
        
        try:
            cache_key = self._get_cache_key(prompt, model, task_type)
            cache_data = {
                **result,
                "cached_at": datetime.now().isoformat(),
                "model": model,
                "task_type": task_type
            }
            
            self.redis_client.setex(
                cache_key,
                self.ttl_seconds,
                json.dumps(cache_data, ensure_ascii=False)
            )
            
            logger.debug(f"✅ Redisキャッシュ保存: {cache_key[:16]}...")
            return True
        except Exception as e:
            logger.warning(f"⚠️ Redis保存エラー: {e}")
            return False
    
    def clear(self, pattern: Optional[str] = None) -> int:
        """
        キャッシュをクリア
        
        Args:
            pattern: パターン（Noneの場合は全て）
            
        Returns:
            削除されたキー数
        """
        if not self.redis_client:
            return 0
        
        try:
            if pattern:
                keys = self.redis_client.keys(pattern)
            else:
                keys = self.redis_client.keys("*")
            
            if keys:
                deleted = self.redis_client.delete(*keys)
                logger.info(f"🗑️ Redisキャッシュクリア: {deleted}件")
                return deleted
            
            return 0
        except Exception as e:
            logger.warning(f"⚠️ Redisクリアエラー: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """統計情報を取得"""
        if not self.redis_client:
            return {
                "enabled": False,
                "connected": False
            }
        
        try:
            info = self.redis_client.info()
            keys_count = len(self.redis_client.keys("*"))
            
            return {
                "enabled": True,
                "connected": True,
                "keys_count": keys_count,
                "memory_used": info.get("used_memory_human", "N/A"),
                "hits": info.get("keyspace_hits", 0),
                "misses": info.get("keyspace_misses", 0)
            }
        except Exception as e:
            logger.warning(f"⚠️ Redis統計取得エラー: {e}")
            return {
                "enabled": True,
                "connected": False,
                "error": str(e)
            }


def get_redis_cache(
    enable: bool = True,
    host: str = "localhost",
    port: int = 6379,
    **kwargs
) -> RedisCache:
    """
    Redisキャッシュインスタンスを取得
    
    Args:
        enable: キャッシュを有効にするか
        host: Redisホスト
        port: Redisポート
        **kwargs: その他のパラメータ
        
    Returns:
        RedisCacheインスタンス
    """
    return RedisCache(enable=enable, host=host, port=port, **kwargs)

