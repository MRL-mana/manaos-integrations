#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔒 ManaOS セキュリティモジュール
API認証、入力検証、レート制限
"""

import os
import time
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable
from functools import wraps
from flask import request, jsonify, g
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

# APIキー管理
class APIKeyManager:
    """APIキー管理"""
    
    def __init__(self):
        self.api_keys = {}
        self._load_api_keys()
    
    def _load_api_keys(self):
        """APIキーを環境変数から読み込み"""
        api_key = os.getenv('MANAOS_API_KEY')
        if api_key:
            self.api_keys['default'] = {
                'key': api_key,
                'created_at': datetime.now().isoformat(),
                'permissions': ['read', 'write']
            }
    
    def validate_api_key(self, api_key: str) -> bool:
        """APIキーを検証"""
        for key_info in self.api_keys.values():
            if hmac.compare_digest(key_info['key'], api_key):
                return True
        return False
    
    def get_permissions(self, api_key: str) -> list:
        """APIキーの権限を取得"""
        for key_info in self.api_keys.values():
            if hmac.compare_digest(key_info['key'], api_key):
                return key_info.get('permissions', [])
        return []


# JWT認証（簡易版）
class JWTManager:
    """JWT認証管理（簡易実装）"""
    
    def __init__(self, secret_key: Optional[str] = None):
        self.secret_key = secret_key or os.getenv('JWT_SECRET_KEY', 'default-secret-key-change-in-production')
    
    def generate_token(self, user_id: str, expires_in: int = 3600) -> str:
        """トークンを生成"""
        import base64
        import json
        
        header = {"alg": "HS256", "typ": "JWT"}
        payload = {
            "user_id": user_id,
            "exp": int(time.time()) + expires_in,
            "iat": int(time.time())
        }
        
        # 簡易実装（本番環境ではjose等のライブラリを使用）
        header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('=')
        payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
        
        signature = hmac.new(
            self.secret_key.encode(),
            f"{header_b64}.{payload_b64}".encode(),
            hashlib.sha256
        ).digest()
        sig_b64 = base64.urlsafe_b64encode(signature).decode().rstrip('=')
        
        return f"{header_b64}.{payload_b64}.{sig_b64}"
    
    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """トークンを検証"""
        try:
            import base64
            import json
            
            parts = token.split('.')
            if len(parts) != 3:
                return None
            
            header_b64, payload_b64, sig_b64 = parts
            
            # 署名検証
            signature = base64.urlsafe_b64decode(sig_b64 + '==')
            expected_sig = hmac.new(
                self.secret_key.encode(),
                f"{header_b64}.{payload_b64}".encode(),
                hashlib.sha256
            ).digest()
            
            if not hmac.compare_digest(signature, expected_sig):
                return None
            
            # ペイロード取得
            payload_json = base64.urlsafe_b64decode(payload_b64 + '==')
            payload = json.loads(payload_json)
            
            # 有効期限チェック
            if payload.get('exp', 0) < int(time.time()):
                return None
            
            return payload
        except Exception as e:
            logger.warning(f"トークン検証エラー: {e}")
            return None


# レート制限
class RateLimiter:
    """レート制限"""
    
    def __init__(self):
        self.requests = defaultdict(list)
        self.limits = {
            'default': {'requests': 100, 'window': 60},  # 60秒間に100リクエスト
            'strict': {'requests': 20, 'window': 60},    # 60秒間に20リクエスト
        }
    
    def is_allowed(self, identifier: str, limit_type: str = 'default') -> bool:
        """リクエストが許可されるかチェック"""
        limit = self.limits.get(limit_type, self.limits['default'])
        now = time.time()
        
        # 古いリクエストを削除
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier]
            if now - req_time < limit['window']
        ]
        
        # 制限チェック
        if len(self.requests[identifier]) >= limit['requests']:
            return False
        
        # リクエストを記録
        self.requests[identifier].append(now)
        return True
    
    def get_remaining(self, identifier: str, limit_type: str = 'default') -> int:
        """残りリクエスト数を取得"""
        limit = self.limits.get(limit_type, self.limits['default'])
        now = time.time()
        
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier]
            if now - req_time < limit['window']
        ]
        
        return max(0, limit['requests'] - len(self.requests[identifier]))


# 入力検証
class InputValidator:
    """入力検証"""
    
    @staticmethod
    def validate_text(text: str, max_length: int = 10000, min_length: int = 1) -> tuple[bool, Optional[str]]:
        """テキストを検証"""
        if not isinstance(text, str):
            return False, "テキストは文字列である必要があります"
        
        if len(text) < min_length:
            return False, f"テキストは{min_length}文字以上である必要があります"
        
        if len(text) > max_length:
            return False, f"テキストは{max_length}文字以下である必要があります"
        
        # SQLインジェクション対策
        dangerous_patterns = ["';", "--", "/*", "*/", "xp_", "sp_"]
        for pattern in dangerous_patterns:
            if pattern.lower() in text.lower():
                return False, "不正な文字列が検出されました"
        
        return True, None
    
    @staticmethod
    def validate_mode(mode: str) -> tuple[bool, Optional[str]]:
        """モードを検証"""
        valid_modes = ['auto', 'manual', 'interactive']
        if mode not in valid_modes:
            return False, f"モードは{valid_modes}のいずれかである必要があります"
        return True, None
    
    @staticmethod
    def validate_json(data: Dict[str, Any], schema: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """JSONデータを検証"""
        for key, value_type in schema.items():
            if key not in data:
                return False, f"必須フィールド '{key}' がありません"
            
            if not isinstance(data[key], value_type):
                return False, f"フィールド '{key}' の型が不正です（期待: {value_type.__name__}）"
        
        return True, None


# Flaskデコレータ
def require_api_key(f: Callable) -> Callable:
    """APIキー認証デコレータ"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
        
        if not api_key:
            return jsonify({"error": "APIキーが必要です"}), 401
        
        key_manager = APIKeyManager()
        if not key_manager.validate_api_key(api_key):
            return jsonify({"error": "無効なAPIキーです"}), 401
        
        g.api_key = api_key
        g.permissions = key_manager.get_permissions(api_key)
        
        return f(*args, **kwargs)
    return decorated_function


def require_jwt(f: Callable) -> Callable:
    """JWT認証デコレータ"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"error": "認証トークンが必要です"}), 401
        
        token = auth_header.split(' ')[1]
        jwt_manager = JWTManager()
        payload = jwt_manager.validate_token(token)
        
        if not payload:
            return jsonify({"error": "無効な認証トークンです"}), 401
        
        g.user_id = payload.get('user_id')
        g.token_payload = payload
        
        return f(*args, **kwargs)
    return decorated_function


def rate_limit(limit_type: str = 'default') -> Callable:
    """レート制限デコレータ"""
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 識別子を取得（IPアドレスまたはAPIキー）
            identifier = request.remote_addr
            if hasattr(g, 'api_key'):
                identifier = hashlib.sha256(g.api_key.encode()).hexdigest()[:16]
            
            limiter = RateLimiter()
            if not limiter.is_allowed(identifier, limit_type):
                remaining = limiter.get_remaining(identifier, limit_type)
                return jsonify({
                    "error": "レート制限を超えました",
                    "retry_after": 60
                }), 429
            
            response = f(*args, **kwargs)
            
            # レスポンスヘッダーに残りリクエスト数を追加
            remaining = limiter.get_remaining(identifier, limit_type)
            if isinstance(response, tuple):
                response[0].headers['X-RateLimit-Remaining'] = str(remaining)
            else:
                response.headers['X-RateLimit-Remaining'] = str(remaining)
            
            return response
        return decorated_function
    return decorator


def validate_input(schema: Dict[str, Any]) -> Callable:
    """入力検証デコレータ"""
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            validator = InputValidator()
            
            # JSONボディの検証
            if request.is_json:
                data = request.get_json()
                is_valid, error = validator.validate_json(data, schema)
                if not is_valid:
                    return jsonify({"error": error}), 400
            
            # クエリパラメータの検証
            for key, value_type in schema.items():
                if key in request.args:
                    if not isinstance(request.args[key], value_type):
                        return jsonify({
                            "error": f"パラメータ '{key}' の型が不正です"
                        }), 400
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# セキュリティ設定
class SecurityConfig:
    """セキュリティ設定"""
    
    def __init__(self):
        self.enable_api_auth = os.getenv('MANAOS_ENABLE_API_AUTH', 'false').lower() == 'true'
        self.enable_jwt = os.getenv('MANAOS_ENABLE_JWT', 'false').lower() == 'true'
        self.enable_rate_limit = os.getenv('MANAOS_ENABLE_RATE_LIMIT', 'true').lower() == 'true'
        self.enable_input_validation = os.getenv('MANAOS_ENABLE_INPUT_VALIDATION', 'true').lower() == 'true'
    
    def apply_security(self, app) -> None:
        """Flaskアプリにセキュリティ設定を適用"""
        # HTTPSリダイレクト（本番環境）
        if os.getenv('FLASK_ENV') == 'production':
            @app.before_request
            def force_https():
                if not request.is_secure:
                    url = request.url.replace('http://', 'https://', 1)
                    return redirect(url, code=301)
        
        # CORS設定
        from flask_cors import CORS
        CORS(app, resources={
            r"/api/*": {
                "origins": os.getenv('CORS_ORIGINS', '*').split(','),
                "methods": ["GET", "POST", "PUT", "DELETE"],
                "allow_headers": ["Content-Type", "Authorization", "X-API-Key"]
            }
        })
        
        logger.info("✅ セキュリティ設定を適用しました")


# シングルトンインスタンス
api_key_manager = APIKeyManager()
jwt_manager = JWTManager()
rate_limiter = RateLimiter()
input_validator = InputValidator()
security_config = SecurityConfig()








