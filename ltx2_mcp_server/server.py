"""
LTX-2 専用 MCP サーバー
統合API (9510) の /api/ltx2/* を MCP ツールとして提供
"""

import asyncio
import json
import os
import sys
from pathlib import Path

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

if sys.platform == "win32":
    import io

    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

API_URL = os.getenv("MANAOS_INTEGRATION_API_URL", "http://127.0.0.1:9510").rstrip("/")
server = Server("ltx2")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="ltx2_generate",
            description="LTX-2 で動画を生成します",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_image_path": {"type": "string", "description": "開始画像パス（必須）"},
                    "prompt": {"type": "string", "description": "プロンプト（必須）"},
                    "negative_prompt": {"type": "string"},
                    "video_length_seconds": {"type": "integer", "default": 5},
                    "width": {"type": "integer", "default": 512},
                    "height": {"type": "integer", "default": 512},
                },
                "required": ["start_image_path", "prompt"],
            },
        ),
        Tool(
            name="ltx2_get_queue",
            description="LTX-2 のキュー状態を取得します",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="ltx2_get_history",
            description="LTX-2 の実行履歴を取得します",
            inputSchema={
                "type": "object",
                "properties": {"max_items": {"type": "integer", "default": 10}},
            },
        ),
        Tool(
            name="ltx2_get_status",
            description="指定した prompt_id の状態を取得します",
            inputSchema={
                "type": "object",
                "properties": {"prompt_id": {"type": "string"}},
                "required": ["prompt_id"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name == "ltx2_generate":
            payload = {
                "start_image_path": arguments.get("start_image_path", ""),
                "prompt": arguments.get("prompt", ""),
                "negative_prompt": arguments.get("negative_prompt", ""),
                "video_length_seconds": arguments.get("video_length_seconds", 5),
                "width": arguments.get("width", 512),
                "height": arguments.get("height", 512),
            }
            async with httpx.AsyncClient() as client:
                r = await client.post(f"{API_URL}/api/ltx2/generate", json=payload, timeout=60.0)
            if r.status_code == 200:
                data = r.json()
                txt = f"✅ 動画生成開始\n{json.dumps(data, indent=2, ensure_ascii=False)}"
                return [TextContent(type="text", text=txt)]
            return [TextContent(type="text", text=f"❌ エラー: HTTP {r.status_code}\n{r.text}")]

        elif name == "ltx2_get_queue":
            async with httpx.AsyncClient() as client:
                r = await client.get(f"{API_URL}/api/ltx2/queue", timeout=15.0)
            if r.status_code == 200:
                txt = json.dumps(r.json(), indent=2, ensure_ascii=False)
                return [TextContent(type="text", text=txt)]
            return [TextContent(type="text", text=f"❌ エラー: HTTP {r.status_code}\n{r.text}")]

        elif name == "ltx2_get_history":
            max_items = arguments.get("max_items", 10)
            async with httpx.AsyncClient() as client:
                r = await client.get(
                    f"{API_URL}/api/ltx2/history",
                    params={"max_items": max_items},
                    timeout=15.0,
                )
            if r.status_code == 200:
                txt = json.dumps(r.json(), indent=2, ensure_ascii=False)
                return [TextContent(type="text", text=txt)]
            return [TextContent(type="text", text=f"❌ エラー: HTTP {r.status_code}\n{r.text}")]

        elif name == "ltx2_get_status":
            prompt_id = arguments.get("prompt_id", "")
            if not prompt_id:
                return [TextContent(type="text", text="❌ prompt_id が必須です")]
            async with httpx.AsyncClient() as client:
                r = await client.get(f"{API_URL}/api/ltx2/status/{prompt_id}", timeout=15.0)
            if r.status_code == 200:
                txt = json.dumps(r.json(), indent=2, ensure_ascii=False)
                return [TextContent(type="text", text=txt)]
            return [TextContent(type="text", text=f"❌ エラー: HTTP {r.status_code}\n{r.text}")]

        return [TextContent(type="text", text=f"❌ 未知のツール: {name}")]
    except Exception as e:
        return [TextContent(type="text", text=f"❌ エラー: {e}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
