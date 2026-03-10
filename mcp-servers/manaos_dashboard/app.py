#!/usr/bin/env python3
"""
🌸 ManaOS Trinity - 統合ダッシュボード
全サービスを一元管理する美しいメインUI
"""

from collections import deque
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
from flask_httpauth import HTTPBasicAuth
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import requests
import psutil
from datetime import datetime, timedelta
import logging
import threading
import time
import subprocess
import os
import secrets
import json
import math
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

sys.path.insert(0, "/root/manaos-knowledge")
from analytics.infra_health_analyzer import generate_infrastructure_health_summary  # type: ignore

# システム連携API
try:
    from system_integration_api import get_all_status, get_system_status, get_integration_status, get_sync_status, get_metrics
    SYSTEM_INTEGRATION_API_AVAILABLE = True
except ImportError:
    SYSTEM_INTEGRATION_API_AVAILABLE = False
    logger.warning("System integration API not available")  # type: ignore[name-defined]

logger = logging.getLogger(__name__)

# Google Drive連携をインポート
try:
    from google_drive_helper import drive_helper
    GOOGLE_DRIVE_ENABLED = True
except ImportError:
    GOOGLE_DRIVE_ENABLED = False
    logger.warning("Google Drive helper not available")

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(32)  # セキュアなランダムキー
app.config['SESSION_COOKIE_SECURE'] = False  # HTTPSの場合はTrue
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# CORS設定を厳密に
socketio = SocketIO(app, cors_allowed_origins=[
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://163.44.120.49:3000",
    "http://100.93.120.33:3000"
], async_mode=os.environ.get("FLASK_SOCKETIO_ASYNC_MODE", "threading"))  # type: ignore

# レート制限
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Basic認証（環境変数から取得、デフォルトはmana/trinity2025）
auth = HTTPBasicAuth()
DASHBOARD_USER = os.environ.get('DASHBOARD_USER', 'mana')
DASHBOARD_PASSWORD = os.environ.get('DASHBOARD_PASSWORD', 'trinity2025')

@auth.verify_password
def verify_password(username, password):
    """パスワード検証"""
    if username == DASHBOARD_USER:
        # パスワードハッシュで比較（本番環境ではハッシュ化推奨）
        return password == DASHBOARD_PASSWORD
    return False

# X280コマンドホワイトリスト
ALLOWED_X280_COMMANDS = [
    'dir', 'ls', 'echo', 'whoami', 'hostname', 'date', 'time',
    'systeminfo', 'tasklist', 'netstat', 'ipconfig', 'ping',
    'Get-Process', 'Get-Service', 'Get-ComputerInfo'
]

def is_command_allowed(command):
    """コマンドがホワイトリストに含まれるか確認"""
    command_parts = command.strip().split()
    if not command_parts:
        return False

    base_command = command_parts[0].lower()
    for allowed in ALLOWED_X280_COMMANDS:
        if base_command == allowed.lower():
            return True
    return False

# リトライデコレーター
def retry_on_failure(max_attempts=3, delay=1, backoff=2):
    """失敗時に自動リトライするデコレーター"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            attempt = 0
            current_delay = delay

            while attempt < max_attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempt += 1
                    if attempt >= max_attempts:
                        logger.error(f"Failed after {max_attempts} attempts: {e}")
                        raise

                    logger.warning(f"Attempt {attempt} failed, retrying in {current_delay}s: {e}")
                    time.sleep(current_delay)
                    current_delay *= backoff

        return wrapper
    return decorator

@retry_on_failure(max_attempts=3, delay=1)
def check_service_health_with_retry(service_id, config):
    """リトライ機能付きサービスヘルスチェック"""
    response = requests.get(config['url'], timeout=2)
    return {
        'status': 'online' if response.status_code == 200 else 'degraded',
        'response_time': response.elapsed.total_seconds() * 1000
    }

# ロギング設定（ローテーション付き）
os.makedirs('/root/logs', exist_ok=True)
log_handler = RotatingFileHandler(
    '/root/logs/manaos_dashboard.log',
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
log_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))

console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))

logging.basicConfig(
    level=logging.INFO,
    handlers=[log_handler, console_handler]
)
logger = logging.getLogger(__name__)

# 通知システムの状態管理
notification_state = {
    'last_gmail_count': 0,
    'last_calendar_events': [],
    'last_system_alert': None,
    'last_service_status': {},
    'calendar_reminders_sent': set()
}

# 自動化ルール
automation_rules = [
    {
        'id': 'gmail_summary',
        'name': 'Gmail定期要約',
        'enabled': True,
        'trigger': 'interval',  # interval or event
        'interval_minutes': 60,  # 60分ごと
        'action': 'create_gmail_summary',
        'last_run': None
    },
    {
        'id': 'weekly_report',
        'name': '週次レポート',
        'enabled': True,
        'trigger': 'schedule',
        'schedule': '0 9 * * MON',  # 毎週月曜9時
        'action': 'generate_weekly_report',
        'last_run': None
    },
    {
        'id': 'system_monitor',
        'name': 'システム監視',
        'enabled': True,
        'trigger': 'event',
        'condition': 'cpu > 90 or memory > 90',
        'action': 'send_alert',
        'last_run': None
    }
]

# サービス定義
SERVICES = {
    'trinity_secretary': {
        'name': 'Trinity秘書システム',
        'icon': '🤖',
        'url': 'http://localhost:8087',
        'port': 8087
    },
    'google_services': {
        'name': 'Google Services',
        'icon': '📧',
        'url': 'http://localhost:8097',
        'port': 8097
    },
    'screen_sharing': {
        'name': 'Mana Screen Sharing',
        'icon': '🖥️',
        'url': 'http://localhost:5008',
        'port': 5008
    },
    'command_center': {
        'name': 'Command Center',
        'icon': '🎯',
        'url': 'http://localhost:10000',
        'port': 10000
    },
    'manaos_v3': {
        'name': 'ManaOS v3.0 Orchestrator',
        'icon': '🎯',
        'url': 'http://localhost:9200',
        'port': 9200
    }
}

INFRA_SUMMARY_PATH = Path("/root/logs/system_health_summary.json")
INFRA_HISTORY_DIR = Path("/root/logs/system_health_history")
STATUS_ORDER = {"critical": 0, "warning": 1, "ok": 2, "unknown": 3}
TRINITY_NOTIFICATIONS_PATH = Path("/root/trinity_workspace/logs/trinity_notifications.jsonl")


def format_number_display(value: object) -> str:
    """人間向けの数値表示を生成"""
    if value is None:
        return "数値情報なし"
    if isinstance(value, (int, float)):
        try:
            if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
                return "数値情報なし"
        except TypeError:
            return "数値情報なし"
        if isinstance(value, float):
            formatted = f"{value:.1f}"
            if formatted.endswith(".0"):
                formatted = formatted[:-2]
            return formatted
        return str(value)
    return str(value)


def summarize_detail(detail: dict) -> str:
    """詳細情報から簡易サマリーを生成"""
    if not detail:
        return ""
    for key in ("info", "state", "note", "status", "level"):
        value = detail.get(key)
        if value:
            return str(value)
    if "port" in detail and "protocol" in detail:
        return f"{detail.get('protocol')}:{detail.get('port')}"
    if "unit" in detail:
        return str(detail.get("unit"))
    return ""


def format_improvement_for_dashboard(item: dict) -> dict:
    """インフラ改善ポイントをダッシュボード表示用に整形"""
    detail = item.get("詳細") or {}
    action = (
        detail.get("action")
        or detail.get("recommended_action")
        or detail.get("hint")
        or item.get("推奨対応")
        or ""
    )
    category = item.get("category") or "unknown"
    severity = item.get("重要度") or "medium"
    raw_status = item.get("raw_status") or ""
    current_value = item.get("現在値")
    threshold_value = item.get("閾値")

    return {
        "label": item.get("監視項目"),
        "category": category,
        "severity": severity,
        "status": raw_status,
        "value": current_value if isinstance(current_value, (int, float)) else None,
        "value_display": format_number_display(current_value),
        "threshold": threshold_value if isinstance(threshold_value, (int, float)) else None,
        "threshold_display": format_number_display(threshold_value),
        "action": action,
        "detail_summary": summarize_detail(detail),
        "details": detail,
    }

def load_infra_health_summary():
    """最新のインフラヘルスチェック結果を読み込む"""
    default_response = {
        "status": "unknown",
        "timestamp": None,
        "notes": [],
        "categories": [],
        "counts": {"ok": 0, "warning": 0, "critical": 0},
        "severity_counts": {},
        "category_breakdown": [],
        "improvement_points": [],
        "summary_path": str(INFRA_SUMMARY_PATH),
        "history_dir": str(INFRA_HISTORY_DIR),
        "error": None,
        "analysis_error": None,
    }

    try:
        with INFRA_SUMMARY_PATH.open("r", encoding="utf-8") as fp:
            raw_summary = json.load(fp)
    except FileNotFoundError:
        default_response["error"] = "not_found"
        return default_response
    except json.JSONDecodeError:
        default_response["error"] = "invalid_json"
        return default_response

    status = raw_summary.get("overall_status", "unknown")
    timestamp = raw_summary.get("timestamp")
    notes = (raw_summary.get("notes") or [])[:3]

    categories_raw = raw_summary.get("categories", [])
    sorted_categories = sorted(
        categories_raw,
        key=lambda cat: STATUS_ORDER.get(cat.get("status", "unknown"), 3)
    )

    categories = []
    counts = {"ok": 0, "warning": 0, "critical": 0}
    for cat in sorted_categories:
        cat_status = cat.get("status", "unknown")
        counts_by_status = cat.get("counts_by_status") or {}
        for key in ("ok", "warning", "critical"):
            value = counts_by_status.get(key)
            if isinstance(value, int):
                counts[key] += value
        categories.append({
            "name": cat.get("name", "unknown"),
            "status": cat_status,
            "counts": counts_by_status,
        })

    severity_counts: dict[str, int] = {}
    category_breakdown: list[dict] = []
    improvement_points: list[dict] = []
    analysis_error: str | None = None

    try:
        analysis = generate_infrastructure_health_summary(str(INFRA_SUMMARY_PATH))
        if analysis.get("success"):
            status_summary = analysis.get("status_summary") or {}
            severity_counts = status_summary.get("severity_counts") or {}
            raw_category_breakdown = status_summary.get("category_breakdown") or []
            for entry in raw_category_breakdown:
                category_breakdown.append(
                    {
                        "category": entry.get("category", "unknown"),
                        "high": entry.get("high", 0),
                        "medium": entry.get("medium", 0),
                        "low": entry.get("low", 0),
                        "items": (entry.get("items") or [])[:5],
                    }
                )
            improvements_raw = analysis.get("improvement_points") or []
            improvement_points = [
                format_improvement_for_dashboard(item) for item in improvements_raw[:10]
            ]
        else:
            analysis_error = analysis.get("error") or analysis.get("error_type")
    except Exception as exc:  # pragma: no cover
        analysis_error = f"analysis_failed: {exc}"
        logger.warning("infra health summary analysis failed: %s", exc)

    return {
        "status": status,
        "timestamp": timestamp,
        "notes": notes,
        "categories": categories[:5],
        "counts": counts,
        "severity_counts": severity_counts,
        "category_breakdown": category_breakdown,
        "improvement_points": improvement_points,
        "summary_path": str(INFRA_SUMMARY_PATH),
        "history_dir": str(INFRA_HISTORY_DIR),
        "error": None,
        "analysis_error": analysis_error,
    }


def load_trinity_notifications(limit: int = 50) -> list[dict]:
    """Trinity通知ログから最新イベントを読み込む"""
    if limit <= 0:
        return []

    if not TRINITY_NOTIFICATIONS_PATH.exists():
        return []

    lines = deque(maxlen=limit)
    try:
        with TRINITY_NOTIFICATIONS_PATH.open("r", encoding="utf-8") as fp:
            for line in fp:
                stripped = line.strip()
                if stripped:
                    lines.append(stripped)
    except Exception as exc:
        logger.warning(f"トリニティ通知ログの読み込みに失敗: {exc}")
        return []

    notifications: list[dict] = []
    for raw in lines:
        try:
            record = json.loads(raw)
        except json.JSONDecodeError:
            continue

        payload = record.get("payload") or {}
        lines_body = payload.get("lines") or []
        fields = payload.get("fields") or []

        formatted_fields: list[dict] = []
        for field in fields:
            if isinstance(field, (list, tuple)) and len(field) >= 2:
                formatted_fields.append({"label": str(field[0]), "value": str(field[1])})
            elif isinstance(field, dict):
                label = field.get("label") or field.get("name")
                value = field.get("value") or field.get("text")
                if label is not None and value is not None:
                    formatted_fields.append({"label": str(label), "value": str(value)})

        title = payload.get("title") or ""
        slack_text = record.get("slack_text") or ""
        if not title:
            if slack_text:
                title = slack_text.splitlines()[0][:120]
            elif lines_body:
                title = str(lines_body[0])

        notifications.append(
            {
                "timestamp": record.get("timestamp"),
                "level": record.get("level", "info"),
                "emoji": record.get("emoji"),
                "title": title,
                "lines": [str(item) for item in lines_body],
                "fields": formatted_fields,
                "footer": payload.get("footer") or "",
                "channels": record.get("channels") or {},
            }
        )

    notifications.reverse()
    return notifications


def check_service_health(service_id, config):
    """サービスの健全性チェック（エラーハンドリング強化版）"""
    try:
        return check_service_health_with_retry(service_id, config)
    except requests.exceptions.Timeout:
        logger.warning(f"Service timeout: {service_id}")
        return {
            'status': 'offline',
            'response_time': None,
            'error': 'timeout'
        }
    except requests.exceptions.ConnectionError:
        logger.warning(f"Service connection error: {service_id}")
        return {
            'status': 'offline',
            'response_time': None,
            'error': 'connection_error'
        }
    except Exception as e:
        logger.error(f"Service health check error for {service_id}: {e}")
        return {
            'status': 'offline',
            'response_time': None,
            'error': str(e)
        }

def get_system_metrics():
    """システムメトリクスを取得"""
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')

    return {
        'cpu': round(cpu_percent, 1),
        'memory': round(memory.percent, 1),
        'disk': round(disk.percent, 1),
        'uptime': round(datetime.now().timestamp() - psutil.boot_time(), 0)
    }

@retry_on_failure(max_attempts=2, delay=0.5)  # type: ignore
def get_gmail_summary():
    """Gmail新着サマリーを取得（リトライ機能付き）"""
    try:
        response = requests.get('http://localhost:8097/api/gmail/messages?max_results=5', timeout=3)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                return {
                    'count': len(data.get('messages', [])),
                    'latest': data.get('messages', [])[0:3],
                    'available': True
                }
    except Exception as e:
        logger.debug(f"Gmail summary error: {e}")
        raise

    return {'count': 0, 'latest': [], 'available': False}

@retry_on_failure(max_attempts=2, delay=0.5)  # type: ignore
def get_calendar_summary():
    """カレンダー予定サマリーを取得（リトライ機能付き）"""
    try:
        response = requests.get('http://localhost:8097/api/calendar/events?max_results=5', timeout=3)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                events = data.get('events', [])
                return {
                    'count': len(events),
                    'today': [e for e in events if e.get('start')][:3],
                    'available': True
                }
    except Exception as e:
        logger.debug(f"Calendar summary error: {e}")
        raise

    return {'count': 0, 'today': [], 'available': False}

@app.route('/')
@auth.login_required
def index():
    """メインダッシュボード"""
    return render_template('index.html')

@app.route('/orchestrator')
@auth.login_required
def orchestrator():
    """Trinity Orchestrator v1.0 UI"""
    return render_template('orchestrator.html')

@app.after_request
def set_security_headers(response):
    """セキュリティヘッダーを設定"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self' https://cdn.socket.io; script-src 'self' 'unsafe-inline' https://cdn.socket.io; style-src 'self' 'unsafe-inline'"
    return response

@app.route('/static/icon-<size>.png')
def generate_icon(size):
    """PWA用アイコンを動的生成（SVG）"""
    from flask import Response

    # 簡易的なSVGアイコン
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}">
        <defs>
            <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" style="stop-color:#667eea;stop-opacity:1" />
                <stop offset="100%" style="stop-color:#764ba2;stop-opacity:1" />
            </linearGradient>
        </defs>
        <rect width="{size}" height="{size}" fill="url(#grad)" rx="20%"/>
        <text x="50%" y="50%" font-size="{int(size)*0.5}" text-anchor="middle"
              dominant-baseline="middle" fill="white" font-family="sans-serif">🌸</text>
    </svg>'''

    return Response(svg, mimetype='image/svg+xml')

@app.route('/static/screenshot.png')
def generate_screenshot():
    """スクリーンショットプレースホルダー"""
    from flask import Response

    svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720">
        <defs>
            <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" style="stop-color:#667eea;stop-opacity:1" />
                <stop offset="100%" style="stop-color:#764ba2;stop-opacity:1" />
            </linearGradient>
        </defs>
        <rect width="1280" height="720" fill="url(#grad)"/>
        <text x="50%" y="50%" font-size="48" text-anchor="middle"
              dominant-baseline="middle" fill="white" font-family="sans-serif" font-weight="bold">
            ManaOS Trinity Dashboard
        </text>
    </svg>'''

    return Response(svg, mimetype='image/svg+xml')

@app.route('/api/status')
@auth.login_required
@limiter.limit("60 per minute")
def get_status():
    """全体ステータスを取得"""
    services_status = {}
    for service_id, config in SERVICES.items():
        services_status[service_id] = {
            **config,
            **check_service_health(service_id, config)
        }

    return jsonify({
        'timestamp': datetime.now().isoformat(),
        'system_metrics': get_system_metrics(),
        'services': services_status,
        'gmail_summary': get_gmail_summary(),
        'calendar_summary': get_calendar_summary()
    })

@app.route('/api/infra-health')
@auth.login_required
@limiter.limit("30 per minute")
def get_infra_health():
    """インフラヘルスチェックの最新結果を返す"""
    summary = load_infra_health_summary()
    return jsonify(summary)


@app.route('/api/trinity/notifications')
@auth.login_required
@limiter.limit("30 per minute")
def get_trinity_notifications():
    """Trinity通知ログを返す"""
    try:
        limit = int(request.args.get("limit", 20))
    except ValueError:
        limit = 20
    limit = max(1, min(limit, 200))
    notifications = load_trinity_notifications(limit=limit)
    return jsonify(
        {
            "notifications": notifications,
            "limit": limit,
        }
    )

@app.route('/api/manaos/command', methods=['POST'])
def manaos_command():
    """ManaOS v3.0に自然言語コマンドを送信"""
    data = request.json
    text = data.get('text', '')
    actor = data.get('actor', 'remi')

    try:
        response = requests.post(
            'http://localhost:9200/api/v3/run',
            json={'text': text, 'actor': actor},
            timeout=30
        )

        if response.status_code == 200:
            return jsonify({
                'success': True,
                'result': response.json()
            })
        else:
            return jsonify({
                'success': False,
                'error': f'HTTP {response.status_code}'
            }), 500
    except Exception as e:
        logger.error(f"ManaOS command error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/screen-sharing/status')
def screen_sharing_status():
    """画面共有ステータス取得"""
    try:
        response = requests.get('http://localhost:5008/api/status', timeout=3)
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'error': 'Screen sharing service unavailable'}), 503
    except requests.RequestException:
        return jsonify({'error': 'Screen sharing service unavailable'}), 503

@app.route('/api/screen-sharing/screenshot', methods=['POST'])
@auth.login_required
@limiter.limit("30 per hour")
def take_screenshot():
    """スクリーンショットを撮影してGoogle Driveに保存"""
    try:
        # スクリーンショット撮影
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'screenshot_{timestamp}.png'

        # 画面共有サービスに撮影リクエスト
        response = requests.post('http://localhost:5008/api/screenshot',
                                json={'filename': filename}, timeout=10)

        if response.status_code == 200:
            data = response.json()
            screenshot_path = data.get('path', f'/tmp/{filename}')

            result = {
                'success': True,
                'filename': filename,
                'path': screenshot_path,
                'message': 'スクリーンショットを保存しました'
            }

            # Google Driveへアップロード
            if GOOGLE_DRIVE_ENABLED and os.path.exists(screenshot_path):
                drive_result = drive_helper.upload_screenshot(screenshot_path)  # type: ignore[possibly-unbound]
                if drive_result:
                    result['drive_link'] = drive_result.get('link')
                    result['message'] += ' (Google Driveに保存)'
                    logger.info(f"Screenshot uploaded to Google Drive: {drive_result.get('link')}")

            return jsonify(result)
        else:
            return jsonify({'success': False, 'error': 'Screenshot failed'}), 500

    except Exception as e:
        logger.error(f"Screenshot error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/screen-sharing/recording/start', methods=['POST'])
def start_recording():
    """録画開始"""
    try:
        response = requests.post('http://localhost:5008/api/recording/start', timeout=5)
        if response.status_code == 200:
            return jsonify({
                'success': True,
                'message': '録画を開始しました'
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to start recording'}), 500
    except Exception as e:
        logger.error(f"Recording start error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/screen-sharing/recording/stop', methods=['POST'])
@auth.login_required
def stop_recording():
    """録画停止とGoogle Driveアップロード"""
    try:
        response = requests.post('http://localhost:5008/api/recording/stop', timeout=5)
        if response.status_code == 200:
            data = response.json()
            recording_path = data.get('path')

            result = {
                'success': True,
                'path': recording_path,
                'message': '録画を停止し、保存しました'
            }

            # Google Driveへアップロード
            if GOOGLE_DRIVE_ENABLED and recording_path and os.path.exists(recording_path):
                drive_result = drive_helper.upload_recording(recording_path)  # type: ignore[possibly-unbound]
                if drive_result:
                    result['drive_link'] = drive_result.get('link')
                    result['message'] += ' (Google Driveに保存)'
                    logger.info(f"Recording uploaded to Google Drive: {drive_result.get('link')}")

            return jsonify(result)
        else:
            return jsonify({'success': False, 'error': 'Failed to stop recording'}), 500
    except Exception as e:
        logger.error(f"Recording stop error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/x280/files')
def x280_list_files():
    """X280のファイル一覧を取得"""
    path = request.args.get('path', 'C:\\Users\\mana')

    try:
        # SSH経由でX280のファイル一覧を取得
        result = subprocess.run(
            ['ssh', 'x280', f'dir "{path}" /B /A'],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            files = result.stdout.strip().split('\n')
            files = [f.strip() for f in files if f.strip()]

            return jsonify({
                'success': True,
                'path': path,
                'files': files,
                'count': len(files)
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to list files'
            }), 500

    except Exception as e:
        logger.error(f"X280 file list error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/x280/download', methods=['POST'])
def x280_download_file():
    """X280からファイルをダウンロード"""
    data = request.json
    remote_path = data.get('path')

    if not remote_path:
        return jsonify({'success': False, 'error': 'Path required'}), 400

    try:
        # ファイル名を取得
        filename = os.path.basename(remote_path)
        local_path = f'/tmp/{filename}'

        # scpでファイル転送
        result = subprocess.run(
            ['scp', f'x280:{remote_path}', local_path],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            return jsonify({
                'success': True,
                'filename': filename,
                'local_path': local_path,
                'message': 'ファイルをダウンロードしました'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Download failed'
            }), 500

    except Exception as e:
        logger.error(f"X280 download error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/x280/upload', methods=['POST'])
def x280_upload_file():
    """X280へファイルをアップロード"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'}), 400

    file = request.files['file']
    remote_path = request.form.get('remote_path', 'C:\\Users\\mana\\Downloads')

    try:
        # 一時ファイルに保存
        temp_path = f'/tmp/{file.filename}'
        file.save(temp_path)

        # scpでファイル転送
        result = subprocess.run(
            ['scp', temp_path, f'x280:{remote_path}\\{file.filename}'],
            capture_output=True,
            text=True,
            timeout=30
        )

        # 一時ファイル削除
        os.remove(temp_path)

        if result.returncode == 0:
            return jsonify({
                'success': True,
                'filename': file.filename,
                'message': 'ファイルをアップロードしました'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Upload failed'
            }), 500

    except Exception as e:
        logger.error(f"X280 upload error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/x280/execute', methods=['POST'])
@auth.login_required
@limiter.limit("10 per minute")
def x280_execute_command():
    """X280でコマンドを実行（ホワイトリスト制限付き）"""
    data = request.json
    command = data.get('command')

    if not command:
        return jsonify({'success': False, 'error': 'Command required'}), 400

    # コマンドホワイトリストチェック
    if not is_command_allowed(command):
        logger.warning(f"Blocked unauthorized command: {command}")
        return jsonify({
            'success': False,
            'error': 'Command not allowed. Allowed commands: ' + ', '.join(ALLOWED_X280_COMMANDS)
        }), 403

    try:
        # SSH経由でコマンド実行（タイムアウト短縮）
        result = subprocess.run(
            ['ssh', 'x280', command],
            capture_output=True,
            text=True,
            timeout=10  # 30秒→10秒に短縮
        )

        return jsonify({
            'success': True,
            'output': result.stdout,
            'error': result.stderr,
            'return_code': result.returncode
        })

    except subprocess.TimeoutExpired:
        logger.error(f"X280 command timeout: {command}")
        return jsonify({
            'success': False,
            'error': 'Command execution timeout'
        }), 408
    except Exception as e:
        logger.error(f"X280 execute error: {e}")
        return jsonify({
            'success': False,
            'error': 'Command execution failed'
        }), 500

@app.route('/api/x280/apps')
def x280_get_apps():
    """X280のアプリケーション一覧"""
    # よく使うアプリケーション
    apps = [
        {'name': 'Chrome', 'path': 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'},
        {'name': 'VSCode', 'path': 'C:\\Program Files\\Microsoft VS Code\\Code.exe'},
        {'name': 'Explorer', 'path': 'explorer.exe'},
        {'name': 'PowerShell', 'path': 'powershell.exe'},
        {'name': 'Notepad', 'path': 'notepad.exe'},
        {'name': 'Calculator', 'path': 'calc.exe'}
    ]

    return jsonify({
        'success': True,
        'apps': apps
    })

@app.route('/api/x280/launch', methods=['POST'])
def x280_launch_app():
    """X280でアプリケーションを起動"""
    data = request.json
    app_path = data.get('path')

    if not app_path:
        return jsonify({'success': False, 'error': 'App path required'}), 400

    try:
        # SSH経由でアプリ起動
        result = subprocess.run(
            ['ssh', 'x280', f'start "" "{app_path}"'],
            capture_output=True,
            text=True,
            timeout=10
        )

        return jsonify({
            'success': True,
            'message': f'{app_path} を起動しました'
        })

    except Exception as e:
        logger.error(f"X280 launch error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/automation/rules')
def get_automation_rules():
    """自動化ルール一覧を取得"""
    return jsonify({
        'rules': automation_rules,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/automation/rules/<rule_id>/toggle', methods=['POST'])
def toggle_automation_rule(rule_id):
    """自動化ルールの有効/無効を切り替え"""
    for rule in automation_rules:
        if rule['id'] == rule_id:
            rule['enabled'] = not rule['enabled']
            logger.info(f"自動化ルール '{rule['name']}' を {'有効' if rule['enabled'] else '無効'} にしました")
            return jsonify({
                'success': True,
                'rule': rule
            })

    return jsonify({
        'success': False,
        'error': 'Rule not found'
    }), 404

@app.route('/api/automation/execute/<rule_id>', methods=['POST'])
def execute_automation_rule(rule_id):
    """自動化ルールを手動実行"""
    for rule in automation_rules:
        if rule['id'] == rule_id:
            result = execute_automation_action(rule)
            rule['last_run'] = datetime.now().isoformat()
            return jsonify({
                'success': True,
                'result': result,
                'rule': rule
            })

    return jsonify({
        'success': False,
        'error': 'Rule not found'
    }), 404

def execute_automation_action(rule):
    """自動化アクションを実行"""
    action = rule['action']

    try:
        if action == 'create_gmail_summary':
            return create_gmail_summary_action()
        elif action == 'generate_weekly_report':
            return generate_weekly_report_action()
        elif action == 'send_alert':
            return send_system_alert_action()
        else:
            return {'error': 'Unknown action'}
    except Exception as e:
        logger.error(f"Automation action error: {e}")
        return {'error': str(e)}

def create_gmail_summary_action():
    """Gmail要約を作成"""
    analysis = analyze_gmail()
    if analysis.get('available'):
        summary = f"📧 Gmail要約: {analysis['total_messages']}件のメールを分析しました。"
        if analysis['top_senders']:
            top = analysis['top_senders'][0]  # type: ignore[index]
            summary += f" 最も多い送信者: {top['sender']} ({top['count']}件)"

        send_notification('automation', '📧 Gmail要約', summary, analysis)
        return {'success': True, 'summary': summary}
    else:
        return {'success': False, 'error': 'Gmail data unavailable'}

def generate_weekly_report_action():
    """週次レポートを生成"""
    gmail_analysis = analyze_gmail()
    calendar_analysis = analyze_calendar()
    system_usage = analyze_system_usage()

    report = "📊 週次レポート\n\n"
    if gmail_analysis.get('available'):
        report += f"メール: {gmail_analysis['total_messages']}件\n"
    if calendar_analysis.get('available'):
        report += f"予定: {calendar_analysis['total_events']}件\n"
    if system_usage:
        metrics = system_usage['current_metrics']
        report += f"平均CPU: {metrics['cpu']}%, メモリ: {metrics['memory']}%\n"  # type: ignore

    send_notification('automation', '📊 週次レポート', report, {
        'gmail': gmail_analysis,
        'calendar': calendar_analysis,
        'system': system_usage
    })

    return {'success': True, 'report': report}

def send_system_alert_action():
    """システムアラートを送信"""
    metrics = get_system_metrics()
    alert = f"⚠️ システムアラート: CPU {metrics['cpu']}%, メモリ {metrics['memory']}%"
    send_notification('automation', '⚠️ システムアラート', alert, metrics)
    return {'success': True, 'alert': alert}

@app.route('/api/insights')
def get_insights():
    """ManaOS v3.0 Insightから分析データを取得"""
    try:
        # Insightから実行統計を取得
        response = requests.get('http://localhost:9205/api/insights', timeout=5)

        if response.status_code == 200:
            insight_data = response.json()
        else:
            insight_data = {'error': 'Insight service unavailable'}

        # Gmail分析
        gmail_analysis = analyze_gmail()

        # カレンダー分析
        calendar_analysis = analyze_calendar()

        # システム使用状況
        system_usage = analyze_system_usage()

        return jsonify({
            'timestamp': datetime.now().isoformat(),
            'manaos_insights': insight_data,
            'gmail_analysis': gmail_analysis,
            'calendar_analysis': calendar_analysis,
            'system_usage': system_usage
        })

    except Exception as e:
        logger.error(f"Insights error: {e}")
        return jsonify({
            'error': str(e)
        }), 500

def analyze_gmail():
    """Gmail分析：トピック抽出、送信者統計など"""
    try:
        response = requests.get('http://localhost:8097/api/gmail/messages?max_results=50', timeout=5)
        if response.status_code != 200:
            return {'available': False}

        data = response.json()
        if data.get('status') != 'success':
            return {'available': False}

        messages = data.get('messages', [])

        # 送信者統計
        senders = {}
        for msg in messages:
            sender = msg.get('from', 'Unknown')
            senders[sender] = senders.get(sender, 0) + 1

        # トップ5送信者
        top_senders = sorted(senders.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            'available': True,
            'total_messages': len(messages),
            'top_senders': [{'sender': s[0], 'count': s[1]} for s in top_senders],
            'analysis_time': datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Gmail analysis error: {e}")
        return {'available': False, 'error': str(e)}

def analyze_calendar():
    """カレンダー分析：予定数、時間帯分析など"""
    try:
        response = requests.get('http://localhost:8097/api/calendar/events?max_results=100', timeout=5)
        if response.status_code != 200:
            return {'available': False}

        data = response.json()
        if data.get('status') != 'success':
            return {'available': False}

        events = data.get('events', [])

        # 予定の種類を分類（簡易版）
        categories = {
            'meetings': 0,
            'personal': 0,
            'work': 0,
            'other': 0
        }

        for event in events:
            summary = event.get('summary', '').lower()
            if 'meeting' in summary or 'ミーティング' in summary or '会議' in summary:
                categories['meetings'] += 1
            elif 'personal' in summary or '個人' in summary:
                categories['personal'] += 1
            elif 'work' in summary or '仕事' in summary:
                categories['work'] += 1
            else:
                categories['other'] += 1

        return {
            'available': True,
            'total_events': len(events),
            'categories': categories,
            'analysis_time': datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Calendar analysis error: {e}")
        return {'available': False, 'error': str(e)}

def analyze_system_usage():
    """システム使用状況分析"""
    try:
        metrics = get_system_metrics()

        # プロセス情報
        process_count = len(psutil.pids())

        # ネットワーク統計
        net_io = psutil.net_io_counters()

        return {
            'current_metrics': metrics,
            'process_count': process_count,
            'network': {
                'bytes_sent': net_io.bytes_sent,
                'bytes_recv': net_io.bytes_recv
            },
            'analysis_time': datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"System usage analysis error: {e}")
        return {'error': str(e)}

@app.route('/api/system-integration/status')
@auth.login_required
def get_system_integration_status():
    """システム連携状態を取得"""
    try:
        if not SYSTEM_INTEGRATION_API_AVAILABLE:
            return jsonify({'error': 'System integration API not available'}), 503

        status = get_all_status()  # type: ignore[possibly-unbound]
        return jsonify(status)
    except Exception as e:
        logger.error(f"System integration status error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/system-integration/systems')
@auth.login_required
def get_system_integration_systems():
    """システム状態を取得"""
    try:
        if not SYSTEM_INTEGRATION_API_AVAILABLE:
            return jsonify({'error': 'System integration API not available'}), 503

        status = get_system_status()  # type: ignore[possibly-unbound]
        return jsonify(status)
    except Exception as e:
        logger.error(f"System status error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/system-integration/connections')
@auth.login_required
def get_system_integration_connections():
    """システム間連携状態を取得"""
    try:
        if not SYSTEM_INTEGRATION_API_AVAILABLE:
            return jsonify({'error': 'System integration API not available'}), 503

        status = get_integration_status()  # type: ignore[possibly-unbound]
        return jsonify(status)
    except Exception as e:
        logger.error(f"Integration status error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/system-integration/sync')
@auth.login_required
def get_system_integration_sync():
    """自動同期状態を取得"""
    try:
        if not SYSTEM_INTEGRATION_API_AVAILABLE:
            return jsonify({'error': 'System integration API not available'}), 503

        status = get_sync_status()  # type: ignore[possibly-unbound]
        return jsonify(status)
    except Exception as e:
        logger.error(f"Sync status error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/system-integration/metrics')
@auth.login_required
def get_system_integration_metrics():
    """メトリクスを取得"""
    try:
        if not SYSTEM_INTEGRATION_API_AVAILABLE:
            return jsonify({'error': 'System integration API not available'}), 503

        metrics = get_metrics()  # type: ignore[possibly-unbound]
        return jsonify(metrics)
    except Exception as e:
        logger.error(f"Metrics error: {e}")
        return jsonify({'error': str(e)}), 500

@socketio.on('connect')
def handle_connect():
    """WebSocket接続"""
    logger.info('Client connected to dashboard')
    emit('connected', {'message': 'ダッシュボード接続完了'})

@socketio.on('request_update')
def handle_update_request():
    """クライアントからの更新リクエスト"""
    status_data = get_status().get_json()
    emit('status_update', status_data)

def send_notification(notification_type, title, message, data=None):
    """全接続クライアントに通知を送信"""
    notification = {
        'type': notification_type,
        'title': title,
        'message': message,
        'data': data or {},
        'timestamp': datetime.now().isoformat()
    }
    socketio.emit('notification', notification)
    logger.info(f"通知送信: {notification_type} - {title}")

def check_gmail_notifications():
    """Gmail新着チェック"""
    try:
        summary = get_gmail_summary()
        current_count = summary['count']

        if current_count > notification_state['last_gmail_count']:
            new_count = current_count - notification_state['last_gmail_count']
            send_notification(
                'gmail',
                '📧 新着メール',
                f'{new_count}件の新しいメールが届きました',
                {'count': new_count, 'latest': summary['latest']}
            )

        notification_state['last_gmail_count'] = current_count
    except Exception as e:
        logger.error(f"Gmail通知チェックエラー: {e}")

def check_calendar_reminders():
    """カレンダーリマインダーチェック（15分前）"""
    try:
        summary = get_calendar_summary()
        now = datetime.now()

        for event in summary.get('today', []):
            event_id = event.get('id', '')
            if event_id in notification_state['calendar_reminders_sent']:
                continue

            start_str = event.get('start', {}).get('dateTime')
            if not start_str:
                continue

            # ISO形式の日時をパース
            try:
                event_time = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                # タイムゾーンを考慮しない簡易比較
                event_time = event_time.replace(tzinfo=None)
            except Exception:
                continue

            time_until = event_time - now

            # 15分前〜10分前の範囲で通知
            if timedelta(minutes=10) <= time_until <= timedelta(minutes=15):
                send_notification(
                    'calendar',
                    '📅 予定のリマインダー',
                    f'{event.get("summary", "予定")}が15分後に始まります',
                    {'event': event}
                )
                notification_state['calendar_reminders_sent'].add(event_id)
    except Exception as e:
        logger.error(f"カレンダー通知チェックエラー: {e}")

def check_system_alerts():
    """システムアラートチェック"""
    try:
        metrics = get_system_metrics()

        # CPU高負荷
        if metrics['cpu'] > 80:
            if notification_state['last_system_alert'] != 'cpu_high':
                send_notification(
                    'system',
                    '⚠️ CPU高負荷',
                    f'CPU使用率が{metrics["cpu"]}%に達しています',
                    {'cpu': metrics['cpu']}
                )
                notification_state['last_system_alert'] = 'cpu_high'

        # メモリ高負荷
        elif metrics['memory'] > 80:
            if notification_state['last_system_alert'] != 'memory_high':
                send_notification(
                    'system',
                    '⚠️ メモリ高負荷',
                    f'メモリ使用率が{metrics["memory"]}%に達しています',
                    {'memory': metrics['memory']}
                )
                notification_state['last_system_alert'] = 'memory_high'

        # ディスク高使用率
        elif metrics['disk'] > 90:
            if notification_state['last_system_alert'] != 'disk_high':
                send_notification(
                    'system',
                    '⚠️ ディスク容量不足',
                    f'ディスク使用率が{metrics["disk"]}%に達しています',
                    {'disk': metrics['disk']}
                )
                notification_state['last_system_alert'] = 'disk_high'
        else:
            # 正常に戻った
            if notification_state['last_system_alert']:
                notification_state['last_system_alert'] = None

    except Exception as e:
        logger.error(f"システムアラートチェックエラー: {e}")

def check_service_status():
    """サービスダウン検知"""
    try:
        for service_id, config in SERVICES.items():
            health = check_service_health(service_id, config)
            current_status = health['status']
            last_status = notification_state['last_service_status'].get(service_id)

            # オフライン検知
            if current_status == 'offline' and last_status != 'offline':
                send_notification(
                    'service_down',
                    '❌ サービス停止',
                    f'{config["name"]}が応答していません',
                    {'service': config['name'], 'port': config['port']}
                )

            # 復旧検知
            elif current_status == 'online' and last_status == 'offline':
                send_notification(
                    'service_up',
                    '✅ サービス復旧',
                    f'{config["name"]}が復旧しました',
                    {'service': config['name'], 'port': config['port']}
                )

            notification_state['last_service_status'][service_id] = current_status

    except Exception as e:
        logger.error(f"サービスステータスチェックエラー: {e}")

def notification_checker():
    """定期的に通知をチェックするバックグラウンドスレッド"""
    logger.info("🔔 通知チェッカー起動")

    while True:
        try:
            check_gmail_notifications()
            check_calendar_reminders()
            check_system_alerts()
            check_service_status()
            check_automation_rules()

            # 60秒ごとにチェック
            time.sleep(60)
        except Exception as e:
            logger.error(f"通知チェッカーエラー: {e}")
            time.sleep(60)

def check_automation_rules():
    """自動化ルールをチェックして実行"""
    now = datetime.now()

    for rule in automation_rules:
        if not rule['enabled']:
            continue

        try:
            # インターバルトリガー
            if rule['trigger'] == 'interval':
                last_run = rule.get('last_run')
                if last_run:
                    last_run_time = datetime.fromisoformat(last_run)
                    interval = timedelta(minutes=rule['interval_minutes'])
                    if now - last_run_time < interval:
                        continue

                # 実行
                logger.info(f"自動化ルール実行: {rule['name']}")
                result = execute_automation_action(rule)
                rule['last_run'] = now.isoformat()
                logger.info(f"自動化ルール完了: {rule['name']} - {result}")

            # イベントトリガー
            elif rule['trigger'] == 'event':
                # 条件チェック
                if evaluate_condition(rule['condition']):
                    # 重複実行を防ぐ
                    last_run = rule.get('last_run')
                    if last_run:
                        last_run_time = datetime.fromisoformat(last_run)
                        if now - last_run_time < timedelta(minutes=5):
                            continue

                    logger.info(f"自動化ルール実行: {rule['name']}")
                    result = execute_automation_action(rule)
                    rule['last_run'] = now.isoformat()
                    logger.info(f"自動化ルール完了: {rule['name']} - {result}")

        except Exception as e:
            logger.error(f"自動化ルール '{rule['name']}' 実行エラー: {e}")

def evaluate_condition(condition):
    """条件式を評価"""
    try:
        metrics = get_system_metrics()
        # 簡易的な条件評価
        condition = condition.replace('cpu', str(metrics['cpu']))
        condition = condition.replace('memory', str(metrics['memory']))
        condition = condition.replace('disk', str(metrics['disk']))
        return eval(condition)
    except Exception as e:
        logger.error(f"条件評価エラー: {e}")
        return False

if __name__ == '__main__':
    logger.info('🌸 ManaOS統合ダッシュボード起動中...')
    logger.info('アクセス: http://localhost:3000')

    # 通知チェッカーをバックグラウンドで起動
    checker_thread = threading.Thread(target=notification_checker, daemon=True)
    checker_thread.start()

    socketio.run(app, host='0.0.0.0', port=3000, debug=False, allow_unsafe_werkzeug=True)

