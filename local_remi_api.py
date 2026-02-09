"""
Local Remi API - Phase 2+3 Status, Voice & Quick Actions
Pixel 7 companion AI backend

Endpoints:
  GET  /status         - System status (GPU, CPU, RAM, tasks)
  GET  /tasks          - Running tasks detail
  GET  /health         - Health check
  POST /tts            - VOICEVOX text-to-speech
  GET  /tts/speakers   - Available VOICEVOX speakers
  GET  /dashboard      - Status dashboard HTML (PWA)
  POST /action/{name}  - Quick actions (comfyui, ollama, etc.)
  POST /emergency-stop - Kill GPU processes
  POST /chat           - Send message to Open WebUI
  GET  /notifications  - Push notification status
"""

from fastapi import FastAPI, Response, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, Response
import psutil
import subprocess
import json
import time
import asyncio
import httpx
import io
import os
from datetime import datetime
from typing import Optional, List

app = FastAPI(title="Local Remi API", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# Notification Store
# ============================================================
notification_log: List[dict] = []
MAX_NOTIFICATIONS = 50

# ============================================================
# System Status
# ============================================================

def get_gpu_info():
    """GPU情報を取得（nvidia-smi使用）"""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu,name",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split(", ")
            return {
                "usage_percent": float(parts[0]),
                "memory_used_mb": float(parts[1]),
                "memory_total_mb": float(parts[2]),
                "temperature_c": float(parts[3]),
                "name": parts[4] if len(parts) > 4 else "Unknown",
                "available": True
            }
    except Exception as e:
        pass
    return {"usage_percent": 0, "memory_used_mb": 0, "memory_total_mb": 0,
            "temperature_c": 0, "name": "N/A", "available": False}


def get_docker_containers():
    """実行中のDockerコンテナ一覧"""
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}\t{{.Status}}\t{{.Ports}}"],
            capture_output=True, text=True, timeout=10
        )
        containers = []
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                if not line.strip():
                    continue
                parts = line.split("\t")
                containers.append({
                    "name": parts[0],
                    "status": parts[1] if len(parts) > 1 else "",
                    "ports": parts[2] if len(parts) > 2 else ""
                })
        return containers
    except Exception:
        return []


def check_comfyui_queue():
    """ComfyUIのキュー状況"""
    try:
        import urllib.request
        req = urllib.request.urlopen("http://127.0.0.1:8188/prompt", timeout=2)
        data = json.loads(req.read())
        return {"queue_remaining": data.get("exec_info", {}).get("queue_remaining", 0)}
    except Exception:
        return {"queue_remaining": 0, "status": "offline"}


def check_ollama_models():
    """Ollamaの読み込み済みモデル"""
    try:
        import urllib.request
        req = urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=3)
        data = json.loads(req.read())
        models = [m["name"] for m in data.get("models", [])]
        return {"models": models, "count": len(models), "status": "online"}
    except Exception:
        return {"models": [], "count": 0, "status": "offline"}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "local-remi-api", "timestamp": datetime.now().isoformat()}


@app.get("/status")
async def get_status():
    """システム全体のステータス"""
    gpu = get_gpu_info()
    cpu_percent = psutil.cpu_percent(interval=0.5)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage("C:\\")

    return {
        "timestamp": datetime.now().isoformat(),
        "gpu": gpu,
        "cpu": {
            "usage_percent": cpu_percent,
            "cores": psutil.cpu_count()
        },
        "ram": {
            "usage_percent": ram.percent,
            "used_gb": round(ram.used / (1024**3), 1),
            "total_gb": round(ram.total / (1024**3), 1)
        },
        "disk": {
            "usage_percent": round(disk.percent, 1),
            "free_gb": round(disk.free / (1024**3), 1)
        },
        "uptime_hours": round((time.time() - psutil.boot_time()) / 3600, 1)
    }


@app.get("/tasks")
async def get_tasks():
    """実行中のタスク一覧"""
    containers = get_docker_containers()
    comfyui = check_comfyui_queue()
    ollama = check_ollama_models()

    # 重要プロセス検出
    important_processes = []
    for proc in psutil.process_iter(["name", "cpu_percent", "memory_percent"]):
        try:
            name = proc.info["name"].lower()
            if any(k in name for k in ["python", "ollama", "comfy", "stable", "kohya", "lora"]):
                if proc.info["cpu_percent"] > 5:
                    important_processes.append({
                        "name": proc.info["name"],
                        "cpu": round(proc.info["cpu_percent"], 1),
                        "ram": round(proc.info["memory_percent"], 1)
                    })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return {
        "docker_containers": containers,
        "comfyui": comfyui,
        "ollama": ollama,
        "active_processes": sorted(important_processes, key=lambda x: x["cpu"], reverse=True)[:10],
        "is_busy": any(p["cpu"] > 50 for p in important_processes)
    }


# ============================================================
# VOICEVOX TTS
# ============================================================

VOICEVOX_URL = "http://127.0.0.1:50021"

@app.post("/tts")
async def text_to_speech(
    text: str = Query(..., description="Text to speak"),
    speaker: int = Query(0, description="VOICEVOX speaker ID (0=Zundamon, 1=Shikoku Metan)"),
    speed: float = Query(1.1, description="Speech speed")
):
    """VOICEVOX音声合成 - WAVデータを返す"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Step 1: Audio query
            query_resp = await client.post(
                f"{VOICEVOX_URL}/audio_query",
                params={"text": text, "speaker": speaker}
            )
            if query_resp.status_code != 200:
                return {"error": "VOICEVOX audio_query failed", "detail": query_resp.text}

            query_data = query_resp.json()
            query_data["speedScale"] = speed

            # Step 2: Synthesis
            synth_resp = await client.post(
                f"{VOICEVOX_URL}/synthesis",
                params={"speaker": speaker},
                json=query_data
            )
            if synth_resp.status_code != 200:
                return {"error": "VOICEVOX synthesis failed", "detail": synth_resp.text}

            return StreamingResponse(
                io.BytesIO(synth_resp.content),
                media_type="audio/wav",
                headers={"Content-Disposition": "inline; filename=speech.wav"}
            )
    except httpx.ConnectError:
        return {"error": "VOICEVOX not running", "hint": "Start VOICEVOX on port 50021"}
    except Exception as e:
        return {"error": str(e)}


@app.get("/tts/speakers")
async def get_speakers():
    """利用可能なVOICEVOX話者一覧"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{VOICEVOX_URL}/speakers")
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass
    return {"error": "VOICEVOX not available", "fallback_speakers": [
        {"name": "ずんだもん", "id": 0},
        {"name": "四国めたん", "id": 2},
        {"name": "春日部つむぎ", "id": 8}
    ]}


# ============================================================
# Dashboard (Pixel 7向け)
# ============================================================

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Pixel 7向けステータスダッシュボード（PWA対応）"""
    dashboard_path = os.path.join(os.path.dirname(__file__), "remi_dashboard.html")
    try:
        with open(dashboard_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>Dashboard file not found</h1>"


@app.get("/manifest.json")
async def manifest():
    manifest_path = os.path.join(os.path.dirname(__file__), "remi_manifest.json")
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            return JSONResponse(content=json.load(f), media_type="application/manifest+json")
    except FileNotFoundError:
        return JSONResponse(content={}, status_code=404)


@app.get("/sw.js")
async def service_worker():
    """Service Worker for PWA"""
    sw_path = os.path.join(os.path.dirname(__file__), "remi_sw.js")
    try:
        with open(sw_path, "r", encoding="utf-8") as f:
            return Response(content=f.read(), media_type="application/javascript")
    except FileNotFoundError:
        return Response(content="// SW not found", media_type="application/javascript")


# ============================================================
# Emergency Stop
# ============================================================

@app.post("/emergency-stop")
async def emergency_stop():
    """緊急停止 - GPU重いプロセスを止める"""
    stopped = []
    for proc in psutil.process_iter(["name", "cpu_percent"]):
        try:
            name = proc.info["name"].lower()
            if any(k in name for k in ["comfy", "kohya", "stable-diffusion"]):
                proc.terminate()
                stopped.append(proc.info["name"])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    add_notification("emergency", f"Emergency stop: {len(stopped)} processes killed")
    return {"stopped": stopped, "message": f"Stopped {len(stopped)} processes"}


# ============================================================
# Quick Actions (Phase 3)
# ============================================================

ACTIONS = {
    "comfyui_start": {
        "name": "Start ComfyUI",
        "cmd": ["python", "C:\\Users\\mana4\\Desktop\\ComfyUI\\main.py", "--listen", "0.0.0.0"],
        "background": True
    },
    "comfyui_stop": {
        "name": "Stop ComfyUI",
        "kill": "main.py"
    },
    "ollama_pull": {
        "name": "Pull Ollama Model",
        "cmd": ["ollama", "pull"],
        "needs_arg": True
    },
    "clear_vram": {
        "name": "Clear VRAM",
        "cmd": ["nvidia-smi", "--gpu-reset"],
        "background": False
    },
    "docker_cleanup": {
        "name": "Docker Cleanup",
        "cmd": ["docker", "system", "prune", "-f"],
        "background": False
    },
}


@app.post("/action/{action_name}")
async def run_action(action_name: str, arg: Optional[str] = Query(None)):
    """クイックアクション実行"""
    if action_name not in ACTIONS:
        return JSONResponse(
            status_code=404,
            content={"error": f"Unknown action: {action_name}", "available": list(ACTIONS.keys())}
        )

    action = ACTIONS[action_name]

    # Kill process type
    if "kill" in action:
        killed = []
        for proc in psutil.process_iter(["name", "cmdline"]):
            try:
                cmdline = " ".join(proc.info.get("cmdline") or [])
                if action["kill"] in cmdline:
                    proc.terminate()
                    killed.append(proc.info["name"])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        add_notification("action", f"{action['name']}: killed {len(killed)} processes")
        return {"action": action_name, "killed": killed}

    # Command type
    cmd = list(action["cmd"])
    if action.get("needs_arg"):
        if not arg:
            return JSONResponse(status_code=400, content={"error": "This action requires 'arg' parameter"})
        cmd.append(arg)

    try:
        if action.get("background"):
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            add_notification("action", f"{action['name']} started")
            return {"action": action_name, "status": "started"}
        else:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            add_notification("action", f"{action['name']} completed (exit={result.returncode})")
            return {
                "action": action_name,
                "status": "completed",
                "exit_code": result.returncode,
                "output": result.stdout[:500] if result.stdout else "",
                "error": result.stderr[:500] if result.stderr else ""
            }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/actions")
async def list_actions():
    """利用可能なアクション一覧"""
    return {name: {"name": a["name"], "needs_arg": a.get("needs_arg", False)}
            for name, a in ACTIONS.items()}


# ============================================================
# Chat Proxy (Phase 3)
# ============================================================

OPENWEBUI_URL = "http://127.0.0.1:3001"

@app.post("/chat")
async def send_chat(message: str = Query(...), model: str = Query("llama3:8b")):
    """Open WebUIにチャットを送信（Pixel 7から直接API呼び出し用）"""
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{OPENWEBUI_URL}/api/chat/completions",
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": message}],
                    "stream": False
                },
                headers={"Content-Type": "application/json"}
            )
            if resp.status_code == 200:
                data = resp.json()
                reply = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                return {"reply": reply, "model": model}
            else:
                return {"error": f"Open WebUI returned {resp.status_code}", "detail": resp.text[:300]}
    except Exception as e:
        return {"error": str(e)}


# ============================================================
# Notifications (Phase 3)
# ============================================================

def add_notification(category: str, message: str):
    """通知を追加"""
    notification_log.append({
        "id": len(notification_log) + 1,
        "category": category,
        "message": message,
        "timestamp": datetime.now().isoformat(),
        "read": False
    })
    if len(notification_log) > MAX_NOTIFICATIONS:
        notification_log.pop(0)


@app.get("/notifications")
async def get_notifications(unread_only: bool = Query(False)):
    """通知一覧取得"""
    if unread_only:
        return [n for n in notification_log if not n["read"]]
    return notification_log[-20:]


@app.post("/notifications/read")
async def mark_notifications_read():
    """全通知を既読にする"""
    for n in notification_log:
        n["read"] = True
    return {"marked": len(notification_log)}


# ============================================================
# Background Monitor (proactive notifications)
# ============================================================

async def background_monitor():
    """バックグラウンドでシステムを監視し、異常時に通知"""
    while True:
        try:
            gpu = get_gpu_info()
            if gpu["available"]:
                if gpu["temperature_c"] > 85:
                    add_notification("warning", f"GPU temp high: {gpu['temperature_c']}C")
                if gpu["memory_used_mb"] / max(gpu["memory_total_mb"], 1) > 0.95:
                    add_notification("warning", f"GPU VRAM almost full: {gpu['memory_used_mb']:.0f}MB")

            ram = psutil.virtual_memory()
            if ram.percent > 90:
                add_notification("warning", f"RAM usage high: {ram.percent}%")

            disk = psutil.disk_usage("C:\\")
            if disk.percent > 95:
                add_notification("warning", f"Disk almost full: {disk.percent}%")
        except Exception:
            pass
        await asyncio.sleep(60)  # Check every 60 seconds


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(background_monitor())
    add_notification("system", "Remi API started")


# ============================================================
# Entry point
# ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5050, log_level="info")
