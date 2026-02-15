"""
Portal Voice Integration MCPサーバー
Portal音声統合機能をMCPツールとして提供
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
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

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

PORTAL_VOICE_API_URL = os.getenv("PORTAL_VOICE_API_URL", "http://127.0.0.1:5116")

if MCP_AVAILABLE:
    app = Server("portal-voice-integration")
else:
    app = None


def call_api(endpoint: str, method: str = "GET", data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Portal Voice Integration APIを呼び出す"""
    url = f"{PORTAL_VOICE_API_URL}{endpoint}"
    
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
                name="portal_voice_health",
                description="Portal Voice Integrationのヘルスチェック",
                inputSchema={"type": "object", "properties": {}}
            ),
            Tool(
                name="portal_voice_execute",
                description="音声コマンドを実行します",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "音声テキスト"},
                        "user": {"type": "string", "description": "ユーザー名（オプション）"}
                    },
                    "required": ["text"]
                }
            ),
            Tool(
                name="portal_slack_execute",
                description="Slackコマンドを実行します",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Slackメッセージ"},
                        "user": {"type": "string", "description": "ユーザー名（オプション）"}
                    },
                    "required": ["text"]
                }
            )
        ]
    
    @app.call_tool()
    async def call_tool(name: str, arguments: Any) -> List[TextContent]:
        """ツールを実行"""
        try:
            args = json.loads(arguments) if isinstance(arguments, str) else arguments
            
            if name == "portal_voice_health":
                result = call_api("/health")
            elif name == "portal_voice_execute":
                result = call_api("/api/voice/execute", "POST", args)
            elif name == "portal_slack_execute":
                result = call_api("/api/slack/execute", "POST", args)
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
