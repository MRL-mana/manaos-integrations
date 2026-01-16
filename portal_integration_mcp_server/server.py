"""
Portal Integration API MCPサーバー
Portal統合機能をMCPツールとして提供
"""

import os
import sys
import json
import logging
import requests
from typing import Any, Dict, List, Optional
from pathlib import Path
import io

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logging.warning("MCP SDKがインストールされていません。pip install mcp を実行してください。")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PORTAL_API_URL = os.getenv("PORTAL_API_URL", "http://localhost:5108")

if MCP_AVAILABLE:
    app = Server("portal-integration")
else:
    app = None


def call_api(endpoint: str, method: str = "GET", data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Portal Integration APIを呼び出す"""
    url = f"{PORTAL_API_URL}{endpoint}"
    
    try:
        if method == "GET":
            response = requests.get(url, timeout=30)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=30)
        else:
            return {"error": f"Unsupported method: {method}"}
        
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"API呼び出しエラー ({endpoint}): {e}")
        return {"error": str(e), "success": False}


if MCP_AVAILABLE:
    @app.list_tools()
    async def list_tools() -> List[Tool]:
        """利用可能なツール一覧を返す"""
        return [
            Tool(
                name="portal_integration_health",
                description="Portal Integration APIのヘルスチェック",
                inputSchema={"type": "object", "properties": {}}
            ),
            Tool(
                name="portal_execute",
                description="タスクを実行します",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "実行するテキスト"},
                        "mode": {"type": "string", "description": "実行モード（オプション）"}
                    },
                    "required": ["text"]
                }
            ),
            Tool(
                name="portal_get_mode",
                description="現在のモードを取得します",
                inputSchema={"type": "object", "properties": {}}
            ),
            Tool(
                name="portal_set_mode",
                description="モードを設定します",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "mode": {"type": "string", "description": "設定するモード"}
                    },
                    "required": ["mode"]
                }
            ),
            Tool(
                name="portal_get_queue_status",
                description="キュー状態を取得します",
                inputSchema={"type": "object", "properties": {}}
            ),
            Tool(
                name="portal_get_history",
                description="実行履歴を取得します",
                inputSchema={"type": "object", "properties": {}}
            )
        ]
    
    @app.call_tool()
    async def call_tool(name: str, arguments: Any) -> List[TextContent]:
        """ツールを実行"""
        try:
            args = json.loads(arguments) if isinstance(arguments, str) else arguments
            
            if name == "portal_integration_health":
                result = call_api("/health")
            elif name == "portal_execute":
                result = call_api("/api/execute", "POST", args)
            elif name == "portal_get_mode":
                result = call_api("/api/mode")
            elif name == "portal_set_mode":
                result = call_api("/api/mode", "POST", args)
            elif name == "portal_get_queue_status":
                result = call_api("/api/queue/status")
            elif name == "portal_get_history":
                result = call_api("/api/history")
            else:
                result = {"error": f"Unknown tool: {name}"}
            
            return [TextContent(
                type="text",
                text=json.dumps(result, ensure_ascii=False, indent=2)
            )]
        
        except Exception as e:
            logger.error(f"ツール実行エラー ({name}): {e}")
            import traceback
            logger.error(traceback.format_exc())
            return [TextContent(
                type="text",
                text=json.dumps({"error": str(e)}, ensure_ascii=False)
            )]


async def main():
    """メイン関数"""
    if not MCP_AVAILABLE:
        logger.error("MCP SDKが利用できません")
        sys.exit(1)
    
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
