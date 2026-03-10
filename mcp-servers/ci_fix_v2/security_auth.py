"""
ManaOS API セキュリティ認証層

JWT/OAuth2を使用した認証・認可の実装
"""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
import os
import hashlib
from enum import Enum

# ===========================
# 設定
# ===========================

class SecurityConfig:
    """セキュリティ設定"""
    # JWTトークン設定
    SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30
    REFRESH_TOKEN_EXPIRE_DAYS = 7
    
    # API Key設定
    API_KEYS = {
        os.environ.get("ADMIN_API_KEY", "admin-key"): "admin",
        os.environ.get("DEVELOPER_API_KEY", "dev-key"): "developer",
        os.environ.get("USER_API_KEY", "user-key"): "user"
    }


class UserRole(str, Enum):
    """ユーザーロール"""
    ADMIN = "admin"
    DEVELOPER = "developer"
    USER = "user"
    SERVICE = "service"


# ===========================
# Pydanticモデル
# ===========================

class Token(BaseModel):
    """トークンレスポンス"""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str
    expires_in: int
    user_id: str
    role: UserRole


class TokenData(BaseModel):
    """トークンデータ"""
    user_id: str
    role: UserRole
    scopes: list[str] = []
    exp: datetime
    iat: datetime


class User(BaseModel):
    """ユーザー情報"""
    user_id: str
    username: str
    email: Optional[str] = None
    role: UserRole
    is_active: bool = True
    permissions: list[str] = []


class LoginRequest(BaseModel):
    """ログインリクエスト"""
    username: str
    password: str


# ===========================
# JWT認証
# ===========================

class JWTManager:
    """JWT トークン管理"""
    
    @staticmethod
    def create_access_token(
        user_id: str,
        role: UserRole,
        scopes: list[str] = None,  # type: ignore
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """アクセストークン作成"""
        if expires_delta is None:
            expires_delta = timedelta(minutes=SecurityConfig.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        expire = datetime.utcnow() + expires_delta
        
        payload = {
            "user_id": user_id,
            "role": role.value,
            "scopes": scopes or [],
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        }
        
        encoded_jwt = jwt.encode(
            payload,
            SecurityConfig.SECRET_KEY,
            algorithm=SecurityConfig.ALGORITHM
        )
        
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(user_id: str) -> str:
        """リフレッシュトークン作成"""
        expire = datetime.utcnow() + timedelta(
            days=SecurityConfig.REFRESH_TOKEN_EXPIRE_DAYS
        )
        
        payload = {
            "user_id": user_id,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh"
        }
        
        encoded_jwt = jwt.encode(
            payload,
            SecurityConfig.SECRET_KEY,
            algorithm=SecurityConfig.ALGORITHM
        )
        
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> TokenData:
        """トークン検証"""
        try:
            payload = jwt.decode(
                token,
                SecurityConfig.SECRET_KEY,
                algorithms=[SecurityConfig.ALGORITHM]
            )
            
            user_id = payload.get("user_id")
            role = payload.get("role")
            scopes = payload.get("scopes", [])
            exp = datetime.fromtimestamp(payload.get("exp"))  # type: ignore
            iat = datetime.fromtimestamp(payload.get("iat"))  # type: ignore
            
            if user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            return TokenData(
                user_id=user_id,
                role=UserRole(role),
                scopes=scopes,
                exp=exp,
                iat=iat
            )
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
                headers={"WWW-Authenticate": "Bearer"}
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"}
            )


# ===========================
# API Key認証
# ===========================

class APIKeyManager:
    """API Key管理"""
    
    @staticmethod
    def verify_api_key(api_key: str) -> Dict[str, Any]:
        """API Key検証"""
        if api_key not in SecurityConfig.API_KEYS:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )
        
        role = SecurityConfig.API_KEYS[api_key]
        
        return {
            "user_id": f"api_key_{api_key[:8]}",
            "role": UserRole(role),
            "is_api_key": True
        }
    
    @staticmethod
    def generate_api_key(role: UserRole) -> str:
        """API Key生成"""
        import secrets
        return f"{role.value}_{secrets.token_urlsafe(32)}"


# ===========================
# OAuth2フロー（簡易版）
# ===========================

class OAuth2Manager:
    """OAuth2管理"""
    
    @staticmethod
    def authenticate_user(username: str, password: str) -> Optional[User]:
        """ユーザー認証（簡易版）"""
        # 実際の実装ではデータベースから取得
        users = {
            "admin": {
                "user_id": "user_001",
                "username": "admin",
                "password_hash": hashlib.sha256("admin".encode()).hexdigest(),
                "role": UserRole.ADMIN,
                "email": "admin@manaos.io"
            },
            "developer": {
                "user_id": "user_002",
                "username": "developer",
                "password_hash": hashlib.sha256("developer".encode()).hexdigest(),
                "role": UserRole.DEVELOPER,
                "email": "developer@manaos.io"
            }
        }
        
        user = users.get(username)
        if not user:
            return None
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        if user["password_hash"] != password_hash:
            return None
        
        return User(
            user_id=user["user_id"],
            username=user["username"],
            role=user["role"],
            email=user["email"]
        )


# ===========================
# FastAPI セキュリティDependency
# ===========================

class AuthDependencies:
    """認証依存関数"""
    
    oauth2_scheme = OAuth2PasswordBearer(
        tokenUrl="token",
        scopes={
            "read": "Read access",
            "write": "Write access",
            "admin": "Admin access"
        }
    )
    
    @staticmethod
    async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
        """現在のユーザー取得"""
        token_data = JWTManager.verify_token(token)
        
        # 簡易版：ユーザー情報を返す
        return User(
            user_id=token_data.user_id,
            username=token_data.user_id,
            role=token_data.role
        )
    
    @staticmethod
    async def get_admin_user(
        current_user: User = Depends(get_current_user.__func__)  # type: ignore
    ) -> User:
        """管理者権限チェック"""
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        return current_user
    
    @staticmethod
    async def verify_api_key(api_key: str) -> Dict[str, Any]:
        """API Key検証"""
        return APIKeyManager.verify_api_key(api_key)


# ===========================
# ロールベースアクセス制御（RBAC）
# ===========================

class RBACPermissions:
    """RBAC権限定義"""
    
    PERMISSIONS = {
        UserRole.ADMIN: [
            "read:all",
            "write:all",
            "delete:all",
            "admin:all"
        ],
        UserRole.DEVELOPER: [
            "read:all",
            "write:own",
            "create:own"
        ],
        UserRole.USER: [
            "read:own"
        ],
        UserRole.SERVICE: [
            "read:all",
            "write:all"
        ]
    }
    
    @staticmethod
    def has_permission(role: UserRole, permission: str) -> bool:
        """権限チェック"""
        permissions = RBACPermissions.PERMISSIONS.get(role, [])
        return permission in permissions or "admin:all" in permissions
    
    @staticmethod
    async def check_permission(
        required_permission: str,
        user: User = Depends(AuthDependencies.get_current_user)
    ) -> bool:
        """権限チェック（FastAPI Dependency）"""
        if not RBACPermissions.has_permission(user.role, required_permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{required_permission}' required"
            )
        return True


# ===========================
# セキュリティテスト用エンドポイント
# ===========================

def create_security_endpoints(app: FastAPI):
    """セキュリティエンドポイント作成"""
    
    @app.post("/auth/login", response_model=Token)
    async def login(credentials: LoginRequest):
        """ログイン"""
        user = OAuth2Manager.authenticate_user(
            credentials.username,
            credentials.password
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        access_token = JWTManager.create_access_token(
            user_id=user.user_id,
            role=user.role
        )
        
        refresh_token = JWTManager.create_refresh_token(user.user_id)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": SecurityConfig.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user_id": user.user_id,
            "role": user.role
        }
    
    @app.post("/auth/token/refresh", response_model=Token)
    async def refresh_token(refresh_token: str):
        """トークンリフレッシュ"""
        try:
            token_data = JWTManager.verify_token(refresh_token)
        except HTTPException:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        access_token = JWTManager.create_access_token(
            user_id=token_data.user_id,
            role=token_data.role
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": SecurityConfig.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user_id": token_data.user_id,
            "role": token_data.role
        }
    
    @app.get("/auth/me", response_model=User)
    async def get_current_user(
        current_user: User = Depends(AuthDependencies.get_current_user)
    ):
        """現在のユーザー情報取得"""
        return current_user
    
    @app.get("/admin/users")
    async def list_users(
        _: User = Depends(AuthDependencies.get_admin_user)
    ):
        """管理者：全ユーザー一覧"""
        return {
            "users": [
                {"user_id": "001", "username": "admin", "role": "admin"},
                {"user_id": "002", "username": "developer", "role": "developer"}
            ]
        }
