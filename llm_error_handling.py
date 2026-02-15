"""
エラーハンドリング強化
詳細なエラー情報とリカバリー
"""

from manaos_logger import get_logger, get_service_logger
import logging
import traceback
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
from pathlib import Path
import json

logger = get_service_logger("llm-error-handling")


class ErrorType(Enum):
    """エラータイプ"""
    NETWORK = "network"
    TIMEOUT = "timeout"
    MODEL_ERROR = "model_error"
    VALIDATION_ERROR = "validation_error"
    CACHE_ERROR = "cache_error"
    UNKNOWN = "unknown"


class ErrorSeverity(Enum):
    """エラー重要度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorHandler:
    """エラーハンドラー"""
    
    def __init__(self, log_dir: Optional[str] = None):
        """
        初期化
        
        Args:
            log_dir: ログディレクトリ
        """
        if log_dir:
            self.log_dir = Path(log_dir)
        else:
            self.log_dir = Path.home() / "llm_error_logs"
        
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.error_log_file = self.log_dir / "errors.json"
        self.errors = self._load_errors()
    
    def _load_errors(self) -> List[Dict[str, Any]]:
        """エラーログを読み込み"""
        if self.error_log_file.exists():
            try:
                with open(self.error_log_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"⚠️ エラーログ読み込みエラー: {e}")
        
        return []
    
    def _save_errors(self):
        """エラーログを保存"""
        try:
            with open(self.error_log_file, 'w', encoding='utf-8') as f:
                json.dump(self.errors, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"⚠️ エラーログ保存エラー: {e}")
    
    def classify_error(self, error: Exception) -> tuple[ErrorType, ErrorSeverity]:
        """
        エラーを分類
        
        Args:
            error: エラーオブジェクト
            
        Returns:
            (エラータイプ, 重要度)のタプル
        """
        error_str = str(error).lower()
        error_type_str = type(error).__name__.lower()
        
        # ネットワークエラー
        if any(keyword in error_str for keyword in ["connection", "network", "timeout", "refused"]):
            if "timeout" in error_str:
                return ErrorType.TIMEOUT, ErrorSeverity.MEDIUM
            return ErrorType.NETWORK, ErrorSeverity.HIGH
        
        # モデルエラー
        if any(keyword in error_str for keyword in ["model", "ollama", "llm", "generation"]):
            return ErrorType.MODEL_ERROR, ErrorSeverity.HIGH
        
        # バリデーションエラー
        if any(keyword in error_type_str for keyword in ["value", "type", "attribute"]):
            return ErrorType.VALIDATION_ERROR, ErrorSeverity.LOW
        
        # キャッシュエラー
        if any(keyword in error_str for keyword in ["cache", "redis"]):
            return ErrorType.CACHE_ERROR, ErrorSeverity.LOW
        
        return ErrorType.UNKNOWN, ErrorSeverity.MEDIUM
    
    def record_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        recoverable: bool = True
    ) -> Dict[str, Any]:
        """
        エラーを記録
        
        Args:
            error: エラーオブジェクト
            context: コンテキスト情報
            recoverable: リカバリー可能かどうか
            
        Returns:
            エラー情報
        """
        error_type, severity = self.classify_error(error)
        
        error_info = {
            "timestamp": datetime.now().isoformat(),
            "error_type": error_type.value,
            "severity": severity.value,
            "error_message": str(error),
            "error_class": type(error).__name__,
            "traceback": traceback.format_exc(),
            "context": context or {},
            "recoverable": recoverable
        }
        
        self.errors.append(error_info)
        
        # 最新1000件のみ保持
        if len(self.errors) > 1000:
            self.errors = self.errors[-1000:]
        
        self._save_errors()
        
        # ログに記録
        log_level = {
            ErrorSeverity.LOW: logging.DEBUG,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL
        }[severity]
        
        logger.log(
            log_level,
            f"[{error_type.value}] {error}: {context}"
        )
        
        return error_info
    
    def get_recovery_strategy(self, error_type: ErrorType) -> Dict[str, Any]:
        """
        リカバリー戦略を取得
        
        Args:
            error_type: エラータイプ
            
        Returns:
            リカバリー戦略
        """
        strategies = {
            ErrorType.NETWORK: {
                "retry": True,
                "max_retries": 3,
                "backoff": "exponential",
                "fallback": "use_cache"
            },
            ErrorType.TIMEOUT: {
                "retry": True,
                "max_retries": 2,
                "backoff": "linear",
                "fallback": "reduce_context"
            },
            ErrorType.MODEL_ERROR: {
                "retry": True,
                "max_retries": 2,
                "backoff": "exponential",
                "fallback": "switch_model"
            },
            ErrorType.VALIDATION_ERROR: {
                "retry": False,
                "max_retries": 0,
                "backoff": None,
                "fallback": "return_error"
            },
            ErrorType.CACHE_ERROR: {
                "retry": False,
                "max_retries": 0,
                "backoff": None,
                "fallback": "skip_cache"
            },
            ErrorType.UNKNOWN: {
                "retry": True,
                "max_retries": 1,
                "backoff": "linear",
                "fallback": "return_error"
            }
        }
        
        return strategies.get(error_type, strategies[ErrorType.UNKNOWN])
    
    def get_error_stats(self) -> Dict[str, Any]:
        """エラー統計を取得"""
        if not self.errors:
            return {
                "total_errors": 0,
                "by_type": {},
                "by_severity": {},
                "recoverable_rate": 0.0
            }
        
        by_type = {}
        by_severity = {}
        recoverable_count = 0
        
        for error in self.errors:
            error_type = error["error_type"]
            severity = error["severity"]
            
            by_type[error_type] = by_type.get(error_type, 0) + 1
            by_severity[severity] = by_severity.get(severity, 0) + 1
            
            if error.get("recoverable", False):
                recoverable_count += 1
        
        return {
            "total_errors": len(self.errors),
            "by_type": by_type,
            "by_severity": by_severity,
            "recoverable_rate": recoverable_count / len(self.errors),
            "recent_errors": self.errors[-10:]  # 最新10件
        }


def safe_execute(
    func,
    error_handler: Optional[ErrorHandler] = None,
    context: Optional[Dict[str, Any]] = None,
    default_return: Any = None
) -> Any:
    """
    安全に実行（エラーハンドリング付き）
    
    Args:
        func: 実行する関数
        error_handler: エラーハンドラー
        context: コンテキスト情報
        default_return: エラー時のデフォルト戻り値
        
    Returns:
        関数の結果、またはデフォルト値
    """
    try:
        return func()
    except Exception as e:
        if error_handler:
            error_info = error_handler.record_error(e, context)
            recovery_strategy = error_handler.get_recovery_strategy(
                ErrorType(error_info["error_type"])
            )
            
            if recovery_strategy.get("retry", False):
                # リトライロジックは呼び出し側で実装
                pass
        
        return default_return

