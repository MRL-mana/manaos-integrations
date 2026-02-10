#!/usr/bin/env python3
"""
MRL Memory Rollout Manager
段階的ロールアウト制御
"""

import os
from typing import Dict, Any, Optional

# 統一モジュールのインポート
try:
    from manaos_logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class RolloutManager:
    """
    段階的ロールアウト制御
    
    環境変数:
    - FWPKM_ENABLED=1
    - FWPKM_WRITE_MODE=readonly|sampled|full
    - FWPKM_WRITE_SAMPLE_RATE=0.1（Write 10%）
    - FWPKM_REVIEW_EFFECT=0|1
    """
    
    def __init__(self):
        """初期化"""
        # 環境変数から読み込み
        self.fwpkm_enabled = os.getenv("FWPKM_ENABLED", "1").lower() in ["1", "true", "yes"]
        self.write_mode = os.getenv("FWPKM_WRITE_MODE", "readonly").lower()
        self.write_sample_rate = float(os.getenv("FWPKM_WRITE_SAMPLE_RATE", "0.1"))
        self.review_effect = os.getenv("FWPKM_REVIEW_EFFECT", "0").lower() in ["1", "true", "yes"]
        
        # モード検証
        if self.write_mode not in ["readonly", "sampled", "full"]:
            logger.warning(f"無効なFWPKM_WRITE_MODE: {self.write_mode}。readonlyにフォールバック")
            self.write_mode = "readonly"
        
        logger.info(
            f"✅ Rollout Manager初期化: "
            f"enabled={self.fwpkm_enabled}, "
            f"write_mode={self.write_mode}, "
            f"sample_rate={self.write_sample_rate}, "
            f"review_effect={self.review_effect}"
        )
    
    def is_write_enabled(self) -> bool:
        """
        書き込みが有効かチェック
        
        Returns:
            書き込みが有効かどうか
        """
        if not self.fwpkm_enabled:
            return False
        
        if self.write_mode == "readonly":
            return False
        
        if self.write_mode == "sampled":
            # サンプリング（リクエストごとに独立判定）
            import random
            return random.random() < self.write_sample_rate
        
        # full
        return True
    
    def is_review_effect_enabled(self) -> bool:
        """
        復習効果が有効かチェック
        
        Returns:
            復習効果が有効かどうか
        """
        return self.fwpkm_enabled and self.review_effect
    
    def get_status(self) -> Dict[str, Any]:
        """
        ステータスを取得
        
        Returns:
            ステータス情報
        """
        return {
            "fwpkm_enabled": self.fwpkm_enabled,
            "write_mode": self.write_mode,
            "write_sample_rate": self.write_sample_rate,
            "review_effect": self.review_effect,
            "write_enabled": self.is_write_enabled()
        }
