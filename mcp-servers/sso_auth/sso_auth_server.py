#!/usr/bin/env python3
"""
SSO認証サーバー: Google/Slack OAuth + RBAC
"""
import asyncio
import logging
import os
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List

import httpx
from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel

# ログ設定
log_dir = Path("/root/logs/sso_auth")
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "sso_auth.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="SSO Auth Server",
    version="1.0.0",
    description="Google/Slack OAuth + RBAC"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== 設定 =====
class Config:
    """設定"""
    PORT = int(os.getenv("SSO_AUTH_PORT", "5018"))
    JWT_SECRET = os.getenv("JWT_SECRET", secrets.token_urlsafe(32))
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRATION = 3600  # 1時間

    # Google OAuth
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:5018/auth/google/callback")

    # Slack OAuth
    SLACK_CLIENT_ID = os.getenv("SLACK_CLIENT_ID", "")
    SLACK_CLIENT_SECRET = os.getenv("SLACK_CLIENT_SECRET", "")
    SLACK_REDIRECT_URI = os.getenv("SLACK_REDIRECT_URI", "http://localhost:5018/auth/slack/callback")


# ===== データモデル =====
class User(BaseModel):
    """ユーザーモデル"""
    id: str
    email: str
    name: str
    role: str  # admin, editor, viewer
    provider: str  # google, slack
    avatar: Optional[str] = None


class TokenResponse(BaseModel):
    """トークンレスポンス"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: User


# ===== RBAC設定 =====
ROLES = {
    "admin": {
        "permissions": ["read", "write", "delete", "admin"],
        "description": "管理者: 全権限"
    },
    "editor": {
        "permissions": ["read", "write"],
        "description": "編集者: 読み書き可能"
    },
    "viewer": {
        "permissions": ["read"],
        "description": "閲覧者: 読み取りのみ"
    }
}

# ユーザーストア（実際の実装ではDBを使用）
user_store: Dict[str, User] = {}


# ===== JWT管理 =====
def create_access_token(user: User) -> str:
    """JWTトークンを作成"""
    payload = {
        "sub": user.id,
        "email": user.email,
        "role": user.role,
        "provider": user.provider,
        "exp": datetime.utcnow() + timedelta(seconds=Config.JWT_EXPIRATION)
    }
    return jwt.encode(payload, Config.JWT_SECRET, algorithm=Config.JWT_ALGORITHM)


def verify_token(token: str) -> Optional[Dict]:
    """JWTトークンを検証"""
    try:
        payload = jwt.decode(token, Config.JWT_SECRET, algorithms=[Config.JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


# ===== OAuth処理 =====
class OAuthProvider:
    """OAuthプロバイダー基底クラス"""

    async def get_user_info(self, access_token: str) -> Dict:
        """ユーザー情報を取得"""
        raise NotImplementedError


class GoogleOAuth(OAuthProvider):
    """Google OAuth"""

    async def get_user_info(self, access_token: str) -> Dict:
        """Googleからユーザー情報を取得"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            response.raise_for_status()
            return response.json()

    def get_authorization_url(self, state: str) -> str:
        """認証URLを取得"""
        params = {
            "client_id": Config.GOOGLE_CLIENT_ID,
            "redirect_uri": Config.GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state
        }
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"https://accounts.google.com/o/oauth2/v2/auth?{query_string}"

    async def exchange_code(self, code: str) -> str:
        """認証コードをアクセストークンに交換"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": Config.GOOGLE_CLIENT_ID,
                    "client_secret": Config.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": Config.GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code"
                }
            )
            response.raise_for_status()
            return response.json()["access_token"]


class SlackOAuth(OAuthProvider):
    """Slack OAuth"""

    async def get_user_info(self, access_token: str) -> Dict:
        """Slackからユーザー情報を取得"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://slack.com/api/users.identity",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            response.raise_for_status()
            data = response.json()
            if not data.get("ok"):
                raise HTTPException(status_code=401, detail="Slack認証失敗")
            return data.get("user", {})

    def get_authorization_url(self, state: str) -> str:
        """認証URLを取得"""
        params = {
            "client_id": Config.SLACK_CLIENT_ID,
            "redirect_uri": Config.SLACK_REDIRECT_URI,
            "scope": "identity.basic identity.email",
            "state": state
        }
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"https://slack.com/oauth/v2/authorize?{query_string}"

    async def exchange_code(self, code: str) -> str:
        """認証コードをアクセストークンに交換"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://slack.com/api/oauth.v2.access",
                data={
                    "code": code,
                    "client_id": Config.SLACK_CLIENT_ID,
                    "client_secret": Config.SLACK_CLIENT_SECRET,
                    "redirect_uri": Config.SLACK_REDIRECT_URI
                }
            )
            response.raise_for_status()
            data = response.json()
            if not data.get("ok"):
                raise HTTPException(status_code=401, detail="Slack認証失敗")
            return data["authed_user"]["access_token"]


google_oauth = GoogleOAuth()
slack_oauth = SlackOAuth()


# ===== ユーザー管理 =====
def get_or_create_user(user_info: Dict, provider: str) -> User:
    """ユーザーを取得または作成"""
    email = user_info.get("email", "")
    user_id = f"{provider}:{email}"

    if user_id in user_store:
        return user_store[user_id]

    # 新規ユーザー作成（デフォルトはviewer）
    user = User(
        id=user_id,
        email=email,
        name=user_info.get("name", user_info.get("real_name", email)),
        role="viewer",  # デフォルトロール
        provider=provider,
        avatar=user_info.get("picture") or user_info.get("image_192")
    )

    user_store[user_id] = user
    logger.info(f"新規ユーザー作成: {user.email} ({user.role})")
    return user


# ===== 認証依存 =====
security = HTTPBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """現在のユーザーを取得"""
    token = credentials.credentials
    payload = verify_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無効なトークン"
        )

    user_id = payload.get("sub")
    if user_id not in user_store:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ユーザーが見つかりません"
        )

    return user_store[user_id]


def require_role(allowed_roles: List[str]):
    """ロールチェックデコレータ"""
    def decorator(user: User = Depends(get_current_user)):
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"権限がありません。必要なロール: {', '.join(allowed_roles)}"
            )
        return user
    return decorator


# ===== APIエンドポイント =====
@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {
        "name": "SSO Auth Server",
        "version": "1.0.0",
        "providers": ["google", "slack"],
        "roles": list(ROLES.keys()),
        "endpoints": {
            "/auth/google": "Google OAuth認証開始",
            "/auth/slack": "Slack OAuth認証開始",
            "/auth/me": "現在のユーザー情報",
            "/auth/roles": "ロール一覧"
        }
    }


@app.get("/auth/google")
async def google_auth():
    """Google OAuth認証開始"""
    if not Config.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Google OAuth未設定")

    state = secrets.token_urlsafe(32)
    auth_url = google_oauth.get_authorization_url(state)
    return RedirectResponse(url=auth_url)


@app.get("/auth/google/callback")
async def google_callback(code: str, state: str):
    """Google OAuthコールバック"""
    try:
        # アクセストークン取得
        access_token = await google_oauth.exchange_code(code)

        # ユーザー情報取得
        user_info = await google_oauth.get_user_info(access_token)

        # ユーザー作成/取得
        user = get_or_create_user(user_info, "google")

        # JWTトークン生成
        jwt_token = create_access_token(user)

        # リダイレクト（実際の実装ではフロントエンドにリダイレクト）
        return JSONResponse({
            "access_token": jwt_token,
            "token_type": "bearer",
            "expires_in": Config.JWT_EXPIRATION,
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": user.role,
                "avatar": user.avatar
            }
        })

    except Exception as e:
        logger.error(f"Google認証エラー: {e}")
        raise HTTPException(status_code=401, detail=f"認証に失敗しました: {str(e)}")


@app.get("/auth/slack")
async def slack_auth():
    """Slack OAuth認証開始"""
    if not Config.SLACK_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Slack OAuth未設定")

    state = secrets.token_urlsafe(32)
    auth_url = slack_oauth.get_authorization_url(state)
    return RedirectResponse(url=auth_url)


@app.get("/auth/slack/callback")
async def slack_callback(code: str, state: str):
    """Slack OAuthコールバック"""
    try:
        # アクセストークン取得
        access_token = await slack_oauth.exchange_code(code)

        # ユーザー情報取得
        user_info = await slack_oauth.get_user_info(access_token)

        # ユーザー作成/取得
        user = get_or_create_user(user_info, "slack")

        # JWTトークン生成
        jwt_token = create_access_token(user)

        return JSONResponse({
            "access_token": jwt_token,
            "token_type": "bearer",
            "expires_in": Config.JWT_EXPIRATION,
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": user.role,
                "avatar": user.avatar
            }
        })

    except Exception as e:
        logger.error(f"Slack認証エラー: {e}")
        raise HTTPException(status_code=401, detail=f"認証に失敗しました: {str(e)}")


@app.get("/auth/me")
async def get_me(user: User = Depends(get_current_user)):
    """現在のユーザー情報を取得"""
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "provider": user.provider,
        "avatar": user.avatar,
        "permissions": ROLES[user.role]["permissions"]
    }


@app.get("/auth/roles")
async def get_roles():
    """ロール一覧を取得"""
    return {
        "roles": {
            role: {
                "permissions": info["permissions"],
                "description": info["description"]
            }
            for role, info in ROLES.items()
        }
    }


@app.post("/auth/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    new_role: str,
    admin_user: User = Depends(require_role(["admin"]))
):
    """ユーザーロールを更新（管理者のみ）"""
    if new_role not in ROLES:
        raise HTTPException(status_code=400, detail=f"無効なロール: {new_role}")

    if user_id not in user_store:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")

    user_store[user_id].role = new_role
    logger.info(f"ユーザーロール更新: {user_id} -> {new_role} (by {admin_user.email})")

    return {
        "success": True,
        "user_id": user_id,
        "new_role": new_role
    }


@app.get("/auth/users")
async def list_users(admin_user: User = Depends(require_role(["admin"]))):
    """ユーザー一覧を取得（管理者のみ）"""
    return {
        "users": [
            {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": user.role,
                "provider": user.provider
            }
            for user in user_store.values()
        ]
    }


@app.on_event("startup")
async def startup():
    """起動時の初期化"""
    logger.info("🚀 SSO Auth Server 起動中...")
    logger.info(f"📊 ポート: {Config.PORT}")
    logger.info(f"🔐 Google OAuth: {'有効' if Config.GOOGLE_CLIENT_ID else '無効'}")
    logger.info(f"🔐 Slack OAuth: {'有効' if Config.SLACK_CLIENT_ID else '無効'}")
    logger.info("✅ サーバー準備完了")


@app.on_event("shutdown")
async def shutdown():
    """シャットダウン時のクリーンアップ"""
    logger.info("🛑 SSO Auth Server シャットダウン中...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=Config.PORT,
        log_level="info"
    )

