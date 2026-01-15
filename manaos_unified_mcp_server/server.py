"""
ManaOS統合MCPサーバー
すべてのManaOS機能をCursorから直接使用できる統合MCPサーバー
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Optional, Sequence
import logging
import io
import httpx

# Windows環境での文字エンコーディング設定
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# パスを追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 環境変数の読み込み（python-dotenvを使用）
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        logger.info(".envファイルを読み込みました")
except ImportError:
    logger.warning("python-dotenvがインストールされていません。.envファイルは読み込まれません。")

# 統一エラーハンドリングのインポート
try:
    from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
    error_handler = ManaOSErrorHandler("manaos-unified-mcp-server")
    ERROR_HANDLER_AVAILABLE = True
except ImportError:
    logger.warning("統一エラーハンドリングモジュールが見つかりません。基本的なエラーハンドリングを使用します。")
    ERROR_HANDLER_AVAILABLE = False
    error_handler = None

# タイムアウト設定のインポート
try:
    from manaos_timeout_config import get_timeout_config
    timeout_config = get_timeout_config()
    TIMEOUT_CONFIG_AVAILABLE = True
except ImportError:
    logger.warning("タイムアウト設定モジュールが見つかりません。デフォルト値を使用します。")
    TIMEOUT_CONFIG_AVAILABLE = False
    timeout_config = None

# 環境変数から設定を読み込み
COMFYUI_URL = os.getenv("COMFYUI_URL", "http://localhost:8188")
MANAOS_API_URL = os.getenv("MANAOS_INTEGRATION_API_URL", "http://localhost:9500")
LEARNING_SYSTEM_URL = os.getenv("LEARNING_SYSTEM_URL", "http://localhost:5126")
PERSONALITY_SYSTEM_URL = os.getenv("PERSONALITY_SYSTEM_URL", "http://localhost:5123")
AUTONOMY_SYSTEM_URL = os.getenv("AUTONOMY_SYSTEM_URL", "http://localhost:5124")
SECRETARY_SYSTEM_URL = os.getenv("SECRETARY_SYSTEM_URL", "http://localhost:5125")

# 統合モジュール（遅延インポート）
_integrations = {}

def get_integration(name: str):
    """統合モジュールを取得（遅延インポート）"""
    if name not in _integrations:
        try:
            if name == "svi":
                from svi_wan22_video_integration import SVIWan22VideoIntegration
                _integrations[name] = SVIWan22VideoIntegration(base_url=COMFYUI_URL)
            elif name == "comfyui":
                from comfyui_integration import ComfyUIIntegration
                _integrations[name] = ComfyUIIntegration(base_url=COMFYUI_URL)
            elif name == "google_drive":
                from google_drive_integration import GoogleDriveIntegration
                _integrations[name] = GoogleDriveIntegration()
            elif name == "rows":
                from rows_integration import RowsIntegration
                _integrations[name] = RowsIntegration()
            elif name == "obsidian":
                vault_path = os.getenv("OBSIDIAN_VAULT_PATH", "C:/Users/mana4/Documents/Obsidian Vault")
                from obsidian_integration import ObsidianIntegration
                _integrations[name] = ObsidianIntegration(vault_path=vault_path)
            elif name == "image_stock":
                from image_stock import ImageStock
                _integrations[name] = ImageStock()
            elif name == "notification":
                from notification_hub import NotificationHub
                _integrations[name] = NotificationHub()
            elif name == "memory":
                from memory_unified import UnifiedMemory
                _integrations[name] = UnifiedMemory()
            elif name == "llm_routing":
                from llm_routing import LLMRouter
                _integrations[name] = LLMRouter()
            elif name == "secretary":
                from secretary_routines import SecretaryRoutines
                _integrations[name] = SecretaryRoutines()
            elif name == "searxng":
                from searxng_integration import SearXNGIntegration
                searxng_url = os.getenv("SEARXNG_BASE_URL", "http://localhost:8080")
                _integrations[name] = SearXNGIntegration(base_url=searxng_url)
            elif name == "brave_search":
                from brave_search_integration import BraveSearchIntegration
                _integrations[name] = BraveSearchIntegration()
            elif name == "base_ai":
                from base_ai_integration import BaseAIIntegration
                use_free = os.getenv("BASE_AI_USE_FREE", "false").lower() == "true"
                _integrations[name] = BaseAIIntegration(use_free=use_free)
        except ImportError as e:
            logger.warning(f"{name}統合のインポートに失敗: {e}")
            return None
    return _integrations.get(name)

# MCPサーバーの作成
server = Server("manaos-unified")

@server.list_tools()
async def list_tools() -> list[Tool]:
    """利用可能なツール一覧を返す"""
    tools = []

    # ========================================
    # SVI動画生成
    # ========================================
    tools.extend([
        Tool(
            name="svi_generate_video",
            description="SVI × Wan 2.2で動画を生成します",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_image_path": {"type": "string", "description": "開始画像のパス（必須）"},
                    "prompt": {"type": "string", "description": "プロンプト（日本語可、必須）"},
                    "video_length_seconds": {"type": "integer", "description": "動画の長さ（秒、デフォルト: 5）", "default": 5},
                    "steps": {"type": "integer", "description": "ステップ数（デフォルト: 6）", "default": 6},
                    "motion_strength": {"type": "number", "description": "モーション強度（デフォルト: 1.3）", "default": 1.3}
                },
                "required": ["start_image_path", "prompt"]
            }
        ),
        Tool(
            name="svi_extend_video",
            description="既存の動画を延長します",
            inputSchema={
                "type": "object",
                "properties": {
                    "previous_video_path": {"type": "string", "description": "前の動画のパス（必須）"},
                    "prompt": {"type": "string", "description": "延長部分のプロンプト（必須）"},
                    "extend_seconds": {"type": "integer", "description": "延長する秒数（デフォルト: 5）", "default": 5}
                },
                "required": ["previous_video_path", "prompt"]
            }
        ),
        Tool(
            name="svi_get_queue_status",
            description="ComfyUIのキュー状態を取得します",
            inputSchema={"type": "object", "properties": {}}
        )
    ])

    # ========================================
    # ComfyUI画像生成
    # ========================================
    tools.extend([
        Tool(
            name="comfyui_generate_image",
            description="ComfyUIで画像を生成します",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "プロンプト（必須）"},
                    "negative_prompt": {"type": "string", "description": "ネガティブプロンプト"},
                    "width": {"type": "integer", "description": "画像幅（デフォルト: 512）", "default": 512},
                    "height": {"type": "integer", "description": "画像高さ（デフォルト: 512）", "default": 512},
                    "steps": {"type": "integer", "description": "ステップ数（デフォルト: 20）", "default": 20}
                },
                "required": ["prompt"]
            }
        )
    ])

    # ========================================
    # Google Drive
    # ========================================
    tools.extend([
        Tool(
            name="google_drive_upload",
            description="Google Driveにファイルをアップロードします",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "アップロードするファイルのパス（必須）"},
                    "folder_id": {"type": "string", "description": "フォルダID（オプション）"}
                },
                "required": ["file_path"]
            }
        ),
        Tool(
            name="google_drive_list_files",
            description="Google Driveのファイル一覧を取得します",
            inputSchema={
                "type": "object",
                "properties": {
                    "folder_id": {"type": "string", "description": "フォルダID（オプション）"},
                    "query": {"type": "string", "description": "検索クエリ（オプション）"}
                }
            }
        )
    ])

    # ========================================
    # Rows（スプレッドシート）
    # ========================================
    tools.extend([
        Tool(
            name="rows_query",
            description="RowsスプレッドシートにAI自然言語クエリを実行します",
            inputSchema={
                "type": "object",
                "properties": {
                    "spreadsheet_id": {"type": "string", "description": "スプレッドシートID（必須）"},
                    "query": {"type": "string", "description": "自然言語クエリ（必須）"},
                    "sheet_name": {"type": "string", "description": "シート名（デフォルト: Sheet1）", "default": "Sheet1"}
                },
                "required": ["spreadsheet_id", "query"]
            }
        ),
        Tool(
            name="rows_send_data",
            description="Rowsスプレッドシートにデータを送信します",
            inputSchema={
                "type": "object",
                "properties": {
                    "spreadsheet_id": {"type": "string", "description": "スプレッドシートID（必須）"},
                    "data": {"type": "array", "description": "送信するデータ（必須）"},
                    "sheet_name": {"type": "string", "description": "シート名（デフォルト: Sheet1）", "default": "Sheet1"}
                },
                "required": ["spreadsheet_id", "data"]
            }
        ),
        Tool(
            name="rows_list_spreadsheets",
            description="Rowsスプレッドシート一覧を取得します",
            inputSchema={"type": "object", "properties": {}}
        )
    ])

    # ========================================
    # Obsidian
    # ========================================
    tools.extend([
        Tool(
            name="obsidian_create_note",
            description="Obsidianにノートを作成します",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "ノートのタイトル（必須）"},
                    "content": {"type": "string", "description": "ノートの内容（必須）"},
                    "folder": {"type": "string", "description": "フォルダ（オプション）"}
                },
                "required": ["title", "content"]
            }
        ),
        Tool(
            name="obsidian_search_notes",
            description="Obsidianでノートを検索します",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "検索クエリ（必須）"}
                },
                "required": ["query"]
            }
        )
    ])

    # ========================================
    # 画像ストック
    # ========================================
    tools.extend([
        Tool(
            name="image_stock_add",
            description="画像をストックに追加します",
            inputSchema={
                "type": "object",
                "properties": {
                    "image_path": {"type": "string", "description": "画像のパス（必須）"},
                    "tags": {"type": "array", "description": "タグ（オプション）", "items": {"type": "string"}},
                    "description": {"type": "string", "description": "説明（オプション）"}
                },
                "required": ["image_path"]
            }
        ),
        Tool(
            name="image_stock_search",
            description="画像ストックから画像を検索します",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "検索クエリ（必須）"}
                },
                "required": ["query"]
            }
        )
    ])

    # ========================================
    # 通知
    # ========================================
    tools.extend([
        Tool(
            name="notification_send",
            description="通知を送信します",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "通知メッセージ（必須）"},
                    "priority": {"type": "string", "description": "優先度（critical/important/normal/low、デフォルト: normal）", "default": "normal"}
                },
                "required": ["message"]
            }
        )
    ])

    # ========================================
    # 記憶システム
    # ========================================
    tools.extend([
        Tool(
            name="memory_store",
            description="記憶に情報を保存します",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "保存する内容（必須）"},
                    "format_type": {"type": "string", "description": "フォーマットタイプ（conversation/memo/research/system、デフォルト: auto）", "default": "auto"}
                },
                "required": ["content"]
            }
        ),
        Tool(
            name="memory_recall",
            description="記憶から情報を検索します",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "検索クエリ（必須）"},
                    "scope": {"type": "string", "description": "スコープ（all/today/week/month、デフォルト: all）", "default": "all"},
                    "limit": {"type": "integer", "description": "取得件数（デフォルト: 10）", "default": 10}
                },
                "required": ["query"]
            }
        )
    ])

    # ========================================
    # LLMルーティング
    # ========================================
    tools.extend([
        Tool(
            name="llm_chat",
            description="LLMとチャットします（最適なモデルを自動選択）",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "プロンプト（必須）"},
                    "task_type": {"type": "string", "description": "タスクタイプ（conversation/code/analysis/generation、デフォルト: conversation）", "default": "conversation"}
                },
                "required": ["prompt"]
            }
        )
    ])

    # ========================================
    # 秘書機能
    # ========================================
    tools.extend([
        Tool(
            name="secretary_morning_routine",
            description="朝のルーチンを実行します",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="secretary_noon_routine",
            description="昼のルーチンを実行します",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="secretary_evening_routine",
            description="夜のルーチンを実行します",
            inputSchema={"type": "object", "properties": {}}
        )
    ])

    # ========================================
    # 学習系（Learning System）
    # ========================================
    tools.extend([
        Tool(
            name="learning_record",
            description="学習システムに使用パターンを記録します",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {"type": "string", "description": "アクション名（必須）"},
                    "context": {"type": "object", "description": "コンテキスト情報"},
                    "result": {"type": "object", "description": "結果情報"}
                },
                "required": ["action"]
            }
        ),
        Tool(
            name="learning_analyze",
            description="学習システムでパターンを分析します",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="learning_get_preferences",
            description="学習された好みを取得します",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="learning_get_optimizations",
            description="最適化提案を取得します",
            inputSchema={"type": "object", "properties": {}}
        )
    ])

    # ========================================
    # 人格系（Personality System）
    # ========================================
    tools.extend([
        Tool(
            name="personality_get_persona",
            description="現在の人格プロフィールを取得します",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="personality_get_prompt",
            description="人格プロンプトを取得します",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="personality_apply",
            description="プロンプトに人格を適用します",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "ベースプロンプト（必須）"},
                    "context": {"type": "string", "description": "コンテキスト（report/conversation）"}
                },
                "required": ["prompt"]
            }
        ),
        Tool(
            name="personality_update",
            description="人格プロフィールを更新します",
            inputSchema={
                "type": "object",
                "properties": {
                    "updates": {"type": "object", "description": "更新内容（必須）"}
                },
                "required": ["updates"]
            }
        )
    ])

    # ========================================
    # 自律系（Autonomy System）
    # ========================================
    tools.extend([
        Tool(
            name="autonomy_add_task",
            description="自律タスクを追加します",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_type": {"type": "string", "description": "タスクタイプ（必須）"},
                    "priority": {"type": "string", "description": "優先度（high/medium/low、デフォルト: medium）", "default": "medium"},
                    "condition": {"type": "object", "description": "実行条件（必須）"},
                    "action": {"type": "object", "description": "実行アクション（必須）"},
                    "schedule": {"type": "string", "description": "スケジュール（cron形式、オプション）"}
                },
                "required": ["task_type", "condition", "action"]
            }
        ),
        Tool(
            name="autonomy_execute_tasks",
            description="条件をチェックして自律タスクを実行します",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="autonomy_list_tasks",
            description="自律タスク一覧を取得します",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="autonomy_get_level",
            description="現在の自律レベルを取得します",
            inputSchema={"type": "object", "properties": {}}
        )
    ])

    # ========================================
    # VS Code操作
    # ========================================
    tools.extend([
        Tool(
            name="vscode_open_file",
            description="VS Codeでファイルを開きます",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "ファイルパス（必須）"},
                    "line": {"type": "integer", "description": "行番号（オプション）"}
                },
                "required": ["file_path"]
            }
        ),
        Tool(
            name="vscode_open_folder",
            description="VS Codeでフォルダを開きます",
            inputSchema={
                "type": "object",
                "properties": {
                    "folder_path": {"type": "string", "description": "フォルダパス（必須）"}
                },
                "required": ["folder_path"]
            }
        ),
        Tool(
            name="vscode_execute_command",
            description="VS Codeでコマンドを実行します",
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "コマンド（必須）"},
                    "args": {"type": "array", "description": "コマンド引数（オプション）", "items": {"type": "string"}}
                },
                "required": ["command"]
            }
        ),
        Tool(
            name="vscode_search_files",
            description="VS Codeでファイルを検索します",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "検索クエリ（必須）"},
                    "include": {"type": "string", "description": "検索対象ファイル（例: *.py）"},
                    "exclude": {"type": "string", "description": "除外ファイル（例: node_modules/**）"}
                },
                "required": ["query"]
            }
        )
    ])

    # ========================================
    # SearXNG Web検索
    # ========================================
    tools.extend([
        Tool(
            name="web_search",
            description="SearXNGを使用してWeb検索を実行します（実質無制限の検索が可能）",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "検索クエリ（必須）"},
                    "max_results": {"type": "integer", "description": "最大結果数（デフォルト: 10）", "default": 10},
                    "language": {"type": "string", "description": "言語コード（デフォルト: ja）", "default": "ja"},
                    "categories": {"type": "array", "description": "検索カテゴリ（例: [\"general\", \"images\"]）", "items": {"type": "string"}},
                    "time_range": {"type": "string", "description": "時間範囲フィルタ（day/week/month/year）"}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="web_search_simple",
            description="シンプルなWeb検索（結果のみ返す）",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "検索クエリ（必須）"},
                    "max_results": {"type": "integer", "description": "最大結果数（デフォルト: 5）", "default": 5}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="brave_search",
            description="Brave Search APIを使用してWeb検索を実行します（高品質な検索結果）",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "検索クエリ（必須）"},
                    "count": {"type": "integer", "description": "取得件数（デフォルト: 10、最大: 20）", "default": 10},
                    "search_lang": {"type": "string", "description": "検索言語（デフォルト: ja）", "default": "ja"},
                    "country": {"type": "string", "description": "国コード（デフォルト: JP）", "default": "JP"},
                    "freshness": {"type": "string", "description": "時間範囲フィルタ（pd: 過去1日、pw: 過去1週間、pm: 過去1ヶ月、py: 過去1年）"}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="brave_search_simple",
            description="Brave Search APIを使用したシンプルな検索（結果のみ返す）",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "検索クエリ（必須）"},
                    "count": {"type": "integer", "description": "取得件数（デフォルト: 5）", "default": 5}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="base_ai_chat",
            description="Base AI APIを使用してチャットを実行します（無料のAI APIも利用可能）",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "ユーザープロンプト（必須）"},
                    "system_prompt": {"type": "string", "description": "システムプロンプト（オプション）"},
                    "use_free": {"type": "boolean", "description": "無料のAI APIを使用するか（デフォルト: false）", "default": False},
                    "temperature": {"type": "number", "description": "温度パラメータ（デフォルト: 0.7）", "default": 0.7},
                    "max_tokens": {"type": "integer", "description": "最大トークン数（オプション）"}
                },
                "required": ["prompt"]
            }
        )
    ])

    # ========================================
    # Open WebUI操作
    # ========================================
    tools.extend([
        Tool(
            name="openwebui_create_chat",
            description="Open WebUIでチャットを作成します",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "最初のメッセージ（必須）"},
                    "model": {"type": "string", "description": "使用するモデル（例: qwen2.5-coder-7b-instruct）"},
                    "context_length": {"type": "integer", "description": "コンテキスト長（オプション）"}
                },
                "required": ["message"]
            }
        ),
        Tool(
            name="openwebui_list_chats",
            description="Open WebUIのチャット一覧を取得します",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "取得件数（デフォルト: 20）", "default": 20},
                    "offset": {"type": "integer", "description": "オフセット（デフォルト: 0）", "default": 0}
                }
            }
        ),
        Tool(
            name="openwebui_send_message",
            description="Open WebUIの既存チャットにメッセージを送信します",
            inputSchema={
                "type": "object",
                "properties": {
                    "chat_id": {"type": "string", "description": "チャットID（必須）"},
                    "message": {"type": "string", "description": "送信するメッセージ（必須）"}
                },
                "required": ["chat_id", "message"]
            }
        ),
        Tool(
            name="openwebui_get_chat",
            description="Open WebUIの特定チャットの情報を取得します",
            inputSchema={
                "type": "object",
                "properties": {
                    "chat_id": {"type": "string", "description": "チャットID（必須）"}
                },
                "required": ["chat_id"]
            }
        ),
        Tool(
            name="openwebui_list_models",
            description="Open WebUIで利用可能なモデル一覧を取得します",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="openwebui_update_settings",
            description="Open WebUIの設定を更新します",
            inputSchema={
                "type": "object",
                "properties": {
                    "enable_signup": {"type": "boolean", "description": "ユーザー登録を有効化するか"},
                    "default_model": {"type": "string", "description": "デフォルトモデル"},
                    "context_length": {"type": "integer", "description": "デフォルトコンテキスト長"}
                }
            }
        )
    ])

    return tools

@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> Sequence[TextContent]:
    """ツールを実行"""
    try:
        # SVI動画生成
        if name == "svi_generate_video":
            svi = get_integration("svi")
            if not svi:
                return [TextContent(type="text", text="❌ SVI統合が利用できません")]

            prompt_id = svi.generate_video(
                start_image_path=arguments.get("start_image_path"),
                prompt=arguments.get("prompt"),
                video_length_seconds=arguments.get("video_length_seconds", 5),
                steps=arguments.get("steps", 6),
                motion_strength=arguments.get("motion_strength", 1.3)
            )

            if prompt_id:
                return [TextContent(type="text", text=f"✅ 動画生成が開始されました\n実行ID: {prompt_id}")]
            else:
                return [TextContent(type="text", text="❌ 動画生成に失敗しました")]

        elif name == "svi_extend_video":
            svi = get_integration("svi")
            if not svi:
                return [TextContent(type="text", text="❌ SVI統合が利用できません")]

            prompt_id = svi.extend_video(
                previous_video_path=arguments.get("previous_video_path"),
                prompt=arguments.get("prompt"),
                extend_seconds=arguments.get("extend_seconds", 5)
            )

            if prompt_id:
                return [TextContent(type="text", text=f"✅ 動画延長が開始されました\n実行ID: {prompt_id}")]
            else:
                return [TextContent(type="text", text="❌ 動画延長に失敗しました")]

        elif name == "svi_get_queue_status":
            svi = get_integration("svi")
            if not svi:
                return [TextContent(type="text", text="❌ SVI統合が利用できません")]

            queue = svi.get_queue_status()
            return [TextContent(type="text", text=f"キュー状態:\n{json.dumps(queue, indent=2, ensure_ascii=False)}")]

        # ComfyUI画像生成
        elif name == "comfyui_generate_image":
            comfyui = get_integration("comfyui")
            if not comfyui:
                return [TextContent(type="text", text="❌ ComfyUI統合が利用できません")]

            prompt_id = comfyui.generate_image(
                prompt=arguments.get("prompt"),
                negative_prompt=arguments.get("negative_prompt", ""),
                width=arguments.get("width", 512),
                height=arguments.get("height", 512),
                steps=arguments.get("steps", 20)
            )

            if prompt_id:
                return [TextContent(type="text", text=f"✅ 画像生成が開始されました\n実行ID: {prompt_id}")]
            else:
                return [TextContent(type="text", text="❌ 画像生成に失敗しました")]

        # Google Drive
        elif name == "google_drive_upload":
            gd = get_integration("google_drive")
            if not gd:
                return [TextContent(type="text", text="❌ Google Drive統合が利用できません")]

            file_id = gd.upload_file(
                arguments.get("file_path"),
                arguments.get("folder_id")
            )

            if file_id:
                return [TextContent(type="text", text=f"✅ アップロード完了\nファイルID: {file_id}")]
            else:
                return [TextContent(type="text", text="❌ アップロードに失敗しました")]

        elif name == "google_drive_list_files":
            gd = get_integration("google_drive")
            if not gd:
                return [TextContent(type="text", text="❌ Google Drive統合が利用できません")]

            files = gd.list_files(
                folder_id=arguments.get("folder_id"),
                query=arguments.get("query")
            )

            return [TextContent(type="text", text=f"ファイル一覧 ({len(files)}件):\n{json.dumps(files, indent=2, ensure_ascii=False)}")]

        # Rows
        elif name == "rows_query":
            rows = get_integration("rows")
            if not rows:
                return [TextContent(type="text", text="❌ Rows統合が利用できません")]

            result = rows.ai_query(
                arguments.get("spreadsheet_id"),
                arguments.get("query"),
                arguments.get("sheet_name", "Sheet1")
            )

            return [TextContent(type="text", text=f"クエリ結果:\n{json.dumps(result, indent=2, ensure_ascii=False)}")]

        elif name == "rows_send_data":
            rows = get_integration("rows")
            if not rows:
                return [TextContent(type="text", text="❌ Rows統合が利用できません")]

            result = rows.send_to_rows(
                arguments.get("spreadsheet_id"),
                arguments.get("data"),
                arguments.get("sheet_name", "Sheet1"),
                append=True
            )

            return [TextContent(type="text", text=f"✅ データ送信完了\n{json.dumps(result, indent=2, ensure_ascii=False)}")]

        elif name == "rows_list_spreadsheets":
            rows = get_integration("rows")
            if not rows:
                return [TextContent(type="text", text="❌ Rows統合が利用できません")]

            spreadsheets = rows.list_spreadsheets()
            return [TextContent(type="text", text=f"スプレッドシート一覧 ({len(spreadsheets)}件):\n{json.dumps(spreadsheets, indent=2, ensure_ascii=False)}")]

        # Obsidian
        elif name == "obsidian_create_note":
            obsidian = get_integration("obsidian")
            if not obsidian:
                return [TextContent(type="text", text="❌ Obsidian統合が利用できません")]

            note_path = obsidian.create_note(
                arguments.get("title"),
                arguments.get("content"),
                arguments.get("folder")
            )

            if note_path:
                return [TextContent(type="text", text=f"✅ ノートを作成しました\nパス: {note_path}")]
            else:
                return [TextContent(type="text", text="❌ ノート作成に失敗しました")]

        elif name == "obsidian_search_notes":
            obsidian = get_integration("obsidian")
            if not obsidian:
                return [TextContent(type="text", text="❌ Obsidian統合が利用できません")]

            results = obsidian.search_notes(arguments.get("query"))
            return [TextContent(type="text", text=f"検索結果 ({len(results)}件):\n{json.dumps(results, indent=2, ensure_ascii=False)}")]

        # 画像ストック
        elif name == "image_stock_add":
            image_stock = get_integration("image_stock")
            if not image_stock:
                return [TextContent(type="text", text="❌ 画像ストック統合が利用できません")]

            from pathlib import Path
            result = image_stock.store(
                Path(arguments.get("image_path")),
                prompt=arguments.get("description"),
                category=None
            )

            if result:
                return [TextContent(type="text", text=f"✅ 画像をストックに追加しました\n{json.dumps(result, indent=2, ensure_ascii=False)}")]
            else:
                return [TextContent(type="text", text="❌ 画像追加に失敗しました")]

        elif name == "image_stock_search":
            image_stock = get_integration("image_stock")
            if not image_stock:
                return [TextContent(type="text", text="❌ 画像ストック統合が利用できません")]

            results = image_stock.search(arguments.get("query"), limit=20)
            return [TextContent(type="text", text=f"検索結果 ({len(results)}件):\n{json.dumps(results, indent=2, ensure_ascii=False)}")]

        # 通知
        elif name == "notification_send":
            notification = get_integration("notification")
            if not notification:
                return [TextContent(type="text", text="❌ 通知ハブ統合が利用できません")]

            notification.notify(
                arguments.get("message"),
                arguments.get("priority", "normal")
            )

            return [TextContent(type="text", text=f"✅ 通知を送信しました\nメッセージ: {arguments.get('message')}")]

        # 記憶システム
        elif name == "memory_store":
            memory = get_integration("memory")
            if not memory:
                return [TextContent(type="text", text="❌ 統一記憶システムが利用できません")]

            result = memory.store(
                {"content": arguments.get("content")},
                arguments.get("format_type", "auto")
            )

            return [TextContent(type="text", text=f"✅ 記憶に保存しました\n{json.dumps(result, indent=2, ensure_ascii=False)}")]

        elif name == "memory_recall":
            memory = get_integration("memory")
            if not memory:
                return [TextContent(type="text", text="❌ 統一記憶システムが利用できません")]

            results = memory.recall(
                arguments.get("query"),
                arguments.get("scope", "all"),
                arguments.get("limit", 10)
            )

            return [TextContent(type="text", text=f"検索結果 ({len(results)}件):\n{json.dumps(results, indent=2, ensure_ascii=False)}")]

        # LLMルーティング
        elif name == "llm_chat":
            llm = get_integration("llm_routing")
            if not llm:
                return [TextContent(type="text", text="❌ LLMルーティングが利用できません")]

            result = llm.route(
                task_type=arguments.get("task_type", "conversation"),
                prompt=arguments.get("prompt")
            )

            return [TextContent(type="text", text=f"LLM応答:\nモデル: {result.get('model', 'N/A')}\n応答: {result.get('response', 'N/A')}")]

        # 秘書機能
        elif name == "secretary_morning_routine":
            secretary = get_integration("secretary")
            if not secretary:
                return [TextContent(type="text", text="❌ 秘書機能が利用できません")]

            result = secretary.morning_routine()
            return [TextContent(type="text", text=f"✅ 朝のルーチンを実行しました\n{json.dumps(result, indent=2, ensure_ascii=False)}")]

        elif name == "secretary_noon_routine":
            secretary = get_integration("secretary")
            if not secretary:
                return [TextContent(type="text", text="❌ 秘書機能が利用できません")]

            result = secretary.noon_routine()
            return [TextContent(type="text", text=f"✅ 昼のルーチンを実行しました\n{json.dumps(result, indent=2, ensure_ascii=False)}")]

        elif name == "secretary_evening_routine":
            secretary = get_integration("secretary")
            if not secretary:
                return [TextContent(type="text", text="❌ 秘書機能が利用できません")]

            result = secretary.evening_routine()
            return [TextContent(type="text", text=f"✅ 夜のルーチンを実行しました\n{json.dumps(result, indent=2, ensure_ascii=False)}")]

        # 学習系（Learning System）
        elif name == "learning_record":
            learning_system_url = LEARNING_SYSTEM_URL
            try:
                timeout = timeout_config.get("api_call", 10.0) if timeout_config else 10.0
                response = httpx.post(
                    f"{learning_system_url}/api/record",
                    json={
                        "action": arguments.get("action"),
                        "context": arguments.get("context", {}),
                        "result": arguments.get("result", {})
                    },
                    timeout=timeout
                )
                if response.status_code == 200:
                    return [TextContent(type="text", text=f"✅ 学習システムに記録しました\n{json.dumps(response.json(), indent=2, ensure_ascii=False)}")]
                else:
                    return [TextContent(type="text", text=f"❌ 記録に失敗しました: HTTP {response.status_code}")]
            except Exception as e:
                return [TextContent(type="text", text=f"❌ 学習システム接続エラー: {e}")]

        elif name == "learning_analyze":
            learning_system_url = LEARNING_SYSTEM_URL
            try:
                timeout = timeout_config.get("api_call", 10.0) if timeout_config else 10.0
                response = httpx.get(f"{learning_system_url}/api/analyze", timeout=timeout)
                if response.status_code == 200:
                    return [TextContent(type="text", text=f"分析結果:\n{json.dumps(response.json(), indent=2, ensure_ascii=False)}")]
                else:
                    return [TextContent(type="text", text=f"❌ 分析に失敗しました: HTTP {response.status_code}")]
            except Exception as e:
                return [TextContent(type="text", text=f"❌ 学習システム接続エラー: {e}")]

        elif name == "learning_get_preferences":
            learning_system_url = LEARNING_SYSTEM_URL
            try:
                timeout = timeout_config.get("api_call", 10.0) if timeout_config else 10.0
                response = httpx.get(f"{learning_system_url}/api/preferences", timeout=timeout)
                if response.status_code == 200:
                    return [TextContent(type="text", text=f"学習された好み:\n{json.dumps(response.json(), indent=2, ensure_ascii=False)}")]
                else:
                    return [TextContent(type="text", text=f"❌ 取得に失敗しました: HTTP {response.status_code}")]
            except Exception as e:
                return [TextContent(type="text", text=f"❌ 学習システム接続エラー: {e}")]

        elif name == "learning_get_optimizations":
            learning_system_url = LEARNING_SYSTEM_URL
            try:
                timeout = timeout_config.get("api_call", 10.0) if timeout_config else 10.0
                response = httpx.get(f"{learning_system_url}/api/optimizations", timeout=timeout)
                if response.status_code == 200:
                    return [TextContent(type="text", text=f"最適化提案:\n{json.dumps(response.json(), indent=2, ensure_ascii=False)}")]
                else:
                    return [TextContent(type="text", text=f"❌ 取得に失敗しました: HTTP {response.status_code}")]
            except Exception as e:
                return [TextContent(type="text", text=f"❌ 学習システム接続エラー: {e}")]

        # 人格系（Personality System）
        elif name == "personality_get_persona":
            personality_url = PERSONALITY_SYSTEM_URL
            try:
                timeout = timeout_config.get("api_call", 10.0) if timeout_config else 10.0
                response = httpx.get(f"{personality_url}/api/persona", timeout=timeout)
                if response.status_code == 200:
                    return [TextContent(type="text", text=f"現在の人格:\n{json.dumps(response.json(), indent=2, ensure_ascii=False)}")]
                else:
                    return [TextContent(type="text", text=f"❌ 取得に失敗しました: HTTP {response.status_code}")]
            except Exception as e:
                return [TextContent(type="text", text=f"❌ 人格システム接続エラー: {e}")]

        elif name == "personality_get_prompt":
            personality_url = PERSONALITY_SYSTEM_URL
            try:
                timeout = timeout_config.get("api_call", 10.0) if timeout_config else 10.0
                response = httpx.get(f"{personality_url}/api/persona/prompt", timeout=timeout)
                if response.status_code == 200:
                    data = response.json()
                    return [TextContent(type="text", text=f"人格プロンプト:\n{data.get('prompt', '')}")]
                else:
                    return [TextContent(type="text", text=f"❌ 取得に失敗しました: HTTP {response.status_code}")]
            except Exception as e:
                return [TextContent(type="text", text=f"❌ 人格システム接続エラー: {e}")]

        elif name == "personality_apply":
            personality_url = PERSONALITY_SYSTEM_URL
            try:
                timeout = timeout_config.get("api_call", 10.0) if timeout_config else 10.0
                response = httpx.post(
                    f"{personality_url}/api/persona/apply",
                    json={
                        "prompt": arguments.get("prompt"),
                        "context": arguments.get("context")
                    },
                    timeout=timeout
                )
                if response.status_code == 200:
                    data = response.json()
                    return [TextContent(type="text", text=f"人格適用後のプロンプト:\n{data.get('enhanced_prompt', '')}")]
                else:
                    return [TextContent(type="text", text=f"❌ 適用に失敗しました: HTTP {response.status_code}")]
            except Exception as e:
                return [TextContent(type="text", text=f"❌ 人格システム接続エラー: {e}")]

        elif name == "personality_update":
            personality_url = PERSONALITY_SYSTEM_URL
            try:
                timeout = timeout_config.get("api_call", 10.0) if timeout_config else 10.0
                response = httpx.post(
                    f"{personality_url}/api/persona",
                    json=arguments.get("updates", {}),
                    timeout=timeout
                )
                if response.status_code == 200:
                    return [TextContent(type="text", text=f"✅ 人格プロフィールを更新しました\n{json.dumps(response.json(), indent=2, ensure_ascii=False)}")]
                else:
                    return [TextContent(type="text", text=f"❌ 更新に失敗しました: HTTP {response.status_code}")]
            except Exception as e:
                return [TextContent(type="text", text=f"❌ 人格システム接続エラー: {e}")]

        # 自律系（Autonomy System）
        elif name == "autonomy_add_task":
            autonomy_url = AUTONOMY_SYSTEM_URL
            try:
                timeout = timeout_config.get("api_call", 10.0) if timeout_config else 10.0
                response = httpx.post(
                    f"{autonomy_url}/api/tasks",
                    json={
                        "task_type": arguments.get("task_type"),
                        "priority": arguments.get("priority", "medium"),
                        "condition": arguments.get("condition"),
                        "action": arguments.get("action"),
                        "schedule": arguments.get("schedule")
                    },
                    timeout=timeout
                )
                if response.status_code == 200:
                    return [TextContent(type="text", text=f"✅ 自律タスクを追加しました\n{json.dumps(response.json(), indent=2, ensure_ascii=False)}")]
                else:
                    return [TextContent(type="text", text=f"❌ 追加に失敗しました: HTTP {response.status_code}")]
            except Exception as e:
                return [TextContent(type="text", text=f"❌ 自律システム接続エラー: {e}")]

        elif name == "autonomy_execute_tasks":
            autonomy_url = AUTONOMY_SYSTEM_URL
            try:
                timeout = timeout_config.get("api_call", 30.0) if timeout_config else 30.0
                response = httpx.post(f"{autonomy_url}/api/execute", timeout=timeout)
                if response.status_code == 200:
                    return [TextContent(type="text", text=f"✅ 自律タスクを実行しました\n{json.dumps(response.json(), indent=2, ensure_ascii=False)}")]
                else:
                    return [TextContent(type="text", text=f"❌ 実行に失敗しました: HTTP {response.status_code}")]
            except Exception as e:
                return [TextContent(type="text", text=f"❌ 自律システム接続エラー: {e}")]

        elif name == "autonomy_list_tasks":
            autonomy_url = AUTONOMY_SYSTEM_URL
            try:
                timeout = timeout_config.get("api_call", 10.0) if timeout_config else 10.0
                response = httpx.get(f"{autonomy_url}/api/tasks", timeout=timeout)
                if response.status_code == 200:
                    return [TextContent(type="text", text=f"自律タスク一覧:\n{json.dumps(response.json(), indent=2, ensure_ascii=False)}")]
                else:
                    return [TextContent(type="text", text=f"❌ 取得に失敗しました: HTTP {response.status_code}")]
            except Exception as e:
                return [TextContent(type="text", text=f"❌ 自律システム接続エラー: {e}")]

        elif name == "autonomy_get_level":
            autonomy_url = AUTONOMY_SYSTEM_URL
            try:
                timeout = timeout_config.get("api_call", 10.0) if timeout_config else 10.0
                response = httpx.get(f"{autonomy_url}/api/status", timeout=timeout)
                if response.status_code == 200:
                    data = response.json()
                    return [TextContent(type="text", text=f"自律レベル: {data.get('autonomy_level', 'N/A')}")]
                else:
                    return [TextContent(type="text", text=f"❌ 取得に失敗しました: HTTP {response.status_code}")]
            except Exception as e:
                return [TextContent(type="text", text=f"❌ 自律システム接続エラー: {e}")]

        # VS Code操作
        elif name == "vscode_open_file":
            file_path = arguments.get("file_path")
            line = arguments.get("line")
            try:
                import subprocess
                cmd = ["code", file_path]
                if line:
                    cmd.extend(["--goto", f"{file_path}:{line}"])
                subprocess.Popen(cmd, shell=True)
                return [TextContent(type="text", text=f"✅ VS Codeでファイルを開きました\nパス: {file_path}" + (f"\n行: {line}" if line else ""))]
            except Exception as e:
                return [TextContent(type="text", text=f"❌ VS Code起動エラー: {e}\nVS Codeがインストールされていないか、PATHに追加されていない可能性があります")]

        elif name == "vscode_open_folder":
            folder_path = arguments.get("folder_path")
            try:
                import subprocess
                subprocess.Popen(["code", folder_path], shell=True)
                return [TextContent(type="text", text=f"✅ VS Codeでフォルダを開きました\nパス: {folder_path}")]
            except Exception as e:
                return [TextContent(type="text", text=f"❌ VS Code起動エラー: {e}\nVS Codeがインストールされていないか、PATHに追加されていない可能性があります")]

        elif name == "vscode_execute_command":
            command = arguments.get("command")
            args = arguments.get("args", [])
            try:
                import subprocess
                cmd = ["code", "--command", command] + args
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    return [TextContent(type="text", text=f"✅ VS Codeコマンドを実行しました\nコマンド: {command}\n出力: {result.stdout}")]
                else:
                    return [TextContent(type="text", text=f"⚠️ VS Codeコマンド実行完了（エラーコード: {result.returncode}）\nコマンド: {command}\nエラー: {result.stderr}")]
            except Exception as e:
                return [TextContent(type="text", text=f"❌ VS Codeコマンド実行エラー: {e}")]

        elif name == "vscode_search_files":
            query = arguments.get("query")
            include = arguments.get("include")
            exclude = arguments.get("exclude")
            try:
                import subprocess
                # VS Codeのクイックオープンで検索
                cmd = ["code", "--command", "workbench.action.quickOpen"]
                subprocess.Popen(cmd, shell=True)
                # 実際の検索はVS CodeのUIで行う必要があるため、検索クエリを返す
                search_info = f"検索クエリ: {query}"
                if include:
                    search_info += f"\n対象: {include}"
                if exclude:
                    search_info += f"\n除外: {exclude}"
                return [TextContent(type="text", text=f"✅ VS Codeの検索を開きました\n{search_info}\n\n注意: 実際の検索はVS CodeのUIで行ってください")]
            except Exception as e:
                return [TextContent(type="text", text=f"❌ VS Code検索エラー: {e}")]

        # SearXNG Web検索
        elif name == "web_search":
            searxng = get_integration("searxng")
            if not searxng:
                return [TextContent(type="text", text="❌ SearXNG統合が利用できません")]

            result = searxng.search(
                query=arguments.get("query"),
                max_results=arguments.get("max_results", 10),
                language=arguments.get("language", "ja"),
                categories=arguments.get("categories"),
                time_range=arguments.get("time_range")
            )

            if result.get("error"):
                return [TextContent(type="text", text=f"❌ 検索エラー: {result.get('error')}")]

            # 結果を整形して返す
            results_text = f"🔍 検索結果: {result.get('query', '')}\n"
            results_text += f"総結果数: {result.get('total_results', 0)}件\n"
            results_text += f"表示件数: {result.get('count', 0)}件\n\n"

            for i, item in enumerate(result.get("results", []), 1):
                results_text += f"{i}. {item.get('title', '')}\n"
                results_text += f"   URL: {item.get('url', '')}\n"
                if item.get('content'):
                    content = item.get('content', '')[:200]
                    results_text += f"   概要: {content}...\n"
                results_text += "\n"

            return [TextContent(type="text", text=results_text)]

        elif name == "web_search_simple":
            searxng = get_integration("searxng")
            if not searxng:
                return [TextContent(type="text", text="❌ SearXNG統合が利用できません")]

            results = searxng.search_simple(
                query=arguments.get("query"),
                max_results=arguments.get("max_results", 5)
            )

            if not results:
                return [TextContent(type="text", text="❌ 検索結果が見つかりませんでした")]

        # Brave Search API
        elif name == "brave_search":
            brave = get_integration("brave_search")
            if not brave:
                return [TextContent(type="text", text="❌ Brave Search統合が利用できません")]

            if not brave.is_available():
                return [TextContent(type="text", text="❌ Brave Search APIキーが設定されていません")]

            result = brave.search_with_summary(
                query=arguments.get("query"),
                count=arguments.get("count", 10)
            )

            if not result.get("results"):
                return [TextContent(type="text", text="❌ 検索結果が見つかりませんでした")]

            # 結果を整形して返す
            results_text = f"🔍 Brave Search結果: {result.get('query', '')}\n"
            results_text += f"総結果数: {result.get('total_results', 0)}件\n\n"

            for i, item in enumerate(result.get("results", []), 1):
                results_text += f"{i}. {item.get('title', '')}\n"
                results_text += f"   URL: {item.get('url', '')}\n"
                if item.get('description'):
                    results_text += f"   概要: {item.get('description', '')}\n"
                if item.get('age'):
                    results_text += f"   公開日: {item.get('age', '')}\n"
                results_text += "\n"

            return [TextContent(type="text", text=results_text)]

        elif name == "brave_search_simple":
            brave = get_integration("brave_search")
            if not brave:
                return [TextContent(type="text", text="❌ Brave Search統合が利用できません")]

            if not brave.is_available():
                return [TextContent(type="text", text="❌ Brave Search APIキーが設定されていません")]

            results = brave.search_simple(
                query=arguments.get("query"),
                count=arguments.get("count", 5)
            )

            if not results:
                return [TextContent(type="text", text="❌ 検索結果が見つかりませんでした")]

            results_text = f"🔍 検索結果 ({len(results)}件):\n\n"
            for i, item in enumerate(results, 1):
                results_text += f"{i}. {item.get('title', '')}\n"
                results_text += f"   {item.get('url', '')}\n\n"

            return [TextContent(type="text", text=results_text)]

        # Base AI API
        elif name == "base_ai_chat":
            base_ai = get_integration("base_ai")
            if not base_ai:
                return [TextContent(type="text", text="❌ Base AI統合が利用できません")]

            if not base_ai.is_available():
                return [TextContent(type="text", text="❌ Base AI APIキーが設定されていません")]

            try:
                # use_freeパラメータに応じて統合を再初期化
                use_free = arguments.get("use_free", False)
                from base_ai_integration import BaseAIIntegration
                if use_free != (os.getenv("BASE_AI_USE_FREE", "false").lower() == "true"):
                    base_ai = BaseAIIntegration(use_free=use_free)

                response = base_ai.chat_simple(
                    prompt=arguments.get("prompt"),
                    system_prompt=arguments.get("system_prompt")
                )

                result_text = f"🤖 Base AI レスポンス:\n\n{response}"

                if base_ai.api_key:
                    api_type = "無料のAI" if use_free else "無料"
                    result_text += f"\n\n[使用API: {api_type}]"

                return [TextContent(type="text", text=result_text)]
            except Exception as e:
                logger.error(f"Base AIチャットエラー: {e}", exc_info=True)
                # 統一エラーハンドリングを使用
                if ERROR_HANDLER_AVAILABLE and error_handler:
                    try:
                        manaos_error = error_handler.handle_exception(
                            e,
                            context={"tool_name": "base_ai_chat", "arguments": arguments},
                            user_message="Base AIチャット中にエラーが発生しました"
                        )
                        error_message = manaos_error.user_message or manaos_error.message
                        return [TextContent(type="text", text=f"❌ {error_message}")]
                    except Exception as handler_error:
                        logger.warning(f"エラーハンドラーでの処理中にエラーが発生: {handler_error}")
                return [TextContent(type="text", text=f"❌ Base AIチャットエラー: {str(e)}")]

        # Open WebUI操作
        elif name == "openwebui_create_chat":
            from manaos_unified_mcp_server.error_helper import requests_with_retry, format_error_response
            openwebui_url = os.getenv("OPENWEBUI_URL", "http://localhost:3001")
            api_key = os.getenv("OPENWEBUI_API_KEY", "")

            try:
                headers = {"Content-Type": "application/json"}
                if api_key:
                    headers["Authorization"] = f"Bearer {api_key}"

                data = {
                    "message": arguments.get("message"),
                    "model": arguments.get("model", "qwen2.5-coder-7b-instruct"),
                    "context_length": arguments.get("context_length")
                }

                response = requests_with_retry(
                    "post",
                    f"{openwebui_url}/api/v1/chats/new",
                    json=data,
                    headers=headers,
                    timeout_key="external_service"
                )

                if response.status_code == 200:
                    chat_data = response.json()
                    return [TextContent(type="text", text=f"✅ チャットを作成しました\nチャットID: {chat_data.get('id', 'N/A')}\nモデル: {data.get('model', 'N/A')}")]
                else:
                    return [TextContent(type="text", text=f"❌ チャット作成に失敗しました: {response.text}")]
            except Exception as e:
                logger.error(f"Open WebUIチャット作成エラー: {e}", exc_info=True)
                return format_error_response(e, tool_name="openwebui_create_chat")

        elif name == "openwebui_list_chats":
            from manaos_unified_mcp_server.error_helper import requests_with_retry, format_error_response
            openwebui_url = os.getenv("OPENWEBUI_URL", "http://localhost:3001")
            api_key = os.getenv("OPENWEBUI_API_KEY", "")

            try:
                headers = {}
                if api_key:
                    headers["Authorization"] = f"Bearer {api_key}"

                params = {
                    "limit": arguments.get("limit", 20),
                    "offset": arguments.get("offset", 0)
                }

                response = requests_with_retry(
                    "get",
                    f"{openwebui_url}/api/v1/chats",
                    params=params,
                    headers=headers,
                    timeout_key="external_service"
                )

                if response.status_code == 200:
                    chats = response.json()
                    if isinstance(chats, list):
                        result_text = f"📋 チャット一覧 ({len(chats)}件):\n\n"
                        for i, chat in enumerate(chats[:10], 1):  # 最大10件表示
                            result_text += f"{i}. {chat.get('title', 'Untitled')}\n"
                            result_text += f"   ID: {chat.get('id', 'N/A')}\n"
                            if chat.get('model'):
                                result_text += f"   モデル: {chat.get('model')}\n"
                            result_text += "\n"
                        return [TextContent(type="text", text=result_text)]
                    else:
                        return [TextContent(type="text", text=f"✅ チャット一覧を取得しました\n{json.dumps(chats, indent=2, ensure_ascii=False)}")]
                else:
                    return [TextContent(type="text", text=f"❌ チャット一覧取得に失敗しました: {response.text}")]
            except Exception as e:
                logger.error(f"Open WebUIチャット一覧取得エラー: {e}", exc_info=True)
                return format_error_response(e, tool_name="openwebui_list_chats")

        elif name == "openwebui_send_message":
            from manaos_unified_mcp_server.error_helper import requests_with_retry, format_error_response
            openwebui_url = os.getenv("OPENWEBUI_URL", "http://localhost:3001")
            api_key = os.getenv("OPENWEBUI_API_KEY", "")

            try:
                headers = {"Content-Type": "application/json"}
                if api_key:
                    headers["Authorization"] = f"Bearer {api_key}"

                data = {
                    "message": arguments.get("message")
                }

                response = requests_with_retry(
                    "post",
                    f"{openwebui_url}/api/v1/chats/{arguments.get('chat_id')}/messages",
                    json=data,
                    headers=headers,
                    timeout_key="external_service"
                )

                if response.status_code == 200:
                    return [TextContent(type="text", text=f"✅ メッセージを送信しました\n{response.text}")]
                else:
                    return [TextContent(type="text", text=f"❌ メッセージ送信に失敗しました: {response.text}")]
            except Exception as e:
                logger.error(f"Open WebUIメッセージ送信エラー: {e}", exc_info=True)
                return format_error_response(e, tool_name="openwebui_send_message")

        elif name == "openwebui_get_chat":
            from manaos_unified_mcp_server.error_helper import requests_with_retry, format_error_response
            openwebui_url = os.getenv("OPENWEBUI_URL", "http://localhost:3001")
            api_key = os.getenv("OPENWEBUI_API_KEY", "")

            try:
                headers = {}
                if api_key:
                    headers["Authorization"] = f"Bearer {api_key}"

                response = requests_with_retry(
                    "get",
                    f"{openwebui_url}/api/v1/chats/{arguments.get('chat_id')}",
                    headers=headers,
                    timeout_key="external_service"
                )

                if response.status_code == 200:
                    chat_data = response.json()
                    return [TextContent(type="text", text=f"✅ チャット情報を取得しました\n{json.dumps(chat_data, indent=2, ensure_ascii=False)}")]
                else:
                    return [TextContent(type="text", text=f"❌ チャット情報取得に失敗しました: {response.text}")]
            except Exception as e:
                logger.error(f"Open WebUIチャット情報取得エラー: {e}", exc_info=True)
                return format_error_response(e, tool_name="openwebui_get_chat")

        elif name == "openwebui_list_models":
            from manaos_unified_mcp_server.error_helper import requests_with_retry, format_error_response
            openwebui_url = os.getenv("OPENWEBUI_URL", "http://localhost:3001")
            api_key = os.getenv("OPENWEBUI_API_KEY", "")

            try:
                headers = {}
                if api_key:
                    headers["Authorization"] = f"Bearer {api_key}"

                response = requests_with_retry(
                    "get",
                    f"{openwebui_url}/api/v1/models",
                    headers=headers,
                    timeout_key="external_service"
                )

                if response.status_code == 200:
                    models = response.json()
                    if isinstance(models, list):
                        result_text = f"🤖 利用可能なモデル ({len(models)}件):\n\n"
                        for i, model in enumerate(models, 1):
                            result_text += f"{i}. {model.get('id', 'N/A')}\n"
                            if model.get('name'):
                                result_text += f"   名前: {model.get('name')}\n"
                            result_text += "\n"
                        return [TextContent(type="text", text=result_text)]
                    else:
                        return [TextContent(type="text", text=f"✅ モデル一覧を取得しました\n{json.dumps(models, indent=2, ensure_ascii=False)}")]
                else:
                    return [TextContent(type="text", text=f"❌ モデル一覧取得に失敗しました: {response.text}")]
            except Exception as e:
                logger.error(f"Open WebUIモデル一覧取得エラー: {e}", exc_info=True)
                return format_error_response(e, tool_name="openwebui_list_models")

        elif name == "openwebui_update_settings":
            from manaos_unified_mcp_server.error_helper import requests_with_retry, format_error_response
            openwebui_url = os.getenv("OPENWEBUI_URL", "http://localhost:3001")
            api_key = os.getenv("OPENWEBUI_API_KEY", "")

            try:
                headers = {"Content-Type": "application/json"}
                if api_key:
                    headers["Authorization"] = f"Bearer {api_key}"

                data = {}
                if "enable_signup" in arguments:
                    data["enable_signup"] = arguments.get("enable_signup")
                if "default_model" in arguments:
                    data["default_model"] = arguments.get("default_model")
                if "context_length" in arguments:
                    data["context_length"] = arguments.get("context_length")

                response = requests_with_retry(
                    "put",
                    f"{openwebui_url}/api/v1/settings",
                    json=data,
                    headers=headers,
                    timeout_key="external_service"
                )

                if response.status_code == 200:
                    return [TextContent(type="text", text=f"✅ 設定を更新しました\n{response.text}")]
                else:
                    return [TextContent(type="text", text=f"❌ 設定更新に失敗しました: {response.text}")]
            except Exception as e:
                logger.error(f"Open WebUI設定更新エラー: {e}", exc_info=True)
                return format_error_response(e, tool_name="openwebui_update_settings")

        else:
            return [TextContent(type="text", text=f"❌ 未知のツール: {name}")]

    except Exception as e:
        logger.error(f"ツール実行エラー: {e}", exc_info=True)
        
        # 統一エラーハンドリングを使用
        if ERROR_HANDLER_AVAILABLE and error_handler:
            try:
                manaos_error = error_handler.handle_exception(
                    e,
                    context={"tool_name": name, "arguments": arguments},
                    user_message=f"ツール '{name}' の実行中にエラーが発生しました"
                )
                error_message = manaos_error.user_message or manaos_error.message
                return [TextContent(type="text", text=f"❌ {error_message}")]
            except Exception as handler_error:
                logger.warning(f"エラーハンドラーでの処理中にエラーが発生: {handler_error}")
        
        # フォールバック: 基本的なエラーメッセージ
        return [TextContent(type="text", text=f"❌ エラーが発生しました: {str(e)}")]

async def main():
    """メイン関数"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())
