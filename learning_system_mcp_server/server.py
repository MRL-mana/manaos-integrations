"""
Learning System MCPサーバー (stdioラッパー)
==========================================
Flask HTTP API (port 5126) への MCP stdio ブリッジ。
VS Code / Cursor のチャットから学習パターン記録・分析が可能。

ツール一覧:
  - learning_record      : 使用パターン記録
  - learning_analyze     : パターン分析
  - learning_preferences : 学習された好み取得
  - learning_optimizations: 最適化提案取得
  - learning_status      : ステータス取得
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
API_BASE = os.getenv("LEARNING_SYSTEM_API_URL", "http://127.0.0.1:5126")
HEALTH_PORT = int(os.getenv("LEARNING_MCP_HEALTH_PORT", "5114"))
TIMEOUT = 10


def _post(path: str, body: dict) -> dict:
    if requests is None:
        return {"error": "requests library not installed"}
    try:
        r = requests.post(f"{API_BASE}{path}", json=body, timeout=TIMEOUT)
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def _get(path: str) -> dict:
    if requests is None:
        return {"error": "requests library not installed"}
    try:
        r = requests.get(f"{API_BASE}{path}", timeout=TIMEOUT)
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
            self.wfile.write(json.dumps({"status": "healthy", "service": "learning-mcp"}).encode())
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
    server = Server("learning-system")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="learning_record",
                description="使用パターンを記録。ユーザーの行動・選択・結果を学習システムに保存。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "description": "実行されたアクション"},
                        "context": {"type": "object", "description": "コンテキスト情報", "default": {}},
                        "result": {"type": "object", "description": "結果情報", "default": {}},
                    },
                    "required": ["action"],
                },
            ),
            Tool(
                name="learning_analyze",
                description="記録されたパターンを分析。使用傾向・頻度・改善点を表示。",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="learning_preferences",
                description="学習された好み・プリファレンスを取得。",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="learning_optimizations",
                description="学習データに基づく最適化提案を取得。",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="learning_apply_preferences",
                description="学習された好みをアクションに適用して最適化パラメータを取得。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "description": "適用対象のアクション"},
                        "params": {"type": "object", "description": "パラメータ", "default": {}},
                    },
                    "required": ["action"],
                },
            ),
            Tool(
                name="learning_status",
                description="学習システムのステータスを取得。",
                inputSchema={"type": "object", "properties": {}},
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        try:
            if name == "learning_record":
                result = _post("/api/record", {
                    "action": arguments["action"],
                    "context": arguments.get("context", {}),
                    "result": arguments.get("result", {}),
                })
            elif name == "learning_analyze":
                result = _get("/api/analyze")
            elif name == "learning_preferences":
                result = _get("/api/preferences")
            elif name == "learning_optimizations":
                result = _get("/api/optimizations")
            elif name == "learning_apply_preferences":
                result = _post("/api/apply-preferences", {
                    "action": arguments["action"],
                    "params": arguments.get("params", {}),
                })
            elif name == "learning_status":
                result = _get("/api/status")
            else:
                result = {"error": f"不明なツール: {name}"}

            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]
        except Exception as e:
            return [TextContent(type="text", text=json.dumps({"error": str(e)}, ensure_ascii=False))]


async def main():
    if not MCP_AVAILABLE:
        print("ERROR: MCP SDK not installed. Run: pip install mcp", file=sys.stderr)
        sys.exit(1)

    threading.Thread(target=_start_health_server, daemon=True).start()

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
