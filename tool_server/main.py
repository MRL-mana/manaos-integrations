#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tool Server (FastAPI)
レミ先輩仕様：確実に動く手動ツール3つ + OpenAPI仕様対応
"""

import os
import sys
import io
import subprocess
import json
import re
import shutil
from manaos_logger import get_logger, get_service_logger
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import requests

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Windows環境での文字エンコーディング設定
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')  # type: ignore[attr-defined]

# パスを追加（サブディレクトリ実行でも _paths 等を解決できるようにする）
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _paths import COMFYUI_PORT, UNIFIED_API_PORT

logger = get_service_logger("main")

app = FastAPI(
    title="manaOS Tool Server",
    description="確実に動く手動ツール3つ + OpenAPI仕様対応",
    version="1.0.0"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# リクエスト/レスポンスモデル


class ServiceStatusRequest(BaseModel):
    service_type: str = Field(description="サービスタイプ: 'docker' or 'systemd'")
    service_name: Optional[str] = Field(None, description="特定のサービス名（オプション）")


class ServiceStatusResponse(BaseModel):
    status: str
    services: List[Dict[str, Any]]
    message: str


class CheckErrorsRequest(BaseModel):
    log_type: str = Field(description="ログタイプ: 'docker' or 'journalctl'")
    service_name: Optional[str] = Field(None, description="サービス名（オプション）")
    lines: int = Field(100, description="取得する行数")


class CheckErrorsResponse(BaseModel):
    status: str
    errors: List[Dict[str, Any]]
    summary: str
    message: str


class GenerateImageRequest(BaseModel):
    prompt: str = Field(description="画像生成のプロンプト")
    width: int = Field(512, description="画像の幅")
    height: int = Field(512, description="画像の高さ")
    steps: int = Field(20, description="生成ステップ数")
    negative_prompt: Optional[str] = Field(None, description="ネガティブプロンプト")
    mufufu_mode: bool = Field(False, description="ムフフモード（セクシー寄り・身体崩れ対策）")
    lab_mode: bool = Field(False, description="闇の実験室モード（ネガ最小限）")


class GenerateImageResponse(BaseModel):
    status: str
    prompt_id: Optional[str] = None
    image_path: Optional[str] = None
    message: str


class ExecuteCommandRequest(BaseModel):
    command: str = Field(description="実行するPowerShellコマンド")
    cwd: Optional[str] = Field(None, description="作業ディレクトリ（許可パス配下のみ）")
    timeout: int = Field(30, description="タイムアウト秒（1-120）")


class ExecuteCommandResponse(BaseModel):
    status: str
    exit_code: int
    stdout: str
    stderr: str
    command: str
    message: str


class VSCodeOpenFileRequest(BaseModel):
    file_path: str = Field(description="開くファイルパス")
    line: Optional[int] = Field(None, description="行番号（1始まり）")


class VSCodeOpenFolderRequest(BaseModel):
    folder_path: str = Field(description="開くフォルダパス")


class VSCodeOpenResponse(BaseModel):
    status: str
    target: str
    message: str


FORBIDDEN_PATTERNS = [
    r"rm\s+-rf",
    r"Remove-Item\s+.+-Recurse\s+-Force",
    r"format\s+[a-zA-Z]:",
    r"shutdown",
    r"Restart-Computer",
    r"Stop-Computer",
    r"Set-ExecutionPolicy",
    r"reg\s+delete",
]

ALLOWED_COMMAND_PREFIXES = [
    "Get-Process",
    "Get-Service",
    "Get-ChildItem",
    "Get-Content",
    "Test-Path",
    "python ",
    "py ",
    "git ",
    "docker ",
    "ollama ",
    "curl ",
]


def _get_patterns_from_env() -> List[str]:
    raw = os.getenv("TOOL_SERVER_FORBIDDEN_PATTERNS", "").strip()
    if not raw:
        return FORBIDDEN_PATTERNS
    return [item.strip() for item in raw.split(";") if item.strip()]


def _get_allowed_prefixes_from_env() -> List[str]:
    raw = os.getenv("TOOL_SERVER_ALLOWED_PREFIXES", "").strip()
    if not raw:
        return ALLOWED_COMMAND_PREFIXES
    return [item.strip() for item in raw.split(";") if item.strip()]


def _write_security_audit(event: Dict[str, Any]) -> None:
    try:
        log_dir = Path(__file__).resolve().parent.parent / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        audit_file = log_dir / "tool_server_security.log"

        payload = {
            "timestamp": datetime.now().isoformat(),
            **event,
        }

        with open(audit_file, "a", encoding="utf-8") as fp:
            fp.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning(f"security audit write failed: {e}")


def _get_allowed_roots() -> List[Path]:
    env_roots = os.getenv("TOOL_SERVER_ALLOWED_ROOTS", "").strip()
    if env_roots:
        roots = [Path(x.strip()).resolve() for x in env_roots.split(";") if x.strip()]
    else:
        desktop = Path.home() / "Desktop"
        roots = [desktop.resolve(), (desktop / "manaos_integrations").resolve()]
    return roots


def _is_path_allowed(target: Path) -> bool:
    resolved = target.resolve()
    for root in _get_allowed_roots():
        try:
            resolved.relative_to(root)
            return True
        except ValueError:
            continue
    return False


def _validate_command(command: str) -> Optional[str]:
    normalized = command.strip()
    if not normalized:
        return "コマンドが空です"

    forbidden_patterns = _get_patterns_from_env()
    for pattern in forbidden_patterns:
        if re.search(pattern, normalized, re.IGNORECASE):
            return f"禁止パターンを含むため実行できません: {pattern}"

    lower_cmd = normalized.lower()
    allowed_prefixes = _get_allowed_prefixes_from_env()
    if any(lower_cmd.startswith(prefix.lower()) for prefix in allowed_prefixes):
        return None

    return "許可リスト外のコマンドです"


def _resolve_vscode_executable() -> Optional[str]:
    env_path = os.getenv("VSCODE_EXECUTABLE", "").strip()
    if env_path and Path(env_path).exists():
        return env_path

    cli = shutil.which("code")
    if cli:
        return cli

    candidates = [
        Path(os.getenv("LOCALAPPDATA", "")) / "Programs" / "Microsoft VS Code" / "Code.exe",
        Path(os.getenv("LOCALAPPDATA", "")) / "Programs" / "Cursor" / "Cursor.exe",
        Path("C:/Program Files/Microsoft VS Code/Code.exe"),
        Path("C:/Program Files/Cursor/Cursor.exe"),
    ]

    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    return None

# ========================================
# Tool 1: docker/systemdの死活確認ツール
# ========================================


@app.post("/service_status", response_model=ServiceStatusResponse)
async def service_status(request: ServiceStatusRequest):
    """
    docker/systemdの死活確認ツール

    実行ログを残し、確実に動作するように実装
    """
    logger.info(f"service_status called: {request.service_type}, {request.service_name}")

    try:
        services = []

        if request.service_type == "docker":
            # Dockerコンテナの状態を取得（レミ先輩仕様：確実に動く実装）
            # ホストから実行されている場合は、dockerコマンドを直接実行
            # コンテナ内から実行されている場合は、統合APIサーバー経由で取得を試す

            # 方法1: dockerコマンドを直接実行（ホストから実行されている場合）
            try:
                # dockerコマンドでコンテナ一覧を取得
                cmd = ["docker", "ps", "-a", "--format", "json"]
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    shell=(sys.platform == "win32")
                )

                if result.returncode == 0 and result.stdout.strip():
                    # dockerコマンドが成功した場合
                    for line in result.stdout.strip().split('\n'):
                        if line:
                            try:
                                container = json.loads(line)
                                container_name = container.get("Names", "")
                                status = container.get("Status", "")

                                # 特定のサービス名でフィルタ
                                if request.service_name and request.service_name not in container_name:
                                    continue

                                # 死活判定
                                is_running = "Up" in status

                                services.append({
                                    "name": container_name,
                                    "status": "running" if is_running else "stopped",
                                    "image": container.get("Image", ""),
                                    "ports": container.get("Ports", ""),
                                    "status_detail": status,
                                    "id": container.get("ID", "")[:12] if container.get("ID") else ""
                                })
                            except json.JSONDecodeError as je:
                                logger.warning(f"JSON解析エラー: {je}, line: {line}")
                                continue

                    message = f"Dockerコンテナ: {len(services)}件取得（ホストから直接実行）"
                else:
                    # dockerコマンドが使えない場合、統合APIサーバー経由で取得を試す
                    raise FileNotFoundError("dockerコマンドが見つかりません")

            except FileNotFoundError:
                # 方法2: 統合APIサーバー経由で取得（コンテナ内から実行されている場合）
                unified_api_url = os.getenv("MANAOS_API_URL", "http://host.docker.internal:9502")

                try:
                    response = requests.get(
                        f"{unified_api_url}/api/system/docker/containers",
                        timeout=10
                    )

                    if response.status_code == 200:
                        data = response.json()

                        if "error" not in data:
                            containers = data.get("containers", [])

                            for container in containers:
                                container_name = container.get("name", "")

                                if request.service_name and request.service_name not in container_name:
                                    continue

                                services.append({
                                    "name": container_name,
                                    "status": container.get("status", "unknown"),
                                    "image": container.get("image", ""),
                                    "ports": container.get("ports", ""),
                                    "status_detail": container.get("status_detail", ""),
                                    "id": container.get("id", "")
                                })

                            message = f"Dockerコンテナ: {len(services)}件取得（統合API経由）"
                        else:
                            raise requests.exceptions.RequestException(data.get("error", "Unknown error"))
                    else:
                        raise requests.exceptions.RequestException(f"HTTP {response.status_code}")

                except requests.exceptions.RequestException as e:
                    logger.error(f"統合APIサーバー経由での取得に失敗: {e}")
                    services.append({
                        "name": "docker_unavailable",
                        "status": "error",
                        "message": f"Dockerに接続できません。ホストから実行してください。エラー: {str(e)}"
                    })
                    message = f"Docker接続エラー: {str(e)}"

            except subprocess.TimeoutExpired:
                services.append({
                    "name": "docker_timeout",
                    "status": "error",
                    "message": "dockerコマンドの実行がタイムアウトしました"
                })
                message = "dockerコマンドの実行がタイムアウトしました"
            except Exception as e:
                logger.error(f"Dockerコマンド実行エラー: {e}", exc_info=True)
                services.append({
                    "name": "docker_error",
                    "status": "error",
                    "message": f"Dockerコマンドの実行に失敗しました: {str(e)}"
                })
                message = f"Dockerコマンド実行エラー: {str(e)}"

        elif request.service_type == "systemd":
            # systemdサービスの状態を取得（Linux専用）
            if sys.platform == "win32":
                # Windowsではsystemdは使えない
                services.append({
                    "name": "systemd",
                    "status": "not_available",
                    "message": "systemd is not available on Windows"
                })
                return ServiceStatusResponse(
                    status="success",
                    services=services,
                    message="systemd is not available on Windows. Use 'docker' service_type instead."
                )

            cmd = ["systemctl", "list-units", "--type=service", "--format=json", "--no-pager"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line:
                        try:
                            unit = json.loads(line)
                            unit_name = unit.get("unit", "")
                            active_state = unit.get("activeState", "")
                            sub_state = unit.get("subState", "")

                            # 特定のサービス名でフィルタ
                            if request.service_name and request.service_name not in unit_name:
                                continue

                            services.append({
                                "name": unit_name,
                                "status": active_state,
                                "sub_state": sub_state,
                                "load_state": unit.get("loadState", "")
                            })
                        except json.JSONDecodeError:
                            continue

            message = f"systemdサービス: {len(services)}件"
        else:
            raise ValueError(f"Unknown service_type: {request.service_type}")

        return ServiceStatusResponse(
            status="success",
            services=services,
            message=message
        )

    except subprocess.TimeoutExpired:
        logger.error("service_status: タイムアウト")
        raise HTTPException(status_code=504, detail="コマンド実行がタイムアウトしました")
    except Exception as e:
        logger.error(f"service_status error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"サービス状態取得エラー: {str(e)}")

# ========================================
# Tool 2: journalctl/docker logsを要約してエラー検知するツール
# ========================================


@app.post("/check_errors", response_model=CheckErrorsResponse)
async def check_errors(request: CheckErrorsRequest):
    """
    journalctl/docker logsを要約してエラー検知するツール

    実行ログを残し、確実に動作するように実装
    """
    logger.info(f"check_errors called: {request.log_type}, {request.service_name}")

    try:
        errors = []

        if request.log_type == "docker":
            # Docker logsを取得（レミ先輩仕様：確実に動く実装）
            # ホストから実行されている場合は、dockerコマンドを直接実行
            # コンテナ内から実行されている場合は、統合APIサーバー経由で取得を試す

            # service_nameが指定されていない場合、すべてのコンテナのログを確認
            if not request.service_name:
                # すべてのコンテナのログを確認
                try:
                    # まず、実行中のコンテナ一覧を取得
                    cmd = ["docker", "ps", "--format", "{{.Names}}"]
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=10,
                        shell=(sys.platform == "win32")
                    )

                    if result.returncode == 0:
                        container_names = [name.strip() for name in result.stdout.strip().split('\n') if name.strip()]

                        # 各コンテナのログを確認
                        all_errors = []
                        for container_name in container_names[:10]:  # 最大10コンテナまで
                            try:
                                log_cmd = ["docker", "logs", "--tail", str(request.lines), container_name]
                                log_result = subprocess.run(
                                    log_cmd,
                                    capture_output=True,
                                    text=True,
                                    timeout=10,
                                    shell=(sys.platform == "win32")
                                )

                                if log_result.returncode == 0:
                                    logs = log_result.stdout.split('\n')
                                    error_patterns = ["ERROR", "error", "Error", "Exception", "Traceback", "Failed", "failed"]

                                    for i, line in enumerate(logs):
                                        for pattern in error_patterns:
                                            if pattern in line:
                                                context_start = max(0, i - 3)
                                                context_end = min(len(logs), i + 4)
                                                context = logs[context_start:context_end]

                                                all_errors.append({
                                                    "container": container_name,
                                                    "line_number": i + 1,
                                                    "error_line": line,
                                                    "context": context,
                                                    "pattern": pattern
                                                })
                                                break
                            except Exception as e:
                                logger.warning(f"コンテナ {container_name} のログ取得エラー: {e}")
                                continue

                        errors = all_errors
                        summary = f"すべてのDockerコンテナのログから {len(errors)} 件のエラーを検出"
                    else:
                        # dockerコマンドが使えない場合、エラーメッセージを返す
                        errors.append({
                            "error_line": "dockerコマンドが実行できません",
                            "message": "dockerコマンドが利用できないか、コンテナが起動していません"
                        })
                        summary = "dockerコマンドが実行できません"
                except Exception as e:
                    logger.error(f"コンテナ一覧取得エラー: {e}")
                    errors.append({
                        "error_line": f"コンテナ一覧の取得に失敗しました: {str(e)}",
                        "message": str(e)
                    })
                    summary = f"コンテナ一覧取得エラー: {str(e)}"

            # 方法1: dockerコマンドを直接実行（ホストから実行されている場合）
            try:
                cmd = ["docker", "logs", "--tail", str(request.lines), request.service_name]
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    shell=(sys.platform == "win32")
                )

                if result.returncode == 0:
                    logs = result.stdout.split('\n')

                    # エラーパターンを検索
                    error_patterns = ["ERROR", "error", "Error", "Exception", "Traceback", "Failed", "failed"]

                    for i, line in enumerate(logs):
                        for pattern in error_patterns:
                            if pattern in line:
                                # 前後3行をコンテキストとして取得
                                context_start = max(0, i - 3)
                                context_end = min(len(logs), i + 4)
                                context = logs[context_start:context_end]

                                errors.append({
                                    "line_number": i + 1,
                                    "error_line": line,
                                    "context": context,
                                    "pattern": pattern
                                })
                                break

                    summary = f"Docker logsから {len(errors)} 件のエラーを検出（ホストから直接実行）"
                else:
                    # dockerコマンドが使えない場合、統合APIサーバー経由で取得を試す
                    raise FileNotFoundError("dockerコマンドが見つかりません")

            except FileNotFoundError:
                # 方法2: 統合APIサーバー経由で取得（コンテナ内から実行されている場合）
                unified_api_url = os.getenv("MANAOS_API_URL", "http://host.docker.internal:9502")

                try:
                    response = requests.get(
                        f"{unified_api_url}/api/system/docker/logs",
                        params={
                            "container": request.service_name,
                            "lines": request.lines
                        },
                        timeout=30
                    )

                    if response.status_code == 200:
                        data = response.json()
                        errors_data = data.get("errors", [])

                        for error_data in errors_data:
                            errors.append({
                                "line_number": error_data.get("line_number", 0),
                                "error_line": error_data.get("error_line", ""),
                                "context": error_data.get("context", []),
                                "pattern": error_data.get("pattern", "")
                            })

                        summary = f"Docker logsから {len(errors)} 件のエラーを検出（統合API経由）"
                    else:
                        errors.append({
                            "line_number": 0,
                            "error_line": f"統合APIサーバーに接続できません (HTTP {response.status_code})",
                            "context": [],
                            "pattern": "API_ERROR"
                        })
                        summary = f"統合APIサーバーエラー: HTTP {response.status_code}"

                except requests.exceptions.RequestException as e:
                    logger.error(f"統合APIサーバー接続エラー: {e}")
                    errors.append({
                        "line_number": 0,
                        "error_line": f"統合APIサーバーに接続できません: {str(e)}",
                        "context": [],
                        "pattern": "CONNECTION_ERROR"
                    })
                    summary = f"統合APIサーバー接続エラー: {str(e)}"

            except subprocess.TimeoutExpired:
                errors.append({
                    "line_number": 0,
                    "error_line": "dockerコマンドの実行がタイムアウトしました",
                    "context": [],
                    "pattern": "TIMEOUT"
                })
                summary = "dockerコマンドの実行がタイムアウトしました"
            except Exception as e:
                logger.error(f"Docker logs取得エラー: {e}", exc_info=True)
                errors.append({
                    "line_number": 0,
                    "error_line": f"Docker logs取得に失敗しました: {str(e)}",
                    "context": [],
                    "pattern": "ERROR"
                })
                summary = f"Docker logs取得エラー: {str(e)}"

        elif request.log_type == "journalctl":
            # journalctlでログを取得（Linux専用）
            if sys.platform == "win32":
                # Windowsではjournalctlは使えない
                return CheckErrorsResponse(
                    status="error",
                    errors=[{
                        "error_line": "journalctl is not available on Windows",
                        "message": "Use 'docker' log_type instead."
                    }],
                    summary="journalctl is not available on Windows",
                    message="journalctl is not available on Windows. Use 'docker' log_type instead."
                )

            cmd = ["journalctl", "-n", str(request.lines), "--no-pager", "-o", "json"]

            if request.service_name:
                cmd.extend(["-u", request.service_name])

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line:
                        try:
                            log_entry = json.loads(line)
                            message = log_entry.get("MESSAGE", "")
                            priority = log_entry.get("PRIORITY", "")

                            # エラーレベルをチェック（3=error, 2=crit, 1=alert, 0=emerg）
                            if priority in ["3", "2", "1", "0"] or "error" in message.lower() or "failed" in message.lower():
                                errors.append({
                                    "timestamp": log_entry.get("__REALTIME_TIMESTAMP", ""),
                                    "priority": priority,
                                    "message": message,
                                    "service": log_entry.get("_SYSTEMD_UNIT", ""),
                                    "hostname": log_entry.get("_HOSTNAME", "")
                                })
                        except json.JSONDecodeError:
                            continue

            summary = f"journalctlから {len(errors)} 件のエラーを検出"
        else:
            raise ValueError(f"Unknown log_type: {request.log_type}")

        return CheckErrorsResponse(
            status="success",
            errors=errors[:50],  # 最大50件まで
            summary=summary,
            message=summary
        )

    except subprocess.TimeoutExpired:
        logger.error("check_errors: タイムアウト")
        raise HTTPException(status_code=504, detail="コマンド実行がタイムアウトしました")
    except Exception as e:
        logger.error(f"check_errors error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"エラー検知エラー: {str(e)}")

# ========================================
# Tool 3: ComfyUI APIを叩いて画像生成してファイルパスを返すツール
# ========================================


@app.post("/generate_image", response_model=GenerateImageResponse)
async def generate_image(request: GenerateImageRequest):
    """
    ComfyUI APIを叩いて画像生成してファイルパスを返すツール

    実行ログを残し、確実に動作するように実装
    """
    logger.info(f"generate_image called: prompt='{request.prompt[:50]}...'")

    try:
        comfyui_url = os.getenv("COMFYUI_URL", f"http://127.0.0.1:{COMFYUI_PORT}")

        # ComfyUIが利用可能かチェック
        try:
            health_check = requests.get(f"{comfyui_url}/system_stats", timeout=5)
            if health_check.status_code != 200:
                return GenerateImageResponse(
                    status="error",
                    message=f"ComfyUIサーバーが利用できません (HTTP {health_check.status_code})"
                )
        except requests.exceptions.RequestException as e:
            return GenerateImageResponse(
                status="error",
                message=f"ComfyUIサーバーに接続できません: {str(e)}"
            )

        # 統合APIサーバー経由で画像生成（既存の実装を利用）
        unified_api_url = os.getenv("MANAOS_API_URL", f"http://127.0.0.1:{UNIFIED_API_PORT}")

        payload = {
            "prompt": request.prompt,
            "width": request.width,
            "height": request.height,
            "steps": request.steps,
            "mufufu_mode": request.mufufu_mode,
            "lab_mode": request.lab_mode,
        }

        if request.negative_prompt:
            payload["negative_prompt"] = request.negative_prompt

        response = requests.post(
            f"{unified_api_url}/api/comfyui/generate",
            json=payload,
            timeout=60
        )

        if response.status_code == 200:
            result = response.json()
            prompt_id = result.get("prompt_id")

            # 画像パスは後で取得できるようにprompt_idを返す
            # 実際のファイルパスはComfyUIの出力ディレクトリを確認する必要がある
            image_path = f"comfyui_output/{prompt_id}.png"  # 仮のパス

            return GenerateImageResponse(
                status="success",
                prompt_id=prompt_id,
                image_path=image_path,
                message=f"画像生成を開始しました (ID: {prompt_id})"
            )
        else:
            return GenerateImageResponse(
                status="error",
                message=f"画像生成に失敗しました: {response.text}"
            )

    except Exception as e:
        logger.error(f"generate_image error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"画像生成エラー: {str(e)}")

# ========================================
# ヘルスチェック
# ========================================


@app.post("/execute_command", response_model=ExecuteCommandResponse)
async def execute_command(request: ExecuteCommandRequest):
    """ローカルOSで安全制限付きPowerShellコマンドを実行"""
    logger.info(f"execute_command called: {request.command[:120]}")

    validation_error = _validate_command(request.command)
    if validation_error:
        _write_security_audit(
            {
                "event": "command_blocked",
                "command": request.command,
                "cwd": request.cwd,
                "reason": validation_error,
            }
        )
        return ExecuteCommandResponse(
            status="blocked",
            exit_code=1,
            stdout="",
            stderr=validation_error,
            command=request.command,
            message=validation_error,
        )

    timeout = max(1, min(request.timeout, 120))
    cwd = Path(request.cwd).resolve() if request.cwd else Path.cwd().resolve()

    if not _is_path_allowed(cwd):
        _write_security_audit(
            {
                "event": "command_blocked",
                "command": request.command,
                "cwd": str(cwd),
                "reason": "cwd_not_allowed",
            }
        )
        return ExecuteCommandResponse(
            status="blocked",
            exit_code=1,
            stdout="",
            stderr="許可された作業ディレクトリ外です",
            command=request.command,
            message="許可された作業ディレクトリ外です",
        )

    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", request.command],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(cwd),
            shell=False,
        )
        status = "success" if result.returncode == 0 else "error"
        _write_security_audit(
            {
                "event": "command_executed",
                "command": request.command,
                "cwd": str(cwd),
                "exit_code": result.returncode,
                "status": status,
            }
        )
        return ExecuteCommandResponse(
            status=status,
            exit_code=result.returncode,
            stdout=result.stdout[-8000:],
            stderr=result.stderr[-8000:],
            command=request.command,
            message="コマンド実行完了" if result.returncode == 0 else "コマンド実行でエラーが発生",
        )
    except subprocess.TimeoutExpired:
        _write_security_audit(
            {
                "event": "command_timeout",
                "command": request.command,
                "cwd": str(cwd),
                "timeout_sec": timeout,
            }
        )
        return ExecuteCommandResponse(
            status="error",
            exit_code=124,
            stdout="",
            stderr=f"タイムアウト（{timeout}秒）",
            command=request.command,
            message="タイムアウト",
        )
    except Exception as e:
        logger.error(f"execute_command error: {e}", exc_info=True)
        _write_security_audit(
            {
                "event": "command_error",
                "command": request.command,
                "cwd": str(cwd),
                "error": str(e),
            }
        )
        return ExecuteCommandResponse(
            status="error",
            exit_code=1,
            stdout="",
            stderr=str(e),
            command=request.command,
            message="実行失敗",
        )


@app.post("/vscode_open_file", response_model=VSCodeOpenResponse)
async def vscode_open_file(request: VSCodeOpenFileRequest):
    """VS Codeでファイルを開く"""
    target = Path(request.file_path).expanduser().resolve()
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="ファイルが見つかりません")
    if not _is_path_allowed(target):
        raise HTTPException(status_code=403, detail="許可されたパス外です")

    editor_exe = _resolve_vscode_executable()
    if not editor_exe:
        raise HTTPException(status_code=500, detail="VS Code/Cursor 実行ファイルが見つかりません")

    try:
        if request.line and request.line > 0:
            subprocess.Popen([editor_exe, "-g", f"{target}:{request.line}"], shell=False)
        else:
            subprocess.Popen([editor_exe, str(target)], shell=False)
        return VSCodeOpenResponse(status="success", target=str(target), message="VS Codeでファイルを開きました")
    except Exception as e:
        logger.error(f"vscode_open_file error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"VS Code起動エラー: {str(e)}")


@app.post("/vscode_open_folder", response_model=VSCodeOpenResponse)
async def vscode_open_folder(request: VSCodeOpenFolderRequest):
    """VS Codeでフォルダを開く"""
    target = Path(request.folder_path).expanduser().resolve()
    if not target.exists() or not target.is_dir():
        raise HTTPException(status_code=404, detail="フォルダが見つかりません")
    if not _is_path_allowed(target):
        raise HTTPException(status_code=403, detail="許可されたパス外です")

    editor_exe = _resolve_vscode_executable()
    if not editor_exe:
        raise HTTPException(status_code=500, detail="VS Code/Cursor 実行ファイルが見つかりません")

    try:
        subprocess.Popen([editor_exe, str(target)], shell=False)
        return VSCodeOpenResponse(status="success", target=str(target), message="VS Codeでフォルダを開きました")
    except Exception as e:
        logger.error(f"vscode_open_folder error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"VS Code起動エラー: {str(e)}")


@app.get("/health")
async def health():
    """ヘルスチェック"""
    return {
        "status": "healthy",
        "service": "manaOS Tool Server",
        "timestamp": datetime.now().isoformat()
    }

# ========================================
# OpenAPI仕様のカスタマイズ（OpenWebUI用）
# ========================================


@app.get("/openapi.json")
async def openapi_spec():
    """OpenAPI仕様を返す（OpenWebUI External Tools対応）"""
    from fastapi.openapi.utils import get_openapi

    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="manaOS Tool Server",
        version="1.0.0",
        description="確実に動く手動ツール3つ + OpenAPI仕様対応",
        routes=app.routes,
    )

    # OpenWebUI用のサーバーURLを追加
    openapi_schema["servers"] = [
        {
            "url": "http://127.0.0.1:9503",
            "description": "ローカルホスト"
        },
        {
            "url": "http://host.docker.internal:9503",
            "description": "ローカルサーバー"
        }
    ]

    app.openapi_schema = openapi_schema
    return JSONResponse(content=openapi_schema)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("TOOL_SERVER_PORT", "9503"))
    logger.info(f"🚀 Tool Server starting on 0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
