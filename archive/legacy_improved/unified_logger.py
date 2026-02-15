#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📝 ManaOS 統一ログ管理システム
集中ログ管理・ログローテーション・エラー通知
"""

import os
import json
import logging
import logging.handlers
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import sys

class UnifiedLogger:
    """統一ログ管理システム"""
    
    def __init__(
        self,
        service_name: str,
        log_dir: Optional[Path] = None,
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5
    ):
        """
        初期化
        
        Args:
            service_name: サービス名
            log_dir: ログディレクトリ
            max_bytes: ログファイルの最大サイズ
            backup_count: 保持するバックアップファイル数
        """
        self.service_name = service_name
        self.log_dir = log_dir or Path(__file__).parent / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # ロガーを設定
        self.logger = logging.getLogger(f"manaos.{service_name}")
        self.logger.setLevel(logging.INFO)
        
        # 既存のハンドラーをクリア
        self.logger.handlers.clear()
        
        # ファイルハンドラー（ローテーション付き）
        log_file = self.log_dir / f"{service_name}.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        
        # エラーファイルハンドラー
        error_log_file = self.log_dir / f"{service_name}_error.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        
        # コンソールハンドラー
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        
        # フォーマッター
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        file_handler.setFormatter(formatter)
        error_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(error_handler)
        self.logger.addHandler(console_handler)
    
    def get_logger(self) -> logging.Logger:
        """ロガーを取得"""
        return self.logger


def setup_unified_logger(service_name: str) -> logging.Logger:
    """統一ロガーをセットアップ"""
    unified_logger = UnifiedLogger(service_name)
    return unified_logger.get_logger()

