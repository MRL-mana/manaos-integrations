"""
MRL Memory MCPサーバー (stdioラッパー)
======================================
Flask HTTP API (port 5105) への MCP stdio ブリッジ。
VS Code / Cursor のチャットからメモリの検索・登録が可能。

ツール一覧:
  - memory_search : メモリを検索
  - memory_store  : テキストをメモリに保存
  - memory_context: LLMコンテキスト用メモリ取得
  - memory_metrics: メトリクス取得
"""

import os
import sys
import json
import asyncio
from pathlib import Path

# 親ディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_common import check_mcp_available, start_health_thread, get_mcp_logger

try:
    from manaos_integrations._paths import MRL_MEMORY_PORT
except Exception:  # pragma: no cover
    try:
        from _paths import MRL_MEMORY_PORT  # type: ignore
    except Exception:  # pragma: no cover
        MRL_MEMORY_PORT = int(os.getenv("MRL_MEMORY_PORT", "5105"))

MCP_AVAILABLE = check_mcp_available()
if MCP_AVAILABLE:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent

try:
    import requests
except ImportError:
    requests = None

logger = get_mcp_logger(__name__)
if not MCP_AVAILABLE:
    logger.warning("MCP SDKがインストールされていません。pip install mcp を実行してください。")

# ── 設定 ─────────────────────────────────────────
API_BASE = os.getenv("MRL_MEMORY_API_URL", f"http://127.0.0.1:{MRL_MEMORY_PORT}")
API_KEY = os.getenv("MRL_MEMORY_API_KEY", os.getenv("API_KEY", ""))
HEALTH_PORT = int(os.getenv("MRL_MEMORY_MCP_HEALTH_PORT", "5113"))
TIMEOUT = 15  # seconds


def _headers():
    h = {"Content-Type": "application/json"}
    if API_KEY:
        h["X-API-Key"] = API_KEY
    return h


def _post(path: str, body: dict) -> dict:
    if requests is None:
        return {"error": "requests library not installed"}
    try:
        r = requests.post(f"{API_BASE}{path}", json=body, headers=_headers(), timeout=TIMEOUT)
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def _get(path: str) -> dict:
    if requests is None:
        return {"error": "requests library not installed"}
    try:
        r = requests.get(f"{API_BASE}{path}", headers=_headers(), timeout=TIMEOUT)
        return r.json()
    except Exception as e:
        return {"error": str(e)}


# ── ヘルスチェック HTTP (mcp_common 使用) ───────────


# ── MCP サーバー ────────────────────────────────────
if MCP_AVAILABLE:
    server = Server("mrl-memory")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="memory_search",
                description="ManaOSメモリを検索。過去の会話・決定事項・技術メモなどを取得。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "検索クエリ"},
                        "limit": {"type": "integer", "description": "取得件数", "default": 10},
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="memory_store",
                description="テキストをManaOSメモリに保存。重要な決定・学び・コンテキストを記憶。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "保存するテキスト"},
                        "source": {"type": "string", "description": "情報源", "default": "mcp-chat"},
                    },
                    "required": ["text"],
                },
            ),
            Tool(
                name="memory_context",
                description="LLMコンテキスト用にメモリを取得。関連する過去の記憶を文脈として返す。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "コンテキストクエリ"},
                        "limit": {"type": "integer", "description": "取得件数", "default": 5},
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="memory_metrics",
                description="MRL Memoryのメトリクス・設定状態を取得。",
                inputSchema={"type": "object", "properties": {}},
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        try:
            if name == "memory_search":
                result = _post("/api/memory/search", {
                    "query": arguments["query"],
                    "limit": arguments.get("limit", 10),
                })
            elif name == "memory_store":
                result = _post("/api/memory/process", {
                    "text": arguments["text"],
                    "source": arguments.get("source", "mcp-chat"),
                    "enable_rehearsal": True,
                })
            elif name == "memory_context":
                result = _post("/api/memory/context", {
                    "query": arguments["query"],
                    "limit": arguments.get("limit", 5),
                })
            elif name == "memory_metrics":
                result = _get("/api/metrics")
            else:
                result = {"error": f"不明なツール: {name}"}

            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]
        except Exception as e:
            return [TextContent(type="text", text=json.dumps({"error": str(e)}, ensure_ascii=False))]


async def main():
    if not MCP_AVAILABLE:
        print("ERROR: MCP SDK not installed. Run: pip install mcp", file=sys.stderr)
        sys.exit(1)

    # ヘルスチェック
    start_health_thread("mrl-memory-mcp", HEALTH_PORT)

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
