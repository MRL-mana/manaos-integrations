"""
MCPサーバー用エラーハンドリングヘルパー
統一エラーハンドリングとリトライメカニズムを提供
"""

from manaos_logger import get_logger, get_service_logger
import requests
from typing import Any, Callable, Optional, Sequence, Dict
from mcp.types import TextContent

logger = get_service_logger("error-helper")

# タイムアウト設定のインポート
try:
    from manaos_timeout_config import get_timeout_config
    timeout_config = get_timeout_config()
    TIMEOUT_CONFIG_AVAILABLE = True
except ImportError:
    logger.warning("タイムアウト設定モジュールが見つかりません。デフォルト値を使用します。")
    TIMEOUT_CONFIG_AVAILABLE = False
    timeout_config = None


def format_error_response(error: Exception, tool_name: str = None) -> Sequence[TextContent]:
    """
    エラーをTextContent形式に変換
    
    Args:
        error: 例外オブジェクト
        tool_name: ツール名（オプション）
    
    Returns:
        TextContentのシーケンス
    """
    try:
        from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
        error_handler = ManaOSErrorHandler("manaos-unified-mcp-server")
        
        context = {}
        if tool_name:
            context["tool_name"] = tool_name
        
        manaos_error = error_handler.handle_exception(
            error,
            context=context,
            user_message=f"ツール '{tool_name}' の実行中にエラーが発生しました" if tool_name else "エラーが発生しました"
        )
        
        error_message = manaos_error.user_message or manaos_error.message
        return [TextContent(type="text", text=f"❌ {error_message}")]
    
    except ImportError:
        # 統一エラーハンドリングが利用できない場合
        logger.warning("統一エラーハンドリングモジュールが見つかりません")
        return [TextContent(type="text", text=f"❌ エラーが発生しました: {str(error)}")]
    except Exception as handler_error:
        logger.warning(f"エラーハンドラーでの処理中にエラーが発生: {handler_error}")
        return [TextContent(type="text", text=f"❌ エラーが発生しました: {str(error)}")]


def handle_integration_error(integration_name: str) -> Sequence[TextContent]:
    """
    統合モジュールが利用できない場合のエラーレスポンス
    
    Args:
        integration_name: 統合モジュール名
    
    Returns:
        TextContentのシーケンス
    """
    return [TextContent(type="text", text=f"❌ {integration_name}統合が利用できません")]


def retry_with_backoff(
    func: Callable,
    max_retries: int = 2,
    initial_delay: float = 0.5,
    max_delay: float = 10.0,
    exponential_base: float = 2.0
) -> Any:
    """
    指数バックオフでリトライするデコレータ/ヘルパー関数
    
    Args:
        func: 実行する関数
        max_retries: 最大リトライ回数
        initial_delay: 初期待機時間（秒）
        max_delay: 最大待機時間（秒）
        exponential_base: 指数の底
    
    Returns:
        関数の戻り値
    """
    import time
    
    for attempt in range(max_retries + 1):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries:
                # 最後の試行も失敗した場合
                raise e
            
            # 待機時間を計算（指数バックオフ）
            delay = min(initial_delay * (exponential_base ** attempt), max_delay)
            logger.warning(f"リトライ ({attempt + 1}/{max_retries}): {delay}秒後に再試行します... エラー: {e}")
            time.sleep(delay)
    
    raise Exception("リトライ回数を超えました")


def get_timeout(key: str = "external_service", default: float = 30.0) -> float:
    """
    タイムアウト値を取得
    
    Args:
        key: タイムアウトキー
        default: デフォルト値
    
    Returns:
        タイムアウト値（秒）
    """
    if TIMEOUT_CONFIG_AVAILABLE and timeout_config:
        return timeout_config.get(key, default)
    return default


def requests_with_retry(
    method: str,
    url: str,
    max_retries: int = 2,
    timeout: Optional[float] = None,
    timeout_key: str = "external_service",
    **kwargs
) -> requests.Response:
    """
    リトライ機能付きrequests呼び出し
    
    Args:
        method: HTTPメソッド（get, post, put, delete等）
        url: URL
        max_retries: 最大リトライ回数
        timeout: タイムアウト値（秒、Noneの場合はtimeout_keyから取得）
        timeout_key: タイムアウト設定キー
        **kwargs: requests呼び出しの引数
    
    Returns:
        requests.Response
    
    Raises:
        requests.RequestException: リトライ後も失敗した場合
    """
    if timeout is None:
        timeout = get_timeout(timeout_key, 30.0)
    
    def _make_request():
        request_method = getattr(requests, method.lower())
        return request_method(url, timeout=timeout, **kwargs)
    
    return retry_with_backoff(
        _make_request,
        max_retries=max_retries,
        initial_delay=0.5,
        max_delay=10.0
    )
