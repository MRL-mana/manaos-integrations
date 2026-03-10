#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔧 統一モジュール統合ヘルパー
主要サービスへの統一モジュール適用を支援
"""

from typing import Dict, Any, Optional
import logging

# 統一モジュールのインポート
try:
    from manaos_logger import get_logger
    from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
    from manaos_timeout_config import get_timeout_config
    UNIFIED_MODULES_AVAILABLE = True
except ImportError:
    UNIFIED_MODULES_AVAILABLE = False
    get_logger = None
    ManaOSErrorHandler = None
    get_timeout_config = None


def setup_unified_modules(service_name: str) -> Dict[str, Any]:
    """
    統一モジュールをセットアップ
    
    Args:
        service_name: サービス名
        
    Returns:
        統一モジュールの辞書
    """
    if not UNIFIED_MODULES_AVAILABLE:
        # フォールバック: 標準ロガーを使用
        logger = logging.getLogger(service_name)
        return {
            "logger": logger,
            "error_handler": None,
            "timeout_config": None,
            "available": False
        }
    
    # 統一ロガー
    logger = get_logger(service_name)  # type: ignore[operator]
    
    # 統一エラーハンドラー
    error_handler = ManaOSErrorHandler(service_name)  # type: ignore[operator]
    
    # 統一タイムアウト設定
    timeout_config = get_timeout_config()  # type: ignore[operator]
    
    return {
        "logger": logger,
        "error_handler": error_handler,
        "timeout_config": timeout_config,
        "available": True
    }


def apply_error_handler(func):
    """
    エラーハンドリングデコレータ
    
    Usage:
        @apply_error_handler
        def my_function():
            ...
    """
    def wrapper(*args, **kwargs):
        # サービス名を取得（可能な場合）
        service_name = getattr(func, '__module__', 'Unknown')
        
        if UNIFIED_MODULES_AVAILABLE and ManaOSErrorHandler:
            error_handler = ManaOSErrorHandler(service_name)
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error = error_handler.handle_exception(e)
                # Flaskアプリケーションの場合
                try:
                    from flask import jsonify
                    return jsonify(error.to_json_response()), error.status_code  # type: ignore
                except ImportError:
                    # Flask以外の場合
                    raise error  # type: ignore
        else:
            # フォールバック: 標準例外処理
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logging.error(f"エラー: {e}", exc_info=True)
                raise
    
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper


def get_timeout(timeout_type: str) -> float:
    """
    タイムアウト値を取得
    
    Args:
        timeout_type: タイムアウトタイプ（'api_call', 'llm_call'等）
        
    Returns:
        タイムアウト値（秒）
    """
    if UNIFIED_MODULES_AVAILABLE and timeout_config:  # type: ignore[name-defined]
        return timeout_config.get_timeout(timeout_type)  # type: ignore[name-defined]
    else:
        # フォールバック: デフォルト値
        defaults = {
            "health_check": 2.0,
            "api_call": 5.0,
            "llm_call": 30.0,
            "llm_call_heavy": 60.0,
            "workflow_execution": 300.0,
            "script_execution": 60.0,
            "command_execution": 30.0,
            "database_query": 10.0,
            "file_operation": 30.0,
            "network_request": 10.0,
            "external_service": 30.0
        }
        return defaults.get(timeout_type, 30.0)








