#!/usr/bin/env python3
"""
🔄 ManaOS インテリジェントリトライシステム
指数バックオフ・サーキットブレーカー・動的リトライ間隔
"""

import os
import json
import time
import httpx
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable, TypeVar, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
from functools import wraps
import asyncio
import inspect

# 統一モジュールのインポート
from manaos_logger import get_logger, get_service_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from manaos_timeout_config import get_timeout_config

# ロガーの初期化
logger = get_service_logger("intelligent-retry")

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("IntelligentRetry")

# タイムアウト設定の取得
timeout_config = get_timeout_config()

T = TypeVar('T')


class RetryStrategy(str, Enum):
    """リトライ戦略"""
    EXPONENTIAL_BACKOFF = "exponential_backoff"  # 指数バックオフ
    LINEAR_BACKOFF = "linear_backoff"  # 線形バックオフ
    FIXED_INTERVAL = "fixed_interval"  # 固定間隔
    CUSTOM = "custom"  # カスタム


class CircuitState(str, Enum):
    """サーキットブレーカーの状態"""
    CLOSED = "closed"  # 正常（リクエスト通過）
    OPEN = "open"  # 開放（リクエスト拒否）
    HALF_OPEN = "half_open"  # 半開放（テストリクエスト許可）


@dataclass
class RetryConfig:
    """リトライ設定（最適化済み）"""
    max_retries: int = 2  # 3 → 2に削減（通信速度向上）
    initial_delay: float = 0.5  # 1.0 → 0.5に短縮
    max_delay: float = 10.0  # 60.0 → 10.0に短縮（通信速度向上）
    exponential_base: float = 2.0
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    retryable_errors: List[str] = None  # type: ignore
    
    def __post_init__(self):
        if self.retryable_errors is None:
            self.retryable_errors = [
                "timeout",
                "connection_error",
                "server_error",
                "rate_limit"
            ]


@dataclass
class CircuitBreakerConfig:
    """サーキットブレーカー設定"""
    failure_threshold: int = 5  # 失敗回数の閾値
    success_threshold: int = 2  # 成功回数の閾値（HALF_OPENからCLOSEDへ）
    timeout_seconds: float = 60.0  # OPEN状態のタイムアウト
    half_open_max_calls: int = 3  # HALF_OPEN状態での最大リクエスト数


@dataclass
class RetryResult:
    """リトライ結果"""
    success: bool
    result: Any
    attempts: int
    total_duration: float
    errors: List[str]


class CircuitBreaker:
    """サーキットブレーカー"""
    
    def __init__(self, config: CircuitBreakerConfig):
        """
        初期化
        
        Args:
            config: サーキットブレーカー設定
        """
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.half_open_calls = 0
    
    def can_execute(self) -> bool:
        """実行可能かチェック"""
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            # タイムアウトをチェック
            if self.last_failure_time:
                elapsed = (datetime.now() - self.last_failure_time).total_seconds()
                if elapsed >= self.config.timeout_seconds:
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_calls = 0
                    logger.info("🔓 サーキットブレーカー: HALF_OPENに移行")
                    return True
            return False
        
        if self.state == CircuitState.HALF_OPEN:
            if self.half_open_calls < self.config.half_open_max_calls:
                return True
            return False
        
        return False
    
    def record_success(self):
        """成功を記録"""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            self.half_open_calls += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
                logger.info("✅ サーキットブレーカー: CLOSEDに復帰")
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0
    
    def record_failure(self):
        """失敗を記録"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            self.half_open_calls = 0
            logger.warning("⚠️ サーキットブレーカー: OPENに移行（HALF_OPENから）")
        elif self.state == CircuitState.CLOSED:
            if self.failure_count >= self.config.failure_threshold:
                self.state = CircuitState.OPEN
                logger.warning(f"⚠️ サーキットブレーカー: OPENに移行（失敗回数: {self.failure_count}）")


class IntelligentRetry:
    """インテリジェントリトライシステム"""
    
    def __init__(self, retry_config: Optional[RetryConfig] = None, circuit_breaker_config: Optional[CircuitBreakerConfig] = None):
        """
        初期化
        
        Args:
            retry_config: リトライ設定
            circuit_breaker_config: サーキットブレーカー設定
        """
        self.retry_config = retry_config or RetryConfig()
        self.circuit_breaker_config = circuit_breaker_config or CircuitBreakerConfig()
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
    
    def get_circuit_breaker(self, key: str) -> CircuitBreaker:
        """サーキットブレーカーを取得（キーごと）"""
        if key not in self.circuit_breakers:
            self.circuit_breakers[key] = CircuitBreaker(self.circuit_breaker_config)
        return self.circuit_breakers[key]
    
    def _calculate_delay(self, attempt: int) -> float:
        """リトライ間隔を計算"""
        if self.retry_config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = self.retry_config.initial_delay * (self.retry_config.exponential_base ** attempt)
            return min(delay, self.retry_config.max_delay)
        elif self.retry_config.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = self.retry_config.initial_delay * (attempt + 1)
            return min(delay, self.retry_config.max_delay)
        elif self.retry_config.strategy == RetryStrategy.FIXED_INTERVAL:
            return self.retry_config.initial_delay
        else:
            return self.retry_config.initial_delay
    
    def _is_retryable_error(self, error: Exception) -> bool:
        """リトライ可能なエラーかチェック"""
        error_type = type(error).__name__.lower()
        error_message = str(error).lower()
        
        for retryable in self.retry_config.retryable_errors:
            if retryable.lower() in error_type or retryable.lower() in error_message:
                return True
        
        return False
    
    async def execute_with_retry(
        self,
        func: Callable[..., T],
        *args,
        circuit_breaker_key: Optional[str] = None,
        **kwargs
    ) -> RetryResult:
        """
        リトライ付きで関数を実行
        
        Args:
            func: 実行する関数
            *args: 関数の引数
            circuit_breaker_key: サーキットブレーカーのキー
            **kwargs: 関数のキーワード引数
        
        Returns:
            リトライ結果
        """
        start_time = datetime.now()
        errors = []
        
        # サーキットブレーカーチェック
        if circuit_breaker_key:
            circuit_breaker = self.get_circuit_breaker(circuit_breaker_key)
            if not circuit_breaker.can_execute():
                error = Exception(f"サーキットブレーカーがOPEN状態です: {circuit_breaker_key}")
                errors.append(str(error))
                return RetryResult(
                    success=False,
                    result=None,
                    attempts=0,
                    total_duration=(datetime.now() - start_time).total_seconds(),
                    errors=errors
                )
        
        for attempt in range(self.retry_config.max_retries + 1):
            try:
                if inspect.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                # 成功を記録
                if circuit_breaker_key:
                    circuit_breaker.record_success()  # type: ignore[possibly-unbound]
                
                return RetryResult(
                    success=True,
                    result=result,
                    attempts=attempt + 1,
                    total_duration=(datetime.now() - start_time).total_seconds(),
                    errors=errors
                )
            
            except Exception as e:
                errors.append(str(e))
                
                # リトライ可能かチェック
                if attempt < self.retry_config.max_retries and self._is_retryable_error(e):
                    delay = self._calculate_delay(attempt)
                    logger.warning(f"⚠️ リトライ {attempt + 1}/{self.retry_config.max_retries}: {delay:.2f}秒後に再試行...")
                    await asyncio.sleep(delay)
                else:
                    # リトライ不可能または最大回数に達した
                    if circuit_breaker_key:
                        circuit_breaker.record_failure()  # type: ignore[possibly-unbound]
                    
                    return RetryResult(
                        success=False,
                        result=None,
                        attempts=attempt + 1,
                        total_duration=(datetime.now() - start_time).total_seconds(),
                        errors=errors
                    )
        
        # ここには到達しないはず
        if circuit_breaker_key:
            circuit_breaker.record_failure()  # type: ignore[possibly-unbound]
        
        return RetryResult(
            success=False,
            result=None,
            attempts=self.retry_config.max_retries + 1,
            total_duration=(datetime.now() - start_time).total_seconds(),
            errors=errors
        )
    
    def retry_decorator(
        self,
        max_retries: Optional[int] = None,
        circuit_breaker_key: Optional[str] = None
    ):
        """
        リトライデコレータ
        
        Args:
            max_retries: 最大リトライ回数（Noneの場合は設定値を使用）
            circuit_breaker_key: サーキットブレーカーのキー
        """
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @wraps(func)
            async def async_wrapper(*args, **kwargs) -> T:
                config = self.retry_config
                if max_retries is not None:
                    config = RetryConfig(
                        max_retries=max_retries,
                        initial_delay=self.retry_config.initial_delay,
                        max_delay=self.retry_config.max_delay,
                        exponential_base=self.retry_config.exponential_base,
                        strategy=self.retry_config.strategy,
                        retryable_errors=self.retry_config.retryable_errors
                    )
                
                retry_system = IntelligentRetry(retry_config=config, circuit_breaker_config=self.circuit_breaker_config)
                result = await retry_system.execute_with_retry(
                    func,
                    *args,
                    circuit_breaker_key=circuit_breaker_key,
                    **kwargs
                )
                
                if not result.success:
                    raise Exception(f"リトライ失敗: {', '.join(result.errors)}")
                
                return result.result
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs) -> T:
                import asyncio
                return asyncio.run(async_wrapper(*args, **kwargs))
            
            if asyncio.iscoroutinefunction(func):
                return async_wrapper  # type: ignore
            else:
                return sync_wrapper
        
        return decorator


# グローバルインスタンス
intelligent_retry = IntelligentRetry()

# デコレータのエクスポート
retry = intelligent_retry.retry_decorator

