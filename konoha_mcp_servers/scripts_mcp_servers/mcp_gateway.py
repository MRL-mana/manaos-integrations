#!/usr/bin/env python3
"""
MCP Gateway for WAN2.2
Model Context Protocol Gateway implementation
"""

import logging
import os
import sys
from datetime import datetime
from typing import Dict, Optional
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# GitHub Bridgeをインポート
sys.path.insert(0, '/root/mana')
try:
    from github_bridge import GitHubBridge
    GITHUB_BRIDGE_AVAILABLE = True
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"GitHub Bridge not available: {e}")
    GITHUB_BRIDGE_AVAILABLE = False

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="WAN2.2 MCP Gateway", version="2.2.0")

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class MCPRequest(BaseModel):
    method: str
    params: Optional[Dict] = None
    id: Optional[str] = None

class MCPResponse(BaseModel):
    result: Optional[Dict] = None
    error: Optional[Dict] = None
    id: Optional[str] = None

# MCPツール登録
mcp_tools = {
    "file_operations": {
        "name": "file_operations",
        "description": "ファイル操作ツール",
        "methods": ["read_file", "write_file", "list_directory"]
    },
    "web_search": {
        "name": "web_search",
        "description": "Web検索ツール",
        "methods": ["search", "get_page_content"]
    },
    "ai_integration": {
        "name": "ai_integration",
        "description": "AI統合ツール",
        "methods": ["chat_completion", "image_generation", "text_analysis"]
    },
    "system_monitoring": {
        "name": "system_monitoring",
        "description": "システム監視ツール",
        "methods": ["get_status", "get_metrics", "health_check"]
    }
}

# GitHub操作ツールを追加
if GITHUB_BRIDGE_AVAILABLE:
    mcp_tools["github_operations"] = {
        "name": "github_operations",
        "description": "GitHub操作ツール（ファイルの作成・更新・削除・取得）",
        "methods": ["push_file", "get_file", "delete_file", "list_files", "test_connection"]
    }

@app.get("/")
async def root():
    """MCP Gateway情報"""
    return {
        "name": "WAN2.2 MCP Gateway",
        "version": "2.2.0",
        "status": "active",
        "available_tools": list(mcp_tools.keys()),
        "features": [
            "MCP プロトコル対応",
            "ツール動的登録",
            "AI統合サポート",
            "システム監視連携",
            "GitHub操作サポート" if GITHUB_BRIDGE_AVAILABLE else ""
        ]
    }

@app.post("/mcp", response_model=MCPResponse)
async def mcp_request(request: MCPRequest):
    """MCP リクエスト処理"""
    try:
        logger.info(f"MCP Request: {request.method}")

        if request.method == "tools/list":
            return MCPResponse(
                result={"tools": list(mcp_tools.values())},
                id=request.id
            )

        elif request.method == "tools/call":
            tool_name = request.params.get("name") if request.params else None
            if tool_name in mcp_tools:
                result = await execute_tool(tool_name, request.params)
                return MCPResponse(
                    result=result,
                    id=request.id
                )
            else:
                return MCPResponse(
                    error={"message": f"Tool {tool_name} not found"},
                    id=request.id
                )

        elif request.method == "ping":
            return MCPResponse(
                result={"message": "pong", "timestamp": datetime.now().isoformat()},
                id=request.id
            )

        else:
            return MCPResponse(
                error={"message": f"Unknown method: {request.method}"},
                id=request.id
            )

    except Exception as e:
        logger.error(f"MCP Request error: {e}")
        return MCPResponse(
            error={"message": str(e)},
            id=request.id
        )

async def execute_tool(tool_name: str, params: Dict) -> Dict:
    """ツール実行"""

    if tool_name == "file_operations":
        method = params.get("method", "")
        if method == "read_file":
            file_path = params.get("file_path", "")
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return {"content": content, "success": True}
            except Exception as e:
                return {"error": str(e), "success": False}

        elif method == "list_directory":
            dir_path = params.get("dir_path", "/root")
            try:
                files = os.listdir(dir_path)
                return {"files": files, "success": True}
            except Exception as e:
                return {"error": str(e), "success": False}

    elif tool_name == "system_monitoring":
        method = params.get("method", "")
        if method == "get_status":
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "uptime": "running",
                "success": True
            }

        elif method == "health_check":
            return {
                "health": "ok",
                "services": ["mcp_gateway", "trinity_api"],
                "success": True
            }

    elif tool_name == "ai_integration":
        method = params.get("method", "")
        if method == "chat_completion":
            message = params.get("message", "")
            return {
                "response": f"MCP Gateway response to: {message}",
                "timestamp": datetime.now().isoformat(),
                "success": True
            }

    elif tool_name == "github_operations" and GITHUB_BRIDGE_AVAILABLE:
        method = params.get("method", "")
        try:
            bridge = GitHubBridge()

            if method == "push_file":
                path = params.get("path", "")
                content = params.get("content", "")
                message = params.get("message", "Update via ManaOS MCP Gateway")
                branch = params.get("branch", "main")
                result = bridge.push_file(path, content, message, branch)
                return result

            elif method == "get_file":
                path = params.get("path", "")
                branch = params.get("branch", "main")
                result = bridge.get_file(path, branch)
                return result

            elif method == "delete_file":
                path = params.get("path", "")
                message = params.get("message", "Delete via ManaOS MCP Gateway")
                branch = params.get("branch", "main")
                result = bridge.delete_file(path, message, branch)
                return result

            elif method == "list_files":
                path = params.get("path", "")
                branch = params.get("branch", "main")
                result = bridge.list_files(path, branch)
                return result

            elif method == "test_connection":
                result = bridge.test_connection()
                return result

            else:
                return {"error": f"Unknown GitHub method: {method}", "success": False}

        except Exception as e:
            logger.error(f"GitHub operation error: {e}")
            return {"error": str(e), "success": False}

    return {"error": "Unknown tool method", "success": False}

@app.get("/health")
async def health_check():
    """ヘルスチェック"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "mcp_tools": len(mcp_tools),
        "version": "2.2.0"
    }

@app.get("/tools")
async def list_tools():
    """利用可能なツール一覧"""
    return {
        "tools": mcp_tools,
        "total": len(mcp_tools)
    }

# ===== GitHub操作用REST APIエンドポイント（n8n連携用） =====
class GitHubPushRequest(BaseModel):
    """GitHubファイルプッシュリクエスト"""
    path: str
    content: str
    message: Optional[str] = "Update via ManaOS API"
    branch: Optional[str] = "main"

class GitHubGetRequest(BaseModel):
    """GitHubファイル取得リクエスト"""
    path: str
    branch: Optional[str] = "main"

@app.post("/api/github/push")
async def github_push_api(request: GitHubPushRequest):
    """GitHubファイルプッシュAPI（n8n連携用）"""
    if not GITHUB_BRIDGE_AVAILABLE:
        return {"success": False, "error": "GitHub Bridge not available"}

    try:
        bridge = GitHubBridge()
        result = bridge.push_file(
            path=request.path,
            content=request.content,
            message=request.message,
            branch=request.branch
        )
        return result
    except Exception as e:
        logger.error(f"GitHub push API error: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/github/get")
async def github_get_api(request: GitHubGetRequest):
    """GitHubファイル取得API（n8n連携用）"""
    if not GITHUB_BRIDGE_AVAILABLE:
        return {"success": False, "error": "GitHub Bridge not available"}

    try:
        bridge = GitHubBridge()
        result = bridge.get_file(
            path=request.path,
            branch=request.branch
        )
        return result
    except Exception as e:
        logger.error(f"GitHub get API error: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/github/list")
async def github_list_api(path: str = "", branch: str = "main"):
    """GitHubファイル一覧取得API（n8n連携用）"""
    if not GITHUB_BRIDGE_AVAILABLE:
        return {"success": False, "error": "GitHub Bridge not available"}

    try:
        bridge = GitHubBridge()
        result = bridge.list_files(path=path, branch=branch)
        return result
    except Exception as e:
        logger.error(f"GitHub list API error: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/github/test")
async def github_test_api():
    """GitHub接続テストAPI（n8n連携用）"""
    if not GITHUB_BRIDGE_AVAILABLE:
        return {"success": False, "error": "GitHub Bridge not available"}

    try:
        bridge = GitHubBridge()
        result = bridge.test_connection()
        return result
    except Exception as e:
        logger.error(f"GitHub test API error: {e}")
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    import os
    # 環境変数でポート指定可能（デフォルト: 3001）
    port = int(os.getenv("MCP_GATEWAY_PORT", "3001"))
    uvicorn.run(
        "mcp_gateway:app",
        host="0.0.0.0",
        port=port,
        reload=False,  # CPU削減のため無効化
        log_level="info"
    )
