"""
Service Monitor MCPサーバー
サービス監視機能をMCPツールとして提供
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
    from manaos_integrations._paths import LLM_ROUTING_PORT
except Exception:  # pragma: no cover
    try:
        from _paths import LLM_ROUTING_PORT  # type: ignore
    except Exception:  # pragma: no cover
        LLM_ROUTING_PORT = int(os.getenv("LLM_ROUTING_PORT", "5117"))

# Windows環境での文字エンコーディング設定
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# パスを追加
sys.path.insert(0, str(Path(__file__).parent.parent))

# MCP SDKのインポート
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logging.warning("MCP SDKがインストールされていません。pip install mcp を実行してください。")

logger = get_service_logger("server")

# APIエンドポイント
# Service Monitor 自体の待受は 5111 がデフォルト。監視対象の LLM Routing とは別ポート。
SERVICE_MONITOR_DEFAULT_PORT = int(os.getenv("SERVICE_MONITOR_PORT", "5111"))
SERVICE_MONITOR_URL = os.getenv(
    "SERVICE_MONITOR_URL",
    f"http://127.0.0.1:{SERVICE_MONITOR_DEFAULT_PORT}",
)

# MCPサーバーの初期化
if MCP_AVAILABLE:
    app = Server("service-monitor")
else:
    app = None


def call_api(endpoint: str, method: str = "GET", params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Service Monitor APIを呼び出す"""
    url = f"{SERVICE_MONITOR_URL}{endpoint}"
    
    try:
        if method == "GET":
            response = requests.get(url, params=params, timeout=30)
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
                name="service_monitor_health",
                description="Service Monitorのヘルスチェック",
                inputSchema={"type": "object", "properties": {}}
            ),
            Tool(
                name="service_monitor_get_status",
                description="サービス監視ステータスを取得します",
                inputSchema={"type": "object", "properties": {}}
            )
        ]
    
    @app.call_tool()
    async def call_tool(name: str, arguments: Any) -> List[TextContent]:
        """ツールを実行"""
        try:
            args = json.loads(arguments) if isinstance(arguments, str) else arguments
            
            if name == "service_monitor_health":
                result = call_api("/health")
            elif name == "service_monitor_get_status":
                result = call_api("/api/status")
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
