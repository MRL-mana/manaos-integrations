#!/usr/bin/env python3
"""
システム連携状態API
ダッシュボード用のシステム連携情報を提供
"""

import sys
import json
import socket
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

sys.path.insert(0, '/root/scripts')
sys.path.insert(0, '/root/manaos_learning')

def check_port(port: int) -> bool:
    """ポートが開いているか確認"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        return result == 0
    except Exception:
        return False

def check_process(process_name: str) -> bool:
    """プロセスが実行中か確認"""
    try:
        result = subprocess.run(
            ['pgrep', '-f', process_name],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except Exception:
        return False

def check_file(filepath: str) -> bool:
    """ファイルが存在するか確認"""
    return Path(filepath).exists()

def get_system_status() -> Dict[str, Any]:
    """全システムの状態を取得"""
    systems = {
        "learning": {
            "name": "学習系",
            "file": "/root/scripts/learning_api.py",
            "process": "learning_api.py",
            "port": None,
            "dashboard_port": 5085
        },
        "memory": {
            "name": "記憶系",
            "file": "/root/manaos_learning/memory_integration.py",
            "process": "weaviate",
            "port": 8080,
            "dashboard_port": None
        },
        "autonomous": {
            "name": "自律系",
            "file": "/root/manaos_learning/autonomous_integration.py",
            "process": "autonomous_integration.py",
            "port": None,
            "dashboard_port": None
        },
        "personality": {
            "name": "人格系",
            "file": "/root/manaos_learning/personality_integration.py",
            "process": "personality_evolution_tracker.py",
            "port": None,
            "dashboard_port": None
        },
        "backup": {
            "name": "バックアップ系",
            "file": "/root/manaos_learning/backup_integration.py",
            "process": "backup_integration.py",
            "port": None,
            "dashboard_port": None
        },
        "secretary": {
            "name": "秘書系",
            "file": "/root/trinity_automation/trinity_enhanced_secretary.py",
            "process": "trinity_enhanced_secretary.py",
            "port": 5013,
            "dashboard_port": None
        }
    }

    result = {
        "timestamp": datetime.now().isoformat(),
        "systems": {},
        "summary": {
            "total": 0,
            "healthy": 0,
            "unhealthy": 0
        }
    }

    for system_id, system_info in systems.items():
        status = {
            "id": system_id,
            "name": system_info["name"],
            "healthy": False,
            "checks": {}
        }

        # ファイルチェック
        file_ok = check_file(system_info["file"])
        status["checks"]["file"] = file_ok

        # プロセスチェック
        process_ok = check_process(system_info["process"])
        status["checks"]["process"] = process_ok

        # ポートチェック
        if system_info["port"]:
            port_ok = check_port(system_info["port"])
            status["checks"]["port"] = port_ok
        else:
            port_ok = True

        # ダッシュボードポートチェック
        if system_info["dashboard_port"]:
            dashboard_ok = check_port(system_info["dashboard_port"])
            status["checks"]["dashboard"] = dashboard_ok
        else:
            dashboard_ok = True

        # 健康状態判定
        if file_ok and process_ok and port_ok and dashboard_ok:
            status["healthy"] = True
            result["summary"]["healthy"] += 1
        else:
            result["summary"]["unhealthy"] += 1

        result["systems"][system_id] = status
        result["summary"]["total"] += 1

    return result

def get_integration_status() -> Dict[str, Any]:
    """システム間連携の状態を取得"""
    connections = {
        "learning_to_autonomous": {
            "from": "学習系",
            "to": "自律系",
            "bridge": "/root/manaos_learning/autonomous_integration.py",
            "status": "ok" if check_file("/root/manaos_learning/autonomous_integration.py") else "missing"
        },
        "learning_to_personality": {
            "from": "学習系",
            "to": "人格系",
            "bridge": "/root/manaos_learning/personality_integration.py",
            "status": "ok" if check_file("/root/manaos_learning/personality_integration.py") else "missing"
        },
        "learning_to_memory": {
            "from": "学習系",
            "to": "記憶系",
            "bridge": "/root/manaos_learning/memory_integration.py",
            "status": "ok" if check_file("/root/manaos_learning/memory_integration.py") else "missing"
        },
        "learning_to_backup": {
            "from": "学習系",
            "to": "バックアップ系",
            "bridge": "/root/manaos_learning/backup_integration.py",
            "status": "ok" if check_file("/root/manaos_learning/backup_integration.py") else "missing"
        },
        "learning_to_secretary": {
            "from": "学習系",
            "to": "秘書系",
            "bridge": "/root/trinity_automation/trinity_secretary_learning_integration.py",
            "status": "ok" if check_file("/root/trinity_automation/trinity_secretary_learning_integration.py") else "missing"
        },
        "bidirectional": {
            "from": "全システム",
            "to": "学習系",
            "bridge": "/root/manaos_learning/bidirectional_integration.py",
            "status": "ok" if check_file("/root/manaos_learning/bidirectional_integration.py") else "missing"
        }
    }

    result = {
        "timestamp": datetime.now().isoformat(),
        "connections": connections,
        "summary": {
            "total": len(connections),
            "ok": sum(1 for c in connections.values() if c["status"] == "ok"),
            "missing": sum(1 for c in connections.values() if c["status"] == "missing")
        }
    }

    return result

def get_sync_status() -> Dict[str, Any]:
    """自動同期の状態を取得"""
    services = {
        "sync_scheduler": {
            "name": "自動同期スケジューラー",
            "service": "system-sync-scheduler.service",
            "log": "/root/logs/system_sync.log"
        },
        "integration_monitor": {
            "name": "連携監視サービス",
            "service": "system-integration-monitor.service",
            "log": "/root/logs/integration_monitor.log"
        }
    }

    result = {
        "timestamp": datetime.now().isoformat(),
        "services": {},
        "summary": {
            "total": 0,
            "running": 0,
            "stopped": 0
        }
    }

    for service_id, service_info in services.items():
        status = {
            "id": service_id,
            "name": service_info["name"],
            "running": False,
            "log_exists": check_file(service_info["log"])
        }

        # systemdサービス状態確認
        try:
            result_cmd = subprocess.run(
                ['systemctl', 'is-active', service_info["service"]],
                capture_output=True,
                text=True,
                timeout=2
            )
            status["running"] = result_cmd.returncode == 0
        except Exception:
            status["running"] = False

        if status["running"]:
            result["summary"]["running"] += 1
        else:
            result["summary"]["stopped"] += 1

        result["services"][service_id] = status
        result["summary"]["total"] += 1

    return result

def get_metrics() -> Dict[str, Any]:
    """メトリクスを取得"""
    metrics = {
        "timestamp": datetime.now().isoformat(),
        "sync": {
            "total_syncs": 0,
            "successful_syncs": 0,
            "failed_syncs": 0,
            "last_sync": None
        },
        "monitor": {
            "total_checks": 0,
            "alerts_triggered": 0,
            "last_check": None
        }
    }

    # 同期ログから統計を取得
    sync_log = Path("/root/logs/system_sync.log")
    if sync_log.exists():
        try:
            with open(sync_log, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                metrics["sync"]["total_syncs"] = len(lines)
                successful = sum(1 for line in lines if '"status": "success"' in line)
                metrics["sync"]["successful_syncs"] = successful
                metrics["sync"]["failed_syncs"] = len(lines) - successful
                if lines:
                    last_line = json.loads(lines[-1])
                    metrics["sync"]["last_sync"] = last_line.get("timestamp")
        except Exception:
            pass

    # 監視ログから統計を取得
    monitor_log = Path("/root/logs/integration_monitor.log")
    if monitor_log.exists():
        try:
            with open(monitor_log, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                metrics["monitor"]["total_checks"] = len(lines)
                alerts = sum(1 for line in lines if '"status": "unhealthy"' in line)
                metrics["monitor"]["alerts_triggered"] = alerts
                if lines:
                    last_line = json.loads(lines[-1])
                    metrics["monitor"]["last_check"] = last_line.get("timestamp")
        except Exception:
            pass

    return metrics

def get_all_status() -> Dict[str, Any]:
    """全状態を取得"""
    return {
        "timestamp": datetime.now().isoformat(),
        "systems": get_system_status(),
        "integrations": get_integration_status(),
        "sync": get_sync_status(),
        "metrics": get_metrics()
    }








