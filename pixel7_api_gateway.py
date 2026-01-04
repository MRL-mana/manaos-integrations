#!/usr/bin/env python3
"""
🌐 Pixel7 API Gateway - ピクセル7（Android端末）側で実行するAPIサーバー
ManaOSからのコマンド実行、リソース監視、ファイル操作を提供

注意: このスクリプトはAndroid端末上で実行する必要があります
TermuxやAndroidアプリとして実行可能
"""

import os
import json
import subprocess
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

# Android上でFastAPIを実行する場合、Termux環境が必要
try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    import uvicorn
except ImportError:
    print("FastAPIがインストールされていません。Termuxで以下を実行してください:")
    print("pkg install python")
    print("pip install fastapi uvicorn")
    exit(1)

# FastAPIアプリの初期化
app = FastAPI(title="Pixel7 API Gateway", version="1.0.0")

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


async def execute_android_command(command: str, timeout: int = 60) -> Dict[str, Any]:
    """Android shellコマンドを実行"""
    try:
        # Android上で直接実行
        process = await asyncio.create_subprocess_exec(
            *command.split(),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            shell=True
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
        "service": "Pixel7 API Gateway",
        "version": "1.0.0",
        "status": "online",
        "platform": "Android",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/execute")
async def execute_command(request: CommandRequest):
    """Android shellコマンドを実行"""
    start_time = datetime.now()
    
    result = await execute_android_command(request.command, request.timeout)
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
        # Androidバージョン
        version_result = await execute_android_command("getprop ro.build.version.release", timeout=5)
        android_version = version_result["stdout"].strip() if version_result["exit_code"] == 0 else "unknown"
        
        # デバイスモデル
        model_result = await execute_android_command("getprop ro.product.model", timeout=5)
        device_model = model_result["stdout"].strip() if model_result["exit_code"] == 0 else "unknown"
        
        # デバイス名
        device_result = await execute_android_command("getprop ro.product.device", timeout=5)
        device_name = device_result["stdout"].strip() if device_result["exit_code"] == 0 else "unknown"
        
        return JSONResponse(content={
            "android_version": android_version,
            "device_model": device_model,
            "device_name": device_name,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/system/resources")
async def get_resources():
    """リソース情報を取得"""
    try:
        # メモリ情報
        mem_result = await execute_android_command("cat /proc/meminfo", timeout=10)
        mem_info = {}
        if mem_result["exit_code"] == 0:
            for line in mem_result["stdout"].split("\n"):
                if "MemTotal" in line:
                    mem_info["total"] = int(line.split()[1]) * 1024  # KB to bytes
                elif "MemAvailable" in line:
                    mem_info["available"] = int(line.split()[1]) * 1024
        
        # CPU使用率（簡易版）
        cpu_result = await execute_android_command("top -n 1 -d 1", timeout=10)
        cpu_usage = 0  # パースが必要
        
        # バッテリー情報
        battery_result = await execute_android_command("dumpsys battery", timeout=10)
        battery_level = 0
        battery_status = "unknown"
        if battery_result["exit_code"] == 0:
            for line in battery_result["stdout"].split("\n"):
                if "level:" in line:
                    battery_level = int(line.split(":")[1].strip())
                elif "status:" in line:
                    battery_status = line.split(":")[1].strip()
        
        # ストレージ情報
        storage_result = await execute_android_command("df /data", timeout=10)
        storage_info = {}
        if storage_result["exit_code"] == 0:
            lines = storage_result["stdout"].split("\n")
            if len(lines) > 1:
                parts = lines[1].split()
                if len(parts) >= 4:
                    storage_info["total"] = int(parts[1]) * 1024  # KB to bytes
                    storage_info["used"] = int(parts[2]) * 1024
                    storage_info["available"] = int(parts[3]) * 1024
        
        # メモリ使用率を計算
        mem_usage_percent = 0
        if mem_info.get("total") and mem_info.get("available"):
            mem_usage_percent = round(((mem_info["total"] - mem_info["available"]) / mem_info["total"]) * 100, 2)
        
        # ストレージ使用率を計算
        storage_usage_percent = 0
        if storage_info.get("total") and storage_info.get("used"):
            storage_usage_percent = round((storage_info["used"] / storage_info["total"]) * 100, 2)
        
        return JSONResponse(content={
            "memory": {
                "total_mb": round(mem_info.get("total", 0) / 1024 / 1024, 2) if mem_info.get("total") else 0,
                "available_mb": round(mem_info.get("available", 0) / 1024 / 1024, 2) if mem_info.get("available") else 0,
                "usage_percent": mem_usage_percent,
                "status": "normal" if mem_usage_percent < 80 else "high"
            },
            "storage": {
                "total_gb": round(storage_info.get("total", 0) / 1024 / 1024 / 1024, 2) if storage_info.get("total") else 0,
                "used_gb": round(storage_info.get("used", 0) / 1024 / 1024 / 1024, 2) if storage_info.get("used") else 0,
                "available_gb": round(storage_info.get("available", 0) / 1024 / 1024 / 1024, 2) if storage_info.get("available") else 0,
                "usage_percent": storage_usage_percent,
                "status": "normal" if storage_usage_percent < 80 else "high"
            },
            "battery": {
                "level": battery_level,
                "status": battery_status
            },
            "cpu": {
                "usage_percent": cpu_usage,
                "status": "normal" if cpu_usage < 80 else "high"
            },
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/apps")
async def get_apps():
    """インストール済みアプリ一覧を取得"""
    try:
        result = await execute_android_command("pm list packages", timeout=30)
        
        if result["exit_code"] == 0:
            apps = [line.replace("package:", "") for line in result["stdout"].strip().split("\n") if line]
            return JSONResponse(content={
                "apps": apps,
                "count": len(apps),
                "timestamp": datetime.now().isoformat()
            })
        else:
            raise HTTPException(status_code=500, detail=result["stderr"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health_check():
    """ヘルスチェック"""
    return JSONResponse(content={
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    })


if __name__ == "__main__":
    port = int(os.getenv("PIXEL7_API_PORT", "5122"))
    uvicorn.run(app, host="0.0.0.0", port=port)

