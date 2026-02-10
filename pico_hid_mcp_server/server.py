"""
Pico HID MCPサーバー (stdioラッパー)
======================================
Raspberry Pi Pico (USB HID) または PC (pynput) 経由で
マウス・キーボードを操作する MCP stdio サーバー。

Pico 接続時 → USB HID でハードウェアレベル入力
Pico 未接続 → pynput でソフトウェア入力（フォールバック）

ツール一覧:
  - hid_mouse_move       : マウスを相対移動
  - hid_mouse_move_abs   : マウスを絶対座標に移動
  - hid_mouse_click      : マウスクリック
  - hid_mouse_click_at   : 指定座標をクリック
  - hid_mouse_scroll     : マウスホイールスクロール
  - hid_mouse_position   : マウス座標取得
  - hid_key_press        : キーを1回押す
  - hid_key_combo        : キーコンボ（Ctrl+C等）
  - hid_type_text        : テキスト入力
  - hid_status           : 接続状態・バックエンド確認
  - hid_screen_size      : 画面サイズ取得
"""

import os
import sys
import json
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    print("WARNING: mcp package not found. Install with: pip install mcp", file=sys.stderr)

try:
    from pico_hid.pc.pico_hid_client import (
        get_client, use_pc_backend, find_pico_port,
        _has_pynput, _has_serial, screen_size,
        PCHIDClient, PicoHIDClient,
    )
    HID_AVAILABLE = True
except ImportError as e:
    HID_AVAILABLE = False
    print(f"WARNING: pico_hid_client import failed: {e}", file=sys.stderr)

# ── 設定 ─────────────────────────────────────────
HEALTH_PORT = int(os.getenv("PICO_HID_MCP_HEALTH_PORT", "5116"))


def _get_client():
    """クライアントを取得（毎回取得・使い捨て）"""
    return get_client()


def _backend_info():
    """現在のバックエンド情報"""
    pico_port = find_pico_port()
    return {
        "pynput_available": _has_pynput,
        "pyserial_available": _has_serial,
        "pico_port": pico_port,
        "active_backend": "pico" if (not use_pc_backend() and pico_port) else "pc_pynput",
        "screen_size": list(screen_size()),
    }


# ── ヘルスチェック HTTP ─────────────────────────────
class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            info = {"status": "healthy", "service": "pico-hid-mcp"}
            if HID_AVAILABLE:
                info.update(_backend_info())
            self.wfile.write(json.dumps(info).encode())
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
    server = Server("pico-hid")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="hid_mouse_move",
                description="マウスを相対移動（dx, dy ピクセル）。Picoまたはpynputで動作。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "dx": {"type": "integer", "description": "X方向の移動量（正=右, 負=左）"},
                        "dy": {"type": "integer", "description": "Y方向の移動量（正=下, 負=上）"},
                    },
                    "required": ["dx", "dy"],
                },
            ),
            Tool(
                name="hid_mouse_move_abs",
                description="マウスを画面の絶対座標(x, y)に移動。PC(pynput)バックエンドのみ対応。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "x": {"type": "integer", "description": "X座標"},
                        "y": {"type": "integer", "description": "Y座標"},
                    },
                    "required": ["x", "y"],
                },
            ),
            Tool(
                name="hid_mouse_click",
                description="マウスをクリック（left/right/middle）",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "button": {"type": "string", "description": "ボタン: left, right, middle", "default": "left"},
                    },
                },
            ),
            Tool(
                name="hid_mouse_click_at",
                description="指定座標(x, y)に移動してクリック。PC(pynput)バックエンドのみ対応。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "x": {"type": "integer", "description": "X座標"},
                        "y": {"type": "integer", "description": "Y座標"},
                        "button": {"type": "string", "description": "ボタン: left, right, middle", "default": "left"},
                    },
                    "required": ["x", "y"],
                },
            ),
            Tool(
                name="hid_mouse_scroll",
                description="マウスホイールスクロール（正=上、負=下）",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "amount": {"type": "integer", "description": "スクロール量（正=上, 負=下）"},
                    },
                    "required": ["amount"],
                },
            ),
            Tool(
                name="hid_mouse_position",
                description="マウスの現在のスクリーン座標(x, y)を取得。PC(pynput)バックエンドのみ。",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="hid_key_press",
                description="キーを1回押して離す。例: 'enter', 'tab', 'a', 'F5'",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "key": {"type": "string", "description": "キー名（enter, tab, space, escape, backspace, delete, up, down, left, right, a-z, 0-9, F1-F12等）"},
                    },
                    "required": ["key"],
                },
            ),
            Tool(
                name="hid_key_combo",
                description="キーコンボを実行。例: ['ctrl', 'c']でCtrl+C, ['alt', 'tab']でAlt+Tab",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "keys": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "同時押しするキーのリスト。例: ['ctrl', 'shift', 's']"
                        },
                    },
                    "required": ["keys"],
                },
            ),
            Tool(
                name="hid_type_text",
                description="テキストを1文字ずつタイプ入力。USキーボードレイアウト。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "入力するテキスト（ASCII/英数字）"},
                    },
                    "required": ["text"],
                },
            ),
            Tool(
                name="hid_status",
                description="HIDバックエンドの状態を確認（Pico接続/pynput/画面サイズ）",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="hid_screen_size",
                description="画面の解像度(width, height)を取得",
                inputSchema={"type": "object", "properties": {}},
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        if not HID_AVAILABLE:
            return [TextContent(type="text", text=json.dumps(
                {"error": "pico_hid_client が利用できません"}, ensure_ascii=False))]

        try:
            result = {}

            if name == "hid_status":
                result = _backend_info()

            elif name == "hid_screen_size":
                w, h = screen_size()
                result = {"width": w, "height": h}

            elif name == "hid_mouse_position":
                client = _get_client()
                try:
                    x, y = client.mouse_position()
                    result = {"x": x, "y": y}
                finally:
                    client.close()

            elif name == "hid_mouse_move":
                client = _get_client()
                try:
                    ok = client.mouse_move(arguments["dx"], arguments["dy"])
                    result = {"success": ok, "dx": arguments["dx"], "dy": arguments["dy"]}
                finally:
                    client.close()

            elif name == "hid_mouse_move_abs":
                client = _get_client()
                try:
                    ok = client.mouse_move_absolute(arguments["x"], arguments["y"])
                    result = {"success": ok, "x": arguments["x"], "y": arguments["y"]}
                finally:
                    client.close()

            elif name == "hid_mouse_click":
                client = _get_client()
                try:
                    btn = arguments.get("button", "left")
                    ok = client.mouse_click(btn)
                    result = {"success": ok, "button": btn}
                finally:
                    client.close()

            elif name == "hid_mouse_click_at":
                client = _get_client()
                try:
                    btn = arguments.get("button", "left")
                    ok = client.mouse_click_at(arguments["x"], arguments["y"], btn)
                    result = {"success": ok, "x": arguments["x"], "y": arguments["y"], "button": btn}
                finally:
                    client.close()

            elif name == "hid_mouse_scroll":
                client = _get_client()
                try:
                    ok = client.scroll(arguments["amount"])
                    result = {"success": ok, "amount": arguments["amount"]}
                finally:
                    client.close()

            elif name == "hid_key_press":
                client = _get_client()
                try:
                    ok = client.key_press(arguments["key"])
                    result = {"success": ok, "key": arguments["key"]}
                finally:
                    client.close()

            elif name == "hid_key_combo":
                client = _get_client()
                try:
                    ok = client.key_combo(arguments["keys"])
                    result = {"success": ok, "keys": arguments["keys"]}
                finally:
                    client.close()

            elif name == "hid_type_text":
                client = _get_client()
                try:
                    ok = client.type_text(arguments["text"])
                    result = {"success": ok, "length": len(arguments["text"])}
                finally:
                    client.close()

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
