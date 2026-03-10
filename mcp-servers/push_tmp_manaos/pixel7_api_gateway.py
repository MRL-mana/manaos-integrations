#!/usr/bin/env python3
# flake8: noqa
# ruff: noqa
"""
🌐 Pixel7 API Gateway - ピクセル7（Android端末）側で実行するAPIサーバー
ManaOSからのコマンド実行、リソース監視、ファイル操作を提供

注意: このスクリプトはAndroid端末上で実行する必要があります
TermuxやAndroidアプリとして実行可能
"""

import os
import json
import asyncio
import secrets
import shlex
from datetime import datetime
from typing import Dict, Any, Optional, List, Union

# Android上でFastAPIを実行する場合、Termux環境が必要
try:
    from fastapi import FastAPI, HTTPException, Depends, Header, Request
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
_CORS_ORIGINS = [
    o.strip()
    for o in os.environ.get("MANAOS_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_API_PROFILE = (os.getenv("PIXEL7_API_PROFILE", "core") or "core").strip().lower()
if _API_PROFILE not in {"core", "full"}:
    _API_PROFILE = "core"


class CommandRequest(BaseModel):
    command: str
    timeout: Optional[int] = 60


class OpenUrlRequest(BaseModel):
    url: str


class OpenAppRequest(BaseModel):
    package: str
    activity: Optional[str] = None


class MacroBroadcastRequest(BaseModel):
    action: Optional[str] = None
    cmd: str
    extras: Optional[Dict[str, Any]] = None


def _is_tailscale_client(ip: str) -> bool:
    # Tailscale IPv4 range is 100.64.0.0/10; we keep it simple here.
    if not ip:
        return False
    # Allow local access (adb forward / on-device localhost)
    if ip == "127.0.0.1" or ip == "::1":
        return True
    if ip.startswith("100."):
        return True
    # IPv6 on tailnet is typically in fd7a:115c:a1e0::/48
    if ip.lower().startswith("fd7a:"):
        return True
    return False


def require_auth(
    request: Request,
    authorization: Optional[str] = Header(default=None),
) -> None:
    if os.getenv("PIXEL7_API_TAILSCALE_ONLY", "1").strip() != "0":
        client_ip = request.client.host if request.client else ""
        if not _is_tailscale_client(client_ip):
            raise HTTPException(
                status_code=403,
                detail="Tailscale-only access is enabled",
            )

    token = os.getenv("PIXEL7_API_TOKEN", "").strip()
    if not token:
        raise HTTPException(status_code=503, detail="PIXEL7_API_TOKEN is not set")

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization: Bearer <token>",
        )

    got = authorization[len("Bearer "):].strip()
    if not secrets.compare_digest(got, token):
        raise HTTPException(status_code=403, detail="Invalid token")


def require_full_profile() -> None:
    if _API_PROFILE != "full":
        raise HTTPException(
            status_code=403,
            detail="This endpoint requires PIXEL7_API_PROFILE=full",
        )


async def execute_android_command(
    command: Union[str, List[str]],
    timeout: int = 60,
) -> Dict[str, Any]:
    """Android shellコマンドを実行

    - str の場合: /system/bin/sh -lc で実行（クォート/URL等が壊れにくい）
    - list の場合: argv をそのまま exec
    """
    try:
        if isinstance(command, str):
            argv = ["/system/bin/sh", "-lc", command]
        else:
            argv = list(command)
            if argv:
                # Prefer Android system binaries over Termux PATH to avoid name collisions.
                if argv[0] in {"am", "monkey", "getprop", "dumpsys"}:
                    argv[0] = f"/system/bin/{argv[0]}"

        process = await asyncio.create_subprocess_exec(
            *argv,
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
    except (OSError, ValueError) as e:
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
        "api_profile": _API_PROFILE,
        "status": "online",
        "platform": "Android",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/execute")
async def execute_command(
    request: CommandRequest,
    _: None = Depends(require_auth),
    __: None = Depends(require_full_profile),
):
    """Android shellコマンドを実行（危険: デフォルト無効）"""
    if os.getenv("PIXEL7_API_ALLOW_EXEC", "0").strip() != "1":
        raise HTTPException(status_code=403, detail="/api/execute is disabled (set PIXEL7_API_ALLOW_EXEC=1)")

    start_time = datetime.now()

    timeout = request.timeout if request.timeout is not None else 60
    result = await execute_android_command(request.command, timeout)
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
async def get_system_info(_: None = Depends(require_auth)):
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
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/system/resources")
async def get_resources(_: None = Depends(require_auth)):
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
        cpu_usage = 0  # パースが必要（MVPでは未実装）

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
        mem_usage_percent: float = 0.0
        if mem_info.get("total") and mem_info.get("available"):
            mem_usage_percent = round(
                ((mem_info["total"] - mem_info["available"]) / mem_info["total"]) * 100,
                2,
            )

        # ストレージ使用率を計算
        storage_usage_percent: float = 0.0
        if storage_info.get("total") and storage_info.get("used"):
            storage_usage_percent = round(
                (storage_info["used"] / storage_info["total"]) * 100,
                2,
            )

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
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/apps")
async def get_apps(_: None = Depends(require_auth)):
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
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/health")
async def health_check():
    """ヘルスチェック"""
    return JSONResponse(content={
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    })


@app.get("/health")
async def health_compat():
    """ヘルスチェック（オーケストレーター・監視用 /health 互換）"""
    return JSONResponse(content={
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    })


@app.get("/api/status")
async def status_bundle(_: None = Depends(require_auth)):
    """よく使う状態を1回で返す"""
    info = await get_system_info()  # type: ignore
    resources = await get_resources()  # type: ignore
    return JSONResponse(content={
        "info": json.loads(info.body.decode("utf-8")),  # type: ignore
        "resources": json.loads(resources.body.decode("utf-8")),  # type: ignore
        "timestamp": datetime.now().isoformat(),
    })


@app.post("/api/open/url")
async def open_url(
    request: OpenUrlRequest,
    _: None = Depends(require_auth),
    __: None = Depends(require_full_profile),
):
    url = (request.url or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="url is required")

    # Prefer termux-open-url if available, fallback to am start.
    r = await execute_android_command(["termux-open-url", url], timeout=10)
    if r["exit_code"] != 0:
        r = await execute_android_command(
            ["am", "start", "-a", "android.intent.action.VIEW", "-d", url],
            timeout=10,
        )

    return JSONResponse(content={
        "ok": r["exit_code"] == 0,
        "exit_code": r["exit_code"],
        "stderr": r["stderr"],
        "timestamp": datetime.now().isoformat(),
    })


@app.post("/api/open/app")
async def open_app(
    request: OpenAppRequest,
    _: None = Depends(require_auth),
    __: None = Depends(require_full_profile),
):
    pkg = (request.package or "").strip()
    if not pkg:
        raise HTTPException(status_code=400, detail="package is required")

    if request.activity:
        component = f"{pkg}/{request.activity}"
        r = await execute_android_command(["am", "start", "-n", component], timeout=10)
    else:
        # On some Android/Termux environments, exec-ing monkey directly can fail;
        # prefer running it via /system/bin/sh.
        r = await execute_android_command(
            f"monkey -p {shlex.quote(pkg)} -c android.intent.category.LAUNCHER 1",
            timeout=15,
        )

    return JSONResponse(content={
        "ok": r["exit_code"] == 0,
        "exit_code": r["exit_code"],
        "stderr": r["stderr"],
        "timestamp": datetime.now().isoformat(),
    })


@app.post("/api/macro/broadcast")
async def macro_broadcast(
    request: MacroBroadcastRequest,
    _: None = Depends(require_auth),
    __: None = Depends(require_full_profile),
):
    """MacroDroid向けにIntentを投げる（MacroDroid側で 'Intent Received' トリガを作る）"""
    action = (
        request.action
        or os.getenv("PIXEL7_MACRO_INTENT_ACTION")
        or "com.manaos.PIXEL7_MACRO"
    ).strip()
    cmd = (request.cmd or "").strip()
    if not cmd:
        raise HTTPException(status_code=400, detail="cmd is required")

    extras = request.extras or {}
    extra_args: List[str] = []
    extra_args += ["--es", "cmd", cmd]
    for k, v in extras.items():
        if v is None:
            continue
        if isinstance(v, (dict, list)):
            extra_args += ["--es", str(k), json.dumps(v, ensure_ascii=False)]
        else:
            extra_args += ["--es", str(k), str(v)]

    cmdline = ["am", "broadcast", "-a", action] + extra_args
    r = await execute_android_command(cmdline, timeout=10)
    return JSONResponse(content={
        "ok": r["exit_code"] == 0,
        "exit_code": r["exit_code"],
        "stdout": r["stdout"],
        "stderr": r["stderr"],
        "timestamp": datetime.now().isoformat(),
    })


@app.get("/api/macro/commands")
async def macro_commands(_: None = Depends(require_auth)):
    """母艦/ドキュメント側で使う想定の cmd 一覧（MacroDroid側の分岐キー）"""
    return JSONResponse(
        content={
            "commands": [
                "Wake",
                "Home",
                "Back",
                "Recents",
                "ExpandNotifications",
                "ExpandQuickSettings",
                "CollapseStatusBar",
            ],
            "intent_action": os.getenv(
                "PIXEL7_MACRO_INTENT_ACTION",
                "com.manaos.PIXEL7_MACRO",
            ),
            "timestamp": datetime.now().isoformat(),
        }
    )


if __name__ == "__main__":
    port = int(os.getenv("PIXEL7_API_PORT", "5122"))
    uvicorn.run(app, host="0.0.0.0", port=port)
