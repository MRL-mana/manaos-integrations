"""Local Remi API - Pixel 7 Companion AI Backend

Endpoints:
  GET  /status         - System status (GPU, CPU, RAM, Disk)
  GET  /tasks          - Running tasks detail
  GET  /health         - Health check
  POST /tts            - VOICEVOX text-to-speech
  GET  /tts/speakers   - Available VOICEVOX speakers
  GET  /dashboard      - Status dashboard HTML (PWA)
  POST /action/{name}  - Quick actions (comfyui, ollama, etc.)
  POST /emergency-stop - Kill GPU processes
  POST /chat           - Send message via Ollama (direct)
  DELETE /chat/history  - Clear chat history
  GET  /notifications  - Notification list
  POST /notifications/read - Mark all read
  GET  /suggestions    - Proactive AI suggestions
  GET  /widget         - Compact widget view for Android home screen

Security: Bearer token via REMI_API_TOKEN env var
"""

from fastapi import FastAPI, Query, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
import psutil
import subprocess
import json
import time
import asyncio
import httpx
import io
import os
import logging
import secrets
from datetime import datetime
from typing import Optional, List

# ============================================================
# Security
# ============================================================
API_TOKEN = os.getenv("REMI_API_TOKEN", "")
if not API_TOKEN:
    API_TOKEN = secrets.token_hex(32)
    print(f"[Remi] Generated API token: {API_TOKEN}")
    print(f"[Remi] Set REMI_API_TOKEN env var to persist this token")

security = HTTPBearer(auto_error=False)

async def verify_token(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """Verify Bearer token. Dashboard/manifest/sw.js/health are exempt."""
    if not credentials or credentials.credentials != API_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing API token")
    return credentials

# ============================================================
# Audit Log
# ============================================================
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

audit_logger = logging.getLogger("remi_audit")
audit_logger.setLevel(logging.INFO)
_handler = logging.FileHandler(os.path.join(LOG_DIR, "remi_api_audit.log"), encoding="utf-8")
_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
audit_logger.addHandler(_handler)

# ============================================================
# Lifespan (replaces deprecated @app.on_event)
# ============================================================
_monitor_task = None

@asynccontextmanager
async def lifespan(app):
    global _monitor_task
    _monitor_task = asyncio.create_task(background_monitor())
    add_notification("system", "Remi API started")
    audit_logger.info("Remi API started")
    yield
    if _monitor_task:
        _monitor_task.cancel()
    audit_logger.info("Remi API stopped")

app = FastAPI(title="Local Remi API", version="4.1.0", lifespan=lifespan)

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
_last_notif_messages: dict = {}  # category -> (message, timestamp) for dedup

# ============================================================
# Proactive Suggestions Store
# ============================================================
suggestion_log: List[dict] = []
MAX_SUGGESTIONS = 10
_last_suggestion_keys: dict = {}  # key -> timestamp for dedup (15 min)

# ============================================================
# System Status
# ============================================================

def get_gpu_info():
    """Get GPU info via nvidia-smi"""
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
    """List running Docker containers"""
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
    """Check ComfyUI queue status"""
    try:
        import urllib.request
        req = urllib.request.urlopen("http://127.0.0.1:8188/prompt", timeout=2)
        data = json.loads(req.read())
        return {"queue_remaining": data.get("exec_info", {}).get("queue_remaining", 0)}
    except Exception:
        return {"queue_remaining": 0, "status": "offline"}


def check_ollama_models():
    """List loaded Ollama models"""
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
    return {"status": "ok", "service": "local-remi-api", "version": "4.1.0",
            "timestamp": datetime.now().isoformat()}


@app.get("/status", dependencies=[Depends(verify_token)])
async def get_status():
    """Full system status (GPU, CPU, RAM, Disk)"""
    gpu = get_gpu_info()
    cpu_percent = psutil.cpu_percent(interval=0.5)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage("C:\\")

    return {
        "timestamp": datetime.now().isoformat(),
        "gpu": gpu,
        "cpu": {
            "percent": cpu_percent,
            "usage_percent": cpu_percent,
            "cores": psutil.cpu_count()
        },
        "memory": {
            "percent": ram.percent,
            "usage_percent": ram.percent,
            "used_gb": round(ram.used / (1024**3), 1),
            "total_gb": round(ram.total / (1024**3), 1)
        },
        "ram": {
            "percent": ram.percent,
            "usage_percent": ram.percent,
            "used_gb": round(ram.used / (1024**3), 1),
            "total_gb": round(ram.total / (1024**3), 1)
        },
        "disk": {
            "percent": round(disk.percent, 1),
            "usage_percent": round(disk.percent, 1),
            "free_gb": round(disk.free / (1024**3), 1)
        },
        "docker": {"containers": get_docker_containers()},
        "ollama": check_ollama_models(),
        "uptime_hours": round((time.time() - psutil.boot_time()) / 3600, 1)
    }


@app.get("/tasks", dependencies=[Depends(verify_token)])
async def get_tasks():
    """List running tasks and containers"""
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


async def verify_token_or_query(request: Request):
    """Verify Bearer token OR query param token (for audio src= tags)"""
    # Check Authorization header first
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer ") and auth[7:] == API_TOKEN:
        return True
    # Fallback: check query param (for <audio src= direct access)
    qt = request.query_params.get("token", "")
    if qt == API_TOKEN:
        return True
    raise HTTPException(status_code=401, detail="Invalid or missing API token")


@app.api_route("/tts", methods=["GET", "POST"], dependencies=[Depends(verify_token_or_query)])
async def text_to_speech(
    text: str = Query(..., description="Text to speak"),
    speaker: int = Query(0, description="VOICEVOX speaker ID (0=Zundamon, 1=Shikoku Metan)"),
    speed: float = Query(1.1, description="Speech speed")
):
    """VOICEVOX TTS - returns WAV audio (GET for browser Audio(), POST for API)"""
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


@app.get("/tts/speakers", dependencies=[Depends(verify_token)])
async def get_speakers():
    """List available VOICEVOX speakers"""
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
    """Pixel 7 status dashboard (PWA)"""
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


@app.get("/widget", response_class=HTMLResponse)
async def widget(token: str = Query("")):
    """Compact widget view for Android home screen (token via query param)"""
    if token != API_TOKEN:
        return HTMLResponse("<h3 style='color:red'>Auth Error</h3>", status_code=401)
    gpu = get_gpu_info()
    cpu_pct = psutil.cpu_percent(interval=0.3)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage("C:\\")
    # Latest suggestion
    active_sug = [s for s in suggestion_log if not s["dismissed"]]
    sug_html = ""
    if active_sug:
        s = active_sug[-1]
        sug_html = f'<div style="margin-top:6px;font-size:11px;color:#ffd54f">{s["icon"]} {s["message"]}</div>'
    # Unread notifications count
    unread = sum(1 for n in notification_log if not n["read"])
    notif_dot = f'<span style="color:#f44336"> ({unread})</span>' if unread > 0 else ''
    html = f"""<!DOCTYPE html><html><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  *{{margin:0;padding:0;box-sizing:border-box}}
  body{{font-family:system-ui;background:#0a0a0f;color:#e0e0e0;padding:8px;min-width:180px}}
  .row{{display:flex;justify-content:space-between;padding:3px 0;font-size:13px}}
  .label{{color:#888}}
  .val{{font-weight:700}}
  .bar{{height:4px;border-radius:2px;margin:2px 0 4px;background:#1a1a2e;overflow:hidden}}
  .fill{{height:100%;border-radius:2px}}
  .gpu{{background:linear-gradient(90deg,#4CAF50,#FF9800)}}
  .cpu{{background:linear-gradient(90deg,#2196F3,#FF5722)}}
  .ram{{background:linear-gradient(90deg,#9C27B0,#E91E63)}}
  .dsk{{background:linear-gradient(90deg,#00BCD4,#FF5722)}}
  .hdr{{text-align:center;font-size:14px;font-weight:700;padding:2px 0 6px;
        background:linear-gradient(135deg,#667eea,#764ba2);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
  a{{color:#667eea;text-decoration:none;font-size:11px;display:block;text-align:center;margin-top:6px}}
</style></head><body>
<div class="hdr">Remi{notif_dot}</div>
<div class="row"><span class="label">GPU</span><span class="val">{gpu['usage_percent']:.0f}% {gpu['temperature_c']:.0f}C</span></div>
<div class="bar"><div class="fill gpu" style="width:{gpu['usage_percent']}%"></div></div>
<div class="row"><span class="label">CPU</span><span class="val">{cpu_pct:.0f}%</span></div>
<div class="bar"><div class="fill cpu" style="width:{cpu_pct}%"></div></div>
<div class="row"><span class="label">RAM</span><span class="val">{ram.percent:.0f}%</span></div>
<div class="bar"><div class="fill ram" style="width:{ram.percent}%"></div></div>
<div class="row"><span class="label">Disk</span><span class="val">{disk.percent:.0f}%</span></div>
<div class="bar"><div class="fill dsk" style="width:{disk.percent}%"></div></div>
{sug_html}
<a href="/dashboard">Open Dashboard</a>
<script>setTimeout(()=>location.reload(),10000)</script>
</body></html>"""
    return html


# ============================================================
# Emergency Stop
# ============================================================

@app.post("/emergency-stop", dependencies=[Depends(verify_token)])
async def emergency_stop():
    """Emergency stop - kill GPU-heavy processes"""
    audit_logger.warning("EMERGENCY STOP triggered")
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
        "special": "clear_vram"
    },
    "docker_cleanup": {
        "name": "Docker Cleanup",
        "cmd": ["docker", "system", "prune", "-f"],
        "background": False
    },
}


@app.post("/action/{action_name}", dependencies=[Depends(verify_token)])
async def run_action(action_name: str, arg: Optional[str] = Query(None)):
    """Execute a quick action"""
    audit_logger.info(f"Action: {action_name} (arg={arg})")
    if action_name not in ACTIONS:
        return JSONResponse(
            status_code=404,
            content={"error": f"Unknown action: {action_name}", "available": list(ACTIONS.keys())}
        )

    action = ACTIONS[action_name]

    # Special actions
    if "special" in action:
        if action["special"] == "clear_vram":
            # Kill GPU-heavy python processes (not essential ones)
            cleared = []
            for proc in psutil.process_iter(["name", "cmdline", "cpu_percent"]):
                try:
                    cmdline = " ".join(proc.info.get("cmdline") or [])
                    if any(k in cmdline.lower() for k in ["comfy", "kohya", "stable-diffusion", "train"]):
                        proc.terminate()
                        cleared.append(proc.info["name"])
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            # Also try to clear CUDA cache via a quick Python call
            try:
                subprocess.run(
                    ["python", "-c", "import torch; torch.cuda.empty_cache(); print('CUDA cache cleared')"],
                    capture_output=True, timeout=10
                )
            except Exception:
                pass  # torch may not be installed in this env
            add_notification("action", f"VRAM cleared: {len(cleared)} processes stopped")
            return {"action": action_name, "cleared_processes": cleared}

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


@app.get("/actions", dependencies=[Depends(verify_token)])
async def list_actions():
    """List available actions"""
    return {name: {"name": a["name"], "needs_arg": a.get("needs_arg", False)}
            for name, a in ACTIONS.items()}


# ============================================================
# Chat Proxy (Phase 3)
# ============================================================

OLLAMA_URL = "http://127.0.0.1:11434"

# Chat history (persisted to file)
CHAT_HISTORY_FILE = os.path.join(os.path.dirname(__file__), "logs", "chat_history.json")
MAX_CHAT_HISTORY = 50

def _load_chat_history() -> List[dict]:
    """Load chat history from disk"""
    try:
        if os.path.exists(CHAT_HISTORY_FILE):
            with open(CHAT_HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return []

def _save_chat_history():
    """Save chat history to disk"""
    try:
        with open(CHAT_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(chat_history[-MAX_CHAT_HISTORY:], f, ensure_ascii=False, indent=1)
    except Exception:
        pass

chat_history: List[dict] = _load_chat_history()

@app.post("/chat", dependencies=[Depends(verify_token)])
async def send_chat(message: str = Query(...), model: str = Query("llama3:8b"),
                    system: str = Query("You are Remi, a helpful AI companion. Reply concisely in the user's language.")):
    """Send chat via Ollama direct (from Pixel 7)"""
    audit_logger.info(f"Chat: model={model} msg_len={len(message)}")
    chat_history.append({"role": "user", "content": message, "ts": datetime.now().isoformat()})
    if len(chat_history) > MAX_CHAT_HISTORY:
        chat_history.pop(0)
    _save_chat_history()

    messages = [{"role": "system", "content": system}] + chat_history[-10:]

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": False
                }
            )
            if resp.status_code == 200:
                data = resp.json()
                reply = data.get("message", {}).get("content", "")
                chat_history.append({"role": "assistant", "content": reply, "ts": datetime.now().isoformat()})
                _save_chat_history()
                return {"reply": reply, "model": model}
            else:
                return {"error": f"Ollama returned {resp.status_code}", "detail": resp.text[:300]}
    except httpx.ConnectError:
        return {"error": "Ollama not running", "hint": "Start Ollama on port 11434"}
    except Exception as e:
        return {"error": str(e)}


@app.get("/chat/history", dependencies=[Depends(verify_token)])
async def get_chat_history():
    """Get chat history"""
    return {"history": chat_history, "count": len(chat_history)}


@app.delete("/chat/history", dependencies=[Depends(verify_token)])
async def clear_chat_history():
    """Clear chat history"""
    chat_history.clear()
    _save_chat_history()
    return {"status": "cleared"}


# ============================================================
# Notifications (Phase 3)
# ============================================================

def add_notification(category: str, message: str):
    """Add notification (dedup same message within 5 min)"""
    now = datetime.now()
    key = f"{category}:{message}"
    last = _last_notif_messages.get(key)
    if last and (now - last).total_seconds() < 300:
        return  # 5分以内の重複はスキップ
    _last_notif_messages[key] = now

    notification_log.append({
        "id": len(notification_log) + 1,
        "category": category,
        "message": message,
        "timestamp": now.isoformat(),
        "read": False
    })
    if len(notification_log) > MAX_NOTIFICATIONS:
        notification_log.pop(0)


@app.get("/notifications", dependencies=[Depends(verify_token)])
async def get_notifications(unread_only: bool = Query(False)):
    """Get notification list"""
    if unread_only:
        return [n for n in notification_log if not n["read"]]
    return notification_log[-20:]


@app.post("/notifications/read", dependencies=[Depends(verify_token)])
async def mark_notifications_read():
    """Mark all notifications as read"""
    for n in notification_log:
        n["read"] = True
    return {"marked": len(notification_log)}


# ============================================================
# Proactive Suggestions
# ============================================================

def add_suggestion(key: str, message: str, action: str = "", icon: str = "💡"):
    """Add a proactive suggestion (dedup same key within 15 min)"""
    now = datetime.now()
    last = _last_suggestion_keys.get(key)
    if last and (now - last).total_seconds() < 900:
        return
    _last_suggestion_keys[key] = now

    # Remove old suggestion with same key
    for i, s in enumerate(suggestion_log):
        if s.get("key") == key:
            suggestion_log.pop(i)
            break

    suggestion_log.append({
        "id": len(suggestion_log) + 1,
        "key": key,
        "message": message,
        "action": action,
        "icon": icon,
        "timestamp": now.isoformat(),
        "dismissed": False
    })
    if len(suggestion_log) > MAX_SUGGESTIONS:
        suggestion_log.pop(0)


@app.get("/suggestions", dependencies=[Depends(verify_token)])
async def get_suggestions():
    """Get proactive suggestions based on system state"""
    return [s for s in suggestion_log if not s["dismissed"]]


@app.post("/suggestions/{suggestion_id}/dismiss", dependencies=[Depends(verify_token)])
async def dismiss_suggestion(suggestion_id: int):
    """Dismiss a suggestion"""
    for s in suggestion_log:
        if s["id"] == suggestion_id:
            s["dismissed"] = True
            return {"status": "dismissed"}
    return JSONResponse(status_code=404, content={"error": "Suggestion not found"})


# ============================================================
# Background Monitor (proactive alerts + suggestions)
# ============================================================

async def background_monitor():
    """Background system monitor - proactive alerts and smart suggestions"""
    _last_chat_time = time.time()
    _consecutive_errors = 0
    while True:
        try:
            gpu = get_gpu_info()
            _consecutive_errors = 0  # Reset on success

            # === Alerts ===
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

            # === Proactive Suggestions ===
            # GPU idle + VRAM free -> suggest image generation
            if gpu["available"]:
                vram_pct = gpu["memory_used_mb"] / max(gpu["memory_total_mb"], 1) * 100
                if gpu["usage_percent"] < 10 and vram_pct < 30:
                    add_suggestion(
                        "gpu_idle_create",
                        "GPUが空いてるよ！画像生成する？",
                        action="comfyui_start",
                        icon="🎨"
                    )
                elif gpu["usage_percent"] > 90:
                    add_suggestion(
                        "gpu_busy_wait",
                        "GPU使用中...完了したら通知するね",
                        action="",
                        icon="⏳"
                    )

            # VRAM almost full -> suggest clear
            if gpu["available"] and gpu["memory_used_mb"] / max(gpu["memory_total_mb"], 1) > 0.80:
                add_suggestion(
                    "vram_high_clear",
                    f"VRAM {gpu['memory_used_mb']:.0f}MB使用中。クリアする？",
                    action="clear_vram",
                    icon="🧹"
                )

            # Disk getting full -> suggest cleanup
            if disk.percent > 85:
                add_suggestion(
                    "disk_cleanup",
                    f"ディスク{disk.percent}%使用中。Docker cleanupする？",
                    action="docker_cleanup",
                    icon="💾"
                )

            # RAM high + many Docker containers -> suggest pruning
            if ram.percent > 80:
                containers = get_docker_containers()
                if len(containers) > 15:
                    add_suggestion(
                        "too_many_docker",
                        f"RAM{ram.percent}% + Docker{len(containers)}台。不要なもの止める？",
                        action="docker_cleanup",
                        icon="🐳"
                    )

            # Ollama available + no recent chat -> suggest chatting
            ollama = check_ollama_models()
            if ollama["status"] == "online" and len(chat_history) == 0:
                time_since_chat = time.time() - _last_chat_time
                if time_since_chat > 1800:  # 30 min no chat
                    add_suggestion(
                        "ollama_idle_chat",
                        "暇？何か話そうよ！",
                        action="chat",
                        icon="💬"
                    )

            # Check if GPU task just finished (was busy, now idle)
            if gpu["available"] and gpu["usage_percent"] < 5:
                # Check ComfyUI status
                comfyui = check_comfyui_queue()
                if comfyui.get("queue_remaining", 0) == 0 and comfyui.get("status") != "offline":
                    add_suggestion(
                        "comfyui_done",
                        "ComfyUIのキューが空になったよ！",
                        action="",
                        icon="✅"
                    )

        except Exception as e:
            _consecutive_errors += 1
            if _consecutive_errors <= 3:
                audit_logger.error(f"Background monitor error ({_consecutive_errors}): {e}")
            # Back off on repeated errors
        await asyncio.sleep(60 if _consecutive_errors < 5 else 120)


# ============================================================
# Request Logging Middleware
# ============================================================

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = round((time.time() - start) * 1000, 1)
    # Skip noisy health/status polling
    path = request.url.path
    if path not in ("/health", "/status", "/tasks", "/sw.js"):
        client = request.client.host if request.client else "unknown"
        audit_logger.info(f"{client} {request.method} {path} -> {response.status_code} ({duration}ms)")
    return response


# ============================================================
# Entry point
# ============================================================

if __name__ == "__main__":
    import uvicorn
    # HTTPS via Tailscale certs (if available)
    cert_dir = os.path.expanduser("~/.tailscale-certs")
    ssl_cert = os.path.join(cert_dir, "cert.pem")
    ssl_key = os.path.join(cert_dir, "key.pem")
    ssl_kwargs = {}
    if os.path.exists(ssl_cert) and os.path.exists(ssl_key):
        ssl_kwargs = {"ssl_certfile": ssl_cert, "ssl_keyfile": ssl_key}
        print(f"[Remi] HTTPS enabled with Tailscale certs")
    else:
        print(f"[Remi] Running HTTP (no Tailscale certs at {cert_dir})")
        print(f"[Remi] To enable HTTPS: tailscale cert <hostname> && copy to {cert_dir}")
    uvicorn.run(app, host="0.0.0.0", port=5050, log_level="info", **ssl_kwargs)
