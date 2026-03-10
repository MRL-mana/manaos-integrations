"""
Trinity System MCPサーバー (直接インポート版)
==============================================
Remi（判断・実行）/ Luna（監視・分析）/ Mina（記憶・学習）
3エージェントへのタスクルーティングをMCPツールとして提供。

HTTP APIへの依存なし。TrinityIntegrationを直接インポートして使用。

ツール一覧:
  - trinity_route              : タスクタイプから担当エージェントを特定
  - trinity_who_does           : 特定の作業（計画/検索/検証/執筆）の担当者を返す
  - trinity_enhance_prompt     : プロンプトをエージェント向けに強化
  - trinity_format_context     : エージェント用コンテキストをフォーマット
  - trinity_log_activity       : エージェント活動をログ記録
"""

import os
import sys
import json
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

# パスを追加（step_deep_researchモジュールを解決）
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    print("WARNING: mcp package not found. Install with: pip install mcp", file=sys.stderr)

# Trinity 設定を読み込む（step_deep_research_config.json から）
_CONFIG_PATH = _ROOT / "step_deep_research_config.json"
_DEFAULT_TRINITY_CONFIG = {
    "trinity_integration": {
        "remi_role": ["planner", "writer"],
        "luna_role": ["searcher", "reader"],
        "mina_role": ["verifier", "critic_assistant"],
    }
}


def _load_config() -> dict:
    try:
        with open(_CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return _DEFAULT_TRINITY_CONFIG


# TrinityIntegration をインポート
_trinity = None
_trinity_error = None

try:
    from step_deep_research.trinity_integration import TrinityIntegration, TrinityAgent
    _config = _load_config()
    _trinity = TrinityIntegration(config=_config)
    _trinity_error = None
except Exception as e:
    _trinity_error = str(e)
    _trinity = None

# ── ヘルスチェック HTTP ─────────────────────────────
HEALTH_PORT = int(os.getenv("TRINITY_MCP_HEALTH_PORT", "5146"))


class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            status = "healthy" if _trinity is not None else "degraded"
            body = {"status": status, "service": "trinity-mcp"}
            if _trinity_error:
                body["error"] = _trinity_error
            self.wfile.write(json.dumps(body).encode())
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


# ── ヘルパー ─────────────────────────────────────
def _agent_name(agent) -> str:
    """TrinityAgent → 日本語名"""
    if agent is None:
        return "不明（デフォルト）"
    mapping = {
        "remi": "Remi（判断・実行）",
        "luna": "Luna（監視・分析）",
        "mina": "Mina（記憶・学習）",
    }
    return mapping.get(agent.value if hasattr(agent, "value") else str(agent), str(agent))


# ── MCP サーバー ────────────────────────────────────
if MCP_AVAILABLE:
    server = Server("trinity-system")  # type: ignore[possibly-unbound]

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(  # type: ignore[possibly-unbound]
                name="trinity_route",
                description=(
                    "タスクタイプから担当エージェント（Remi/Luna/Mina）を特定する。\n"
                    "タスクタイプ例: planner, writer, searcher, reader, verifier, critic_assistant"
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "task_type": {
                            "type": "string",
                            "description": "タスクタイプ（例: planner, searcher, verifier）",
                        }
                    },
                    "required": ["task_type"],
                },
            ),
            Tool(  # type: ignore[possibly-unbound]
                name="trinity_who_does",
                description=(
                    "特定の作業（planning/search/reading/verification/writing/critique）を誰が担当するか返す。\n"
                    "action: planning, search, reading, verification, writing, critique のいずれか"
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["planning", "search", "reading", "verification", "writing", "critique"],
                            "description": "作業種別",
                        }
                    },
                    "required": ["action"],
                },
            ),
            Tool(  # type: ignore[possibly-unbound]
                name="trinity_enhance_prompt",
                description="プロンプトをエージェント（Remi/Luna/Mina）向けに強化する。エージェント専用の文脈情報を先頭に付与。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "強化するプロンプトテキスト",
                        },
                        "agent": {
                            "type": "string",
                            "enum": ["remi", "luna", "mina"],
                            "description": "対象エージェント",
                        },
                    },
                    "required": ["prompt", "agent"],
                },
            ),
            Tool(  # type: ignore[possibly-unbound]
                name="trinity_format_context",
                description="エージェント向けのコンテキスト説明文を生成する（役割・担当・注意事項）。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "agent": {
                            "type": "string",
                            "enum": ["remi", "luna", "mina"],
                            "description": "対象エージェント",
                        }
                    },
                    "required": ["agent"],
                },
            ),
            Tool(  # type: ignore[possibly-unbound]
                name="trinity_log_activity",
                description="エージェントの活動をログに記録する。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "agent": {
                            "type": "string",
                            "enum": ["remi", "luna", "mina"],
                            "description": "エージェント名",
                        },
                        "activity": {
                            "type": "string",
                            "description": "活動内容",
                        },
                        "details": {
                            "type": "object",
                            "description": "追加詳細情報（任意）",
                        },
                    },
                    "required": ["agent", "activity"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        if _trinity is None:
            result = {"error": f"Trinity未初期化: {_trinity_error}"}
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]  # type: ignore[possibly-unbound]

        try:
            if name == "trinity_route":
                task_type = arguments.get("task_type", "")
                agent = _trinity.route_to_agent(task_type)
                result = {
                    "task_type": task_type,
                    "assigned_agent": agent.value if agent else None,
                    "assigned_agent_ja": _agent_name(agent),
                }

            elif name == "trinity_who_does":
                action = arguments.get("action", "")
                action_map = {
                    "planning": _trinity.get_agent_for_planning,
                    "search": _trinity.get_agent_for_search,
                    "reading": _trinity.get_agent_for_reading,
                    "verification": _trinity.get_agent_for_verification,
                    "writing": _trinity.get_agent_for_writing,
                    "critique": _trinity.get_agent_for_critique,
                }
                fn = action_map.get(action)
                if fn:
                    agent = fn()
                    result = {
                        "action": action,
                        "agent": agent.value,
                        "agent_ja": _agent_name(agent),
                    }
                else:
                    result = {"error": f"Unknown action: {action}"}

            elif name == "trinity_enhance_prompt":
                prompt = arguments.get("prompt", "")
                agent_name_str = arguments.get("agent", "remi")
                try:
                    from step_deep_research.trinity_integration import TrinityAgent as _TA
                    agent = _TA(agent_name_str)
                except Exception:
                    agent = None
                if agent:
                    enhanced = _trinity.enhance_prompt_for_agent(prompt, agent, {})
                    result = {"enhanced_prompt": enhanced, "agent": agent_name_str}
                else:
                    result = {"error": f"Invalid agent: {agent_name_str}"}

            elif name == "trinity_format_context":
                agent_name_str = arguments.get("agent", "remi")
                try:
                    from step_deep_research.trinity_integration import TrinityAgent as _TA
                    agent = _TA(agent_name_str)
                except Exception:
                    agent = None
                if agent:
                    context_text = _trinity.format_agent_context(agent, {})
                    result = {"agent": agent_name_str, "context": context_text}
                else:
                    result = {"error": f"Invalid agent: {agent_name_str}"}

            elif name == "trinity_log_activity":
                agent_name_str = arguments.get("agent", "remi")
                activity = arguments.get("activity", "")
                details = arguments.get("details", {})
                try:
                    from step_deep_research.trinity_integration import TrinityAgent as _TA
                    agent = _TA(agent_name_str)
                except Exception:
                    agent = None
                if agent:
                    _trinity.log_agent_activity(agent, activity, details)
                    result = {"logged": True, "agent": agent_name_str, "activity": activity}
                else:
                    result = {"error": f"Invalid agent: {agent_name_str}"}

            else:
                result = {"error": f"Unknown tool: {name}"}

        except Exception as e:
            result = {"error": str(e)}

        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]  # type: ignore[possibly-unbound]


async def main():
    if not MCP_AVAILABLE:
        print("ERROR: mcp package required. Run: pip install mcp", file=sys.stderr)
        sys.exit(1)

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
