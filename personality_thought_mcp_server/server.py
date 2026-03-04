#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧠 personality_thought_mcp_server
PersonalityThoughtSystem の MCP stdio ブリッジ (port 5126, health:5147)

ツール一覧:
  - thought_get_mood            : 現在の気分状態を取得
  - thought_detect_mood         : テキストからムードを推定・更新
  - thought_set_mood            : ムードを手動設定
  - thought_get_values          : 価値観スコア一覧を取得
  - thought_reinforce_value     : 価値観スコアを強化
  - thought_weaken_value        : 価値観スコアを弱化
  - thought_check_contradiction : 応答テキストの矛盾を検出
  - thought_log                 : 思想ログを記録
  - thought_get_log             : 直近の思想ログを取得
  - thought_record_evolution    : 人格進化を記録
  - thought_get_evolution       : 人格進化タイムラインを取得
  - thought_get_prompt_prefix   : ムード対応プロンプト前置きを取得
  - thought_dashboard           : 全ステータスダッシュボード
"""

import os
import sys
import json
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

import requests

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
    _MCP_AVAILABLE = True
except ImportError:
    _MCP_AVAILABLE = False

# ----------------------------------------------------------------
# API 設定
# ----------------------------------------------------------------
API_URL = os.getenv("PERSONALITY_THOUGHT_API_URL", "http://127.0.0.1:5126")
HEALTH_PORT = int(os.getenv("PERSONALITY_THOUGHT_MCP_HEALTH_PORT", "5147"))
TIMEOUT = 10


def _get(path: str) -> dict:
    resp = requests.get(f"{API_URL}{path}", timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def _post(path: str, payload: dict) -> dict:
    resp = requests.post(f"{API_URL}{path}", json=payload, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


# ----------------------------------------------------------------
# ヘルスチェック HTTP サーバー（サイドカー）
# ----------------------------------------------------------------

class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            body = json.dumps({"status": "healthy", "service": "personality-thought-mcp"}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args):
        pass


def _start_health_server():
    try:
        httpd = HTTPServer(("127.0.0.1", HEALTH_PORT), _HealthHandler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
    except Exception as e:
        print(f"[thought-mcp] ヘルスサーバー起動失敗 port={HEALTH_PORT}: {e}", file=sys.stderr)


# ----------------------------------------------------------------
# MCPツール定義
# ----------------------------------------------------------------

TOOL_DEFS = [
    Tool(name="thought_get_mood",
         description="現在の気分(ムード)状態を取得する",
         inputSchema={"type": "object", "properties": {}}),

    Tool(name="thought_detect_mood",
         description="テキストからムードを推定して更新する",
         inputSchema={"type": "object", "properties": {
             "text": {"type": "string", "description": "ムード推定用テキスト"}
         }, "required": ["text"]}),

    Tool(name="thought_set_mood",
         description="ムードを手動設定する (energetic/calm/curious/focused/playful/tired)",
         inputSchema={"type": "object", "properties": {
             "mood": {"type": "string", "description": "設定するムード"}
         }, "required": ["mood"]}),

    Tool(name="thought_get_values",
         description="全価値観スコア (honesty/helpfulness/curiosity/empathy/efficiency/creativity) を取得",
         inputSchema={"type": "object", "properties": {}}),

    Tool(name="thought_reinforce_value",
         description="価値観スコアを強化 (良い行動を記録)",
         inputSchema={"type": "object", "properties": {
             "value":   {"type": "string", "description": "価値観名"},
             "delta":   {"type": "number", "description": "強化量 (default: 0.02)"},
             "example": {"type": "string", "description": "具体例テキスト"}
         }, "required": ["value"]}),

    Tool(name="thought_weaken_value",
         description="価値観スコアを弱化 (矛盾する行動を記録)",
         inputSchema={"type": "object", "properties": {
             "value":   {"type": "string", "description": "価値観名"},
             "delta":   {"type": "number", "description": "弱化量 (default: 0.03)"},
             "example": {"type": "string", "description": "具体例テキスト"}
         }, "required": ["value"]}),

    Tool(name="thought_check_contradiction",
         description="応答テキスト中の価値観矛盾を検出する",
         inputSchema={"type": "object", "properties": {
             "text": {"type": "string", "description": "チェックするテキスト"}
         }, "required": ["text"]}),

    Tool(name="thought_log",
         description="思想ログ (内省エントリー) を記録する",
         inputSchema={"type": "object", "properties": {
             "user_input":  {"type": "string", "description": "ユーザー入力テキスト"},
             "context":     {"type": "string", "description": "コンテキスト (chat/report/planning)"},
             "reflection":  {"type": "string", "description": "内省コメント (省略時は自動生成)"}
         }, "required": ["user_input"]}),

    Tool(name="thought_get_log",
         description="直近の思想ログを取得する",
         inputSchema={"type": "object", "properties": {
             "n": {"type": "integer", "description": "取得件数 (default: 10)"}
         }}),

    Tool(name="thought_record_evolution",
         description="人格進化 (学習・成長) を記録する",
         inputSchema={"type": "object", "properties": {
             "trigger":      {"type": "string", "description": "進化のトリガーとなった出来事"},
             "description":  {"type": "string", "description": "変化の説明"},
             "value_deltas": {"type": "object", "description": "各価値観の変化量 (例: {honesty: 0.05})"}
         }, "required": ["trigger", "description"]}),

    Tool(name="thought_get_evolution",
         description="人格進化タイムラインを取得する",
         inputSchema={"type": "object", "properties": {}}),

    Tool(name="thought_get_prompt_prefix",
         description="ムードと直近思考に基づくプロンプト前置き文字列を取得",
         inputSchema={"type": "object", "properties": {}}),

    Tool(name="thought_dashboard",
         description="人格思想システム全体のダッシュボードを取得",
         inputSchema={"type": "object", "properties": {}}),
]


# ----------------------------------------------------------------
# ハンドラー
# ----------------------------------------------------------------

async def handle_tool(name: str, args: dict) -> str:
    try:
        if name == "thought_get_mood":
            return json.dumps(_get("/api/thought/mood"), ensure_ascii=False)

        if name == "thought_detect_mood":
            return json.dumps(_post("/api/thought/mood/detect", {"text": args["text"]}), ensure_ascii=False)

        if name == "thought_set_mood":
            return json.dumps(_post("/api/thought/mood", {"mood": args["mood"]}), ensure_ascii=False)

        if name == "thought_get_values":
            return json.dumps(_get("/api/thought/values"), ensure_ascii=False)

        if name == "thought_reinforce_value":
            return json.dumps(_post("/api/thought/values/reinforce", {
                "value":   args["value"],
                "delta":   args.get("delta", 0.02),
                "example": args.get("example", "")
            }), ensure_ascii=False)

        if name == "thought_weaken_value":
            return json.dumps(_post("/api/thought/values/weaken", {
                "value":   args["value"],
                "delta":   args.get("delta", 0.03),
                "example": args.get("example", "")
            }), ensure_ascii=False)

        if name == "thought_check_contradiction":
            return json.dumps(_post("/api/thought/contradict", {"text": args["text"]}), ensure_ascii=False)

        if name == "thought_log":
            return json.dumps(_post("/api/thought/log", {
                "user_input":  args.get("user_input", ""),
                "context":     args.get("context", "chat"),
                "reflection":  args.get("reflection", "")
            }), ensure_ascii=False)

        if name == "thought_get_log":
            n = int(args.get("n", 10))
            return json.dumps(_get(f"/api/thought/log?n={n}"), ensure_ascii=False)

        if name == "thought_record_evolution":
            return json.dumps(_post("/api/thought/evolution", {
                "trigger":      args["trigger"],
                "description":  args["description"],
                "value_deltas": args.get("value_deltas", {})
            }), ensure_ascii=False)

        if name == "thought_get_evolution":
            return json.dumps(_get("/api/thought/evolution"), ensure_ascii=False)

        if name == "thought_get_prompt_prefix":
            return json.dumps(_get("/api/thought/prompt_prefix"), ensure_ascii=False)

        if name == "thought_dashboard":
            return json.dumps(_get("/api/thought/dashboard"), ensure_ascii=False)

        return json.dumps({"error": f"不明なツール: {name}"}, ensure_ascii=False)

    except requests.exceptions.ConnectionError:
        return json.dumps({"error": f"PersonalityThoughtSystem API ({API_URL}) に接続できません"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


# ----------------------------------------------------------------
# エントリーポイント
# ----------------------------------------------------------------

async def main():
    if not _MCP_AVAILABLE:
        print("[thought-mcp] mcp package が未インストールです", file=sys.stderr)
        sys.exit(1)

    _start_health_server()
    server = Server("personality-thought-system")

    @server.list_tools()
    async def list_tools():
        return TOOL_DEFS

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        result = await handle_tool(name, arguments)
        return [TextContent(type="text", text=result)]

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
