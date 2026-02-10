from __future__ import annotations

import os
from typing import Any, Dict


def build_openapi_spec() -> Dict[str, Any]:
    """
    OpenAPI仕様（Open WebUI External Tools向け）。

    NOTE: 互換のため、URLは従来どおり host.docker.internal をデフォルトにする。
    """
    base_url = os.getenv("MANAOS_OPENAPI_SERVER_URL", "http://host.docker.internal:9500").rstrip(
        "/"
    )

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
            "/api/sd-prompt/generate": {
                "post": {
                    "summary": "SD用プロンプトを生成",
                    "description": "日本語の説明からStable Diffusion用の英語プロンプトを生成します（Ollama）",
                    "operationId": "generateSDPrompt",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "description": {
                                            "type": "string",
                                            "description": "画像の日本語説明",
                                        },
                                        "prompt": {
                                            "type": "string",
                                            "description": "descriptionの別名",
                                        },
                                        "model": {
                                            "type": "string",
                                            "description": "Ollamaモデル（デフォルト: llama3-uncensored）",
                                            "default": "llama3-uncensored",
                                        },
                                        "temperature": {
                                            "type": "number",
                                            "description": "温度 0.0-1.0",
                                            "default": 0.9,
                                        },
                                        "with_negative": {
                                            "type": "boolean",
                                            "description": "ネガティブプロンプトも返す",
                                            "default": False,
                                        },
                                    },
                                    "required": [],
                                }
                            }
                        },
                    },
                    "responses": {"200": {"description": "成功"}},
                }
            },
            "/api/devices/status": {
                "get": {
                    "summary": "デバイス状態を取得",
                    "description": "オーケストレーター経由で全デバイス（母艦・このは・X280・Pixel 7等）の状態を取得します",
                    "operationId": "getDevicesStatus",
                    "responses": {"200": {"description": "成功（devices, stats, queue_length 等）"}, "503": {"description": "オーケストレーター取得失敗"}},
                }
            },
            "/api/pixel7/resources": {
                "get": {
                    "summary": "Pixel 7 リソース",
                    "description": "Pixel 7 のバッテリー・メモリ等（ブリッジ 5122 にプロキシ）",
                    "operationId": "getPixel7Resources",
                    "responses": {"200": {"description": "成功"}, "503": {"description": "ブリッジ未接続"}},
                }
            },
            "/api/pixel7/execute": {
                "post": {
                    "summary": "Pixel 7 でコマンド実行",
                    "description": "Pixel 7 ブリッジ経由で Android コマンドを実行します",
                    "operationId": "executePixel7Command",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {"command": {"type": "string", "description": "実行する shell コマンド"}},
                                    "required": ["command"],
                                }
                            }
                        },
                    },
                    "responses": {"200": {"description": "成功"}, "503": {"description": "ブリッジ未接続"}},
                }
            },
            "/api/pixel7/screenshot": {
                "get": {
                    "summary": "Pixel 7 スクリーンショット",
                    "description": "Pixel 7 の画面をキャプチャし、保存パスを返します",
                    "operationId": "getPixel7Screenshot",
                    "responses": {"200": {"description": "成功（path 含む）"}, "503": {"description": "ブリッジ未接続"}},
                }
            },
            "/api/pixel7/apps": {
                "get": {
                    "summary": "Pixel 7 アプリ一覧",
                    "description": "Pixel 7 にインストールされているアプリ（パッケージ名）一覧",
                    "operationId": "getPixel7Apps",
                    "responses": {"200": {"description": "成功"}, "503": {"description": "ブリッジ未接続"}},
                }
            },
            "/api/pixel7/tts": {
                "post": {
                    "summary": "Pixel 7 で音声再生（TTS）",
                    "description": "テキストをサーバーで合成し、Pixel 7 に転送して再生。音声統合・ブリッジ要。",
                    "operationId": "pixel7Tts",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {"text": {"type": "string"}, "speed": {"type": "number"}},
                                    "required": ["text"],
                                }
                            }
                        },
                    },
                    "responses": {"200": {"description": "成功"}, "503": {"description": "TTS/ブリッジ未利用"}},
                }
            },
            "/api/pixel7/transcribe": {
                "post": {
                    "summary": "Pixel 7 の音声ファイルを文字起こし",
                    "description": "remote_path で指定した端末上のファイルを取得し、STTで文字起こし。",
                    "operationId": "pixel7Transcribe",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "remote_path": {"type": "string", "description": "例: /sdcard/Download/rec.wav"},
                                        "sample_rate": {"type": "integer", "default": 16000},
                                    },
                                    "required": ["remote_path"],
                                }
                            }
                        },
                    },
                    "responses": {"200": {"description": "成功（text）"}, "503": {"description": "STT/ブリッジ未利用"}},
                }
            },
            "/api/konoha/health": {
                "get": {
                    "summary": "Konoha ヘルス",
                    "description": "Konoha（このはサーバー 5106）の稼働確認",
                    "operationId": "getKonohaHealth",
                    "responses": {"200": {"description": "成功"}, "503": {"description": "未接続"}},
                }
            },
            "/api/nanokvm/console_url": {
                "get": {
                    "summary": "NanoKVM コンソールURL",
                    "description": "NanoKVM ログイン画面の URL。ManaOS からブラウザで開く・Browser MCP でスナップショット取得に利用",
                    "operationId": "getNanokvmConsoleUrl",
                    "responses": {"200": {"description": "成功（url, message）"}, "503": {"description": "未設定"}},
                }
            },
            "/api/nanokvm/health": {
                "get": {
                    "summary": "NanoKVM 到達性",
                    "description": "NanoKVM（母艦接続 KVM）の到達性チェック",
                    "operationId": "getNanokvmHealth",
                    "responses": {"200": {"description": "成功（reachable）"}, "503": {"description": "未到達"}},
                }
            },
            "/api/file-secretary/health": {
                "get": {
                    "summary": "File Secretary ヘルス",
                    "description": "File Secretary の稼働確認（FILE_SECRETARY_URL にプロキシ）",
                    "operationId": "getFileSecretaryHealth",
                    "responses": {"200": {"description": "成功"}, "503": {"description": "未接続"}},
                }
            },
            "/api/file-secretary/inbox/status": {
                "get": {
                    "summary": "File Secretary INBOX 状況",
                    "description": "INBOX 状況取得。クエリ: source, status, days",
                    "operationId": "getFileSecretaryInboxStatus",
                    "responses": {"200": {"description": "成功"}, "503": {"description": "未接続"}},
                }
            },
            "/api/file-secretary/files/organize": {
                "post": {
                    "summary": "File Secretary ファイル整理",
                    "description": "ファイル整理実行。body: targets, thread_ref, user, auto_tag, auto_alias",
                    "operationId": "postFileSecretaryOrganize",
                    "requestBody": {"content": {"application/json": {"schema": {"type": "object"}}}},
                    "responses": {"200": {"description": "成功"}, "503": {"description": "未接続"}},
                }
            },
            "/api/x280/resources": {
                "get": {
                    "summary": "X280 リソース",
                    "description": "X280（ThinkPad）の CPU・メモリ・ディスクを取得します（5120 にプロキシ）",
                    "operationId": "getX280Resources",
                    "responses": {"200": {"description": "成功"}, "503": {"description": "X280 未接続"}},
                }
            },
            "/api/x280/execute": {
                "post": {
                    "summary": "X280 でコマンド実行",
                    "description": "X280 で PowerShell/CMD コマンドを実行します",
                    "operationId": "executeX280Command",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "command": {"type": "string"},
                                        "timeout": {"type": "integer"},
                                    },
                                    "required": ["command"],
                                }
                            }
                        },
                    },
                    "responses": {"200": {"description": "成功"}, "503": {"description": "X280 未接続"}},
                }
            },
            "/api/mothership/resources": {
                "get": {
                    "summary": "母艦リソース",
                    "description": "母艦（このAPIが動いているPC）の CPU・メモリ・ディスクを取得します（psutil 要）",
                    "operationId": "getMothershipResources",
                    "responses": {"200": {"description": "成功"}, "503": {"description": "psutil 未導入"}},
                }
            },
            "/api/mothership/execute": {
                "post": {
                    "summary": "母艦でコマンド実行",
                    "description": "母艦（ローカルPC）でシェルコマンドを実行します。タイムアウト付き。",
                    "operationId": "executeMothershipCommand",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "command": {"type": "string", "description": "実行するコマンド"},
                                        "timeout": {"type": "integer", "description": "タイムアウト秒（最大300）"},
                                    },
                                    "required": ["command"],
                                }
                            }
                        },
                    },
                    "responses": {"200": {"description": "成功（stdout, stderr, returncode）"}, "408": {"description": "タイムアウト"}},
                }
            },
            "/api/research/quick": {
                "post": {
                    "summary": "Step Deep Research クイック調査",
                    "description": "調査クエリで作成→実行を一括実行",
                    "operationId": "researchQuick",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {"query": {"type": "string"}, "use_cache": {"type": "boolean", "default": True}},
                                    "required": ["query"],
                                }
                            }
                        },
                    },
                    "responses": {"200": {"description": "成功"}},
                }
            },
            "/api/voice/health": {
                "get": {
                    "summary": "音声機能ヘルス",
                    "description": "STT/TTS の稼働確認",
                    "operationId": "getVoiceHealth",
                    "responses": {"200": {"description": "成功"}},
                }
            },
            "/api/n8n/workflows": {
                "get": {
                    "summary": "n8n ワークフロー一覧",
                    "description": "n8n のワークフロー一覧を取得",
                    "operationId": "getN8nWorkflows",
                    "responses": {"200": {"description": "成功"}},
                }
            },
            "/api/github/search": {
                "get": {
                    "summary": "GitHub リポジトリ検索",
                    "description": "query でリポジトリを検索",
                    "operationId": "githubSearch",
                    "parameters": [
                        {"name": "query", "in": "query", "required": True, "schema": {"type": "string"}},
                        {"name": "limit", "in": "query", "schema": {"type": "integer", "default": 10}},
                    ],
                    "responses": {"200": {"description": "成功"}},
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
            "/api/moltbot/plan": {
                "post": {
                    "summary": "MoltbotにPlanを送信",
                    "description": (
                        "まなOS→Moltbot Gateway経由でファイル整理Plan（list_only/read_only）を送信。"
                        "body: intent, path, user_hint または完全なplan JSON"
                    ),
                    "operationId": "moltbotSubmitPlan",
                    "requestBody": {
                        "required": False,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "intent": {
                                            "type": "string",
                                            "description": "list_only | read_only",
                                            "default": "list_only",
                                        },
                                        "path": {
                                            "type": "string",
                                            "description": "対象パス",
                                            "default": "~/Downloads",
                                        },
                                        "user_hint": {
                                            "type": "string",
                                            "description": "ユーザー指示の要約",
                                        },
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "成功",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "ok": {"type": "boolean"},
                                            "plan_id": {"type": "string"},
                                            "data": {"type": "object"},
                                        },
                                    }
                                }
                            },
                        }
                    },
                }
            },
            "/api/moltbot/plan/{plan_id}/result": {
                "get": {
                    "summary": "Plan実行結果を取得",
                    "description": "Moltbotで実行したPlanの結果を取得します",
                    "operationId": "moltbotGetResult",
                    "parameters": [
                        {
                            "name": "plan_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "responses": {"200": {"description": "成功"}},
                }
            },
            "/api/moltbot/health": {
                "get": {
                    "summary": "Moltbot Gatewayの死活確認",
                    "description": "Moltbot Gatewayの稼働状態を返します",
                    "operationId": "moltbotHealth",
                    "responses": {"200": {"description": "成功"}},
                }
            },
        },
    }
