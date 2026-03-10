#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📝 ManaOS統一ロガーシステム（最適化版）
ログの統合、フィルタリング、動的レベル調整
"""

import logging
import logging.handlers
import sys
import io
import os
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime
from threading import Lock

# Windows環境での文字エンコーディング設定
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')  # type: ignore[attr-defined]

# ログディレクトリ
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ログフォーマット
LOG_FORMAT = "%(asctime)s [%(levelname)8s] [%(name)s] %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# ログファイル設定
LOG_FILE_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_FILE_BACKUP_COUNT = 5

# グローバル設定
_loggers: Dict[str, logging.Logger] = {}
_logger_lock = Lock()
_log_level = logging.INFO
_log_filters: List[Callable] = []


class LogFilter(logging.Filter):
    """ログフィルタ"""
    
    def __init__(self, filters: List[Callable]):
        super().__init__()
        self.filters = filters
    
    def filter(self, record: logging.LogRecord) -> bool:
        """ログレコードをフィルタリング"""
        for filter_func in self.filters:
            if not filter_func(record):
                return False
        return True


def set_log_level(level: int):
    """
    グローバルログレベルを設定
    
    Args:
        level: ログレベル（logging.DEBUG, INFO, WARNING, ERROR, CRITICAL）
    """
    global _log_level
    _log_level = level
    
    with _logger_lock:
        for logger in _loggers.values():
            logger.setLevel(level)
            for handler in logger.handlers:
                handler.setLevel(level)
    
    logging.getLogger().setLevel(level)


def add_log_filter(filter_func: Callable):
    """
    ログフィルタを追加
    
    Args:
        filter_func: フィルタ関数（LogRecord -> bool）
    """
    global _log_filters
    _log_filters.append(filter_func)
    
    # 既存のロガーにフィルタを適用
    with _logger_lock:
        for logger in _loggers.values():
            for handler in logger.handlers:
                handler.addFilter(LogFilter(_log_filters))


def remove_log_filter(filter_func: Callable):
    """
    ログフィルタを削除
    
    Args:
        filter_func: 削除するフィルタ関数
    """
    global _log_filters
    if filter_func in _log_filters:
        _log_filters.remove(filter_func)


def setup_logger(
    name: str,
    log_file: Optional[Path] = None,
    level: Optional[int] = None,
    console: bool = True,
    file: bool = True,
    max_bytes: int = LOG_FILE_MAX_BYTES,
    backup_count: int = LOG_FILE_BACKUP_COUNT
) -> logging.Logger:
    """
    ロガーをセットアップ（最適化版）
    
    Args:
        name: ロガー名
        log_file: ログファイルパス（Noneの場合は自動生成）
        level: ログレベル（Noneの場合はグローバルレベルを使用）
        console: コンソール出力するか
        file: ファイル出力するか
        max_bytes: ログファイルの最大サイズ
        backup_count: 保持するバックアップファイル数
    
    Returns:
        設定済みロガー
    """
    # 既存のロガーをチェック
    with _logger_lock:
        if name in _loggers:
            return _loggers[name]
        
        logger = logging.getLogger(name)
        logger.setLevel(level or _log_level)
        
        # 既存のハンドラーをクリア
        logger.handlers.clear()
        
        # フォーマッター
        formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
        
        # コンソールハンドラー
        if console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(level or _log_level)
            console_handler.setFormatter(formatter)
            if _log_filters:
                console_handler.addFilter(LogFilter(_log_filters))
            logger.addHandler(console_handler)
        
        # ファイルハンドラー（ローテーション付き）
        if file:
            if log_file is None:
                log_file = LOG_DIR / f"{name}.log"
            
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(level or _log_level)
            file_handler.setFormatter(formatter)
            if _log_filters:
                file_handler.addFilter(LogFilter(_log_filters))
            logger.addHandler(file_handler)
        
        # ロガーを保存
        _loggers[name] = logger
        
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
    with _logger_lock:
        if name in _loggers:
            return _loggers[name]
        
        return setup_logger(name, **kwargs)


def configure_from_env():
    """環境変数からログ設定を読み込む"""
    # ログレベル
    log_level_str = os.getenv("MANAOS_LOG_LEVEL", "INFO").upper()
    log_level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }
    if log_level_str in log_level_map:
        set_log_level(log_level_map[log_level_str])
    
    # ログファイルサイズ
    max_bytes_str = os.getenv("MANAOS_LOG_MAX_BYTES")
    if max_bytes_str:
        try:
            max_bytes = int(max_bytes_str)
            global LOG_FILE_MAX_BYTES
            LOG_FILE_MAX_BYTES = max_bytes
        except ValueError:
            pass
    
    # コンソール出力の有効/無効
    console_enabled = os.getenv("MANAOS_LOG_CONSOLE", "true").lower() == "true"
    if not console_enabled:
        # すべてのコンソールハンドラーを削除
        with _logger_lock:
            for logger in _loggers.values():
                logger.handlers = [
                    h for h in logger.handlers
                    if not isinstance(h, logging.StreamHandler) or h.stream != sys.stdout
                ]


def get_log_stats() -> Dict[str, Any]:
    """ログ統計情報を取得"""
    with _logger_lock:
        total_loggers = len(_loggers)
        total_handlers = sum(len(logger.handlers) for logger in _loggers.values())
        
        # ログファイルサイズを計算
        total_size = 0
        log_files = []
        for log_file in LOG_DIR.glob("*.log*"):
            try:
                size = log_file.stat().st_size
                total_size += size
                log_files.append({
                    "name": log_file.name,
                    "size": size,
                    "size_mb": size / (1024 * 1024)
                })
            except Exception:
                pass
        
        return {
            "total_loggers": total_loggers,
            "total_handlers": total_handlers,
            "log_level": logging.getLevelName(_log_level),
            "log_filters": len(_log_filters),
            "total_log_size_mb": total_size / (1024 * 1024),
            "log_files": log_files
        }


# 環境変数から設定を読み込む
configure_from_env()


def main():
    """テスト用メイン関数"""
    print("ManaOS統一ロガーシステムテスト")
    print("=" * 60)
    
    # ロガーを作成
    logger1 = get_logger("test1")
    logger2 = get_logger("test2")
    
    # テストログ
    logger1.info("テストログ1")
    logger2.warning("テストログ2")
    
    # 統計情報
    stats = get_log_stats()
    print("\n統計情報:")
    print(f"  ロガー数: {stats['total_loggers']}")
    print(f"  ハンドラー数: {stats['total_handlers']}")
    print(f"  ログレベル: {stats['log_level']}")
    print(f"  ログファイル総サイズ: {stats['total_log_size_mb']:.2f} MB")


if __name__ == "__main__":
    main()






















