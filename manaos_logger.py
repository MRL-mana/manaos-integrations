#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📝 ManaOS 統一ロガーモジュール
全サービスで統一されたログ管理を提供
"""

import logging
import logging.handlers
import sys
import io
from pathlib import Path
from typing import Optional
from datetime import datetime

# Windows環境での文字エンコーディング設定
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ログディレクトリ
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ログフォーマット
LOG_FORMAT = "%(asctime)s [%(levelname)8s] [%(name)s] %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# ログファイル設定
LOG_FILE_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_FILE_BACKUP_COUNT = 5


def setup_logger(
    name: str,
    log_file: Optional[Path] = None,
    level: int = logging.INFO,
    console: bool = True,
    file: bool = True
) -> logging.Logger:
    """
    ロガーをセットアップ
    
    Args:
        name: ロガー名
        log_file: ログファイルパス（Noneの場合は自動生成）
        level: ログレベル
        console: コンソール出力するか
        file: ファイル出力するか
    
    Returns:
        設定済みロガー
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 既存のハンドラーをクリア
    logger.handlers.clear()
    
    # フォーマッター
    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    
    # コンソールハンドラー
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # ファイルハンドラー（ローテーション付き）
    if file:
        if log_file is None:
            log_file = LOG_DIR / f"{name}.log"
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=LOG_FILE_MAX_BYTES,
            backupCount=LOG_FILE_BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str, **kwargs) -> logging.Logger:
    """
    ロガーを取得（既存の場合はそのまま返す）
    
    Args:
        name: ロガー名
        **kwargs: setup_loggerへの追加引数
    
    Returns:
        ロガー
    """
    logger = logging.getLogger(name)
    
    # ハンドラーが設定されていない場合のみセットアップ
    if not logger.handlers:
        setup_logger(name, **kwargs)
    
    return logger


# デフォルトロガー
default_logger = setup_logger("ManaOS", level=logging.INFO)

