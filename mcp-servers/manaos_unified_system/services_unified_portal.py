#!/usr/bin/env python3
"""🎯 ManaOS Unified Portal v2.0 - Consciousness Dashboard"""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import psutil
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS

# アンチグラビティAPI統合
try:
    from api.antigravity_api import antigravity_bp
    from api.antigravity_advanced import antigravity_adv_bp
    from api.antigravity_automation import antigravity_auto_bp
    ANTIGRAVITY_AVAILABLE = True
except ImportError as e:
    ANTIGRAVITY_AVAILABLE = False
    print(f"⚠️  アンチグラビティAPIのインポートに失敗: {e}")

app = Flask(__name__)
CORS(app)

# アンチグラビティBlueprint登録
if ANTIGRAVITY_AVAILABLE:
    app.register_blueprint(antigravity_bp)
    app.register_blueprint(antigravity_adv_bp)
    app.register_blueprint(antigravity_auto_bp)
    print("✅ アンチグラビティAPIを統合しました")

FEED_BASE_URL = os.getenv("MACHI_FEED_BASE_URL", "http://127.0.0.1:5057")
FEED_PORTAL_TOKEN = os.getenv(
    "MACHI_FEED_PORTAL_TOKEN", os.getenv("MACHI_FEED_TOKEN", ""))
TASKS_PATH = Path("/root/trinity_workspace/shared/tasks.json")
DEFAULT_AUTO_METADATA = {"in_progress": False, "final_status": None}

SERVICES = {
    "AI Services": [
        {"name": "AI Model Hub", "port": 5080, "icon": "🧠"},
        {"name": "AI Predictive", "port": 5054, "icon": "📈"},
        {"name": "Trinity Secretary", "port": 5013, "icon": "🤖"},
        {"name": "Voice Control", "port": 5200, "icon": "🎤"},
        {"name": "MCP Auto Proposal", "port": 5100, "icon": "💡"},
    ],
    "System Management": [
        {"name": "Security Monitor", "port": 5062, "icon": "🛡️"},
        {"name": "Task Executor", "port": 5176, "icon": "⚙️"},
        {"name": "Cost Optimizer", "port": 5063, "icon": "💰"},
        {"name": "Screen Sharing", "port": 5008, "icon": "🖥️"},
        {"name": "Monitoring Dashboard", "port": 5020, "icon": "📊"},
        {"name": "Gallery API", "port": 5559, "icon": "🖼️"},
    ],
    "Trinity Workspace": [
        {"name": "Trinity Orchestrator", "port": 9400, "icon": "🎛️"},
        {"name": "ManaSpec API", "port": 9301, "icon": "📋"},
        {"name": "ManaSearch Nexus", "port": 9111, "icon": "🔍"},
    ],
    "Integration": [
        {"name": "API Gateway", "port": 5059, "icon": "🌐"},
        {"name": "Foundation Manager", "port": 8100, "icon": "🛠️"},
        {"name": "Unified Auth", "port": 8098, "icon": "🔐"},
        {"name": "Google Services", "port": 8097, "icon": "☁️"},
    ],
    "Memory System": [
        {"name": "Memory System API", "port": 5055, "icon": "🧠"},
        {"name": "Memory Dashboard", "port": 5055,
            "icon": "📊", "path": "/api/memory/stats"},
    ],
}


def check_service(port: int) -> str:
    try:
        response = requests.get(f"http://localhost:{port}/health", timeout=2)
        return "online" if response.status_code == 200 else "listening"
    except requests.RequestException:
        try:
            response = requests.get(f"http://localhost:{port}", timeout=2)
            return "listening" if response.status_code < 500 else "offline"
        except requests.RequestException:
            for conn in psutil.net_connections():
                laddr = getattr(conn, "laddr", None)
                status = getattr(conn, "status", "")
                conn_port = getattr(laddr, "port", None) if laddr else None
                if conn_port == port and status == "LISTEN":
                    return "listening"
            return "offline"


def fetch_feed(path: str, default: Optional[Dict] = None) -> Dict:
    url = f"{FEED_BASE_URL.rstrip('/')}{path}"
    headers: Dict[str, str] = {}
    if FEED_PORTAL_TOKEN:
        headers["Authorization"] = f"Bearer {FEED_PORTAL_TOKEN}"
    try:
        response = requests.get(url, headers=headers, timeout=3)
        if response.status_code == 200:
            return response.json() or {}
        return default or {}
    except requests.RequestException:
        return default or {}


def _load_tasks() -> list:
    if TASKS_PATH.exists():
        try:
            return json.loads(TASKS_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return []


def append_feedback_task(action: str, capsule_id: Optional[str], record_id: Optional[str], channel: Optional[str], message: Optional[str]) -> str:
    tasks = _load_tasks()
    now = datetime.utcnow().isoformat()
    task_id = f"feedback-{uuid.uuid4().hex[:8]}"
    assigned_to = "luna" if action == "approve" else "remi"
    priority = 2 if action == "approve" else 1
    description_parts = []
    if capsule_id:
        description_parts.append(f"Capsule ID: {capsule_id}")
    if channel:
        description_parts.append(f"Channel: {channel}")
    if message:
        description_parts.append(f"Message: {message}")
    description = "\n".join(
        description_parts) if description_parts else "Manual feedback from portal"
    task = {
        "id": task_id,
        "title": f"[{action.upper()}] {record_id or 'Timeline feedback'}",
        "description": description,
        "status": "todo",
        "priority": priority,
        "assigned_to": assigned_to,
        "auto_orchestrate": True,
        "automation": {
            **DEFAULT_AUTO_METADATA,
            "stage": "feedback",
            "notes": "Generated from portal timeline action",
        },
        "created_at": now,
        "updated_at": now,
        "feedback": {
            "capsule_id": capsule_id,
            "record_id": record_id,
            "channel": channel,
            "action": action,
        },
    }
    tasks.append(task)
    TASKS_PATH.write_text(json.dumps(
        tasks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return task_id


def get_recent_learning(top: int = 3) -> Dict:
    return fetch_feed(f"/feed/learning/recent?top={top}", default={"items": []})


def get_future_intents(limit: int = 5) -> Dict:
    return fetch_feed(f"/feed/future?limit={limit}", default={"items": []})


def get_recent_summary() -> Dict:
    return fetch_feed("/feed/summary?since=1970-01-01T00:00:00Z", default={})


def get_capsules(limit: int = 10) -> Dict:
    limit = max(1, min(limit, 50))
    return fetch_feed(f"/feed/capsules?limit={limit}", default={"items": []})


def get_commentary(limit: int = 30) -> Dict:
    limit = max(1, min(limit, 200))
    return fetch_feed(f"/feed/commentary?limit={limit}", default={"items": []})


def load_mode() -> str:
    return os.getenv("MACHI_FEED_MODE", "observer").lower()


@app.route("/api/services")
def api_services():
    result: Dict[str, list] = {}
    for category, services in SERVICES.items():
        result[category] = []
        for svc in services:
            result[category].append(
                {**svc, "status": check_service(svc["port"])})
    return jsonify(result)


@app.route("/api/metrics")
def api_metrics():
    return jsonify(
        {
            "cpu": psutil.cpu_percent(interval=1),
            "memory": psutil.virtual_memory().percent,
            "disk": psutil.disk_usage("/").percent,
            "timestamp": datetime.now().isoformat(),
        }
    )


@app.route("/api/feed/learning")
def api_feed_learning():
    return jsonify(get_recent_learning())


@app.route("/api/feed/future")
def api_feed_future():
    return jsonify(get_future_intents())


@app.route("/api/feed/summary")
def api_feed_summary():
    return jsonify(get_recent_summary())


@app.route("/api/feed/capsules")
def api_feed_capsules():
    try:
        limit = int(request.args.get("limit", 10))
    except (TypeError, ValueError):
        limit = 10
    return jsonify(get_capsules(limit))


@app.route("/api/feed/commentary")
def api_feed_commentary():
    try:
        limit = int(request.args.get("limit", 30))
    except (TypeError, ValueError):
        limit = 30
    return jsonify(get_commentary(limit))


@app.route("/api/feedback/actions", methods=["POST"])
def api_feedback_actions():
    payload = request.get_json(silent=True) or {}
    action = payload.get("action", "unknown")
    capsule_id = payload.get("capsule_id")
    record_id = payload.get("record_id")
    channel = payload.get("channel")
    message = payload.get("message")
    task_id = append_feedback_task(
        action, capsule_id, record_id, channel, message)
    app.logger.info(
        "Timeline feedback received",
        extra={
            "action": action,
            "capsule_id": capsule_id,
            "record_id": record_id,
            "channel": channel,
            "message": message,
            "task_id": task_id,
        },
    )
    return jsonify({"status": "ok", "task_id": task_id})


@app.route("/api/memory/recent")
def api_memory_recent():
    try:
        response = requests.get(
            "http://localhost:5055/api/memory/memos?limit=5", timeout=3)
        if response.status_code == 200:
            return jsonify(response.json())
        return jsonify({"memos": []})
    except requests.RequestException:
        return jsonify({"memos": []})


@app.route("/api/memory/stats")
def api_memory_stats():
    try:
        response = requests.get(
            "http://localhost:5055/api/memory/stats", timeout=3)
        if response.status_code == 200:
            return jsonify(response.json())
        return jsonify({"error": "記憶システムが利用できません"})
    except requests.RequestException:
        return jsonify({"error": "記憶システムが利用できません"})


@app.route("/health")
def health():
    return jsonify({"service": "unified-portal", "status": "healthy", "version": "2.0.0"})


@app.route("/")
def index():
    feed_base_js = json.dumps(FEED_BASE_URL)
    feed_token_js = json.dumps(FEED_PORTAL_TOKEN or "")
    mode_js = json.dumps(load_mode())
    template = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8" />
<title>🎯 ManaOS Unified Portal v2.0</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body {
    font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif;
    background: linear-gradient(135deg, #1a1a2e, #16213e, #0f3460);
    color: #ffffff;
    min-height: 100vh;
    padding: 28px;
}
.container { max-width: 1600px; margin: 0 auto; }
.header {
    background: rgba(255,255,255,0.08);
    border-radius: 22px;
    padding: 28px;
    margin-bottom: 28px;
    backdrop-filter: blur(20px);
    display:flex;
    justify-content:space-between;
    align-items:center;
}
.header h1 { font-size: 2.4em; font-weight: 700; }
.header-controls { display:flex; gap:12px; }
.header button {
    padding: 10px 20px;
    border: none;
    border-radius: 12px;
    font-weight: 600;
    cursor: pointer;
    background: rgba(255,255,255,0.2);
    color: #fff;
}
.subject-card {
    background: rgba(255,255,255,0.1);
    border-radius: 20px;
    padding: 24px;
    margin-bottom: 24px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.25);
}
.subject-card h2 { display:flex; align-items:center; gap:10px; font-size:1.6em; }
.mode-tag {
    font-size:0.75em;
    padding:4px 12px;
    border-radius:999px;
    background:rgba(255,255,255,0.2);
    letter-spacing:0.05em;
}
.subject-note { font-size:0.85em; opacity:0.7; margin-top:6px; }
.insight-grid {
    display:grid;
    grid-template-columns: repeat(auto-fit, minmax(260px,1fr));
    gap:20px;
    margin-bottom:24px;
}
.insight-card {
    background: rgba(255,255,255,0.08);
    border-radius: 20px;
    padding: 20px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.2);
}
.insight-card h3 { margin-bottom: 12px; font-size: 1.2em; display:flex; align-items:center; gap:8px; }
.insight-card ul { list-style:none; line-height:1.6; }
.insight-card li { padding:6px 0; border-bottom:1px solid rgba(255,255,255,0.12); }
.insight-card li:last-child { border-bottom:none; }
.insight-comment { color:#facc15; font-size:0.95em; font-weight:500; }
.alert-item { padding:6px 0; border-bottom:1px solid rgba(255,255,255,0.12); }
.alert-item:last-child { border-bottom:none; }
.alert-warning { color:#fbbf24; font-weight:600; }
.alert-info { color:#93c5fd; }
.alert-critical { color:#f87171; font-weight:600; }
.ticker-card {
    background: rgba(255,255,255,0.08);
    border-radius: 20px;
    padding: 20px;
    margin-bottom: 24px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.2);
    display:flex;
    flex-direction:column;
    gap:14px;
}
.ticker-card h3 { font-size:1.3em; display:flex; align-items:center; gap:8px; }
.ticker-stream { display:flex; flex-direction:column; gap:10px; max-height:150px; overflow:hidden; }
.ticker-item {
    background: rgba(255,255,255,0.06);
    border-radius:14px;
    padding:10px 14px;
    box-shadow:0 6px 16px rgba(0,0,0,0.18);
    display:flex;
    flex-direction:column;
    gap:4px;
}
.ticker-item .ticker-time { font-size:0.75em; opacity:0.65; }
.ticker-item .ticker-channel { font-size:0.8em; opacity:0.8; letter-spacing:0.05em; text-transform:uppercase; }
.ticker-item .ticker-message { font-size:1em; font-weight:500; }
.ticker-item.ticker-level-critical { border-left:3px solid #f87171; }
.ticker-item.ticker-level-warning { border-left:3px solid #fbbf24; }
.ticker-item.ticker-level-info { border-left:3px solid #60a5fa; }
.ticker-item.ticker-level-positive { border-left:3px solid #4ade80; }
.ticker-item.new { animation:tickerGlow 1.2s ease-in-out 1; }
@keyframes tickerGlow { 0%{box-shadow:0 0 0 0 rgba(99,102,241,0.6);} 70%{box-shadow:0 0 0 12px rgba(99,102,241,0);} 100%{box-shadow:0 0 0 0 rgba(99,102,241,0);} }
.timeline-card {
    background: rgba(255,255,255,0.08);
    border-radius: 20px;
    padding: 24px;
    margin-bottom: 24px;
    box-shadow: 0 10px 28px rgba(0,0,0,0.25);
}
.timeline-card h3 { font-size:1.4em; display:flex; align-items:center; gap:8px; margin-bottom:16px; }
.timeline-card ul { list-style:none; margin:0; padding:0; }
.timeline-item {
    padding: 12px 0;
    border-bottom: 1px solid rgba(255,255,255,0.1);
    display:flex;
    flex-direction:column;
    gap:6px;
}
.timeline-item:last-child { border-bottom:none; }
.timeline-item .time { font-size:0.85em; opacity:0.7; }
.timeline-item .headline { font-size:1.05em; font-weight:600; }
.timeline-item .details { font-size:0.95em; opacity:0.85; }
.timeline-item.timeline-critical .headline { color:#fca5a5; }
.timeline-item.timeline-warning .headline { color:#fbbf24; }
.timeline-item.timeline-positive .headline { color:#86efac; }
.timeline-item.timeline-highlight { background:rgba(255,255,255,0.08); border-radius:12px; box-shadow:0 0 0 2px rgba(255,207,134,0.4); animation:timelinePulse 1.6s ease-in-out 2; }
.timeline-item.acknowledged { opacity:0.75; border-left:4px solid rgba(134,239,172,0.6); padding-left:10px; }
.timeline-actions { display:flex; gap:8px; margin-top:8px; flex-wrap:wrap; }
.timeline-actions button { border:none; padding:6px 12px; border-radius:999px; font-size:0.85em; font-weight:600; color:#fff; cursor:pointer; background:rgba(99,102,241,0.5); transition:background 0.2s ease; }
.timeline-actions button:hover { background:rgba(129,140,248,0.8); }
.timeline-actions button[data-action="reject"] { background:rgba(248,113,113,0.45); }
.timeline-actions button[data-action="reject"]:hover { background:rgba(248,113,113,0.7); }
.timeline-actions button[data-action="approve"] { background:rgba(74,222,128,0.45); }
.timeline-actions button[data-action="approve"]:hover { background:rgba(74,222,128,0.7); }
@keyframes timelinePulse { 0%{box-shadow:0 0 0 0 rgba(255,207,134,0.6);} 50%{box-shadow:0 0 0 6px rgba(255,207,134,0);} 100%{box-shadow:0 0 0 0 rgba(255,207,134,0);} }
.metrics {
    display:grid;
    grid-template-columns: repeat(auto-fit,minmax(200px,1fr));
    gap:20px;
    margin-bottom:24px;
}
.metric-card {
    background: rgba(255,255,255,0.08);
    border-radius: 18px;
    padding: 20px;
    text-align:center;
    box-shadow:0 6px 20px rgba(0,0,0,0.18);
}
.metric-value { font-size:2.2em; font-weight:700; margin-top:10px; }
.services-grid { display:grid; grid-template-columns: repeat(auto-fit,minmax(260px,1fr)); gap:20px; }
.service-card {
    position:relative;
    background: rgba(255,255,255,0.08);
    border-radius: 18px;
    padding: 20px;
    box-shadow:0 10px 24px rgba(0,0,0,0.24);
    transition: transform 0.2s ease;
}
.service-card:hover { transform: translateY(-4px); }
.service-header { display:flex; align-items:center; gap:14px; margin-bottom:8px; }
.service-icon { font-size:2.4em; }
.service-name { font-size:1.15em; font-weight:600; }
.service-port { position:absolute; top:16px; right:16px; padding:4px 10px; border-radius:12px; background:rgba(0,0,0,0.3); font-size:0.85em; }
.status-badge { display:inline-block; margin-top:6px; padding:4px 10px; border-radius:999px; font-size:0.8em; font-weight:600; }
.status-online { background:#22c55e; }
.status-listening { background:#f59e0b; }
.status-offline { background:#ef4444; }
.modal {
    position:fixed; inset:0; display:none;
    align-items:center; justify-content:center;
    background: rgba(15,15,35,0.65);
    backdrop-filter: blur(6px);
    padding:40px 20px;
    z-index:999;
}
.modal.show { display:flex; }
body.modal-open { overflow:hidden; }
.modal-dialog {
    position:relative;
    background: rgba(10,10,20,0.9);
    border-radius: 20px;
    max-width:760px;
    width:100%;
    max-height:90vh;
    overflow:auto;
    padding:28px;
    box-shadow:0 20px 60px rgba(0,0,0,0.5);
    outline:none;
}
.modal-close {
    position:absolute; top:14px; right:14px;
    width:36px; height:36px;
    border:none; border-radius:999px;
    background:rgba(255,255,255,0.12);
    color:#fff; font-size:1.2em;
    cursor:pointer;
}
.modal-close:hover { background:rgba(255,255,255,0.25); }
.modal-content-body h2 { font-size:1.6em; margin-bottom:8px; }
.modal-meta { font-size:0.9em; opacity:0.75; margin-bottom:14px; }
.modal-tabs { display:flex; gap:10px; margin-bottom:16px; }
.modal-tab-btn { flex:1; border:none; padding:10px 12px; border-radius:12px; background:rgba(255,255,255,0.08); color:#fff; font-weight:600; cursor:pointer; }
.modal-tab-btn.active { background:rgba(79,70,229,0.6); }
.modal-panel { display:none; background:rgba(255,255,255,0.05); border-radius:14px; padding:14px; }
.modal-panel.active { display:block; }
.modal-panel h3 { font-size:1.1em; margin:0 0 10px; }
.modal-list { list-style:none; margin:0; padding:0; }
.modal-list li { padding:6px 0; border-bottom:1px solid rgba(255,255,255,0.08); }
.modal-list li:last-child { border-bottom:none; }
.modal-tag { display:inline-block; margin-right:8px; padding:4px 8px; border-radius:999px; background:rgba(79,70,229,0.35); font-size:0.8em; }
.modal-two-column { display:grid; grid-template-columns: repeat(auto-fit,minmax(180px,1fr)); gap:12px; margin-bottom:12px; }
.modal-section { background:rgba(255,255,255,0.04); padding:10px; border-radius:10px; }
.modal-empty { opacity:0.6; }
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>🎯 ManaOS Unified Portal v2.0</h1>
    <div class="header-controls">
      <button id="streaming-toggle">🟢 実況ON</button>
      <button onclick="loadMetricsAndServices()">🔄 Refresh</button>
    </div>
  </div>
  <div class="subject-card" id="subject-card">
    <h2>🧭 主観トラッカー <span class="mode-tag" id="mode-tag"></span></h2>
    <p id="subject-values">loading...</p>
    <span class="subject-note" id="subject-note">Reflection Feedからムードを取得中</span>
  </div>
  <div class="insight-grid">
    <div class="insight-card">
      <h3>🧩 最近覚えたパターン</h3>
      <ul id="learning-list"><li>読み込み中...</li></ul>
    </div>
    <div class="insight-card">
      <h3>🔮 明日の意図</h3>
      <ul id="future-list"><li>読み込み中...</li></ul>
    </div>
    <div class="insight-card">
      <h3>⚠️ 注意フラグ</h3>
      <ul id="alert-list"><li>読み込み中...</li></ul>
    </div>
  </div>
  <div class="ticker-card" aria-live="polite" aria-atomic="true">
    <h3>🗣️ リアルタイム実況</h3>
    <div class="ticker-stream" id="ticker-stream">
      <div class="ticker-item"><span class="ticker-message">最新ログを待機中...</span></div>
    </div>
  </div>
  <div class="timeline-card">
    <h3>🪄 意識タイムライン</h3>
    <ul id="timeline-list"><li>読み込み中...</li></ul>
  </div>
  <div class="metrics">
    <div class="metric-card"><div>CPU</div><div class="metric-value" id="cpu">--</div></div>
    <div class="metric-card"><div>Memory</div><div class="metric-value" id="memory">--</div></div>
    <div class="metric-card"><div>Disk</div><div class="metric-value" id="disk">--</div></div>
    <div class="metric-card"><div>Services Online</div><div class="metric-value" id="online">--</div></div>
  </div>
  <div id="services-container" class="services-grid"></div>
</div>
<div id="timeline-modal" class="modal" aria-hidden="true">
  <div class="modal-dialog" role="dialog" aria-modal="true" aria-labelledby="timeline-modal-title" tabindex="-1">
    <button type="button" class="modal-close" aria-label="閉じる">×</button>
    <div class="modal-content-body"></div>
  </div>
</div>
<script>
const FEED_BASE = __FEED_BASE__;
const FEED_TOKEN = __FEED_TOKEN__;
const INITIAL_MODE = __INITIAL_MODE__;
const SUBJECT_VOCAB = {
  stability: {label: '安定', comment: '落ち着いてじっくりモードだよ'},
  exploration: {label: '探索', comment: 'ワクワク探検モードだよ'},
  speed: {label: '速度', comment: 'テンポ良くやりきるモードだよ'}
};
const MAX_TICKER_ITEMS = 15;
const STORAGE_KEYS = {
  streaming: 'mana_portal_streaming_enabled'
};
let timelineCache = [];
let commentaryBuffer = [];
let pendingTimelineHighlightId = null;
let activeTimelineCapsuleId = null;
let eventSource = null;
let reconnectTimer = null;
const timelineListEl = document.getElementById('timeline-list');
const tickerStreamEl = document.getElementById('ticker-stream');
const modalEl = document.getElementById('timeline-modal');
const modalDialog = modalEl ? modalEl.querySelector('.modal-dialog') : null;
const modalBody = modalEl ? modalEl.querySelector('.modal-content-body') : null;
const modalClose = modalEl ? modalEl.querySelector('.modal-close') : null;
const body = document.body;
const streamingToggleBtn = document.getElementById('streaming-toggle');
let streamingEnabled = true;
let lastFocusedTimelineEl = null;

function buildHeaders(){
  if(!FEED_TOKEN){return {};}
  return {Authorization: `Bearer ${FEED_TOKEN}`};
}
function safeJson(res){
  if(!res.ok){throw new Error(`status ${res.status}`);}
  return res.json();
}
function formatRelative(ts){
  const date = new Date(ts);
  if(Number.isNaN(date.getTime())){return '';}
  const diff = (Date.now() - date.getTime()) / 1000;
  if(diff < 60){return `${Math.max(0, Math.floor(diff))}秒前`;}
  if(diff < 3600){return `${Math.floor(diff/60)}分前`;}
  if(diff < 86400){return `${Math.floor(diff/3600)}時間前`;}
  return `${date.getMonth()+1}月${date.getDate()}日 ${date.getHours().toString().padStart(2,'0')}:${date.getMinutes().toString().padStart(2,'0')}`;
}
function updateModeTag(mode){
  const modeTag = document.getElementById('mode-tag');
  if(!modeTag){return;}
  if(mode === 'expressive'){
    modeTag.textContent = 'EXPRESSIVE';
    modeTag.style.background = 'rgba(255,120,120,0.35)';
  } else {
    modeTag.textContent = 'OBSERVER';
    modeTag.style.background = 'rgba(120,200,255,0.35)';
  }
}
function formatVector(vector){
  if(!vector || typeof vector !== 'object'){return '';}
  return Object.entries(vector).map(([k,v]) => typeof v === 'number' ? `${k}:${v.toFixed(2)}` : `${k}:${v}`).join(' / ');
}
function renderTicker(){
  if(!tickerStreamEl){return;}
  tickerStreamEl.innerHTML = '';
  if(!commentaryBuffer.length){
    const placeholder = document.createElement('div');
    placeholder.className = 'ticker-item';
    placeholder.innerHTML = '<span class="ticker-message">最新ログを待機中...</span>';
    tickerStreamEl.appendChild(placeholder);
    return;
  }
  commentaryBuffer.forEach(entry => {
    const itemEl = document.createElement('div');
    const classes = ['ticker-item'];
    if(entry.levelClass){classes.push(entry.levelClass);}
    if(entry.isNew){classes.push('new');}
    itemEl.className = classes.join(' ');
    itemEl.innerHTML = `<span class="ticker-time">${entry.relative||''}</span><span class="ticker-channel">${entry.channel||'thought'}</span><span class="ticker-message">${entry.message||''}</span>`;
    if(entry.metaText){
      const meta = document.createElement('span');
      meta.style.opacity = '0.7';
      meta.style.fontSize = '0.78em';
      meta.textContent = entry.metaText;
      itemEl.appendChild(meta);
    }
    if(entry.isNew){setTimeout(()=>itemEl.classList.remove('new'), 2000);}
    tickerStreamEl.appendChild(itemEl);
  });
}
function tickerLevelClass(level){
  if(!level){return '';}
  const normalized = level.toLowerCase();
  if(normalized.includes('critical')||normalized.includes('danger')||normalized.includes('error')){return 'ticker-level-critical';}
  if(normalized.includes('warn')||normalized.includes('caution')){return 'ticker-level-warning';}
  if(normalized.includes('positive')||normalized.includes('success')||normalized.includes('good')){return 'ticker-level-positive';}
  return 'ticker-level-info';
}
function pushCommentaryEntry(entry, markNew=true){
  if(!streamingEnabled){return;}
  const ts = entry.timestamp || entry.ts || entry.time;
  const normalized = {
    id: entry.id || `comment-${Date.now()}`,
    timestamp: ts,
    message: entry.message || '',
    channel: entry.channel || 'thought',
    levelClass: tickerLevelClass(entry.level || ''),
    relative: formatRelative(ts),
    metaText: entry.metadata && Object.keys(entry.metadata).length ? JSON.stringify(entry.metadata) : '',
    isNew: markNew,
  };
  if(entry.id){
    const idx = commentaryBuffer.findIndex(item => item.id === entry.id);
    if(idx !== -1){
      commentaryBuffer.splice(idx, 1);
    }
  }
  commentaryBuffer.unshift(normalized);
  while(commentaryBuffer.length > MAX_TICKER_ITEMS){commentaryBuffer.pop();}
  renderTicker();
}
function mergeCommentary(entries){
  if(!streamingEnabled){return;}
  if(!Array.isArray(entries)){return;}
  commentaryBuffer = entries
    .sort((a,b)=>new Date(b.ts||b.timestamp||0).getTime()-new Date(a.ts||a.timestamp||0).getTime())
    .map(entry => ({
      id: entry.id || `comment-${Date.now()}`,
      timestamp: entry.ts || entry.timestamp,
      message: entry.message || '',
      channel: entry.channel || 'thought',
      levelClass: tickerLevelClass(entry.level || ''),
      relative: formatRelative(entry.ts || entry.timestamp),
      metaText: entry.metadata && Object.keys(entry.metadata).length ? JSON.stringify(entry.metadata) : '',
      isNew: false,
    }));
  renderTicker();
}
function renderServiceCards(data){
  const container = document.getElementById('services-container');
  if(!container){return;}
  container.innerHTML = '';
  const entries = Object.entries(data);
  if(!entries.length){
    container.innerHTML = '<p style="opacity:0.6">サービス情報を取得できなかったよ</p>';
    return;
  }
  entries.forEach(([,services])=>{
    services.forEach(svc=>{
      const card = document.createElement('div');
      card.className = `service-card ${svc.status}`;
      card.innerHTML = `
        <div class="service-header">
          <div class="service-icon">${svc.icon||'🧩'}</div>
          <div>
            <div class="service-name">${svc.name}</div>
            <span class="status-badge status-${svc.status}">${svc.status.toUpperCase()}</span>
          </div>
        </div>
        <div class="service-port">:${svc.port}</div>
        <button class="btn" style="margin-top:10px" onclick="window.open('http://localhost:${svc.port}','_blank')">Open</button>
      `;
      container.appendChild(card);
    });
  });
}
function describeAlerts(summary){
  const alerts=[];
  const decision=summary.decision_log||{};
  const loopEval=summary.loop_eval||{};
  const future=summary.future_intents||{};
  if(!decision.count){alerts.push({level:'warning',message:'🪵 決定ログは静かだよ。必要ならトリガーしてね。'});} else if(decision.stale_minutes&&decision.stale_minutes>30){alerts.push({level:'warning',message:`🕒 決定ログが${decision.stale_minutes}分更新されていないよ。`});}
  if(!loopEval.count){alerts.push({level:'info',message:'🔁 まだ自己振り返りが投稿されていないよ。'});}
  if(!future.count){alerts.push({level:'info',message:'📭 未来意図が未登録だよ。次の予定を考えたら教えてね。'});}
  if(summary.alerts&&Array.isArray(summary.alerts)){
    summary.alerts.forEach(item=>alerts.push({level:item.level||'warning',message:item.message||'追加アラートが届いたよ'}));
  }
  return alerts;
}
function classifyCapsule(item){
  const capsule=item.capsule||{};
  const reflection=capsule.reflection||{};
  const issues=Array.isArray(reflection.issues)?reflection.issues.filter(entry=>typeof entry==='string'):[];
  if(issues.length){return 'timeline-critical';}
  const wins=Array.isArray(reflection.what_went_well)?reflection.what_went_well.filter(entry=>typeof entry==='string'):[];
  if(wins.length){return 'timeline-positive';}
  const outcome=capsule.outcome||{};
  if(typeof outcome==='object'){
    const status=(outcome.status||outcome.state||'').toString().toLowerCase();
    if(status.includes('risk')||status.includes('warn')){return 'timeline-warning';}
  }
  const futureScore=item.scores&&item.scores.future_confidence!=null?Number(item.scores.future_confidence):null;
  return futureScore!==null && futureScore>=0.7 ? 'timeline-positive' : '';
}
function buildTimelineHeadline(item){
  const capsule=item.capsule||{};
  const decision=capsule.decision||{};
  const selected=(decision.selected||{}).task_id||'未命名タスク';
  const intentLabel=extractIntentLabel(capsule.intent,selected);
  const metric=decision.selected_metric?` / ${decision.selected_metric}`:'';
  return `${intentLabel}${metric}`;
}
function extractIntentLabel(intent,fallback){
  if(intent == null){return fallback;}
  if(typeof intent === 'string'){return intent;}
  if(typeof intent === 'object'){
    const preferred=['summary','title','goal','intent','description','name','headline','label','topic'];
    for(const key of preferred){
      if(Object.prototype.hasOwnProperty.call(intent,key)&&intent[key]){return String(intent[key]);}
    }
  }
  return fallback;
}
function summarizeActions(actions){
  if(!Array.isArray(actions)||!actions.length){return '';} return actions.slice(0,3).join(' / ');
}
function summarizeReflection(reflection){
  if(!reflection||typeof reflection!=='object'){return '';}
  const issues=Array.isArray(reflection.issues)?reflection.issues.filter(item=>typeof item==='string'):[];
  if(issues.length){return `気になる点: ${issues.slice(0,2).join(' / ')}`;}
  const wins=Array.isArray(reflection.what_went_well)?reflection.what_went_well.filter(item=>typeof item==='string'):[];
  if(wins.length){return `良かった点: ${wins.slice(0,2).join(' / ')}`;}
  if(typeof reflection.note==='string'){return `メモ: ${reflection.note}`;}
  return '';
}
function summarizeOutcome(outcome){
  if(!outcome){return '';} if(typeof outcome==='string'){return `結果: ${outcome}`;}
  if(typeof outcome==='object'){
    const fragments=[];
    Object.entries(outcome).forEach(([key,value])=>{
      if(value==null){return;}
      if(typeof value==='number'){fragments.push(`${key}:${value.toFixed(2)}`);} else {fragments.push(`${key}:${value}`);}
    });
    if(fragments.length){return `結果: ${fragments.slice(0,2).join(', ')}`;}
  }
  return '';
}
function summarizeFuture(nextIntent){
  if(!nextIntent||typeof nextIntent!=='object'){return '';}
  const confidence=nextIntent.confidence!=null?`(確信度 ${(nextIntent.confidence*100).toFixed(0)}%)`:'';
  const title=nextIntent.intent||nextIntent.id||'次の意図';
  return `次の意図: ${title} ${confidence}`.trim();
}
function buildTimelineDetails(item){
  const capsule=item.capsule||{};
  const details=[];
  const actions=summarizeActions(capsule.action);
  if(actions){details.push(`行動: ${actions}`);}
  const outcome=summarizeOutcome(capsule.outcome);
  if(outcome){details.push(outcome);}
  const reflection=summarizeReflection(capsule.reflection);
  if(reflection){details.push(reflection);}
  const future=summarizeFuture(capsule.next_intent);
  if(future){details.push(future);}
  return details.join(' ｜ ');
}
function renderTimeline(items, highlightId){
  if(!timelineListEl){return;}
  timelineListEl.innerHTML='';
  if(!items.length){
    timelineListEl.innerHTML='<li>まだタイムラインイベントがないよ</li>';
    return;
  }
  items.forEach((item,index)=>{
    const li=document.createElement('li');
    li.className='timeline-item';
    const tone=classifyCapsule(item);
    if(tone){li.classList.add(tone);}
    li.dataset.timelineIndex=String(index);
    li.setAttribute('role','button');
    li.setAttribute('aria-haspopup','dialog');
    li.tabIndex=0;
    li.addEventListener('click',()=>openTimelineModal(index,li));
    li.addEventListener('keydown',event=>{
      if(event.key==='Enter'||event.key===' '){event.preventDefault();event.stopPropagation();openTimelineModal(index,li);}
    });
    const time=document.createElement('div');
    time.className='time';
    time.textContent=formatRelative(item.decision_ts||item.timestamp)||'時刻不明';
    const headline=document.createElement('div');
    headline.className='headline';
    headline.textContent=buildTimelineHeadline(item);
    li.appendChild(time);
    li.appendChild(headline);
    const details=buildTimelineDetails(item);
    if(details){
      const detailEl=document.createElement('div');
      detailEl.className='details';
      detailEl.textContent=details;
      li.appendChild(detailEl);
    }
    if(highlightId && (item.capsule_id===highlightId||item.capsuleId===highlightId)){
      li.classList.add('timeline-highlight');
      setTimeout(()=>li.classList.remove('timeline-highlight'),4000);
    }
    const actions=document.createElement('div');
    actions.className='timeline-actions';
    const approveBtn=document.createElement('button');
    approveBtn.dataset.action='approve';
    approveBtn.type='button';
    approveBtn.textContent='👍 承認';
    approveBtn.addEventListener('click',evt=>{evt.preventDefault();evt.stopPropagation();performTimelineAction(index,'approve',approveBtn);});
    const rejectBtn=document.createElement('button');
    rejectBtn.dataset.action='reject';
    rejectBtn.type='button';
    rejectBtn.textContent='↩️ 差し戻し';
    rejectBtn.addEventListener('click',evt=>{evt.preventDefault();evt.stopPropagation();performTimelineAction(index,'reject',rejectBtn);});
    actions.appendChild(approveBtn);
    actions.appendChild(rejectBtn);
    li.appendChild(actions);
    timelineListEl.appendChild(li);
  });
}
function openTimelineModal(index, triggerEl){
  if(!modalEl||!modalBody||!modalDialog){return;}
  const item=timelineCache[index];
  if(!item){return;}
  activeTimelineCapsuleId=item.capsule_id||item.capsuleId||null;
  lastFocusedTimelineEl=triggerEl||null;
  renderTimelineModalContent(item);
  modalEl.classList.add('show');
  modalEl.setAttribute('aria-hidden','false');
  body.classList.add('modal-open');
  setTimeout(()=>modalDialog.focus({preventScroll:true}),0);
}
function closeTimelineModal(){
  if(!modalEl){return;}
  modalEl.classList.remove('show');
  modalEl.setAttribute('aria-hidden','true');
  body.classList.remove('modal-open');
  activeTimelineCapsuleId=null;
  if(lastFocusedTimelineEl){lastFocusedTimelineEl.focus();}
}
function renderTimelineModalContent(item){
  if(!modalBody){return;}
  const title=buildTimelineHeadline(item);
  const absolute=new Date(item.decision_ts||item.timestamp||Date.now()).toLocaleString('ja-JP', {year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit'});
  const relative=formatRelative(item.decision_ts||item.timestamp||Date.now());
  const decisionHtml=buildDecisionHtml(item);
  const reflectionHtml=buildReflectionHtml(item);
  const futureHtml=buildFutureHtml(item);
  modalBody.innerHTML=`
    <h2 id="timeline-modal-title">${title}</h2>
    <p class="modal-meta">${absolute}${relative?` ｜ ${relative}`:''}</p>
    <div class="modal-tabs" role="tablist">
      <button type="button" class="modal-tab-btn active" data-tab-target="decision" role="tab" aria-selected="true" aria-controls="tab-decision">決定</button>
      <button type="button" class="modal-tab-btn" data-tab-target="reflection" role="tab" aria-selected="false" aria-controls="tab-reflection">振り返り</button>
      <button type="button" class="modal-tab-btn" data-tab-target="future" role="tab" aria-selected="false" aria-controls="tab-future">次の意図</button>
    </div>
    <div class="modal-panels">
      <div class="modal-panel active" data-tab-panel="decision" id="tab-decision" role="tabpanel" aria-hidden="false">${decisionHtml}</div>
      <div class="modal-panel" data-tab-panel="reflection" id="tab-reflection" role="tabpanel" aria-hidden="true">${reflectionHtml}</div>
      <div class="modal-panel" data-tab-panel="future" id="tab-future" role="tabpanel" aria-hidden="true">${futureHtml}</div>
    </div>
  `;
  const tabButtons=modalBody.querySelectorAll('.modal-tab-btn');
  const panels=modalBody.querySelectorAll('.modal-panel');
  tabButtons.forEach(btn => {
    btn.addEventListener('click',()=>activateTab(btn.dataset.tabTarget,tabButtons,panels));
    btn.addEventListener('keydown',event => {
      if(event.key==='ArrowRight'||event.key==='ArrowLeft'){
        event.preventDefault();
        const arr=Array.from(tabButtons);
        const currentIndex=arr.indexOf(btn);
        const dir=event.key==='ArrowRight'?1:-1;
        const nextIndex=(currentIndex+dir+arr.length)%arr.length;
        arr[nextIndex].focus();
      }
    });
  });
}
function activateTab(name, buttons, panels){
  buttons.forEach(btn=>{
    const active=btn.dataset.tabTarget===name;
    btn.classList.toggle('active',active);
    btn.setAttribute('aria-selected',active?'true':'false');
  });
  panels.forEach(panel=>{
    const active=panel.dataset.tabPanel===name;
    panel.classList.toggle('active',active);
    panel.setAttribute('aria-hidden',active?'false':'true');
  });
}
function buildDecisionHtml(item){
  const capsule=item.capsule||{};
  const decision=capsule.decision||{};
  const selected=decision.selected||{};
  const candidates=Array.isArray(decision.candidates)?decision.candidates:[];
  const tradeOffs=Array.isArray(decision.trade_offs)?decision.trade_offs:[];
  const vector=formatVector(decision.priority_vector||{});
  const candidatesHtml=candidates.length?
    `<ul class="modal-list">${candidates.map(c=>{
      const vec=formatVector(c.vector||{});
      return `<li><span class="modal-tag">${c.task_id}</span>score: ${c.score}${vec?` ｜ ${vec}`:''}</li>`;
    }).join('')}</ul>`:
    '<p class="modal-empty">候補ログはまだないよ</p>';
  const tradeHtml=tradeOffs.length?`<ul class="modal-list">${tradeOffs.map(t=>`<li>${t}</li>`).join('')}</ul>`:'<p class="modal-empty">トレードオフはまだないよ</p>';
  return `
    <div class="modal-two-column">
      <div class="modal-section"><h3>選択タスク</h3><p><span class="modal-tag">task</span>${selected.task_id||'未定義'}</p>${selected.reason?`<p>${selected.reason}</p>`:''}</div>
      <div class="modal-section"><h3>優先度ベクトル</h3>${vector?`<p>${vector}</p>`:'<p class="modal-empty">ベクトル情報はまだないよ</p>'}</div>
    </div>
    <div class="modal-section"><h3>トレードオフ</h3>${tradeHtml}</div>
    <div class="modal-section"><h3>候補一覧</h3>${candidatesHtml}</div>
  `;
}
function buildReflectionHtml(item){
  const capsule=item.capsule||{};
  const reflection=capsule.reflection||{};
  const actions=Array.isArray(capsule.action)?capsule.action:[];
  const outcome=capsule.outcome||{};
  const wins=Array.isArray(reflection.what_went_well)?reflection.what_went_well:[];
  const issues=Array.isArray(reflection.issues)?reflection.issues:[];
  return `
    <div class="modal-two-column">
      <div class="modal-section"><h3>アクション</h3>${actions.length?`<ul class="modal-list">${actions.map(a=>`<li>${a}</li>`).join('')}</ul>`:'<p class="modal-empty">行動ログはまだないよ</p>'}</div>
      <div class="modal-section"><h3>結果</h3>${Object.keys(outcome).length?renderKeyValueList(outcome):'<p class="modal-empty">結果データはまだないよ</p>'}</div>
    </div>
    <div class="modal-two-column">
      <div class="modal-section"><h3>良かった点</h3>${wins.length?`<ul class="modal-list">${wins.map(w=>`<li>${w}</li>`).join('')}</ul>`:'<p class="modal-empty">良かった点はまだないよ</p>'}</div>
      <div class="modal-section"><h3>気になった点</h3>${issues.length?`<ul class="modal-list">${issues.map(i=>`<li>${i}</li>`).join('')}</ul>`:'<p class="modal-empty">気になった点はまだないよ</p>'}</div>
    </div>
    ${reflection.note?`<div class="modal-section"><h3>メモ</h3><p>${reflection.note}</p></div>`:''}
  `;
}
function renderKeyValueList(obj){
  const rows=Object.entries(obj).map(([k,v])=>`<li><span class="modal-tag">${k}</span>${typeof v==='object'?JSON.stringify(v):v}</li>`).join('');
  return rows?`<ul class="modal-list">${rows}</ul>`:'<p class="modal-empty">情報が見つからなかったよ</p>';
}
function buildFutureHtml(item){
  const capsule=item.capsule||{};
  const nextIntent=capsule.next_intent;
  if(!nextIntent){return '<p class="modal-empty">次の意図はまだ登録されていないよ</p>';}
  const dependencies=Array.isArray(nextIntent.dependencies)?nextIntent.dependencies:[];
  const requirements=Array.isArray(nextIntent.requirements)?nextIntent.requirements:[];
  const impact=nextIntent.expected_impact||{};
  const confidence=nextIntent.confidence!=null?`${Math.round(nextIntent.confidence*100)}%`:'不明';
  const futureScore=item.scores&&item.scores.future_confidence!=null?`${Math.round(item.scores.future_confidence*100)}%`:'';
  return `
    <div class="modal-section"><h3>意図</h3><p><span class="modal-tag">intent</span>${nextIntent.intent||'未定義'}</p><p>確信度: ${confidence}${futureScore?` ｜ 全体スコア: ${futureScore}`:''}</p><p>ETA: ${nextIntent.eta_hint||'未設定'}</p></div>
    <div class="modal-two-column">
      <div class="modal-section"><h3>依存関係</h3>${dependencies.length?`<ul class="modal-list">${dependencies.map(d=>`<li>${d}</li>`).join('')}</ul>`:'<p class="modal-empty">依存関係は特にないよ</p>'}</div>
      <div class="modal-section"><h3>要求事項</h3>${requirements.length?`<ul class="modal-list">${requirements.map(r=>`<li>${r}</li>`).join('')}</ul>`:'<p class="modal-empty">要求事項は特にないよ</p>'}</div>
    </div>
    <div class="modal-section"><h3>期待される影響</h3>${Object.keys(impact).length?renderKeyValueList(impact):'<p class="modal-empty">影響範囲はまだ記録されていないよ</p>'}</div>
  `;
}
function performTimelineAction(index, action, button){
  const item=timelineCache[index];
  if(!item){return;}
  const payload={
    action,
    capsule_id:item.capsule_id||item.capsuleId||null,
    record_id:item.capsule?.decision?.selected?.task_id||item.record_id||item.capsule_id,
    channel:item.capsule?.intent?.summary||item.capsule?.intent?.title||null,
    message:item.capsule?.reflection?.note||item.capsule?.decision?.selected?.reason||''
  };
  if(button){button.disabled=true;}
  fetch('/api/feedback/actions',{
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify(payload)
  }).then(safeJson).then(response=>{
    const li=document.querySelector(`li[data-timeline-index="${index}"]`);
    if(li){
      li.classList.add('acknowledged');
      if(response.task_id){li.dataset.feedbackTaskId=response.task_id;}
    }
  }).catch(error=>{
    console.error('Timeline action failed',error);
  }).finally(()=>{
    if(button){button.disabled=false;}
  });
}
function scheduleReconnect(){
  if(!streamingEnabled || reconnectTimer){return;}
  reconnectTimer=setTimeout(()=>{
    reconnectTimer=null;
    initEventStream();
  },5000);
}
function initEventStream(){
  if(!streamingEnabled || !FEED_BASE || typeof EventSource==='undefined'){return;}
  const url=new URL(`${FEED_BASE}/feed/events/stream`);
  if(FEED_TOKEN){url.searchParams.set('token',FEED_TOKEN);}
  if(eventSource){eventSource.close();}
  eventSource=new EventSource(url.toString());
  eventSource.onopen=()=>{
    if(reconnectTimer){clearTimeout(reconnectTimer); reconnectTimer=null;}
  };
  eventSource.onmessage=event=>{
    if(!event.data){return;}
    try{
      const payload=JSON.parse(event.data);
      if(payload.type==='timeline_update'){
        pendingTimelineHighlightId=payload.capsule_id||null;
        loadTimeline();
      } else if(payload.type==='commentary'){
        pushCommentaryEntry(payload,true);
      }
    }catch(error){console.error('Failed to parse stream payload',error);}
  };
  eventSource.addEventListener('ping',()=>{});
  eventSource.onerror=()=>{
    if(eventSource){eventSource.close();}
    scheduleReconnect();
  };
}
function loadMetricsAndServices(){
  fetch('/api/metrics').then(safeJson).then(data=>{
    document.getElementById('cpu').textContent = data.cpu.toFixed(1)+'%';
    document.getElementById('memory').textContent = data.memory.toFixed(1)+'%';
    document.getElementById('disk').textContent = data.disk.toFixed(1)+'%';
  }).catch(error=>console.error('metrics failed',error));
  fetch('/api/services').then(safeJson).then(data=>{
    renderServiceCards(data);
    const total=Object.values(data).reduce((acc,services)=>acc+services.length,0);
    const online=Object.values(data).flat().filter(svc=>svc.status==='online'||svc.status==='listening').length;
    document.getElementById('online').textContent = `${online}/${total}`;
  }).catch(error=>console.error('services failed',error));
}
function loadSubjectTracker(){
  const valueEl=document.getElementById('subject-values');
  const noteEl=document.getElementById('subject-note');
  if(!FEED_BASE){valueEl.textContent='設定待ち'; if(noteEl)noteEl.textContent='MACHI_FEED_BASE_URL を設定してね'; return;}
  fetch(`${FEED_BASE}/feed/priority/vector`,{headers:buildHeaders()}).then(safeJson).then(data=>{
    const vec=data.averages||{};
    const pct=key=>Math.round(((vec[key]||0)*100));
    valueEl.textContent=`安定: ${pct('stability')}% / 探索: ${pct('exploration')}% / 速度: ${pct('speed')}%`;
    if(noteEl){
      const dominant=Object.entries(vec||{}).reduce((best,current)=>current[1]>(best?best[1]:-Infinity)?current:best,null);
      if(dominant&&SUBJECT_VOCAB[dominant[0]]){
        const mood=SUBJECT_VOCAB[dominant[0]];
        noteEl.textContent=`${mood.comment}（${mood.label}優勢）`;
      }else{
        noteEl.textContent='最新の移動平均を表示中';
      }
    }
  }).catch(error=>{
    console.error('subject tracker failed',error);
    valueEl.textContent='まだデータがないよ';
    if(noteEl)noteEl.textContent='Reflection Feedのデータが溜まったら表示するよ';
  });
}
function loadLearning(){
  const list=document.getElementById('learning-list');
  if(!FEED_BASE){list.innerHTML='<li>データ源が設定されていません</li>';return;}
  fetch('/api/feed/learning').then(safeJson).then(data=>{
    const items=(data.items||[]).slice().sort((a,b)=>(b.count||0)-(a.count||0));
    if(!items.length){list.innerHTML='<li>まだ学習ログがないよ</li>';return;}
    list.innerHTML='';
    const top=items[0];
    if(top){
      const comment=document.createElement('li');
      comment.className='insight-comment';
      comment.textContent=`最近は「${top.pattern}」の学習がいちばん多いよ。`;
      list.appendChild(comment);
    }
    items.slice(0,5).forEach(item=>{
      const li=document.createElement('li');
      li.textContent=`${item===top?'✨ ':''}${item.pattern} ×${item.count}`;
      list.appendChild(li);
    });
  }).catch(error=>{
    console.error('learning failed',error);
    list.innerHTML='<li>読み込み失敗</li>';
  });
}
function loadFuture(){
  const list=document.getElementById('future-list');
  if(!FEED_BASE){list.innerHTML='<li>データ源が設定されていません</li>';return;}
  fetch('/api/feed/future').then(safeJson).then(data=>{
    const items=data.items||[];
    if(!items.length){list.innerHTML='<li>予定はまだないよ</li>';return;}
    list.innerHTML='';
    items.slice(0,5).forEach(item=>{
      const confidence=item.confidence!=null?Math.round(item.confidence*100):null;
      let tone='アイデアを温め中';
      if(confidence!==null){tone=confidence>=70?'ほぼ決定で動く予定':confidence>=40?'候補として様子見':'アイデアを温め中';}
      list.innerHTML += `<li>${item.intent} ${confidence!=null?`(確信度 ${confidence}%)`:''} - ${tone}</li>`;
    });
  }).catch(error=>{
    console.error('future failed',error);
    list.innerHTML='<li>読み込み失敗</li>';
  });
}
function loadAlerts(){
  const list=document.getElementById('alert-list');
  if(!FEED_BASE){list.innerHTML='<li>データ源が設定されていません</li>';return;}
  fetch('/api/feed/summary').then(safeJson).then(summary=>{
    const alerts=describeAlerts(summary);
    if(!alerts.length){list.innerHTML='<li>特筆すべき注意はありません</li>';return;}
    list.innerHTML='';
    alerts.forEach(alert=>{
      const li=document.createElement('li');
      li.className=`alert-item alert-${alert.level||'info'}`;
      li.textContent=alert.message||alert;
      list.appendChild(li);
    });
  }).catch(error=>{
    console.error('summary failed',error);
    list.innerHTML='<li>読み込み失敗</li>';
  });
}
function loadCommentary(){
  if(!FEED_BASE || !streamingEnabled){return;}
  fetch('/api/feed/commentary?limit='+MAX_TICKER_ITEMS).then(safeJson).then(data=>{
    mergeCommentary(data.items||[]);
  }).catch(error=>console.error('commentary failed',error));
}
function loadTimeline(){
  fetch('/api/feed/capsules?limit=12').then(safeJson).then(data=>{
    timelineCache=data.items||[];
    renderTimeline(timelineCache, pendingTimelineHighlightId);
    pendingTimelineHighlightId=null;
    if(modalEl&&modalEl.classList.contains('show')&&activeTimelineCapsuleId){
      const idx=timelineCache.findIndex(item=>item.capsule_id===activeTimelineCapsuleId);
      if(idx!==-1){renderTimelineModalContent(timelineCache[idx]);} else {closeTimelineModal();}
    }
  }).catch(error=>{
    console.error('timeline failed',error);
    if(timelineListEl){timelineListEl.innerHTML='<li>読み込み失敗</li>';}
  });
}
function initIntervals(){
  loadMetricsAndServices();
  loadSubjectTracker();
  loadLearning();
  loadFuture();
  loadAlerts();
  loadTimeline();
  if(streamingEnabled){
    loadCommentary();
    initEventStream();
  } else if(tickerStreamEl){
    tickerStreamEl.innerHTML = '<div class="ticker-item"><span class="ticker-message">実況を停止中だよ</span></div>';
  }
  updateModeTag(INITIAL_MODE);
  setInterval(loadMetricsAndServices, 30000);
  setInterval(loadSubjectTracker, 30000);
  setInterval(loadLearning, 45000);
  setInterval(loadFuture, 45000);
  setInterval(loadAlerts, 45000);
  setInterval(loadTimeline, 45000);
  setInterval(()=>{ if(streamingEnabled){ loadCommentary(); } }, 60000);
}
if(modalClose){modalClose.addEventListener('click', closeTimelineModal);}
if(modalEl){modalEl.addEventListener('click', event=>{if(event.target===modalEl){closeTimelineModal();}});}
document.addEventListener('keydown', event=>{if(event.key==='Escape'&&modalEl&&modalEl.classList.contains('show')){closeTimelineModal();}});
window.addEventListener('beforeunload',()=>{if(eventSource){eventSource.close();}});
function updateStreamingToggle(){
  if(!streamingToggleBtn){return;}
  streamingToggleBtn.textContent = streamingEnabled ? '🟢 実況ON' : '🔕 実況OFF';
  streamingToggleBtn.style.background = streamingEnabled ? 'rgba(74,222,128,0.35)' : 'rgba(148,163,184,0.35)';
}
function setStreamingEnabled(enabled){
  if(streamingEnabled === enabled){return;}
  streamingEnabled = enabled;
  try {
    localStorage.setItem(STORAGE_KEYS.streaming, String(enabled));
  } catch (error) {
    console.warn('streaming preference persist failed', error);
  }
  updateStreamingToggle();
  if(!streamingEnabled){
    if(eventSource){eventSource.close(); eventSource = null;}
    if(reconnectTimer){clearTimeout(reconnectTimer); reconnectTimer=null;}
    if(tickerStreamEl){
      tickerStreamEl.innerHTML = '<div class="ticker-item"><span class="ticker-message">実況を停止中だよ</span></div>';
    }
  } else {
    renderTicker();
    loadCommentary();
    initEventStream();
  }
}
function restoreStreamingPreference(){
  try {
    const raw = localStorage.getItem(STORAGE_KEYS.streaming);
    if(raw === 'false'){
      streamingEnabled = false;
    } else if(raw === 'true'){
      streamingEnabled = true;
    }
  } catch (error) {
    console.warn('streaming preference read failed', error);
  }
}
if(streamingToggleBtn){
  streamingToggleBtn.addEventListener('click',()=>{
    setStreamingEnabled(!streamingEnabled);
  });
}
restoreStreamingPreference();
updateStreamingToggle();
initIntervals();
</script>
</body>
</html>
"""
    return (
        template
        .replace("__FEED_BASE__", feed_base_js)
        .replace("__FEED_TOKEN__", feed_token_js)
        .replace("__INITIAL_MODE__", mode_js)
    )


if __name__ == "__main__":  # pragma: no cover
    print("=" * 60)
    print("🎯 ManaOS Unified Portal v2.0 - Working Version")
    print("=" * 60)
    print("📍 http://localhost:5050")
    print("🌐 Tailscale: http://100.93.120.33:5050")
    print("🌍 External: http://163.44.120.49:5050")
    print("=" * 60)
    print("✨ Managing 17 Services")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5050, debug=os.getenv(
        "DEBUG", "False").lower() == "true")
