"""
System Status API MCPサーバー
システムステータス監視機能をMCPツールとして提供
"""

import os
import sys
import json
from manaos_logger import get_logger
import requests
from typing import Any, Dict, List, Optional
from pathlib import Path
import io

try:
    from manaos_integrations._paths import VIDEO_PIPELINE_PORT
except Exception:  # pragma: no cover
    try:
        from _paths import VIDEO_PIPELINE_PORT  # type: ignore
    except Exception:  # pragma: no cover
        VIDEO_PIPELINE_PORT = int(os.getenv("VIDEO_PIPELINE_PORT", "5112"))

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
SYSTEM_STATUS_URL = os.getenv("SYSTEM_STATUS_URL", f"http://127.0.0.1:{VIDEO_PIPELINE_PORT}")

# MCPサーバーの初期化
if MCP_AVAILABLE:
    app = Server("system-status")
else:
    app = None


def call_api(endpoint: str, method: str = "GET", params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """System Status APIを呼び出す"""
    url = f"{SYSTEM_STATUS_URL}{endpoint}"
    
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
                name="system_status_health",
                description="System Status APIのヘルスチェック",
                inputSchema={"type": "object", "properties": {}}
            ),
            Tool(
                name="system_status_get_all",
                description="すべてのサービスのステータスを取得します",
                inputSchema={"type": "object", "properties": {}}
            ),
            Tool(
                name="system_status_get_simple",
                description="簡易ステータスを取得します（スマホ向け）",
                inputSchema={"type": "object", "properties": {}}
            ),
            Tool(
                name="system_status_get_resources",
                description="システムリソース情報を取得します",
                inputSchema={"type": "object", "properties": {}}
            )
        ]
    
    @app.call_tool()
    async def call_tool(name: str, arguments: Any) -> List[TextContent]:
        """ツールを実行"""
        try:
            args = json.loads(arguments) if isinstance(arguments, str) else arguments
            
            if name == "system_status_health":
                result = call_api("/health")
            elif name == "system_status_get_all":
                result = call_api("/api/status")
            elif name == "system_status_get_simple":
                result = call_api("/api/status/simple")
            elif name == "system_status_get_resources":
                result = call_api("/api/resources")
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
