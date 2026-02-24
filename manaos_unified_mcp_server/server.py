"""
ManaOS統合MCPサーバー
すべてのManaOS機能をCursorから直接使用できる統合MCPサーバー
"""

import asyncio
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Optional, Sequence
from manaos_logger import get_logger, get_service_logger
import io
import httpx

try:
    from manaos_integrations._paths import SEARXNG_PORT
except Exception:  # pragma: no cover
    try:
        from _paths import SEARXNG_PORT  # type: ignore
    except Exception:  # pragma: no cover
        SEARXNG_PORT = int(os.getenv("SEARXNG_PORT", "8080"))

# Windows環境での文字エンコーディング設定
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# パスを追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from autonomy_gates import get_action_class_for_tool, ActionClass, get_usage_key_for_tool

logger = get_service_logger("server")

# 環境変数の読み込み（python-dotenvを使用）
try:
    from dotenv import load_dotenv

    env_path = Path(__file__).parent.parent / ".env"
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
    logger.warning(
        "統一エラーハンドリングモジュールが見つかりません。基本的なエラーハンドリングを使用します。"
    )
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
from _paths import (
    AUTONOMY_SYSTEM_PORT,
    COMFYUI_PORT,
    LEARNING_SYSTEM_PORT,
    PERSONALITY_SYSTEM_PORT,
    PORTAL_INTEGRATION_PORT,
    SECRETARY_SYSTEM_PORT,
    UNIFIED_API_PORT,
)

DEFAULT_COMFYUI_URL = f"http://127.0.0.1:{COMFYUI_PORT}"
DEFAULT_MANAOS_API_URL = f"http://127.0.0.1:{UNIFIED_API_PORT}"
DEFAULT_PORTAL_INTEGRATION_URL = f"http://127.0.0.1:{PORTAL_INTEGRATION_PORT}"
DEFAULT_LEARNING_SYSTEM_URL = f"http://127.0.0.1:{LEARNING_SYSTEM_PORT}"
DEFAULT_PERSONALITY_SYSTEM_URL = f"http://127.0.0.1:{PERSONALITY_SYSTEM_PORT}"
DEFAULT_AUTONOMY_SYSTEM_URL = f"http://127.0.0.1:{AUTONOMY_SYSTEM_PORT}"
DEFAULT_SECRETARY_SYSTEM_URL = f"http://127.0.0.1:{SECRETARY_SYSTEM_PORT}"

COMFYUI_URL = os.getenv("COMFYUI_URL", DEFAULT_COMFYUI_URL)
MANAOS_API_URL = os.getenv("MANAOS_INTEGRATION_API_URL", DEFAULT_MANAOS_API_URL)
PORTAL_INTEGRATION_URL = os.getenv("PORTAL_INTEGRATION_URL", DEFAULT_PORTAL_INTEGRATION_URL)
ROOT = Path(__file__).resolve().parent.parent
LEARNING_SYSTEM_URL = os.getenv("LEARNING_SYSTEM_URL", DEFAULT_LEARNING_SYSTEM_URL)
PERSONALITY_SYSTEM_URL = os.getenv("PERSONALITY_SYSTEM_URL", DEFAULT_PERSONALITY_SYSTEM_URL)
AUTONOMY_SYSTEM_URL = os.getenv("AUTONOMY_SYSTEM_URL", DEFAULT_AUTONOMY_SYSTEM_URL)
SECRETARY_SYSTEM_URL = os.getenv("SECRETARY_SYSTEM_URL", DEFAULT_SECRETARY_SYSTEM_URL)


# 危険度の高いツール（VS Code操作など）の有効/無効


def _vscode_tools_enabled() -> bool:
    return os.getenv("MANAOS_ENABLE_VSCODE_TOOLS", "false").strip().lower() in (
        "1",
        "true",
        "yes",
        "y",
        "on",
    )


# Autonomy System 連携ユーティリティ


def _autonomy_check_tool(tool_name: str, confirm_token: str | None = None) -> tuple[bool, str]:
    """
    自律ゲートにツール実行可否を問い合わせる。
    Autonomy System が落ちている場合は許可（ログのみ）。
    """
    try:
        timeout = timeout_config.get("api_call", 5.0) if TIMEOUT_CONFIG_AVAILABLE else 5.0
        payload = {"tool_name": tool_name}
        if confirm_token:
            payload["confirm_token"] = confirm_token
        resp = httpx.post(
            f"{AUTONOMY_SYSTEM_URL}/api/check-tool",
            json=payload,
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        return bool(data.get("allowed", True)), data.get("reason", "")
    except Exception as e:
        logger.debug(f"Autonomy check-tool エラー（許可で継続）: {e}")
        return True, ""


def _autonomy_record_cost(tool_name: str) -> None:
    """
    C3 ツール実行後にコスト使用量を Autonomy System に記録。
    Autonomy System が落ちている場合は無視。
    """
    usage_key = get_usage_key_for_tool(tool_name)
    if not usage_key:
        return
    try:
        timeout = timeout_config.get("api_call", 5.0) if TIMEOUT_CONFIG_AVAILABLE else 5.0
        httpx.post(
            f"{AUTONOMY_SYSTEM_URL}/api/record-cost",
            json={"usage_key": usage_key, "period": "per_hour", "amount": 1},
            timeout=timeout,
        )
    except Exception as e:
        logger.debug(f"Autonomy record-cost エラー（無視）: {e}")


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
                vault_path = os.getenv(
                    "OBSIDIAN_VAULT_PATH",
                    str(Path.home() / "Documents" / "Obsidian Vault"),
                )
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

                searxng_url = os.getenv(
                    "SEARXNG_BASE_URL",
                    f"http://127.0.0.1:{SEARXNG_PORT}",
                )
                _integrations[name] = SearXNGIntegration(base_url=searxng_url)
            elif name == "brave_search":
                from brave_search_integration import BraveSearchIntegration

                _integrations[name] = BraveSearchIntegration()
            elif name == "civitai":
                from civitai_integration import CivitAIIntegration

                # APIキーはCivitAIIntegration内でも環境変数から取得できる
                _integrations[name] = CivitAIIntegration(api_key=os.getenv("CIVITAI_API_KEY"))
            elif name == "base_ai":
                from base_ai_integration import BaseAIIntegration

                use_free = os.getenv("BASE_AI_USE_FREE", "false").lower() == "true"
                _integrations[name] = BaseAIIntegration(use_free=use_free)
            elif name == "device_orchestrator":
                from device_orchestrator import DeviceOrchestrator

                config_path = os.getenv(
                    "DEVICE_ORCHESTRATOR_CONFIG", "device_orchestrator_config.json"
                )
                _integrations[name] = DeviceOrchestrator(config_path=config_path)
        except ImportError as e:
            logger.warning(f"{name}統合のインポートに失敗: {e}")
            return None
    return _integrations.get(name)


# MCPサーバーの作成
server = Server("manaos-unified")

# MCP_DOMAIN による分割: media | productivity | ai | devices | moltbot | (空=全ツール)
MCP_DOMAIN = (os.getenv("MCP_DOMAIN") or "").strip().lower()
DOMAIN_TOOLS = {
    "media": [
        "svi_generate_video",
        "svi_extend_video",
        "svi_get_queue_status",
        "ltx2_generate_video",
        "ltx2_infinity_generate_video",
        "ltx2_infinity_list_templates",
        "ltx2_infinity_storage_stats",
        "comfyui_generate_image",
        "generate_sd_prompt",
        "civitai_get_favorites",
        "civitai_download_favorites",
        "civitai_get_images",
        "civitai_get_image_details",
        "civitai_get_creators",
        "image_stock_add",
        "image_stock_search",
    ],
    "productivity": [
        "google_drive_upload",
        "google_drive_list_files",
        "rows_query",
        "rows_send_data",
        "rows_list_spreadsheets",
        "obsidian_create_note",
        "obsidian_search_notes",
        "notification_send",
    ],
    "ai": [
        "memory_store",
        "memory_recall",
        "llm_chat",
        "secretary_morning_routine",
        "secretary_noon_routine",
        "secretary_evening_routine",
        "learning_record",
        "learning_analyze",
        "learning_get_preferences",
        "learning_get_optimizations",
        "phase1_run_off_3rounds",
        "phase1_run_on_rounds",
        "phase1_save_run",
        "phase1_aggregate",
        "phase1_compare_on_off",
        "phase1_phase2_full_run",
        "phase1_low_sat_archive",
        "phase1_low_sat_history_view",
        "phase1_weekly_report",
        "phase2_backfill_memos",
        "phase2_get_memos",
        "phase2_memo_summary",
        "phase2_auto_cleanup",
        "personality_get_persona",
        "personality_get_prompt",
        "personality_apply",
        "personality_update",
        "autonomy_add_task",
        "autonomy_execute_tasks",
        "autonomy_list_tasks",
        "autonomy_get_level",
        "web_search",
        "web_search_simple",
        "brave_search",
        "brave_search_simple",
        "base_ai_chat",
        "openwebui_create_chat",
        "openwebui_list_chats",
        "openwebui_send_message",
        "openwebui_get_chat",
        "openwebui_list_models",
        "openwebui_update_settings",
        "research_quick",
        "research_status",
        "voice_health",
        "voice_synthesize",
        "n8n_list_workflows",
        "n8n_execute_workflow",
        "secretary_file_organize",
        "github_search",
        "github_commits",
        "cache_stats",
        "performance_stats",
    ],
    "devices": [
        "device_discover",
        "device_get_status",
        "device_get_health",
        "device_get_resources",
        "device_get_alerts",
        "pixel7_execute",
        "pixel7_get_resources",
        "pixel7_screenshot",
        "pixel7_get_apps",
        "pixel7_push_file",
        "pixel7_pull_file",
        "mothership_get_resources",
        "mothership_execute",
        "x280_get_resources",
        "x280_execute",
        "konoha_health",
        "nanokvm_console_url",
        "nanokvm_health",
        "pixel7_tts",
        "pixel7_transcribe",
    ],
    "moltbot": ["moltbot_submit_plan", "moltbot_get_result", "moltbot_health"],
    "file_secretary": ["file_secretary_inbox_status", "file_secretary_organize"],
    "research": ["research_quick", "research_status"],
}


def _filter_tools_by_domain(tools_list: list) -> list:
    """MCP_DOMAIN が設定されていれば該当ツールのみ返す"""
    if not MCP_DOMAIN or MCP_DOMAIN not in DOMAIN_TOOLS:
        return tools_list
    allowed = set(DOMAIN_TOOLS[MCP_DOMAIN])
    return [t for t in tools_list if t.name in allowed]


@server.list_tools()
async def list_tools() -> list[Tool]:
    """利用可能なツール一覧を返す"""
    tools = []

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
                        "prompt": {"type": "string", "description": "プロンプト（日本語可、必須）"},
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
                        "prompt": {"type": "string", "description": "延長部分のプロンプト（必須）"},
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
        ]
    )

    # ========================================
    # LTX-2 / LTX-2 Infinity
    # ========================================
    tools.extend(
        [
            Tool(
                name="ltx2_generate_video",
                description="LTX-2で動画を生成します（Unified API経由）",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "string", "description": "プロンプト（必須）"},
                        "workflow": {"type": "string", "description": "ワークフローJSONパス（任意）"},
                        "image": {"type": "string", "description": "開始画像（ComfyUI input内のファイル名、任意）"},
                        "timeout": {"type": "number", "description": "待機タイムアウト秒（任意）", "default": 600},
                    },
                    "required": ["prompt"],
                },
            ),
            Tool(
                name="ltx2_infinity_generate_video",
                description="LTX-2 Infinity（segments回の反復生成、Unified API経由）",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "string", "description": "プロンプト（必須）"},
                        "segments": {"type": "integer", "description": "反復回数（デフォルト: 1）", "default": 1},
                        "workflow": {"type": "string", "description": "ワークフローJSONパス（任意）"},
                        "image": {"type": "string", "description": "開始画像（任意）"},
                        "timeout_per_segment": {"type": "number", "default": 600},
                        "positive_suffix": {"type": "string", "description": "追記ポジティブタグ（任意）"},
                        "negative_suffix": {"type": "string", "description": "追記ネガティブタグ（任意）"},
                    },
                    "required": ["prompt"],
                },
            ),
            Tool(
                name="ltx2_infinity_list_templates",
                description="LTX-2 Infinityのテンプレート一覧を取得します（Unified API経由）",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="ltx2_infinity_storage_stats",
                description="LTX-2 Infinityのストレージ統計を取得します（Unified API経由）",
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
                description="ComfyUIで画像を生成します（複数LoRA対応）",
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
                            "description": "ステップ数（デフォルト: 70）",
                            "default": 70,
                        },
                        "cfg_scale": {
                            "type": "number",
                            "description": "CFGスケール（デフォルト: 8.5）",
                            "default": 8.5,
                        },
                        "model": {"type": "string", "description": "使用するモデル名"},
                        "loras": {
                            "type": "array",
                            "description": 'LoRAのリスト [{"name": "lora_name", "strength": 0.8}, ...]',
                            "items": {"type": "object"},
                        },
                        "sampler": {
                            "type": "string",
                            "description": "サンプラー（デフォルト: euler_ancestral）",
                            "default": "euler_ancestral",
                        },
                        "scheduler": {
                            "type": "string",
                            "description": "スケジューラー（デフォルト: karras）",
                            "default": "karras",
                        },
                        "seed": {
                            "type": "integer",
                            "description": "シード（-1の場合はランダム）",
                            "default": -1,
                        },
                    },
                    "required": ["prompt"],
                },
            ),
            Tool(
                name="generate_sd_prompt",
                description="日本語の説明からStable Diffusion用の英語プロンプトを生成します（Ollama llama3-uncensored使用）",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "description": {
                            "type": "string",
                            "description": "画像の日本語説明（必須）",
                        },
                        "model": {
                            "type": "string",
                            "description": "Ollamaモデル名（デフォルト: llama3-uncensored）",
                            "default": "llama3-uncensored",
                        },
                        "temperature": {
                            "type": "number",
                            "description": "温度 0.0-1.0（デフォルト: 0.9）",
                            "default": 0.9,
                        },
                        "with_negative": {
                            "type": "boolean",
                            "description": "デフォルトのネガティブプロンプトも返す",
                            "default": False,
                        },
                    },
                    "required": ["description"],
                },
            ),
        ]
    )

    # ========================================
    # CivitAI
    # ========================================
    tools.extend(
        [
            Tool(
                name="civitai_get_favorites",
                description="CivitAIのお気に入りモデル一覧を取得します",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "取得数（デフォルト: 100）",
                            "default": 100,
                        },
                        "model_type": {
                            "type": "string",
                            "description": "モデルタイプ（Checkpoint, LORA等）",
                        },
                    },
                },
            ),
            Tool(
                name="civitai_download_favorites",
                description="CivitAIのお気に入りモデルを自動ダウンロードします",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "auto": {
                            "type": "boolean",
                            "description": "自動モード（確認なし）",
                            "default": False,
                        },
                        "model_type": {
                            "type": "string",
                            "description": "モデルタイプ（Checkpoint, LORA等）",
                        },
                    },
                },
            ),
            Tool(
                name="civitai_get_images",
                description="CivitAIで画像を取得します（プロンプト情報含む）",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "取得数（最大200、デフォルト: 20）",
                            "default": 20,
                        },
                        "model_id": {"type": "integer", "description": "モデルIDでフィルタ"},
                        "model_version_id": {
                            "type": "integer",
                            "description": "モデルバージョンIDでフィルタ",
                        },
                        "username": {"type": "string", "description": "ユーザー名でフィルタ"},
                        "nsfw": {"type": "boolean", "description": "NSFWフラグ"},
                        "sort": {
                            "type": "string",
                            "description": "ソート方法（Most Reactions, Most Comments, Newest）",
                            "default": "Most Reactions",
                        },
                        "period": {
                            "type": "string",
                            "description": "期間（AllTime, Year, Month, Week, Day）",
                            "default": "AllTime",
                        },
                        "page": {
                            "type": "integer",
                            "description": "ページ番号（デフォルト: 1）",
                            "default": 1,
                        },
                    },
                },
            ),
            Tool(
                name="civitai_get_image_details",
                description="CivitAIで画像の詳細情報を取得します（プロンプト情報含む）",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "image_id": {"type": "integer", "description": "画像ID（必須）"}
                    },
                    "required": ["image_id"],
                },
            ),
            Tool(
                name="civitai_get_creators",
                description="CivitAIでクリエイター一覧を取得します",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "username": {"type": "string", "description": "ユーザー名でフィルタ"},
                        "limit": {
                            "type": "integer",
                            "description": "取得数（デフォルト: 20）",
                            "default": 20,
                        },
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
                        "folder_id": {"type": "string", "description": "フォルダID（オプション）"},
                        "confirm_token": {
                            "type": "string",
                            "description": "自律ゲート用のConfirm Token（C3/C4が必要な場合）",
                        },
                    },
                    "required": ["file_path"],
                },
            ),
            Tool(
                name="google_drive_list_files",
                description="Google Driveのファイル一覧を取得します",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "folder_id": {"type": "string", "description": "フォルダID（オプション）"},
                        "query": {"type": "string", "description": "検索クエリ（オプション）"},
                    },
                },
            ),
        ]
    )

    # ========================================
    # Rows（スプレッドシート）
    # ========================================
    tools.extend(
        [
            Tool(
                name="rows_query",
                description="RowsスプレッドシートにAI自然言語クエリを実行します",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "spreadsheet_id": {
                            "type": "string",
                            "description": "スプレッドシートID（必須）",
                        },
                        "query": {"type": "string", "description": "自然言語クエリ（必須）"},
                        "sheet_name": {
                            "type": "string",
                            "description": "シート名（デフォルト: Sheet1）",
                            "default": "Sheet1",
                        },
                    },
                    "required": ["spreadsheet_id", "query"],
                },
            ),
            Tool(
                name="rows_send_data",
                description="Rowsスプレッドシートにデータを送信します",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "spreadsheet_id": {
                            "type": "string",
                            "description": "スプレッドシートID（必須）",
                        },
                        "data": {"type": "array", "description": "送信するデータ（必須）"},
                        "sheet_name": {
                            "type": "string",
                            "description": "シート名（デフォルト: Sheet1）",
                            "default": "Sheet1",
                        },
                    },
                    "required": ["spreadsheet_id", "data"],
                },
            ),
            Tool(
                name="rows_list_spreadsheets",
                description="Rowsスプレッドシート一覧を取得します",
                inputSchema={"type": "object", "properties": {}},
            ),
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
                        "title": {"type": "string", "description": "ノートのタイトル（必須）"},
                        "content": {"type": "string", "description": "ノートの内容（必須）"},
                        "folder": {"type": "string", "description": "フォルダ（オプション）"},
                    },
                    "required": ["title", "content"],
                },
            ),
            Tool(
                name="obsidian_search_notes",
                description="Obsidianでノートを検索します",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "検索クエリ（必須）"}
                    },
                    "required": ["query"],
                },
            ),
        ]
    )

    # ========================================
    # 画像ストック
    # ========================================
    tools.extend(
        [
            Tool(
                name="image_stock_add",
                description="画像をストックに追加します",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "image_path": {"type": "string", "description": "画像のパス（必須）"},
                        "tags": {
                            "type": "array",
                            "description": "タグ（オプション）",
                            "items": {"type": "string"},
                        },
                        "description": {"type": "string", "description": "説明（オプション）"},
                    },
                    "required": ["image_path"],
                },
            ),
            Tool(
                name="image_stock_search",
                description="画像ストックから画像を検索します",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "検索クエリ（必須）"}
                    },
                    "required": ["query"],
                },
            ),
        ]
    )

    # ========================================
    # 通知
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
                            "description": "優先度（critical/important/normal/low、デフォルト: normal）",
                            "default": "normal",
                        },
                    },
                    "required": ["message"],
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
                description="記憶に情報を保存します",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "description": "保存する内容（必須）"},
                        "format_type": {
                            "type": "string",
                            "description": "フォーマットタイプ（conversation/memo/research/system、デフォルト: auto）",
                            "default": "auto",
                        },
                    },
                    "required": ["content"],
                },
            ),
            Tool(
                name="memory_recall",
                description="記憶から情報を検索します",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "検索クエリ（必須）"},
                        "scope": {
                            "type": "string",
                            "description": "スコープ（all/today/week/month、デフォルト: all）",
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
    # LLMルーティング
    # ========================================
    tools.extend(
        [
            Tool(
                name="llm_chat",
                description="LLMとチャットします（最適なモデルを自動選択）",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "string", "description": "プロンプト（必須）"},
                        "task_type": {
                            "type": "string",
                            "description": "タスクタイプ（conversation/code/analysis/generation、デフォルト: conversation）",
                            "default": "conversation",
                        },
                    },
                    "required": ["prompt"],
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
            Tool(
                name="secretary_file_organize",
                description="秘書のファイル整理 Plan を送信します（MoltBot 経由）。path と intent（list_only/read_only）、user_hint を指定。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "対象パス（例: ~/Downloads）", "default": "~/Downloads"},
                        "intent": {"type": "string", "description": "list_only または read_only", "default": "list_only"},
                        "user_hint": {"type": "string", "description": "ユーザーからのヒント（例: Downloads 一覧）"},
                    },
                },
            ),
        ]
    )

    # ========================================
    # 学習系（Learning System）
    # ========================================
    tools.extend(
        [
            Tool(
                name="learning_record",
                description="学習システムに使用パターンを記録します",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "description": "アクション名（必須）"},
                        "context": {"type": "object", "description": "コンテキスト情報"},
                        "result": {"type": "object", "description": "結果情報"},
                    },
                    "required": ["action"],
                },
            ),
            Tool(
                name="learning_analyze",
                description="学習システムでパターンを分析します",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="learning_get_preferences",
                description="学習された好みを取得します",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="learning_get_optimizations",
                description="最適化提案を取得します",
                inputSchema={"type": "object", "properties": {}},
            ),
        ]
    )

    # ========================================
    # Phase1 自己観察実験
    # ========================================
    tools.extend(
        [
            Tool(
                name="phase1_run_off_3rounds",
                description="Phase1 OFF 3往復テストを実行。unified_api_server が PHASE1_REFLECTION=off で起動している必要あり。API (127.0.0.1:9502) に接続してログを採取し、集計結果を返す。",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="phase1_run_on_rounds",
                description="Phase1 ON N往復テストを実行。unified_api_server が PHASE1_REFLECTION=on で起動している必要あり。デフォルト15往復。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "rounds": {
                            "type": "integer",
                            "description": "往復数（デフォルト: 15）",
                            "default": 15,
                        }
                    },
                },
            ),
            Tool(
                name="phase1_run_extended",
                description="Phase1 拡張実験（30往復）。condition=on/off, rounds=30。API起動後実行。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "condition": {
                            "type": "string",
                            "description": "on または off",
                            "enum": ["on", "off"],
                        },
                        "rounds": {"type": "integer", "description": "往復数", "default": 30},
                    },
                },
            ),
            Tool(
                name="phase1_save_run",
                description="現在の phase1 ログを phase1_runs/ にスナップショット保存する。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "condition": {
                            "type": "string",
                            "description": "on または off",
                            "enum": ["on", "off"],
                        },
                        "tag": {"type": "string", "description": "任意タグ（例: round3, round15）"},
                    },
                    "required": ["condition"],
                },
            ),
            Tool(
                name="phase1_aggregate",
                description="現在の phase1 ログを集計し、継続率・テーマ再訪・満足度を返す。",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="phase1_compare_on_off",
                description="phase1_runs/ 内の ON/OFF スナップショットを比較して差分を表示する。",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="phase1_phase2_full_run",
                description="Phase1/Phase2 を一気に全部実行（集計・低満足度・バックフィル・メモ概要・アーカイブ・履歴表示）。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "save": {
                            "type": "boolean",
                            "description": "先にログをスナップショット保存する",
                            "default": False,
                        },
                        "condition": {
                            "type": "string",
                            "description": "save 時の条件（on/off）",
                            "enum": ["on", "off"],
                            "default": "on",
                        },
                        "tag": {
                            "type": "string",
                            "description": "save 時のタグ",
                            "default": "full",
                        },
                        "history_tail": {
                            "type": "integer",
                            "description": "履歴表示の直近件数",
                            "default": 10,
                        },
                    },
                },
            ),
            Tool(
                name="phase1_run_multi_thread",
                description="複数スレッドで異なるテーマの会話を実行し、同一テーマ再訪を計測する。",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="phase1_low_satisfaction",
                description="振り返りログから満足度1〜2の行を抽出し、理由を集約して表示する。",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="phase1_low_sat_archive",
                description="低満足度の件数と理由トップ5を phase1_low_sat_history.jsonl に1行追記する。",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="phase1_low_sat_history_view",
                description="低満足度履歴（phase1_low_sat_history.jsonl）の直近N件を一覧表示する。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "tail": {
                            "type": "integer",
                            "description": "表示する直近件数",
                            "default": 10,
                        },
                    },
                },
            ),
            Tool(
                name="phase1_weekly_report",
                description="Phase1 週次レポート（集計＋低満足度を一括実行）。オプションでログをスナップショット保存してから集計。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "save": {
                            "type": "boolean",
                            "description": "先に phase1_save_run でログを保存する",
                            "default": False,
                        },
                        "condition": {
                            "type": "string",
                            "description": "save 時の条件（on/off）",
                            "enum": ["on", "off"],
                            "default": "on",
                        },
                        "tag": {
                            "type": "string",
                            "description": "save 時のタグ（例: weekly）",
                            "default": "weekly",
                        },
                        "phase2": {
                            "type": "boolean",
                            "description": "Phase2 メモ概要を末尾に追加",
                            "default": False,
                        },
                    },
                },
            ),
            Tool(
                name="phase2_backfill_memos",
                description="phase1 ログから振り返りメモを phase2_reflection_memos.jsonl に投入する。",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="phase2_get_memos",
                description="テーマIDで振り返りメモを取得する（第三層 PoC）。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "theme_id": {
                            "type": "string",
                            "description": "テーマID（例: 今日/気/明日 または python/プ/ミ）",
                        },
                    },
                    "required": ["theme_id"],
                },
            ),
            Tool(
                name="phase2_memo_summary",
                description="Phase2 メモのテーマ別件数・満足度平均を一覧表示する。",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="phase2_auto_cleanup",
                description="Phase2 メモを自動整理（dedup→ZIP退避→.bak削除）する。",
                inputSchema={"type": "object", "properties": {}},
            ),
        ]
    )

    # ========================================
    # 人格系（Personality System）
    # ========================================
    tools.extend(
        [
            Tool(
                name="personality_get_persona",
                description="現在の人格プロフィールを取得します",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="personality_get_prompt",
                description="人格プロンプトを取得します",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="personality_apply",
                description="プロンプトに人格を適用します",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "string", "description": "ベースプロンプト（必須）"},
                        "context": {
                            "type": "string",
                            "description": "コンテキスト（report/conversation）",
                        },
                    },
                    "required": ["prompt"],
                },
            ),
            Tool(
                name="personality_update",
                description="人格プロフィールを更新します",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "updates": {"type": "object", "description": "更新内容（必須）"}
                    },
                    "required": ["updates"],
                },
            ),
        ]
    )

    # ========================================
    # 自律系（Autonomy System）
    # ========================================
    tools.extend(
        [
            Tool(
                name="autonomy_add_task",
                description="自律タスクを追加します",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "task_type": {"type": "string", "description": "タスクタイプ（必須）"},
                        "priority": {
                            "type": "string",
                            "description": "優先度（high/medium/low、デフォルト: medium）",
                            "default": "medium",
                        },
                        "condition": {"type": "object", "description": "実行条件（必須）"},
                        "action": {"type": "object", "description": "実行アクション（必須）"},
                        "schedule": {
                            "type": "string",
                            "description": "スケジュール（cron形式、オプション）",
                        },
                    },
                    "required": ["task_type", "condition", "action"],
                },
            ),
            Tool(
                name="autonomy_execute_tasks",
                description="条件をチェックして自律タスクを実行します",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="autonomy_list_tasks",
                description="自律タスク一覧を取得します",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="autonomy_get_level",
                description="現在の自律レベルを取得します",
                inputSchema={"type": "object", "properties": {}},
            ),
        ]
    )

    # ========================================
    # Device Orchestrator（デバイス監視）
    # ========================================
    tools.extend(
        [
            Tool(
                name="device_discover",
                description="全デバイス（母艦・このは・X280・Pixel7）を検出し、オンライン状態を更新します",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="device_get_status",
                description="デバイスオーケストレーターの状態（全デバイス・キュー・統計）を取得します",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="device_get_health",
                description="Portal API経由で特定デバイスの詳細ヘルス（CPU/メモリ/ディスク等）を取得します",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "device_name": {
                            "type": "string",
                            "description": "デバイス名（例: mothership, konoha, x280）",
                        },
                    },
                    "required": ["device_name"],
                },
            ),
            Tool(
                name="device_get_resources",
                description="Portal API経由で全デバイスのリソース使用状況を取得します",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="device_get_alerts",
                description="Portal API経由で全デバイスのアラートを取得します",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="pixel7_execute",
                description="Pixel 7（USB接続・ADBブリッジ経由）でAndroidコマンドを実行します",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "実行するAndroid shellコマンド（例: getprop ro.product.model, dumpsys battery）",
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "タイムアウト秒（省略時60）",
                            "default": 60,
                        },
                    },
                    "required": ["command"],
                },
            ),
            Tool(
                name="pixel7_get_resources",
                description="Pixel 7のリソース情報（メモリ・バッテリー・システム情報）を取得します",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="pixel7_screenshot",
                description="Pixel 7の画面のスクリーンショットを取得し、保存パスを返します",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="pixel7_get_apps",
                description="Pixel 7にインストールされているアプリ（パッケージ名）一覧を取得します",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="pixel7_push_file",
                description="母艦のファイルをPixel 7に送ります（ADB push）",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "local_path": {"type": "string", "description": "母艦上のファイルパス"},
                        "remote_path": {"type": "string", "description": "Pixel 7上の保存先（例: /sdcard/Download/）"},
                    },
                    "required": ["local_path", "remote_path"],
                },
            ),
            Tool(
                name="pixel7_pull_file",
                description="Pixel 7のファイルを母艦に取得します（ADB pull）",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "remote_path": {"type": "string", "description": "Pixel 7上のファイルパス（例: /sdcard/DCIM/xxx.jpg）"},
                        "local_path": {"type": "string", "description": "母艦上の保存先パス"},
                    },
                    "required": ["remote_path", "local_path"],
                },
            ),
            Tool(
                name="mothership_get_resources",
                description="母艦（このPC）のリソース情報（CPU・メモリ・ディスク）を取得します。統合API経由。",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="mothership_execute",
                description="母艦（このPC）でコマンドを実行します。統合API経由。PowerShell/CMD 等。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "実行するコマンド（例: dir, Get-Date）"},
                        "timeout": {"type": "integer", "description": "タイムアウト秒（省略時60）", "default": 60},
                    },
                    "required": ["command"],
                },
            ),
            Tool(
                name="x280_get_resources",
                description="X280（ThinkPad）のリソース情報（CPU・メモリ・ディスク）を取得します。統合API経由。",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="x280_execute",
                description="X280 でコマンドを実行します（PowerShell/CMD）。統合API経由。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "実行するコマンド"},
                        "timeout": {"type": "integer", "description": "タイムアウト秒（省略時60）", "default": 60},
                    },
                    "required": ["command"],
                },
            ),
            Tool(
                name="konoha_health",
                description="Konoha（このはサーバー 5106）のヘルスチェック。統合API経由。",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="nanokvm_console_url",
                description="NanoKVM のログイン画面 URL を取得。ManaOS からブラウザで開く・Browser MCP でスナップショット取得に使う。統合API経由。",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="nanokvm_health",
                description="NanoKVM の到達性チェック（母艦から）。統合API経由。",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="pixel7_tts",
                description="Pixel 7 で音声再生（TTS）。テキストをサーバーで合成し、端末に転送して再生。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "読み上げるテキスト（必須）"},
                        "speed": {"type": "number", "description": "速度", "default": 1.0},
                    },
                    "required": ["text"],
                },
            ),
            Tool(
                name="pixel7_transcribe",
                description="Pixel 7 上の音声ファイルを文字起こし。remote_path で録音ファイルを指定（例: /sdcard/Download/rec.wav）。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "remote_path": {
                            "type": "string",
                            "description": "Pixel 7 上のファイルパス（必須）。例: /sdcard/Download/recording.wav",
                        },
                        "sample_rate": {"type": "integer", "description": "サンプリングレート", "default": 16000},
                    },
                    "required": ["remote_path"],
                },
            ),
        ]
    )

    # ========================================
    # MoltBot（Plan 実行・監査）
    # ========================================
    tools.extend(
        [
            Tool(
                name="moltbot_submit_plan",
                description="MoltBot に Plan を送信して実行します。統合API経由。intent=list_only で指定パスの一覧、read_only で読み取りのみ。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "intent": {
                            "type": "string",
                            "description": "list_only（一覧取得）または read_only（読み取りのみ）",
                            "default": "list_only",
                        },
                        "path": {
                            "type": "string",
                            "description": "対象パス（例: ~/Downloads）",
                            "default": "~/Downloads",
                        },
                        "user_hint": {
                            "type": "string",
                            "description": "ユーザーからの追加ヒント",
                        },
                    },
                },
            ),
            Tool(
                name="moltbot_get_result",
                description="MoltBot Plan の実行結果を取得します",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "plan_id": {"type": "string", "description": "Plan ID（必須）"},
                    },
                    "required": ["plan_id"],
                },
            ),
            Tool(
                name="moltbot_health",
                description="MoltBot Gateway のヘルスチェック",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="file_secretary_inbox_status",
                description="File Secretary の INBOX 状況を取得します。統合API経由。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "source": {"type": "string", "description": "ソースでフィルタ"},
                        "status": {"type": "string", "description": "ステータスでフィルタ"},
                        "days": {"type": "integer", "description": "何日分（デフォルト1）", "default": 1},
                    },
                },
            ),
            Tool(
                name="file_secretary_organize",
                description="File Secretary でファイル整理を実行します。targets に file_id のリストを指定。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "targets": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "整理対象の file_id リスト",
                        },
                        "thread_ref": {"type": "string"},
                        "user": {"type": "string"},
                        "auto_tag": {"type": "boolean", "default": True},
                        "auto_alias": {"type": "boolean", "default": True},
                    },
                    "required": ["targets"],
                },
            ),
            Tool(
                name="research_quick",
                description="Step Deep Research でクイック調査を実行します（作成→実行を一括）。統合API経由。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "調査クエリ（必須）"},
                        "use_cache": {"type": "boolean", "description": "キャッシュ利用", "default": True},
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="research_status",
                description="Step Deep Research のジョブ状態を取得します。job_id を指定。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "job_id": {"type": "string", "description": "ジョブID（必須）"},
                    },
                    "required": ["job_id"],
                },
            ),
            Tool(
                name="voice_health",
                description="音声機能（STT/TTS）の稼働状態を取得します。統合API経由。",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="voice_synthesize",
                description="テキストを音声に変換（TTS）します。統合API経由。text を指定。音声バイナリはAPIから取得。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "読み上げるテキスト（必須）"},
                        "speaker_id": {"type": "string"},
                        "speed": {"type": "number", "default": 1.0},
                    },
                    "required": ["text"],
                },
            ),
            Tool(
                name="n8n_list_workflows",
                description="n8n のワークフロー一覧を取得します。統合API経由。N8N_BASE_URL と N8N_API_KEY 要。",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="n8n_execute_workflow",
                description="n8n のワークフローを実行します。workflow_id を指定。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "workflow_id": {"type": "string", "description": "ワークフローID（必須）"},
                        "data": {"type": "object", "description": "実行時に渡すデータ（任意）"},
                    },
                    "required": ["workflow_id"],
                },
            ),
            Tool(
                name="github_search",
                description="GitHub でリポジトリを検索します。統合API経由。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "検索クエリ（必須）"},
                        "limit": {"type": "integer", "description": "取得件数", "default": 10},
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="github_commits",
                description="GitHub リポジトリの直近コミットを取得します。owner と repo を指定。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string", "description": "オーナー（必須）"},
                        "repo": {"type": "string", "description": "リポジトリ名（必須）"},
                        "limit": {"type": "integer", "description": "取得件数", "default": 10},
                    },
                    "required": ["owner", "repo"],
                },
            ),
            Tool(
                name="cache_stats",
                description="統合API のキャッシュ統計を取得します。",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="performance_stats",
                description="統合API のパフォーマンス統計を取得します。",
                inputSchema={"type": "object", "properties": {}},
            ),
        ]
    )

    # ========================================
    # VS Code操作
    # ========================================
    if _vscode_tools_enabled():
        tools.extend(
            [
                Tool(
                    name="vscode_open_file",
                    description="VS Codeでファイルを開きます",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_path": {"type": "string", "description": "ファイルパス（必須）"},
                            "line": {"type": "integer", "description": "行番号（オプション）"},
                        },
                        "required": ["file_path"],
                    },
                ),
                Tool(
                    name="vscode_open_folder",
                    description="VS Codeでフォルダを開きます",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "folder_path": {"type": "string", "description": "フォルダパス（必須）"}
                        },
                        "required": ["folder_path"],
                    },
                ),
                Tool(
                    name="vscode_execute_command",
                    description="VS Codeでコマンドを実行します（危険: 明示的に有効化された場合のみ表示）",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "command": {"type": "string", "description": "コマンド（必須）"},
                            "args": {
                                "type": "array",
                                "description": "コマンド引数（オプション）",
                                "items": {"type": "string"},
                            },
                        },
                        "required": ["command"],
                    },
                ),
                Tool(
                    name="vscode_search_files",
                    description="VS Codeでファイルを検索します",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "検索クエリ（必須）"},
                            "include": {
                                "type": "string",
                                "description": "検索対象ファイル（例: *.py）",
                            },
                            "exclude": {
                                "type": "string",
                                "description": "除外ファイル（例: node_modules/**）",
                            },
                        },
                        "required": ["query"],
                    },
                ),
            ]
        )

    # ========================================
    # SearXNG Web検索
    # ========================================
    tools.extend(
        [
            Tool(
                name="web_search",
                description="SearXNGを使用してWeb検索を実行します（実質無制限の検索が可能）",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "検索クエリ（必須）"},
                        "max_results": {
                            "type": "integer",
                            "description": "最大結果数（デフォルト: 10）",
                            "default": 10,
                        },
                        "language": {
                            "type": "string",
                            "description": "言語コード（デフォルト: ja）",
                            "default": "ja",
                        },
                        "categories": {
                            "type": "array",
                            "description": '検索カテゴリ（例: ["general", "images"]）',
                            "items": {"type": "string"},
                        },
                        "time_range": {
                            "type": "string",
                            "description": "時間範囲フィルタ（day/week/month/year）",
                        },
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="web_search_simple",
                description="シンプルなWeb検索（結果のみ返す）",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "検索クエリ（必須）"},
                        "max_results": {
                            "type": "integer",
                            "description": "最大結果数（デフォルト: 5）",
                            "default": 5,
                        },
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="brave_search",
                description="Brave Search APIを使用してWeb検索を実行します（高品質な検索結果）",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "検索クエリ（必須）"},
                        "count": {
                            "type": "integer",
                            "description": "取得件数（デフォルト: 10、最大: 20）",
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
                        "freshness": {
                            "type": "string",
                            "description": "時間範囲フィルタ（pd: 過去1日、pw: 過去1週間、pm: 過去1ヶ月、py: 過去1年）",
                        },
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="brave_search_simple",
                description="Brave Search APIを使用したシンプルな検索（結果のみ返す）",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "検索クエリ（必須）"},
                        "count": {
                            "type": "integer",
                            "description": "取得件数（デフォルト: 5）",
                            "default": 5,
                        },
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="base_ai_chat",
                description="Base AI APIを使用してチャットを実行します（無料のAI APIも利用可能）",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "string", "description": "ユーザープロンプト（必須）"},
                        "system_prompt": {
                            "type": "string",
                            "description": "システムプロンプト（オプション）",
                        },
                        "use_free": {
                            "type": "boolean",
                            "description": "無料のAI APIを使用するか（デフォルト: false）",
                            "default": False,
                        },
                        "temperature": {
                            "type": "number",
                            "description": "温度パラメータ（デフォルト: 0.7）",
                            "default": 0.7,
                        },
                        "max_tokens": {
                            "type": "integer",
                            "description": "最大トークン数（オプション）",
                        },
                    },
                    "required": ["prompt"],
                },
            ),
        ]
    )

    return _filter_tools_by_domain(tools)


def _tool_json(payload: dict) -> list[TextContent]:
    return [TextContent(type="text", text=json.dumps(payload, indent=2, ensure_ascii=False))]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    args = arguments or {}

    confirm_token = args.get("confirm_token")
    allowed, reason = _autonomy_check_tool(name, confirm_token=confirm_token)
    if not allowed:
        return _tool_json({"error": "autonomy_blocked", "reason": reason})

    try:
        if name == "ltx2_generate_video":
            prompt = str(args.get("prompt", "")).strip()
            if not prompt:
                return _tool_json({"error": "prompt is required"})

            payload = {
                "prompt": prompt,
                "workflow": args.get("workflow"),
                "image": args.get("image"),
                "timeout": args.get("timeout", 600),
            }
            timeout = timeout_config.get("api_call", 30.0) if TIMEOUT_CONFIG_AVAILABLE else 30.0
            resp = httpx.post(f"{MANAOS_API_URL.rstrip('/')}/api/ltx2/generate", json=payload, timeout=timeout)
            resp.raise_for_status()
            result = resp.json()

        elif name == "ltx2_infinity_generate_video":
            prompt = str(args.get("prompt", "")).strip()
            if not prompt:
                return _tool_json({"error": "prompt is required"})

            payload = {
                "prompt": prompt,
                "segments": args.get("segments", 1),
                "workflow": args.get("workflow"),
                "image": args.get("image"),
                "timeout_per_segment": args.get("timeout_per_segment", 600),
                "positive_suffix": args.get("positive_suffix"),
                "negative_suffix": args.get("negative_suffix"),
            }
            timeout = timeout_config.get("api_call", 30.0) if TIMEOUT_CONFIG_AVAILABLE else 30.0
            resp = httpx.post(
                f"{MANAOS_API_URL.rstrip('/')}/api/ltx2-infinity/generate",
                json=payload,
                timeout=timeout,
            )
            resp.raise_for_status()
            result = resp.json()

        elif name == "ltx2_infinity_list_templates":
            timeout = timeout_config.get("api_call", 10.0) if TIMEOUT_CONFIG_AVAILABLE else 10.0
            resp = httpx.get(f"{MANAOS_API_URL.rstrip('/')}/api/ltx2-infinity/templates", timeout=timeout)
            resp.raise_for_status()
            result = resp.json()

        elif name == "ltx2_infinity_storage_stats":
            timeout = timeout_config.get("api_call", 10.0) if TIMEOUT_CONFIG_AVAILABLE else 10.0
            resp = httpx.get(f"{MANAOS_API_URL.rstrip('/')}/api/ltx2-infinity/storage", timeout=timeout)
            resp.raise_for_status()
            result = resp.json()

        if name == "google_drive_upload":
            file_path = str(args.get("file_path", "")).strip()
            if not file_path:
                return _tool_json({"error": "file_path is required"})

            integration = get_integration("google_drive")
            if not integration or not integration.is_available():
                return _tool_json({"error": "google_drive_integration_unavailable"})

            file_id = integration.upload_file(
                file_path,
                folder_id=args.get("folder_id"),
            )
            if not file_id:
                return _tool_json({"error": "upload_failed"})

            result = {"success": True, "file_id": file_id}

        elif name == "google_drive_list_files":
            integration = get_integration("google_drive")
            if not integration or not integration.is_available():
                return _tool_json({"error": "google_drive_integration_unavailable"})

            files = integration.list_files(folder_id=args.get("folder_id"))
            result = {"success": True, "files": files}

        elif name == "rows_query":
            integration = get_integration("rows")
            if not integration or not integration.is_available():
                return _tool_json({"error": "rows_integration_unavailable"})

            spreadsheet_id = str(args.get("spreadsheet_id", "")).strip()
            query = str(args.get("query", "")).strip()
            if not spreadsheet_id or not query:
                return _tool_json({"error": "spreadsheet_id and query are required"})

            context = {}
            sheet_name = args.get("sheet_name")
            if sheet_name:
                context["sheet_name"] = sheet_name

            response = integration.ai_query(spreadsheet_id, query, context=context or None)
            result = {"success": True, "response": response}

        elif name == "rows_send_data":
            integration = get_integration("rows")
            if not integration or not integration.is_available():
                return _tool_json({"error": "rows_integration_unavailable"})

            spreadsheet_id = str(args.get("spreadsheet_id", "")).strip()
            data = args.get("data")
            if not spreadsheet_id or data is None:
                return _tool_json({"error": "spreadsheet_id and data are required"})

            sheet_name = args.get("sheet_name") or "Sheet1"
            response = integration.send_to_rows(spreadsheet_id, data, sheet_name=sheet_name, append=True)
            result = {"success": True, "response": response}

        elif name == "rows_list_spreadsheets":
            integration = get_integration("rows")
            if not integration or not integration.is_available():
                return _tool_json({"error": "rows_integration_unavailable"})

            limit = args.get("limit")
            try:
                limit_int = int(limit) if limit is not None else 50
            except (TypeError, ValueError):
                limit_int = 50

            sheets = integration.list_spreadsheets(limit=limit_int)
            if sheets is None:
                last_error = getattr(integration, "last_error", None)
                # Rows API は権限不足/キー不正時に 404 を返すケースがあるため、次アクションを明示する
                hint = {
                    "success": False,
                    "error": "rows_api_error",
                    "details": last_error,
                    "next_steps": [
                        "Rows の Workspace Settings で API Key を作成し直し、manaos_integrations/.env の ROWS_API_KEY を更新してください",
                        "そのAPI Key のユーザーが対象Workspaceの Owner/Admin か、最低でも対象Spreadsheetへ Viewer/Editor 権限があるか確認してください",
                        "更新後、MCPサーバ（productivity）を再起動して再実行してください",
                    ],
                }
                return _tool_json(hint)

            result = {"success": True, "spreadsheets": sheets}

        elif name == "obsidian_create_note":
            integration = get_integration("obsidian")
            if not integration or not integration.is_available():
                return _tool_json({"error": "obsidian_integration_unavailable"})

            title = str(args.get("title", "")).strip()
            content = str(args.get("content", "")).strip()
            if not title or not content:
                return _tool_json({"error": "title and content are required"})

            folder = args.get("folder")
            note_path = integration.create_note(title=title, content=content, folder=folder)
            if not note_path:
                return _tool_json({"error": "note_create_failed"})

            result = {"success": True, "note_path": str(note_path)}

        elif name == "obsidian_search_notes":
            integration = get_integration("obsidian")
            if not integration or not integration.is_available():
                return _tool_json({"error": "obsidian_integration_unavailable"})

            query = str(args.get("query", "")).strip()
            if not query:
                return _tool_json({"error": "query is required"})

            matches = integration.search_notes(query)
            result = {"success": True, "notes": [str(path) for path in matches]}

        elif name == "notification_send":
            integration = get_integration("notification")
            if not integration:
                return _tool_json({"error": "notification_integration_unavailable"})

            message = str(args.get("message", "")).strip()
            if not message:
                return _tool_json({"error": "message is required"})

            priority = str(args.get("priority", "normal")).strip() or "normal"
            response = integration.notify(message=message, priority=priority)
            result = {"success": True, "response": response}

        else:
            return _tool_json({"error": "tool_not_implemented", "tool": name})

        _autonomy_record_cost(name)
        return _tool_json(result)

    except Exception as e:
        logger.error(f"Tool call failed ({name}): {e}", exc_info=True)
        return _tool_json({"error": str(e)})


async def main() -> None:
    """MCP stdioエントリポイント。"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())