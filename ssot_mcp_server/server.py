"""
SSOT API MCPサーバー
Single Source of Truth機能をMCPツールとして提供
"""

import os
import sys
import json
import logging
import requests
from typing import Any, Dict, List, Optional
from pathlib import Path
import io

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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# APIエンドポイント
SSOT_API_URL = os.getenv("SSOT_API_URL", "http://127.0.0.1:5120")

# MCPサーバーの初期化
if MCP_AVAILABLE:
    app = Server("ssot-api")
else:
    app = None


def call_api(endpoint: str, method: str = "GET", params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """SSOT APIを呼び出す"""
    url = f"{SSOT_API_URL}{endpoint}"
    
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
                name="ssot_api_health",
                description="SSOT APIのヘルスチェック",
                inputSchema={"type": "object", "properties": {}}
            ),
            Tool(
                name="ssot_get",
                description="SSOTデータを取得します",
                inputSchema={"type": "object", "properties": {}}
            ),
            Tool(
                name="ssot_get_summary",
                description="SSOTサマリーを取得します",
                inputSchema={"type": "object", "properties": {}}
            ),
            Tool(
                name="ssot_get_services",
                description="サービス状態のみを取得します",
                inputSchema={"type": "object", "properties": {}}
            ),
            Tool(
                name="ssot_get_recent_inputs",
                description="最新指令を取得します",
                inputSchema={"type": "object", "properties": {}}
            ),
            Tool(
                name="ssot_get_last_error",
                description="直近エラーを取得します",
                inputSchema={"type": "object", "properties": {}}
            )
        ]
    
    @app.call_tool()
    async def call_tool(name: str, arguments: Any) -> List[TextContent]:
        """ツールを実行"""
        try:
            args = json.loads(arguments) if isinstance(arguments, str) else arguments
            
            if name == "ssot_api_health":
                result = call_api("/health")
            elif name == "ssot_get":
                result = call_api("/api/ssot")
            elif name == "ssot_get_summary":
                result = call_api("/api/ssot/summary")
            elif name == "ssot_get_services":
                result = call_api("/api/ssot/services")
            elif name == "ssot_get_recent_inputs":
                result = call_api("/api/ssot/recent")
            elif name == "ssot_get_last_error":
                result = call_api("/api/ssot/error")
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
