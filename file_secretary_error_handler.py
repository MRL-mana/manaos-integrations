#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File Secretary エラーハンドリング強化
統一エラーハンドリングとリトライ機能
"""

import time
from typing import Optional, Callable, Any
from functools import wraps

from manaos_logger import get_logger, get_service_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity

logger = get_service_logger("file-secretary-error-handler")
error_handler = ManaOSErrorHandler("FileSecretary")


def retry_on_error(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    エラー時のリトライデコレータ
    
    Args:
        max_retries: 最大リトライ回数
        delay: 初回リトライまでの遅延（秒）
        backoff: リトライ間隔の倍率
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            retry_count = 0
            current_delay = delay
            
            while retry_count < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retry_count += 1
                    if retry_count >= max_retries:
                        error_handler.handle_exception(
                            e,
                            context={"function": func.__name__, "retry_count": retry_count},
                            user_message=f"{func.__name__}の実行に失敗しました（{max_retries}回リトライ後）"
                        )
                        raise
                    
                    logger.warning(f"{func.__name__}実行エラー（リトライ {retry_count}/{max_retries}）: {e}")
                    time.sleep(current_delay)
                    current_delay *= backoff
            
            return None
        return wrapper
    return decorator


def safe_database_operation(operation_name: str):
    """
    データベース操作の安全な実行デコレータ
    
    Args:
        operation_name: 操作名
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_handler.handle_exception(
                    e,
                    context={"operation": operation_name, "function": func.__name__},
                    user_message=f"データベース操作に失敗しました: {operation_name}"
                )
                return None
        return wrapper
    return decorator


class FileSecretaryError(Exception):
    """File Secretary専用エラー"""
    pass


class DatabaseError(FileSecretaryError):
    """データベースエラー"""
    pass


class FileIndexError(FileSecretaryError):
    """ファイルインデックスエラー"""
    pass


class OrganizeError(FileSecretaryError):
    """整理エラー"""
    pass






















