#!/usr/bin/env python3
"""
Mana Unified Dashboard
全システムを統合管理する究極のダッシュボード
"""

import os
import json
import asyncio
import logging
import psutil
import requests
from datetime import datetime
from typing import Dict, List, Any
from pathlib import Path

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ManaUnifiedDashboard:
    def __init__(self):
        self.app = FastAPI(title="Mana Unified Dashboard", version="1.0.0")
        
        # システムエンドポイント設定
        self.services = {
            "manaos_orchestrator": {"url": "http://localhost:9200", "name": "ManaOS Orchestrator"},
            "manaos_intention": {"url": "http://localhost:9201", "name": "ManaOS Intention"},
            "manaos_policy": {"url": "http://localhost:9202", "name": "ManaOS Policy"},
            "manaos_actuator": {"url": "http://localhost:9203", "name": "ManaOS Actuator"},
            "manaos_ingestor": {"url": "http://localhost:9204", "name": "ManaOS Ingestor"},
            "manaos_insight": {"url": "http://localhost:9205", "name": "ManaOS Insight"},
            "screen_sharing": {"url": "http://localhost:5008/api/status", "name": "Screen Sharing"},
            "trinity_secretary": {"url": "http://localhost:8889/api/status", "name": "Trinity Secretary"},
        }
        
        # WebSocket接続管理
        self.active_connections: List[WebSocket] = []
        
        self.setup_middleware()
        self.setup_routes()
        
        logger.info("🎨 Mana Unified Dashboard 初期化完了")
    
    def setup_middleware(self):
        """CORS設定"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    async def get_system_metrics(self) -> Dict[str, Any]:
        """システムメトリクス取得"""
        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            # メモリ
            memory = psutil.virtual_memory()
            
            # ディスク
            disk = psutil.disk_usage('/')
            
            # ネットワーク
            net_io = psutil.net_io_counters()
            
            # プロセス数
            process_count = len(psutil.pids())
            
            return {
                "cpu": {
                    "percent": round(cpu_percent, 1),
                    "count": cpu_count
                },
                "memory": {
                    "total": memory.total,
                    "used": memory.used,
                    "free": memory.available,
                    "percent": round(memory.percent, 1)
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": round(disk.percent, 1)
                },
                "network": {
                    "bytes_sent": net_io.bytes_sent,
                    "bytes_recv": net_io.bytes_recv,
                    "packets_sent": net_io.packets_sent,
                    "packets_recv": net_io.packets_recv
                },
                "processes": process_count,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"メトリクス取得エラー: {e}")
            return {}
    
    async def check_service_health(self, service_id: str, config: Dict[str, str]) -> Dict[str, Any]:
        """サービスヘルスチェック"""
        try:
            response = requests.get(config["url"], timeout=2)
            return {
                "id": service_id,
                "name": config["name"],
                "status": "online" if response.status_code == 200 else "degraded",
                "response_time": response.elapsed.total_seconds() * 1000,
                "status_code": response.status_code
            }
        except requests.exceptions.Timeout:
            return {
                "id": service_id,
                "name": config["name"],
                "status": "timeout",
                "response_time": None
            }
        except Exception as e:
            return {
                "id": service_id,
                "name": config["name"],
                "status": "offline",
                "error": str(e)
            }
    
    async def get_all_services_health(self) -> List[Dict[str, Any]]:
        """全サービスのヘルスチェック"""
        tasks = [
            self.check_service_health(service_id, config)
            for service_id, config in self.services.items()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 例外処理
        health_status = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"ヘルスチェックエラー: {result}")
            else:
                health_status.append(result)
        
        return health_status
    
    async def get_security_status(self) -> Dict[str, Any]:
        """セキュリティ状態取得"""
        try:
            # 最新の監査レポートを読み込み
            report_dir = Path("/root/security_audit_reports")
            if report_dir.exists():
                reports = sorted(report_dir.glob("security_audit_*.json"), reverse=True)
                if reports:
                    with open(reports[0], 'r') as f:
                        latest_report = json.load(f)
                        return {
                            "score": latest_report.get("security_score", 0),
                            "status": latest_report.get("status", "unknown"),
                            "issues": latest_report.get("issues", {}),
                            "last_audit": latest_report.get("audit_date", ""),
                            "report_file": str(reports[0].name)
                        }
            
            return {
                "score": 0,
                "status": "no_data",
                "message": "セキュリティ監査未実施"
            }
        except Exception as e:
            logger.error(f"セキュリティ状態取得エラー: {e}")
            return {"error": str(e)}
    
    async def get_recent_logs(self, lines: int = 100) -> List[Dict[str, Any]]:
        """最近のログ取得"""
        logs = []
        log_files = [
            "/root/logs/mana_screen_sharing.log",
            "/root/logs/trinity_secretary_enhanced.log",
            "/root/logs/screen_sharing_enhanced.log"
        ]
        
        for log_file in log_files:
            if os.path.exists(log_file):
                try:
                    with open(log_file, 'r') as f:
                        content = f.readlines()
                        for line in content[-lines:]:
                            if line.strip():
                                logs.append({
                                    "file": os.path.basename(log_file),
                                    "content": line.strip(),
                                    "timestamp": datetime.now().isoformat()
                                })
                except Exception as e:
                    logger.error(f"ログ読み込みエラー ({log_file}): {e}")
        
        return logs[-100:]  # 最新100件
    
    async def broadcast_update(self, data: Dict[str, Any]):
        """WebSocketで全クライアントに更新を送信"""
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except Exception as e:
                logger.error(f"WebSocket送信エラー: {e}")
    
    def setup_routes(self):
        """APIルート設定"""
        
        @self.app.get("/")
        def index():
            return HTMLResponse(open("/root/templates/unified_dashboard.html").read())
        
        @self.app.get("/api/overview")
        async def get_overview():
            """システム全体概要"""
            metrics = await self.get_system_metrics()
            services = await self.get_all_services_health()
            security = await self.get_security_status()
            
            # サービス統計
            online_count = len([s for s in services if s.get("status") == "online"])
            
            return JSONResponse({
                "system_metrics": metrics,
                "services": {
                    "total": len(services),
                    "online": online_count,
                    "offline": len(services) - online_count,
                    "list": services
                },
                "security": security,
                "timestamp": datetime.now().isoformat()
            })
        
        @self.app.get("/api/metrics")
        async def get_metrics():
            """システムメトリクス"""
            return JSONResponse(await self.get_system_metrics())
        
        @self.app.get("/api/services")
        async def get_services():
            """サービス一覧"""
            return JSONResponse(await self.get_all_services_health())
        
        @self.app.get("/api/security")
        async def get_security():
            """セキュリティ状態"""
            return JSONResponse(await self.get_security_status())
        
        @self.app.get("/api/logs")
        async def get_logs(lines: int = 100):
            """最近のログ"""
            logs = await self.get_recent_logs(lines)
            return JSONResponse({"logs": logs})
        
        @self.app.post("/api/service/{service_id}/restart")
        async def restart_service(service_id: str):
            """サービス再起動"""
            # TODO: 実装
            return JSONResponse({"success": False, "message": "Not implemented"})
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocketエンドポイント"""
            await websocket.accept()
            self.active_connections.append(websocket)
            
            try:
                while True:
                    # クライアントからのメッセージ待機
                    data = await websocket.receive_text()
                    
                    # リアルタイム更新送信
                    overview = await self.get_overview()
                    await websocket.send_json(overview)
                    
                    await asyncio.sleep(2)  # 2秒間隔
                    
            except WebSocketDisconnect:
                self.active_connections.remove(websocket)
                logger.info("WebSocket切断")

def main():
    logger.info("🎨 Mana Unified Dashboard 起動")
    dashboard = ManaUnifiedDashboard()
    uvicorn.run(dashboard.app, host="0.0.0.0", port=9999, log_level="info")

if __name__ == "__main__":
    main()

