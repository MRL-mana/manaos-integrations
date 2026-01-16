#!/usr/bin/env python3
"""
MRL Memory Kill Switch
環境変数で即停止できる仕組み
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


class KillSwitch:
    """
    Kill Switch
    
    環境変数で即停止:
    - FWPKM_WRITE_ENABLED=0/1
    - FWPKM_ENABLED=0/1
    """
    
    def __init__(self):
        """初期化"""
        # 環境変数から読み込み
        self.fwpkm_enabled = os.getenv("FWPKM_ENABLED", "1").lower() in ["1", "true", "yes"]
        self.fwpkm_write_enabled = os.getenv("FWPKM_WRITE_ENABLED", "1").lower() in ["1", "true", "yes"]
        
        logger.info(f"✅ Kill Switch初期化: FWPKM={self.fwpkm_enabled}, Write={self.fwpkm_write_enabled}")
    
    def is_enabled(self) -> bool:
        """
        FWPKMが有効かチェック
        
        Returns:
            有効かどうか
        """
        return self.fwpkm_enabled
    
    def is_write_enabled(self) -> bool:
        """
        FWPKM書き込みが有効かチェック
        
        Returns:
            書き込みが有効かどうか
        """
        return self.fwpkm_enabled and self.fwpkm_write_enabled
    
    def check_and_raise(self, operation: str = "write"):
        """
        操作が許可されているかチェックして、許可されていなければ例外を発生
        
        Args:
            operation: 操作タイプ（"write", "read", "all"）
        
        Raises:
            RuntimeError: 操作が無効な場合
        """
        if operation == "write" and not self.is_write_enabled():
            raise RuntimeError(
                f"FWPKM書き込みが無効です。"
                f"環境変数 FWPKM_WRITE_ENABLED=1 を設定してください。"
            )
        
        if not self.is_enabled():
            raise RuntimeError(
                f"FWPKMが無効です。"
                f"環境変数 FWPKM_ENABLED=1 を設定してください。"
            )
    
    def get_status(self) -> Dict[str, Any]:
        """
        ステータスを取得
        
        Returns:
            ステータス情報
        """
        return {
            "fwpkm_enabled": self.fwpkm_enabled,
            "fwpkm_write_enabled": self.fwpkm_write_enabled,
            "read_only_mode": self.fwpkm_enabled and not self.fwpkm_write_enabled
        }
