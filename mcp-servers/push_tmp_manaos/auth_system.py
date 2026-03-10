#!/usr/bin/env python3
"""
🔐 ManaOS 認証・認可システム
APIキー認証・トークンベース認証・ロールベースアクセス制御
"""

import os
import json
import hashlib
import secrets
import sqlite3
import warnings
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
from functools import wraps
import jwt

# 統一モジュールのインポート
from manaos_logger import get_logger, get_service_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from manaos_timeout_config import get_timeout_config
from manaos_jwt import (
    JWT_ALGORITHM,
    accept_legacy_short_key,
    derive_hs256_signing_key,
    get_or_create_jwt_secret,
)

# ロガーの初期化
logger = get_service_logger("auth-system")

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("AuthSystem")

# タイムアウト設定の取得
timeout_config = get_timeout_config()

JWT_SECRET_KEY = get_or_create_jwt_secret()
JWT_SIGNING_KEY = derive_hs256_signing_key(JWT_SECRET_KEY)


class Role(str, Enum):
    """ロール"""
    GUEST = "guest"
    USER = "user"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


@dataclass
class APIKey:
    """APIキー"""
    key_id: str
    key_hash: str
    user_id: str
    role: Role
    created_at: str
    expires_at: Optional[str] = None
    last_used_at: Optional[str] = None
    is_active: bool = True
    metadata: Dict[str, Any] = None  # type: ignore
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class User:
    """ユーザー"""
    user_id: str
    username: str
    email: str
    role: Role
    created_at: str
    is_active: bool = True
    metadata: Dict[str, Any] = None  # type: ignore
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class AuthSystem:
    """認証・認可システム"""
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        初期化
        
        Args:
            db_path: データベースパス
        """
        self.db_path = db_path or Path(__file__).parent / "auth.db"
        self._init_database()
        
        logger.info(f"✅ Auth System初期化完了")
    
    def _init_database(self):
        """データベースを初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # ユーザーテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                role TEXT NOT NULL,
                created_at TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                metadata TEXT
            )
        """)
        
        # APIキーテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                key_id TEXT PRIMARY KEY,
                key_hash TEXT NOT NULL,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT,
                last_used_at TEXT,
                is_active INTEGER DEFAULT 1,
                metadata TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        # トークンテーブル（リフレッシュトークン用）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tokens (
                token_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                token_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info(f"✅ 認証データベース初期化完了: {self.db_path}")
    
    def create_user(
        self,
        username: str,
        email: str,
        role: Role = Role.USER,
        metadata: Optional[Dict[str, Any]] = None
    ) -> User:
        """
        ユーザーを作成
        
        Args:
            username: ユーザー名
            email: メールアドレス
            role: ロール
            metadata: メタデータ
        
        Returns:
            作成されたユーザー
        """
        user_id = hashlib.sha256(f"{username}{email}{datetime.now().isoformat()}".encode()).hexdigest()[:16]
        
        user = User(
            user_id=user_id,
            username=username,
            email=email,
            role=role,
            created_at=datetime.now().isoformat(),
            metadata=metadata or {}
        )
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO users (user_id, username, email, role, created_at, is_active, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            user.user_id,
            user.username,
            user.email,
            user.role.value,
            user.created_at,
            1 if user.is_active else 0,
            json.dumps(user.metadata, ensure_ascii=False) if user.metadata else None
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ ユーザー作成完了: {username} ({user_id})")
        return user
    
    def create_api_key(
        self,
        user_id: str,
        role: Optional[Role] = None,
        expires_days: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        APIキーを作成
        
        Args:
            user_id: ユーザーID
            role: ロール（Noneの場合はユーザーのロールを使用）
            expires_days: 有効期限（日数、Noneの場合は無期限）
            metadata: メタデータ
        
        Returns:
            APIキー（平文）
        """
        # ユーザー情報を取得
        user = self.get_user(user_id)
        if not user:
            raise ValueError(f"ユーザーが見つかりません: {user_id}")
        
        # APIキーを生成
        api_key = f"mana_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        key_id = hashlib.sha256(key_hash.encode()).hexdigest()[:16]
        
        expires_at = None
        if expires_days:
            expires_at = (datetime.now() + timedelta(days=expires_days)).isoformat()
        
        api_key_obj = APIKey(
            key_id=key_id,
            key_hash=key_hash,
            user_id=user_id,
            role=role or user.role,
            created_at=datetime.now().isoformat(),
            expires_at=expires_at,
            metadata=metadata or {}
        )
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO api_keys (key_id, key_hash, user_id, role, created_at, expires_at, is_active, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            api_key_obj.key_id,
            api_key_obj.key_hash,
            api_key_obj.user_id,
            api_key_obj.role.value,
            api_key_obj.created_at,
            api_key_obj.expires_at,
            1 if api_key_obj.is_active else 0,
            json.dumps(api_key_obj.metadata, ensure_ascii=False) if api_key_obj.metadata else None
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ APIキー作成完了: {key_id}")
        return api_key
    
    def verify_api_key(self, api_key: str) -> Optional[APIKey]:
        """
        APIキーを検証
        
        Args:
            api_key: APIキー（平文）
        
        Returns:
            APIキー情報（検証成功時）
        """
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM api_keys
            WHERE key_hash = ? AND is_active = 1
        """, (key_hash,))
        
        row = cursor.fetchone()
        if not row:
            conn.close()
            return None
        
        # 有効期限チェック
        if row[5]:  # expires_at
            expires_at = datetime.fromisoformat(row[5])
            if datetime.now() > expires_at:
                conn.close()
                return None
        
        # 最終使用日時を更新
        cursor.execute("""
            UPDATE api_keys SET last_used_at = ? WHERE key_id = ?
        """, (datetime.now().isoformat(), row[0]))
        
        conn.commit()
        conn.close()
        
        return APIKey(
            key_id=row[0],
            key_hash=row[1],
            user_id=row[2],
            role=Role(row[3]),
            created_at=row[4],
            expires_at=row[5],
            last_used_at=datetime.now().isoformat(),
            is_active=bool(row[7]),
            metadata=json.loads(row[8]) if row[8] else {}
        )
    
    def create_token(
        self,
        user_id: str,
        expires_hours: int = 24
    ) -> str:
        """
        JWTトークンを作成
        
        Args:
            user_id: ユーザーID
            expires_hours: 有効期限（時間）
        
        Returns:
            JWTトークン
        """
        user = self.get_user(user_id)
        if not user:
            raise ValueError(f"ユーザーが見つかりません: {user_id}")
        
        now = datetime.now(timezone.utc)
        payload = {
            "user_id": user_id,
            "role": user.role.value,
            "exp": now + timedelta(hours=expires_hours),
            "iat": now
        }
        
        token = jwt.encode(payload, JWT_SIGNING_KEY, algorithm=JWT_ALGORITHM)
        
        logger.info(f"✅ トークン作成完了: {user_id}")
        return token
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        JWTトークンを検証
        
        Args:
            token: JWTトークン
        
        Returns:
            ペイロード（検証成功時）
        """
        try:
            try:
                payload = jwt.decode(token, JWT_SIGNING_KEY, algorithms=[JWT_ALGORITHM])
                return payload
            except Exception:
                # 互換性: 短いJWT_SECRET_KEYをそのまま使っていた旧トークンを受け入れる場合
                if accept_legacy_short_key() and len(JWT_SECRET_KEY.encode("utf-8")) < 32:
                    with warnings.catch_warnings():
                        warnings.filterwarnings('ignore', category=Warning)
                        return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
                raise
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("トークンの有効期限が切れています")
            return None
        except jwt.InvalidTokenError:
            logger.warning("無効なトークンです")
            return None
    
    def get_user(self, user_id: str) -> Optional[User]:
        """ユーザーを取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        
        conn.close()
        
        if not row:
            return None
        
        return User(
            user_id=row[0],
            username=row[1],
            email=row[2],
            role=Role(row[3]),
            created_at=row[4],
            is_active=bool(row[5]),
            metadata=json.loads(row[6]) if row[6] else {}
        )
    
    def check_permission(self, role: Role, required_role: Role) -> bool:
        """
        権限をチェック
        
        Args:
            role: ユーザーのロール
            required_role: 必要なロール
        
        Returns:
            権限がある場合True
        """
        role_hierarchy = {
            Role.GUEST: 0,
            Role.USER: 1,
            Role.ADMIN: 2,
            Role.SUPER_ADMIN: 3
        }
        
        return role_hierarchy.get(role, 0) >= role_hierarchy.get(required_role, 0)
    
    def auth_decorator(self, required_role: Role = Role.USER, use_api_key: bool = True, use_token: bool = True):
        """
        認証デコレータ
        
        Args:
            required_role: 必要なロール
            use_api_key: APIキー認証を使用するか
            use_token: トークン認証を使用するか
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                from flask import request
                
                # APIキー認証
                if use_api_key:
                    api_key = request.headers.get("X-API-Key") or request.args.get("api_key")
                    if api_key:
                        api_key_obj = self.verify_api_key(api_key)
                        if api_key_obj:
                            if self.check_permission(api_key_obj.role, required_role):
                                kwargs["auth_user_id"] = api_key_obj.user_id
                                kwargs["auth_role"] = api_key_obj.role
                                return func(*args, **kwargs)
                            else:
                                return {"error": "権限が不足しています"}, 403
                        else:
                            return {"error": "無効なAPIキーです"}, 401
                
                # トークン認証
                if use_token:
                    auth_header = request.headers.get("Authorization", "")
                    if auth_header.startswith("Bearer "):
                        token = auth_header[7:]
                        payload = self.verify_token(token)
                        if payload:
                            role = Role(payload.get("role", "guest"))
                            if self.check_permission(role, required_role):
                                kwargs["auth_user_id"] = payload.get("user_id")
                                kwargs["auth_role"] = role
                                return func(*args, **kwargs)
                            else:
                                return {"error": "権限が不足しています"}, 403
                        else:
                            return {"error": "無効なトークンです"}, 401
                
                return {"error": "認証が必要です"}, 401
            
            return wrapper
        return decorator


# グローバルインスタンス
auth_system = AuthSystem()

# デコレータのエクスポート
require_auth = auth_system.auth_decorator

