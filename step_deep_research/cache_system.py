#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
キャッシュシステム（同一クエリの再調査防止）
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from manaos_logger import get_logger

logger = get_logger(__name__)


class CacheSystem:
    """キャッシュシステム"""
    
    def __init__(self, cache_dir: str = "logs/step_deep_research/cache"):
        """
        初期化
        
        Args:
            cache_dir: キャッシュディレクトリ
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # キャッシュ有効期限（デフォルト7日）
        self.cache_ttl_days = 7
    
    def generate_cache_key(
        self,
        query: str,
        scope: Optional[str] = None,
        time_window: Optional[str] = None
    ) -> str:
        """
        キャッシュキー生成
        
        Args:
            query: クエリ
            scope: スコープ（オプション）
            time_window: 時間ウィンドウ（オプション）
        
        Returns:
            キャッシュキー（ハッシュ）
        """
        # クエリを正規化（空白除去、小文字化）
        normalized_query = " ".join(query.lower().split())
        
        # キー生成
        key_parts = [normalized_query]
        if scope:
            key_parts.append(scope)
        if time_window:
            key_parts.append(time_window)
        
        key_string = "|".join(key_parts)
        cache_key = hashlib.sha256(key_string.encode()).hexdigest()
        
        return cache_key
    
    def get_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        キャッシュ取得
        
        Args:
            cache_key: キャッシュキー
        
        Returns:
            キャッシュデータ（Noneの場合はキャッシュなし）
        """
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
            
            # TTLチェック
            cached_at = datetime.fromisoformat(cache_data.get("cached_at", ""))
            age_days = (datetime.now() - cached_at).days
            
            if age_days > self.cache_ttl_days:
                logger.info(f"Cache expired: {cache_key} (age: {age_days} days)")
                cache_file.unlink()  # 期限切れキャッシュを削除
                return None
            
            logger.info(f"Cache hit: {cache_key}")
            return cache_data
            
        except Exception as e:
            logger.warning(f"Cache read error: {e}")
            return None
    
    def set_cache(
        self,
        cache_key: str,
        report: str,
        score: int,
        citations: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        キャッシュ保存
        
        Args:
            cache_key: キャッシュキー
            report: レポート
            score: スコア
            citations: 引用リスト
            metadata: メタデータ（オプション）
        """
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        cache_data = {
            "cached_at": datetime.now().isoformat(),
            "report": report,
            "score": score,
            "citations": citations,
            "metadata": metadata or {}
        }
        
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Cache saved: {cache_key}")
            
        except Exception as e:
            logger.warning(f"Cache write error: {e}")
    
    def should_use_cache(self, cache_data: Dict[str, Any], min_score: int = 18) -> bool:
        """
        キャッシュを使用すべきか判定
        
        Args:
            cache_data: キャッシュデータ
            min_score: 最低スコア
        
        Returns:
            使用すべきか
        """
        score = cache_data.get("score", 0)
        return score >= min_score


