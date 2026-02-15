"""
API認証ミドルウェア
すべてのManaOS APIサービスで使用可能な統一認証システム
"""
import os
import secrets
import hashlib
import time
from functools import wraps
from typing import Callable, Optional, Dict, Set
from flask import Request, jsonify, request


class APIAuthManager:
    """API認証マネージャー"""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Args:
            config: 認証設定（省略時は環境変数から読み込み）
        """
        self.config = config or {}
        
        # API キーの読み込み
        self.api_keys: Set[str] = set()
        self._load_api_keys()
        
        # レート制限設定
        self.rate_limit_enabled = self.config.get("rate_limit_enabled", True)
        self.rate_limit_requests = int(self.config.get("rate_limit_requests", 100))
        self.rate_limit_window = int(self.config.get("rate_limit_window", 60))  # 秒
        
        # リクエスト履歴（レート制限用）
        self.request_history: Dict[str, list] = {}
    
    def _load_api_keys(self):
        """環境変数からAPIキーを読み込み"""
        # 環境変数 MANAOS_API_KEYS（カンマ区切り）
        api_keys_str = os.getenv("MANAOS_API_KEYS", "")
        if api_keys_str:
            self.api_keys = set(key.strip() for key in api_keys_str.split(",") if key.strip())
        
        # 開発環境用のデフォルトキー（本番環境では無効化すべき）
        if os.getenv("MANAOS_ENV", "development") == "development":
            self.api_keys.add("dev_default_key_DO_NOT_USE_IN_PRODUCTION")
    
    def generate_api_key(self, prefix: str = "manaos") -> str:
        """
        新しいAPIキーを生成
        
        Args:
            prefix: キーのプレフィックス
        
        Returns:
            生成されたAPIキー
        """
        random_part = secrets.token_urlsafe(32)
        api_key = f"{prefix}_{random_part}"
        return api_key
    
    def hash_api_key(self, api_key: str) -> str:
        """
        APIキーをハッシュ化（保存用）
        
        Args:
            api_key: APIキー
        
        Returns:
            ハッシュ化されたキー
        """
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    def validate_api_key(self, api_key: Optional[str]) -> bool:
        """
        APIキーを検証
        
        Args:
            api_key: 検証するAPIキー
        
        Returns:
            有効な場合True
        """
        if not api_key:
            return False
        
        return api_key in self.api_keys
    
    def check_rate_limit(self, client_id: str) -> bool:
        """
        レート制限をチェック
        
        Args:
            client_id: クライアント識別子（IPアドレスやAPIキーなど）
        
        Returns:
            制限内の場合True
        """
        if not self.rate_limit_enabled:
            return True
        
        current_time = time.time()
        
        # クライアントのリクエスト履歴を取得
        if client_id not in self.request_history:
            self.request_history[client_id] = []
        
        # 古いリクエストを削除
        window_start = current_time - self.rate_limit_window
        self.request_history[client_id] = [
            req_time for req_time in self.request_history[client_id]
            if req_time > window_start
        ]
        
        # レート制限チェック
        if len(self.request_history[client_id]) >= self.rate_limit_requests:
            return False
        
        # 新しいリクエストを記録
        self.request_history[client_id].append(current_time)
        return True
    
    def require_api_key(self, func: Callable):
        """
        APIキー認証を要求するデコレーター（Flask用）
        
        Usage:
            @app.route("/protected")
            @auth_manager.require_api_key
            def protected_endpoint():
                return jsonify({"message": "Success"})
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            # APIキーを取得（ヘッダーまたはクエリパラメータ）
            api_key = request.headers.get("X-API-Key") or request.args.get("api_key")
            
            # APIキー検証
            if not self.validate_api_key(api_key):
                return jsonify({
                    "error": "Unauthorized",
                    "message": "Invalid or missing API key"
                }), 401
            
            # レート制限チェック
            client_id = api_key or request.remote_addr
            if not self.check_rate_limit(client_id):
                return jsonify({
                    "error": "Rate limit exceeded",
                    "message": f"Maximum {self.rate_limit_requests} requests per {self.rate_limit_window} seconds"
                }), 429
            
            return func(*args, **kwargs)
        
        return wrapper
    
    def optional_api_key(self, func: Callable):
        """
        APIキー認証をオプションとするデコレーター
        APIキーがある場合は検証し、ない場合はスキップ
        
        Usage:
            @app.route("/public")
            @auth_manager.optional_api_key
            def public_endpoint():
                # request.api_key_validated でAPIキーの有無を確認可能
                return jsonify({"message": "Success"})
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            api_key = request.headers.get("X-API-Key") or request.args.get("api_key")
            
            # APIキーがある場合は検証
            if api_key:
                request.api_key_validated = self.validate_api_key(api_key)
            else:
                request.api_key_validated = False
            
            return func(*args, **kwargs)
        
        return wrapper


# グローバルインスタンス（各サービスで使用可能）
_global_auth_manager: Optional[APIAuthManager] = None


def get_auth_manager() -> APIAuthManager:
    """
    グローバル認証マネージャーを取得
    
    Returns:
        APIAuthManager インスタンス
    """
    global _global_auth_manager
    if _global_auth_manager is None:
        _global_auth_manager = APIAuthManager()
    return _global_auth_manager


def init_auth(config: Optional[Dict] = None):
    """
    認証マネージャーを初期化
    
    Args:
        config: 認証設定
    """
    global _global_auth_manager
    _global_auth_manager = APIAuthManager(config)


# FastAPI用のデコレーター
def require_api_key_fastapi():
    """FastAPI用のAPIキー認証依存関数"""
    try:
        from fastapi import Header, HTTPException
        
        def verify_api_key(x_api_key: Optional[str] = Header(None)):
            auth_manager = get_auth_manager()
            if not auth_manager.validate_api_key(x_api_key):
                raise HTTPException(
                    status_code=401,
                    detail="Invalid or missing API key"
                )
            return x_api_key
        
        return verify_api_key
    except ImportError:
        # FastAPIがインストールされていない場合
        return None


if __name__ == "__main__":
    # 使用例
    auth_manager = APIAuthManager()
    
    # 新しいAPIキーを生成
    new_key = auth_manager.generate_api_key()
    print(f"Generated API Key: {new_key}")
    
    # APIキーをハッシュ化
    hashed = auth_manager.hash_api_key(new_key)
    print(f"Hashed: {hashed}")
