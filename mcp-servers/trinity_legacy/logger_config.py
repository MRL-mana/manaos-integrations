#!/usr/bin/env python3
"""
Trinity Reusable Module - Logger Config
統一されたロギング設定
"""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logger(
    name: str = "trinity",
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    log_dir: str = "/root/logs",
    console: bool = True,
    file: bool = True,
    format_string: Optional[str] = None
) -> logging.Logger:
    """
    統一されたロガーをセットアップ
    
    Args:
        name: ロガー名
        level: ログレベル
        log_file: ログファイル名（省略時は name.log）
        log_dir: ログディレクトリ
        console: コンソール出力するか
        file: ファイル出力するか
        format_string: カスタムフォーマット
        
    Returns:
        設定済みロガー
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 既存のハンドラーをクリア
    logger.handlers.clear()
    
    # フォーマット
    if format_string is None:
        format_string = "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s"
    
    formatter = logging.Formatter(format_string, datefmt="%Y-%m-%d %H:%M:%S")
    
    # コンソールハンドラー
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # ファイルハンドラー
    if file:
        # ログディレクトリ作成
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        
        # ログファイル名
        if log_file is None:
            log_file = f"{name}.log"
        
        file_path = log_path / log_file
        
        file_handler = logging.FileHandler(file_path, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def setup_rotating_logger(
    name: str = "trinity",
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    log_dir: str = "/root/logs",
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    console: bool = True
) -> logging.Logger:
    """
    ローテーション機能付きロガーをセットアップ
    
    Args:
        name: ロガー名
        level: ログレベル
        log_file: ログファイル名
        log_dir: ログディレクトリ
        max_bytes: 最大ファイルサイズ
        backup_count: バックアップファイル数
        console: コンソール出力するか
        
    Returns:
        設定済みロガー
    """
    from logging.handlers import RotatingFileHandler
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.handlers.clear()
    
    formatter = logging.Formatter(
        "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # コンソールハンドラー
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # ローテーションファイルハンドラー
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    if log_file is None:
        log_file = f"{name}.log"
    
    file_path = log_path / log_file
    
    rotating_handler = RotatingFileHandler(
        file_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8"
    )
    rotating_handler.setLevel(level)
    rotating_handler.setFormatter(formatter)
    logger.addHandler(rotating_handler)
    
    return logger


# カラー出力用フォーマッター
class ColoredFormatter(logging.Formatter):
    """カラー付きフォーマッター"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        record.levelname = f"{log_color}{record.levelname}{self.COLORS['RESET']}"
        return super().format(record)


def setup_colored_logger(
    name: str = "trinity",
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    log_dir: str = "/root/logs",
    file: bool = True
) -> logging.Logger:
    """
    カラー出力付きロガーをセットアップ
    
    Args:
        name: ロガー名
        level: ログレベル
        log_file: ログファイル名
        log_dir: ログディレクトリ
        file: ファイル出力するか
        
    Returns:
        設定済みロガー
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.handlers.clear()
    
    # カラーフォーマッター（コンソール用）
    console_formatter = ColoredFormatter(
        "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S"
    )
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # 通常フォーマッター（ファイル用）
    if file:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        
        if log_file is None:
            log_file = f"{name}.log"
        
        file_path = log_path / log_file
        
        file_formatter = logging.Formatter(
            "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        
        file_handler = logging.FileHandler(file_path, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger


if __name__ == "__main__":
    # テスト
    logger = setup_colored_logger("test", level=logging.DEBUG)
    
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")
    
    print("\n✅ Log file created: /root/logs/test.log")



