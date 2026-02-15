"""
Step Deep Research Service MCPサーバー
深いリサーチ機能をMCPツールとして提供
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
    from manaos_integrations._paths import STEP_DEEP_RESEARCH_PORT
except Exception:  # pragma: no cover
    try:
        from _paths import STEP_DEEP_RESEARCH_PORT  # type: ignore
    except Exception:  # pragma: no cover
        STEP_DEEP_RESEARCH_PORT = int(os.getenv("STEP_DEEP_RESEARCH_PORT", "5121"))

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

logger = get_logger(__name__)

# APIエンドポイント
STEP_DEEP_RESEARCH_URL = os.getenv(
    "STEP_DEEP_RESEARCH_URL",
    f"http://127.0.0.1:{STEP_DEEP_RESEARCH_PORT}",
)

# MCPサーバーの初期化
if MCP_AVAILABLE:
    app = Server("step-deep-research")
else:
    app = None


def call_api(endpoint: str, method: str = "GET", data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Step Deep Research APIを呼び出す"""
    url = f"{STEP_DEEP_RESEARCH_URL}{endpoint}"
    
    try:
        if method == "GET":
            response = requests.get(url, timeout=30)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=600)  # リサーチは時間がかかる
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
                name="step_deep_research_health",
                description="Step Deep Research Serviceのヘルスチェック",
                inputSchema={"type": "object", "properties": {}}
            ),
            Tool(
                name="step_deep_research_create",
                description="深いリサーチジョブを作成します",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "リサーチクエリ（必須）"
                        }
                    },
                    "required": ["query"]
                }
            ),
            Tool(
                name="step_deep_research_execute",
                description="リサーチジョブを実行します",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "job_id": {
                            "type": "string",
                            "description": "ジョブID（必須）"
                        }
                    },
                    "required": ["job_id"]
                }
            ),
            Tool(
                name="step_deep_research_status",
                description="リサーチジョブのステータスを取得します",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "job_id": {
                            "type": "string",
                            "description": "ジョブID（必須）"
                        }
                    },
                    "required": ["job_id"]
                }
            )
        ]
    
    @app.call_tool()
    async def call_tool(name: str, arguments: Any) -> List[TextContent]:
        """ツールを実行"""
        try:
            args = json.loads(arguments) if isinstance(arguments, str) else arguments
            
            if name == "step_deep_research_health":
                result = call_api("/health")
            elif name == "step_deep_research_create":
                result = call_api("/research", "POST", args)
            elif name == "step_deep_research_execute":
                job_id = args.get("job_id")
                result = call_api(f"/research/{job_id}", "POST")
            elif name == "step_deep_research_status":
                job_id = args.get("job_id")
                result = call_api(f"/research/{job_id}/status")
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
