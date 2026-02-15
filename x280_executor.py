#!/usr/bin/env python3
"""
⚡ Pixel7 Executor - ManaOSタスク実行システムへのピクセル7統合
Task PlannerやExecutor Enhancedからピクセル7でコマンドを実行可能にする
"""

import os
import json
import httpx
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass

try:
    from manaos_integrations._paths import X280_NODE_MANAGER_PORT
except Exception:  # pragma: no cover
    try:
        from _paths import X280_NODE_MANAGER_PORT  # type: ignore
    except Exception:  # pragma: no cover
        X280_NODE_MANAGER_PORT = int(os.getenv("X280_NODE_MANAGER_PORT", "5121"))

from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity

logger = get_service_logger("x280-executor")
error_handler = ManaOSErrorHandler("Pixel7Executor")

# ピクセル7 Node ManagerのURL
PIXEL7_NODE_MANAGER_URL = os.getenv(
    "PIXEL7_NODE_MANAGER_URL",
    os.getenv(
        "X280_NODE_MANAGER_URL",
        f"http://127.0.0.1:{X280_NODE_MANAGER_PORT}",
    ),
)


@dataclass
class Pixel7ExecutionResult:
    """ピクセル7実行結果"""
    success: bool
    command: str
    exit_code: int
    stdout: str
    stderr: str
    execution_time: float
    timestamp: datetime
    error: Optional[str] = None


class Pixel7Executor:
    """ピクセル7実行エンジン"""
    
    def __init__(self):
        self.node_manager_url = PIXEL7_NODE_MANAGER_URL
        self.default_timeout = 60
    
    async def execute(
        self,
        command: str,
        timeout: Optional[int] = None,
        node: str = "pixel7"
    ) -> Pixel7ExecutionResult:
        """ピクセル7でコマンドを実行"""
        start_time = datetime.now()
        timeout = timeout or self.default_timeout
        
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{self.node_manager_url}/api/execute",
                    json={"command": command, "timeout": timeout},
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                result_data = response.json()
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                return Pixel7ExecutionResult(
                    success=result_data.get("exit_code", 1) == 0,
                    command=command,
                    exit_code=result_data.get("exit_code", 1),
                    stdout=result_data.get("stdout", ""),
                    stderr=result_data.get("stderr", ""),
                    execution_time=execution_time,
                    timestamp=datetime.now()
                )
        except httpx.RequestError as e:
            logger.error(f"ピクセル7実行リクエスト失敗: {e}")
            error_handler.handle_error(
                ErrorCategory.NETWORK,
                ErrorSeverity.MEDIUM,
                f"ピクセル7実行リクエスト失敗: {command}",
                str(e)
            )
            execution_time = (datetime.now() - start_time).total_seconds()
            return Pixel7ExecutionResult(
                success=False,
                command=command,
                exit_code=1,
                stdout="",
                stderr="",
                execution_time=execution_time,
                timestamp=datetime.now(),
                error=str(e)
            )
        except Exception as e:
            logger.error(f"ピクセル7実行エラー: {e}")
            error_handler.handle_error(
                ErrorCategory.EXECUTION,
                ErrorSeverity.MEDIUM,
                f"ピクセル7実行エラー: {command}",
                str(e)
            )
            execution_time = (datetime.now() - start_time).total_seconds()
            return Pixel7ExecutionResult(
                success=False,
                command=command,
                exit_code=1,
                stdout="",
                stderr="",
                execution_time=execution_time,
                timestamp=datetime.now(),
                error=str(e)
            )
    
    async def get_resources(self) -> Dict[str, Any]:
        """ピクセル7のリソース情報を取得"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.node_manager_url}/api/resources")
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"リソース情報取得失敗: {e}")
            return {}
    
    async def check_health(self) -> bool:
        """ピクセル7のヘルスチェック"""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.node_manager_url}/api/health")
                response.raise_for_status()
                health_data = response.json()
                return health_data.get("status") == "healthy"
        except Exception:
            return False
    
    async def transfer_file(
        self,
        local_path: str,
        remote_path: str,
        direction: str = "upload"
    ) -> Dict[str, Any]:
        """ファイル転送"""
        try:
            async with httpx.AsyncClient(timeout=300) as client:  # ファイル転送は長めのタイムアウト
                response = await client.post(
                    f"{self.node_manager_url}/api/transfer",
                    json={
                        "local_path": local_path,
                        "remote_path": remote_path,
                        "direction": direction
                    },
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"ファイル転送失敗: {e}")
            return {"success": False, "error": str(e)}


# グローバルインスタンス
pixel7_executor = Pixel7Executor()

# 後方互換性のためのエイリアス
x280_executor = pixel7_executor


# Task PlannerやExecutor Enhancedから使用するためのヘルパー関数

async def execute_on_pixel7(
    command: str,
    timeout: Optional[int] = None
) -> Dict[str, Any]:
    """
    ピクセル7でコマンドを実行（Task PlannerやExecutor Enhancedから呼び出し可能）
    
    Args:
        command: 実行するコマンド
        timeout: タイムアウト（秒）
    
    Returns:
        実行結果の辞書
    """
    result = await pixel7_executor.execute(command, timeout)
    return {
        "success": result.success,
        "exit_code": result.exit_code,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "execution_time": result.execution_time,
        "timestamp": result.timestamp.isoformat(),
        "error": result.error
    }


# 後方互換性のためのエイリアス
execute_on_x280 = execute_on_pixel7


async def get_pixel7_resources() -> Dict[str, Any]:
    """ピクセル7のリソース情報を取得"""
    return await pixel7_executor.get_resources()


# 後方互換性のためのエイリアス
get_x280_resources = get_pixel7_resources


async def check_pixel7_health() -> bool:
    """ピクセル7のヘルスチェック"""
    return await pixel7_executor.check_health()


# 後方互換性のためのエイリアス
check_x280_health = check_pixel7_health


# Task Plannerへの統合例
# task_planner.py で以下のように使用可能：

"""
from x280_executor import execute_on_pixel7, get_pixel7_resources

# タスクプランにピクセル7実行を追加
if task_type == "pixel7_command":
    result = await execute_on_pixel7(command)
    return result
"""

