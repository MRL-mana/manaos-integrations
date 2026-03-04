"""
Autonomy System MCPサーバー (stdioラッパー)
==========================================
Flask HTTP API (port 5124) への MCP stdio ブリッジ。
VS Code / Cursor のチャットから自律実行レベル管理・タスク追加・ツール実行可否チェックが可能。

ツール一覧:
  - autonomy_status        : 自律システムの状態取得
  - autonomy_get_level     : 現在の自律レベル取得
  - autonomy_set_level     : 自律レベル変更 (0-4)
  - autonomy_check_tool    : ツール実行可否をチェック
  - autonomy_add_task      : 自律タスクを追加
  - autonomy_list_tasks    : タスク一覧取得
  - autonomy_dashboard     : ダッシュボード情報取得
"""

import os
import sys
import json
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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

try:
    from _paths import AUTONOMY_SYSTEM_PORT
except Exception:
    AUTONOMY_SYSTEM_PORT = int(os.getenv("AUTONOMY_SYSTEM_PORT", "5124"))

# ── 設定 ─────────────────────────────────────────
API_BASE = os.getenv("AUTONOMY_API_URL", f"http://127.0.0.1:{AUTONOMY_SYSTEM_PORT}")
HEALTH_PORT = int(os.getenv("AUTONOMY_MCP_HEALTH_PORT", "5134"))
TIMEOUT = 10


def _get(path: str) -> dict:
    if requests is None:
        return {"error": "requests library not installed"}
    try:
        r = requests.get(f"{API_BASE}{path}", timeout=TIMEOUT)
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def _post(path: str, body: dict) -> dict:
    if requests is None:
        return {"error": "requests library not installed"}
    try:
        r = requests.post(f"{API_BASE}{path}", json=body, timeout=TIMEOUT)
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
            self.wfile.write(json.dumps({"status": "healthy", "service": "autonomy-mcp"}).encode())
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
    server = Server("autonomy-system")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="autonomy_status",
                description="自律システムの現在の状態（レベル・実行中タスク数・予算消費など）を返す。",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="autonomy_get_level",
                description="現在の自律実行レベルを取得。0=完全手動 〜 4=完全自律。",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="autonomy_set_level",
                description="自律実行レベルを変更する。level: 0（完全手動）〜 4（完全自律）。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "level": {
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 4,
                            "description": "自律レベル（0-4）",
                        },
                        "reason": {
                            "type": "string",
                            "description": "変更理由（任意）",
                        },
                    },
                    "required": ["level"],
                },
            ),
            Tool(
                name="autonomy_check_tool",
                description="指定ツールが現在の自律レベルで実行可能か確認する。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "tool_name": {
                            "type": "string",
                            "description": "チェックするツール名（例: file_write, web_search）",
                        },
                        "context": {
                            "type": "object",
                            "description": "実行コンテキスト（任意）",
                        },
                    },
                    "required": ["tool_name"],
                },
            ),
            Tool(
                name="autonomy_add_task",
                description="自律タスクをキューに追加する。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "task_type": {
                            "type": "string",
                            "description": "タスクタイプ（例: health_check, file_organize）",
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["low", "medium", "high", "critical"],
                            "description": "優先度",
                        },
                        "action": {
                            "type": "object",
                            "description": "実行アクション定義",
                        },
                        "condition": {
                            "type": "object",
                            "description": "実行条件（例: {\"type\": \"always\"}）",
                        },
                    },
                    "required": ["task_type", "action"],
                },
            ),
            Tool(
                name="autonomy_list_tasks",
                description="自律タスク一覧を取得する。",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="autonomy_dashboard",
                description="自律システムの全体ダッシュボード情報（タスク・履歴・統計）を返す。",
                inputSchema={"type": "object", "properties": {}},
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        if name == "autonomy_status":
            result = _get("/api/status")

        elif name == "autonomy_get_level":
            result = _get("/api/level")

        elif name == "autonomy_set_level":
            result = _post("/api/level", arguments)

        elif name == "autonomy_check_tool":
            result = _post("/api/check-tool", arguments)

        elif name == "autonomy_add_task":
            result = _post("/api/tasks", arguments)

        elif name == "autonomy_list_tasks":
            result = _get("/api/tasks")

        elif name == "autonomy_dashboard":
            result = _get("/api/dashboard")

        else:
            result = {"error": f"Unknown tool: {name}"}

        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


async def main():
    if not MCP_AVAILABLE:
        print("ERROR: mcp package required. Run: pip install mcp", file=sys.stderr)
        sys.exit(1)

    health_thread = threading.Thread(target=_start_health_server, daemon=True)
    health_thread.start()

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
