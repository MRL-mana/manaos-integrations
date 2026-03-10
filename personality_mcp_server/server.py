"""
Personality System MCPサーバー (stdioラッパー)
=============================================
Flask HTTP API (port 5123) への MCP stdio ブリッジ。
VS Code / Cursor のチャットから人格ペルソナの取得・変更・プロンプト生成が可能。

ツール一覧:
  - personality_get_persona      : 現在のペルソナ取得
  - personality_get_prompt       : ペルソナ用システムプロンプト生成
  - personality_apply_to_prompt  : 任意テキストにペルソナを適用
  - personality_update_persona   : ペルソナ更新
"""

import os
import sys
import json
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

# パスを追加
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
    from _paths import PERSONALITY_SYSTEM_PORT
except Exception:
    PERSONALITY_SYSTEM_PORT = int(os.getenv("PERSONALITY_SYSTEM_PORT", "5123"))

# ── 設定 ─────────────────────────────────────────
API_BASE = os.getenv("PERSONALITY_API_URL", f"http://127.0.0.1:{PERSONALITY_SYSTEM_PORT}")
HEALTH_PORT = int(os.getenv("PERSONALITY_MCP_HEALTH_PORT", "5143"))
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
            self.wfile.write(json.dumps({"status": "healthy", "service": "personality-mcp"}).encode())
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
    server = Server("personality-system")  # type: ignore[possibly-unbound]

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(  # type: ignore[possibly-unbound]
                name="personality_get_persona",
                description="現在のペルソナ（人格プロファイル）を取得。名前・特性・トーン・スタイルを返す。",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(  # type: ignore[possibly-unbound]
                name="personality_get_prompt",
                description="現在のペルソナに基づくシステムプロンプトを生成して返す。LLMへのsystem instructionに使用。",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(  # type: ignore[possibly-unbound]
                name="personality_apply_to_prompt",
                description="任意のプロンプトテキストにペルソナのスタイルを適用して返す。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "ペルソナを適用する元のプロンプトテキスト",
                        }
                    },
                    "required": ["prompt"],
                },
            ),
            Tool(  # type: ignore[possibly-unbound]
                name="personality_update_persona",
                description="ペルソナを更新する。name, traits, tone, response_style を指定可能。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "ペルソナ名（例: pure_gal, professional）",
                        },
                        "traits": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "人格特性リスト（例: [\"pure\",\"friendly\"]）",
                        },
                        "tone": {
                            "type": "string",
                            "description": "話し方トーン（例: casual, formal）",
                        },
                        "response_style": {
                            "type": "string",
                            "description": "応答スタイル（例: detailed, concise）",
                        },
                    },
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        if name == "personality_get_persona":
            result = _get("/api/persona")

        elif name == "personality_get_prompt":
            result = _get("/api/persona/prompt")

        elif name == "personality_apply_to_prompt":
            prompt = arguments.get("prompt", "")
            result = _post("/api/persona/apply", {"prompt": prompt})

        elif name == "personality_update_persona":
            result = _post("/api/persona", arguments)

        else:
            result = {"error": f"Unknown tool: {name}"}

        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]  # type: ignore[possibly-unbound]


async def main():
    if not MCP_AVAILABLE:
        print("ERROR: mcp package required. Run: pip install mcp", file=sys.stderr)
        sys.exit(1)

    # ヘルスチェックサーバーをバックグラウンドで起動
    health_thread = threading.Thread(target=_start_health_server, daemon=True)
    health_thread.start()

    async with stdio_server() as (read_stream, write_stream):  # type: ignore[possibly-unbound]
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
