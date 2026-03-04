#!/usr/bin/env python3
"""
Mana Realtime Notification Dashboard
リアルタイム通知ダッシュボード - 全システムイベントを統合表示
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ManaRealtimeNotificationDashboard:
    def __init__(self):
        self.app = FastAPI(title="Mana Realtime Notification Dashboard")
        self.active_connections: List[WebSocket] = []
        self.notification_queue = []
        
        self.setup_middleware()
        self.setup_routes()
        
        logger.info("📢 Mana Realtime Notification Dashboard 初期化完了")
    
    def setup_middleware(self):
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    async def broadcast_notification(self, notification: Dict[str, Any]):
        """通知をブロードキャスト"""
        for connection in self.active_connections:
            try:
                await connection.send_json(notification)
            except Exception as e:
                logger.error(f"通知送信エラー: {e}")
    
    async def monitor_systems(self):
        """システム監視ループ"""
        while True:
            try:
                # システム状態取得
                response = requests.get("http://localhost:9999/api/overview", timeout=5)
                overview = response.json()
                
                metrics = overview.get("system_metrics", {})
                services = overview.get("services", {})
                security = overview.get("security", {})
                
                # 警告チェック
                notifications = []
                
                if metrics.get("cpu", {}).get("percent", 0) > 80:
                    notifications.append({
                        "type": "warning",
                        "title": "CPU使用率警告",
                        "message": f"CPU: {metrics['cpu']['percent']:.1f}%",
                        "timestamp": datetime.now().isoformat()
                    })
                
                if metrics.get("memory", {}).get("percent", 0) > 80:
                    notifications.append({
                        "type": "warning",
                        "title": "メモリ使用率警告",
                        "message": f"メモリ: {metrics['memory']['percent']:.1f}%",
                        "timestamp": datetime.now().isoformat()
                    })
                
                if metrics.get("disk", {}).get("percent", 0) > 85:
                    notifications.append({
                        "type": "critical",
                        "title": "ディスク容量警告",
                        "message": f"ディスク: {metrics['disk']['percent']:.1f}%",
                        "timestamp": datetime.now().isoformat()
                    })
                
                if security.get("score", 100) < 50:
                    notifications.append({
                        "type": "warning",
                        "title": "セキュリティスコア低下",
                        "message": f"スコア: {security['score']}/100",
                        "timestamp": datetime.now().isoformat()
                    })
                
                if services.get("online", 0) < services.get("total", 0):
                    offline = services["total"] - services["online"]
                    notifications.append({
                        "type": "error",
                        "title": "サービス停止検出",
                        "message": f"{offline}個のサービスが停止しています",
                        "timestamp": datetime.now().isoformat()
                    })
                
                # 通知をブロードキャスト
                for notif in notifications:
                    await self.broadcast_notification(notif)
                    self.notification_queue.append(notif)
                
                # キューは最新100件のみ保持
                if len(self.notification_queue) > 100:
                    self.notification_queue = self.notification_queue[-100:]
                
                await asyncio.sleep(10)  # 10秒ごとにチェック
                
            except Exception as e:
                logger.error(f"監視エラー: {e}")
                await asyncio.sleep(10)
    
    def setup_routes(self):
        @self.app.get("/")
        def index():
            html_content = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>📢 Realtime Notifications</title>
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        margin: 0;
                        padding: 20px;
                    }
                    .container {
                        max-width: 1200px;
                        margin: 0 auto;
                        background: white;
                        border-radius: 15px;
                        padding: 30px;
                        box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                    }
                    h1 {
                        color: #667eea;
                        text-align: center;
                    }
                    .notification {
                        padding: 15px;
                        margin: 10px 0;
                        border-radius: 10px;
                        border-left: 5px solid;
                        animation: slideIn 0.3s;
                    }
                    @keyframes slideIn {
                        from { transform: translateX(-100%); opacity: 0; }
                        to { transform: translateX(0); opacity: 1; }
                    }
                    .notification.info { border-color: #3b82f6; background: #dbeafe; }
                    .notification.warning { border-color: #f59e0b; background: #fef3c7; }
                    .notification.error { border-color: #ef4444; background: #fee2e2; }
                    .notification.critical { border-color: #dc2626; background: #fecaca; }
                    .notification.success { border-color: #10b981; background: #d1fae5; }
                    .notification-title { font-weight: bold; margin-bottom: 5px; }
                    .notification-time { font-size: 0.9em; color: #666; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>📢 リアルタイム通知ダッシュボード</h1>
                    <div id="notifications"></div>
                </div>
                <script>
                    const ws = new WebSocket('ws://localhost:10000/ws');
                    const container = document.getElementById('notifications');
                    
                    ws.onmessage = (event) => {
                        const notification = JSON.parse(event.data);
                        const div = document.createElement('div');
                        div.className = `notification ${notification.type}`;
                        div.innerHTML = `
                            <div class="notification-title">${notification.title}</div>
                            <div>${notification.message}</div>
                            <div class="notification-time">${new Date(notification.timestamp).toLocaleString('ja-JP')}</div>
                        `;
                        container.insertBefore(div, container.firstChild);
                        
                        // 最新50件のみ表示
                        while (container.children.length > 50) {
                            container.removeChild(container.lastChild);
                        }
                    };
                </script>
            </body>
            </html>
            """
            return HTMLResponse(html_content)
        
        @self.app.get("/api/notifications")
        def get_notifications():
            return {"notifications": self.notification_queue}
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            self.active_connections.append(websocket)
            logger.info("WebSocket接続")
            
            try:
                while True:
                    await asyncio.sleep(1)
            except WebSocketDisconnect:
                self.active_connections.remove(websocket)
                logger.info("WebSocket切断")

async def run_app():
    dashboard = ManaRealtimeNotificationDashboard()
    
    # 監視タスクをバックグラウンドで開始
    asyncio.create_task(dashboard.monitor_systems())
    
    config = uvicorn.Config(dashboard.app, host="0.0.0.0", port=10000, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(run_app())

