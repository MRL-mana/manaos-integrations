"""
Slack Integration MCPサーバー
Slack統合機能をMCPツールとして提供
"""

import os
import sys
import json
from manaos_logger import get_logger, get_service_logger
import requests
from typing import Any, Dict, List, Optional
from pathlib import Path
import io

try:
    from manaos_integrations._paths import SLACK_INTEGRATION_PORT
except Exception:  # pragma: no cover
    try:
        from _paths import SLACK_INTEGRATION_PORT  # type: ignore
    except Exception:  # pragma: no cover
        SLACK_INTEGRATION_PORT = int(os.getenv("SLACK_INTEGRATION_PORT", "5114"))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')  # type: ignore[attr-defined]

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logging.warning("MCP SDKがインストールされていません。pip install mcp を実行してください。")  # type: ignore[name-defined]

logger = get_service_logger("server")

SLACK_API_URL = os.getenv("SLACK_API_URL", f"http://127.0.0.1:{SLACK_INTEGRATION_PORT}")

if MCP_AVAILABLE:
    app = Server("slack-integration")  # type: ignore[possibly-unbound]
else:
    app = None


def call_api(endpoint: str, method: str = "GET", data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Slack Integration APIを呼び出す"""
    url = f"{SLACK_API_URL}{endpoint}"
    
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
    @app.list_tools()  # type: ignore[union-attr]
    async def list_tools() -> List[Tool]:
        """利用可能なツール一覧を返す"""
        return [
            Tool(  # type: ignore[possibly-unbound]
                name="slack_integration_health",
                description="Slack Integrationのヘルスチェック",
                inputSchema={"type": "object", "properties": {}}
            ),
            Tool(  # type: ignore[possibly-unbound]
                name="slack_send_message",
                description="Slackにメッセージを送信します",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "送信するメッセージ"},
                        "channel": {"type": "string", "description": "チャンネル名（オプション）"}
                    },
                    "required": ["text"]
                }
            ),
            Tool(  # type: ignore[possibly-unbound]
                name="slack_test",
                description="Slack統合をテストします",
                inputSchema={"type": "object", "properties": {}}
            )
        ]
    
    @app.call_tool()  # type: ignore[union-attr]
    async def call_tool(name: str, arguments: Any) -> List[TextContent]:
        """ツールを実行"""
        try:
            args = json.loads(arguments) if isinstance(arguments, str) else arguments
            
            if name == "slack_integration_health":
                result = call_api("/health")
            elif name == "slack_send_message":
                result = call_api("/api/slack/webhook", "POST", args)
            elif name == "slack_test":
                result = call_api("/api/slack/test")
            else:
                result = {"error": f"Unknown tool: {name}"}
            
            return [TextContent(  # type: ignore[possibly-unbound]
                type="text",
                text=json.dumps(result, ensure_ascii=False, indent=2)
            )]
        
        except Exception as e:
            logger.error(f"ツール実行エラー ({name}): {e}")
            import traceback
            logger.error(traceback.format_exc())
            return [TextContent(  # type: ignore[possibly-unbound]
                type="text",
                text=json.dumps({"error": str(e)}, ensure_ascii=False)
            )]


async def main():
    """メイン関数"""
    if not MCP_AVAILABLE:
        logger.error("MCP SDKが利用できません")
        sys.exit(1)
    
    async with stdio_server() as (read_stream, write_stream):  # type: ignore[possibly-unbound]
        await app.run(  # type: ignore[union-attr]
            read_stream,
            write_stream,
            app.create_initialization_options()  # type: ignore[union-attr]
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
