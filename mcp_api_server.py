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
import subprocess
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from flask import Flask, request, jsonify
from flask_cors import CORS
from manaos_logger import get_logger, get_service_logger

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

_OPS_PLANS: Dict[str, Dict[str, Any]] = {}
_OPS_JOBS: Dict[str, Dict[str, Any]] = {}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _memory_log_path() -> Path:
    configured = os.getenv("MANAOS_MEMORY_LOG_PATH", "logs/blueprint_memory.jsonl")
    path = Path(configured)
    if not path.is_absolute():
        path = Path(__file__).parent / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _append_memory_entry(entry: Dict[str, Any]) -> None:
    log_path = _memory_log_path()
    with log_path.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _load_memory_entries(limit: int = 2000) -> list[Dict[str, Any]]:
    log_path = _memory_log_path()
    if not log_path.exists():
        return []

    entries: list[Dict[str, Any]] = []
    try:
        with log_path.open("r", encoding="utf-8") as fp:
            for line in fp:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        logger.warning(f"memory log read failed: {e}")

    return entries[-limit:]


def _score_memory_entry(query: str, entry: Dict[str, Any]) -> float:
    normalized = query.strip().lower()
    if not normalized:
        return 1.0

    content = str(entry.get("content", "")).lower()
    metadata = json.dumps(entry.get("metadata", {}), ensure_ascii=False).lower()
    haystack = f"{content} {metadata}"

    if normalized in haystack:
        if normalized in content:
            return 1.0
        return 0.75
    return 0.0


def _require_ops_token() -> Optional[tuple[Any, int]]:
    required_token = os.getenv("OPS_EXEC_BEARER_TOKEN", "").strip()
    if not required_token:
        return None

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"success": False, "error": "missing bearer token"}), 401

    provided = auth_header.replace("Bearer ", "", 1).strip()
    if provided != required_token:
        return jsonify({"success": False, "error": "invalid bearer token"}), 403
    return None


def _is_dangerous_command(command: str) -> bool:
    blocked_markers = [
        "rm -rf",
        "del /s /q",
        "format ",
        "shutdown",
        "reboot",
        "mkfs",
    ]
    lowered = command.lower()
    return any(marker in lowered for marker in blocked_markers)


def _create_job(job_type: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    job_id = str(uuid.uuid4())
    job = {
        "job_id": job_id,
        "type": job_type,
        "status": "queued",
        "created_at": _utc_now_iso(),
        "updated_at": _utc_now_iso(),
        "payload": payload or {},
        "result": None,
        "error": None,
    }
    _OPS_JOBS[job_id] = job
    return job


def _update_job(job_id: str, *, status: str, result: Optional[Dict[str, Any]] = None, error: Optional[str] = None) -> None:
    job = _OPS_JOBS.get(job_id)
    if not job:
        return
    job["status"] = status
    job["updated_at"] = _utc_now_iso()
    if result is not None:
        job["result"] = result
    if error is not None:
        job["error"] = error

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


@app.route("/memory/write", methods=["POST"])
@app.route("/api/memory/write", methods=["POST"])
def memory_write():
    """Blueprint memory write endpoint."""
    data = request.json or {}
    content = str(data.get("content", "")).strip()
    if not content:
        return jsonify({"success": False, "error": "content is required"}), 400

    metadata = data.get("metadata") or {}
    if not isinstance(metadata, dict):
        return jsonify({"success": False, "error": "metadata must be an object"}), 400

    entry = {
        "id": data.get("id") or str(uuid.uuid4()),
        "content": content,
        "metadata": metadata,
        "source": data.get("source", "api"),
        "timestamp": _utc_now_iso(),
    }
    _append_memory_entry(entry)
    return jsonify({"success": True, "entry": entry})


@app.route("/memory/search", methods=["POST"])
@app.route("/api/memory/search", methods=["POST"])
def memory_search():
    """Blueprint memory search endpoint."""
    data = request.json or {}
    query = str(data.get("query", "")).strip()
    limit = int(data.get("limit", 10) or 10)
    limit = max(1, min(limit, 100))

    entries = _load_memory_entries()
    scored = []
    for entry in entries:
        score = _score_memory_entry(query, entry)
        if score > 0:
            item = dict(entry)
            item["score"] = score
            scored.append(item)

    scored.sort(key=lambda x: (x.get("score", 0.0), x.get("timestamp", "")), reverse=True)
    results = scored[:limit]
    return jsonify({
        "success": True,
        "query": query,
        "count": len(results),
        "results": results,
    })


@app.route("/ops/plan", methods=["POST"])
@app.route("/api/ops/plan", methods=["POST"])
def ops_plan():
    """Create lightweight operation plan for approval flow."""
    data = request.json or {}
    goal = str(data.get("goal", "")).strip()
    if not goal:
        return jsonify({"success": False, "error": "goal is required"}), 400

    input_steps = data.get("steps")
    steps: list[str]
    if isinstance(input_steps, list) and input_steps:
        steps = [str(step).strip() for step in input_steps if str(step).strip()]
    else:
        steps = [
            f"Define scope: {goal}",
            "Run safe verification command",
            "Capture result and write memory",
        ]

    plan_id = str(uuid.uuid4())
    plan = {
        "plan_id": plan_id,
        "goal": goal,
        "steps": steps,
        "approval_required": os.getenv("OPS_APPROVAL_MODE", "required").lower() == "required",
        "created_at": _utc_now_iso(),
        "status": "planned",
    }
    _OPS_PLANS[plan_id] = plan
    return jsonify({"success": True, "plan": plan})


@app.route("/ops/exec", methods=["POST"])
@app.route("/api/ops/exec", methods=["POST"])
def ops_exec():
    """Execute approved operation command (dry-run by default)."""
    auth_error = _require_ops_token()
    if auth_error:
        return auth_error

    data = request.json or {}
    approval_required = os.getenv("OPS_APPROVAL_MODE", "required").lower() == "required"
    approved = bool(data.get("approved", False))
    dry_run = bool(data.get("dry_run", True))
    plan_id = str(data.get("plan_id", "")).strip()

    if approval_required and not approved:
        return jsonify({"success": False, "error": "approval required"}), 403

    plan = _OPS_PLANS.get(plan_id) if plan_id else None
    command = str(data.get("command", "")).strip()
    if not command and plan:
        command = "echo plan approved"
    if not command:
        return jsonify({"success": False, "error": "command is required"}), 400

    if _is_dangerous_command(command):
        return jsonify({"success": False, "error": "dangerous command blocked"}), 400

    job = _create_job(
        "ops_exec",
        {
            "plan_id": plan_id or None,
            "command": command,
            "dry_run": dry_run,
            "approved": approved,
        },
    )

    response_payload = {
        "success": True,
        "job_id": job["job_id"],
        "plan_id": plan_id or None,
        "command": command,
        "dry_run": dry_run,
        "approved": approved,
        "executed_at": _utc_now_iso(),
    }

    if dry_run:
        response_payload["stdout"] = "dry-run: command not executed"
        response_payload["returncode"] = 0
        _update_job(job["job_id"], status="completed", result=response_payload)
        return jsonify(response_payload)

    try:
        completed = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(Path(__file__).parent),
        )
        response_payload["stdout"] = (completed.stdout or "").strip()
        response_payload["stderr"] = (completed.stderr or "").strip()
        response_payload["returncode"] = completed.returncode
        response_payload["success"] = completed.returncode == 0
        _update_job(
            job["job_id"],
            status=("completed" if completed.returncode == 0 else "failed"),
            result=response_payload,
            error=(response_payload.get("stderr") or None),
        )
        return jsonify(response_payload), (200 if completed.returncode == 0 else 500)
    except subprocess.TimeoutExpired:
        _update_job(job["job_id"], status="failed", error="command timeout")
        return jsonify({"success": False, "error": "command timeout"}), 504
    except Exception as e:
        logger.error(f"ops exec error: {e}", exc_info=True)
        _update_job(job["job_id"], status="failed", error=str(e))
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/ops/job/<job_id>", methods=["GET"])
@app.route("/api/ops/job/<job_id>", methods=["GET"])
def ops_get_job(job_id: str):
    job = _OPS_JOBS.get(job_id)
    if not job:
        return jsonify({"success": False, "error": "job not found", "job_id": job_id}), 404
    return jsonify({"success": True, "job": job})


@app.route("/ops/notify", methods=["POST"])
@app.route("/api/ops/notify", methods=["POST"])
def ops_notify():
    data = request.json or {}
    channel = str(data.get("channel", "")).strip()
    level = str(data.get("level", "info")).strip().lower()
    message = str(data.get("message", "")).strip()
    metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}

    if not message:
        return jsonify({"success": False, "error": "message is required"}), 400

    logger.info(f"ops notify channel={channel or '-'} level={level}: {message}")
    payload = {
        "channel": channel or None,
        "level": level,
        "message": message,
        "metadata": metadata,
        "sent_at": _utc_now_iso(),
    }
    return jsonify({"success": True, "notification": payload})


@app.route("/dev/patch", methods=["POST"])
@app.route("/api/dev/patch", methods=["POST"])
def dev_patch():
    data = request.json or {}
    job = _create_job("dev_patch", data)
    return jsonify({"success": True, "status": "queued", "action": "patch", "job_id": job["job_id"]})


@app.route("/dev/test", methods=["POST"])
@app.route("/api/dev/test", methods=["POST"])
def dev_test():
    data = request.json or {}
    job = _create_job("dev_test", data)
    return jsonify({"success": True, "status": "queued", "action": "test", "job_id": job["job_id"]})


@app.route("/dev/deploy", methods=["POST"])
@app.route("/api/dev/deploy", methods=["POST"])
def dev_deploy():
    auth_error = _require_ops_token()
    if auth_error:
        return auth_error
    data = request.json or {}
    job = _create_job("dev_deploy", data)
    return jsonify({"success": True, "status": "queued", "action": "deploy", "job_id": job["job_id"]})


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
                    credentials_path = os.getenv("GOOGLE_DRIVE_CREDENTIALS", "credentials.json")
                    token_path = os.getenv("GOOGLE_DRIVE_TOKEN", "token.json")
                    _integrations[name] = GoogleDriveIntegration(
                        credentials_path=credentials_path,
                        token_path=token_path,
                    )
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

        paths["/memory/write"] = {
            "post": {
                "summary": "Write memory",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "content": {"type": "string"},
                                    "metadata": {"type": "object"},
                                    "source": {"type": "string"},
                                },
                                "required": ["content"],
                            }
                        }
                    }
                },
                "responses": {"200": {"description": "成功"}},
            }
        }

        paths["/memory/search"] = {
            "post": {
                "summary": "Search memory",
                "requestBody": {
                    "required": False,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "query": {"type": "string"},
                                    "limit": {"type": "integer"},
                                },
                            }
                        }
                    }
                },
                "responses": {"200": {"description": "成功"}},
            }
        }

        paths["/ops/plan"] = {
            "post": {
                "summary": "Create operation plan",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "goal": {"type": "string"},
                                    "steps": {"type": "array", "items": {"type": "string"}},
                                },
                                "required": ["goal"],
                            }
                        }
                    }
                },
                "responses": {"200": {"description": "成功"}},
            }
        }

        paths["/ops/exec"] = {
            "post": {
                "summary": "Execute approved operation",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "plan_id": {"type": "string"},
                                    "command": {"type": "string"},
                                    "approved": {"type": "boolean"},
                                    "dry_run": {"type": "boolean"},
                                },
                            }
                        }
                    }
                },
                "responses": {"200": {"description": "成功"}},
            }
        }

        paths["/ops/job/{job_id}"] = {
            "get": {
                "summary": "Get operation/dev job status",
                "parameters": [
                    {
                        "name": "job_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "responses": {"200": {"description": "成功"}, "404": {"description": "見つからない"}},
            }
        }

        paths["/ops/notify"] = {
            "post": {
                "summary": "Send operation notification",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "channel": {"type": "string"},
                                    "level": {"type": "string"},
                                    "message": {"type": "string"},
                                    "metadata": {"type": "object"},
                                },
                                "required": ["message"],
                            }
                        }
                    }
                },
                "responses": {"200": {"description": "成功"}},
            }
        }

        paths["/dev/patch"] = {"post": {"summary": "Queue patch task", "responses": {"200": {"description": "成功"}}}}
        paths["/dev/test"] = {"post": {"summary": "Queue test task", "responses": {"200": {"description": "成功"}}}}
        paths["/dev/deploy"] = {"post": {"summary": "Queue deploy task", "responses": {"200": {"description": "成功"}}}}

        alias_targets = [
            "/memory/write",
            "/memory/search",
            "/ops/plan",
            "/ops/exec",
            "/ops/job/{job_id}",
            "/ops/notify",
            "/dev/patch",
            "/dev/test",
            "/dev/deploy",
        ]
        for base_path in alias_targets:
            paths[f"/api{base_path}"] = paths[base_path]

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
