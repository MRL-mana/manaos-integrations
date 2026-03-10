"""
CASTLE-EX Layer2 LoRA 推論 MCP サーバー
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Layer2 スタイル矯正 LoRA (v1.1.6 production) の推論ツールを
Cursor / VS Code Copilot に公開する MCP サーバー。

castle_ex_layer2_inference_server.py (port 9520) に HTTP で通信する。

ツール一覧:
  castle_ex_layer2_generate  -- メイン生成
  castle_ex_layer2_status    -- サーバー状態確認
"""
from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from mcp_common import check_mcp_available, get_mcp_logger, start_health_thread  # type: ignore
    from _paths import LAYER2_INFER_PORT  # type: ignore
except ImportError:
    # フォールバック
    def check_mcp_available() -> bool:  # type: ignore
        try:
            import mcp  # noqa: F401
            return True
        except ImportError:
            return False

    def get_mcp_logger(name: str):  # type: ignore
        return logging.getLogger(name)

    def start_health_thread(*_, **__):  # type: ignore
        pass

    LAYER2_INFER_PORT: int = int(os.getenv("LAYER2_INFER_PORT", "9520"))

MCP_AVAILABLE = check_mcp_available()
if MCP_AVAILABLE:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent  # type: ignore

logger = get_mcp_logger(__name__)

LAYER2_API_URL = os.environ.get(
    "LAYER2_INFER_URL", f"http://127.0.0.1:{LAYER2_INFER_PORT}"
)

# ─── HTTP ヘルパー ────────────────────────────────────────────────────────────

def _post(path: str, payload: dict, timeout: int = 120) -> Dict[str, Any]:
    url = f"{LAYER2_API_URL}{path}"
    try:
        r = requests.post(url, json=payload, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        return {"error": f"Layer2 推論サーバー (port {LAYER2_INFER_PORT}) に接続できません。start_castle_ex_layer2.ps1 で起動してください。"}
    except Exception as exc:
        return {"error": str(exc)}


def _get(path: str, timeout: int = 10) -> Dict[str, Any]:
    url = f"{LAYER2_API_URL}{path}"
    try:
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        return {"error": f"Layer2 推論サーバー (port {LAYER2_INFER_PORT}) に接続できません。"}
    except Exception as exc:
        return {"error": str(exc)}

# ─── MCP ─────────────────────────────────────────────────────────────────────

if MCP_AVAILABLE:
    app = Server("castle-ex-layer2")  # type: ignore[possibly-unbound]

    @app.list_tools()
    async def list_tools() -> List[Tool]:
        return [
            Tool(  # type: ignore[possibly-unbound]
                name="castle_ex_layer2_generate",
                description=(
                    "CASTLE-EX Layer2 スタイル矯正 LoRA (v1.1.6) で短文生成する。\n"
                    "mode='short' → LoRA ON（property 質問への短文答えを強制）\n"
                    "mode='free'  → LoRA OFF（通常の自然会話）\n"
                    "mode='training_eval' → LoRA OFF（評価干渉防止）\n"
                    "※ Layer2 推論サーバー (port 9520) が起動済みである必要があります。"
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "推論プロンプト（ユーザーの質問文など）"
                        },
                        "mode": {
                            "type": "string",
                            "enum": ["short", "free", "training_eval"],
                            "description": "LoRA 使用モード (default: 'short')",
                            "default": "short"
                        },
                        "max_new_tokens": {
                            "type": "integer",
                            "description": "生成上限トークン (1~256, default: 64)",
                            "default": 64,
                            "minimum": 1,
                            "maximum": 256
                        },
                        "temperature": {
                            "type": "number",
                            "description": "サンプリング温度 (default: 0.2)",
                            "default": 0.2
                        },
                        "repetition_penalty": {
                            "type": "number",
                            "description": "繰り返し抑制係数 (default: 1.1)",
                            "default": 1.1
                        },
                        "do_sample": {
                            "type": "boolean",
                            "description": "サンプリング ON/OFF (default: false = greedy)",
                            "default": False
                        }
                    },
                    "required": ["prompt"]
                },
            ),
            Tool(  # type: ignore[possibly-unbound]
                name="castle_ex_layer2_status",
                description="Layer2 推論サーバーの状態（モデルロード済み/LoRA アクティブ）を確認する。",
                inputSchema={"type": "object", "properties": {}},
            ),
        ]

    @app.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        try:
            if name == "castle_ex_layer2_generate":
                payload = {
                    "prompt":             arguments.get("prompt", ""),
                    "mode":               arguments.get("mode", "short"),
                    "max_new_tokens":     arguments.get("max_new_tokens", 64),
                    "temperature":        arguments.get("temperature", 0.2),
                    "repetition_penalty": arguments.get("repetition_penalty", 1.1),
                    "do_sample":          arguments.get("do_sample", False),
                }
                result = _post("/generate", payload, timeout=120)

            elif name == "castle_ex_layer2_status":
                result = _get("/status")

            else:
                result = {"error": f"未知のツール: {name}"}

            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]  # type: ignore[possibly-unbound]

        except Exception as exc:
            logger.exception("call_tool error")
            return [TextContent(type="text", text=json.dumps({"error": str(exc)}, ensure_ascii=False))]  # type: ignore[possibly-unbound]


async def main() -> None:
    if not MCP_AVAILABLE:
        logger.error("MCP SDK がありません。pip install mcp を実行してください。")
        sys.exit(1)

    health_port = int(os.getenv("PORT", "5140"))
    start_health_thread("castle-ex-layer2", health_port)

    async with stdio_server() as (rs, ws):  # type: ignore[possibly-unbound]
        await app.run(rs, ws, app.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
