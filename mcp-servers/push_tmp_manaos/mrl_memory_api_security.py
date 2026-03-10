#!/usr/bin/env python3
"""
MRL Memory API Security
APIの安全対策（認証、レート制限、入力サイズ制限）
"""

import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from functools import wraps

# 統一モジュールのインポート
try:
    from unified_logging import get_service_logger
    logger = get_service_logger("mrl-memory-api-security")
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class APISecurity:
    """
    APIの安全対策
    
    - 認証
    - レート制限
    - 入力サイズ制限
    - PIIマスキング
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        rate_limit_per_minute: int = 60,
        max_input_size: int = 1000000,  # 1MB
        require_auth: bool = True
    ):
        """
        初期化
        
        Args:
            api_key: APIキー（Noneの場合は認証なし）
            rate_limit_per_minute: レート制限（1分あたり）
            max_input_size: 最大入力サイズ（バイト）
            require_auth: 認証必須かどうか（環境変数から読み込み可能）
        """
        import os

        # APIキー（MRL専用 -> 共通キーの順で採用）
        self.api_key = api_key or os.getenv("MRL_MEMORY_API_KEY") or os.getenv("API_KEY")

        # 認証必須フラグ（優先順）
        # 1) MRL_MEMORY_REQUIRE_AUTH
        # 2) REQUIRE_AUTH
        # 3) どちらも未設定なら「APIキーがある時のみ認証ON」
        raw_require_auth = os.getenv("MRL_MEMORY_REQUIRE_AUTH")
        if raw_require_auth is None:
            raw_require_auth = os.getenv("REQUIRE_AUTH")

        if raw_require_auth is None:
            self.require_auth = bool(self.api_key) if require_auth else False
        else:
            self.require_auth = raw_require_auth.lower() in ["1", "true", "yes"]

        self.rate_limit_per_minute = int(os.getenv("RATE_LIMIT_PER_MIN", str(rate_limit_per_minute)))
        self.max_input_size = int(os.getenv("MAX_INPUT_CHARS", str(max_input_size)))
        
        # レート制限の追跡
        self.rate_limit_tracker: Dict[str, List[float]] = defaultdict(list)  # type: ignore[name-defined]
        
        # 起動時にセキュリティ設定をログ出力（本番運用の証拠）
        logger.info(
            "SECURITY: auth=%s, rate_limit=%s, max_input=%s, pii_mask=enabled",
            "enabled" if self.require_auth else "disabled",
            "enabled" if self.rate_limit_per_minute > 0 else "disabled",
            self.max_input_size,
        )
        
        # Windows(cp932)でも壊れないログにする（絵文字禁止）
        logger.info("[OK] API Security初期化完了")
    
    def authenticate(self, api_key: Optional[str]) -> bool:
        """
        認証
        
        Args:
            api_key: 提供されたAPIキー
        
        Returns:
            認証成功かどうか
        """
        # 認証必須モードの場合
        if self.require_auth:
            if self.api_key is None:
                logger.warning("認証必須ですがAPIキーが設定されていません")
                return False
            # デバッグ用ログ（本番では削除可能）
            if api_key != self.api_key:
                logger.debug(f"認証失敗: 提供されたキー={api_key[:20] if api_key else None}..., 期待されるキー={self.api_key[:20] if self.api_key else None}...")
            return api_key == self.api_key
        
        # 認証なしモード
        if self.api_key is None:
            return True
        
        # APIキーが設定されている場合は検証
        return api_key == self.api_key
    
    def check_rate_limit(self, client_id: str) -> bool:
        """
        レート制限チェック
        
        Args:
            client_id: クライアントID
        
        Returns:
            レート制限内かどうか
        """
        now = time.time()
        
        # 1分前より古い記録を削除
        self.rate_limit_tracker[client_id] = [
            t for t in self.rate_limit_tracker[client_id]
            if now - t < 60
        ]
        
        # レート制限チェック
        if len(self.rate_limit_tracker[client_id]) >= self.rate_limit_per_minute:
            return False
        
        # 記録を追加
        self.rate_limit_tracker[client_id].append(now)
        return True
    
    def check_input_size(self, text: str) -> bool:
        """
        入力サイズチェック
        
        Args:
            text: 入力テキスト
        
        Returns:
            サイズ制限内かどうか
        """
        size = len(text.encode('utf-8'))
        return size <= self.max_input_size
    
    def mask_pii(self, text: str) -> str:
        """
        PIIをマスキング
        
        Args:
            text: 入力テキスト
        
        Returns:
            マスキング済みテキスト
        """
        import re
        
        # メールアドレス
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', text)
        
        # 電話番号（簡易）
        text = re.sub(r'\d{3}-\d{4}-\d{4}', '[PHONE]', text)
        
        # クレジットカード番号（簡易）
        text = re.sub(r'\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}', '[CARD]', text)
        
        return text


def require_auth(security: APISecurity):
    """認証デコレータ"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # リクエストからAPIキーを取得（実装はFlask等に依存）
            api_key = kwargs.get('api_key') or args[0].headers.get('X-API-Key')
            
            if not security.authenticate(api_key):
                return {"error": "認証に失敗しました"}, 401
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def rate_limit(security: APISecurity):
    """レート制限デコレータ"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # クライアントIDを取得（実装はFlask等に依存）
            client_id = kwargs.get('client_id') or args[0].remote_addr
            
            if not security.check_rate_limit(client_id):
                return {"error": "レート制限を超えました"}, 429
            
            return func(*args, **kwargs)
        return wrapper
    return decorator
