#!/usr/bin/env python3
# flake8: noqa
# ruff: noqa
"""
🖥️ X280 API Gateway - ThinkPad X280側で実行するAPIゲートウェイ
母艦からのリクエストを受け、USB接続されたPixel7のAPIへプロキシする

使い方:
  python x280_api_gateway.py
  X280_API_PORT=5120 python x280_api_gateway.py

エンドポイント:
  GET  /health           - ヘルスチェック（母艦スクリプト用）
  GET  /api/health       - 詳細ヘルス（セットアップスクリプト用）
  GET  /api/status       - ADB・Pixel7接続状態
  ANY  /api/pixel7/{path} - Pixel7 APIへのプロキシ
  POST /api/adb/forward  - ADB ポートフォワード設定
  POST /api/adb/connect  - ADB Wi-Fi 接続
"""

import os
import asyncio
import subprocess
import shutil
from datetime import datetime
from typing import Any, Dict, Optional

try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    import httpx
    import uvicorn
except ImportError:
    print("依存パッケージが不足しています。以下を実行してください:")
    print("pip install fastapi uvicorn httpx pydantic")
    raise SystemExit(1)

# ---------------------------------------------------------------------------
# 設定
# ---------------------------------------------------------------------------
_PORT = int(os.getenv("X280_API_PORT", "5120"))
_HOST = os.getenv("X280_API_HOST", "0.0.0.0")

# Pixel7 API の向き先（USB ADB フォワード済みの場合は localhost:5122）
_PIXEL7_PORT = int(os.getenv("PIXEL7_API_PORT", "5122"))
_PIXEL7_ADB_TCP = os.getenv("PIXEL7_ADB_TCP", "100.84.2.125:5555")

# ADB 実行ファイル
def _find_adb() -> Optional[str]:
    if shutil.which("adb"):
        return "adb"
    candidates = [
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Android", "Sdk", "platform-tools", "adb.exe"),
        r"C:\Android\platform-tools\adb.exe",
        r"C:\platform-tools\adb.exe",
        r"C:\adb\adb.exe",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None

_ADB = _find_adb()

# ---------------------------------------------------------------------------
# FastAPI アプリ
# ---------------------------------------------------------------------------
app = FastAPI(
    title="X280 API Gateway",
    version="1.0.0",
    description="母艦 → X280 → Pixel7 のプロキシゲートウェイ",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# ユーティリティ
# ---------------------------------------------------------------------------
async def _run(cmd: list[str], timeout: int = 10) -> dict:
    """サブプロセスを非同期実行"""
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return {
            "exit_code": proc.returncode,
            "stdout": stdout.decode(errors="replace").strip(),
            "stderr": stderr.decode(errors="replace").strip(),
        }
    except asyncio.TimeoutError:
        return {"exit_code": -1, "stdout": "", "stderr": "timeout"}
    except Exception as e:
        return {"exit_code": -1, "stdout": "", "stderr": str(e)}


def _adb_devices() -> list[str]:
    """接続中のADBデバイス一覧を返す"""
    if not _ADB:
        return []
    try:
        result = subprocess.run(
            [_ADB, "devices"], capture_output=True, text=True, timeout=5
        )
        devices = []
        for line in result.stdout.splitlines()[1:]:
            line = line.strip()
            if line and line.endswith("\tdevice"):
                devices.append(line.split("\t")[0])
        return devices
    except Exception:
        return []


async def _pixel7_healthy() -> bool:
    """Pixel7 API（localhost:5122）が生きているか確認"""
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"http://127.0.0.1:{_PIXEL7_PORT}/health")
            return r.status_code < 400
    except Exception:
        return False


# ---------------------------------------------------------------------------
# ルート
# ---------------------------------------------------------------------------

@app.get("/health")
async def health_simple():
    """母艦スクリプト（mother_to_x280_openwebui_pixel7.ps1）向け簡易ヘルス"""
    return JSONResponse(content={
        "status": "healthy",
        "service": "x280_api_gateway",
        "timestamp": datetime.now().isoformat(),
    })


@app.get("/api/health")
async def health_detail():
    """セットアップスクリプト（x280_setup_and_start.ps1）向け詳細ヘルス"""
    devices = _adb_devices()
    pixel7_ok = await _pixel7_healthy()
    return JSONResponse(content={
        "status": "healthy",
        "service": "x280_api_gateway",
        "port": _PORT,
        "adb_available": _ADB is not None,
        "adb_devices": devices,
        "pixel7_api_reachable": pixel7_ok,
        "pixel7_api_url": f"http://127.0.0.1:{_PIXEL7_PORT}",
        "timestamp": datetime.now().isoformat(),
    })


@app.get("/api/status")
async def status():
    """ADB・Pixel7接続の総合ステータス"""
    devices = _adb_devices()
    pixel7_ok = await _pixel7_healthy()

    # ADB フォワード状態確認
    forward_list = []
    if _ADB:
        r = await _run([_ADB, "forward", "--list"])
        forward_list = [l for l in r["stdout"].splitlines() if l.strip()]

    return JSONResponse(content={
        "gateway": "x280",
        "adb": {
            "executable": _ADB or "not found",
            "devices": devices,
            "forward_rules": forward_list,
        },
        "pixel7_api": {
            "url": f"http://127.0.0.1:{_PIXEL7_PORT}",
            "reachable": pixel7_ok,
        },
        "timestamp": datetime.now().isoformat(),
    })


# ---------------------------------------------------------------------------
# Pixel7 API プロキシ
# ---------------------------------------------------------------------------

@app.api_route("/api/pixel7/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_to_pixel7(path: str, request: Request):
    """
    母艦からのリクエストを Pixel7 API へプロキシ

    例: GET /api/pixel7/health  →  GET http://127.0.0.1:5122/health
        POST /api/pixel7/api/run →  POST http://127.0.0.1:5122/api/run
    """
    target_url = f"http://127.0.0.1:{_PIXEL7_PORT}/{path}"
    if request.url.query:
        target_url += f"?{request.url.query}"

    body = await request.body()

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.request(
                method=request.method,
                url=target_url,
                headers={
                    k: v for k, v in request.headers.items()
                    if k.lower() not in {"host", "content-length"}
                },
                content=body,
            )
            try:
                data = resp.json()
            except Exception:
                data = {"raw": resp.text}

            return JSONResponse(content=data, status_code=resp.status_code)

    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Pixel7 API に接続できません",
                "hint": "ADB フォワードが必要です: POST /api/adb/forward",
                "pixel7_url": target_url,
            },
        )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Pixel7 API タイムアウト")


# ---------------------------------------------------------------------------
# ADB 操作
# ---------------------------------------------------------------------------

class AdbForwardRequest(BaseModel):
    local_port: int = 5122
    remote_port: int = 5122
    serial: Optional[str] = None


class AdbConnectRequest(BaseModel):
    address: Optional[str] = None  # 省略時は PIXEL7_ADB_TCP 環境変数


@app.post("/api/adb/forward")
async def adb_forward(req: AdbForwardRequest):
    """ADB ポートフォワード設定（USB接続されたPixel7のポートをlocalhostに転送）"""
    if not _ADB:
        raise HTTPException(status_code=500, detail="ADB が見つかりません")

    cmd = [_ADB]
    if req.serial:
        cmd += ["-s", req.serial]
    cmd += ["forward", f"tcp:{req.local_port}", f"tcp:{req.remote_port}"]

    r = await _run(cmd)
    return JSONResponse(content={
        "ok": r["exit_code"] == 0,
        "local_port": req.local_port,
        "remote_port": req.remote_port,
        "stdout": r["stdout"],
        "stderr": r["stderr"],
        "hint": f"転送後: http://127.0.0.1:{req.local_port}/ でPixel7にアクセス可能",
    })


@app.post("/api/adb/connect")
async def adb_connect(req: AdbConnectRequest):
    """ADB Wi-Fi 接続（Tailscale経由）"""
    if not _ADB:
        raise HTTPException(status_code=500, detail="ADB が見つかりません")

    address = req.address or _PIXEL7_ADB_TCP
    if not address:
        raise HTTPException(status_code=400, detail="address が必要です")

    r = await _run([_ADB, "connect", address])
    devices = _adb_devices()
    return JSONResponse(content={
        "ok": r["exit_code"] == 0,
        "address": address,
        "stdout": r["stdout"],
        "stderr": r["stderr"],
        "devices": devices,
    })


@app.get("/api/adb/devices")
async def adb_devices_list():
    """接続中の ADB デバイス一覧"""
    if not _ADB:
        return JSONResponse(content={"devices": [], "adb": "not found"})

    r = await _run([_ADB, "devices", "-l"])
    devices = _adb_devices()
    return JSONResponse(content={
        "devices": devices,
        "raw": r["stdout"],
        "timestamp": datetime.now().isoformat(),
    })


@app.post("/api/adb/setup")
async def adb_setup_pixel7():
    """
    Pixel7 USB接続→フォワード設定のワンコマンドセットアップ

    1. adb start-server
    2. adb forward tcp:5122 tcp:5122
    3. 疎通確認
    """
    if not _ADB:
        raise HTTPException(status_code=500, detail="ADB が見つかりません")

    steps = []

    # 1. adb start-server
    r1 = await _run([_ADB, "start-server"])
    steps.append({"step": "start-server", "ok": r1["exit_code"] == 0, "out": r1["stdout"]})

    # 2. デバイス確認
    devices = _adb_devices()
    steps.append({"step": "devices", "devices": devices})

    if not devices:
        return JSONResponse(content={
            "ok": False,
            "steps": steps,
            "hint": "USB ケーブルを接続し、Pixel7で『USB デバッグを許可』を選択してください",
        })

    # 3. フォワード設定
    r3 = await _run([_ADB, "forward", f"tcp:{_PIXEL7_PORT}", f"tcp:{_PIXEL7_PORT}"])
    steps.append({"step": "forward", "ok": r3["exit_code"] == 0, "port": _PIXEL7_PORT})

    # 4. Pixel7 API 疎通確認
    pixel7_ok = await _pixel7_healthy()
    steps.append({"step": "pixel7_health", "ok": pixel7_ok})

    return JSONResponse(content={
        "ok": r3["exit_code"] == 0,
        "devices": devices,
        "pixel7_api_reachable": pixel7_ok,
        "forward_port": _PIXEL7_PORT,
        "steps": steps,
        "hint": f"http://127.0.0.1:{_PIXEL7_PORT}/ でPixel7にアクセス可能" if r3["exit_code"] == 0 else "フォワード失敗",
    })


# ---------------------------------------------------------------------------
# エントリポイント
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print(f"=== X280 API Gateway starting on {_HOST}:{_PORT} ===")
    print(f"  ADB: {_ADB or 'not found'}")
    print(f"  Pixel7 API target: http://127.0.0.1:{_PIXEL7_PORT}")
    print(f"  Proxy: /api/pixel7/{{path}} → http://127.0.0.1:{_PIXEL7_PORT}/{{path}}")
    print(f"  Docs: http://127.0.0.1:{_PORT}/docs")
    uvicorn.run(app, host=_HOST, port=_PORT, log_level="info")
