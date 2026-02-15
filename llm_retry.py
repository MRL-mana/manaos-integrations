"""
LLMリトライ機能
エラー時の自動リトライとフォールバック
"""

from manaos_logger import get_logger
import time
from typing import Callable, Any, Optional, Dict, List
from functools import wraps

logger = get_service_logger("llm-retry")


class RetryConfig:
    """リトライ設定クラス"""
    
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        backoff_factor: float = 2.0,
        max_delay: float = 60.0,
        retryable_exceptions: Optional[tuple] = None
    ):
        """
        初期化
        
        Args:
            max_retries: 最大リトライ回数
            initial_delay: 初期遅延時間（秒）
            backoff_factor: バックオフ係数
            max_delay: 最大遅延時間（秒）
            retryable_exceptions: リトライ可能な例外のタプル
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.backoff_factor = backoff_factor
        self.max_delay = max_delay
        self.retryable_exceptions = retryable_exceptions or (Exception,)


def retry_with_backoff(
    func: Callable,
    config: Optional[RetryConfig] = None,
    fallback_func: Optional[Callable] = None
) -> Any:
    """
    リトライ機能付きで関数を実行
    
    Args:
        func: 実行する関数
        config: リトライ設定
        fallback_func: フォールバック関数
        
    Returns:
        関数の実行結果
    """
    if config is None:
        config = RetryConfig()
    
    last_exception = None
    
    for attempt in range(config.max_retries + 1):
        try:
            return func()
        except config.retryable_exceptions as e:
            last_exception = e
            
            if attempt < config.max_retries:
                delay = min(
                    config.initial_delay * (config.backoff_factor ** attempt),
                    config.max_delay
                )
                logger.warning(
                    f"⚠️ リトライ {attempt + 1}/{config.max_retries}: "
                    f"{type(e).__name__} - {str(e)[:100]}"
                )
                time.sleep(delay)
            else:
                logger.error(f"❌ リトライ上限に達しました: {e}")
                break
    
    # フォールバック関数を試行
    if fallback_func:
        try:
            logger.info("🔄 フォールバック関数を実行")
            return fallback_func()
        except Exception as fallback_error:
            logger.error(f"❌ フォールバックも失敗: {fallback_error}")
    
    # すべて失敗した場合は例外を再発生
    if last_exception:
        raise last_exception
    
    raise Exception("リトライとフォールバックがすべて失敗しました")


def retry_decorator(config: Optional[RetryConfig] = None):
    """
    リトライ機能付きデコレータ
    
    Usage:
        @retry_decorator(config=RetryConfig(max_retries=3))
        def my_function():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            def _func():
                return func(*args, **kwargs)
            
            return retry_with_backoff(_func, config=config)
        
        return wrapper
    return decorator


class ModelFallback:
    """モデルフォールバッククラス"""
    
    def __init__(self, models: List[str]):
        """
        初期化
        
        Args:
            models: フォールバック順のモデルリスト
        """
        self.models = models
        self.current_model_index = 0
    
    def get_current_model(self) -> str:
        """現在のモデルを取得"""
        return self.models[self.current_model_index]
    
    def get_fallback_model(self) -> Optional[str]:
        """次のフォールバックモデルを取得"""
        if self.current_model_index < len(self.models) - 1:
            self.current_model_index += 1
            return self.models[self.current_model_index]
        return None
    
    def reset(self):
        """モデルインデックスをリセット"""
        self.current_model_index = 0

