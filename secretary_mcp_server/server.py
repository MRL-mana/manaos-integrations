"""
Secretary System MCPサーバー (stdioラッパー)
==========================================
Flask HTTP API (port 5125) への MCP stdio ブリッジ。
VS Code / Cursor のチャットからリマインダー管理・日次レポート生成が可能。

ツール一覧:
  - secretary_add_reminder       : リマインダーを追加
  - secretary_list_reminders     : 期限切れリマインダー一覧
  - secretary_complete_reminder  : リマインダーを完了済みにする
  - secretary_daily_report       : 日次レポートを生成
  - secretary_get_reports        : 過去レポート一覧取得
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
    from _paths import SECRETARY_SYSTEM_PORT
except Exception:
    SECRETARY_SYSTEM_PORT = int(os.getenv("SECRETARY_SYSTEM_PORT", "5125"))

# ── 設定 ─────────────────────────────────────────
API_BASE = os.getenv("SECRETARY_API_URL", f"http://127.0.0.1:{SECRETARY_SYSTEM_PORT}")
HEALTH_PORT = int(os.getenv("SECRETARY_MCP_HEALTH_PORT", "5145"))
TIMEOUT = 15


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
            self.wfile.write(json.dumps({"status": "healthy", "service": "secretary-mcp"}).encode())
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
    server = Server("secretary-system")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="secretary_add_reminder",
                description="リマインダーを追加する。タイトル・説明・実行時刻・繰り返しタイプを指定。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "リマインダーのタイトル",
                        },
                        "description": {
                            "type": "string",
                            "description": "詳細説明（任意）",
                        },
                        "scheduled_time": {
                            "type": "string",
                            "description": "実行時刻 ISO8601形式（例: 2026-03-05T09:00:00）",
                        },
                        "reminder_type": {
                            "type": "string",
                            "enum": ["once", "daily", "weekly", "monthly", "custom"],
                            "description": "繰り返しタイプ（デフォルト: once）",
                        },
                    },
                    "required": ["title", "scheduled_time"],
                },
            ),
            Tool(
                name="secretary_list_reminders",
                description="期限切れ（未完了）のリマインダー一覧を返す。",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="secretary_complete_reminder",
                description="指定IDのリマインダーを完了済みマークする。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "reminder_id": {
                            "type": "string",
                            "description": "完了するリマインダーのID",
                        }
                    },
                    "required": ["reminder_id"],
                },
            ),
            Tool(
                name="secretary_daily_report",
                description="今日の日次レポートを生成する（タスク・イベント・メモのサマリー）。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "date": {
                            "type": "string",
                            "description": "対象日付 YYYY-MM-DD（省略時は今日）",
                        }
                    },
                },
            ),
            Tool(
                name="secretary_get_reports",
                description="過去の秘書レポート一覧を返す。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "report_type": {
                            "type": "string",
                            "enum": ["daily", "weekly", "monthly", "custom"],
                            "description": "レポートタイプでフィルタ（任意）",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "取得件数（デフォルト: 10）",
                        },
                    },
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        if name == "secretary_add_reminder":
            result = _post("/api/reminders", arguments)

        elif name == "secretary_list_reminders":
            result = _get("/api/reminders")

        elif name == "secretary_complete_reminder":
            rid = arguments.get("reminder_id", "")
            result = _post(f"/api/reminders/{rid}/complete", {})

        elif name == "secretary_daily_report":
            result = _post("/api/reports/daily", arguments)

        elif name == "secretary_get_reports":
            params = []
            if "report_type" in arguments:
                params.append(f"type={arguments['report_type']}")
            if "limit" in arguments:
                params.append(f"limit={arguments['limit']}")
            qs = "?" + "&".join(params) if params else ""
            result = _get(f"/api/reports{qs}")

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
