#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 ManaOS サービス監視システム
サービス停止の自動検知・再起動・メトリクス収集
"""

import os
import json
from manaos_logger import get_logger
import httpx
import time
import subprocess
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
from dataclasses import dataclass, asdict
import threading

logger = get_service_logger("service-monitor")


@dataclass
class ServiceStatus:
    """サービス状態"""
    name: str
    port: int
    status: str  # "running", "stopped", "error"
    last_check: str
    restart_count: int
    error_message: Optional[str] = None


class ServiceMonitor:
    """サービス監視システム"""
    
    def __init__(
        self,
        config_path: Optional[Path] = None,
        check_interval: int = 30,
        max_restarts: int = 5
    ):
        """
        初期化
        
        Args:
            config_path: 設定ファイルのパス
            check_interval: チェック間隔（秒）
            max_restarts: 最大再起動回数
        """
        self.config_path = config_path or Path(__file__).parent / "service_monitor_config.json"
        self.config = self._load_config()
        self.check_interval = check_interval
        self.max_restarts = max_restarts
        
        self.services: Dict[str, ServiceStatus] = {}
        self.monitoring = False
        self.monitor_thread = None
        
        self._init_services()
        logger.info(f"✅ サービス監視システム初期化完了")
    
    def _load_config(self) -> Dict[str, Any]:
        """設定を読み込む"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"設定読み込みエラー: {e}")
        
        return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """デフォルト設定"""
        return {
            "services": [
                {"name": "Intent Router", "port": 5100, "script": "intent_router.py"},
                {"name": "Task Planner", "port": 5101, "script": "task_planner.py"},
                {"name": "Task Critic", "port": 5102, "script": "task_critic.py"},
                {"name": "RAG記憶進化", "port": 5103, "script": "rag_memory_enhanced.py"},
                {"name": "汎用タスクキュー", "port": 5104, "script": "task_queue_system.py"},
                {"name": "MRL Memory", "port": 5105, "script": "mrl_memory_integration"},
                {"name": "統合オーケストレーター", "port": 5106, "script": "unified_orchestrator.py"},
                {"name": "Executor拡張", "port": 5107, "script": "task_executor_enhanced.py"},
                {"name": "Portal統合", "port": 5108, "script": "portal_integration_api.py"},
                {"name": "成果物自動生成", "port": 5109, "script": "content_generation_loop.py"},
                {"name": "LLM Routing MCP", "port": 5111, "script": "llm_routing_mcp_server"},
                {"name": "Video Pipeline", "port": 5112, "script": "video_pipeline_mcp_server"},
                {"name": "Learning System", "port": 5126, "script": "learning_system_api"},
                {"name": "Unified API", "port": 9502, "script": "unified_api_server.py"}
            ],
            "check_interval": 30,
            "max_restarts": 5,
            "restart_delay": 5
        }
    
    def _init_services(self):
        """サービスを初期化"""
        for svc_config in self.config.get("services", []):
            name = svc_config.get("name")
            port = svc_config.get("port")
            
            self.services[name] = ServiceStatus(
                name=name,
                port=port,
                status="unknown",
                last_check=datetime.now().isoformat(),
                restart_count=0
            )
    
    def start_monitoring(self):
        """監視を開始"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("✅ サービス監視開始")
    
    def stop_monitoring(self):
        """監視を停止"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("🛑 サービス監視停止")
    
    def _monitor_loop(self):
        """監視ループ"""
        while self.monitoring:
            try:
                self._check_all_services()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"監視ループエラー: {e}")
                time.sleep(self.check_interval)
    
    def _check_all_services(self):
        """全サービスをチェック"""
        for svc_config in self.config.get("services", []):
            name = svc_config.get("name")
            port = svc_config.get("port")
            script = svc_config.get("script")
            
            status = self._check_service(port)
            service_status = self.services.get(name)
            
            if service_status:
                service_status.last_check = datetime.now().isoformat()
                
                if status == "running":
                    if service_status.status != "running":
                        logger.info(f"✅ {name} が起動しました")
                    service_status.status = "running"
                    service_status.error_message = None
                else:
                    if service_status.status == "running":
                        logger.warning(f"⚠️  {name} が停止しました")
                    service_status.status = "stopped"
                    
                    # 再起動を試みる
                    if service_status.restart_count < self.max_restarts:
                        self._restart_service(name, script)
                        service_status.restart_count += 1
                    else:
                        logger.error(f"❌ {name} が最大再起動回数に達しました")
                        service_status.status = "error"
                        service_status.error_message = "Max restarts exceeded"
    
    def _check_service(self, port: int) -> str:
        """サービスをチェック"""
        try:
            response = httpx.get(
                f"http://127.0.0.1:{port}/health",
                timeout=5
            )
            if response.status_code == 200:
                return "running"
        except httpx.ConnectError:
            return "stopped"
        except Exception as e:
            logger.debug(f"サービスチェックエラー (ポート{port}): {e}")
            return "stopped"
        
        return "stopped"
    
    def _restart_service(self, name: str, script: str):
        """サービスを再起動"""
        script_path = Path(__file__).parent / script
        
        if not script_path.exists():
            logger.error(f"スクリプトが見つかりません: {script}")
            return
        
        logger.info(f"🔄 {name} を再起動中...")
        
        try:
            # 既存プロセスを停止
            self._stop_service_process(script)
            
            # 少し待機
            time.sleep(self.config.get("restart_delay", 5))
            
            # 新しいプロセスを起動
            subprocess.Popen(
                ["python", str(script_path)],
                cwd=str(script_path.parent),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            logger.info(f"✅ {name} 再起動完了")
        except Exception as e:
            logger.error(f"❌ {name} 再起動失敗: {e}")
    
    def _stop_service_process(self, script: str):
        """サービスプロセスを停止"""
        import platform
        
        if platform.system() == "Windows":
            # Windows: tasklistでプロセスを検索して停止
            try:
                result = subprocess.run(
                    ["tasklist", "/FI", f"IMAGENAME eq python.exe", "/FO", "CSV"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                # スクリプト名を含むプロセスを停止
                # 簡易実装（実際にはWMIを使用する方が確実）
                pass
            except Exception as e:
                logger.debug(f"プロセス停止エラー: {e}")
    
    def get_status_report(self) -> Dict[str, Any]:
        """ステータスレポートを取得"""
        running_count = sum(1 for s in self.services.values() if s.status == "running")
        stopped_count = sum(1 for s in self.services.values() if s.status == "stopped")
        error_count = sum(1 for s in self.services.values() if s.status == "error")
        
        return {
            "timestamp": datetime.now().isoformat(),
            "total_services": len(self.services),
            "running": running_count,
            "stopped": stopped_count,
            "error": error_count,
            "services": {name: asdict(status) for name, status in self.services.items()}
        }


# Flask APIサーバー
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

monitor = None

def init_monitor():
    """モニターを初期化"""
    global monitor
    if monitor is None:
        monitor = ServiceMonitor()
        monitor.start_monitoring()
    return monitor

@app.route('/health', methods=['GET'])
def health():
    """ヘルスチェック"""
    return jsonify({"status": "healthy", "service": "Service Monitor"})

@app.route('/api/status', methods=['GET'])
def get_status():
    """ステータス取得"""
    monitor = init_monitor()
    report = monitor.get_status_report()
    return jsonify(report)

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5111))
    logger.info(f"🔍 サービス監視システム起動中... (ポート: {port})")
    init_monitor()
    app.run(host='0.0.0.0', port=port, debug=os.getenv("DEBUG", "False").lower() == "true")

