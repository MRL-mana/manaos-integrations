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
    print(
        "WARNING: mcp package not found. Install with: pip install mcp",
        file=sys.stderr,
    )

try:
    from pico_hid.pc.pico_hid_client import (
        get_client, use_pc_backend, find_pico_port,
        _has_pynput, _has_serial, screen_size,
        take_screenshot,
        type_text_auto,
        clear_input_then_type_auto,
        click_then_type_auto,
    )
    HID_AVAILABLE = True
except ImportError as e:
    HID_AVAILABLE = False
    print(f"WARNING: pico_hid_client import failed: {e}", file=sys.stderr)

try:
    from pico_hid.pc.pico_hid_macros import (
        run_macro as _run_macro,
        list_macros as _list_macros,
    )
    MACROS_AVAILABLE = True
except ImportError:
    MACROS_AVAILABLE = False

# ── 設定 ─────────────────────────────────────────
HEALTH_PORT = int(os.getenv("PICO_HID_MCP_HEALTH_PORT", "5136"))


def _get_client():
    """クライアントを取得（毎回取得・使い捨て）"""
    return get_client()  # type: ignore[possibly-unbound]


def _backend_info():
    """現在のバックエンド情報"""
    pico_port = find_pico_port()  # type: ignore[possibly-unbound]
    return {
        "pynput_available": _has_pynput,  # type: ignore[possibly-unbound]
        "pyserial_available": _has_serial,  # type: ignore[possibly-unbound]
        "pico_port": pico_port,
        "active_backend": (
            "pico" if (not use_pc_backend() and pico_port) else "pc_pynput"  # type: ignore[possibly-unbound]
        ),
        "screen_size": list(screen_size()),  # type: ignore[possibly-unbound]
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

    def log_message(
        self,
        format,
        *args,
    ):  # pylint: disable=redefined-builtin,arguments-differ
        pass


def _start_health_server():
    try:
        srv = HTTPServer(("127.0.0.1", HEALTH_PORT), _HealthHandler)
        srv.serve_forever()
    except OSError:
        pass


# ── MCP サーバー ────────────────────────────────────
if MCP_AVAILABLE:
    server = Server("pico-hid")  # type: ignore[possibly-unbound]

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(  # type: ignore[possibly-unbound]
                name="hid_mouse_move",
                description="マウスを相対移動（dx, dy ピクセル）。Picoまたはpynputで動作。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "dx": {
                            "type": "integer",
                            "description": "X方向の移動量（正=右, 負=左）",
                        },
                        "dy": {
                            "type": "integer",
                            "description": "Y方向の移動量（正=下, 負=上）",
                        },
                    },
                    "required": ["dx", "dy"],
                },
            ),
            Tool(  # type: ignore[possibly-unbound]
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
            Tool(  # type: ignore[possibly-unbound]
                name="hid_mouse_click",
                description="マウスをクリック（left/right/middle）",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "button": {
                            "type": "string",
                            "description": "ボタン: left, right, middle",
                            "default": "left",
                        },
                    },
                },
            ),
            Tool(  # type: ignore[possibly-unbound]
                name="hid_mouse_click_at",
                description="指定座標(x, y)に移動してクリック。PC(pynput)バックエンドのみ対応。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "x": {"type": "integer", "description": "X座標"},
                        "y": {"type": "integer", "description": "Y座標"},
                        "button": {
                            "type": "string",
                            "description": "ボタン: left, right, middle",
                            "default": "left",
                        },
                    },
                    "required": ["x", "y"],
                },
            ),
            Tool(  # type: ignore[possibly-unbound]
                name="hid_mouse_scroll",
                description="マウスホイールスクロール（正=上、負=下）",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "amount": {
                            "type": "integer",
                            "description": "スクロール量（正=上, 負=下）",
                        },
                    },
                    "required": ["amount"],
                },
            ),
            Tool(  # type: ignore[possibly-unbound]
                name="hid_mouse_position",
                description="マウスの現在のスクリーン座標(x, y)を取得。PC(pynput)バックエンドのみ。",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(  # type: ignore[possibly-unbound]
                name="hid_key_press",
                description="キーを1回押して離す。例: 'enter', 'tab', 'a', 'F5'",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "key": {
                            "type": "string",
                            "description": (
                                "キー名（enter, tab, space, escape, backspace, "
                                "delete, up, down, left, right, a-z, 0-9, "
                                "F1-F12等）"
                            ),
                        },
                    },
                    "required": ["key"],
                },
            ),
            Tool(  # type: ignore[possibly-unbound]
                name="hid_key_combo",
                description=(
                    "キーコンボを実行。例: ['ctrl', 'c']でCtrl+C, "
                    "['alt', 'tab']でAlt+Tab"
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "keys": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": (
                                "同時押しするキーのリスト。例: ['ctrl', 'shift', 's']"
                            ),
                        },
                    },
                    "required": ["keys"],
                },
            ),
            Tool(  # type: ignore[possibly-unbound]
                name="hid_type_text",
                description="テキストを1文字ずつタイプ入力。USキーボードレイアウト。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "入力するテキスト（ASCII/英数字）",
                        },
                    },
                    "required": ["text"],
                },
            ),
            Tool(  # type: ignore[possibly-unbound]
                name="hid_status",
                description="HIDバックエンドの状態を確認（Pico接続/pynput/画面サイズ）",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(  # type: ignore[possibly-unbound]
                name="hid_screen_size",
                description="画面の解像度(width, height)を取得",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(  # type: ignore[possibly-unbound]
                name="hid_run_macro",
                description="Pico HID マクロを実行（Win+R→コマンド実行など）。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "macro name",
                        },
                        "args": {
                            "type": "object",
                            "description": "macro arguments (optional)",
                            "additionalProperties": True,
                        },
                        "speed": {
                            "type": "number",
                            "description": "sleep speed multiplier",
                            "default": 1.0,
                        },
                        "dry_run": {
                            "type": "boolean",
                            "description": "if true, do not send input",
                            "default": False,
                        },
                        "confirm_token": {
                            "type": "string",
                            "description": (
                                "required if PICO_HID_MACRO_CONFIRM_TOKEN is "
                                "set"
                            ),
                        },
                    },
                    "required": ["name"],
                },
            ),

            # --- aliases for ManaOS docs/autonomy gates (pico_hid_*) ---
            Tool(  # type: ignore[possibly-unbound]
                name="pico_hid_mouse_move",
                description="(alias) マウスを相対移動（dx, dy ピクセル）。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "dx": {"type": "integer"},
                        "dy": {"type": "integer"},
                    },
                    "required": ["dx", "dy"],
                },
            ),
            Tool(  # type: ignore[possibly-unbound]
                name="pico_hid_mouse_move_absolute",
                description="(alias) マウスを絶対座標(x, y)に移動。PC(pynput)のみ。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "x": {"type": "integer"},
                        "y": {"type": "integer"},
                    },
                    "required": ["x", "y"],
                },
            ),
            Tool(  # type: ignore[possibly-unbound]
                name="pico_hid_mouse_click",
                description="(alias) マウスクリック（left/right/middle）",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "button": {"type": "string", "default": "left"},
                    },
                },
            ),
            Tool(  # type: ignore[possibly-unbound]
                name="pico_hid_mouse_click_at",
                description="(alias) 指定座標(x, y)をクリック。PC(pynput)のみ。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "x": {"type": "integer"},
                        "y": {"type": "integer"},
                        "button": {"type": "string", "default": "left"},
                    },
                    "required": ["x", "y"],
                },
            ),
            Tool(  # type: ignore[possibly-unbound]
                name="pico_hid_scroll",
                description="(alias) ホイールスクロール（delta: 正=上, 負=下）",
                inputSchema={
                    "type": "object",
                    "properties": {"delta": {"type": "integer"}},
                    "required": ["delta"],
                },
            ),
            Tool(  # type: ignore[possibly-unbound]
                name="pico_hid_key_press",
                description="(alias) キーを1回押す",
                inputSchema={
                    "type": "object",
                    "properties": {"key": {"type": "string"}},
                    "required": ["key"],
                },
            ),
            Tool(  # type: ignore[possibly-unbound]
                name="pico_hid_key_combo",
                description="(alias) キーコンボを実行",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "keys": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["keys"],
                },
            ),
            Tool(  # type: ignore[possibly-unbound]
                name="pico_hid_type_text",
                description="(alias) テキスト入力",
                inputSchema={
                    "type": "object",
                    "properties": {"text": {"type": "string"}},
                    "required": ["text"],
                },
            ),
            Tool(  # type: ignore[possibly-unbound]
                name="pico_hid_mouse_position",
                description="(alias) マウス座標取得（PCのみ）",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(  # type: ignore[possibly-unbound]
                name="pico_hid_screen_size",
                description="(alias) 画面サイズ取得",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(  # type: ignore[possibly-unbound]
                name="pico_hid_screenshot",
                description="(alias) スクリーンショットをPNG保存（path省略可）",
                inputSchema={
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                },
            ),
            Tool(  # type: ignore[possibly-unbound]
                name="pico_hid_type_text_auto",
                description="(alias) IME切替→入力→スクショ（確認用）",
                inputSchema={
                    "type": "object",
                    "properties": {"text": {"type": "string"}},
                    "required": ["text"],
                },
            ),
            Tool(  # type: ignore[possibly-unbound]
                name="pico_hid_clear_and_retype_auto",
                description="(alias) Ctrl+A→Delete→IME切替→入力→スクショ",
                inputSchema={
                    "type": "object",
                    "properties": {"text": {"type": "string"}},
                    "required": ["text"],
                },
            ),
            Tool(  # type: ignore[possibly-unbound]
                name="pico_hid_click_then_type_auto",
                description="(alias) (x,y)クリック→IME切替→入力→スクショ（PCのみ）",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "x": {"type": "integer"},
                        "y": {"type": "integer"},
                        "text": {"type": "string"},
                    },
                    "required": ["x", "y", "text"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        if not HID_AVAILABLE:
            return [TextContent(type="text", text=json.dumps(  # type: ignore[possibly-unbound]
                {"error": "pico_hid_client が利用できません"}, ensure_ascii=False))]

        try:
            result = {}

            if name == "hid_status":
                result = _backend_info()

            elif name == "hid_screen_size":
                w, h = screen_size()  # type: ignore[possibly-unbound]
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
                    result = {
                        "success": ok,
                        "dx": arguments["dx"],
                        "dy": arguments["dy"],
                    }
                finally:
                    client.close()

            elif name == "hid_mouse_move_abs":
                client = _get_client()
                try:
                    ok = client.mouse_move_absolute(
                        arguments["x"],
                        arguments["y"],
                    )
                    result = {
                        "success": ok,
                        "x": arguments["x"],
                        "y": arguments["y"],
                    }
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
                    ok = client.mouse_click_at(
                        arguments["x"],
                        arguments["y"],
                        btn,
                    )
                    result = {
                        "success": ok,
                        "x": arguments["x"],
                        "y": arguments["y"],
                        "button": btn,
                    }
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

            elif name == "hid_run_macro":
                if not MACROS_AVAILABLE:
                    result = {
                        "success": False,
                        "error": "macros module not available",
                    }
                else:
                    macro_name = (arguments.get("name") or "").strip()
                    macro_args = arguments.get("args") or {}
                    speed = float(arguments.get("speed") or 1.0)
                    dry_run = bool(arguments.get("dry_run") or False)
                    confirm_token = (
                        (arguments.get("confirm_token") or "").strip() or None
                    )
                    r = _run_macro(  # type: ignore[possibly-unbound]
                        macro_name,
                        args=macro_args,
                        speed=speed,
                        dry_run=dry_run,
                        confirm_token=confirm_token,
                    )
                    result = {
                        "macro": r.name,
                        "success": r.success,
                        "executed_steps": r.executed_steps,
                        "failed_step_index": r.failed_step_index,
                        "error": r.error,
                        "artifacts": getattr(r, "artifacts", {}) or {},
                        "available_macros": (
                            _list_macros() if MACROS_AVAILABLE else []  # type: ignore[possibly-unbound]
                        ),
                    }

            elif name == "pico_hid_screen_size":
                w, h = screen_size()  # type: ignore[possibly-unbound]
                result = {"width": w, "height": h}

            elif name == "pico_hid_screenshot":
                path = arguments.get("path")
                saved = take_screenshot(path if path else None)  # type: ignore[possibly-unbound]
                result = {"success": bool(saved), "path": saved or ""}

            elif name == "pico_hid_mouse_position":
                client = _get_client()
                try:
                    x, y = client.mouse_position()
                    result = {"x": x, "y": y}
                finally:
                    client.close()

            elif name == "pico_hid_mouse_move":
                client = _get_client()
                try:
                    ok = client.mouse_move(arguments["dx"], arguments["dy"])
                    result = {
                        "success": ok,
                        "dx": arguments["dx"],
                        "dy": arguments["dy"],
                    }
                finally:
                    client.close()

            elif name == "pico_hid_mouse_move_absolute":
                client = _get_client()
                try:
                    ok = client.mouse_move_absolute(
                        arguments["x"],
                        arguments["y"],
                    )
                    result = {
                        "success": ok,
                        "x": arguments["x"],
                        "y": arguments["y"],
                    }
                finally:
                    client.close()

            elif name == "pico_hid_mouse_click":
                client = _get_client()
                try:
                    btn = arguments.get("button", "left")
                    ok = client.mouse_click(btn)
                    result = {"success": ok, "button": btn}
                finally:
                    client.close()

            elif name == "pico_hid_mouse_click_at":
                client = _get_client()
                try:
                    btn = arguments.get("button", "left")
                    ok = client.mouse_click_at(
                        arguments["x"],
                        arguments["y"],
                        btn,
                    )
                    result = {
                        "success": ok,
                        "x": arguments["x"],
                        "y": arguments["y"],
                        "button": btn,
                    }
                finally:
                    client.close()

            elif name == "pico_hid_scroll":
                client = _get_client()
                try:
                    ok = client.scroll(arguments["delta"])
                    result = {"success": ok, "delta": arguments["delta"]}
                finally:
                    client.close()

            elif name == "pico_hid_key_press":
                client = _get_client()
                try:
                    ok = client.key_press(arguments["key"])
                    result = {"success": ok, "key": arguments["key"]}
                finally:
                    client.close()

            elif name == "pico_hid_key_combo":
                client = _get_client()
                try:
                    ok = client.key_combo(arguments["keys"])
                    result = {"success": ok, "keys": arguments["keys"]}
                finally:
                    client.close()

            elif name == "pico_hid_type_text":
                client = _get_client()
                try:
                    ok = client.type_text(arguments["text"])
                    result = {
                        "success": ok,
                        "length": len(arguments["text"]),
                    }
                finally:
                    client.close()

            elif name == "pico_hid_type_text_auto":
                ok, screenshot_path = type_text_auto(arguments["text"])  # type: ignore[possibly-unbound]
                result = {
                    "success": bool(ok),
                    "screenshot_path": screenshot_path,
                }

            elif name == "pico_hid_clear_and_retype_auto":
                ok, screenshot_path = clear_input_then_type_auto(  # type: ignore[possibly-unbound]
                    arguments["text"]
                )
                result = {
                    "success": bool(ok),
                    "screenshot_path": screenshot_path,
                }

            elif name == "pico_hid_click_then_type_auto":
                ok, screenshot_path = click_then_type_auto(  # type: ignore[possibly-unbound]
                    arguments["x"],
                    arguments["y"],
                    arguments["text"],
                )
                result = {
                    "success": bool(ok),
                    "screenshot_path": screenshot_path,
                }

            else:
                result = {"error": f"不明なツール: {name}"}

            return [
                TextContent(  # type: ignore[possibly-unbound]
                    type="text",
                    text=json.dumps(result, indent=2, ensure_ascii=False),
                )
            ]
        except Exception as e:  # pylint: disable=broad-except
            return [
                TextContent(  # type: ignore[possibly-unbound]
                    type="text",
                    text=json.dumps({"error": str(e)}, ensure_ascii=False),
                )
            ]


async def main():
    if not MCP_AVAILABLE:
        print(
            "ERROR: MCP SDK not installed. Run: pip install mcp",
            file=sys.stderr,
        )
        sys.exit(1)

    threading.Thread(target=_start_health_server, daemon=True).start()

    async with stdio_server() as (read_stream, write_stream):  # type: ignore[possibly-unbound]
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
