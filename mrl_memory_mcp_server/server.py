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
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    print("WARNING: mcp package not found. Install with: pip install mcp", file=sys.stderr)

try:
    import requests
except ImportError:
    requests = None

# ── 設定 ─────────────────────────────────────────
API_BASE = os.getenv("MRL_MEMORY_API_URL", "http://127.0.0.1:5105")
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


# ── ヘルスチェック HTTP ─────────────────────────────
class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "healthy", "service": "mrl-memory-mcp"}).encode())
        else:
            self.send_error(404)

    def log_message(self, format, *args):
        pass


def _start_health_server():
    try:
        srv = HTTPServer(("127.0.0.1", HEALTH_PORT), _HealthHandler)
        srv.serve_forever()
    except Exception:
        pass


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
    threading.Thread(target=_start_health_server, daemon=True).start()

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
