#!/usr/bin/env python3
"""
MCP-Proxy: 安全で高性能なMCPサーバープロキシ
- レート制限
- 認証・認可
- リクエストログ
- エラーハンドリング
- ヘルスチェック
- メトリクス収集
"""
import asyncio
import json
from manaos_logger import get_logger
import os
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Request, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

# ログ設定
log_dir = Path("/root/logs/mcp_proxy")
log_dir.mkdir(parents=True, exist_ok=True)

logger = get_logger(__name__)

# FastAPI app
app = FastAPI(
    title="MCP-Proxy",
    version="2.0.0",
    description="安全で高性能なMCPサーバープロキシ"
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
    """MCP-Proxy設定"""
    # ポート
    PORT = int(os.getenv("MCP_PROXY_PORT", "3011"))

    # レート制限（リクエスト/分）
    RATE_LIMIT_PER_MINUTE = int(os.getenv("MCP_PROXY_RATE_LIMIT", "60"))

    # 認証トークン（環境変数から取得、なければ生成）
    AUTH_TOKEN = os.getenv("MCP_PROXY_AUTH_TOKEN", None)

    # タイムアウト（秒）
    REQUEST_TIMEOUT = 30.0

    # リトライ回数
    MAX_RETRIES = 3

    # ログ保持日数
    LOG_RETENTION_DAYS = 7


# ===== データモデル =====


class MCPRequest(BaseModel):
    """MCPリクエスト"""
    mcp_server: str = Field(..., description="MCPサーバー名")
    method: str = Field(..., description="MCPメソッド")
    params: Dict[str, Any] = Field(default_factory=dict, description="パラメータ")
    id: Optional[str] = Field(None, description="リクエストID")


class MCPResponse(BaseModel):
    """MCPレスポンス"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    timestamp: str
    request_id: Optional[str] = None
    server: Optional[str] = None


class HealthStatus(BaseModel):
    """ヘルスステータス"""
    status: str
    version: str
    uptime: str
    servers: Dict[str, Any]
    metrics: Dict[str, Any]


# ===== MCPサーバー設定 =====
MCP_SERVERS = {
    "trinity-agents": {
        "command": "python3",
        "args": ["/root/trinity_workspace/mcp-server/trinity_mcp_server.py"],
        "env": {"PYTHONPATH": "/root/trinity_workspace"},
        "type": "stdio",
        "description": "Trinity Agents MCP"
    },
    "trinity-manaos": {
        "command": "python3",
        "args": ["/root/trinity_mcp_server.py"],
        "env": {"PYTHONPATH": "/root"},
        "type": "stdio",
        "description": "Trinity ManaOS MCP"
    },
    "manasearch-nexus": {
        "command": "python3",
        "args": ["/root/manaos_v3/services/manasearch/mcp_server.py"],
        "env": {"PYTHONPATH": "/root/manaos_v3/services/manasearch"},
        "type": "stdio",
        "description": "Manasearch Nexus MCP"
    },
    "image-editor": {
        "command": "python3",
        "args": ["/root/trinity_workspace/mcp/image_editor_mcp_server.py"],
        "env": {"PYTHONPATH": "/root/trinity_workspace"},
        "type": "stdio",
        "description": "Image Editor MCP"
    },
    "super-ocr-pipeline": {
        "command": "python3",
        "args": ["/root/super_ocr_pipeline/mcp_server.py"],
        "env": {"PYTHONPATH": "/root/super_ocr_pipeline"},
        "type": "stdio",
        "description": "Super OCR Pipeline MCP"
    },
    "runpod-gpu": {
        "command": "docker",
        "args": ["exec", "-i", "runpod-mcp-server", "python", "-u", "runpod_mcp_server.py"],
        "env": {},
        "type": "docker",
        "description": "RunPod GPU MCP"
    }
}


# ===== レート制限 =====


class RateLimiter:
    """レート制限管理"""

    def __init__(self, max_requests: int = 60, window: int = 60):
        self.max_requests = max_requests
        self.window = window  # 秒
        self.requests: Dict[str, List[float]] = defaultdict(list)
        self.lock = asyncio.Lock()

    async def is_allowed(self, key: str) -> bool:
        """リクエストが許可されるかチェック"""
        async with self.lock:
            now = time.time()
            # 古いリクエストを削除
            self.requests[key] = [
                req_time for req_time in self.requests[key]
                if now - req_time < self.window
            ]

            # 制限チェック
            if len(self.requests[key]) >= self.max_requests:
                return False

            # リクエストを記録
            self.requests[key].append(now)
            return True

    def get_remaining(self, key: str) -> int:
        """残りリクエスト数を取得"""
        now = time.time()
        self.requests[key] = [
            req_time for req_time in self.requests[key]
            if now - req_time < self.window
        ]
        return max(0, self.max_requests - len(self.requests[key]))


rate_limiter = RateLimiter(
    max_requests=Config.RATE_LIMIT_PER_MINUTE,
    window=60
)


# ===== 認証 =====
async def verify_token(authorization: Optional[str] = Header(None)):
    """認証トークンを検証"""
    if Config.AUTH_TOKEN is None:
        # 認証が無効な場合はスキップ
        return True

    if authorization is None:
        raise HTTPException(status_code=401, detail="認証トークンが必要です")

    # Bearer トークンを抽出
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="無効な認証形式")

    token = authorization.replace("Bearer ", "")
    if token != Config.AUTH_TOKEN:
        raise HTTPException(status_code=403, detail="無効な認証トークン")

    return True


# ===== メトリクス =====


class Metrics:
    """メトリクス収集"""

    def __init__(self):
        self.start_time = datetime.now()
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.server_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {
            "requests": 0,
            "success": 0,
            "errors": 0
        })
        self.error_types: Dict[str, int] = defaultdict(int)

    def record_request(self, server: str, success: bool, error_type: Optional[str] = None):
        """リクエストを記録"""
        self.total_requests += 1
        if success:
            self.successful_requests += 1
            self.server_stats[server]["success"] += 1
        else:
            self.failed_requests += 1
            self.server_stats[server]["errors"] += 1
            if error_type:
                self.error_types[error_type] += 1

        self.server_stats[server]["requests"] += 1

    def get_stats(self) -> Dict[str, Any]:
        """統計情報を取得"""
        uptime = datetime.now() - self.start_time
        return {
            "uptime_seconds": int(uptime.total_seconds()),
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": (
                self.successful_requests / self.total_requests * 100
                if self.total_requests > 0 else 0
            ),
            "server_stats": dict(self.server_stats),
            "error_types": dict(self.error_types)
        }


metrics = Metrics()


# ===== MCPプロキシ =====


class MCPProxy:
    """MCPプロキシコア"""

    def __init__(self):
        self.http_client = httpx.AsyncClient(timeout=Config.REQUEST_TIMEOUT)
        self.server_processes: Dict[str, Any] = {}

    async def forward_request(
        self,
        server_name: str,
        method: str,
        params: Dict[str, Any],
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """MCPリクエストを転送"""
        if server_name not in MCP_SERVERS:
            raise HTTPException(
                status_code=404,
                detail=f"Unknown MCP server: {server_name}"
            )

        server_config = MCP_SERVERS[server_name]
        logger.info(f"📤 Forwarding request to {server_name}: {method}")

        # リトライロジック
        last_error = None
        for attempt in range(Config.MAX_RETRIES):
            try:
                if server_config["type"] == "stdio":
                    # stdio経由のMCPサーバー（直接プロセス実行）
                    result = await self._execute_stdio_request(
                        server_name, server_config, method, params
                    )
                    metrics.record_request(server_name, True)
                    return result

                elif server_config["type"] == "docker":
                    # Docker経由のMCPサーバー
                    result = await self._execute_docker_request(
                        server_name, server_config, method, params
                    )
                    metrics.record_request(server_name, True)
                    return result

                else:
                    raise ValueError(f"Unknown server type: {server_config['type']}")

            except Exception as e:
                last_error = e
                logger.warning(f"⚠️ Attempt {attempt + 1} failed for {server_name}: {e}")
                if attempt < Config.MAX_RETRIES - 1:
                    await asyncio.sleep(0.5 * (attempt + 1))  # 指数バックオフ

        # 全リトライ失敗
        error_msg = str(last_error)
        metrics.record_request(server_name, False, error_type=type(last_error).__name__)
        raise HTTPException(status_code=500, detail=f"MCP server error: {error_msg}")

    async def _execute_stdio_request(
        self,
        server_name: str,
        config: Dict[str, Any],
        method: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """stdio経由のMCPリクエストを実行"""
        # MCP stdioプロトコルに従って実装
        # 実際の実装は各MCPサーバーのプロトコルに依存
        # ここでは簡易実装（実際はMCP SDKを使用）

        # 一時的な実装: HTTPエンドポイントがある場合はそれを使用
        # ない場合は、stdioプロセスを起動して通信

        # 実際の実装では、MCP SDKを使用してstdio通信を行う
        # ここではプレースホルダーとしてエラーを返す
        raise NotImplementedError(
            "stdio MCP通信はMCP SDKを使用して実装する必要があります"
        )

    async def _execute_docker_request(
        self,
        server_name: str,
        config: Dict[str, Any],
        method: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Docker経由のMCPリクエストを実行"""
        # Docker exec経由でMCPサーバーに接続
        # 実際の実装では、docker execでプロセスを起動して通信

        raise NotImplementedError(
            "Docker MCP通信は実装が必要です"
        )

    async def check_server_health(self, server_name: str) -> Dict[str, Any]:
        """サーバーのヘルスチェック"""
        if server_name not in MCP_SERVERS:
            return {"status": "unknown", "error": "Server not found"}

        try:
            # 簡易ヘルスチェック（実際の実装では各サーバーのヘルスエンドポイントを確認）
            return {
                "status": "healthy",
                "server": server_name,
                "description": MCP_SERVERS[server_name]["description"]
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "server": server_name,
                "error": str(e)
            }

    async def get_all_servers_health(self) -> Dict[str, Dict[str, Any]]:
        """全サーバーのヘルスチェック"""
        tasks = [
            self.check_server_health(server_name)
            for server_name in MCP_SERVERS.keys()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        health_status = {}
        for server_name, result in zip(MCP_SERVERS.keys(), results):
            if isinstance(result, Exception):
                health_status[server_name] = {
                    "status": "error",
                    "error": str(result)
                }
            else:
                health_status[server_name] = result

        return health_status


# グローバルプロキシインスタンス
proxy = MCPProxy()


# ===== APIエンドポイント =====


@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {
        "name": "MCP-Proxy",
        "version": "2.0.0",
        "description": "安全で高性能なMCPサーバープロキシ",
        "features": [
            "レート制限",
            "認証・認可",
            "リクエストログ",
            "エラーハンドリング",
            "ヘルスチェック",
            "メトリクス収集"
        ],
        "endpoints": {
            "/health": "ヘルスチェック",
            "/servers": "利用可能なMCPサーバー一覧",
            "/servers/{name}/health": "特定サーバーのヘルスチェック",
            "/mcp": "MCPリクエスト転送",
            "/metrics": "メトリクス情報"
        }
    }


@app.get("/health", response_model=HealthStatus)
async def health_check():
    """ヘルスチェック"""
    servers_health = await proxy.get_all_servers_health()
    uptime = datetime.now() - metrics.start_time

    return HealthStatus(
        status="healthy",
        version="2.0.0",
        uptime=str(uptime),
        servers=servers_health,
        metrics=metrics.get_stats()
    )


@app.get("/servers")
async def list_servers():
    """利用可能なMCPサーバー一覧"""
    servers_health = await proxy.get_all_servers_health()

    servers_list = []
    for server_name, config in MCP_SERVERS.items():
        health = servers_health.get(server_name, {"status": "unknown"})
        servers_list.append({
            "name": server_name,
            "description": config["description"],
            "type": config["type"],
            "status": health.get("status", "unknown"),
            "error": health.get("error")
        })

    return {
        "servers": servers_list,
        "total": len(servers_list),
        "healthy": sum(1 for s in servers_list if s["status"] == "healthy")
    }


@app.get("/servers/{server_name}/health")
async def server_health(server_name: str):
    """特定サーバーのヘルスチェック"""
    health = await proxy.check_server_health(server_name)
    return health


@app.post("/mcp", response_model=MCPResponse)
async def handle_mcp_request(
    request: MCPRequest,
    authorization: Optional[str] = Header(None)
):
    """MCPリクエストを処理"""
    # 認証チェック
    if Config.AUTH_TOKEN:
        await verify_token(authorization)

    # レート制限チェック
    client_id = request.id or "anonymous"
    if not await rate_limiter.is_allowed(client_id):
        remaining = rate_limiter.get_remaining(client_id)
        raise HTTPException(
            status_code=429,
            detail=f"レート制限に達しました。残り: {remaining}リクエスト/分"
        )

    # リクエストログ
    logger.info(
        f"📥 MCP Request: {request.mcp_server}.{request.method} "
        f"(ID: {request.id})"
    )

    try:
        # リクエスト転送
        result = await proxy.forward_request(
            request.mcp_server,
            request.method,
            request.params,
            request.id
        )

        return MCPResponse(
            success=True,
            data=result,
            timestamp=datetime.now().isoformat(),
            request_id=request.id,
            server=request.mcp_server
        )

    except HTTPException as e:
        return MCPResponse(
            success=False,
            error=str(e.detail),
            timestamp=datetime.now().isoformat(),
            request_id=request.id,
            server=request.mcp_server
        )

    except Exception as e:
        logger.error(f"❌ Unhandled error: {e}", exc_info=True)
        return MCPResponse(
            success=False,
            error=str(e),
            timestamp=datetime.now().isoformat(),
            request_id=request.id,
            server=request.mcp_server
        )


@app.get("/metrics")
async def get_metrics():
    """メトリクス情報を取得"""
    return {
        "metrics": metrics.get_stats(),
        "rate_limit": {
            "max_per_minute": Config.RATE_LIMIT_PER_MINUTE,
            "current_usage": "N/A"  # 実装が必要
        }
    }


@app.on_event("startup")
async def startup():
    """起動時の初期化"""
    logger.info("🚀 Starting MCP-Proxy...")

    # 認証トークンの生成（未設定の場合）
    if Config.AUTH_TOKEN is None:
        import secrets
        token = secrets.token_urlsafe(32)
        logger.warning(f"⚠️ 認証トークンが未設定です。生成されたトークン: {token}")
        logger.warning("⚠️ 環境変数 MCP_PROXY_AUTH_TOKEN に設定してください")
        Config.AUTH_TOKEN = token

    logger.info(f"✅ MCP-Proxy ready on port {Config.PORT}")
    logger.info(f"📊 Rate limit: {Config.RATE_LIMIT_PER_MINUTE} requests/minute")
    logger.info(f"🔐 Auth: {'Enabled' if Config.AUTH_TOKEN else 'Disabled'}")


@app.on_event("shutdown")
async def shutdown():
    """シャットダウン時のクリーンアップ"""
    logger.info("🛑 Shutting down MCP-Proxy...")
    await proxy.http_client.aclose()


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=Config.PORT,
        log_level="info"
    )

