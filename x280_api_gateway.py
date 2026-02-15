#!/usr/bin/env python3
"""
🌐 X280 API Gateway - X280（Windows PC）側で実行するAPIサーバー
ManaOSからのコマンド実行、リソース監視、ファイル操作を提供
"""

import os
import json
import subprocess
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# FastAPIアプリの初期化
app = FastAPI(title="X280 API Gateway", version="1.0.0")

# CORS設定（ManaOSからのアクセスを許可）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では適切に制限
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CommandRequest(BaseModel):
    command: str
    timeout: Optional[int] = 60


class FileOperationRequest(BaseModel):
    path: str
    operation: str = "read"  # read, write, delete, list
    content: Optional[str] = None


class ProcessRequest(BaseModel):
    action: str = "list"  # list, start, stop, kill
    name: Optional[str] = None
    command: Optional[str] = None


async def execute_powershell_command(command: str, timeout: int = 60) -> Dict[str, Any]:
    """PowerShellコマンドを実行"""
    try:
        ps_command = f"powershell.exe -Command \"{command}\""
        process = await asyncio.create_subprocess_exec(
            *ps_command.split(),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            process.kill()
            return {
                "exit_code": 124,
                "stdout": "",
                "stderr": f"Command timeout after {timeout} seconds"
            }
        
        return {
            "exit_code": process.returncode,
            "stdout": stdout.decode("utf-8", errors="ignore"),
            "stderr": stderr.decode("utf-8", errors="ignore")
        }
    except Exception as e:
        return {
            "exit_code": 1,
            "stdout": "",
            "stderr": str(e)
        }


async def execute_cmd_command(command: str, timeout: int = 60) -> Dict[str, Any]:
    """CMDコマンドを実行"""
    try:
        process = await asyncio.create_subprocess_exec(
            *command.split(),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            process.kill()
            return {
                "exit_code": 124,
                "stdout": "",
                "stderr": f"Command timeout after {timeout} seconds"
            }
        
        return {
            "exit_code": process.returncode,
            "stdout": stdout.decode("utf-8", errors="ignore"),
            "stderr": stderr.decode("utf-8", errors="ignore")
        }
    except Exception as e:
        return {
            "exit_code": 1,
            "stdout": "",
            "stderr": str(e)
        }


@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {
        "service": "X280 API Gateway",
        "version": "1.0.0",
        "status": "online",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/execute")
async def execute_command(request: CommandRequest):
    """コマンドを実行"""
    start_time = datetime.now()
    
    # PowerShellコマンドかCMDコマンドかを判定
    if request.command.startswith("powershell") or request.command.startswith("pwsh"):
        result = await execute_powershell_command(request.command, request.timeout)
    else:
        result = await execute_cmd_command(request.command, request.timeout)
    
    execution_time = (datetime.now() - start_time).total_seconds()
    
    return JSONResponse(content={
        "command": request.command,
        "exit_code": result["exit_code"],
        "stdout": result["stdout"],
        "stderr": result["stderr"],
        "execution_time": execution_time,
        "timestamp": datetime.now().isoformat()
    })


@app.get("/api/system/info")
async def get_system_info():
    """システム情報を取得"""
    try:
        # ホスト名
        hostname_result = await execute_cmd_command("hostname", timeout=5)
        hostname = hostname_result["stdout"].strip() if hostname_result["exit_code"] == 0 else "unknown"
        
        # OS情報
        os_result = await execute_powershell_command(
            "Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, BuildNumber | ConvertTo-Json",
            timeout=10
        )
        os_info = json.loads(os_result["stdout"]) if os_result["exit_code"] == 0 else {}
        
        # 起動時刻
        boot_result = await execute_powershell_command(
            "$os = Get-CimInstance Win32_OperatingSystem; $os.LastBootUpTime.ToString('yyyy-MM-dd HH:mm:ss')",
            timeout=10
        )
        boot_time = boot_result["stdout"].strip() if boot_result["exit_code"] == 0 else "unknown"
        
        return JSONResponse(content={
            "hostname": hostname,
            "os": os_info,
            "boot_time": boot_time,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/system/resources")
async def get_resources():
    """リソース情報を取得"""
    try:
        # CPU使用率
        cpu_result = await execute_powershell_command(
            "Get-CimInstance Win32_Processor | Select-Object -ExpandProperty LoadPercentage",
            timeout=10
        )
        cpu_usage = int(cpu_result["stdout"].strip()) if cpu_result["exit_code"] == 0 else 0
        
        # メモリ情報
        mem_result = await execute_powershell_command(
            "$mem = Get-CimInstance Win32_OperatingSystem; @{Total=$mem.TotalVisibleMemorySize; Free=$mem.FreePhysicalMemory; Used=$mem.TotalVisibleMemorySize - $mem.FreePhysicalMemory} | ConvertTo-Json",
            timeout=10
        )
        mem_info = json.loads(mem_result["stdout"]) if mem_result["exit_code"] == 0 else {}
        
        # ディスク情報
        disk_result = await execute_powershell_command(
            "Get-CimInstance Win32_LogicalDisk -Filter 'DeviceID=\"C:\"' | Select-Object Size, FreeSpace | ConvertTo-Json",
            timeout=10
        )
        disk_info = json.loads(disk_result["stdout"]) if disk_result["exit_code"] == 0 else {}
        
        # メモリ使用率を計算
        mem_usage_percent = 0
        if mem_info.get("Total") and mem_info.get("Used"):
            mem_usage_percent = round((mem_info["Used"] / mem_info["Total"]) * 100, 2)
        
        # ディスク使用率を計算
        disk_usage_percent = 0
        if disk_info.get("Size") and disk_info.get("FreeSpace"):
            disk_usage_percent = round(((disk_info["Size"] - disk_info["FreeSpace"]) / disk_info["Size"]) * 100, 2)
        
        return JSONResponse(content={
            "cpu": {
                "usage_percent": cpu_usage,
                "status": "normal" if cpu_usage < 80 else "high"
            },
            "memory": {
                "total_mb": round(mem_info.get("Total", 0) / 1024 / 1024, 2) if mem_info.get("Total") else 0,
                "free_mb": round(mem_info.get("Free", 0) / 1024 / 1024, 2) if mem_info.get("Free") else 0,
                "used_mb": round(mem_info.get("Used", 0) / 1024 / 1024, 2) if mem_info.get("Used") else 0,
                "usage_percent": mem_usage_percent,
                "status": "normal" if mem_usage_percent < 80 else "high"
            },
            "disk": {
                "total_gb": round(disk_info.get("Size", 0) / 1024 / 1024 / 1024, 2) if disk_info.get("Size") else 0,
                "free_gb": round(disk_info.get("FreeSpace", 0) / 1024 / 1024 / 1024, 2) if disk_info.get("FreeSpace") else 0,
                "used_gb": round((disk_info.get("Size", 0) - disk_info.get("FreeSpace", 0)) / 1024 / 1024 / 1024, 2) if disk_info.get("Size") and disk_info.get("FreeSpace") else 0,
                "usage_percent": disk_usage_percent,
                "status": "normal" if disk_usage_percent < 80 else "high"
            },
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/processes")
async def get_processes():
    """実行中のプロセス一覧を取得"""
    try:
        result = await execute_powershell_command(
            "Get-Process | Select-Object Id, ProcessName, CPU, WorkingSet, StartTime | ConvertTo-Json",
            timeout=30
        )
        
        if result["exit_code"] == 0:
            processes = json.loads(result["stdout"])
            if not isinstance(processes, list):
                processes = [processes]
            
            # メモリ使用量をMBに変換
            for proc in processes:
                if "WorkingSet" in proc:
                    proc["memory_mb"] = round(proc["WorkingSet"] / 1024 / 1024, 2)
            
            return JSONResponse(content={
                "processes": processes,
                "count": len(processes),
                "timestamp": datetime.now().isoformat()
            })
        else:
            raise HTTPException(status_code=500, detail=result["stderr"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/file")
async def file_operation(request: FileOperationRequest):
    """ファイル操作"""
    try:
        path = Path(request.path)
        
        if request.operation == "read":
            if not path.exists():
                raise HTTPException(status_code=404, detail="File not found")
            content = path.read_text(encoding="utf-8", errors="ignore")
            return JSONResponse(content={
                "operation": "read",
                "path": str(path),
                "content": content,
                "size": path.stat().st_size
            })
        
        elif request.operation == "write":
            if request.content is None:
                raise HTTPException(status_code=400, detail="Content is required for write operation")
            path.write_text(request.content, encoding="utf-8")
            return JSONResponse(content={
                "operation": "write",
                "path": str(path),
                "success": True
            })
        
        elif request.operation == "list":
            if not path.exists():
                raise HTTPException(status_code=404, detail="Path not found")
            if path.is_dir():
                files = [{"name": f.name, "is_dir": f.is_dir(), "size": f.stat().st_size if f.is_file() else 0} 
                        for f in path.iterdir()]
                return JSONResponse(content={
                    "operation": "list",
                    "path": str(path),
                    "files": files
                })
            else:
                raise HTTPException(status_code=400, detail="Path is not a directory")
        
        elif request.operation == "delete":
            if not path.exists():
                raise HTTPException(status_code=404, detail="File not found")
            path.unlink()
            return JSONResponse(content={
                "operation": "delete",
                "path": str(path),
                "success": True
            })
        
        else:
            raise HTTPException(status_code=400, detail=f"Unknown operation: {request.operation}")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check_simple():
    """シンプルなヘルスチェック（/health）"""
    return JSONResponse(content={
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    })


@app.get("/api/health")
async def health_check():
    """ヘルスチェック（/api/health）"""
    return JSONResponse(content={
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    })


if __name__ == "__main__":
    port = int(os.getenv("X280_API_PORT", "5120"))
    host = os.getenv("X280_API_HOST", "0.0.0.0")
    print(f"🚀 X280 API Gateway starting on {host}:{port}")
    print(f"📖 API Documentation: http://{host}:{port}/docs")
    uvicorn.run(app, host=host, port=port)

