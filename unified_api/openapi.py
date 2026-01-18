from __future__ import annotations

import os
from typing import Any, Dict


def build_openapi_spec() -> Dict[str, Any]:
    """
    OpenAPI仕様（Open WebUI External Tools向け）。

    NOTE: 互換のため、URLは従来どおり host.docker.internal をデフォルトにする。
    """
    base_url = os.getenv("MANAOS_OPENAPI_SERVER_URL", "http://host.docker.internal:9500").rstrip("/")

    return {
        "openapi": "3.0.0",
        "info": {
            "title": "manaOS統合API",
            "description": "manaOS統合システムへのアクセス（画像生成、ファイル管理、ノート作成など）",
            "version": "1.0.0",
        },
        "servers": [{"url": base_url, "description": "ローカルサーバー"}],
        "paths": {
            "/api/comfyui/generate": {
                "post": {
                    "summary": "ComfyUIで画像を生成",
                    "description": "ComfyUIを使って画像を生成します",
                    "operationId": "generateImageComfyUI",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "prompt": {
                                            "type": "string",
                                            "description": "画像生成のプロンプト",
                                        },
                                        "width": {
                                            "type": "integer",
                                            "description": "画像の幅（デフォルト: 512）",
                                            "default": 512,
                                        },
                                        "height": {
                                            "type": "integer",
                                            "description": "画像の高さ（デフォルト: 512）",
                                            "default": 512,
                                        },
                                        "steps": {
                                            "type": "integer",
                                            "description": "生成ステップ数（デフォルト: 20）",
                                            "default": 20,
                                        },
                                    },
                                    "required": ["prompt"],
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "成功",
                            "content": {"application/json": {"schema": {"type": "object"}}},
                        }
                    },
                }
            },
            "/api/google_drive/upload": {
                "post": {
                    "summary": "Google Driveにファイルをアップロード",
                    "description": "ファイルをGoogle Driveにアップロードします",
                    "operationId": "uploadToGoogleDrive",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "file_path": {
                                            "type": "string",
                                            "description": "アップロードするファイルのパス",
                                        },
                                        "folder_id": {
                                            "type": "string",
                                            "description": "アップロード先のフォルダID（オプション）",
                                        },
                                    },
                                    "required": ["file_path"],
                                }
                            }
                        },
                    },
                    "responses": {"200": {"description": "成功"}},
                }
            },
            "/api/obsidian/create": {
                "post": {
                    "summary": "Obsidianにノートを作成",
                    "description": "Obsidianにノートを作成します",
                    "operationId": "createObsidianNote",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "title": {
                                            "type": "string",
                                            "description": "ノートのタイトル",
                                        },
                                        "content": {
                                            "type": "string",
                                            "description": "ノートの内容",
                                        },
                                        "tags": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                            "description": "タグのリスト",
                                        },
                                    },
                                    "required": ["title", "content"],
                                }
                            }
                        },
                    },
                    "responses": {"200": {"description": "成功"}},
                }
            },
            "/api/civitai/search": {
                "get": {
                    "summary": "CivitAIでモデルを検索",
                    "description": "CivitAIでモデルを検索します",
                    "operationId": "searchCivitAIModels",
                    "parameters": [
                        {
                            "name": "query",
                            "in": "query",
                            "required": True,
                            "schema": {"type": "string"},
                            "description": "検索クエリ",
                        },
                        {
                            "name": "limit",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "integer", "default": 10},
                            "description": "結果の最大数",
                        },
                    ],
                    "responses": {"200": {"description": "成功"}},
                }
            },
        },
    }

