"""
Gallery API Server MCPサーバー
画像生成・管理機能をMCPツールとして提供
"""

import os
import sys
import json
from manaos_logger import get_logger
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

logger = get_logger(__name__)

# APIエンドポイント
GALLERY_API_URL = os.getenv("GALLERY_API_URL", "http://127.0.0.1:5559")

# MCPサーバーの初期化
if MCP_AVAILABLE:
    app = Server("gallery-api")
else:
    app = None


def call_api(endpoint: str, method: str = "GET", data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Gallery API Serverを呼び出す"""
    url = f"{GALLERY_API_URL}{endpoint}"
    
    try:
        if method == "GET":
            response = requests.get(url, timeout=30)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=300)  # 画像生成は時間がかかる
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
                name="gallery_api_health",
                description="Gallery API Serverのヘルスチェック",
                inputSchema={"type": "object", "properties": {}}
            ),
            Tool(
                name="gallery_generate_image",
                description="画像を生成します",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "プロンプト（必須）"
                        },
                        "model": {
                            "type": "string",
                            "description": "モデル名（デフォルト: realisian_v60.safetensors）",
                            "default": "realisian_v60.safetensors"
                        },
                        "steps": {
                            "type": "integer",
                            "description": "ステップ数（デフォルト: 50）",
                            "default": 50
                        },
                        "guidance_scale": {
                            "type": "number",
                            "description": "ガイダンススケール（デフォルト: 7.5）",
                            "default": 7.5
                        },
                        "width": {
                            "type": "integer",
                            "description": "画像幅（デフォルト: 768）",
                            "default": 768
                        },
                        "height": {
                            "type": "integer",
                            "description": "画像高さ（デフォルト: 1024）",
                            "default": 1024
                        },
                        "sampler": {
                            "type": "string",
                            "description": "サンプラー（デフォルト: dpmpp_2m）",
                            "default": "dpmpp_2m"
                        },
                        "scheduler": {
                            "type": "string",
                            "description": "スケジューラー（デフォルト: karras）",
                            "default": "karras"
                        },
                        "mufufu_mode": {
                            "type": "boolean",
                            "description": "ムフフモード（デフォルト: false）",
                            "default": False
                        },
                        "negative_prompt": {
                            "type": "string",
                            "description": "ネガティブプロンプト"
                        },
                        "seed": {
                            "type": "integer",
                            "description": "シード値（オプション）"
                        }
                    },
                    "required": ["prompt"]
                }
            ),
            Tool(
                name="gallery_get_job_status",
                description="画像生成ジョブのステータスを取得します",
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
                name="gallery_list_images",
                description="生成された画像の一覧を取得します",
                inputSchema={"type": "object", "properties": {}}
            )
        ]
    
    @app.call_tool()
    async def call_tool(name: str, arguments: Any) -> List[TextContent]:
        """ツールを実行"""
        try:
            args = json.loads(arguments) if isinstance(arguments, str) else arguments
            
            if name == "gallery_api_health":
                result = call_api("/health")
            elif name == "gallery_generate_image":
                result = call_api("/api/generate", "POST", args)
            elif name == "gallery_get_job_status":
                job_id = args.get("job_id")
                result = call_api(f"/api/job/{job_id}")
            elif name == "gallery_list_images":
                result = call_api("/api/images")
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
