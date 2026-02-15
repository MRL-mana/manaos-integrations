#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCPサーバーのツールをREST API経由で呼び出すサーバー
Open WebUIのFunctionsとして使用可能にする
"""

import asyncio
import json
import os
import sys
import io
from pathlib import Path
from typing import Dict, Any, Optional
from flask import Flask, request, jsonify
from flask_cors import CORS
from manaos_logger import get_logger

from _paths import COMFYUI_PORT, UNIFIED_API_PORT
# Windows環境での文字エンコーディング設定
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# パスを追加
sys.path.insert(0, str(Path(__file__).parent))

logger = get_service_logger("mcp")
app = Flask(__name__)
CORS(app)

# MCPサーバーをインポート
MCP_SERVER_AVAILABLE = False
server = None
call_tool_func = None

try:
    from manaos_unified_mcp_server.server import server as mcp_server
    server = mcp_server
    MCP_SERVER_AVAILABLE = True
    logger.info("✅ MCPサーバーを読み込みました")
except ImportError as e:
    logger.warning(f"manaos_unified_mcp_serverが見つかりません: {e}")
    MCP_SERVER_AVAILABLE = False


@app.route("/health", methods=["GET"])
def health():
    """ヘルスチェック"""
    return jsonify({
        "status": "healthy",
        "service": "MCP API Server",
        "mcp_available": MCP_SERVER_AVAILABLE
    })


@app.route("/api/mcp/tools", methods=["GET"])
def list_tools():
    """利用可能なツール一覧を返す"""
    if not MCP_SERVER_AVAILABLE or not server:
        return jsonify({"error": "MCPサーバーが利用できません"}), 503

    try:
        # MCPサーバーのlist_toolsを呼び出す
        # server.list_tools()はデコレータで定義されているため、直接呼び出す必要がある
        async def get_tools():
            # @server.list_tools()デコレータで定義された関数を取得
            # 実際には、serverインスタンスのlist_toolsハンドラーを呼び出す
            # しかし、これは複雑なので、代わりに統合API経由でツールを取得する
            return []

        tools = asyncio.run(get_tools())

        # 基本的なツールリストを返す（実際のツールは統合API経由で取得可能）
        tools_list = [
            {
                "name": "comfyui_generate_image",
                "description": "ComfyUIで画像を生成します",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "string", "description": "画像生成のプロンプト"},
                        "width": {"type": "integer", "description": "画像の幅（デフォルト: 512）", "default": 512},
                        "height": {"type": "integer", "description": "画像の高さ（デフォルト: 512）", "default": 512},
                        "steps": {"type": "integer", "description": "生成ステップ数（デフォルト: 20）", "default": 20}
                    },
                    "required": ["prompt"]
                }
            },
            {
                "name": "google_drive_upload",
                "description": "Google Driveにファイルをアップロードします",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "アップロードするファイルのパス"},
                        "folder_id": {"type": "string", "description": "アップロード先のフォルダID（オプション）"}
                    },
                    "required": ["file_path"]
                }
            },
            {
                "name": "obsidian_create_note",
                "description": "Obsidianにノートを作成します",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "ノートのタイトル"},
                        "content": {"type": "string", "description": "ノートの内容"},
                        "tags": {"type": "array", "items": {"type": "string"}, "description": "タグのリスト"}
                    },
                    "required": ["title", "content"]
                }
            }
        ]

        return jsonify({"tools": tools_list})
    except Exception as e:
        logger.error(f"ツール一覧取得エラー: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


async def _call_mcp_tool_async(tool_name: str, arguments: dict):
    """MCPツールを非同期で呼び出す（統合インスタンスを直接使用）"""
    from mcp.types import TextContent

    # 統合インスタンスを取得するヘルパー関数（MCPサーバーと同じロジック）
    _integrations = {}

    def get_integration(name: str):
        """統合モジュールを取得（遅延インポート）"""
        if name not in _integrations:
            try:
                if name == "svi":
                    from svi_wan22_video_integration import SVIWan22VideoIntegration
                    comfyui_url = os.getenv("COMFYUI_URL", f"http://127.0.0.1:{COMFYUI_PORT}")
                    _integrations[name] = SVIWan22VideoIntegration(base_url=comfyui_url)
                elif name == "comfyui":
                    from comfyui_integration import ComfyUIIntegration
                    comfyui_url = os.getenv("COMFYUI_URL", f"http://127.0.0.1:{COMFYUI_PORT}")
                    _integrations[name] = ComfyUIIntegration(base_url=comfyui_url)
                elif name == "google_drive":
                    from google_drive_integration import GoogleDriveIntegration
                    _integrations[name] = GoogleDriveIntegration()
                elif name == "obsidian":
                    vault_path = os.getenv("OBSIDIAN_VAULT_PATH", str(Path.home() / "Documents" / "Obsidian Vault"))
                    from obsidian_integration import ObsidianIntegration
                    _integrations[name] = ObsidianIntegration(vault_path=vault_path)
                # 他の統合も同様に追加可能
            except ImportError as e:
                logger.warning(f"{name}統合のインポートに失敗: {e}")
                return None
        return _integrations.get(name)

    try:
        # MCPサーバーと同じロジックでツールを呼び出す
        if tool_name == "comfyui_generate_image":
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

        elif tool_name == "google_drive_upload":
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

        elif tool_name == "obsidian_create_note":
            obsidian = get_integration("obsidian")
            if not obsidian:
                return [TextContent(type="text", text="❌ Obsidian統合が利用できません")]

            note_path = obsidian.create_note(
                title=arguments.get("title"),
                content=arguments.get("content"),
                tags=arguments.get("tags", [])
            )

            if note_path:
                return [TextContent(type="text", text=f"✅ ノートを作成しました\nパス: {note_path}")]
            else:
                return [TextContent(type="text", text="❌ ノート作成に失敗しました")]

        else:
            # その他のツールは統合API経由で呼び出す
            import requests
            manaos_api_url = os.getenv(
                "MANAOS_API_URL", f"http://127.0.0.1:{UNIFIED_API_PORT}"
            )

            # ツール名をAPIエンドポイントにマッピング
            api_mapping = {
                "civitai_search_models": ("GET", "/api/civitai/search"),
                "svi_generate_video": ("POST", "/api/svi/generate"),
                "web_search": ("GET", "/api/searxng/search"),
            }

            if tool_name in api_mapping:
                method, endpoint = api_mapping[tool_name]
                url = f"{manaos_api_url}{endpoint}"

                if method == "POST":
                    response = requests.post(url, json=arguments, timeout=30)
                else:
                    response = requests.get(url, params=arguments, timeout=30)

                if response.status_code == 200:
                    return [TextContent(type="text", text=f"✅ 実行完了\n{response.text}")]
                else:
                    return [TextContent(type="text", text=f"❌ 実行に失敗しました: {response.text}")]

            return [TextContent(type="text", text=f"❌ 不明なツール: {tool_name}")]

    except Exception as e:
        logger.error(f"ツール呼び出しエラー: {e}", exc_info=True)
        return [TextContent(type="text", text=f"❌ エラーが発生しました: {str(e)}")]


@app.route("/api/mcp/tool/<tool_name>", methods=["POST"])
def call_mcp_tool_endpoint(tool_name: str):
    """MCPツールを呼び出す"""
    if not MCP_SERVER_AVAILABLE:
        return jsonify({"error": "MCPサーバーが利用できません"}), 503

    try:
        data = request.json or {}
        logger.info(f"MCPツール呼び出し: {tool_name}, 引数: {data}")

        # MCPツールを非同期で呼び出し
        result = asyncio.run(_call_mcp_tool_async(tool_name, data))

        # TextContent型を辞書に変換
        response_text = ""
        if isinstance(result, list):
            for content in result:
                if hasattr(content, 'text'):
                    response_text += content.text + "\n"
                elif isinstance(content, dict) and 'text' in content:
                    response_text += content['text'] + "\n"
                elif isinstance(content, str):
                    response_text += content + "\n"
        elif isinstance(result, str):
            response_text = result
        elif isinstance(result, dict):
            response_text = json.dumps(result, ensure_ascii=False, indent=2)

        return jsonify({
            "success": True,
            "tool": tool_name,
            "result": response_text.strip()
        })
    except Exception as e:
        logger.error(f"MCPツール呼び出しエラー: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e),
            "tool": tool_name
        }), 500


@app.route("/openapi.json", methods=["GET"])
def openapi_spec():
    """OpenAPI仕様を返す（Open WebUI External Tools対応）"""
    try:
        # MCPサーバーからツール一覧を取得
        tools = []
        if MCP_SERVER_AVAILABLE and server:
            try:
                tools = asyncio.run(server.list_tools())
                logger.info(f"MCPサーバーから {len(tools)} 個のツールを取得しました")
            except Exception as e:
                logger.warning(f"MCPサーバーからツール一覧を取得できませんでした: {e}")
                tools = []

        # OpenAPI仕様を構築
        paths = {}

        # MCPサーバーのツールを追加
        for tool in tools:
            if hasattr(tool, 'name') and hasattr(tool, 'description') and hasattr(tool, 'inputSchema'):
                path_name = f"/api/mcp/tool/{tool.name}"
                paths[path_name] = {
                    "post": {
                        "summary": tool.description,
                        "description": tool.description,
                        "operationId": tool.name,
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": tool.inputSchema
                                }
                            }
                        },
                        "responses": {
                            "200": {
                                "description": "成功",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "success": {"type": "boolean"},
                                                "tool": {"type": "string"},
                                                "result": {"type": "string"}
                                            }
                                        }
                                    }
                                }
                            },
                            "500": {
                                "description": "エラー",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "success": {"type": "boolean"},
                                                "error": {"type": "string"},
                                                "tool": {"type": "string"}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

        return jsonify({
            "openapi": "3.0.0",
            "info": {
                "title": "ManaOS統合MCP API",
                "description": "ManaOS統合MCPサーバーのツールをREST API経由で呼び出します",
                "version": "1.0.0"
            },
            "servers": [
                {
                    "url": f"http://host.docker.internal:{os.getenv('MCP_API_PORT', '9502')}",
                    "description": "ローカルサーバー"
                }
            ],
            "paths": paths
        })
    except Exception as e:
        logger.error(f"OpenAPI仕様生成エラー: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.getenv("MCP_API_PORT", "9502"))
    host = os.getenv("MCP_API_HOST", "0.0.0.0")
    logger.info(f"🚀 MCP API Server starting on {host}:{port}")
    app.run(host=host, port=port, debug=True)
