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
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, Response, RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
import psutil
import subprocess
import json
import time

from manaos_process_manager import get_process_manager as _get_pm
import asyncio
import httpx
import io
import os
import logging
import secrets
import base64
import binascii
import tempfile
import re
from datetime import datetime
from typing import Optional, List
from pathlib import Path

from _paths import (
    COMFYUI_PORT,
    FILE_SECRETARY_PORT,
    LEARNING_SYSTEM_PORT,
    LLM_ROUTING_PORT,
    MCP_API_SERVER_PORT,
    MRL_MEMORY_PORT,
    OLLAMA_PORT,
    ORCHESTRATOR_PORT,
    RAG_MEMORY_PORT,
    SECRETARY_API_PORT,
    SECRETARY_SYSTEM_PORT,
    TASK_QUEUE_PORT,
    UNIFIED_API_PORT,
    VOICEVOX_PORT,
    INTENT_ROUTER_PORT,
)


# ============================================================
# Workspace helpers
# ============================================================

_WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
_VENV_PYTHON = _WORKSPACE_ROOT / ".venv" / "Scripts" / "python.exe"


def _workspace_python() -> str:
    if _VENV_PYTHON.exists():
        return str(_VENV_PYTHON)
    return "python"


def _powershell_exe() -> str:
    return "powershell.exe" if os.name == "nt" else "powershell"


def _safe_resolve_workspace_path(rel_path: str) -> Path:
    """Resolve a user-supplied path safely under workspace root."""
    raw = (rel_path or "").strip().lstrip("/\\")
    if not raw:
        raise ValueError("path is empty")
    candidate = (_WORKSPACE_ROOT / raw).resolve()
    workspace = _WORKSPACE_ROOT.resolve()
    try:
        candidate.relative_to(workspace)
    except Exception as e:
        raise ValueError("path escapes workspace") from e
    return candidate


def _run_cmd_capture(cmd: List[str], cwd: Optional[Path] = None, timeout: int = 60) -> dict:
    """Run a command and capture limited output."""
    try:
        result = subprocess.run(
            cmd,
            cwd=str(cwd or _WORKSPACE_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        out = (result.stdout or "")
        err = (result.stderr or "")
        # keep response small
        out_tail = out[-4000:] if out else ""
        err_tail = err[-2000:] if err else ""
        return {
            "ok": result.returncode == 0,
            "exit_code": result.returncode,
            "stdout": out_tail,
            "stderr": err_tail,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _extract_patch_paths(patch_text: str) -> List[str]:
    """Extract file paths from unified diff headers."""
    paths: List[str] = []
    for line in (patch_text or "").splitlines():
        if line.startswith("+++ ") or line.startswith("--- "):
            # examples: '+++ b/manaos_integrations/foo.py' or '--- a/manaos_integrations/foo.py'
            m = re.match(r"^[+\-]{3}\s+[ab]/(.+)$", line.strip())
            if m:
                p = m.group(1).strip()
                if p and p not in paths:
                    paths.append(p)
    return paths


def _is_patch_path_allowed(path: str) -> bool:
    norm = (path or "").replace("\\", "/")
    if not norm or norm.startswith("/"):
        return False
    if ".." in norm.split("/"):
        return False
    # Hard allowlist: only edit files inside manaos_integrations
    return norm.startswith("manaos_integrations/")

# ============================================================
# Security
# ============================================================
API_TOKEN = os.getenv("REMI_API_TOKEN", "")
if not API_TOKEN:
    API_TOKEN = secrets.token_hex(32)
    # トークン値をログに出力しない（セキュリティ）
    print("[Remi] API token auto-generated. Set REMI_API_TOKEN env var to persist.")

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

app = FastAPI(title="Local Remi API", version="4.3.0", lifespan=lifespan)

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
        req = urllib.request.urlopen(f"http://127.0.0.1:{COMFYUI_PORT}/prompt", timeout=2)
        data = json.loads(req.read())
        return {"queue_remaining": data.get("exec_info", {}).get("queue_remaining", 0)}
    except Exception:
        return {"queue_remaining": 0, "status": "offline"}


def check_ollama_models():
    """List loaded Ollama models"""
    try:
        import urllib.request
        req = urllib.request.urlopen(f"http://127.0.0.1:{OLLAMA_PORT}/api/tags", timeout=3)
        data = json.loads(req.read())
        models = [m["name"] for m in data.get("models", [])]
        return {"models": models, "count": len(models), "status": "online"}
    except Exception:
        return {"models": [], "count": 0, "status": "offline"}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "local-remi-api", "version": "4.3.0",
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
    pm = _get_pm()
    for p in pm.list_top_processes(sort_by="cpu", limit=50):
        name = (p.get("name") or "").lower()
        if any(k in name for k in ["python", "ollama", "comfy", "stable", "kohya", "lora"]):
            if p.get("cpu_percent", 0) > 5:
                important_processes.append({
                    "name": p["name"],
                    "cpu": round(p.get("cpu_percent", 0), 1),
                    "ram": round(p.get("memory_mb", 0) / (psutil.virtual_memory().total / (1024**2)) * 100, 1),
                })

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

VOICEVOX_URL = os.getenv("VOICEVOX_URL", f"http://127.0.0.1:{VOICEVOX_PORT}")


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


@app.get("/remi-live", response_class=HTMLResponse)
async def remi_live(token: str = Query(""), mode: str = Query("standalone")):
    """Animated Remi character page for home screen / live wallpaper"""
    if token != API_TOKEN:
        return HTMLResponse("<h3 style='color:red'>Auth Error</h3>", status_code=401)
    char_path = os.path.join(os.path.dirname(__file__), "remi_character.html")
    try:
        with open(char_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return HTMLResponse("<h1>Character file not found</h1>", status_code=404)


@app.get("/remi-wallpaper", response_class=HTMLResponse)
async def remi_wallpaper(request: Request, token: str = Query("")):
    """Full-screen live wallpaper with animated Remi + clock + sky.

    Supports a cookie-based token so the URL can stay clean after the first open.
    """
    cookie_token = request.cookies.get("remi_token", "")
    presented = token or cookie_token
    if presented != API_TOKEN:
        return HTMLResponse("<h3 style='color:red'>Auth Error</h3>", status_code=401)

    # If a token was provided in the query, set cookie and redirect to tokenless URL.
    if token and token == API_TOKEN:
        resp = RedirectResponse(url="/remi-wallpaper", status_code=302)
        resp.set_cookie(
            key="remi_token",
            value=API_TOKEN,
            max_age=60 * 60 * 24 * 365,
            path="/",
            httponly=True,
            samesite="lax",
        )
        return resp

    wp_path = os.path.join(os.path.dirname(__file__), "remi_wallpaper.html")
    try:
        with open(wp_path, "r", encoding="utf-8") as f:
            html = f.read()

        # Inject the token so the page can call APIs without relying on URL parameters.
        bootstrap = f"<script>window.REMI_TOKEN={json.dumps(API_TOKEN)};</script>\n"
        if "</head>" in html:
            html = html.replace("</head>", bootstrap + "</head>", 1)
        else:
            html = bootstrap + html

        resp = HTMLResponse(html)
        # Ensure cookie is present for future clean reloads.
        if cookie_token != API_TOKEN:
            resp.set_cookie(
                key="remi_token",
                value=API_TOKEN,
                max_age=60 * 60 * 24 * 365,
                path="/",
                httponly=True,
                samesite="lax",
            )
        return resp
    except FileNotFoundError:
        return HTMLResponse("<h1>Wallpaper file not found</h1>", status_code=404)


@app.get("/remi-wallpaper/{token}", response_class=HTMLResponse)
async def remi_wallpaper_path_token(token: str):
    """Same as /remi-wallpaper but token is passed in the URL path (no query string)."""
    if token != API_TOKEN:
        return HTMLResponse("<h3 style='color:red'>Auth Error</h3>", status_code=401)

    # Set cookie then redirect to the clean URL.
    resp = RedirectResponse(url="/remi-wallpaper", status_code=302)
    resp.set_cookie(
        key="remi_token",
        value=API_TOKEN,
        max_age=60 * 60 * 24 * 365,
        path="/",
        httponly=True,
        samesite="lax",
    )
    return resp


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
    pm = _get_pm()
    killed = pm.kill_processes_by_keywords(["comfy", "kohya", "stable-diffusion"])
    stopped = [f"process_{i}" for i in range(killed)]  # ProcessManager 経由
    add_notification("emergency", f"Emergency stop: {killed} processes killed")
    return {"stopped": stopped, "message": f"Stopped {killed} processes"}


# ============================================================
# Quick Actions (Phase 3)
# ============================================================

ACTIONS = {
    "comfyui_start": {
        "name": "Start ComfyUI",
        "cmd": ["python", str(Path.home() / "Desktop" / "ComfyUI" / "main.py"), "--listen", "0.0.0.0"],
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

    # --- ManaOS Ops (VS Code でやっている運用操作をチャット/壁紙から実行) ---
    "manaos_start_services": {
        "name": "Start ManaOS Services",
        "cmd": [_workspace_python(), str(_WORKSPACE_ROOT / "manaos_integrations" / "start_vscode_cursor_services.py")],
        "background": True,
        "timeout": 10,
    },
    "manaos_health_check": {
        "name": "ManaOS Health Check",
        "cmd": [_workspace_python(), str(_WORKSPACE_ROOT / "manaos_integrations" / "check_services_health.py")],
        "background": False,
        "timeout": 90,
    },
    "manaos_release_9502": {
        "name": "Release Unified API Port (9510)",
        "cmd": [
            _powershell_exe(),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(_WORKSPACE_ROOT / "manaos_integrations" / "restart_unified_api_port9502.ps1"),
            "-Port",
            "9510",
        ],
        "background": False,
        "timeout": 90,
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
            pm = _get_pm()
            killed = pm.kill_processes_by_keywords(["comfy", "kohya", "stable-diffusion", "train"])
            cleared = [f"process_{i}" for i in range(killed)]
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
        pm = _get_pm()
        killed_count = pm.kill_processes_by_keywords([action["kill"]])
        killed = [f"process_{i}" for i in range(killed_count)]
        add_notification("action", f"{action['name']}: killed {killed_count} processes")
        return {"action": action_name, "killed": killed}

    # Command type
    cmd = list(action["cmd"])
    if action.get("needs_arg"):
        if not arg:
            return JSONResponse(status_code=400, content={"error": "This action requires 'arg' parameter"})
        cmd.append(arg)

    timeout_sec = int(action.get("timeout", 30))

    try:
        if action.get("background"):
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            add_notification("action", f"{action['name']} started")
            return {"action": action_name, "status": "started"}
        else:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec)
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

OLLAMA_URL = os.getenv("OLLAMA_URL", f"http://127.0.0.1:{OLLAMA_PORT}")

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

# Patch buffer for chunked uploads via chat
_PATCH_B64_BUFFER: str = ""  # raw append mode
_PATCH_CHUNKS: dict = {}  # indexed mode: {idx:int -> chunk:str}
_PATCH_EXPECTED_TOTAL: Optional[int] = None
_PATCH_B64_UPDATED_AT: Optional[datetime] = None
_PATCH_MAX_AGE_SEC = 30 * 60


def _patch_buffer_is_stale() -> bool:
    if not _PATCH_B64_UPDATED_AT:
        return False
    return (datetime.now() - _PATCH_B64_UPDATED_AT).total_seconds() > _PATCH_MAX_AGE_SEC


def _patch_buffer_clear():
    global _PATCH_B64_BUFFER, _PATCH_CHUNKS, _PATCH_EXPECTED_TOTAL, _PATCH_B64_UPDATED_AT
    _PATCH_B64_BUFFER = ""
    _PATCH_CHUNKS = {}
    _PATCH_EXPECTED_TOTAL = None
    _PATCH_B64_UPDATED_AT = None


def _patch_buffer_get_b64_or_raise() -> str:
    if _patch_buffer_is_stale():
        _patch_buffer_clear()
        raise ValueError("buffer expired. please /patchbegin again")
    if _PATCH_CHUNKS:
        if not _PATCH_EXPECTED_TOTAL:
            raise ValueError("buffer missing total. use /patchbegin <total> or /patchadd i/total ...")
        missing = [i for i in range(1, _PATCH_EXPECTED_TOTAL + 1) if i not in _PATCH_CHUNKS]
        if missing:
            raise ValueError(f"missing chunks: {missing[:10]}" + (" ..." if len(missing) > 10 else ""))
        return "".join(_PATCH_CHUNKS[i] for i in range(1, _PATCH_EXPECTED_TOTAL + 1))
    if _PATCH_B64_BUFFER:
        return _PATCH_B64_BUFFER
    raise ValueError("buffer is empty. use /patchbegin then /patchadd")

@app.post("/chat", dependencies=[Depends(verify_token)])
async def send_chat(
    request: Request,
    message: Optional[str] = Query(None),
    model: str = Query("qwen2.5:7b"),
    system: str = Query(
        "You are Remi, a cheerful AI companion for your commander. You MUST reply in Japanese only. Never mix Chinese or other languages. Be concise, friendly, and helpful. Use casual Japanese like a close friend."
    ),
):
    """Send chat via Ollama direct (from Pixel 7)

    Compatibility:
      - Existing clients: POST /chat?message=...
      - New clients: POST /chat with JSON body {"message": "..."}
    """
    if message is None:
        try:
            data = await request.json()
            if isinstance(data, dict):
                message = str(data.get("message") or data.get("text") or "")
        except Exception:
            message = ""
    message = (message or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="message is required")

    global _PATCH_B64_BUFFER, _PATCH_B64_UPDATED_AT
    global _PATCH_CHUNKS, _PATCH_EXPECTED_TOTAL

    audit_logger.info(f"Chat: model={model} msg_len={len(message)}")
    chat_history.append({"role": "user", "content": message, "ts": datetime.now().isoformat()})
    if len(chat_history) > MAX_CHAT_HISTORY:
        chat_history.pop(0)
    _save_chat_history()

    # ============================================================
    # Chat Commands (安全な運用コマンド)
    # ============================================================
    cmd = (message or "").strip()
    if cmd.startswith("/") or cmd.startswith("!"):
        body = cmd.lstrip("/!")
        body = body.lstrip()
        m = re.match(r"^(\S+)(?:\s+([\s\S]*))?$", body)
        key = (m.group(1).lower() if m else "")
        rest = (m.group(2) if m and m.group(2) is not None else "")
        args = rest.split() if rest else []

        if key in ("help", "?"):
            reply = (
                "使えるコマンドだよ：\n"
                "- /health : ManaOSのヘルスチェック\n"
                "- /start  : ManaOSサービス起動（まとめて）\n"
                "- /release9502 : 9510ポート解放（Unified API用・互換エイリアス）\n"
                "- /read <path> [start] [end] : ファイル読む（1-based行番号）\n"
                "- /grep <pattern> [glob] : ワークスペース検索\n"
                "- /gitdiff : git diff（差分）\n"
                "- /gitstatus : git status（変更一覧）\n"
                "- /pycheck <path> : Python構文チェック\n"
                "- /queue <text> : VS Code側でやる作業依頼を記録\n"
                "- /applycheck <base64> : unified diffをgit apply --check（検査のみ）\n"
                "- /applypatch <base64> : unified diffをgit apply（manaos_integrations配下のみ）\n"
                "- /checktext <diff> : unified diffを直貼りしてチェック（適用しない）\n"
                "- /applytext <diff> : unified diffを直貼りして適用（manaos_integrations配下のみ）\n"
                "- /patchbegin : 分割パッチ入力開始（バッファ初期化）\n"
                "- /patchbegin <total> : 分割パッチ入力開始（チャンク総数を指定・推奨）\n"
                "- /patchadd <chunk> : 分割パッチ追記（単純追記モード）\n"
                "- /patchadd i/total <chunk> : 分割パッチ追記（番号付き・推奨）\n"
                "- /patchcheck : バッファのパッチをチェック（適用しない）\n"
                "- /patchapply : バッファのパッチを適用\n"
                "- /patchclear : バッファ破棄\n"
                "- /help   : これ"
            )
            chat_history.append({"role": "assistant", "content": reply, "ts": datetime.now().isoformat()})
            _save_chat_history()
            return {"reply": reply, "mode": "command"}

        if key in ("health", "hc"):
            try:
                result = subprocess.run(
                    [_workspace_python(), str(_WORKSPACE_ROOT / "manaos_integrations" / "check_services_health.py")],
                    capture_output=True,
                    text=True,
                    timeout=90,
                )
                out = (result.stdout or "").strip()
                err = (result.stderr or "").strip()

                def _health_summarize(text: str) -> str:
                    t = (text or "").strip()
                    if not t:
                        return ""
                    lines = [ln.rstrip() for ln in t.splitlines() if ln.strip()]

                    # Key lines
                    ng_lines = [ln for ln in lines if ln.lstrip().startswith("[NG]")]
                    warn_lines = [ln for ln in lines if "[!!]" in ln or "要検査" in ln]
                    core_summary = next((ln for ln in reversed(lines) if ln.startswith("[コア]")), "")
                    ok_line = next((ln for ln in reversed(lines) if ln.startswith("[OK]")), "")
                    bad_line = next((ln for ln in reversed(lines) if ln.startswith("[!!]")), "")
                    action_line = next((ln for ln in lines if "対処:" in ln), "")

                    # Prefer a short, actionable reply
                    parts = []
                    if bad_line:
                        parts.append(bad_line)
                    if core_summary:
                        parts.append(core_summary)
                    if ng_lines:
                        parts.append("\n".join(ng_lines[:12]))
                        if len(ng_lines) > 12:
                            parts.append(f"... (+{len(ng_lines) - 12} more NG)")
                    if action_line:
                        parts.append(action_line)
                    if not bad_line and ok_line:
                        parts.append(ok_line)

                    # If still empty (format changed), fall back to tail
                    reply0 = "\n".join([p for p in parts if p]).strip()
                    if not reply0:
                        return t[-1800:]

                    # Keep response small
                    return reply0[-2000:]

                summarized = _health_summarize(out)
                reply = summarized if summarized else (err[:1800] if err else "ヘルスチェックの出力が空だったよ")
            except Exception as e:
                reply = f"ヘルスチェック失敗: {e}"

            chat_history.append({"role": "assistant", "content": reply, "ts": datetime.now().isoformat()})
            _save_chat_history()
            return {"reply": reply, "mode": "command"}

        if key in ("start", "up"):
            try:
                subprocess.Popen(
                    [_workspace_python(), str(_WORKSPACE_ROOT / "manaos_integrations" / "start_vscode_cursor_services.py")],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                )
                reply = "了解！ManaOSサービス起動を投げたよ。数秒後に /health してね。"
            except Exception as e:
                reply = f"起動失敗: {e}"

            chat_history.append({"role": "assistant", "content": reply, "ts": datetime.now().isoformat()})
            _save_chat_history()
            return {"reply": reply, "mode": "command"}

        # Backward compatible alias: historically this was "release9502"
        if key in ("release9502", "release"):
            try:
                result = subprocess.run(
                    [
                        _powershell_exe(),
                        "-NoProfile",
                        "-ExecutionPolicy",
                        "Bypass",
                        "-File",
                        str(_WORKSPACE_ROOT / "manaos_integrations" / "restart_unified_api_port9502.ps1"),
                        "-Port",
                        "9510",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=90,
                )
                out = (result.stdout or "").strip()
                err = (result.stderr or "").strip()
                reply = (out[-1200:] if out else "") or (err[-1200:] if err else "ポート解放を実行したよ")
            except Exception as e:
                reply = f"9510解放失敗: {e}"

            chat_history.append({"role": "assistant", "content": reply, "ts": datetime.now().isoformat()})
            _save_chat_history()
            return {"reply": reply, "mode": "command"}

        if key == "read":
            try:
                if not args:
                    raise ValueError("usage: /read <path> [start] [end]")
                path = _safe_resolve_workspace_path(args[0])
                start = int(args[1]) if len(args) >= 2 else 1
                end = int(args[2]) if len(args) >= 3 else start + 200
                start = max(1, start)
                end = max(start, end)

                if not path.exists() or not path.is_file():
                    raise ValueError(f"not found: {args[0]}")

                def _compact(text: str, head: int = 1200, tail: int = 2200, max_total: int = 3800) -> str:
                    t = (text or "").rstrip()
                    if len(t) <= max_total:
                        return t
                    h = t[:head].rstrip()
                    tt = t[-tail:].lstrip()
                    omitted = max(0, len(t) - len(h) - len(tt))
                    return h + f"\n\n... (truncated {omitted} chars) ...\n\n" + tt

                lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
                total = len(lines)
                slice_lines = lines[start - 1 : end]
                preview = "\n".join(f"{i+start}: {line}" for i, line in enumerate(slice_lines))
                header = f"FILE: {args[0]}\nRANGE: {start}-{min(end, total)} (total {total})\n\n"
                reply = header + (preview if preview else "(empty)")
                reply = _compact(reply)
            except Exception as e:
                reply = f"/read 失敗: {e}"

            chat_history.append({"role": "assistant", "content": reply, "ts": datetime.now().isoformat()})
            _save_chat_history()
            return {"reply": reply, "mode": "command"}

        if key == "grep":
            try:
                if not args:
                    raise ValueError("usage: /grep <pattern> [glob]")
                pattern = args[0]
                glob = args[1] if len(args) >= 2 else "**/*"
                # Use PowerShell Select-String (fast on Windows) but restrict scope to workspace
                ps = (
                    "param($pattern,$glob,$root) "
                    "$files=Get-ChildItem -Path $root -Recurse -File -ErrorAction SilentlyContinue | "
                    "Where-Object { $_.FullName -like (Join-Path $root $glob) }; "
                    "$hits=@(); "
                    "foreach($f in $files){ try { $m=Select-String -Path $f.FullName -Pattern $pattern -SimpleMatch -ErrorAction SilentlyContinue; "
                    "foreach($x in $m){ $hits += ($x.Path + ':' + $x.LineNumber + ':' + $x.Line.Trim()); if($hits.Count -ge 50){ break } } } catch {} "
                    "if($hits.Count -ge 50){ break } } "
                    "$hits | Out-String"
                )
                run = _run_cmd_capture(
                    [_powershell_exe(), "-NoProfile", "-Command", ps, "-pattern", pattern, "-glob", glob, "-root", str(_WORKSPACE_ROOT)],
                    cwd=_WORKSPACE_ROOT,
                    timeout=60,
                )
                if run.get("ok"):
                    def _compact(text: str, head: int = 1600, tail: int = 1800, max_total: int = 3800) -> str:
                        t = (text or "").strip()
                        if len(t) <= max_total:
                            return t
                        h = t[:head].rstrip()
                        tt = t[-tail:].lstrip()
                        omitted = max(0, len(t) - len(h) - len(tt))
                        return h + f"\n\n... (truncated {omitted} chars) ...\n\n" + tt

                    out = (run.get("stdout") or "").strip()
                    lines = [ln for ln in out.splitlines() if ln.strip()]
                    if not lines:
                        reply = "(no matches)"
                    else:
                        header = f"Matches: {len(lines)} (showing up to 50)\n"
                        reply = _compact(header + "\n".join(lines))
                else:
                    reply = f"/grep 失敗: {run}"
            except Exception as e:
                reply = f"/grep 失敗: {e}"

            chat_history.append({"role": "assistant", "content": reply, "ts": datetime.now().isoformat()})
            _save_chat_history()
            return {"reply": reply, "mode": "command"}

        if key in ("gitdiff", "diff"):
            def _compact(text: str, head: int = 1400, tail: int = 2200, max_total: int = 3800) -> str:
                t = (text or "").strip()
                if len(t) <= max_total:
                    return t
                h = t[:head].rstrip()
                tt = t[-tail:].lstrip()
                omitted = max(0, len(t) - len(h) - len(tt))
                return h + f"\n\n... (truncated {omitted} chars) ...\n\n" + tt

            # File list first (quick scan)
            names = _run_cmd_capture(
                ["git", "-C", str(_WORKSPACE_ROOT), "diff", "--name-only", "--ignore-submodules=all"],
                cwd=_WORKSPACE_ROOT,
                timeout=30,
            )
            name_out = (names.get("stdout") or "").strip() if names.get("ok") else ""
            if name_out:
                files = [x for x in name_out.splitlines() if x.strip()]
                file_list = "\n".join(files[:30])
                if len(files) > 30:
                    file_list += f"\n... (+{len(files) - 30} more)"
                prefix = "Changed files:\n" + file_list + "\n\n"
            else:
                prefix = ""

            run = _run_cmd_capture(
                [
                    "git",
                    "-C",
                    str(_WORKSPACE_ROOT),
                    "diff",
                    "--no-color",
                    "--ignore-submodules=all",
                ],
                cwd=_WORKSPACE_ROOT,
                timeout=60,
            )
            out = (run.get("stdout") or "").strip()
            err = (run.get("stderr") or "").strip()
            if out:
                reply = prefix + _compact(out)
            else:
                reply = prefix + (err[-1800:] if err else "(no diff / git not available)")
            chat_history.append({"role": "assistant", "content": reply, "ts": datetime.now().isoformat()})
            _save_chat_history()
            return {"reply": reply, "mode": "command"}

        if key in ("gitstatus", "status"):
            run = _run_cmd_capture(
                [
                    "git",
                    "-C",
                    str(_WORKSPACE_ROOT),
                    "status",
                    "--porcelain",
                    "--ignore-submodules=all",
                ],
                cwd=_WORKSPACE_ROOT,
                timeout=30,
            )
            out = (run.get("stdout") or "").strip()
            err = (run.get("stderr") or "").strip()

            def _format_status(porcelain: str) -> str:
                lines = [ln for ln in (porcelain or "").splitlines() if ln.strip()]
                if not lines:
                    return "(clean)"

                buckets = {
                    "M": [],  # modified
                    "A": [],  # added
                    "D": [],  # deleted
                    "R": [],  # renamed
                    "C": [],  # copied
                    "U": [],  # unmerged
                    "?": [],  # untracked
                    "!": [],  # ignored
                    "O": [],  # other
                }

                for ln in lines:
                    if len(ln) < 3:
                        buckets["O"].append(ln)
                        continue
                    x = ln[0]
                    y = ln[1]
                    path = ln[3:].strip()
                    code = "?" if (x == "?" and y == "?") else ("U" if (x == "U" or y == "U") else (x if x != " " else y))
                    if code not in buckets:
                        code = "O"
                    buckets[code].append(path)

                label = {
                    "M": "Modified",
                    "A": "Added",
                    "D": "Deleted",
                    "R": "Renamed",
                    "C": "Copied",
                    "U": "Unmerged",
                    "?": "Untracked",
                    "!": "Ignored",
                    "O": "Other",
                }

                order = ["M", "A", "D", "R", "C", "U", "?", "!", "O"]
                total = len(lines)
                parts = [f"Changes: {total}"]
                for k in order:
                    if buckets[k]:
                        parts.append(f"- {label[k]}: {len(buckets[k])}")

                detail_lines = []
                shown = 0
                cap = 60
                for k in order:
                    if not buckets[k]:
                        continue
                    for p in buckets[k]:
                        if shown >= cap:
                            break
                        detail_lines.append(f"{k} {p}")
                        shown += 1
                    if shown >= cap:
                        break
                if total > cap:
                    detail_lines.append(f"... (+{total - cap} more)")

                return "\n".join(parts) + "\n\n" + "\n".join(detail_lines)

            if out:
                reply = _format_status(out)
                reply = reply[-3800:] if reply else "(clean)"
            else:
                reply = err if err else "(clean)"
            chat_history.append({"role": "assistant", "content": reply, "ts": datetime.now().isoformat()})
            _save_chat_history()
            return {"reply": reply, "mode": "command"}

        if key == "applycheck":
            try:
                if not args:
                    raise ValueError("usage: /applycheck <base64>")
                b64 = "".join(args).strip().replace(" ", "+")
                if len(b64) > 120000:
                    raise ValueError("patch too large")

                try:
                    patch_bytes = base64.b64decode(b64.encode("utf-8"), validate=True)
                except (binascii.Error, ValueError):
                    padded = b64 + "=" * ((4 - (len(b64) % 4)) % 4)
                    patch_bytes = base64.urlsafe_b64decode(padded.encode("utf-8"))
                patch_text = patch_bytes.decode("utf-8", errors="replace")
                if len(patch_text) > 80000:
                    raise ValueError("patch too large")

                paths = _extract_patch_paths(patch_text)
                if not paths:
                    raise ValueError("could not detect paths from diff")
                bad = [p for p in paths if not _is_patch_path_allowed(p)]
                if bad:
                    raise ValueError(f"disallowed paths: {bad}")

                patch_file = None
                try:
                    with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8", suffix=".patch") as tf:
                        tf.write(patch_text)
                        patch_file = tf.name

                    check = _run_cmd_capture(
                        [
                            "git",
                            "-C",
                            str(_WORKSPACE_ROOT),
                            "apply",
                            "--check",
                            "--whitespace=nowarn",
                            patch_file,
                        ],
                        cwd=_WORKSPACE_ROOT,
                        timeout=60,
                    )
                    if check.get("ok"):
                        reply = "チェックOK（まだ適用してないよ）。適用するなら /applypatch <base64> だよ"
                    else:
                        reply = "チェック失敗: " + json.dumps(check, ensure_ascii=False)
                finally:
                    try:
                        if patch_file and os.path.exists(patch_file):
                            os.unlink(patch_file)
                    except Exception:
                        pass
            except Exception as e:
                reply = f"/applycheck 失敗: {e}"

            chat_history.append({"role": "assistant", "content": reply, "ts": datetime.now().isoformat()})
            _save_chat_history()
            return {"reply": reply, "mode": "command"}

        if key in ("checktext", "applytext"):
            try:
                patch_text = (rest or "")
                if not patch_text.strip():
                    raise ValueError(f"usage: /{key} <unified diff text>")
                if len(patch_text) > 80000:
                    raise ValueError("patch too large")

                paths = _extract_patch_paths(patch_text)
                if not paths:
                    raise ValueError("could not detect paths from diff")
                bad = [p for p in paths if not _is_patch_path_allowed(p)]
                if bad:
                    raise ValueError(f"disallowed paths: {bad}")

                patch_file = None
                try:
                    with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8", suffix=".patch") as tf:
                        tf.write(patch_text)
                        patch_file = tf.name

                    check = _run_cmd_capture(
                        [
                            "git",
                            "-C",
                            str(_WORKSPACE_ROOT),
                            "apply",
                            "--check",
                            "--whitespace=nowarn",
                            patch_file,
                        ],
                        cwd=_WORKSPACE_ROOT,
                        timeout=60,
                    )
                    if not check.get("ok"):
                        reply = "チェック失敗: " + json.dumps(check, ensure_ascii=False)
                    elif key == "checktext":
                        reply = "チェックOK（まだ適用してないよ）。適用するなら /applytext <diff> だよ"
                    else:
                        run = _run_cmd_capture(
                            ["git", "-C", str(_WORKSPACE_ROOT), "apply", "--whitespace=nowarn", patch_file],
                            cwd=_WORKSPACE_ROOT,
                            timeout=60,
                        )
                        if run.get("ok"):
                            diff = _run_cmd_capture(
                                [
                                    "git",
                                    "-C",
                                    str(_WORKSPACE_ROOT),
                                    "diff",
                                    "--no-color",
                                    "--ignore-submodules=all",
                                ],
                                cwd=_WORKSPACE_ROOT,
                                timeout=30,
                            )
                            d = (diff.get("stdout") or "").strip()
                            reply = "適用OK。\n" + (d[-2800:] if d else "(no diff)")
                        else:
                            reply = "適用失敗: " + json.dumps(run, ensure_ascii=False)
                finally:
                    try:
                        if patch_file and os.path.exists(patch_file):
                            os.unlink(patch_file)
                    except Exception:
                        pass
            except Exception as e:
                reply = f"/{key} 失敗: {e}"

            chat_history.append({"role": "assistant", "content": reply, "ts": datetime.now().isoformat()})
            _save_chat_history()
            return {"reply": reply, "mode": "command"}

        if key == "patchbegin":
            _patch_buffer_clear()
            _PATCH_B64_UPDATED_AT = datetime.now()
            if args:
                try:
                    _PATCH_EXPECTED_TOTAL = int(args[0])
                    if _PATCH_EXPECTED_TOTAL <= 0 or _PATCH_EXPECTED_TOTAL > 200:
                        raise ValueError("total out of range")
                except Exception:
                    _PATCH_EXPECTED_TOTAL = None
            reply = (
                "OK。分割パッチ入力を開始したよ。"
                "おすすめは /patchadd i/total <chunk> を繰り返して、最後に /patchcheck か /patchapply だよ。"
            )
            chat_history.append({"role": "assistant", "content": reply, "ts": datetime.now().isoformat()})
            _save_chat_history()
            return {"reply": reply, "mode": "command"}

        if key == "patchadd":
            try:
                if not args:
                    raise ValueError("usage: /patchadd <base64chunk>")
                if _patch_buffer_is_stale():
                    _patch_buffer_clear()
                    raise ValueError("buffer expired. please /patchbegin again")

                # tolerate spaces/newlines from chat clients
                cleaned_args = [a.replace("\n", "").replace("\r", "") for a in args]

                # Indexed mode: first token like 3/10
                m = re.match(r"^(\d+)/(\d+)$", cleaned_args[0].strip())
                if m and len(cleaned_args) >= 2:
                    idx = int(m.group(1))
                    total = int(m.group(2))
                    if total <= 0 or total > 200:
                        raise ValueError("total out of range")
                    if idx <= 0 or idx > total:
                        raise ValueError("index out of range")
                    chunk = "".join(cleaned_args[1:]).strip().replace(" ", "+")
                    if not chunk:
                        raise ValueError("chunk is empty")
                    if _PATCH_EXPECTED_TOTAL is None:
                        _PATCH_EXPECTED_TOTAL = total
                    if _PATCH_EXPECTED_TOTAL != total:
                        raise ValueError(f"total mismatch (expected {_PATCH_EXPECTED_TOTAL}, got {total})")
                    # switch to indexed mode
                    if _PATCH_B64_BUFFER:
                        raise ValueError("already in raw mode; /patchbegin to restart")
                    _PATCH_CHUNKS[idx] = chunk
                    _PATCH_B64_UPDATED_AT = datetime.now()
                    got = len(_PATCH_CHUNKS)
                    reply = f"追加OK（{idx}/{total}）。received={got}/{total}。次は /patchadd か /patchcheck だよ。"
                else:
                    # Raw append mode
                    chunk = "".join(cleaned_args).strip().replace(" ", "+")
                    if not chunk:
                        raise ValueError("chunk is empty")
                    if _PATCH_CHUNKS:
                        raise ValueError("already in indexed mode; use /patchadd i/total ...")
                    if len(_PATCH_B64_BUFFER) + len(chunk) > 200000:
                        raise ValueError("buffer too large")
                    _PATCH_B64_BUFFER += chunk
                    _PATCH_B64_UPDATED_AT = datetime.now()
                    reply = f"追加OK。buffer_len={len(_PATCH_B64_BUFFER)}。続けて /patchadd するか、/patchcheck してね。"
            except Exception as e:
                reply = f"/patchadd 失敗: {e}"

            chat_history.append({"role": "assistant", "content": reply, "ts": datetime.now().isoformat()})
            _save_chat_history()
            return {"reply": reply, "mode": "command"}

        if key in ("patchclear", "patchreset"):
            _patch_buffer_clear()
            reply = "バッファを破棄したよ。"
            chat_history.append({"role": "assistant", "content": reply, "ts": datetime.now().isoformat()})
            _save_chat_history()
            return {"reply": reply, "mode": "command"}

        if key in ("patchcheck", "patchapply"):
            try:
                b64 = _patch_buffer_get_b64_or_raise()
                if key == "patchcheck":
                    try:
                        patch_bytes = base64.b64decode(b64.encode("utf-8"), validate=True)
                    except (binascii.Error, ValueError):
                        padded = b64 + "=" * ((4 - (len(b64) % 4)) % 4)
                        patch_bytes = base64.urlsafe_b64decode(padded.encode("utf-8"))
                    patch_text = patch_bytes.decode("utf-8", errors="replace")
                    paths = _extract_patch_paths(patch_text)
                    if not paths:
                        raise ValueError("could not detect paths from diff")
                    bad = [p for p in paths if not _is_patch_path_allowed(p)]
                    if bad:
                        raise ValueError(f"disallowed paths: {bad}")
                    patch_file = None
                    try:
                        with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8", suffix=".patch") as tf:
                            tf.write(patch_text)
                            patch_file = tf.name
                        check = _run_cmd_capture(
                            [
                                "git",
                                "-C",
                                str(_WORKSPACE_ROOT),
                                "apply",
                                "--check",
                                "--whitespace=nowarn",
                                patch_file,
                            ],
                            cwd=_WORKSPACE_ROOT,
                            timeout=60,
                        )
                        if check.get("ok"):
                            reply = "チェックOK（まだ適用してないよ）。このまま適用するなら /patchapply だよ"
                        else:
                            reply = "チェック失敗: " + json.dumps(check, ensure_ascii=False)
                    finally:
                        try:
                            if patch_file and os.path.exists(patch_file):
                                os.unlink(patch_file)
                        except Exception:
                            pass
                else:
                    # patchapply
                    try:
                        patch_bytes = base64.b64decode(b64.encode("utf-8"), validate=True)
                    except (binascii.Error, ValueError):
                        padded = b64 + "=" * ((4 - (len(b64) % 4)) % 4)
                        patch_bytes = base64.urlsafe_b64decode(padded.encode("utf-8"))
                    patch_text = patch_bytes.decode("utf-8", errors="replace")
                    paths = _extract_patch_paths(patch_text)
                    if not paths:
                        raise ValueError("could not detect paths from diff")
                    bad = [p for p in paths if not _is_patch_path_allowed(p)]
                    if bad:
                        raise ValueError(f"disallowed paths: {bad}")
                    patch_file = None
                    try:
                        with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8", suffix=".patch") as tf:
                            tf.write(patch_text)
                            patch_file = tf.name
                        check = _run_cmd_capture(
                            [
                                "git",
                                "-C",
                                str(_WORKSPACE_ROOT),
                                "apply",
                                "--check",
                                "--whitespace=nowarn",
                                patch_file,
                            ],
                            cwd=_WORKSPACE_ROOT,
                            timeout=60,
                        )
                        if not check.get("ok"):
                            reply = "適用前チェック失敗: " + json.dumps(check, ensure_ascii=False)
                        else:
                            run = _run_cmd_capture(
                                ["git", "-C", str(_WORKSPACE_ROOT), "apply", "--whitespace=nowarn", patch_file],
                                cwd=_WORKSPACE_ROOT,
                                timeout=60,
                            )
                            if run.get("ok"):
                                _patch_buffer_clear()
                                diff = _run_cmd_capture(
                                    [
                                        "git",
                                        "-C",
                                        str(_WORKSPACE_ROOT),
                                        "diff",
                                        "--no-color",
                                        "--ignore-submodules=all",
                                    ],
                                    cwd=_WORKSPACE_ROOT,
                                    timeout=30,
                                )
                                d = (diff.get("stdout") or "").strip()
                                reply = "適用OK。\n" + (d[-2800:] if d else "(no diff)")
                            else:
                                reply = "適用失敗: " + json.dumps(run, ensure_ascii=False)
                    finally:
                        try:
                            if patch_file and os.path.exists(patch_file):
                                os.unlink(patch_file)
                        except Exception:
                            pass
            except Exception as e:
                reply = f"/{key} 失敗: {e}"

            chat_history.append({"role": "assistant", "content": reply, "ts": datetime.now().isoformat()})
            _save_chat_history()
            return {"reply": reply, "mode": "command"}

        if key == "applypatch":
            try:
                if not args:
                    raise ValueError("usage: /applypatch <base64>")
                b64 = "".join(args).strip().replace(" ", "+")
                if len(b64) > 120000:
                    raise ValueError("patch too large")

                try:
                    patch_bytes = base64.b64decode(b64.encode("utf-8"), validate=True)
                except (binascii.Error, ValueError):
                    # Accept URL-safe base64 too
                    padded = b64 + "=" * ((4 - (len(b64) % 4)) % 4)
                    patch_bytes = base64.urlsafe_b64decode(padded.encode("utf-8"))
                patch_text = patch_bytes.decode("utf-8", errors="replace")
                if len(patch_text) > 80000:
                    raise ValueError("patch too large")

                paths = _extract_patch_paths(patch_text)
                if not paths:
                    raise ValueError("could not detect paths from diff")
                bad = [p for p in paths if not _is_patch_path_allowed(p)]
                if bad:
                    raise ValueError(f"disallowed paths: {bad}")

                patch_file = None
                try:
                    with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8", suffix=".patch") as tf:
                        tf.write(patch_text)
                        patch_file = tf.name

                    # Pre-check
                    check = _run_cmd_capture(
                        [
                            "git",
                            "-C",
                            str(_WORKSPACE_ROOT),
                            "apply",
                            "--check",
                            "--whitespace=nowarn",
                            patch_file,
                        ],
                        cwd=_WORKSPACE_ROOT,
                        timeout=60,
                    )
                    if not check.get("ok"):
                        reply = "適用前チェック失敗: " + json.dumps(check, ensure_ascii=False)
                        chat_history.append({"role": "assistant", "content": reply, "ts": datetime.now().isoformat()})
                        _save_chat_history()
                        return {"reply": reply, "mode": "command"}

                    # Apply patch using git
                    run = _run_cmd_capture(
                        ["git", "-C", str(_WORKSPACE_ROOT), "apply", "--whitespace=nowarn", patch_file],
                        cwd=_WORKSPACE_ROOT,
                        timeout=60,
                    )
                    if run.get("ok"):
                        # Return a short diff tail after apply
                        diff = _run_cmd_capture(
                            [
                                "git",
                                "-C",
                                str(_WORKSPACE_ROOT),
                                "diff",
                                "--no-color",
                                "--ignore-submodules=all",
                            ],
                            cwd=_WORKSPACE_ROOT,
                            timeout=30,
                        )
                        d = (diff.get("stdout") or "").strip()
                        reply = "適用OK。\n" + (d[-2800:] if d else "(no diff)")
                    else:
                        reply = "適用失敗: " + json.dumps(run, ensure_ascii=False)
                finally:
                    try:
                        if patch_file and os.path.exists(patch_file):
                            os.unlink(patch_file)
                    except Exception:
                        pass
            except Exception as e:
                reply = f"/applypatch 失敗: {e}"

            chat_history.append({"role": "assistant", "content": reply, "ts": datetime.now().isoformat()})
            _save_chat_history()
            return {"reply": reply, "mode": "command"}

        if key in ("pycheck", "compile"):
            try:
                if not args:
                    raise ValueError("usage: /pycheck <path>")
                path = _safe_resolve_workspace_path(args[0])
                run = _run_cmd_capture(
                    [_workspace_python(), "-m", "py_compile", str(path)],
                    cwd=_WORKSPACE_ROOT,
                    timeout=60,
                )
                if run.get("ok"):
                    reply = f"OK: {args[0]}"
                else:
                    reply = (run.get("stderr") or run.get("stdout") or str(run))[-3800:]
            except Exception as e:
                reply = f"/pycheck 失敗: {e}"

            chat_history.append({"role": "assistant", "content": reply, "ts": datetime.now().isoformat()})
            _save_chat_history()
            return {"reply": reply, "mode": "command"}

        if key in ("queue", "todo"):
            try:
                text = (rest or "").strip()
                if not text:
                    raise ValueError("usage: /queue <text>")
                queue_path = Path(LOG_DIR) / "remi_agent_queue.jsonl"
                entry = {
                    "ts": datetime.now().isoformat(),
                    "text": text,
                    "source": "remi_chat",
                }
                queue_path.parent.mkdir(parents=True, exist_ok=True)
                with open(queue_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                reply = f"キューに入れたよ: {text}"
            except Exception as e:
                reply = f"/queue 失敗: {e}"

            chat_history.append({"role": "assistant", "content": reply, "ts": datetime.now().isoformat()})
            _save_chat_history()
            return {"reply": reply, "mode": "command"}

        # Unknown command: fall through to LLM

    # Inject real-time PC status into context so Remi can answer system questions
    gpu = get_gpu_info()
    cpu_pct = psutil.cpu_percent(interval=0.3)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage("C:\\")
    ollama = check_ollama_models()
    docker_count = len(get_docker_containers())
    uptime_h = round((time.time() - psutil.boot_time()) / 3600, 1)

    status_context = (
        f"\n[Current PC Status] "
        f"GPU: {gpu.get('name','N/A')} usage={gpu.get('usage_percent',0)}% "
        f"VRAM={gpu.get('memory_used_mb',0):.0f}/{gpu.get('memory_total_mb',0):.0f}MB "
        f"temp={gpu.get('temperature_c',0)}C | "
        f"CPU: {cpu_pct}% ({psutil.cpu_count()} cores) | "
        f"RAM: {ram.percent}% ({round(ram.used/(1024**3),1)}/{round(ram.total/(1024**3),1)}GB) | "
        f"Disk: {round(disk.percent,1)}% (free {round(disk.free/(1024**3),1)}GB) | "
        f"Docker: {docker_count} containers | "
        f"Ollama: {ollama.get('count',0)} models ({', '.join(ollama.get('models',[]))}) | "
        f"Uptime: {uptime_h}h"
    )

    full_system = system + status_context
    messages = [{"role": "system", "content": full_system}] + chat_history[-10:]

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
# Secretary & ManaOS Integration
# ============================================================

SECRETARY_API = os.getenv("SECRETARY_API_URL", f"http://127.0.0.1:{SECRETARY_API_PORT}")
SSOT_API = os.getenv("SSOT_API_URL", f"http://127.0.0.1:{FILE_SECRETARY_PORT}")
UNIFIED_API = os.getenv("UNIFIED_API_URL", f"http://127.0.0.1:{UNIFIED_API_PORT}")
SECRETARY_SYSTEM_API = os.getenv("SECRETARY_SYSTEM_URL", f"http://127.0.0.1:{SECRETARY_SYSTEM_PORT}")
ORCHESTRATOR_API = os.getenv("ORCHESTRATOR_URL", f"http://127.0.0.1:{ORCHESTRATOR_PORT}")


async def _proxy_get(url: str, timeout: float = 10.0) -> dict:
    """Proxy GET to internal service"""
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.get(url)
        return resp.json()


async def _proxy_post(url: str, data: dict = None, timeout: float = 15.0) -> dict:
    """Proxy POST to internal service"""
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, json=data or {})
        return resp.json()


@app.get("/secretary/status", dependencies=[Depends(verify_token)])
async def secretary_status():
    """Check all secretary and ManaOS service health"""
    services = {
        "secretary_api": {"url": f"{SECRETARY_API}/health", "port": SECRETARY_API_PORT},
        "ssot_api": {"url": f"{SSOT_API}/health", "port": FILE_SECRETARY_PORT},
        "unified_api": {"url": f"{UNIFIED_API}/health", "port": UNIFIED_API_PORT},
        "secretary_system": {"url": f"{SECRETARY_SYSTEM_API}/health", "port": SECRETARY_SYSTEM_PORT},
        "orchestrator": {"url": f"{ORCHESTRATOR_API}/health", "port": ORCHESTRATOR_PORT},
    }
    results = {}
    for name, info in services.items():
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(info["url"])
                results[name] = {"status": "online", "port": info["port"], "data": resp.json()}
        except Exception:
            results[name] = {"status": "offline", "port": info["port"]}
    return {"services": results, "online": sum(1 for v in results.values() if v["status"] == "online"), "total": len(results)}


@app.get("/secretary/reminders", dependencies=[Depends(verify_token)])
async def get_reminders():
    """Get pending reminders from Secretary System"""
    try:
        data = await _proxy_get(f"{SECRETARY_SYSTEM_API}/api/reminders")
        return data
    except httpx.ConnectError:
        return {"error": "Secretary System offline (port 5125)", "hint": "Start secretary_system.py"}
    except Exception as e:
        return {"error": str(e)}


@app.post("/secretary/reminders", dependencies=[Depends(verify_token)])
async def add_reminder(
    title: str = Query(..., description="Reminder title"),
    due: str = Query(None, description="Due date (YYYY-MM-DD HH:MM)"),
    repeat: str = Query("once", description="once/daily/weekly/monthly")
):
    """Add a reminder via Secretary System"""
    try:
        payload = {"title": title, "repeat_type": repeat}
        if due:
            payload["due_date"] = due
        data = await _proxy_post(f"{SECRETARY_SYSTEM_API}/api/reminders", payload)
        return data
    except httpx.ConnectError:
        return {"error": "Secretary System offline (port 5125)"}
    except Exception as e:
        return {"error": str(e)}


@app.post("/secretary/report", dependencies=[Depends(verify_token)])
async def daily_report():
    """Generate daily report via Secretary System"""
    try:
        data = await _proxy_post(f"{SECRETARY_SYSTEM_API}/api/reports/daily")
        return data
    except httpx.ConnectError:
        return {"error": "Secretary System offline (port 5125)"}
    except Exception as e:
        return {"error": str(e)}


@app.get("/secretary/reports", dependencies=[Depends(verify_token)])
async def get_reports(report_type: str = Query("daily"), limit: int = Query(5)):
    """Get past reports from Secretary System"""
    try:
        data = await _proxy_get(f"{SECRETARY_SYSTEM_API}/api/reports?type={report_type}&limit={limit}")
        return data
    except httpx.ConnectError:
        return {"error": "Secretary System offline (port 5125)"}
    except Exception as e:
        return {"error": str(e)}


@app.get("/manaos/services", dependencies=[Depends(verify_token)])
async def manaos_services():
    """List all ManaOS services and their status"""
    service_map = {
        "unified_api": UNIFIED_API_PORT,
        "llm_routing": LLM_ROUTING_PORT,
        "mcp_api": MCP_API_SERVER_PORT,
        "intent_router": INTENT_ROUTER_PORT,
        "rag_memory": RAG_MEMORY_PORT,
        "task_queue": TASK_QUEUE_PORT,
        "orchestrator": ORCHESTRATOR_PORT,
        "service_monitor": LLM_ROUTING_PORT,
        "secretary_system": SECRETARY_SYSTEM_PORT,
        "file_secretary": FILE_SECRETARY_PORT,
        "mrl_memory": MRL_MEMORY_PORT,
        "learning_system": LEARNING_SYSTEM_PORT,
    }
    async def _check(client, name, port):
        try:
            await client.get(f"http://127.0.0.1:{port}/health")
            return name, {"status": "online", "port": port}
        except Exception:
            return name, {"status": "offline", "port": port}

    async with httpx.AsyncClient(timeout=2.0) as client:
        checks = await asyncio.gather(
            *[_check(client, n, p) for n, p in service_map.items()]
        )
    results = dict(checks)
    online = sum(1 for v in results.values() if v["status"] == "online")
    return {"services": results, "online": online, "total": len(results)}


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
