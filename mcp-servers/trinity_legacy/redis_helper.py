#!/usr/bin/env python3
"""
Trinity Reusable Module - Redis Helper
Redis接続と基本操作の共通ヘルパー
"""

import redis
import json
from typing import Optional, Any, Dict
import logging

logger = logging.getLogger(__name__)


class RedisHelper:
    """Redis接続と基本操作のヘルパークラス"""
    
    def __init__(self, host: str = 'localhost', port: int = 6379, db: int = 0, decode_responses: bool = True):
        """
        Redis接続初期化
        
        Args:
            host: Redisホスト
            port: Redisポート
            db: DB番号
            decode_responses: レスポンスをデコードするか
        """
        try:
            self.client = redis.Redis(
                host=host,
                port=port,
                db=db,
                decode_responses=decode_responses
            )
            # 接続確認
            self.client.ping()
            logger.info(f"✅ Redis connected: {host}:{port}/{db}")
        except redis.ConnectionError as e:
            logger.error(f"❌ Redis connection failed: {e}")
            raise
    
    def set_json(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """
        JSONとして保存
        
        Args:
            key: キー
            value: 値（辞書・リスト）
            expire: 有効期限（秒）
            
        Returns:
            成功したらTrue
        """
        try:
            json_str = json.dumps(value, ensure_ascii=False)
            if expire:
                return self.client.setex(key, expire, json_str)
            else:
                return self.client.set(key, json_str)
        except Exception as e:
            logger.error(f"❌ set_json failed: {e}")
            return False
    
    def get_json(self, key: str, default: Any = None) -> Any:
        """
        JSONとして取得
        
        Args:
            key: キー
            default: デフォルト値
            
        Returns:
            取得した値（辞書・リスト）、存在しない場合はdefault
        """
        try:
            value = self.client.get(key)
            if value is None:
                return default
            return json.loads(value)
        except Exception as e:
            logger.error(f"❌ get_json failed: {e}")
            return default
    
    def exists(self, key: str) -> bool:
        """キーが存在するか確認"""
        return self.client.exists(key) > 0
    
    def delete(self, key: str) -> bool:
        """キーを削除"""
        return self.client.delete(key) > 0
    
    def keys(self, pattern: str = "*") -> list:
        """パターンマッチでキー一覧取得"""
        return self.client.keys(pattern)
    
    def set_hash(self, key: str, mapping: Dict[str, Any]) -> bool:
        """ハッシュとして保存"""
        try:
            return self.client.hset(key, mapping=mapping) >= 0
        except Exception as e:
            logger.error(f"❌ set_hash failed: {e}")
            return False
    
    def get_hash(self, key: str) -> Dict:
        """ハッシュとして取得"""
        try:
            return self.client.hgetall(key)
        except Exception as e:
            logger.error(f"❌ get_hash failed: {e}")
            return {}
    
    def list_push(self, key: str, *values) -> int:
        """リストに追加（右側）"""
        return self.client.rpush(key, *values)
    
    def list_pop(self, key: str) -> Optional[str]:
        """リストから取得（左側）"""
        return self.client.lpop(key)
    
    def list_range(self, key: str, start: int = 0, end: int = -1) -> list:
        """リストの範囲取得"""
        return self.client.lrange(key, start, end)
    
    def set_add(self, key: str, *members) -> int:
        """セットに追加"""
        return self.client.sadd(key, *members)
    
    def set_members(self, key: str) -> set:
        """セットのメンバー取得"""
        return self.client.smembers(key)
    
    def set_remove(self, key: str, *members) -> int:
        """セットから削除"""
        return self.client.srem(key, *members)
    
    def ttl(self, key: str) -> int:
        """TTL取得（秒）"""
        return self.client.ttl(key)
    
    def expire(self, key: str, seconds: int) -> bool:
        """有効期限設定"""
        return self.client.expire(key, seconds)
    
    def close(self):
        """接続クローズ"""
        try:
            self.client.close()
            logger.info("✅ Redis connection closed")
        except Exception as e:
            logger.error(f"❌ Redis close failed: {e}")


# シングルトンインスタンス（必要に応じて使用）
_default_instance: Optional[RedisHelper] = None


def get_redis(host: str = 'localhost', port: int = 6379, db: int = 0) -> RedisHelper:
    """
    デフォルトのRedisインスタンスを取得（シングルトン）
    
    Args:
        host: Redisホスト
        port: Redisポート
        db: DB番号
        
    Returns:
        RedisHelperインスタンス
    """
    global _default_instance
    if _default_instance is None:
        _default_instance = RedisHelper(host, port, db)
    return _default_instance


if __name__ == "__main__":
    # テスト
    logging.basicConfig(level=logging.INFO)
    
    redis_client = RedisHelper()
    
    # JSON保存・取得
    redis_client.set_json("test:data", {"name": "Mana", "age": 25})
    data = redis_client.get_json("test:data")
    print(f"✅ JSON: {data}")
    
    # ハッシュ
    redis_client.set_hash("test:hash", {"key1": "value1", "key2": "value2"})
    hash_data = redis_client.get_hash("test:hash")
    print(f"✅ Hash: {hash_data}")
    
    # リスト
    redis_client.list_push("test:list", "item1", "item2", "item3")
    list_data = redis_client.list_range("test:list")
    print(f"✅ List: {list_data}")
    
    # セット
    redis_client.set_add("test:set", "a", "b", "c")
    set_data = redis_client.set_members("test:set")
    print(f"✅ Set: {set_data}")
    
    # クリーンアップ
    redis_client.delete("test:data")
    redis_client.delete("test:hash")
    redis_client.delete("test:list")
    redis_client.delete("test:set")
    
    print("✅ All tests passed")



