#!/usr/bin/env python3
"""
🔌 Pixel7 Node Manager - ピクセル7（Android端末）をManaOSのリモートノードとして統合
ピクセル7のリソース管理、コマンド実行、監視を提供
"""

import os
import json
import httpx
import subprocess
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# 統一モジュールのインポート
from manaos_logger import get_logger, get_service_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from manaos_timeout_config import get_timeout_config

# ロガーの初期化
logger = get_service_logger("pixel7-node-manager")

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("Pixel7NodeManager")

# タイムアウト設定の取得
timeout_config = get_timeout_config()

# FastAPIアプリの初期化
app = FastAPI(title="Pixel7 Node Manager", version="1.0.0")

# ピクセル7設定
PIXEL7_HOST = os.getenv("PIXEL7_HOST", "100.84.2.125")  # Pixel 7a Tailscale IP
PIXEL7_API_PORT = int(os.getenv("PIXEL7_API_PORT", "5122"))  # ピクセル7側のAPIポート
PIXEL7_ADB_PORT = int(os.getenv("PIXEL7_ADB_PORT", "5555"))  # ADB接続ポート


class NodeStatus(str, Enum):
    """ノードステータス"""
    ONLINE = "online"
    OFFLINE = "offline"
    UNKNOWN = "unknown"
    ERROR = "error"


@dataclass
class Pixel7NodeInfo:
    """ピクセル7ノード情報"""
    node_id: str = "pixel7"
    device_name: str = "Pixel 7"
    status: NodeStatus = NodeStatus.UNKNOWN
    last_seen: Optional[datetime] = None
    resources: Dict[str, Any] = None
    capabilities: List[str] = None

    def __post_init__(self):
        if self.resources is None:
            self.resources = {}
        if self.capabilities is None:
            self.capabilities = ["adb_command", "file_transfer", "resource_monitoring", "app_control"]


@dataclass
class CommandResult:
    """コマンド実行結果"""
    command: str
    exit_code: int
    stdout: str
    stderr: str
    execution_time: float
    timestamp: datetime


class Pixel7NodeManager:
    """ピクセル7ノード管理クラス"""

    def __init__(self):
        self.node_info = Pixel7NodeInfo()
        self.health_check_interval = 30  # 秒
        self.command_timeout = 60  # 秒

    async def check_connection(self) -> bool:
        """ピクセル7への接続確認"""
        try:
            # API経由で確認
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"http://{PIXEL7_HOST}:{PIXEL7_API_PORT}/api/health")
                return response.status_code == 200
        except Exception as e:
            logger.error(f"ピクセル7接続確認失敗: {e}")
            return False

    async def execute_command(
        self,
        command: str,
        timeout: Optional[int] = None,
        use_api: bool = True
    ) -> CommandResult:
        """ピクセル7でコマンドを実行（Android shellコマンド）"""
        start_time = datetime.now()
        timeout = timeout or self.command_timeout

        try:
            if use_api:
                # ピクセル7側のAPI経由で実行（推奨）
                result = await self._execute_via_api(command, timeout)
            else:
                # ADB経由で直接実行
                result = await self._execute_via_adb(command, timeout)

            execution_time = (datetime.now() - start_time).total_seconds()
            return CommandResult(
                command=command,
                exit_code=result.get("exit_code", 1),
                stdout=result.get("stdout", ""),
                stderr=result.get("stderr", ""),
                execution_time=execution_time,
                timestamp=datetime.now()
            )
        except Exception as e:
            logger.error(f"コマンド実行失敗: {e}")
            error_handler.handle_error(
                ErrorCategory.EXECUTION,
                ErrorSeverity.MEDIUM,
                f"ピクセル7コマンド実行失敗: {command}",
                str(e)
            )
            execution_time = (datetime.now() - start_time).total_seconds()
            return CommandResult(
                command=command,
                exit_code=1,
                stdout="",
                stderr=str(e),
                execution_time=execution_time,
                timestamp=datetime.now()
            )

    async def _execute_via_api(self, command: str, timeout: int) -> Dict[str, Any]:
        """ピクセル7側のAPI経由でコマンド実行"""
        try:
            url = f"http://{PIXEL7_HOST}:{PIXEL7_API_PORT}/api/execute"
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    url,
                    json={"command": command},
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                return response.json()
        except httpx.RequestError as e:
            logger.warning(f"API経由実行失敗、ADB経由にフォールバック: {e}")
            return await self._execute_via_adb(command, timeout)

    async def _execute_via_adb(self, command: str, timeout: int) -> Dict[str, Any]:
        """ADB経由でコマンド実行"""
        adb_command = [
            "adb",
            "-s", f"{PIXEL7_HOST}:{PIXEL7_ADB_PORT}",
            "shell",
            command
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *adb_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )

            return {
                "exit_code": process.returncode,
                "stdout": stdout.decode("utf-8", errors="ignore"),
                "stderr": stderr.decode("utf-8", errors="ignore")
            }
        except asyncio.TimeoutError:
            return {
                "exit_code": 124,
                "stdout": "",
                "stderr": f"Command timeout after {timeout} seconds"
            }

    async def get_resources(self) -> Dict[str, Any]:
        """ピクセル7のリソース情報を取得"""
        try:
            # API経由で取得
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"http://{PIXEL7_HOST}:{PIXEL7_API_PORT}/api/resources")
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"リソース情報取得失敗: {e}")
            return {}

    async def health_check(self) -> Dict[str, Any]:
        """ピクセル7のヘルスチェック"""
        is_online = await self.check_connection()

        if is_online:
            self.node_info.status = NodeStatus.ONLINE
            self.node_info.last_seen = datetime.now()
            resources = await self.get_resources()
            self.node_info.resources = resources
        else:
            self.node_info.status = NodeStatus.OFFLINE

        return {
            "status": self.node_info.status.value,
            "last_seen": self.node_info.last_seen.isoformat() if self.node_info.last_seen else None,
            "resources": self.node_info.resources
        }

    async def transfer_file(
        self,
        local_path: str,
        remote_path: str,
        direction: str = "upload"
    ) -> Dict[str, Any]:
        """ファイル転送（upload/download）"""
        try:
            if direction == "upload":
                # ローカルからピクセル7へ
                adb_command = [
                    "adb",
                    "-s", f"{PIXEL7_HOST}:{PIXEL7_ADB_PORT}",
                    "push",
                    local_path,
                    remote_path
                ]
            else:
                # ピクセル7からローカルへ
                adb_command = [
                    "adb",
                    "-s", f"{PIXEL7_HOST}:{PIXEL7_ADB_PORT}",
                    "pull",
                    remote_path,
                    local_path
                ]

            process = await asyncio.create_subprocess_exec(
                *adb_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            return {
                "success": process.returncode == 0,
                "stdout": stdout.decode("utf-8", errors="ignore"),
                "stderr": stderr.decode("utf-8", errors="ignore")
            }
        except Exception as e:
            logger.error(f"ファイル転送失敗: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# グローバルインスタンス
node_manager = Pixel7NodeManager()


# APIエンドポイント

class CommandRequest(BaseModel):
    command: str
    timeout: Optional[int] = None


class FileTransferRequest(BaseModel):
    local_path: str
    remote_path: str
    direction: str = "upload"  # upload or download


@app.get("/api/status")
async def get_status():
    """ピクセル7ノードのステータスを取得"""
    health = await node_manager.health_check()
    return JSONResponse(content={
        "node": asdict(node_manager.node_info),
        "health": health
    })


@app.post("/api/execute")
async def execute_command(request: CommandRequest):
    """ピクセル7でコマンドを実行"""
    result = await node_manager.execute_command(
        request.command,
        timeout=request.timeout
    )
    return JSONResponse(content=asdict(result))


@app.get("/api/resources")
async def get_resources():
    """ピクセル7のリソース情報を取得"""
    resources = await node_manager.get_resources()
    return JSONResponse(content=resources)


@app.post("/api/transfer")
async def transfer_file(request: FileTransferRequest):
    """ファイル転送"""
    result = await node_manager.transfer_file(
        request.local_path,
        request.remote_path,
        request.direction
    )
    return JSONResponse(content=result)


@app.get("/api/health")
async def health_check():
    """ヘルスチェック"""
    health = await node_manager.health_check()
    return JSONResponse(content=health)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PIXEL7_NODE_MANAGER_PORT", "5123"))
    uvicorn.run(app, host="0.0.0.0", port=port)
