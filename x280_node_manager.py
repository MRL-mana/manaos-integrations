#!/usr/bin/env python3
"""
🔌 Pixel7 Node Manager - ピクセル7をManaOSのリモートノードとして統合
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
from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from manaos_timeout_config import get_timeout_config

# ロガーの初期化
logger = get_logger(__name__)

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("Pixel7NodeManager")

# タイムアウト設定の取得
timeout_config = get_timeout_config()

# FastAPIアプリの初期化
app = FastAPI(title="Pixel7 Node Manager", version="1.0.0")

# ピクセル7設定（SSH接続用のホスト名は実際の設定に合わせて変更可能）
PIXEL7_HOST = os.getenv("PIXEL7_HOST", os.getenv("X280_HOST", "x280"))  # 後方互換性のため
PIXEL7_USER = os.getenv("PIXEL7_USER", os.getenv("X280_USER", "mana"))
PIXEL7_PORT = int(os.getenv("PIXEL7_PORT", os.getenv("X280_PORT", "22")))
PIXEL7_API_PORT = int(os.getenv("PIXEL7_API_PORT", os.getenv("X280_API_PORT", "5120")))  # ピクセル7側のAPIポート
PIXEL7_TAILSCALE_IP = os.getenv("PIXEL7_TAILSCALE_IP", os.getenv("X280_TAILSCALE_IP", "100.127.121.20"))


class NodeStatus(str, Enum):
    """ノードステータス"""
    ONLINE = "online"
    OFFLINE = "offline"
    UNKNOWN = "unknown"
    ERROR = "error"


class ResourceType(str, Enum):
    """リソースタイプ"""
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    PROCESS = "process"


@dataclass
class Pixel7NodeInfo:
    """ピクセル7ノード情報"""
    node_id: str = "pixel7"
    hostname: str = "DESKTOP-ASMRKIM"
    status: NodeStatus = NodeStatus.UNKNOWN
    last_seen: Optional[datetime] = None
    resources: Dict[str, Any] = None
    capabilities: List[str] = None
    
    def __post_init__(self):
        if self.resources is None:
            self.resources = {}
        if self.capabilities is None:
            self.capabilities = ["command_execution", "file_transfer", "resource_monitoring"]


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
            result = await self.execute_command("echo 'ping'", timeout=5)
            return result.exit_code == 0
        except Exception as e:
            logger.error(f"ピクセル7接続確認失敗: {e}")
            return False
    
    async def execute_command(
        self, 
        command: str, 
        timeout: Optional[int] = None,
        use_api: bool = True
    ) -> CommandResult:
        """ピクセル7でコマンドを実行"""
        start_time = datetime.now()
        timeout = timeout or self.command_timeout
        
        try:
            if use_api:
                # ピクセル7側のAPI経由で実行（推奨）
                result = await self._execute_via_api(command, timeout)
            else:
                # SSH経由で直接実行
                result = await self._execute_via_ssh(command, timeout)
            
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
            url = f"http://{PIXEL7_TAILSCALE_IP}:{PIXEL7_API_PORT}/api/execute"
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    url,
                    json={"command": command},
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                return response.json()
        except httpx.RequestError as e:
            logger.warning(f"API経由実行失敗、SSH経由にフォールバック: {e}")
            return await self._execute_via_ssh(command, timeout)
    
    async def _execute_via_ssh(self, command: str, timeout: int) -> Dict[str, Any]:
        """SSH経由でコマンド実行"""
        ssh_command = [
            "ssh",
            "-o", "StrictHostKeyChecking=no",
            "-o", f"ConnectTimeout={timeout}",
            f"{PIXEL7_USER}@{PIXEL7_HOST}",
            command
        ]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *ssh_command,
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
            # CPU使用率
            cpu_result = await self.execute_command(
                "powershell.exe -Command \"Get-CimInstance Win32_Processor | Select-Object -ExpandProperty LoadPercentage\"",
                timeout=10
            )
            cpu_usage = int(cpu_result.stdout.strip()) if cpu_result.exit_code == 0 else 0
            
            # メモリ使用率
            mem_result = await self.execute_command(
                "powershell.exe -Command \"$mem = Get-CimInstance Win32_OperatingSystem; [math]::Round((($mem.TotalVisibleMemorySize - $mem.FreePhysicalMemory) / $mem.TotalVisibleMemorySize) * 100, 2)\"",
                timeout=10
            )
            mem_usage = float(mem_result.stdout.strip()) if mem_result.exit_code == 0 else 0
            
            # ディスク使用率
            disk_result = await self.execute_command(
                "powershell.exe -Command \"Get-CimInstance Win32_LogicalDisk -Filter 'DeviceID=\"C:\"' | Select-Object @{Name='UsedPercent';Expression={[math]::Round((($_.Size - $_.FreeSpace) / $_.Size) * 100, 2)}}\"",
                timeout=10
            )
            disk_usage = float(disk_result.stdout.strip().split()[-1]) if disk_result.exit_code == 0 else 0
            
            # システム情報
            hostname_result = await self.execute_command("hostname", timeout=5)
            hostname = hostname_result.stdout.strip() if hostname_result.exit_code == 0 else "unknown"
            
            uptime_result = await self.execute_command(
                "powershell.exe -Command \"$os = Get-CimInstance Win32_OperatingSystem; $uptime = (Get-Date) - $os.LastBootUpTime; Write-Host ('{0} days, {1} hours, {2} minutes' -f $uptime.Days, $uptime.Hours, $uptime.Minutes)\"",
                timeout=10
            )
            uptime = uptime_result.stdout.strip() if uptime_result.exit_code == 0 else "unknown"
            
            return {
                "cpu": {
                    "usage_percent": cpu_usage,
                    "status": "normal" if cpu_usage < 80 else "high"
                },
                "memory": {
                    "usage_percent": mem_usage,
                    "status": "normal" if mem_usage < 80 else "high"
                },
                "disk": {
                    "usage_percent": disk_usage,
                    "status": "normal" if disk_usage < 80 else "high"
                },
                "system": {
                    "hostname": hostname,
                    "uptime": uptime,
                    "last_check": datetime.now().isoformat()
                }
            }
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
                scp_command = [
                    "scp",
                    "-o", "StrictHostKeyChecking=no",
                    local_path,
                    f"{PIXEL7_USER}@{PIXEL7_HOST}:{remote_path}"
                ]
            else:
                # ピクセル7からローカルへ
                scp_command = [
                    "scp",
                    "-o", "StrictHostKeyChecking=no",
                    f"{PIXEL7_USER}@{PIXEL7_HOST}:{remote_path}",
                    local_path
                ]
            
            process = await asyncio.create_subprocess_exec(
                *scp_command,
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
    port = int(os.getenv("PIXEL7_NODE_MANAGER_PORT", os.getenv("X280_NODE_MANAGER_PORT", "5121")))
    uvicorn.run(app, host="0.0.0.0", port=port)

