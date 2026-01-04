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

# 環境変数から設定を読み込み
COMFYUI_URL = os.getenv("COMFYUI_URL", "http://localhost:8188")
MANAOS_API_URL = os.getenv("MANAOS_INTEGRATION_API_URL", "http://localhost:9500")

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
        
        else:
            return [TextContent(type="text", text=f"❌ 未知のツール: {name}")]
    
    except Exception as e:
        logger.error(f"ツール実行エラー: {e}", exc_info=True)
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

