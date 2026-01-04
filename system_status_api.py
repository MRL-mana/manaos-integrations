#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📊 ManaOS 統合ステータスAPI
全11サービスのhealthを1画面/1JSONにまとめる
"""

import os
import json
import httpx
import psutil
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
from flask import Flask, jsonify
from flask_cors import CORS

# 統一モジュールのインポート
from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from manaos_timeout_config import get_timeout_config

# ロガーの初期化
logger = get_logger(__name__)

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("SystemStatus")

# タイムアウト設定の取得
timeout_config = get_timeout_config()

app = Flask(__name__)
CORS(app)

# サービス定義
SERVICES = [
    {"name": "Intent Router", "port": 5100, "script": "intent_router.py"},
    {"name": "Task Planner", "port": 5101, "script": "task_planner.py"},
    {"name": "Task Critic", "port": 5102, "script": "task_critic.py"},
    {"name": "RAG Memory", "port": 5103, "script": "rag_memory_enhanced.py"},
    {"name": "Task Queue", "port": 5104, "script": "task_queue_system.py"},
    {"name": "UI Operations", "port": 5105, "script": "ui_operations_api.py"},
    {"name": "Unified Orchestrator", "port": 5106, "script": "unified_orchestrator.py"},
    {"name": "Executor Enhanced", "port": 5107, "script": "task_executor_enhanced.py"},
    {"name": "Portal Integration", "port": 5108, "script": "portal_integration_api.py"},
    {"name": "Content Generation", "port": 5109, "script": "content_generation_loop.py"},
    {"name": "LLM Optimization", "port": 5110, "script": "llm_optimization.py"},
    {"name": "Service Monitor", "port": 5111, "script": "service_monitor.py"},
]

def check_service_health(port: int, timeout: Optional[float] = None) -> Dict[str, Any]:
    """サービスヘルスチェック"""
    if timeout is None:
        timeout = timeout_config.get("health_check", 5.0)
    try:
        response = httpx.get(
            f"http://localhost:{port}/health",
            timeout=timeout
        )
        if response.status_code == 200:
            data = response.json()
            return {
                "status": "healthy",
                "response_time_ms": response.elapsed.total_seconds() * 1000,
                "details": data
            }
        else:
            return {
                "status": "unhealthy",
                "response_time_ms": None,
                "error": f"HTTP {response.status_code}"
            }
    except httpx.ConnectError:
        return {
            "status": "down",
            "response_time_ms": None,
            "error": "Connection refused"
        }
    except httpx.TimeoutException:
        return {
            "status": "timeout",
            "response_time_ms": None,
            "error": "Request timeout"
        }
    except Exception as e:
        return {
            "status": "error",
            "response_time_ms": None,
            "error": str(e)
        }

def get_system_resources() -> Dict[str, Any]:
    """システムリソース情報を取得"""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "cpu": {
                "percent": cpu_percent,
                "count": psutil.cpu_count()
            },
            "memory": {
                "total_gb": round(memory.total / (1024**3), 2),
                "used_gb": round(memory.used / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "percent": memory.percent
            },
            "disk": {
                "total_gb": round(disk.total / (1024**3), 2),
                "used_gb": round(disk.used / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "percent": disk.percent
            }
        }
    except Exception as e:
        logger.error(f"システムリソース取得エラー: {e}")
        return {}

def get_service_process_info(script_name: str) -> Optional[Dict[str, Any]]:
    """サービスプロセス情報を取得"""
    try:
        import subprocess
        import platform
        
        if platform.system() == "Windows":
            # Windows: tasklistでプロセス検索
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq python.exe", "/FO", "CSV"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            # 簡易実装（実際にはWMIを使用する方が確実）
            # ここではプロセスが存在するかだけ確認
            if script_name in result.stdout:
                return {
                    "running": True,
                    "note": "Process found (detailed info requires WMI)"
                }
        else:
            # Linux: psコマンド
            result = subprocess.run(
                ["ps", "aux"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if script_name in result.stdout:
                return {
                    "running": True,
                    "note": "Process found"
                }
        
        return {"running": False}
    except Exception as e:
        logger.debug(f"プロセス情報取得エラー: {e}")
        return None

@app.route('/health', methods=['GET'])
def health():
    """ヘルスチェック"""
    return jsonify({"status": "healthy", "service": "System Status API"})

@app.route('/api/status', methods=['GET'])
def get_status():
    """統合ステータス取得"""
    timestamp = datetime.now().isoformat()
    
    # 各サービスのヘルスチェック
    service_statuses = []
    healthy_count = 0
    unhealthy_count = 0
    down_count = 0
    
    for service in SERVICES:
        health_info = check_service_health(service["port"])
        process_info = get_service_process_info(service["script"])
        
        service_status = {
            "name": service["name"],
            "port": service["port"],
            "health": health_info,
            "process": process_info
        }
        
        service_statuses.append(service_status)
        
        if health_info["status"] == "healthy":
            healthy_count += 1
        elif health_info["status"] in ["unhealthy", "timeout", "error"]:
            unhealthy_count += 1
        else:
            down_count += 1
    
    # システムリソース
    system_resources = get_system_resources()
    
    # 全体ステータス
    total_services = len(SERVICES)
    overall_status = "healthy" if healthy_count == total_services else "degraded" if healthy_count > 0 else "down"
    
    return jsonify({
        "timestamp": timestamp,
        "overall_status": overall_status,
        "summary": {
            "total_services": total_services,
            "healthy": healthy_count,
            "unhealthy": unhealthy_count,
            "down": down_count
        },
        "services": service_statuses,
        "system_resources": system_resources
    })

@app.route('/api/status/simple', methods=['GET'])
def get_status_simple():
    """簡易ステータス（スマホ向け）"""
    service_statuses = []
    healthy_count = 0
    
    for service in SERVICES:
        health_info = check_service_health(service["port"], timeout=1.0)
        is_healthy = health_info["status"] == "healthy"
        
        if is_healthy:
            healthy_count += 1
        
        service_statuses.append({
            "name": service["name"],
            "port": service["port"],
            "status": "✅" if is_healthy else "❌"
        })
    
    total_services = len(SERVICES)
    status_emoji = "🟢" if healthy_count == total_services else "🟡" if healthy_count > 0 else "🔴"
    
    return jsonify({
        "status": status_emoji,
        "services": f"{healthy_count}/{total_services}",
        "details": service_statuses
    })

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5112))
    logger.info(f"📊 System Status API起動中... (ポート: {port})")
    app.run(host='0.0.0.0', port=port, debug=os.getenv("DEBUG", "False").lower() == "true")

