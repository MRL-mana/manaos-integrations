#!/usr/bin/env python3
"""
🎮 Portal Integration API - Unified Portal v2統合用API
UI操作機能をUnified Portal v2に統合
"""

import os
import json
import time
import threading
import httpx
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from flask import Flask, jsonify, request, Response
from flask_cors import CORS

# 統一モジュールのインポート
from manaos_logger import get_logger, get_service_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from manaos_timeout_config import get_timeout_config
from manaos_config_validator import ConfigValidator

from _paths import AUTONOMY_SYSTEM_PORT, MRL_MEMORY_PORT, ORCHESTRATOR_PORT, TASK_QUEUE_PORT

# ロガーの初期化
logger = get_service_logger("portal-integration-api")

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("PortalIntegration")

# タイムアウト設定の取得
timeout_config = get_timeout_config()

app = Flask(__name__)
CORS(app)

# サービスURL
DEFAULT_ORCHESTRATOR_URL = f"http://127.0.0.1:{ORCHESTRATOR_PORT}"
DEFAULT_UI_OPERATIONS_URL = f"http://127.0.0.1:{MRL_MEMORY_PORT}"
DEFAULT_TASK_QUEUE_URL = f"http://127.0.0.1:{TASK_QUEUE_PORT}"
DEFAULT_AUTONOMY_SYSTEM_URL = f"http://127.0.0.1:{AUTONOMY_SYSTEM_PORT}"

SERVICES = {
    "unified_orchestrator": os.getenv("ORCHESTRATOR_URL", DEFAULT_ORCHESTRATOR_URL).rstrip("/"),
    "ui_operations": os.getenv("UI_OPERATIONS_URL", DEFAULT_UI_OPERATIONS_URL).rstrip("/"),
    "task_queue": os.getenv("TASK_QUEUE_URL", DEFAULT_TASK_QUEUE_URL).rstrip("/"),
}
AUTONOMY_SYSTEM_URL = os.getenv("AUTONOMY_SYSTEM_URL", DEFAULT_AUTONOMY_SYSTEM_URL).rstrip("/")

# 外部クライアント用: Portal → 5106 のタイムアウト（短めで切る。LLM待ちでUX死ぬの防止）
ORCHESTRATOR_CLIENT_TIMEOUT = float(os.getenv("PORTAL_ORCHESTRATOR_TIMEOUT", "12"))

# 多重発火防止: 同一リクエストの重複排除キャッシュ（TTL 秒）
IDEMPOTENCY_TTL_SEC = 10
_idempotency_cache: Dict[str, Tuple[float, Any]] = {}
_idempotency_lock = threading.Lock()

# 同時二発抑止: 同じキーで実行中なら後続は「待って同じ結果」を受け取る
# (event, result_holder, exception_holder) result_holder[0] = (status_code, body)
_inflight: Dict[str, Tuple[threading.Event, List[Any], List[Optional[Exception]]]] = {}
_inflight_lock = threading.Lock()


def _idempotency_key(data: Dict[str, Any], query_or_text: str) -> str:
    """idempotency_key があればそれ、なければ query/text のハッシュ"""
    key = data.get("idempotency_key")
    if key:
        return str(key)
    return str(hash(query_or_text) % (10**10))


def _get_cached_response(key: str) -> Optional[Any]:
    """重複排除キャッシュから取得。期限切れなら None"""
    with _idempotency_lock:
        if key not in _idempotency_cache:
            return None
        expiry, payload = _idempotency_cache[key]
        if time.time() > expiry:
            del _idempotency_cache[key]
            return None
        return payload


def _generate_portal_trace_id() -> str:
    """Portal 側のリクエスト識別子（上流追跡用）。ログ突合・デバッグ用。"""
    return (
        f"portal_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{int(time.time() * 1000) % 100000:05d}"
    )


def _store_cached_response(key: str, payload: Any) -> None:
    """成功レスポンスをキャッシュに保存"""
    with _idempotency_lock:
        _idempotency_cache[key] = (time.time() + IDEMPOTENCY_TTL_SEC, payload)
        # 古いエントリを適当に削除（キー数が多くなりすぎないように）
        to_del = [k for k, (exp, _) in _idempotency_cache.items() if exp < time.time()]
        for k in to_del:
            del _idempotency_cache[k]


def _get_orchestrator_response(
    key: str,
    json_payload: Dict[str, Any],
    portal_trace_id: Optional[str] = None,
) -> Tuple[int, Any]:
    """
    キャッシュ → inflight 待ち → 5106 呼び出し の順で実行。
    戻り値: (status_code, body)。例外時は raise。
    同時二発は同一キーで待ち、同じ結果に収束する。
    portal_trace_id を渡すと 5106 への転送ヘッダ X-Portal-Trace-Id に載せ、5106 側ログとの相関が楽になる。
    """
    cached = _get_cached_response(key)
    if cached is not None:
        return 200, cached

    with _inflight_lock:
        if key in _inflight:
            ev, rh, eh = _inflight[key]
            is_first = False
        else:
            ev = threading.Event()
            rh: List[Any] = [None]
            eh: List[Optional[Exception]] = [None]
            _inflight[key] = (ev, rh, eh)
            is_first = True

    headers = {}
    if portal_trace_id:
        headers["X-Portal-Trace-Id"] = portal_trace_id

    def do_call() -> None:
        try:
            response = httpx.post(
                f"{SERVICES['unified_orchestrator']}/api/execute",
                json=json_payload,
                headers=headers or None,
                timeout=ORCHESTRATOR_CLIENT_TIMEOUT,
            )
            if response.status_code == 200:
                body = response.json()
                _store_cached_response(key, body)
                rh[0] = (200, body)
            else:
                try:
                    err_body = response.json()
                except Exception:
                    err_body = {"error": response.text or f"HTTP {response.status_code}"}
                rh[0] = (response.status_code, err_body)
        except Exception as e:
            eh[0] = e
        finally:
            # 必ず実行（後続のデッドロック防止）。どんな落ち方でも event.set と inflight 削除
            ev.set()
            with _inflight_lock:
                _inflight.pop(key, None)

    if is_first:
        do_call()
    else:
        ev.wait()
    if eh[0] is not None:
        raise eh[0]
    return rh[0]


# 本格運用: メトリクス＋抑制付きアラート（オプション）
try:
    from orchestrator_operational_metrics import (
        record_and_maybe_alert,
        get_stats as get_orchestrator_stats,
    )

    ORCHESTRATOR_METRICS_AVAILABLE = True
except ImportError:
    ORCHESTRATOR_METRICS_AVAILABLE = False
    record_and_maybe_alert = None
    get_orchestrator_stats = None

# 統合デバイス管理システム（オプション）
try:
    from device_health_monitor import DeviceHealthMonitor
    from device_orchestrator import DeviceOrchestrator

    DEVICE_MANAGEMENT_AVAILABLE = True
except ImportError:
    DEVICE_MANAGEMENT_AVAILABLE = False
    DeviceHealthMonitor = None
    DeviceOrchestrator = None

# デバイス管理システムの初期化
device_health_monitor = None
device_orchestrator = None
if DEVICE_MANAGEMENT_AVAILABLE:
    try:
        device_health_monitor = DeviceHealthMonitor()  # type: ignore[operator]
        device_orchestrator = DeviceOrchestrator()  # type: ignore[operator]
        logger.info("✅ 統合デバイス管理システム初期化完了")
    except Exception as e:
        logger.warning(f"⚠️ 統合デバイス管理システム初期化エラー: {e}")


@app.route("/health", methods=["GET"])
def health():
    """ヘルスチェック"""
    return jsonify({"status": "healthy", "service": "Portal Integration API"})


@app.route("/api/execute", methods=["POST"])
def execute_task():
    """タスク実行エンドポイント（Unified Orchestrator経由）"""
    data = request.get_json() or {}
    # ask_orchestrator 互換: text または query で自然文を受け付ける
    input_text = data.get("text") or data.get("query") or ""
    mode = data.get("mode")

    if not input_text:
        return jsonify({"error": "text or query is required"}), 400

    portal_trace_id = _generate_portal_trace_id()
    key = _idempotency_key(data, input_text)
    payload = {"text": input_text, "mode": mode, "auto_evaluate": True, "save_to_memory": True}
    try:
        status_code, body = _get_orchestrator_response(key, payload, portal_trace_id)
        if isinstance(body, dict):
            body.setdefault("meta", {})["portal_trace_id"] = portal_trace_id
        if (
            ORCHESTRATOR_METRICS_AVAILABLE
            and record_and_maybe_alert
            and status_code == 200
            and isinstance(body, dict)
        ):
            record_and_maybe_alert(body, is_portal_timeout=False)
        return jsonify(body), status_code
    except httpx.TimeoutError:  # type: ignore[attr-defined]
        if ORCHESTRATOR_METRICS_AVAILABLE and record_and_maybe_alert:
            record_and_maybe_alert({}, is_portal_timeout=True)
        error = error_handler.handle_exception(
            Exception("Unified Orchestrator タイムアウト"),
            context={"endpoint": "/api/execute"},
            user_message="オーケストレーターへの接続がタイムアウトしました",
        )
        return jsonify(error.to_json_response()), 504
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/execute"},
            user_message="タスク実行エンドポイントでエラーが発生しました",
        )
        return jsonify(error.to_json_response()), 500


@app.route("/api/ask_orchestrator", methods=["POST"])
def ask_orchestrator():
    """AI向け汎用オーケストレーター（1ツールで自然文を投げる窓口）"""
    data = request.get_json() or {}
    query = data.get("query", "")
    if not query:
        return jsonify({"error": "query is required"}), 400

    portal_trace_id = _generate_portal_trace_id()
    key = _idempotency_key(data, query)
    payload = {"query": query, "auto_evaluate": True, "save_to_memory": True}
    try:
        status_code, body = _get_orchestrator_response(key, payload, portal_trace_id)
        if isinstance(body, dict):
            body.setdefault("meta", {})["portal_trace_id"] = portal_trace_id
        if (
            ORCHESTRATOR_METRICS_AVAILABLE
            and record_and_maybe_alert
            and status_code == 200
            and isinstance(body, dict)
        ):
            record_and_maybe_alert(body, is_portal_timeout=False)
        return jsonify(body), status_code
    except httpx.TimeoutError:  # type: ignore[attr-defined]
        if ORCHESTRATOR_METRICS_AVAILABLE and record_and_maybe_alert:
            record_and_maybe_alert({}, is_portal_timeout=True)
        error = error_handler.handle_exception(
            Exception("Unified Orchestrator タイムアウト"),
            context={"endpoint": "/api/ask_orchestrator"},
            user_message="オーケストレーターへの接続がタイムアウトしました",
        )
        return jsonify(error.to_json_response()), 504
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/ask_orchestrator"},
            user_message="ask_orchestrator でエラーが発生しました",
        )
        return jsonify(error.to_json_response()), 500


@app.route("/api/orchestrator/stats", methods=["GET"])
def get_orchestrator_stats_endpoint():
    """本格運用: ask_orchestrator の集計（status 別・error_code 別・Portal タイムアウト）。ダッシュボード用。"""
    if not ORCHESTRATOR_METRICS_AVAILABLE or not get_orchestrator_stats:
        return jsonify({"error": "orchestrator_operational_metrics が利用できません"}), 503
    try:
        return jsonify(get_orchestrator_stats())
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/orchestrator/stats"},
            user_message="集計の取得に失敗しました",
        )
        return jsonify(error.to_json_response()), 500


@app.route("/api/mode", methods=["GET"])
def get_mode():
    """モード取得エンドポイント"""
    try:
        timeout = timeout_config.get("api_call", 10.0)
        response = httpx.get(f"{SERVICES['ui_operations']}/api/mode", timeout=timeout)
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({"mode": "auto"}), 200
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"service": "UI Operations", "url": SERVICES["ui_operations"]},
            user_message="モード取得に失敗しました",
        )
        logger.warning(f"モード取得エラー: {error.message}")
        return jsonify({"mode": "auto"}), 200


@app.route("/api/mode", methods=["POST"])
def set_mode():
    """モード設定エンドポイント"""
    data = request.get_json() or {}
    mode = data.get("mode")

    if not mode:
        return jsonify({"error": "mode is required"}), 400

    try:
        timeout = timeout_config.get("api_call", 10.0)
        response = httpx.post(
            f"{SERVICES['ui_operations']}/api/mode", json={"mode": mode}, timeout=timeout
        )

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            error = error_handler.handle_exception(
                Exception(f"UI Operations接続失敗: HTTP {response.status_code}"),
                context={"service": "UI Operations", "url": SERVICES["ui_operations"]},
                user_message="モード設定に失敗しました",
            )
            return jsonify(error.to_json_response()), response.status_code
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/mode", "mode": mode},
            user_message="モード設定エンドポイントでエラーが発生しました",
        )
        return jsonify(error.to_json_response()), 500


@app.route("/api/cost", methods=["GET"])
def get_cost():
    """コスト取得エンドポイント"""
    days = request.args.get("days", 1, type=int)

    try:
        response = httpx.get(f"{SERVICES['ui_operations']}/api/cost?days={days}", timeout=5)

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({"error": response.text}), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/queue/status", methods=["GET"])
def get_queue_status():
    """キュー状態取得エンドポイント"""
    try:
        response = httpx.get(f"{SERVICES['task_queue']}/api/status", timeout=5)
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({"error": response.text}), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/history", methods=["GET"])
def get_execution_history():
    """実行履歴取得エンドポイント"""
    limit = request.args.get("limit", 10, type=int)

    try:
        response = httpx.get(
            f"{SERVICES['unified_orchestrator']}/api/history?limit={limit}", timeout=5
        )

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({"error": response.text}), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/execution/<execution_id>", methods=["GET"])
def get_execution(execution_id: str):
    """実行結果取得エンドポイント"""
    try:
        response = httpx.get(
            f"{SERVICES['unified_orchestrator']}/api/execution/{execution_id}", timeout=5
        )

        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({"error": response.text}), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/devices/status", methods=["GET"])
def get_devices_status():
    """統合デバイス管理ダッシュボード: 全デバイスの状態を取得"""
    if not DEVICE_MANAGEMENT_AVAILABLE or not device_health_monitor:
        return (
            jsonify({"error": "統合デバイス管理システムが利用できません", "available": False}),
            503,
        )

    try:
        # 全デバイスの健康状態を取得
        devices_health = device_health_monitor.check_all_devices()

        # デバイスオーケストレーターの状態を取得
        orchestrator_status = {}
        if device_orchestrator:
            try:
                orchestrator_status = device_orchestrator.get_status()
            except Exception as e:
                logger.warning(f"デバイスオーケストレーター状態取得エラー: {e}")

        # DeviceHealthオブジェクトを辞書に変換
        devices_dict = []
        for device in devices_health:
            devices_dict.append(
                {
                    "device_name": device.device_name,
                    "device_type": device.device_type,
                    "status": device.status,
                    "timestamp": device.timestamp,
                    "cpu_percent": device.cpu_percent,
                    "memory_percent": device.memory_percent,
                    "disk_percent": device.disk_percent,
                    "network_sent_mb": device.network_sent_mb,
                    "network_recv_mb": device.network_recv_mb,
                    "uptime_seconds": device.uptime_seconds,
                    "alerts": device.alerts,
                    "api_endpoint": device.api_endpoint,
                }
            )

        return jsonify(
            {
                "timestamp": datetime.now().isoformat(),
                "devices": devices_dict,
                "orchestrator": orchestrator_status,
                "summary": {
                    "total_devices": len(devices_dict),
                    "healthy_devices": sum(1 for d in devices_dict if d.get("status") == "healthy"),
                    "warning_devices": sum(1 for d in devices_dict if d.get("status") == "warning"),
                    "critical_devices": sum(
                        1 for d in devices_dict if d.get("status") == "critical"
                    ),
                    "offline_devices": sum(1 for d in devices_dict if d.get("status") == "offline"),
                },
            }
        )
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/devices/status"},
            user_message="デバイス状態の取得に失敗しました",
        )
        return jsonify(error.to_json_response()), 500


@app.route("/api/devices/<device_name>/health", methods=["GET"])
def get_device_health(device_name: str):
    """統合デバイス管理ダッシュボード: 特定デバイスの健康状態を取得"""
    if not DEVICE_MANAGEMENT_AVAILABLE or not device_health_monitor:
        return (
            jsonify({"error": "統合デバイス管理システムが利用できません", "available": False}),
            503,
        )

    try:
        # 全デバイスをチェックして該当デバイスを探す
        devices_health = device_health_monitor.check_all_devices()
        for device in devices_health:
            if device.device_name.lower() == device_name.lower():
                return jsonify(
                    {
                        "device_name": device.device_name,
                        "device_type": device.device_type,
                        "status": device.status,
                        "timestamp": device.timestamp,
                        "cpu_percent": device.cpu_percent,
                        "memory_percent": device.memory_percent,
                        "disk_percent": device.disk_percent,
                        "network_sent_mb": device.network_sent_mb,
                        "network_recv_mb": device.network_recv_mb,
                        "uptime_seconds": device.uptime_seconds,
                        "alerts": device.alerts,
                        "api_endpoint": device.api_endpoint,
                    }
                )

        return jsonify({"error": f"デバイス '{device_name}' が見つかりません"}), 404
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": f"/api/devices/{device_name}/health", "device_name": device_name},
            user_message=f"デバイス '{device_name}' の健康状態取得に失敗しました",
        )
        return jsonify(error.to_json_response()), 500


@app.route("/api/devices/resources", methods=["GET"])
def get_devices_resources():
    """統合デバイス管理ダッシュボード: 全デバイスのリソース使用状況を取得"""
    if not DEVICE_MANAGEMENT_AVAILABLE or not device_health_monitor:
        return (
            jsonify({"error": "統合デバイス管理システムが利用できません", "available": False}),
            503,
        )

    try:
        devices_health = device_health_monitor.check_all_devices()

        resources = []
        for device in devices_health:
            resources.append(
                {
                    "device_name": device.device_name,
                    "device_type": device.device_type,
                    "cpu_percent": device.cpu_percent,
                    "memory_percent": device.memory_percent,
                    "disk_percent": device.disk_percent,
                    "network_sent_mb": device.network_sent_mb,
                    "network_recv_mb": device.network_recv_mb,
                    "uptime_seconds": device.uptime_seconds,
                    "status": device.status,
                    "timestamp": device.timestamp,
                }
            )

        return jsonify(
            {
                "timestamp": datetime.now().isoformat(),
                "resources": resources,
                "summary": {
                    "total_devices": len(resources),
                    "average_cpu": (
                        sum(r["cpu_percent"] for r in resources) / len(resources)
                        if resources
                        else 0.0
                    ),
                    "average_memory": (
                        sum(r["memory_percent"] for r in resources) / len(resources)
                        if resources
                        else 0.0
                    ),
                    "average_disk": (
                        sum(r["disk_percent"] for r in resources) / len(resources)
                        if resources
                        else 0.0
                    ),
                },
            }
        )
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/devices/resources"},
            user_message="デバイスリソース情報の取得に失敗しました",
        )
        return jsonify(error.to_json_response()), 500


@app.route("/api/devices/alerts", methods=["GET"])
def get_devices_alerts():
    """統合デバイス管理ダッシュボード: 全デバイスのアラートを取得"""
    if not DEVICE_MANAGEMENT_AVAILABLE or not device_health_monitor:
        return (
            jsonify({"error": "統合デバイス管理システムが利用できません", "available": False}),
            503,
        )

    try:
        devices_health = device_health_monitor.check_all_devices()

        alerts = []
        for device in devices_health:
            device_alerts = device.alerts
            for alert in device_alerts:
                alerts.append(
                    {
                        "device_name": device.device_name,
                        "device_type": device.device_type,
                        "alert": alert,
                        "status": device.status,
                        "timestamp": device.timestamp,
                    }
                )

        # アラートを優先度順にソート（critical > warning > healthy）
        priority_order = {"critical": 0, "warning": 1, "healthy": 2, "offline": 3}
        alerts.sort(key=lambda x: priority_order.get(x["status"], 99))

        return jsonify(
            {
                "timestamp": datetime.now().isoformat(),
                "alerts": alerts,
                "summary": {
                    "total_alerts": len(alerts),
                    "critical_alerts": sum(1 for a in alerts if a["status"] == "critical"),
                    "warning_alerts": sum(1 for a in alerts if a["status"] == "warning"),
                },
            }
        )
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/devices/alerts"},
            user_message="デバイスアラート情報の取得に失敗しました",
        )
        return jsonify(error.to_json_response()), 500


# ---------------------------------------------------------------------------
# 自律システム（Autonomy）プロキシ・ダッシュボードUI
# ---------------------------------------------------------------------------


@app.route("/api/autonomy/dashboard", methods=["GET"])
def proxy_autonomy_dashboard():
    """Autonomy System の GET /api/dashboard をプロキシ（Portal 同一オリジンで取得）"""
    try:
        r = httpx.get(f"{AUTONOMY_SYSTEM_URL}/api/dashboard", timeout=10.0)
        r.raise_for_status()
        return jsonify(r.json())
    except Exception as e:
        logger.warning(f"Autonomy dashboard プロキシエラー: {e}")
        return (
            jsonify(
                {
                    "error": str(e),
                    "autonomy_level": 0,
                    "budget_usage": {},
                    "runbook_last_runs": {},
                    "audit_tail": [],
                }
            ),
            503,
        )


@app.route("/api/autonomy/approvals", methods=["POST"])
def proxy_autonomy_approvals():
    """Autonomy System の POST /api/approvals をプロキシ（1回限り承認トークン発行）"""
    try:
        body = request.get_json() or {}
        r = httpx.post(f"{AUTONOMY_SYSTEM_URL}/api/approvals", json=body, timeout=10.0)
        r.raise_for_status()
        return jsonify(r.json())
    except Exception as e:
        logger.warning(f"Autonomy approvals プロキシエラー: {e}")
        return jsonify({"error": str(e)}), 503


@app.route("/api/autonomy/level", methods=["GET"])
def proxy_autonomy_level_get():
    """Autonomy System の GET /api/level をプロキシ"""
    try:
        r = httpx.get(f"{AUTONOMY_SYSTEM_URL}/api/level", timeout=10.0)
        r.raise_for_status()
        return jsonify(r.json())
    except Exception as e:
        logger.warning(f"Autonomy level GET プロキシエラー: {e}")
        return jsonify({"error": str(e)}), 503


@app.route("/api/autonomy/level", methods=["POST"])
def proxy_autonomy_level_post():
    """Autonomy System の POST /api/level をプロキシ（レベル変更）"""
    try:
        body = request.get_json() or {}
        r = httpx.post(f"{AUTONOMY_SYSTEM_URL}/api/level", json=body, timeout=10.0)
        r.raise_for_status()
        return jsonify(r.json())
    except Exception as e:
        logger.warning(f"Autonomy level POST プロキシエラー: {e}")
        return jsonify({"error": str(e)}), 503


@app.route("/autonomy-dashboard", methods=["GET"])
def autonomy_dashboard_ui():
    """自律レベル・予算・承認ボタンを表示するダッシュボードHTML"""
    html = _AUTONOMY_DASHBOARD_HTML.replace("{{AUTONOMY_API}}", request.url_root.rstrip("/"))
    return Response(html, mimetype="text/html; charset=utf-8")


_AUTONOMY_DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>自律システム ダッシュボード</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', sans-serif; background: #1a1a2e; color: #eee; padding: 20px; }
        .container { max-width: 800px; margin: 0 auto; }
        h1 { margin-bottom: 16px; color: #a0a0ff; }
        .card { background: #16213e; border-radius: 10px; padding: 16px; margin-bottom: 16px; }
        .card h2 { font-size: 1rem; color: #88a; margin-bottom: 8px; }
        .level { font-size: 1.5rem; font-weight: bold; color: #7cff7c; }
        .budget table { width: 100%; border-collapse: collapse; }
        .budget th, .budget td { text-align: left; padding: 6px 8px; border-bottom: 1px solid #333; }
        .approval { margin-top: 12px; }
        .approval input { padding: 8px; width: 200px; margin-right: 8px; background: #333; border: 1px solid #555; color: #eee; border-radius: 4px; }
        .approval button { padding: 8px 16px; background: #4a7c59; color: #fff; border: none; border-radius: 4px; cursor: pointer; }
        .approval button:hover { background: #5a9c69; }
        .token-result { margin-top: 8px; padding: 8px; background: #0f0f1a; border-radius: 4px; font-family: monospace; font-size: 0.9rem; word-break: break-all; }
        .error { color: #ff8888; }
        .refresh { margin-bottom: 16px; }
        .refresh button { padding: 8px 16px; background: #3a5a7a; color: #fff; border: none; border-radius: 4px; cursor: pointer; }
    </style>
</head>
<body>
    <div class="container">
        <h1>自律システム ダッシュボード</h1>
        <div class="refresh"><button onclick="load()">更新</button></div>
        <div class="card">
            <h2>自律レベル</h2>
            <div class="level" id="level">-</div>
            <div id="levelName" style="color:#88a;"></div>
            <div class="level-change" style="margin-top:12px;">
                <label>レベル変更: </label>
                <select id="levelSelect" style="padding:6px; background:#333; color:#eee; border:1px solid #555; border-radius:4px;">
                    <option value="0">L0 OFF</option>
                    <option value="1">L1 Observe</option>
                    <option value="2">L2 Notify</option>
                    <option value="3">L3 Assist</option>
                    <option value="4">L4 Act</option>
                    <option value="5">L5 Autopilot</option>
                    <option value="6">L6 Ops</option>
                </select>
                <input type="text" id="levelConfirmToken" placeholder="L5/L6時は confirm_token（任意）" style="padding:6px; width:180px; margin-left:8px; background:#333; border:1px solid #555; color:#eee; border-radius:4px;" />
                <button onclick="setLevel()" style="padding:6px 12px; margin-left:8px; background:#5a7c9a; color:#fff; border:none; border-radius:4px; cursor:pointer;">反映</button>
                <span id="levelResult" style="margin-left:8px; font-size:0.9rem;"></span>
            </div>
        </div>
        <div class="card budget">
            <h2>予算使用量</h2>
            <table>
                <thead><tr><th>種別</th><th>1時間</th><th>1日</th></tr></thead>
                <tbody id="budgetBody"></tbody>
            </table>
        </div>
        <div class="card approval">
            <h2>1回限り承認トークン発行</h2>
            <p style="color:#88a; font-size:0.9rem;">C3/C4 ツールを1回だけ実行可能にするトークンを発行します。有効期限は発行から最大60分。</p>
            <input type="text" id="toolName" placeholder="ツール名（任意）例: llm_chat" />
            <input type="number" id="expiresIn" value="300" min="60" max="3600" placeholder="有効秒" style="width:100px;" />
            <button onclick="issueToken()">発行</button>
            <div id="tokenResult" class="token-result" style="display:none;"></div>
        </div>
        <div class="card">
            <h2>監査ログ（直近）</h2>
            <pre id="auditTail" style="font-size:0.8rem; max-height:200px; overflow:auto;"></pre>
        </div>
    </div>
    <script>
        const API = "{{AUTONOMY_API}}";
        async function load() {
            try {
                const r = await fetch(API + "/api/autonomy/dashboard");
                const d = await r.json();
                document.getElementById("level").textContent = "L" + (d.autonomy_level ?? 0);
                document.getElementById("levelName").textContent = d.autonomy_level_name || "";
                const sel = document.getElementById("levelSelect");
                if (sel) sel.value = String(d.autonomy_level ?? 0);
                const perHour = d.budget_usage?.per_hour || {};
                const perDay = d.budget_usage?.per_day || {};
                const tbody = document.getElementById("budgetBody");
                tbody.innerHTML = "";
                ["llm_calls","image_jobs","video_jobs"].forEach(k => {
                    const tr = document.createElement("tr");
                    tr.innerHTML = "<td>" + k + "</td><td>" + (perHour[k] ?? 0) + "</td><td>" + (perDay[k] ?? 0) + "</td>";
                    tbody.appendChild(tr);
                });
                const audit = (d.audit_tail || []).slice(-10).map(e => e.ts + " " + (e.tool || e.result) + " " + (e.result || "")).join("\\n");
                document.getElementById("auditTail").textContent = audit || "(なし)";
            } catch (e) {
                document.getElementById("level").textContent = "?";
                document.getElementById("level").className = "level error";
                document.getElementById("auditTail").textContent = "取得エラー: " + e.message;
            }
        }
        async function setLevel() {
            const level = parseInt(document.getElementById("levelSelect").value, 10);
            const confirmToken = document.getElementById("levelConfirmToken").value.trim() || undefined;
            const resultEl = document.getElementById("levelResult");
            try {
                const body = { level };
                if (confirmToken) body.confirm_token = confirmToken;
                const r = await fetch(API + "/api/autonomy/level", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
                const d = await r.json();
                if (d.error) { resultEl.textContent = "エラー: " + d.error; resultEl.className = "error"; return; }
                resultEl.textContent = "OK: " + (d.autonomy_level_name || "L" + d.autonomy_level);
                resultEl.className = "";
                load();
            } catch (e) { resultEl.textContent = "エラー: " + e.message; resultEl.className = "error"; }
        }
        async function issueToken() {
            const toolName = document.getElementById("toolName").value.trim() || null;
            const expiresIn = parseInt(document.getElementById("expiresIn").value, 10) || 300;
            const resultEl = document.getElementById("tokenResult");
            resultEl.style.display = "block";
            try {
                const r = await fetch(API + "/api/autonomy/approvals", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ tool_name: toolName || undefined, expires_in_seconds: expiresIn })
                });
                const d = await r.json();
                if (d.error) { resultEl.textContent = "エラー: " + d.error; resultEl.classList.add("error"); return; }
                resultEl.textContent = "発行しました。このトークンを C3/C4 実行時に confirm_token として渡してください。\\nconfirm_token: " + (d.confirm_token || "");
                resultEl.classList.remove("error");
            } catch (e) {
                resultEl.textContent = "エラー: " + e.message;
                resultEl.classList.add("error");
            }
        }
        load();
    </script>
</body>
</html>
"""


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5108))
    logger.info(f"🎮 Portal Integration API起動中... (ポート: {port})")
    app.run(host="0.0.0.0", port=port, debug=os.getenv("DEBUG", "False").lower() == "true")
