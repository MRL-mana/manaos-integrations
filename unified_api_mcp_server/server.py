"""
Unified API Server MCPサーバー
Unified API Serverのすべての機能をMCPツールとして提供
"""

import os
import sys
import json
import requests
from typing import Any, Dict, List, Optional
from pathlib import Path

# Windows環境での文字エンコーディング設定
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# パスを追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from _paths import ORCHESTRATOR_PORT, UNIFIED_API_PORT

from mcp_common import check_mcp_available, get_mcp_logger

MCP_AVAILABLE = check_mcp_available()
if MCP_AVAILABLE:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent

logger = get_mcp_logger(__name__)
if not MCP_AVAILABLE:
    logger.warning("MCP SDKがインストールされていません。pip install mcp を実行してください。")

# APIエンドポイント
# NOTE:
# - ManaOSの統合APIはデフォルト 9510（Docker/WSL の 9500-9503 衝突回避）
# - 必要に応じて環境変数 `MANAOS_INTEGRATION_API_URL` で上書き可能
UNIFIED_API_URL = (
    os.getenv("MANAOS_INTEGRATION_API_URL")
    or f"http://127.0.0.1:{UNIFIED_API_PORT}"
).rstrip("/")
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", f"http://127.0.0.1:{ORCHESTRATOR_PORT}")

# MCPサーバーの初期化
if MCP_AVAILABLE:
    app = Server("unified-api")
else:
    app = None


def call_api(
    endpoint: str,
    method: str = "GET",
    data: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Unified API Serverを呼び出す"""
    url = f"{UNIFIED_API_URL}{endpoint}"

    try:
        if method == "GET":
            response = requests.get(url, params=params, timeout=30)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=300)
        elif method == "PUT":
            response = requests.put(url, json=data, timeout=30)
        elif method == "DELETE":
            response = requests.delete(url, timeout=30)
        else:
            return {"error": f"Unsupported method: {method}"}

        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"API呼び出しエラー ({endpoint}): {e}")
        return {"error": str(e), "success": False}


def call_orchestrator(query: str) -> Dict[str, Any]:
    """Unified Orchestrator（ask_orchestrator）を呼び出す"""
    url = f"{ORCHESTRATOR_URL}/api/execute"
    try:
        response = requests.post(
            url,
            json={"query": query, "auto_evaluate": True, "save_to_memory": True},
            timeout=300,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Orchestrator呼び出しエラー: {e}")
        return {"error": str(e), "success": False}


if MCP_AVAILABLE:

    @app.list_tools()
    async def list_tools() -> List[Tool]:
        """利用可能なツール一覧を返す"""
        tools = []

        # ========================================
        # 汎用オーケストレーター（1ツールで自然文を投げる）
        # ========================================
        tools.extend(
            [
                Tool(
                    name="ask_orchestrator",
                    description="室温・湿度・天気・照明操作など、ローカル環境に関する情報取得や操作を自然文で依頼する。知らないことはこのツールに投げる。一般的な知識や検索はこのツールを使わず検索で対応する。",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "自然文でのリクエスト内容"}
                        },
                        "required": ["query"],
                    },
                )
            ]
        )

        # ========================================
        # ヘルスチェック・ステータス
        # ========================================
        tools.extend(
            [
                Tool(
                    name="unified_api_health",
                    description="Unified API Serverのヘルスチェック",
                    inputSchema={"type": "object", "properties": {}},
                ),
                Tool(
                    name="unified_api_status",
                    description="Unified API Serverの詳細ステータスを取得",
                    inputSchema={"type": "object", "properties": {}},
                ),
                Tool(
                    name="unified_api_integrations_status",
                    description="統合モジュールの状態を取得",
                    inputSchema={"type": "object", "properties": {}},
                ),
            ]
        )

        # ========================================
        # ComfyUI画像生成
        # ========================================
        tools.extend(
            [
                Tool(
                    name="comfyui_generate_image",
                    description="ComfyUIで画像を生成します",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "prompt": {"type": "string", "description": "プロンプト（必須）"},
                            "negative_prompt": {
                                "type": "string",
                                "description": "ネガティブプロンプト",
                            },
                            "width": {
                                "type": "integer",
                                "description": "画像幅（デフォルト: 512）",
                                "default": 512,
                            },
                            "height": {
                                "type": "integer",
                                "description": "画像高さ（デフォルト: 512）",
                                "default": 512,
                            },
                            "steps": {
                                "type": "integer",
                                "description": "ステップ数（デフォルト: 20）",
                                "default": 20,
                            },
                            "seed": {"type": "integer", "description": "シード値（オプション）"},
                        },
                        "required": ["prompt"],
                    },
                )
            ]
        )

        # ========================================
        # SVI動画生成
        # ========================================
        tools.extend(
            [
                Tool(
                    name="svi_generate_video",
                    description="SVI × Wan 2.2で動画を生成します",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "start_image_path": {
                                "type": "string",
                                "description": "開始画像のパス（必須）",
                            },
                            "prompt": {
                                "type": "string",
                                "description": "プロンプト（日本語可、必須）",
                            },
                            "video_length_seconds": {
                                "type": "integer",
                                "description": "動画の長さ（秒、デフォルト: 5）",
                                "default": 5,
                            },
                            "steps": {
                                "type": "integer",
                                "description": "ステップ数（デフォルト: 6）",
                                "default": 6,
                            },
                            "motion_strength": {
                                "type": "number",
                                "description": "モーション強度（デフォルト: 1.3）",
                                "default": 1.3,
                            },
                        },
                        "required": ["start_image_path", "prompt"],
                    },
                ),
                Tool(
                    name="svi_extend_video",
                    description="既存の動画を延長します",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "previous_video_path": {
                                "type": "string",
                                "description": "前の動画のパス（必須）",
                            },
                            "prompt": {
                                "type": "string",
                                "description": "延長部分のプロンプト（必須）",
                            },
                            "extend_seconds": {
                                "type": "integer",
                                "description": "延長する秒数（デフォルト: 5）",
                                "default": 5,
                            },
                        },
                        "required": ["previous_video_path", "prompt"],
                    },
                ),
                Tool(
                    name="svi_get_queue_status",
                    description="ComfyUIのキュー状態を取得します",
                    inputSchema={"type": "object", "properties": {}},
                ),
                Tool(
                    name="svi_get_history",
                    description="SVI動画生成履歴を取得します",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": "取得件数（デフォルト: 10）",
                                "default": 10,
                            }
                        },
                    },
                ),
            ]
        )

        # ========================================
        # Google Drive
        # ========================================
        tools.extend(
            [
                Tool(
                    name="google_drive_upload",
                    description="Google Driveにファイルをアップロードします",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "アップロードするファイルのパス（必須）",
                            },
                            "folder_name": {
                                "type": "string",
                                "description": "アップロード先フォルダ名",
                            },
                            "file_name": {
                                "type": "string",
                                "description": "アップロード後のファイル名",
                            },
                        },
                        "required": ["file_path"],
                    },
                )
            ]
        )

        # ========================================
        # CivitAI
        # ========================================
        tools.extend(
            [
                Tool(
                    name="civitai_search",
                    description="CivitAIでモデルを検索します",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "検索クエリ（必須）"},
                            "limit": {
                                "type": "integer",
                                "description": "取得件数（デフォルト: 10）",
                                "default": 10,
                            },
                        },
                        "required": ["query"],
                    },
                )
            ]
        )

        # ========================================
        # 検索エンジン
        # ========================================
        tools.extend(
            [
                Tool(
                    name="searxng_search",
                    description="SearXNGで検索します",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "検索クエリ（必須）"},
                            "categories": {
                                "type": "string",
                                "description": "カテゴリ（カンマ区切り）",
                            },
                            "engines": {
                                "type": "string",
                                "description": "検索エンジン（カンマ区切り）",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "取得件数（デフォルト: 10）",
                                "default": 10,
                            },
                        },
                        "required": ["query"],
                    },
                ),
                Tool(
                    name="brave_search",
                    description="Brave Searchで検索します",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "検索クエリ（必須）"},
                            "count": {
                                "type": "integer",
                                "description": "取得件数（デフォルト: 10）",
                                "default": 10,
                            },
                            "search_lang": {
                                "type": "string",
                                "description": "検索言語（デフォルト: ja）",
                                "default": "ja",
                            },
                            "country": {
                                "type": "string",
                                "description": "国コード（デフォルト: JP）",
                                "default": "JP",
                            },
                        },
                        "required": ["query"],
                    },
                ),
            ]
        )

        # ========================================
        # Base AI
        # ========================================
        tools.extend(
            [
                Tool(
                    name="base_ai_chat",
                    description="Base AIでチャットします",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "message": {"type": "string", "description": "メッセージ（必須）"},
                            "conversation_id": {
                                "type": "string",
                                "description": "会話ID（オプション）",
                            },
                        },
                        "required": ["message"],
                    },
                )
            ]
        )

        # ========================================
        # Obsidian
        # ========================================
        tools.extend(
            [
                Tool(
                    name="obsidian_create_note",
                    description="Obsidianにノートを作成します",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "ノートタイトル（必須）"},
                            "content": {"type": "string", "description": "ノート内容（必須）"},
                            "folder": {
                                "type": "string",
                                "description": "フォルダパス（オプション）",
                            },
                        },
                        "required": ["title", "content"],
                    },
                )
            ]
        )

        # ========================================
        # 記憶システム
        # ========================================
        tools.extend(
            [
                Tool(
                    name="memory_store",
                    description="統一記憶システムに情報を保存します",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "content": {"type": "string", "description": "保存する内容（必須）"},
                            "metadata": {
                                "type": "object",
                                "description": "メタデータ（オプション）",
                            },
                            "format_type": {
                                "type": "string",
                                "description": "フォーマットタイプ（auto/text/json/markdown）",
                                "default": "auto",
                            },
                        },
                        "required": ["content"],
                    },
                ),
                Tool(
                    name="memory_recall",
                    description="統一記憶システムから情報を検索します",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "検索クエリ（必須）"},
                            "scope": {
                                "type": "string",
                                "description": "検索スコープ（all/recent/important）",
                                "default": "all",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "取得件数（デフォルト: 10）",
                                "default": 10,
                            },
                        },
                        "required": ["query"],
                    },
                ),
            ]
        )

        # ========================================
        # 通知システム
        # ========================================
        tools.extend(
            [
                Tool(
                    name="notification_send",
                    description="通知を送信します",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "message": {"type": "string", "description": "通知メッセージ（必須）"},
                            "priority": {
                                "type": "string",
                                "description": "優先度（low/normal/high/urgent）",
                                "default": "normal",
                            },
                        },
                        "required": ["message"],
                    },
                )
            ]
        )

        # ========================================
        # 秘書機能
        # ========================================
        tools.extend(
            [
                Tool(
                    name="secretary_morning_routine",
                    description="朝のルーチンを実行します",
                    inputSchema={"type": "object", "properties": {}},
                ),
                Tool(
                    name="secretary_noon_routine",
                    description="昼のルーチンを実行します",
                    inputSchema={"type": "object", "properties": {}},
                ),
                Tool(
                    name="secretary_evening_routine",
                    description="夜のルーチンを実行します",
                    inputSchema={"type": "object", "properties": {}},
                ),
            ]
        )

        # ========================================
        # キャッシュ・パフォーマンス
        # ========================================
        tools.extend(
            [
                Tool(
                    name="cache_stats",
                    description="キャッシュ統計を取得します",
                    inputSchema={"type": "object", "properties": {}},
                ),
                Tool(
                    name="performance_stats",
                    description="パフォーマンス統計を取得します",
                    inputSchema={"type": "object", "properties": {}},
                ),
            ]
        )

        return tools

    @app.call_tool()
    async def call_tool(name: str, arguments: Any) -> List[TextContent]:
        """ツールを実行"""
        try:
            args = json.loads(arguments) if isinstance(arguments, str) else arguments

            # 汎用オーケストレーター
            if name == "ask_orchestrator":
                result = call_orchestrator(args.get("query", ""))

            # ヘルスチェック・ステータス
            elif name == "unified_api_health":
                result = call_api("/health")
            elif name == "unified_api_status":
                result = call_api("/status")
            elif name == "unified_api_integrations_status":
                result = call_api("/api/integrations/status")

            # ComfyUI
            elif name == "comfyui_generate_image":
                result = call_api("/api/comfyui/generate", "POST", args)

            # SVI
            elif name == "svi_generate_video":
                result = call_api("/api/svi/generate", "POST", args)
            elif name == "svi_extend_video":
                result = call_api("/api/svi/extend", "POST", args)
            elif name == "svi_get_queue_status":
                result = call_api("/api/svi/queue")
            elif name == "svi_get_history":
                result = call_api("/api/svi/history", params={"limit": args.get("limit", 10)})

            # Google Drive
            elif name == "google_drive_upload":
                result = call_api("/api/google_drive/upload", "POST", args)

            # CivitAI
            elif name == "civitai_search":
                result = call_api(
                    "/api/civitai/search",
                    params={"query": args.get("query"), "limit": args.get("limit", 10)},
                )

            # 検索エンジン
            elif name == "searxng_search":
                result = call_api("/api/searxng/search", "POST", args)
            elif name == "brave_search":
                result = call_api("/api/brave/search", "POST", args)

            # Base AI
            elif name == "base_ai_chat":
                result = call_api("/api/base-ai/chat", "POST", args)

            # Obsidian
            elif name == "obsidian_create_note":
                result = call_api("/api/obsidian/create", "POST", args)

            # 記憶システム
            elif name == "memory_store":
                result = call_api("/api/memory/store", "POST", args)
            elif name == "memory_recall":
                result = call_api(
                    "/api/memory/recall",
                    params={
                        "query": args.get("query"),
                        "scope": args.get("scope", "all"),
                        "limit": args.get("limit", 10),
                    },
                )

            # 通知システム
            elif name == "notification_send":
                result = call_api("/api/notification/send", "POST", args)

            # 秘書機能
            elif name == "secretary_morning_routine":
                result = call_api("/api/secretary/morning", "POST")
            elif name == "secretary_noon_routine":
                result = call_api("/api/secretary/noon", "POST")
            elif name == "secretary_evening_routine":
                result = call_api("/api/secretary/evening", "POST")

            # キャッシュ・パフォーマンス
            elif name == "cache_stats":
                result = call_api("/api/cache/stats")
            elif name == "performance_stats":
                result = call_api("/api/performance/stats")

            else:
                result = {"error": f"Unknown tool: {name}"}

            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

        except Exception as e:
            logger.error(f"ツール実行エラー ({name}): {e}")
            import traceback

            logger.error(traceback.format_exc())
            return [
                TextContent(type="text", text=json.dumps({"error": str(e)}, ensure_ascii=False))
            ]


async def main():
    """メイン関数"""
    if not MCP_AVAILABLE:
        logger.error("MCP SDKが利用できません")
        sys.exit(1)

    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
