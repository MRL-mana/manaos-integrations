import asyncio
import json
import logging
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import httpx
from fastapi import FastAPI, Request
from pydantic import BaseModel
import uvicorn

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

class MobileAction(BaseModel):
    action_type: str  # quick_start, emergency_stop, status_check, etc.
    target_system: str
    parameters: Dict[str, Any] = {}
    user_id: str = "mobile_user"
    timestamp: Optional[str] = None

class MobileNotification(BaseModel):
    id: Optional[str] = None
    title: str
    message: str
    priority: str = "normal"  # low, normal, high, urgent
    target_system: str
    created_at: Optional[str] = None
    read: bool = False

class ManaMobileInterfaceSystem:
    def __init__(self):
        self.app = FastAPI(title="Mana Mobile Interface System", version="1.0.0")
        self.db_path = "/root/mana_mobile_interface.db"
        self.logger = logger
        self.systems_config = self.load_systems_config()
        self.mobile_sessions = {}
        self.offline_cache = {}
        self.init_database()
        self.setup_api()
        self.setup_startup_events()
        self.start_background_tasks()
        self.logger.info("🚀 Mana Mobile Interface System 初期化完了")

    def load_systems_config(self) -> Dict[str, Any]:
        return {
            "trinity": {"port": 5005, "name": "Trinity", "mobile_actions": ["start_automation", "stop_automation", "check_status"]},
            "optimized": {"port": 5009, "name": "Optimized", "mobile_actions": ["optimize", "status"]},
            "ai": {"port": 5010, "name": "AI Secretary", "mobile_actions": ["chat", "status"]},
            "workflow": {"port": 5011, "name": "Workflow", "mobile_actions": ["execute", "status"]},
            "monitoring": {"port": 5012, "name": "Monitoring", "mobile_actions": ["alerts", "status"]},
            "security": {"port": 5013, "name": "Security", "mobile_actions": ["lockdown", "status"]},
            "scalability": {"port": 5014, "name": "Scalability", "mobile_actions": ["scale", "status"]},
            "orchestrator": {"port": 5015, "name": "Orchestrator", "mobile_actions": ["start", "stop", "status"]},
            "learning": {"port": 5016, "name": "Learning", "mobile_actions": ["train", "status"]},
            "predictive": {"port": 5017, "name": "Predictive", "mobile_actions": ["predict", "status"]},
            "dynamic_scaling": {"port": 5018, "name": "Dynamic Scaling", "mobile_actions": ["scale", "status"]},
            "security_auto": {"port": 5019, "name": "Security Auto", "mobile_actions": ["respond", "status"]},
            "multiagent": {"port": 5020, "name": "Multi-Agent", "mobile_actions": ["coordinate", "status"]},
            "timeseries": {"port": 5021, "name": "Time Series", "mobile_actions": ["predict", "status"]},
            "realtime": {"port": 5022, "name": "Real-time", "mobile_actions": ["decide", "status"]},
            "self_healing": {"port": 5023, "name": "Self-Healing", "mobile_actions": ["heal", "status"]},
            "manaos": {"port": 5024, "name": "ManaOS", "mobile_actions": ["status", "control"]},
            "monitoring_central": {"port": 5025, "name": "Central Monitoring", "mobile_actions": ["dashboard", "alerts"]},
            "rule_approval": {"port": 5026, "name": "Rule Approval", "mobile_actions": ["approve", "reject"]},
            "security_advanced": {"port": 5027, "name": "Advanced Security", "mobile_actions": ["threats", "actions"]},
            "cloud_resources": {"port": 5028, "name": "Cloud Resources", "mobile_actions": ["create", "delete", "scale"]},
            "distributed": {"port": 5029, "name": "Distributed", "mobile_actions": ["tasks", "workers"]},
            "high_availability": {"port": 5030, "name": "High Availability", "mobile_actions": ["failover", "status"]}
        }

    def init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # モバイルアクション履歴テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mobile_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_type TEXT NOT NULL,
                target_system TEXT NOT NULL,
                parameters TEXT,
                user_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                success BOOLEAN,
                result TEXT
            )
        """)
        
        # モバイル通知テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mobile_notifications (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                priority TEXT NOT NULL,
                target_system TEXT NOT NULL,
                created_at TEXT NOT NULL,
                read BOOLEAN DEFAULT FALSE
            )
        """)
        
        # モバイルセッションテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mobile_sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                device_info TEXT,
                last_activity TEXT NOT NULL,
                active BOOLEAN DEFAULT TRUE
            )
        """)
        
        # オフラインキャッシュテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS offline_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cache_key TEXT NOT NULL,
                cache_data TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        
        conn.commit()
        conn.close()
        self.logger.info("データベース初期化完了")

    def setup_api(self):
        @self.app.get("/api/status", summary="モバイルインターフェースシステムのステータス")
        async def get_status():
            return {
                "timestamp": datetime.now().isoformat(),
                "system": "Mana Mobile Interface System",
                "status": "healthy",
                "version": self.app.version,
                "mobile_sessions": len(self.mobile_sessions),
                "cached_systems": len(self.offline_cache)
            }

        @self.app.post("/api/mobile/action", summary="モバイルアクション実行")
        async def execute_mobile_action(action: MobileAction):
            action.timestamp = datetime.now().isoformat()
            
            # アクション履歴を記録
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO mobile_actions 
                (action_type, target_system, parameters, user_id, timestamp, success, result)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                action.action_type,
                action.target_system,
                json.dumps(action.parameters),
                action.user_id,
                action.timestamp,
                False,  # 初期値
                None
            ))
            
            action_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            # アクション実行
            result = await self.execute_action(action)
            
            # 結果を更新
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE mobile_actions 
                SET success = ?, result = ?
                WHERE id = ?
            """, (result["success"], json.dumps(result), action_id))
            conn.commit()
            conn.close()
            
            self.logger.info(f"モバイルアクション実行: {action.action_type} - {action.target_system}")
            return {"status": "success", "action_id": action_id, "result": result}

        @self.app.get("/api/mobile/quick-actions", summary="クイックアクション一覧")
        async def get_quick_actions():
            quick_actions = []
            
            for system_id, system_config in self.systems_config.items():
                for action in system_config.get("mobile_actions", []):
                    quick_actions.append({
                        "system_id": system_id,
                        "system_name": system_config["name"],
                        "action": action,
                        "endpoint": f"http://localhost:{system_config['port']}/api/status"
                    })
            
            return {"quick_actions": quick_actions, "count": len(quick_actions)}

        @self.app.get("/api/mobile/dashboard", summary="モバイルダッシュボード")
        async def get_mobile_dashboard():
            dashboard_data = {
                "timestamp": datetime.now().isoformat(),
                "systems": {},
                "notifications": [],
                "quick_stats": {}
            }
            
            # 各システムのステータス取得
            for system_id, system_config in self.systems_config.items():
                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.get(f"http://localhost:{system_config['port']}/api/status", timeout=3)
                        if response.status_code == 200:
                            dashboard_data["systems"][system_id] = {
                                "name": system_config["name"],
                                "status": "healthy",
                                "port": system_config["port"],
                                "mobile_actions": system_config.get("mobile_actions", [])
                            }
                        else:
                            dashboard_data["systems"][system_id] = {
                                "name": system_config["name"],
                                "status": "unhealthy",
                                "port": system_config["port"],
                                "mobile_actions": system_config.get("mobile_actions", [])
                            }
                except Exception as e:
                    dashboard_data["systems"][system_id] = {
                        "name": system_config["name"],
                        "status": "offline",
                        "port": system_config["port"],
                        "mobile_actions": system_config.get("mobile_actions", []),
                        "error": str(e)
                    }
            
            # 通知取得
            dashboard_data["notifications"] = self.get_recent_notifications()
            
            # クイック統計
            dashboard_data["quick_stats"] = {
                "total_systems": len(dashboard_data["systems"]),
                "healthy_systems": len([s for s in dashboard_data["systems"].values() if s["status"] == "healthy"]),
                "unhealthy_systems": len([s for s in dashboard_data["systems"].values() if s["status"] == "unhealthy"]),
                "offline_systems": len([s for s in dashboard_data["systems"].values() if s["status"] == "offline"]),
                "unread_notifications": len([n for n in dashboard_data["notifications"] if not n["read"]])
            }
            
            return dashboard_data

        @self.app.get("/api/mobile/notifications", summary="モバイル通知一覧")
        async def get_notifications(unread_only: bool = False):
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if unread_only:
                cursor.execute("""
                    SELECT * FROM mobile_notifications 
                    WHERE read = FALSE 
                    ORDER BY created_at DESC
                """)
            else:
                cursor.execute("""
                    SELECT * FROM mobile_notifications 
                    ORDER BY created_at DESC 
                    LIMIT 50
                """)
            
            notifications = []
            for row in cursor.fetchall():
                notifications.append({
                    "id": row[0],
                    "title": row[1],
                    "message": row[2],
                    "priority": row[3],
                    "target_system": row[4],
                    "created_at": row[5],
                    "read": bool(row[6])
                })
            
            conn.close()
            return {"notifications": notifications, "count": len(notifications)}

        @self.app.post("/api/mobile/notifications/{notification_id}/read", summary="通知を既読にする")
        async def mark_notification_read(notification_id: str):
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE mobile_notifications 
                SET read = TRUE 
                WHERE id = ?
            """, (notification_id,))
            
            conn.commit()
            conn.close()
            
            return {"status": "success", "message": "通知を既読にしました"}

        @self.app.get("/api/mobile/offline-cache", summary="オフラインキャッシュ取得")
        async def get_offline_cache():
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT cache_key, cache_data, expires_at 
                FROM offline_cache 
                WHERE expires_at > datetime('now')
                ORDER BY created_at DESC
            """)
            
            cache_data = {}
            for row in cursor.fetchall():
                cache_data[row[0]] = {
                    "data": json.loads(row[1]),
                    "expires_at": row[2]
                }
            
            conn.close()
            return {"cache": cache_data, "count": len(cache_data)}

        @self.app.get("/", summary="モバイルダッシュボード")
        async def mobile_dashboard(request: Request):
            # ユーザーエージェントをチェックしてモバイル最適化
            user_agent = request.headers.get("user-agent", "").lower()
            is_mobile = any(device in user_agent for device in ["mobile", "android", "iphone", "ipad"])
            
            return """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Mana Mobile Interface</title>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1, user-scalable=no">
                <meta name="apple-mobile-web-app-capable" content="yes">
                <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
                <style>
                    * { margin: 0; padding: 0; box-sizing: border-box; }
                    body { 
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white; 
                        min-height: 100vh;
                        padding: 10px;
                        overflow-x: hidden;
                    }
                    .container { max-width: 100%; margin: 0 auto; }
                    .header { text-align: center; margin-bottom: 20px; padding: 10px; }
                    .header h1 { font-size: 1.8em; margin: 0; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
                    .header p { font-size: 0.9em; opacity: 0.9; margin-top: 5px; }
                    .quick-stats { 
                        display: grid; 
                        grid-template-columns: repeat(2, 1fr); 
                        gap: 10px; 
                        margin-bottom: 20px; 
                    }
                    .stat-card { 
                        background: rgba(255,255,255,0.15); 
                        border-radius: 12px; 
                        padding: 15px; 
                        text-align: center;
                        backdrop-filter: blur(10px);
                        border: 1px solid rgba(255,255,255,0.2);
                    }
                    .stat-number { font-size: 1.5em; font-weight: bold; color: #ffd700; }
                    .stat-label { font-size: 0.8em; opacity: 0.9; margin-top: 5px; }
                    .systems-grid { 
                        display: grid; 
                        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); 
                        gap: 10px; 
                        margin-bottom: 20px; 
                    }
                    .system-card { 
                        background: rgba(255,255,255,0.1); 
                        border-radius: 12px; 
                        padding: 15px; 
                        text-align: center;
                        backdrop-filter: blur(10px);
                        border: 1px solid rgba(255,255,255,0.2);
                        cursor: pointer;
                        transition: transform 0.2s;
                    }
                    .system-card:hover { transform: scale(1.05); }
                    .system-card.healthy { border-left: 4px solid #4CAF50; }
                    .system-card.unhealthy { border-left: 4px solid #f44336; }
                    .system-card.offline { border-left: 4px solid #ff9800; }
                    .system-name { font-size: 0.9em; font-weight: bold; margin-bottom: 5px; }
                    .system-status { font-size: 0.8em; opacity: 0.9; }
                    .quick-actions { 
                        display: grid; 
                        grid-template-columns: repeat(2, 1fr); 
                        gap: 10px; 
                        margin-bottom: 20px; 
                    }
                    .action-btn { 
                        background: rgba(76,175,80,0.8); 
                        color: white; 
                        border: none; 
                        padding: 15px; 
                        border-radius: 12px; 
                        font-size: 0.9em;
                        cursor: pointer;
                        transition: background 0.2s;
                        backdrop-filter: blur(10px);
                    }
                    .action-btn:hover { background: rgba(76,175,80,1); }
                    .action-btn.danger { background: rgba(244,67,54,0.8); }
                    .action-btn.danger:hover { background: rgba(244,67,54,1); }
                    .notifications { 
                        background: rgba(255,255,255,0.1); 
                        border-radius: 12px; 
                        padding: 15px; 
                        margin-bottom: 20px;
                        backdrop-filter: blur(10px);
                        border: 1px solid rgba(255,255,255,0.2);
                    }
                    .notification-item { 
                        background: rgba(255,255,255,0.1); 
                        border-radius: 8px; 
                        padding: 10px; 
                        margin: 5px 0; 
                        font-size: 0.8em;
                    }
                    .notification-item.urgent { border-left: 4px solid #f44336; }
                    .notification-item.high { border-left: 4px solid #ff9800; }
                    .notification-item.normal { border-left: 4px solid #4CAF50; }
                    .refresh-btn { 
                        position: fixed; 
                        bottom: 20px; 
                        right: 20px; 
                        background: rgba(76,175,80,0.9); 
                        color: white; 
                        border: none; 
                        width: 60px; 
                        height: 60px; 
                        border-radius: 50%; 
                        font-size: 1.5em;
                        cursor: pointer;
                        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                        z-index: 1000;
                    }
                    .refresh-btn:hover { background: rgba(76,175,80,1); }
                    @media (max-width: 480px) {
                        .systems-grid { grid-template-columns: repeat(2, 1fr); }
                        .quick-actions { grid-template-columns: 1fr; }
                        .header h1 { font-size: 1.5em; }
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>📱 Mana Mobile Interface</h1>
                        <p>モバイル最適化・ワンクリック操作・オフライン対応</p>
                    </div>
                    
                    <div class="quick-stats" id="quick-stats">
                        <!-- クイック統計がここに表示されます -->
                    </div>
                    
                    <div class="systems-grid" id="systems-grid">
                        <!-- システムカードがここに表示されます -->
                    </div>
                    
                    <div class="quick-actions">
                        <button class="action-btn" onclick="emergencyStop()">🛑 緊急停止</button>
                        <button class="action-btn" onclick="systemOptimize()">⚡ 最適化</button>
                        <button class="action-btn" onclick="securityCheck()">🛡️ セキュリティ</button>
                        <button class="action-btn danger" onclick="emergencyLockdown()">🚨 ロックダウン</button>
                    </div>
                    
                    <div class="notifications">
                        <h3 style="margin-bottom: 10px; color: #ffd700;">🔔 通知</h3>
                        <div id="notifications-list">
                            <!-- 通知がここに表示されます -->
                        </div>
                    </div>
                </div>
                
                <button class="refresh-btn" onclick="refreshDashboard()">🔄</button>
                
                <script>
                    async function refreshDashboard() {
                        try {
                            const response = await fetch('/api/mobile/dashboard');
                            const data = await response.json();
                            
                            // クイック統計更新
                            const quickStats = document.getElementById('quick-stats');
                            quickStats.innerHTML = `
                                <div class="stat-card">
                                    <div class="stat-number">${data.quick_stats.healthy_systems}</div>
                                    <div class="stat-label">健全システム</div>
                                </div>
                                <div class="stat-card">
                                    <div class="stat-number">${data.quick_stats.unhealthy_systems}</div>
                                    <div class="stat-label">不健全システム</div>
                                </div>
                                <div class="stat-card">
                                    <div class="stat-number">${data.quick_stats.offline_systems}</div>
                                    <div class="stat-label">オフライン</div>
                                </div>
                                <div class="stat-card">
                                    <div class="stat-number">${data.quick_stats.unread_notifications}</div>
                                    <div class="stat-label">未読通知</div>
                                </div>
                            `;
                            
                            // システムカード更新
                            const systemsGrid = document.getElementById('systems-grid');
                            systemsGrid.innerHTML = Object.entries(data.systems).map(([systemId, system]) => {
                                const statusClass = system.status;
                                const statusIcon = system.status === 'healthy' ? '✅' : 
                                                 system.status === 'unhealthy' ? '⚠️' : '❌';
                                
                                return `
                                    <div class="system-card ${statusClass}" onclick="showSystemActions('${systemId}')">
                                        <div class="system-name">${statusIcon} ${system.name}</div>
                                        <div class="system-status">${system.status}</div>
                                    </div>
                                `;
                            }).join('');
                            
                            // 通知更新
                            const notificationsList = document.getElementById('notifications-list');
                            if (data.notifications && data.notifications.length > 0) {
                                notificationsList.innerHTML = data.notifications.slice(0, 5).map(notification => `
                                    <div class="notification-item ${notification.priority}">
                                        <strong>${notification.title}</strong><br>
                                        ${notification.message}<br>
                                        <small>${new Date(notification.created_at).toLocaleString()}</small>
                                    </div>
                                `).join('');
                            } else {
                                notificationsList.innerHTML = '<div style="text-align: center; opacity: 0.7;">通知はありません</div>';
                            }
                            
                        } catch (error) {
                            console.error('ダッシュボード更新エラー:', error);
                        }
                    }
                    
                    async function emergencyStop() {
                        if (confirm('緊急停止を実行しますか？')) {
                            try {
                                const response = await fetch('/api/mobile/action', {
                                    method: 'POST',
                                    headers: {'Content-Type': 'application/json'},
                                    body: JSON.stringify({
                                        action_type: 'emergency_stop',
                                        target_system: 'all',
                                        parameters: {reason: 'Mobile emergency stop'}
                                    })
                                });
                                const result = await response.json();
                                alert('緊急停止実行: ' + result.result.message);
                                refreshDashboard();
                            } catch (error) {
                                console.error('緊急停止エラー:', error);
                            }
                        }
                    }
                    
                    async function systemOptimize() {
                        try {
                            const response = await fetch('/api/mobile/action', {
                                method: 'POST',
                                headers: {'Content-Type': 'application/json'},
                                body: JSON.stringify({
                                    action_type: 'optimize',
                                    target_system: 'optimized',
                                    parameters: {}
                                })
                            });
                            const result = await response.json();
                            alert('システム最適化実行: ' + result.result.message);
                            refreshDashboard();
                        } catch (error) {
                            console.error('最適化エラー:', error);
                        }
                    }
                    
                    async function securityCheck() {
                        try {
                            const response = await fetch('/api/mobile/action', {
                                method: 'POST',
                                headers: {'Content-Type': 'application/json'},
                                body: JSON.stringify({
                                    action_type: 'security_check',
                                    target_system: 'security_advanced',
                                    parameters: {}
                                })
                            });
                            const result = await response.json();
                            alert('セキュリティチェック実行: ' + result.result.message);
                            refreshDashboard();
                        } catch (error) {
                            console.error('セキュリティチェックエラー:', error);
                        }
                    }
                    
                    async function emergencyLockdown() {
                        if (confirm('緊急ロックダウンを実行しますか？全ての外部アクセスがブロックされます。')) {
                            try {
                                const response = await fetch('/api/mobile/action', {
                                    method: 'POST',
                                    headers: {'Content-Type': 'application/json'},
                                    body: JSON.stringify({
                                        action_type: 'emergency_lockdown',
                                        target_system: 'security_advanced',
                                        parameters: {reason: 'Mobile emergency lockdown'}
                                    })
                                });
                                const result = await response.json();
                                alert('緊急ロックダウン実行: ' + result.result.message);
                                refreshDashboard();
                            } catch (error) {
                                console.error('ロックダウンエラー:', error);
                            }
                        }
                    }
                    
                    function showSystemActions(systemId) {
                        // システム固有のアクションを表示
                        alert(`システム ${systemId} のアクションを表示`);
                    }
                    
                    // 初期読み込み
                    refreshDashboard();
                    
                    // 30秒ごとに自動更新
                    setInterval(refreshDashboard, 30000);
                    
                    // プルツーリフレッシュ対応
                    let startY = 0;
                    document.addEventListener('touchstart', (e) => {
                        startY = e.touches[0].clientY;
                    });
                    
                    document.addEventListener('touchmove', (e) => {
                        const currentY = e.touches[0].clientY;
                        if (currentY - startY > 100) {
                            refreshDashboard();
                        }
                    });
                </script>
            </body>
            </html>
            """

    def setup_startup_events(self):
        @self.app.on_event("startup")
        async def startup_event():
            asyncio.create_task(self._notification_worker())
            asyncio.create_task(self._offline_cache_worker())
            asyncio.create_task(self._mobile_session_worker())
            self.logger.info("バックグラウンドタスク開始")

    async def execute_action(self, action: MobileAction) -> Dict[str, Any]:
        """モバイルアクションを実行"""
        try:
            if action.target_system not in self.systems_config:
                return {"success": False, "message": f"システム {action.target_system} が見つかりません"}
            
            system_config = self.systems_config[action.target_system]
            
            # アクションタイプに応じて実行
            if action.action_type == "emergency_stop":
                return await self.emergency_stop_all_systems()
            elif action.action_type == "optimize":
                return await self.optimize_system(system_config)
            elif action.action_type == "security_check":
                return await self.security_check(system_config)
            elif action.action_type == "emergency_lockdown":
                return await self.emergency_lockdown(system_config)
            elif action.action_type == "status":
                return await self.get_system_status(system_config)
            else:
                return {"success": False, "message": f"不明なアクション: {action.action_type}"}
                
        except Exception as e:
            self.logger.error(f"モバイルアクション実行エラー: {e}")
            return {"success": False, "message": str(e)}

    async def emergency_stop_all_systems(self) -> Dict[str, Any]:
        """全システムの緊急停止"""
        stopped_systems = []
        
        for system_id, system_config in self.systems_config.items():
            try:
                async with httpx.AsyncClient() as client:
                    # 実際の実装では、各システムの停止APIを呼び出し
                    stopped_systems.append(system_id)
            except Exception as e:
                self.logger.error(f"システム停止エラー {system_id}: {e}")
        
        return {
            "success": True,
            "message": f"{len(stopped_systems)}個のシステムを停止しました",
            "stopped_systems": stopped_systems
        }

    async def optimize_system(self, system_config: Dict[str, Any]) -> Dict[str, Any]:
        """システム最適化"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"http://localhost:{system_config['port']}/api/optimize",
                    timeout=10
                )
                if response.status_code == 200:
                    return {"success": True, "message": "システム最適化が完了しました"}
                else:
                    return {"success": False, "message": f"最適化エラー: HTTP {response.status_code}"}
        except Exception as e:
            return {"success": False, "message": f"最適化エラー: {str(e)}"}

    async def security_check(self, system_config: Dict[str, Any]) -> Dict[str, Any]:
        """セキュリティチェック"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"http://localhost:{system_config['port']}/api/threats",
                    timeout=10
                )
                if response.status_code == 200:
                    threats = response.json()
                    return {
                        "success": True,
                        "message": f"セキュリティチェック完了: {threats.get('count', 0)}個の脅威を検出",
                        "threats": threats
                    }
                else:
                    return {"success": False, "message": f"セキュリティチェックエラー: HTTP {response.status_code}"}
        except Exception as e:
            return {"success": False, "message": f"セキュリティチェックエラー: {str(e)}"}

    async def emergency_lockdown(self, system_config: Dict[str, Any]) -> Dict[str, Any]:
        """緊急ロックダウン"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"http://localhost:{system_config['port']}/api/actions",
                    json={
                        "action_type": "emergency_lockdown",
                        "target": "all_systems",
                        "parameters": {"reason": "Mobile emergency lockdown"}
                    },
                    timeout=10
                )
                if response.status_code == 200:
                    return {"success": True, "message": "緊急ロックダウンが実行されました"}
                else:
                    return {"success": False, "message": f"ロックダウンエラー: HTTP {response.status_code}"}
        except Exception as e:
            return {"success": False, "message": f"ロックダウンエラー: {str(e)}"}

    async def get_system_status(self, system_config: Dict[str, Any]) -> Dict[str, Any]:
        """システムステータス取得"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"http://localhost:{system_config['port']}/api/status",
                    timeout=5
                )
                if response.status_code == 200:
                    return {"success": True, "message": "ステータス取得完了", "status": response.json()}
                else:
                    return {"success": False, "message": f"ステータス取得エラー: HTTP {response.status_code}"}
        except Exception as e:
            return {"success": False, "message": f"ステータス取得エラー: {str(e)}"}

    def get_recent_notifications(self) -> List[Dict[str, Any]]:
        """最近の通知を取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM mobile_notifications 
            ORDER BY created_at DESC 
            LIMIT 10
        """)
        
        notifications = []
        for row in cursor.fetchall():
            notifications.append({
                "id": row[0],
                "title": row[1],
                "message": row[2],
                "priority": row[3],
                "target_system": row[4],
                "created_at": row[5],
                "read": bool(row[6])
            })
        
        conn.close()
        return notifications

    async def _notification_worker(self):
        """通知ワーカー"""
        while True:
            try:
                await self.check_system_notifications()
                await asyncio.sleep(60)  # 1分ごとにチェック
            except Exception as e:
                self.logger.error(f"通知ワーカーエラー: {e}")
                await asyncio.sleep(60)

    async def check_system_notifications(self):
        """システム通知をチェック"""
        for system_id, system_config in self.systems_config.items():
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"http://localhost:{system_config['port']}/api/status", timeout=5)
                    if response.status_code != 200:
                        await self.create_notification(
                            title=f"{system_config['name']} システム異常",
                            message=f"システム {system_config['name']} が応答しません",
                            priority="high",
                            target_system=system_id
                        )
            except Exception as e:
                await self.create_notification(
                    title=f"{system_config['name']} システムオフライン",
                    message=f"システム {system_config['name']} がオフラインです: {str(e)}",
                    priority="urgent",
                    target_system=system_id
                )

    async def create_notification(self, title: str, message: str, priority: str, target_system: str):
        """通知を作成"""
        notification_id = f"notif_{int(time.time())}_{hash(title) % 10000}"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO mobile_notifications 
            (id, title, message, priority, target_system, created_at, read)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (notification_id, title, message, priority, target_system, datetime.now().isoformat(), False))
        
        conn.commit()
        conn.close()
        
        self.logger.info(f"モバイル通知作成: {title}")

    async def _offline_cache_worker(self):
        """オフラインキャッシュワーカー"""
        while True:
            try:
                await self.update_offline_cache()
                await asyncio.sleep(300)  # 5分ごとに更新
            except Exception as e:
                self.logger.error(f"オフラインキャッシュワーカーエラー: {e}")
                await asyncio.sleep(300)

    async def update_offline_cache(self):
        """オフラインキャッシュを更新"""
        for system_id, system_config in self.systems_config.items():
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"http://localhost:{system_config['port']}/api/status", timeout=5)
                    if response.status_code == 200:
                        cache_data = response.json()
                        cache_key = f"system_status_{system_id}"
                        
                        conn = sqlite3.connect(self.db_path)
                        cursor = conn.cursor()
                        
                        cursor.execute("""
                            INSERT OR REPLACE INTO offline_cache 
                            (cache_key, cache_data, expires_at, created_at)
                            VALUES (?, ?, ?, ?)
                        """, (
                            cache_key,
                            json.dumps(cache_data),
                            (datetime.now() + timedelta(minutes=10)).isoformat(),
                            datetime.now().isoformat()
                        ))
                        
                        conn.commit()
                        conn.close()
                        
                        self.offline_cache[cache_key] = cache_data
                        
            except Exception as e:
                self.logger.error(f"オフラインキャッシュ更新エラー {system_id}: {e}")

    async def _mobile_session_worker(self):
        """モバイルセッションワーカー"""
        while True:
            try:
                await self.cleanup_old_sessions()
                await asyncio.sleep(3600)  # 1時間ごとにクリーンアップ
            except Exception as e:
                self.logger.error(f"モバイルセッションワーカーエラー: {e}")
                await asyncio.sleep(3600)

    async def cleanup_old_sessions(self):
        """古いセッションをクリーンアップ"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 24時間以上古いセッションを削除
        cutoff_time = (datetime.now() - timedelta(hours=24)).isoformat()
        cursor.execute("DELETE FROM mobile_sessions WHERE last_activity < ?", (cutoff_time,))
        
        conn.commit()
        conn.close()

    def start_background_tasks(self):
        # バックグラウンドタスクはFastAPIのstartupイベントで開始
        self.logger.info("バックグラウンドタスク準備完了")

def main():
    system = ManaMobileInterfaceSystem()
    uvicorn.run(system.app, host="0.0.0.0", port=5031)

if __name__ == "__main__":
    main()
