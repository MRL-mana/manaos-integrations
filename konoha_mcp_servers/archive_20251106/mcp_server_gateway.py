#!/usr/bin/env python3
"""MCP統合ゲートウェイすべてのMCPサーバーを1つのゲートウェイで統合管理
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any

from datetime import datetime
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import redis
import os

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(title="MCP Unified Gateway", version="1.0.0")

# 認証ミドルウェア（内部使用を想定）
# 必要に応じて認証を追加する場合は以下を有効化:
# from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
# security = HTTPBearer()
#
# @app.middleware("http")
# async def verify_token(request: Request, call_next):
#     # 認証トークンの検証処理
#     response = await call_next(request)
#     return response

# ルート追加
@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {"status": "ok", "service": "mcp_server_gateway"}

@app.get("/health")
async def health():
    """ヘルスチェック"""
    return {"status": "healthy"}

@app.get("/api/status")
async def api_status():
    """APIステータス"""
    return {"status": "running", "service": "mcp_server_gateway"}

# Redis client (optional)
redis_client = None

class MCPRequest(BaseModel):
    """MCPリクエストモデル"""
    mcp_server: str
    method: str
    params: Dict[str, Any]

class MCPResponse(BaseModel):
    """MCPレスポンスモデル"""
    success: bool
    data: Any
    error: Optional[str] = None
    timestamp: str

class MCPGateway:
    """MCP統合ゲートウェイ"""

    def __init__(self):
        # 環境変数からサーバーURLを取得（デフォルト値あり）
        localhost = os.getenv("MCP_LOCALHOST", "localhost")
        self.servers = {
            "manaos": {
                "url": os.getenv("MCP_MANAOS_URL", f"http://{localhost}:7000"),
                "description": "ManaOS統合API",
                "status": "unknown"
            },
            "image-editor": {
                "url": os.getenv("MCP_IMAGE_EDITOR_URL", f"http://{localhost}:5559"),
                "description": "Image Editor MCP",
                "status": "unknown"
            },
            "github": {
                "url": os.getenv("MCP_GITHUB_URL", f"http://{localhost}:3001"),
                "description": "GitHub MCP",
                "status": "unknown"
            },
            "filesystem": {
                "url": os.getenv("MCP_FILESYSTEM_URL", f"http://{localhost}:3010"),
                "description": "FileSystem MCP",
                "status": "unknown"
            },
            "browser": {
                "url": os.getenv("MCP_BROWSER_URL", f"http://{localhost}:5001"),
                "description": "Browser MCP",
                "status": "unknown"
            },
            "byterover": {
                "url": os.getenv("MCP_BYTEROVER_URL", "https://mcp.byterover.dev/mcp"),
                "description": "ByteRover MCP",
                "status": "unknown"
            },
            "super-ocr-pipeline": {
                "url": os.getenv("MCP_SUPER_OCR_URL", f"http://{localhost}:8002"),
                "description": "Super OCR Pipeline (超解像→OCR)",
                "status": "unknown"
            }
        }
        self.http_client = httpx.AsyncClient(timeout=30.0)

    async def check_server_health(self, server_name: str) -> bool:
        """サーバーのヘルスチェック

        Args:
            server_name: チェック対象のサーバー名

        Returns:
            サーバーが正常な場合True、それ以外False
        """
        if server_name not in self.servers:
            return False

        server = self.servers[server_name]
        try:
            # ヘルスチェックエンドポイント（存在する場合）
            health_url = f"{server['url']}/health"
            response = await self.http_client.get(health_url)
            self.servers[server_name]["status"] = "healthy" if response.status_code == 200 else "unhealthy"
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"⚠️ {server_name} health check failed: {e}")
            self.servers[server_name]["status"] = "unhealthy"
            return False

    async def forward_request(
        self,
        server_name: str,
        method: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """MCPリクエストを転送

        Args:
            server_name: 転送先サーバー名
            method: MCPメソッド名
            params: リクエストパラメータ

        Returns:
            サーバーからのレスポンスデータ

        Raises:
            HTTPException: サーバーが見つからない、またはエラー時
        """
        if server_name not in self.servers:
            raise HTTPException(status_code=404, detail=f"Unknown MCP server: {server_name}")

        server = self.servers[server_name]
        try:
            # MCPサーバーにリクエストを転送
            # 実際の実装は各MCPサーバーのプロトコルに依存
            if server_name == "byterover":
                # ByteRoverはHTTPS外部サービス
                response = await self.http_client.post(
                    server['url'],
                    json={"method": method, "params": params},
                    headers={"Content-Type": "application/json"}
                )
            else:
                # ローカルMCPサーバー（HTTP経由）
                response = await self.http_client.post(
                    f"{server['url']}/mcp",
                    json={"method": method, "params": params},
                    headers={"Content-Type": "application/json"}
                )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"❌ {server_name} request failed: {e}")
            raise HTTPException(status_code=500, detail=f"MCP server error: {str(e)}")

    async def get_server_list(self) -> List[Dict[str, Any]]:
        """利用可能なMCPサーバー一覧

        Returns:
            各サーバーの情報（名前、説明、ステータス、URL）のリスト
        """
        # ヘルスチェックを並列実行
        tasks = [self.check_server_health(name) for name in self.servers.keys()]
        await asyncio.gather(*tasks, return_exceptions=True)

        return [
            {
                "name": name,
                "description": info["description"],
                "status": info["status"],
                "url": info["url"]
            }
            for name, info in self.servers.items()
        ]

# グローバルゲートウェイインスタンス
gateway = MCPGateway()

@app.get("/health")
async def health_check():
    """ヘルスチェック"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {
        "name": "MCP Unified Gateway",
        "version": "1.0.0",
        "description": "統合MCPゲートウェイ",
        "endpoints": {
            "/health": "ヘルスチェック",
            "/servers": "利用可能なMCPサーバー一覧",
            "/mcp": "MCPリクエスト転送"
        }
    }

@app.get("/servers")
async def list_servers():
    """利用可能なMCPサーバー一覧"""
    servers = await gateway.get_server_list()
    return {
        "servers": servers,
        "count": len(servers),
        "healthy": sum(1 for s in servers if s["status"] == "healthy")
    }

@app.post("/mcp", response_model=MCPResponse)
async def handle_mcp_request(request: MCPRequest):
    """MCPリクエストを処理"""
    try:
        result = await gateway.forward_request(
            request.mcp_server,
            request.method,
            request.params
        )
        return MCPResponse(
            success=True,
            data=result,
            timestamp=datetime.now().isoformat()
        )
    except HTTPException as e:
        return MCPResponse(
            success=False,
            data=None,
            error=str(e.detail),
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        logger.error(f"❌ Unhandled error: {e}")
        return MCPResponse(
            success=False,
            data=None,
            error=str(e),
            timestamp=datetime.now().isoformat()
        )

@app.on_event("startup")
async def startup():
    """起動時の初期化"""
    logger.info("🚀 Starting MCP Unified Gateway...")

    # Redis接続（オプション）
    global redis_client
    try:
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
        redis_client.ping()
        logger.debug("✅ Connected to Redis")
    except Exception as e:
        logger.debug(f"⚠️  Redis connection failed: {e}")
        redis_client = None

    logger.info("✅ MCP Gateway ready!")

@app.on_event("shutdown")
async def shutdown():
    """シャットダウン時のクリーンアップ"""
    logger.info("🛑 Shutting down MCP Gateway...")

    # Redis接続のクリーンアップ
    global redis_client
    if redis_client:
        try:
            redis_client.close()
            logger.debug("✅ Redis connection closed")
        except Exception as e:
            logger.debug(f"⚠️ Redis close error: {e}")
        redis_client = None

    # HTTPクライアントのクリーンアップ
    await gateway.http_client.aclose()

    # その他のクリーンアップ処理
    logger.debug("✅ Cleanup completed")

if __name__ == "__main__":
    import uvicorn
    import os
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "3010")))
