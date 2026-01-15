#!/usr/bin/env python3
"""
🎮 Portal Integration API - Unified Portal v2統合用API
UI操作機能をUnified Portal v2に統合
"""

import os
import json
import httpx
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
from flask import Flask, jsonify, request
from flask_cors import CORS

# 統一モジュールのインポート
from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from manaos_timeout_config import get_timeout_config
from manaos_config_validator import ConfigValidator

# ロガーの初期化
logger = get_logger(__name__)

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("PortalIntegration")

# タイムアウト設定の取得
timeout_config = get_timeout_config()

app = Flask(__name__)
CORS(app)

# サービスURL
SERVICES = {
    "unified_orchestrator": "http://localhost:5106",
    "ui_operations": "http://localhost:5105",
    "task_queue": "http://localhost:5104"
}

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
        device_health_monitor = DeviceHealthMonitor()
        device_orchestrator = DeviceOrchestrator()
        logger.info("✅ 統合デバイス管理システム初期化完了")
    except Exception as e:
        logger.warning(f"⚠️ 統合デバイス管理システム初期化エラー: {e}")


@app.route('/health', methods=['GET'])
def health():
    """ヘルスチェック"""
    return jsonify({"status": "healthy", "service": "Portal Integration API"})


@app.route('/api/execute', methods=['POST'])
def execute_task():
    """タスク実行エンドポイント（Unified Orchestrator経由）"""
    data = request.get_json() or {}
    input_text = data.get("text", "")
    mode = data.get("mode")
    
    if not input_text:
        return jsonify({"error": "text is required"}), 400
    
    try:
        timeout = timeout_config.get("workflow_execution", 300.0)
        response = httpx.post(
            f"{SERVICES['unified_orchestrator']}/api/execute",
            json={
                "text": input_text,
                "mode": mode,
                "auto_evaluate": True,
                "save_to_memory": True
            },
            timeout=timeout
        )
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            error = error_handler.handle_exception(
                Exception(f"Unified Orchestrator接続失敗: HTTP {response.status_code}"),
                context={"service": "Unified Orchestrator", "url": SERVICES['unified_orchestrator']},
                user_message="タスクの実行に失敗しました"
            )
            return jsonify(error.to_json_response()), response.status_code
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/execute"},
            user_message="タスク実行エンドポイントでエラーが発生しました"
        )
        return jsonify(error.to_json_response()), 500


@app.route('/api/mode', methods=['GET'])
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
            context={"service": "UI Operations", "url": SERVICES['ui_operations']},
            user_message="モード取得に失敗しました"
        )
        logger.warning(f"モード取得エラー: {error.message}")
        return jsonify({"mode": "auto"}), 200


@app.route('/api/mode', methods=['POST'])
def set_mode():
    """モード設定エンドポイント"""
    data = request.get_json() or {}
    mode = data.get("mode")
    
    if not mode:
        return jsonify({"error": "mode is required"}), 400
    
    try:
        timeout = timeout_config.get("api_call", 10.0)
        response = httpx.post(
            f"{SERVICES['ui_operations']}/api/mode",
            json={"mode": mode},
            timeout=timeout
        )
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            error = error_handler.handle_exception(
                Exception(f"UI Operations接続失敗: HTTP {response.status_code}"),
                context={"service": "UI Operations", "url": SERVICES['ui_operations']},
                user_message="モード設定に失敗しました"
            )
            return jsonify(error.to_json_response()), response.status_code
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/mode", "mode": mode},
            user_message="モード設定エンドポイントでエラーが発生しました"
        )
        return jsonify(error.to_json_response()), 500


@app.route('/api/cost', methods=['GET'])
def get_cost():
    """コスト取得エンドポイント"""
    days = request.args.get("days", 1, type=int)
    
    try:
        response = httpx.get(
            f"{SERVICES['ui_operations']}/api/cost?days={days}",
            timeout=5
        )
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({"error": response.text}), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/queue/status', methods=['GET'])
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


@app.route('/api/history', methods=['GET'])
def get_execution_history():
    """実行履歴取得エンドポイント"""
    limit = request.args.get("limit", 10, type=int)
    
    try:
        response = httpx.get(
            f"{SERVICES['unified_orchestrator']}/api/history?limit={limit}",
            timeout=5
        )
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({"error": response.text}), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/execution/<execution_id>', methods=['GET'])
def get_execution(execution_id: str):
    """実行結果取得エンドポイント"""
    try:
        response = httpx.get(
            f"{SERVICES['unified_orchestrator']}/api/execution/{execution_id}",
            timeout=5
        )
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({"error": response.text}), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/devices/status', methods=['GET'])
def get_devices_status():
    """統合デバイス管理ダッシュボード: 全デバイスの状態を取得"""
    if not DEVICE_MANAGEMENT_AVAILABLE or not device_health_monitor:
        return jsonify({
            "error": "統合デバイス管理システムが利用できません",
            "available": False
        }), 503
    
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
            devices_dict.append({
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
                "api_endpoint": device.api_endpoint
            })
        
        return jsonify({
            "timestamp": datetime.now().isoformat(),
            "devices": devices_dict,
            "orchestrator": orchestrator_status,
            "summary": {
                "total_devices": len(devices_dict),
                "healthy_devices": sum(1 for d in devices_dict if d.get("status") == "healthy"),
                "warning_devices": sum(1 for d in devices_dict if d.get("status") == "warning"),
                "critical_devices": sum(1 for d in devices_dict if d.get("status") == "critical"),
                "offline_devices": sum(1 for d in devices_dict if d.get("status") == "offline")
            }
        })
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/devices/status"},
            user_message="デバイス状態の取得に失敗しました"
        )
        return jsonify(error.to_json_response()), 500


@app.route('/api/devices/<device_name>/health', methods=['GET'])
def get_device_health(device_name: str):
    """統合デバイス管理ダッシュボード: 特定デバイスの健康状態を取得"""
    if not DEVICE_MANAGEMENT_AVAILABLE or not device_health_monitor:
        return jsonify({
            "error": "統合デバイス管理システムが利用できません",
            "available": False
        }), 503
    
    try:
        # 全デバイスをチェックして該当デバイスを探す
        devices_health = device_health_monitor.check_all_devices()
        for device in devices_health:
            if device.device_name.lower() == device_name.lower():
                return jsonify({
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
                    "api_endpoint": device.api_endpoint
                })
        
        return jsonify({"error": f"デバイス '{device_name}' が見つかりません"}), 404
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": f"/api/devices/{device_name}/health", "device_name": device_name},
            user_message=f"デバイス '{device_name}' の健康状態取得に失敗しました"
        )
        return jsonify(error.to_json_response()), 500


@app.route('/api/devices/resources', methods=['GET'])
def get_devices_resources():
    """統合デバイス管理ダッシュボード: 全デバイスのリソース使用状況を取得"""
    if not DEVICE_MANAGEMENT_AVAILABLE or not device_health_monitor:
        return jsonify({
            "error": "統合デバイス管理システムが利用できません",
            "available": False
        }), 503
    
    try:
        devices_health = device_health_monitor.check_all_devices()
        
        resources = []
        for device in devices_health:
            resources.append({
                "device_name": device.device_name,
                "device_type": device.device_type,
                "cpu_percent": device.cpu_percent,
                "memory_percent": device.memory_percent,
                "disk_percent": device.disk_percent,
                "network_sent_mb": device.network_sent_mb,
                "network_recv_mb": device.network_recv_mb,
                "uptime_seconds": device.uptime_seconds,
                "status": device.status,
                "timestamp": device.timestamp
            })
        
        return jsonify({
            "timestamp": datetime.now().isoformat(),
            "resources": resources,
            "summary": {
                "total_devices": len(resources),
                "average_cpu": sum(r["cpu_percent"] for r in resources) / len(resources) if resources else 0.0,
                "average_memory": sum(r["memory_percent"] for r in resources) / len(resources) if resources else 0.0,
                "average_disk": sum(r["disk_percent"] for r in resources) / len(resources) if resources else 0.0
            }
        })
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/devices/resources"},
            user_message="デバイスリソース情報の取得に失敗しました"
        )
        return jsonify(error.to_json_response()), 500


@app.route('/api/devices/alerts', methods=['GET'])
def get_devices_alerts():
    """統合デバイス管理ダッシュボード: 全デバイスのアラートを取得"""
    if not DEVICE_MANAGEMENT_AVAILABLE or not device_health_monitor:
        return jsonify({
            "error": "統合デバイス管理システムが利用できません",
            "available": False
        }), 503
    
    try:
        devices_health = device_health_monitor.check_all_devices()
        
        alerts = []
        for device in devices_health:
            device_alerts = device.alerts
            for alert in device_alerts:
                alerts.append({
                    "device_name": device.device_name,
                    "device_type": device.device_type,
                    "alert": alert,
                    "status": device.status,
                    "timestamp": device.timestamp
                })
        
        # アラートを優先度順にソート（critical > warning > healthy）
        priority_order = {"critical": 0, "warning": 1, "healthy": 2, "offline": 3}
        alerts.sort(key=lambda x: priority_order.get(x["status"], 99))
        
        return jsonify({
            "timestamp": datetime.now().isoformat(),
            "alerts": alerts,
            "summary": {
                "total_alerts": len(alerts),
                "critical_alerts": sum(1 for a in alerts if a["status"] == "critical"),
                "warning_alerts": sum(1 for a in alerts if a["status"] == "warning")
            }
        })
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/devices/alerts"},
            user_message="デバイスアラート情報の取得に失敗しました"
        )
        return jsonify(error.to_json_response()), 500


if __name__ == '__main__':
    port = int(os.getenv("PORT", 5108))
    logger.info(f"🎮 Portal Integration API起動中... (ポート: {port})")
    app.run(host='0.0.0.0', port=port, debug=os.getenv("DEBUG", "False").lower() == "true")

