#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📊 ManaOS SSOT (Single Source of Truth) Generator
19サービスの統一ステータスJSONを生成・更新
"""

import os
import json
import logging
import httpx
import psutil
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path
from threading import Lock
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# SSOTファイルパス
SSOT_FILE = Path(__file__).parent / "manaos_status.json"
SSOT_LOCK = Lock()

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
    {"name": "System Status API", "port": 5112, "script": "system_status_api.py"},
    {"name": "Crash Snapshot", "port": 5113, "script": "crash_snapshot.py"},
    {"name": "Slack Integration", "port": 5114, "script": "slack_integration.py"},
    {"name": "Web Voice Interface", "port": 5115, "script": "web_voice_interface.py"},
    {"name": "Portal Voice Integration", "port": 5116, "script": "portal_voice_integration.py"},
    {"name": "Revenue Tracker", "port": 5117, "script": "revenue_tracker.py"},
    {"name": "Product Automation", "port": 5118, "script": "product_automation.py"},
    {"name": "Payment Integration", "port": 5119, "script": "payment_integration.py"},
]

class SSOTGenerator:
    """SSOT生成器"""
    
    def __init__(self):
        self.recent_inputs = []  # 最新指令5件
        self.last_error = None  # 直近エラー
        self.update_interval = 5  # 更新間隔（秒）
        
    def check_service_health(self, port: int, timeout: float = 2.0) -> Dict[str, Any]:
        """サービスヘルスチェック"""
        try:
            response = httpx.get(
                f"http://127.0.0.1:{port}/health",
                timeout=timeout
            )
            if response.status_code == 200:
                return {
                    "status": "up",
                    "response_time_ms": round(response.elapsed.total_seconds() * 1000, 2),
                    "last_heartbeat": datetime.now().isoformat()
                }
            else:
                return {
                    "status": "unhealthy",
                    "response_time_ms": None,
                    "last_heartbeat": None
                }
        except httpx.ConnectError:
            return {
                "status": "down",
                "response_time_ms": None,
                "last_heartbeat": None
            }
        except httpx.TimeoutException:
            return {
                "status": "timeout",
                "response_time_ms": None,
                "last_heartbeat": None
            }
        except Exception as e:
            return {
                "status": "error",
                "response_time_ms": None,
                "last_heartbeat": None,
                "error": str(e)
            }
    
    def get_service_process_info(self, script_name: str) -> Optional[Dict[str, Any]]:
        """サービスプロセス情報を取得"""
        try:
            pid = None
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'memory_info', 'cpu_percent']):
                try:
                    if proc.info['cmdline'] and script_name in ' '.join(proc.info['cmdline']):
                        pid = proc.info['pid']
                        return {
                            "pid": pid,
                            "memory_mb": round(proc.info['memory_info'].rss / (1024**2), 2),
                            "cpu_percent": proc.info['cpu_percent'] or 0.0
                        }
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return None
        except Exception as e:
            logger.debug(f"プロセス情報取得エラー: {e}")
            return None
    
    def get_system_resources(self) -> Dict[str, Any]:
        """システムリソース情報を取得"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # GPU情報（可能な場合）
            gpu_info = None
            try:
                import GPUtil
                gpus = GPUtil.getGPUs()
                if gpus:
                    gpu = gpus[0]
                    gpu_info = {
                        "utilization": gpu.load * 100,
                        "memory_used_mb": gpu.memoryUsed,
                        "memory_total_mb": gpu.memoryTotal,
                        "temperature": gpu.temperature
                    }
            except Exception:
                pass
            
            return {
                "cpu": {
                    "percent": cpu_percent,
                    "count": psutil.cpu_count()
                },
                "ram": {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "used_gb": round(memory.used / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "percent": memory.percent
                },
                "gpu": gpu_info,
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
    
    def get_active_tasks(self) -> Dict[str, Any]:
        """実行中/待機中タスクを取得"""
        try:
            # Task Queueから取得
            response = httpx.get(
                "http://127.0.0.1:5104/api/status",
                timeout=2
            )
            if response.status_code == 200:
                data = response.json()
                return {
                    "pending": data.get("pending_tasks", 0),
                    "running": data.get("status_counts", {}).get("running", 0),
                    "total": data.get("total_tasks", 0)
                }
        except Exception:
            pass
        
        return {
            "pending": 0,
            "running": 0,
            "total": 0
        }
    
    def get_recent_inputs(self) -> List[Dict[str, Any]]:
        """最新指令5件を取得"""
        # Unified Orchestratorから実行履歴を取得
        try:
            response = httpx.get(
                "http://127.0.0.1:5106/api/history?limit=5",
                timeout=2
            )
            if response.status_code == 200:
                data = response.json()
                inputs = []
                for result in data.get("results", [])[:5]:
                    inputs.append({
                        "text": result.get("input_text", ""),
                        "intent_type": result.get("intent_type", ""),
                        "status": result.get("status", ""),
                        "timestamp": result.get("created_at", "")
                    })
                return inputs
        except Exception:
            pass
        
        return self.recent_inputs[-5:] if self.recent_inputs else []
    
    def get_last_error(self) -> Optional[Dict[str, Any]]:
        """直近エラーを取得"""
        # Crash Snapshotから最新エラーを取得
        try:
            response = httpx.get(
                "http://127.0.0.1:5113/api/snapshots?limit=1",
                timeout=2
            )
            if response.status_code == 200:
                data = response.json()
                snapshots = data.get("snapshots", [])
                if snapshots:
                    snapshot = snapshots[0]
                    return {
                        "service_name": snapshot.get("service_name", ""),
                        "error_message": snapshot.get("error_message", ""),
                        "timestamp": snapshot.get("timestamp", "")
                    }
        except Exception:
            pass
        
        return self.last_error
    
    def generate_ssot(self) -> Dict[str, Any]:
        """SSOTを生成"""
        timestamp = datetime.now().isoformat()
        
        # サービス状態
        services_status = []
        for service in SERVICES:
            health = self.check_service_health(service["port"])
            process_info = self.get_service_process_info(service["script"])
            
            service_status = {
                "name": service["name"],
                "port": service["port"],
                "status": health["status"],
                "pid": process_info["pid"] if process_info else None,
                "response_time_ms": health.get("response_time_ms"),
                "last_heartbeat": health.get("last_heartbeat"),
                "memory_mb": process_info.get("memory_mb") if process_info else None,
                "cpu_percent": process_info.get("cpu_percent") if process_info else None
            }
            services_status.append(service_status)
        
        # システムリソース
        system_resources = self.get_system_resources()
        
        # 実行中/待機中タスク
        active_tasks = self.get_active_tasks()
        
        # 最新指令5件
        recent_inputs = self.get_recent_inputs()
        
        # 直近エラー
        last_error = self.get_last_error()
        
        # SSOT構築
        ssot = {
            "timestamp": timestamp,
            "version": "1.0",
            "services": services_status,
            "system": system_resources,
            "active_tasks": active_tasks,
            "recent_inputs": recent_inputs,
            "last_error": last_error,
            "summary": {
                "total_services": len(SERVICES),
                "up": len([s for s in services_status if s["status"] == "up"]),
                "down": len([s for s in services_status if s["status"] == "down"]),
                "unhealthy": len([s for s in services_status if s["status"] in ["unhealthy", "timeout", "error"]])
            }
        }
        
        return ssot
    
    def save_ssot(self, ssot: Dict[str, Any]):
        """SSOTをファイルに保存"""
        with SSOT_LOCK:
            try:
                with open(SSOT_FILE, 'w', encoding='utf-8') as f:
                    json.dump(ssot, f, indent=2, ensure_ascii=False)
                logger.debug(f"SSOT保存完了: {SSOT_FILE}")
            except Exception as e:
                logger.error(f"SSOT保存エラー: {e}")
    
    def update_loop(self):
        """更新ループ"""
        logger.info(f"📊 SSOT Generator起動中... (更新間隔: {self.update_interval}秒)")
        
        while True:
            try:
                ssot = self.generate_ssot()
                self.save_ssot(ssot)
                logger.debug(f"SSOT更新完了: {ssot['summary']}")
            except Exception as e:
                logger.error(f"SSOT生成エラー: {e}")
            
            time.sleep(self.update_interval)

def main():
    """メイン関数"""
    generator = SSOTGenerator()
    
    # 初回生成
    ssot = generator.generate_ssot()
    generator.save_ssot(ssot)
    logger.info(f"✅ SSOT初回生成完了: {SSOT_FILE}")
    logger.info(f"   サービス状態: {ssot['summary']['up']}/{ssot['summary']['total_services']} up")
    
    # 更新ループ開始
    generator.update_loop()

if __name__ == '__main__':
    main()

