#!/usr/bin/env python3
"""
ManaOS 統一ログ設定システム
全サービスで一貫したログ設定を提供

使用例:
    from unified_logging import get_logger
    
    logger = get_logger(__name__)
    logger.info("メッセージ")
"""
import os
import sys
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime
import json
from typing import Optional
from manaos_logger import get_service_logger  # type: ignore


class ManaOSLogFormatter(logging.Formatter):
    """ManaOS標準ログフォーマッター（色付き・構造化）"""
    
    # ログレベル別カラーコード（ANSI）
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def __init__(self, use_colors: bool = True, json_format: bool = False):
        super().__init__()
        self.use_colors = use_colors and sys.stdout.isatty()
        self.json_format = json_format
    
    def format(self, record: logging.LogRecord) -> str:
        if self.json_format:
            return self._format_json(record)
        else:
            return self._format_text(record)
    
    def _format_text(self, record: logging.LogRecord) -> str:
        """テキスト形式でフォーマット"""
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        level = record.levelname
        
        if self.use_colors:
            color = self.COLORS.get(level, self.COLORS['RESET'])
            reset = self.COLORS['RESET']
            level_str = f"{color}[{level:>8}]{reset}"
        else:
            level_str = f"[{level:>8}]"
        
        # モジュール名（短縮）
        module = record.name
        if len(module) > 30:
            module = "..." + module[-27:]
        
        message = record.getMessage()
        
        # 例外情報があれば追加
        if record.exc_info:
            message += "\n" + self.formatException(record.exc_info)
        
        return f"{timestamp} {level_str} [{module:>30}] {message}"
    
    def _format_json(self, record: logging.LogRecord) -> str:
        """JSON形式でフォーマット"""
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "process": record.process,
            "thread": record.thread
        }
        
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # カスタムフィールドを追加
        if hasattr(record, 'service_name'):
            log_data["service_name"] = record.service_name  # type: ignore
        if hasattr(record, 'request_id'):
            log_data["request_id"] = record.request_id  # type: ignore
        
        return json.dumps(log_data, ensure_ascii=False)


class UnifiedLoggingConfig:
    """統一ログ設定マネージャー"""
    
    DEFAULT_CONFIG = {
        "log_dir": "logs",
        "log_level": "INFO",
        "console_output": True,
        "file_output": True,
        "json_format": False,
        "max_file_size_mb": 50,        # ファイルサイズ上限（MB）
        "backup_count": 5,              # ローテーション保持数
        "use_colors": True
    }
    
    def __init__(self, config_file: Optional[str] = None):
        self.config = self.DEFAULT_CONFIG.copy()
        
        # 環境変数から設定を読み込み
        if os.getenv("MANAOS_LOG_LEVEL"):
            self.config["log_level"] = os.getenv("MANAOS_LOG_LEVEL")
        if os.getenv("MANAOS_LOG_DIR"):
            self.config["log_dir"] = os.getenv("MANAOS_LOG_DIR")
        if os.getenv("MANAOS_LOG_JSON"):
            self.config["json_format"] = os.getenv("MANAOS_LOG_JSON").lower() in ("1", "true", "yes")  # type: ignore[union-attr]
        
        # 設定ファイルから読み込み
        if config_file and Path(config_file).exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    self.config.update(loaded)
            except Exception as e:
                print(f"⚠️ ログ設定ファイル読み込みエラー: {e}", file=sys.stderr)
        
        # ログディレクトリを作成
        Path(self.config["log_dir"]).mkdir(parents=True, exist_ok=True)  # type: ignore
    
    def get_log_level(self) -> int:
        """ログレベルを取得"""
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
        return level_map.get(self.config["log_level"].upper(), logging.INFO)
    
    def create_file_handler(self, logger_name: str) -> logging.handlers.RotatingFileHandler:
        """ファイルハンドラーを作成（自動ローテーション付き）"""
        log_file = Path(self.config["log_dir"]) / f"{logger_name}.log"
        max_bytes = self.config["max_file_size_mb"] * 1024 * 1024
        
        handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=self.config["backup_count"],
            encoding='utf-8'
        )
        
        formatter = ManaOSLogFormatter(
            use_colors=False,  # ファイルには色不要
            json_format=self.config["json_format"]
        )
        handler.setFormatter(formatter)
        return handler
    
    def create_console_handler(self) -> logging.StreamHandler:
        """コンソールハンドラーを作成"""
        handler = logging.StreamHandler(sys.stdout)
        
        formatter = ManaOSLogFormatter(
            use_colors=self.config["use_colors"],
            json_format=False  # コンソールは常にテキスト
        )
        handler.setFormatter(formatter)
        return handler


# グローバル設定インスタンス
_config: Optional[UnifiedLoggingConfig] = None
_configured_loggers: set[str] = set()


def configure_logging(config_file: Optional[str] = None, force: bool = False):
    """
    ログ設定を初期化
    
    Args:
        config_file: 設定ファイルパス（オプション）
        force: 既に設定済みでも再設定する
    """
    global _config
    
    if _config is not None and not force:
        return
    
    _config = UnifiedLoggingConfig(config_file)


def get_logger(
    name: str,
    service_name: Optional[str] = None,
    console: Optional[bool] = None,
    file_output: Optional[bool] = None
) -> logging.Logger:
    """
    統一設定されたロガーを取得
    
    Args:
        name: ロガー名（通常は __name__）
        service_name: サービス名（オプション）
        console: コンソール出力を有効化（設定上書き）
        file_output: ファイル出力を有効化（設定上書き）
    
    Returns:
        設定済みロガー
    
    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("起動しました")
    """
    global _config, _configured_loggers
    
    # 設定が未初期化なら初期化
    if _config is None:
        configure_logging()
    
    # ロガーを取得
    logger = logging.getLogger(name)
    
    # 既に設定済みなら返す
    if name in _configured_loggers:
        return logger
    
    # ログレベルを設定
    logger.setLevel(_config.get_log_level())  # type: ignore[union-attr]
    logger.propagate = False  # 親ロガーに伝播しない
    
    # ハンドラーを追加
    should_console = console if console is not None else _config.config["console_output"]  # type: ignore[union-attr]
    should_file = file_output if file_output is not None else _config.config["file_output"]  # type: ignore[union-attr]
    
    if should_console:
        logger.addHandler(_config.create_console_handler())  # type: ignore[union-attr]
    
    if should_file:
        # サービス名からログファイル名を決定
        log_name = service_name or name.split('.')[-1]
        logger.addHandler(_config.create_file_handler(log_name))  # type: ignore[union-attr]
    
    _configured_loggers.add(name)
    
    return logger


def set_log_level(level: str):
    """
    全ロガーのログレベルを変更
    
    Args:
        level: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
    """
    global _config
    
    if _config is None:
        configure_logging()
    
    _config.config["log_level"] = level.upper()  # type: ignore[union-attr]
    new_level = _config.get_log_level()  # type: ignore[union-attr]
    
    # 既存の全ロガーのレベルを更新
    for logger_name in _configured_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(new_level)


# 便利関数
def get_service_logger(service_name: str) -> logging.Logger:
    """
    サービス用のロガーを取得（サービス名をログファイル名に使用）
    
    Args:
        service_name: サービス名（例: "unified_api", "mrl_memory"）
    
    Returns:
        設定済みロガー
    """
    return get_logger(service_name, service_name=service_name)


if __name__ == "__main__":
    # テスト
    print("🧪 統一ログ設定システム - テスト\n")
    
    # 設定を初期化
    configure_logging()
    
    # テストロガーを作成
    logger = get_logger("test_module", service_name="test_service")
    
    print("📝 ログ出力テスト:")
    logger.debug("デバッグメッセージ")
    logger.info("情報メッセージ")
    logger.warning("警告メッセージ")
    logger.error("エラーメッセージ")
    
    try:
        1 / 0
    except Exception:
        logger.exception("例外が発生しました")
    
    print("\n✅ テスト完了")
    print(f"📁 ログファイル: logs/test_service.log")
