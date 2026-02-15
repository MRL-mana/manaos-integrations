"""
LLMキャッシュシステム
同じクエリの結果をキャッシュして高速化
"""

import hashlib
import json
import os
from manaos_logger import get_logger
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime, timedelta
import pickle

logger = get_service_logger("llm-cache")


class LLMCache:
    """LLMキャッシュクラス"""
    
    def __init__(self, cache_dir: Optional[str] = None, ttl_hours: int = 24):
        """
        初期化
        
        Args:
            cache_dir: キャッシュディレクトリ（Noneの場合は自動決定）
            ttl_hours: キャッシュの有効期限（時間）
        """
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            # デフォルトのキャッシュディレクトリ
            if Path("/root").exists() and os.access("/root", os.W_OK):
                self.cache_dir = Path("/root/.llm_cache")
            else:
                self.cache_dir = Path.home() / ".llm_cache"
        
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_hours = ttl_hours
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "total": 0
        }
    
    def _get_cache_key(self, prompt: str, model: str, task_type: str = "rag") -> str:
        """キャッシュキーを生成"""
        key_string = f"{prompt}|{model}|{task_type}"
        return hashlib.sha256(key_string.encode()).hexdigest()
    
    def _get_cache_path(self, cache_key: str) -> Path:
        """キャッシュファイルのパスを取得"""
        return self.cache_dir / f"{cache_key}.cache"
    
    def get(self, prompt: str, model: str, task_type: str = "rag") -> Optional[Dict[str, Any]]:
        """
        キャッシュから結果を取得
        
        Args:
            prompt: プロンプト
            model: モデル名
            task_type: タスクタイプ
            
        Returns:
            キャッシュされた結果、またはNone
        """
        cache_key = self._get_cache_key(prompt, model, task_type)
        cache_path = self._get_cache_path(cache_key)
        
        if not cache_path.exists():
            self.cache_stats["misses"] += 1
            self.cache_stats["total"] += 1
            return None
        
        try:
            with open(cache_path, 'rb') as f:
                cache_data = pickle.load(f)
            
            # TTLチェック
            cache_time = cache_data.get("timestamp")
            if cache_time:
                age = datetime.now() - datetime.fromisoformat(cache_time)
                if age > timedelta(hours=self.ttl_hours):
                    # 期限切れ
                    cache_path.unlink()
                    self.cache_stats["misses"] += 1
                    self.cache_stats["total"] += 1
                    return None
            
            # キャッシュヒット
            self.cache_stats["hits"] += 1
            self.cache_stats["total"] += 1
            logger.info(f"✅ キャッシュヒット: {prompt[:50]}...")
            return cache_data.get("result")
        
        except Exception as e:
            logger.warning(f"⚠️ キャッシュ読み込みエラー: {e}")
            self.cache_stats["misses"] += 1
            self.cache_stats["total"] += 1
            return None
    
    def set(self, prompt: str, model: str, result: Dict[str, Any], task_type: str = "rag"):
        """
        結果をキャッシュに保存
        
        Args:
            prompt: プロンプト
            model: モデル名
            result: 結果データ
            task_type: タスクタイプ
        """
        cache_key = self._get_cache_key(prompt, model, task_type)
        cache_path = self._get_cache_path(cache_key)
        
        try:
            cache_data = {
                "prompt": prompt,
                "model": model,
                "task_type": task_type,
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
            
            with open(cache_path, 'wb') as f:
                pickle.dump(cache_data, f)
            
            logger.debug(f"💾 キャッシュ保存: {prompt[:50]}...")
        
        except Exception as e:
            logger.warning(f"⚠️ キャッシュ保存エラー: {e}")
    
    def clear(self, older_than_hours: Optional[int] = None):
        """
        キャッシュをクリア
        
        Args:
            older_than_hours: 指定時間より古いキャッシュのみ削除（Noneの場合はすべて削除）
        """
        deleted = 0
        for cache_file in self.cache_dir.glob("*.cache"):
            try:
                if older_than_hours:
                    # ファイルの更新時刻をチェック
                    file_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
                    age = datetime.now() - file_time
                    if age <= timedelta(hours=older_than_hours):
                        continue
                
                cache_file.unlink()
                deleted += 1
            except Exception as e:
                logger.warning(f"⚠️ キャッシュ削除エラー: {e}")
        
        logger.info(f"🗑️ キャッシュ削除: {deleted}件")
        return deleted
    
    def get_stats(self) -> Dict[str, Any]:
        """キャッシュ統計を取得"""
        hit_rate = 0.0
        if self.cache_stats["total"] > 0:
            hit_rate = self.cache_stats["hits"] / self.cache_stats["total"]
        
        cache_files = len(list(self.cache_dir.glob("*.cache")))
        
        return {
            "hits": self.cache_stats["hits"],
            "misses": self.cache_stats["misses"],
            "total": self.cache_stats["total"],
            "hit_rate": hit_rate,
            "cache_files": cache_files,
            "cache_dir": str(self.cache_dir)
        }


# グローバルキャッシュインスタンス（シングルトン）
_global_cache: Optional[LLMCache] = None


def get_cache(enable: bool = True, **kwargs) -> Optional[LLMCache]:
    """
    グローバルキャッシュインスタンスを取得
    
    Args:
        enable: キャッシュを有効にするか
        **kwargs: LLMCacheの初期化パラメータ
        
    Returns:
        LLMCacheインスタンス、またはNone
    """
    global _global_cache
    
    if not enable:
        return None
    
    if _global_cache is None:
        _global_cache = LLMCache(**kwargs)
    
    return _global_cache

