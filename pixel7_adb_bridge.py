#!/usr/bin/env python3
"""
Pixel7 ADB Bridge - 母艦で 5122 を立て、USB接続の Pixel 7 に ADB でコマンドを転送
Termux なしでデバイスオーケストレーターから Pixel 7 をオンライン表示するため
"""
import os
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Pixel7 API Gateway (ADB Bridge)", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# USB 接続の Pixel 7（PIXEL7_ADB_SERIAL 未設定時は実機を自動選択＝エミュレータ除外）
def _get_adb_device() -> str:
    """利用する ADB デバイス serial を取得（実機優先）"""
    s = os.getenv("PIXEL7_ADB_SERIAL", "").strip()
    if s:
        return s
    import subprocess
    try:
        r = subprocess.run(
            ["adb", "devices"],
            capture_output=True,
            text=True,
            timeout=5,
            encoding="utf-8",
            errors="replace",
        )
        for line in (r.stdout or "").strip().splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "device":
                serial = parts[0]
                if not serial.startswith("emulator-"):
                    return serial
        return ""
    except Exception:
        return ""


def _adb_shell(command: str, timeout: int = 60) -> Dict[str, Any]:
    """ADB shell でコマンド実行（同期）"""
    import subprocess
    device = _get_adb_device()
    cmd = ["adb"]
    if device:
        cmd += ["-s", device]
    cmd += ["shell", command]
    try:
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
        return {
            "exit_code": r.returncode,
            "stdout": r.stdout or "",
            "stderr": r.stderr or "",
        }
    except subprocess.TimeoutExpired:
        return {"exit_code": 124, "stdout": "", "stderr": f"Command timeout after {timeout}s"}
    except Exception as e:
        return {"exit_code": 1, "stdout": "", "stderr": str(e)}


async def run_adb_shell(command: str, timeout: int = 60) -> Dict[str, Any]:
    """非同期で ADB shell 実行"""
    return await asyncio.get_event_loop().run_in_executor(
        None, lambda: _adb_shell(command, timeout)
    )


class CommandRequest(BaseModel):
    command: str
    timeout: Optional[int] = 60


@app.get("/")
async def root():
    return {
        "service": "Pixel7 API Gateway (ADB Bridge)",
        "version": "1.0.0",
        "status": "online",
        "platform": "Android (via ADB)",
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/health")
async def health_compat():
    return JSONResponse(content={
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
    })


@app.get("/api/health")
async def health_check():
    return JSONResponse(content={
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
    })


@app.post("/api/execute")
async def execute_command(request: CommandRequest):
    start = datetime.now()
    result = await run_adb_shell(request.command, request.timeout or 60)
    elapsed = (datetime.now() - start).total_seconds()
    return JSONResponse(content={
        "command": request.command,
        "exit_code": result["exit_code"],
        "stdout": result["stdout"],
        "stderr": result["stderr"],
        "execution_time": elapsed,
        "timestamp": datetime.now().isoformat(),
    })


@app.get("/api/system/info")
async def get_system_info():
    v = await run_adb_shell("getprop ro.build.version.release", 5)
    m = await run_adb_shell("getprop ro.product.model", 5)
    d = await run_adb_shell("getprop ro.product.device", 5)
    return JSONResponse(content={
        "android_version": (v["stdout"] or "").strip() or "unknown",
        "device_model": (m["stdout"] or "").strip() or "unknown",
        "device_name": (d["stdout"] or "").strip() or "unknown",
        "timestamp": datetime.now().isoformat(),
    })


@app.get("/api/system/resources")
async def get_resources():
    mem = await run_adb_shell("cat /proc/meminfo", 10)
    bat = await run_adb_shell("dumpsys battery", 10)
    mem_info, battery_level, battery_status = {}, 0, "unknown"
    if mem["exit_code"] == 0:
        for line in (mem["stdout"] or "").split("\n"):
            if "MemTotal" in line:
                mem_info["total"] = int(line.split()[1]) * 1024
            elif "MemAvailable" in line:
                mem_info["available"] = int(line.split()[1]) * 1024
    if bat["exit_code"] == 0:
        for line in (bat["stdout"] or "").split("\n"):
            if "level:" in line:
                battery_level = int(line.split(":")[1].strip())
            elif "status:" in line:
                battery_status = line.split(":")[1].strip()
    mem_usage = 0.0
    if mem_info.get("total") and mem_info.get("available"):
        t, a = mem_info["total"], mem_info["available"]
        mem_usage = round(((t - a) / t) * 100, 2)
    return JSONResponse(content={
        "memory": {
            "total_mb": round(mem_info.get("total", 0) / 1024 / 1024, 2),
            "available_mb": round(mem_info.get("available", 0) / 1024 / 1024, 2),
            "usage_percent": mem_usage,
            "status": "normal" if mem_usage < 80 else "high",
        },
        "battery": {"level": battery_level, "status": battery_status},
        "cpu": {"usage_percent": 0, "status": "normal"},
        "storage": {},
        "timestamp": datetime.now().isoformat(),
    })


@app.get("/api/apps")
async def get_apps():
    result = await run_adb_shell("pm list packages", 30)
    if result["exit_code"] != 0:
        raise HTTPException(status_code=500, detail=result["stderr"])
    out = (result["stdout"] or "").split("\n")
    apps = [line.replace("package:", "").strip() for line in out if line.strip()]
    return JSONResponse(content={
        "apps": apps,
        "count": len(apps),
        "timestamp": datetime.now().isoformat(),
    })


def _screencap_sync() -> Optional[str]:
    """ADB screencap を実行し、保存先パスを返す（同期）"""
    import subprocess
    device = _get_adb_device()
    cmd = ["adb"]
    if device:
        cmd += ["-s", device]
    cmd += ["exec-out", "screencap", "-p"]
    save_dir = Path(__file__).resolve().parent / "pixel7_screenshots"
    save_dir.mkdir(exist_ok=True)
    path = save_dir / f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    try:
        with open(path, "wb") as f:
            r = subprocess.run(cmd, stdout=f, timeout=30)
        return str(path) if r.returncode == 0 else None
    except Exception:
        return None


def _adb_push_sync(local: str, remote: str) -> Dict[str, Any]:
    """ADB push（同期）"""
    import subprocess
    device = _get_adb_device()
    cmd = ["adb"]
    if device:
        cmd += ["-s", device]
    cmd += ["push", local, remote]
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120, encoding="utf-8", errors="replace"
        )
        return {"ok": r.returncode == 0, "stdout": r.stdout or "", "stderr": r.stderr or ""}
    except Exception as e:
        return {"ok": False, "stdout": "", "stderr": str(e)}


def _adb_pull_sync(remote: str, local: str) -> Dict[str, Any]:
    """ADB pull（同期）"""
    import subprocess
    device = _get_adb_device()
    cmd = ["adb"]
    if device:
        cmd += ["-s", device]
    cmd += ["pull", remote, local]
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120, encoding="utf-8", errors="replace"
        )
        return {"ok": r.returncode == 0, "stdout": r.stdout or "", "stderr": r.stderr or ""}
    except Exception as e:
        return {"ok": False, "stdout": "", "stderr": str(e)}


class FileTransferRequest(BaseModel):
    local_path: str
    remote_path: str


@app.post("/api/file/push")
async def file_push(req: FileTransferRequest):
    """母艦のファイルを Pixel 7 に送る"""
    loop = asyncio.get_event_loop()
    out = await loop.run_in_executor(None, lambda: _adb_push_sync(req.local_path, req.remote_path))
    if not out["ok"]:
        raise HTTPException(status_code=500, detail=out["stderr"] or "push failed")
    return JSONResponse(content={"ok": True, "message": f"pushed to {req.remote_path}"})


@app.post("/api/file/pull")
async def file_pull(req: FileTransferRequest):
    """Pixel 7 のファイルを母艦に取得（remote_path → local_path）"""
    loop = asyncio.get_event_loop()
    out = await loop.run_in_executor(
        None, lambda: _adb_pull_sync(req.remote_path, req.local_path)
    )
    if not out["ok"]:
        raise HTTPException(status_code=500, detail=out["stderr"] or "pull failed")
    return JSONResponse(content={"ok": True, "message": f"pulled to {req.local_path}"})


@app.get("/api/screenshot")
async def get_screenshot():
    """Pixel 7 のスクリーンショットを取得し、保存パスを返す"""
    loop = asyncio.get_event_loop()
    path = await loop.run_in_executor(None, _screencap_sync)
    if not path:
        raise HTTPException(status_code=500, detail="screencap failed")
    return JSONResponse(content={
        "path": path,
        "ok": True,
        "timestamp": datetime.now().isoformat(),
    })


if __name__ == "__main__":
    port = int(os.getenv("PIXEL7_API_PORT", "5122"))
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port)
