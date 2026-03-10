"""
Windows Automation MCPサーバー (stdioラッパー)
================================================
WindowsAutomationToolkit を直接呼び出す MCP stdio サーバー。
VS Code / Cursor のチャットから母艦PCの操作が可能。

ツール一覧:
  - win_system_info      : システム情報取得
  - win_resource_usage   : CPU/RAM/GPU/Disk使用率
  - win_resource_alerts  : リソースアラート確認
  - win_screenshot       : スクリーンショット
  - win_monitor_info     : モニター情報
  - win_top_processes    : プロセスTOP表示
  - win_kill_process     : プロセス終了
  - win_start_app        : アプリ起動
  - win_list_windows     : ウィンドウ一覧
  - win_focus_window     : ウィンドウを前面に
  - win_powershell       : PowerShellコマンド実行
  - win_network_info     : ネットワーク情報
  - win_disk_info        : ディスク情報
  - win_list_apps        : インストール済みアプリ
  - win_install_app      : アプリインストール(winget)
  - win_uninstall_app    : アプリアンインストール(winget)
"""

import os
import sys
import json
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# toolkitのimportパスを確保
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
sys.path.insert(0, os.path.join(_REPO_ROOT, "scripts", "misc"))

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    print("WARNING: mcp package not found. Install with: pip install mcp", file=sys.stderr)

try:
    from windows_automation_toolkit import WindowsAutomationToolkit
    TOOLKIT_AVAILABLE = True
except ImportError:
    TOOLKIT_AVAILABLE = False
    print("WARNING: windows_automation_toolkit not found", file=sys.stderr)

# ── 設定 ─────────────────────────────────────────
HEALTH_PORT = int(os.getenv("WIN_AUTOMATION_MCP_HEALTH_PORT", "5115"))
toolkit = WindowsAutomationToolkit() if TOOLKIT_AVAILABLE else None  # type: ignore[possibly-unbound]


# ── ヘルスチェック HTTP ─────────────────────────────
class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "healthy",
                "service": "windows-automation-mcp",
                "toolkit_available": TOOLKIT_AVAILABLE,
            }).encode())
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
    server = Server("windows-automation")  # type: ignore[possibly-unbound]

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(  # type: ignore[possibly-unbound]
                name="win_system_info",
                description="母艦PCのシステム情報を取得（OS、CPU、RAM、GPU、稼働時間）",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(  # type: ignore[possibly-unbound]
                name="win_resource_usage",
                description="CPU/RAM/Disk/GPU/ネットワークの現在の使用率を取得",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(  # type: ignore[possibly-unbound]
                name="win_resource_alerts",
                description="リソース使用量が閾値を超えていないか確認",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(  # type: ignore[possibly-unbound]
                name="win_screenshot",
                description="母艦PCのスクリーンショットを撮影して保存",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "filename": {"type": "string", "description": "保存ファイル名（省略で自動生成）"},
                        "monitor": {"type": "integer", "description": "モニター番号（0=全画面, 1=メイン, 2=2番目）", "default": 0},
                    },
                },
            ),
            Tool(  # type: ignore[possibly-unbound]
                name="win_monitor_info",
                description="接続されているモニターの情報を取得",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(  # type: ignore[possibly-unbound]
                name="win_top_processes",
                description="CPU/メモリ使用量トップのプロセスを表示",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "sort_by": {"type": "string", "description": "'cpu' または 'memory'", "default": "cpu"},
                        "limit": {"type": "integer", "description": "取得件数", "default": 10},
                    },
                },
            ),
            Tool(  # type: ignore[possibly-unbound]
                name="win_kill_process",
                description="PIDを指定してプロセスを終了",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "pid": {"type": "integer", "description": "終了するプロセスのPID"},
                    },
                    "required": ["pid"],
                },
            ),
            Tool(  # type: ignore[possibly-unbound]
                name="win_start_app",
                description="アプリケーションを起動",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "実行ファイル名またはパス"},
                        "args": {"type": "array", "items": {"type": "string"}, "description": "引数リスト"},
                    },
                    "required": ["command"],
                },
            ),
            Tool(  # type: ignore[possibly-unbound]
                name="win_list_windows",
                description="現在表示されているウィンドウの一覧を取得",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(  # type: ignore[possibly-unbound]
                name="win_focus_window",
                description="指定したウィンドウを前面に表示",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "hwnd": {"type": "integer", "description": "ウィンドウハンドル"},
                        "title_contains": {"type": "string", "description": "タイトルに含まれる文字列（部分一致検索）"},
                    },
                },
            ),
            Tool(  # type: ignore[possibly-unbound]
                name="win_powershell",
                description="PowerShellコマンドを実行して結果を返す",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "実行するPowerShellコマンド"},
                        "timeout": {"type": "integer", "description": "タイムアウト秒数", "default": 30},
                    },
                    "required": ["command"],
                },
            ),
            Tool(  # type: ignore[possibly-unbound]
                name="win_network_info",
                description="ネットワーク接続情報（IP、Tailscale状態）を取得",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(  # type: ignore[possibly-unbound]
                name="win_disk_info",
                description="全ドライブのディスク使用量を取得",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(  # type: ignore[possibly-unbound]
                name="win_list_apps",
                description="wingetでインストール済みアプリを一覧表示",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name_filter": {"type": "string", "description": "名前フィルタ（部分一致）"},
                    },
                },
            ),
            Tool(  # type: ignore[possibly-unbound]
                name="win_install_app",
                description="wingetでアプリをインストール",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "app_id": {"type": "string", "description": "wingetアプリID（例: Google.Chrome）"},
                    },
                    "required": ["app_id"],
                },
            ),
            Tool(  # type: ignore[possibly-unbound]
                name="win_uninstall_app",
                description="wingetでアプリをアンインストール",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "app_id": {"type": "string", "description": "wingetアプリID"},
                    },
                    "required": ["app_id"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        if not toolkit:
            return [TextContent(type="text", text=json.dumps(  # type: ignore[possibly-unbound]
                {"error": "WindowsAutomationToolkit が利用できません"}, ensure_ascii=False))]

        try:
            result: Any = None  # type: ignore[name-defined]

            if name == "win_system_info":
                result = toolkit.get_system_info()
            elif name == "win_resource_usage":
                result = toolkit.get_resource_usage()
            elif name == "win_resource_alerts":
                result = toolkit.check_resource_alerts()
            elif name == "win_screenshot":
                result = toolkit.take_screenshot(
                    filename=arguments.get("filename"),
                    monitor=arguments.get("monitor", 0),
                )
            elif name == "win_monitor_info":
                result = toolkit.get_monitor_info()
            elif name == "win_top_processes":
                result = toolkit.get_top_processes(
                    sort_by=arguments.get("sort_by", "cpu"),
                    limit=arguments.get("limit", 10),
                )
            elif name == "win_kill_process":
                result = toolkit.kill_process(arguments["pid"])
            elif name == "win_start_app":
                result = toolkit.start_application(
                    arguments["command"],
                    arguments.get("args"),
                )
            elif name == "win_list_windows":
                result = toolkit.list_windows()
            elif name == "win_focus_window":
                result = toolkit.focus_window(
                    hwnd=arguments.get("hwnd"),
                    title_contains=arguments.get("title_contains"),
                )
            elif name == "win_powershell":
                result = toolkit.execute_powershell(
                    arguments["command"],
                    timeout=arguments.get("timeout", 30),
                )
            elif name == "win_network_info":
                result = toolkit.get_network_info()
            elif name == "win_disk_info":
                result = toolkit.get_disk_info()
            elif name == "win_list_apps":
                result = toolkit.list_installed_apps(
                    name_filter=arguments.get("name_filter"),
                )
            elif name == "win_install_app":
                result = toolkit.install_app(arguments["app_id"])
            elif name == "win_uninstall_app":
                result = toolkit.uninstall_app(arguments["app_id"])
            else:
                result = {"error": f"不明なツール: {name}"}

            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]  # type: ignore[possibly-unbound]
        except Exception as e:
            return [TextContent(type="text", text=json.dumps({"error": str(e)}, ensure_ascii=False))]  # type: ignore[possibly-unbound]


async def main():
    if not MCP_AVAILABLE:
        print("ERROR: MCP SDK not installed. Run: pip install mcp", file=sys.stderr)
        sys.exit(1)

    # ヘルスチェック
    threading.Thread(target=_start_health_server, daemon=True).start()

    async with stdio_server() as (read_stream, write_stream):  # type: ignore[possibly-unbound]
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
