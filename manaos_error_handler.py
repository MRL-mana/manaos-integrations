#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔧 ManaOS 統一エラーハンドリングモジュール
全サービスで統一されたエラーハンドリングを提供
"""

from manaos_logger import get_logger
import traceback
from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict

logger = get_service_logger("manaos-error-handler")


class ErrorSeverity(Enum):
    """エラー深刻度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """エラーカテゴリ"""
    NETWORK = "network"
    TIMEOUT = "timeout"
    VALIDATION = "validation"
    CONFIGURATION = "configuration"
    RESOURCE = "resource"
    EXTERNAL_SERVICE = "external_service"
    INTERNAL = "internal"
    UNKNOWN = "unknown"


@dataclass


class ManaOSError:
    """ManaOS統一エラー形式"""
    error_code: str
    message: str
    category: ErrorCategory
    severity: ErrorSeverity
    service_name: str
    timestamp: str
    details: Optional[Dict[str, Any]] = None
    stack_trace: Optional[str] = None
    retryable: bool = False
    user_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        result = asdict(self)
        result["category"] = self.category.value
        result["severity"] = self.severity.value
        return result
    
    def to_json_response(self, status_code: int = 500) -> Dict[str, Any]:
        """JSONレスポンス形式に変換"""
        return {
            "status": "error",
            "error": {
                "code": self.error_code,
                "message": self.message,
                "user_message": self.user_message or self.message,
                "category": self.category.value,
                "severity": self.severity.value,
                "service": self.service_name,
                "timestamp": self.timestamp,
                "retryable": self.retryable,
                "details": self.details
            }
        }


class ManaOSErrorHandler:
    """ManaOS統一エラーハンドラー"""
    
    def __init__(self, service_name: str):
        """
        初期化
        
        Args:
            service_name: サービス名
        """
        self.service_name = service_name
    
    def handle_exception(
        self,
        exception: Exception,
        context: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None
    ) -> ManaOSError:
        """
        例外を処理してManaOSErrorに変換
        
        Args:
            exception: 例外オブジェクト
            context: コンテキスト情報
            user_message: ユーザー向けメッセージ
        
        Returns:
            ManaOSError
        """
        error_type = type(exception).__name__
        error_message = str(exception)
        stack_trace = traceback.format_exc()
        
        # エラータイプに応じた分類
        category, severity, retryable = self._classify_error(exception)
        
        # エラーコード生成
        error_code = self._generate_error_code(category, error_type)
        
        # ManaOSError作成
        manaos_error = ManaOSError(
            error_code=error_code,
            message=error_message,
            category=category,
            severity=severity,
            service_name=self.service_name,
            timestamp=datetime.now().isoformat(),
            details=context,
            stack_trace=stack_trace,
            retryable=retryable,
            user_message=user_message
        )
        
        # ログ出力
        self._log_error(manaos_error)
        
        return manaos_error
    
    def handle_httpx_error(
        self,
        exception: Exception,
        url: Optional[str] = None,
        method: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ManaOSError:
        """
        httpxエラーを処理
        
        Args:
            exception: httpx例外
            url: リクエストURL
            method: HTTPメソッド
            context: コンテキスト情報
        
        Returns:
            ManaOSError
        """
        import httpx
        
        error_context = context or {}
        if url:
            error_context["url"] = url
        if method:
            error_context["method"] = method
        
        if isinstance(exception, httpx.ConnectError):
            category = ErrorCategory.NETWORK
            severity = ErrorSeverity.MEDIUM
            retryable = True
            user_message = "サービスに接続できませんでした。しばらく待ってから再試行してください。"
        elif isinstance(exception, httpx.TimeoutException):
            category = ErrorCategory.TIMEOUT
            severity = ErrorSeverity.MEDIUM
            retryable = True
            user_message = "リクエストがタイムアウトしました。しばらく待ってから再試行してください。"
        elif isinstance(exception, httpx.HTTPStatusError):
            category = ErrorCategory.EXTERNAL_SERVICE
            severity = ErrorSeverity.MEDIUM
            retryable = exception.response.status_code >= 500
            user_message = f"外部サービスエラー: HTTP {exception.response.status_code}"
            error_context["status_code"] = exception.response.status_code
        else:
            category = ErrorCategory.NETWORK
            severity = ErrorSeverity.MEDIUM
            retryable = True
            user_message = "ネットワークエラーが発生しました。"
        
        error_code = self._generate_error_code(category, type(exception).__name__)
        
        manaos_error = ManaOSError(
            error_code=error_code,
            message=str(exception),
            category=category,
            severity=severity,
            service_name=self.service_name,
            timestamp=datetime.now().isoformat(),
            details=error_context,
            stack_trace=traceback.format_exc(),
            retryable=retryable,
            user_message=user_message
        )
        
        self._log_error(manaos_error)
        
        return manaos_error
    
    def handle_validation_error(
        self,
        field: str,
        value: Any,
        reason: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ManaOSError:
        """
        バリデーションエラーを処理
        
        Args:
            field: フィールド名
            value: 値
            reason: エラー理由
            context: コンテキスト情報
        
        Returns:
            ManaOSError
        """
        error_context = context or {}
        error_context["field"] = field
        error_context["value"] = str(value)
        error_context["reason"] = reason
        
        manaos_error = ManaOSError(
            error_code="VALIDATION_ERROR",
            message=f"Validation error: {field} - {reason}",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            service_name=self.service_name,
            timestamp=datetime.now().isoformat(),
            details=error_context,
            retryable=False,
            user_message=f"入力値が不正です: {field}"
        )
        
        self._log_error(manaos_error)
        
        return manaos_error
    
    def handle_config_error(
        self,
        config_key: str,
        reason: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ManaOSError:
        """
        設定エラーを処理
        
        Args:
            config_key: 設定キー
            reason: エラー理由
            context: コンテキスト情報
        
        Returns:
            ManaOSError
        """
        error_context = context or {}
        error_context["config_key"] = config_key
        error_context["reason"] = reason
        
        manaos_error = ManaOSError(
            error_code="CONFIG_ERROR",
            message=f"Configuration error: {config_key} - {reason}",
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.HIGH,
            service_name=self.service_name,
            timestamp=datetime.now().isoformat(),
            details=error_context,
            retryable=False,
            user_message=f"設定エラー: {config_key}"
        )
        
        self._log_error(manaos_error)
        
        return manaos_error
    
    def _classify_error(
        self,
        exception: Exception
    ) -> tuple[ErrorCategory, ErrorSeverity, bool]:
        """
        エラーを分類
        
        Args:
            exception: 例外オブジェクト
        
        Returns:
            (category, severity, retryable)
        """
        error_str = str(exception).lower()
        error_type = type(exception).__name__
        
        # ネットワークエラー
        if "connection" in error_str or "network" in error_str:
            return ErrorCategory.NETWORK, ErrorSeverity.MEDIUM, True
        
        # タイムアウトエラー
        if "timeout" in error_str or "timed out" in error_str:
            return ErrorCategory.TIMEOUT, ErrorSeverity.MEDIUM, True
        
        # リソースエラー
        if "memory" in error_str or "resource" in error_str:
            return ErrorCategory.RESOURCE, ErrorSeverity.HIGH, False
        
        # 設定エラー
        if "config" in error_str or "setting" in error_str:
            return ErrorCategory.CONFIGURATION, ErrorSeverity.HIGH, False
        
        # バリデーションエラー
        if "validation" in error_str or "invalid" in error_str:
            return ErrorCategory.VALIDATION, ErrorSeverity.LOW, False
        
        # デフォルト
        return ErrorCategory.UNKNOWN, ErrorSeverity.MEDIUM, False
    
    def _generate_error_code(
        self,
        category: ErrorCategory,
        error_type: str
    ) -> str:
        """
        エラーコード生成
        
        Args:
            category: エラーカテゴリ
            error_type: エラータイプ
        
        Returns:
            エラーコード
        """
        category_code = category.value.upper()[:3]
        type_code = error_type.upper()[:5]
        return f"{category_code}_{type_code}"
    
    def _log_error(self, error: ManaOSError):
        """
        エラーをログ出力
        
        Args:
            error: ManaOSError
        """
        log_message = f"[{error.error_code}] {error.message}"
        
        if error.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message, extra={"error": error.to_dict()})
        elif error.severity == ErrorSeverity.HIGH:
            logger.error(log_message, extra={"error": error.to_dict()})
        elif error.severity == ErrorSeverity.MEDIUM:
            logger.warning(log_message, extra={"error": error.to_dict()})
        else:
            logger.info(log_message, extra={"error": error.to_dict()})
        
        # スタックトレースも出力（DEBUGレベル）
        if error.stack_trace:
            logger.debug(error.stack_trace)


# Flask用デコレータ


def handle_errors(service_name: str):
    """
    エラーハンドリングデコレータ
    
    Usage:
        @handle_errors("Intent Router")
        def my_function():
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            handler = ManaOSErrorHandler(service_name)
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error = handler.handle_exception(e)
                from flask import jsonify
                return jsonify(error.to_json_response()), 500
        return wrapper
    return decorator

