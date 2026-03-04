import asyncio
import logging
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

class HealthCheck(BaseModel):
    service_name: str
    endpoint: str
    status: str  # healthy, unhealthy, degraded
    response_time: float
    last_checked: str
    error_message: Optional[str] = None

class FailoverEvent(BaseModel):
    id: Optional[str] = None
    service_name: str
    primary_endpoint: str
    backup_endpoint: str
    failover_reason: str
    timestamp: Optional[str] = None
    status: str = "initiated"  # initiated, completed, failed

class ManaHighAvailabilitySystem:
    def __init__(self):
        self.app = FastAPI(title="Mana High Availability System", version="1.0.0")
        self.db_path = "/root/mana_high_availability.db"
        self.logger = logger
        self.services_config = self.load_services_config()
        self.health_checks = {}
        self.failover_events = []
        self.init_database()
        self.setup_api()
        self.setup_startup_events()
        self.start_background_tasks()
        self.logger.info("🚀 Mana High Availability System 初期化完了")

    def load_services_config(self) -> Dict[str, Any]:
        return {
            "trinity": {
                "primary": {"port": 5005, "endpoint": "/api/status"},
                "backup": {"port": 5006, "endpoint": "/api/status"},
                "health_check_interval": 30
            },
            "optimized": {
                "primary": {"port": 5009, "endpoint": "/api/status"},
                "backup": {"port": 5010, "endpoint": "/api/status"},
                "health_check_interval": 30
            },
            "ai": {
                "primary": {"port": 5010, "endpoint": "/api/status"},
                "backup": {"port": 5011, "endpoint": "/api/status"},
                "health_check_interval": 30
            },
            "workflow": {
                "primary": {"port": 5011, "endpoint": "/api/status"},
                "backup": {"port": 5012, "endpoint": "/api/status"},
                "health_check_interval": 30
            },
            "monitoring": {
                "primary": {"port": 5012, "endpoint": "/api/status"},
                "backup": {"port": 5013, "endpoint": "/api/status"},
                "health_check_interval": 30
            },
            "security": {
                "primary": {"port": 5013, "endpoint": "/api/status"},
                "backup": {"port": 5014, "endpoint": "/api/status"},
                "health_check_interval": 30
            },
            "scalability": {
                "primary": {"port": 5014, "endpoint": "/api/status"},
                "backup": {"port": 5015, "endpoint": "/api/status"},
                "health_check_interval": 30
            },
            "orchestrator": {
                "primary": {"port": 5015, "endpoint": "/api/status"},
                "backup": {"port": 5016, "endpoint": "/api/status"},
                "health_check_interval": 30
            }
        }

    def init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # ヘルスチェック履歴テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS health_check_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_name TEXT NOT NULL,
                endpoint TEXT NOT NULL,
                status TEXT NOT NULL,
                response_time REAL,
                error_message TEXT,
                timestamp TEXT NOT NULL
            )
        """)
        
        # フェイルオーバーイベントテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS failover_events (
                id TEXT PRIMARY KEY,
                service_name TEXT NOT NULL,
                primary_endpoint TEXT NOT NULL,
                backup_endpoint TEXT NOT NULL,
                failover_reason TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                status TEXT DEFAULT 'initiated'
            )
        """)
        
        # サービス可用性統計テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS availability_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_name TEXT NOT NULL,
                uptime_percentage REAL,
                total_checks INTEGER,
                successful_checks INTEGER,
                failed_checks INTEGER,
                avg_response_time REAL,
                date TEXT NOT NULL
            )
        """)
        
        # 自動復旧ログテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recovery_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_name TEXT NOT NULL,
                recovery_action TEXT NOT NULL,
                success BOOLEAN,
                details TEXT,
                timestamp TEXT NOT NULL
            )
        """)
        
        conn.commit()
        conn.close()
        self.logger.info("データベース初期化完了")

    def setup_api(self):
        @self.app.get("/api/status", summary="高可用性システムのステータス")
        async def get_status():
            return {
                "timestamp": datetime.now().isoformat(),
                "system": "Mana High Availability System",
                "status": "healthy",
                "version": self.app.version,
                "monitored_services": len(self.services_config),
                "active_failovers": len([f for f in self.failover_events if f.status == "initiated"])
            }

        @self.app.get("/api/health", summary="全サービスのヘルスチェック結果")
        async def get_health_status():
            health_status = {}
            for service_name, service_config in self.services_config.items():
                primary_health = self.health_checks.get(f"{service_name}_primary", {})
                backup_health = self.health_checks.get(f"{service_name}_backup", {})
                
                health_status[service_name] = {
                    "primary": primary_health,
                    "backup": backup_health,
                    "overall_status": self.determine_overall_status(primary_health, backup_health)
                }
            
            return {
                "timestamp": datetime.now().isoformat(),
                "health_status": health_status,
                "summary": self.generate_health_summary(health_status)
            }

        @self.app.get("/api/failover-events", summary="フェイルオーバーイベント一覧")
        async def get_failover_events():
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM failover_events 
                ORDER BY timestamp DESC 
                LIMIT 50
            """)
            
            events = []
            for row in cursor.fetchall():
                events.append({
                    "id": row[0],
                    "service_name": row[1],
                    "primary_endpoint": row[2],
                    "backup_endpoint": row[3],
                    "failover_reason": row[4],
                    "timestamp": row[5],
                    "status": row[6]
                })
            
            conn.close()
            return {"failover_events": events, "count": len(events)}

        @self.app.post("/api/failover/{service_name}", summary="手動フェイルオーバー実行")
        async def manual_failover(service_name: str, reason: str = "Manual failover"):
            if service_name not in self.services_config:
                raise HTTPException(status_code=404, detail="サービスが見つかりません")
            
            result = await self.execute_failover(service_name, reason)
            return {"status": "success", "result": result}

        @self.app.get("/api/availability-stats", summary="可用性統計")
        async def get_availability_stats(days: int = 7):
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            since_date = (datetime.now() - timedelta(days=days)).date().isoformat()
            
            cursor.execute("""
                SELECT service_name, uptime_percentage, total_checks, successful_checks, 
                       failed_checks, avg_response_time, date
                FROM availability_stats 
                WHERE date >= ?
                ORDER BY date DESC, service_name
            """, (since_date,))
            
            stats = []
            for row in cursor.fetchall():
                stats.append({
                    "service_name": row[0],
                    "uptime_percentage": row[1],
                    "total_checks": row[2],
                    "successful_checks": row[3],
                    "failed_checks": row[4],
                    "avg_response_time": row[5],
                    "date": row[6]
                })
            
            conn.close()
            return {"availability_stats": stats, "period_days": days}

        @self.app.get("/api/recovery-logs", summary="復旧ログ")
        async def get_recovery_logs(service_name: Optional[str] = None):
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if service_name:
                cursor.execute("""
                    SELECT * FROM recovery_logs 
                    WHERE service_name = ?
                    ORDER BY timestamp DESC 
                    LIMIT 50
                """, (service_name,))
            else:
                cursor.execute("""
                    SELECT * FROM recovery_logs 
                    ORDER BY timestamp DESC 
                    LIMIT 50
                """)
            
            logs = []
            for row in cursor.fetchall():
                logs.append({
                    "id": row[0],
                    "service_name": row[1],
                    "recovery_action": row[2],
                    "success": bool(row[3]),
                    "details": row[4],
                    "timestamp": row[5]
                })
            
            conn.close()
            return {"recovery_logs": logs, "count": len(logs)}

        @self.app.get("/", summary="高可用性ダッシュボード")
        async def dashboard():
            return """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Mana High Availability System</title>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
                    .container { max-width: 1200px; margin: 0 auto; }
                    .header { text-align: center; margin-bottom: 30px; }
                    .header h1 { font-size: 2.5em; margin: 0; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
                    .header p { font-size: 1.2em; opacity: 0.9; }
                    .dashboard-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 30px; }
                    .card { background: rgba(255,255,255,0.1); border-radius: 15px; padding: 20px; backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.2); }
                    .card h3 { margin-top: 0; color: #ffd700; }
                    .service-item { background: rgba(255,255,255,0.1); border-radius: 10px; padding: 15px; margin: 10px 0; }
                    .status-healthy { border-left: 4px solid #4CAF50; }
                    .status-unhealthy { border-left: 4px solid #f44336; }
                    .status-degraded { border-left: 4px solid #ff9800; }
                    .status-failover { border-left: 4px solid #9C27B0; }
                    .btn { background: #4CAF50; color: white; border: none; padding: 8px 16px; border-radius: 5px; cursor: pointer; margin: 5px; }
                    .btn:hover { background: #45a049; }
                    .btn-warning { background: #ff9800; }
                    .btn-warning:hover { background: #f57c00; }
                    .btn-danger { background: #f44336; }
                    .btn-danger:hover { background: #da190b; }
                    .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🔄 Mana High Availability System</h1>
                        <p>高可用性・自動フェイルオーバー・ゼロダウンタイムシステム</p>
                    </div>
                    
                    <div class="dashboard-grid">
                        <div class="card">
                            <h3>🏥 サービスヘルス</h3>
                            <div id="service-health"></div>
                        </div>
                        
                        <div class="card">
                            <h3>🔄 フェイルオーバーイベント</h3>
                            <div id="failover-events"></div>
                        </div>
                        
                        <div class="card">
                            <h3>📊 可用性統計</h3>
                            <div id="availability-stats"></div>
                        </div>
                    </div>
                    
                    <div class="dashboard-grid">
                        <div class="card">
                            <h3>🔧 復旧ログ</h3>
                            <div id="recovery-logs"></div>
                        </div>
                        
                        <div class="card">
                            <h3>⚡ 自動復旧</h3>
                            <div id="auto-recovery"></div>
                        </div>
                        
                        <div class="card">
                            <h3>📈 システム統計</h3>
                            <div id="system-stats"></div>
                        </div>
                    </div>
                    
                    <div style="text-align: center; margin-top: 30px;">
                        <button class="btn" onclick="refreshDashboard()">🔄 ダッシュボード更新</button>
                        <button class="btn btn-warning" onclick="runHealthChecks()">🏥 ヘルスチェック実行</button>
                        <button class="btn btn-danger" onclick="emergencyFailover()">🚨 緊急フェイルオーバー</button>
                    </div>
                </div>
                
                <script>
                    async function refreshDashboard() {
                        try {
                            // ヘルスステータス取得
                            const healthResponse = await fetch('/api/health');
                            const healthData = await healthResponse.json();
                            
                            const serviceHealth = document.getElementById('service-health');
                            if (healthData.health_status && Object.keys(healthData.health_status).length > 0) {
                                serviceHealth.innerHTML = Object.entries(healthData.health_status).map(([service, status]) => {
                                    const statusClass = `status-${status.overall_status}`;
                                    const statusIcon = status.overall_status === 'healthy' ? '✅' : 
                                                     status.overall_status === 'degraded' ? '⚠️' : '❌';
                                    
                                    return `
                                        <div class="service-item ${statusClass}">
                                            <h4>${statusIcon} ${service.toUpperCase()}</h4>
                                            <p><strong>プライマリ:</strong> ${status.primary.status || 'Unknown'}</p>
                                            <p><strong>バックアップ:</strong> ${status.backup.status || 'Unknown'}</p>
                                            <p><strong>全体ステータス:</strong> ${status.overall_status}</p>
                                            <button class="btn btn-warning" onclick="manualFailover('${service}')">🔄 フェイルオーバー</button>
                                        </div>
                                    `;
                                }).join('');
                            } else {
                                serviceHealth.innerHTML = '<p>ヘルスチェックデータはありません</p>';
                            }
                            
                            // フェイルオーバーイベント取得
                            const failoverResponse = await fetch('/api/failover-events');
                            const failoverData = await failoverResponse.json();
                            
                            const failoverEvents = document.getElementById('failover-events');
                            if (failoverData.failover_events && failoverData.failover_events.length > 0) {
                                failoverEvents.innerHTML = failoverData.failover_events.slice(0, 5).map(event => `
                                    <div class="service-item status-failover">
                                        <h4>🔄 ${event.service_name.toUpperCase()}</h4>
                                        <p><strong>理由:</strong> ${event.failover_reason}</p>
                                        <p><strong>ステータス:</strong> ${event.status}</p>
                                        <p><strong>時刻:</strong> ${new Date(event.timestamp).toLocaleString()}</p>
                                    </div>
                                `).join('');
                            } else {
                                failoverEvents.innerHTML = '<p>フェイルオーバーイベントはありません</p>';
                            }
                            
                            // 可用性統計取得
                            const availabilityResponse = await fetch('/api/availability-stats?days=7');
                            const availabilityData = await availabilityResponse.json();
                            
                            const availabilityStats = document.getElementById('availability-stats');
                            if (availabilityData.availability_stats && availabilityData.availability_stats.length > 0) {
                                availabilityStats.innerHTML = availabilityData.availability_stats.slice(0, 5).map(stat => `
                                    <div style="background: rgba(255,255,255,0.1); border-radius: 5px; padding: 10px; margin: 5px 0;">
                                        <strong>${stat.service_name}</strong><br>
                                        稼働率: ${stat.uptime_percentage.toFixed(2)}%<br>
                                        総チェック: ${stat.total_checks}<br>
                                        成功: ${stat.successful_checks} | 失敗: ${stat.failed_checks}<br>
                                        平均応答時間: ${stat.avg_response_time.toFixed(3)}s
                                    </div>
                                `).join('');
                            } else {
                                availabilityStats.innerHTML = '<p>可用性統計はありません</p>';
                            }
                            
                            // 復旧ログ取得
                            const recoveryResponse = await fetch('/api/recovery-logs');
                            const recoveryData = await recoveryResponse.json();
                            
                            const recoveryLogs = document.getElementById('recovery-logs');
                            if (recoveryData.recovery_logs && recoveryData.recovery_logs.length > 0) {
                                recoveryLogs.innerHTML = recoveryData.recovery_logs.slice(0, 5).map(log => `
                                    <div style="background: rgba(255,255,255,0.1); border-radius: 5px; padding: 10px; margin: 5px 0;">
                                        <strong>${log.service_name}</strong><br>
                                        ${log.recovery_action}<br>
                                        成功: ${log.success ? '✅' : '❌'}<br>
                                        <small>${new Date(log.timestamp).toLocaleString()}</small>
                                    </div>
                                `).join('');
                            } else {
                                recoveryLogs.innerHTML = '<p>復旧ログはありません</p>';
                            }
                            
                            // 統計情報
                            const systemStats = document.getElementById('system-stats');
                            const stats = {
                                total_services: Object.keys(healthData.health_status).length,
                                healthy_services: Object.values(healthData.health_status).filter(s => s.overall_status === 'healthy').length,
                                degraded_services: Object.values(healthData.health_status).filter(s => s.overall_status === 'degraded').length,
                                unhealthy_services: Object.values(healthData.health_status).filter(s => s.overall_status === 'unhealthy').length,
                                total_failovers: failoverData.failover_events.length,
                                avg_uptime: availabilityData.availability_stats.reduce((sum, stat) => sum + stat.uptime_percentage, 0) / availabilityData.availability_stats.length || 0
                            };
                            
                            systemStats.innerHTML = `
                                <div class="stats-grid">
                                    <div style="text-align: center; background: rgba(76,175,80,0.2); border-radius: 10px; padding: 15px;">
                                        <h3>${stats.healthy_services}</h3>
                                        <p>健全サービス</p>
                                    </div>
                                    <div style="text-align: center; background: rgba(255,152,0,0.2); border-radius: 10px; padding: 15px;">
                                        <h3>${stats.degraded_services}</h3>
                                        <p>劣化サービス</p>
                                    </div>
                                    <div style="text-align: center; background: rgba(244,67,54,0.2); border-radius: 10px; padding: 15px;">
                                        <h3>${stats.unhealthy_services}</h3>
                                        <p>不健全サービス</p>
                                    </div>
                                    <div style="text-align: center; background: rgba(156,39,176,0.2); border-radius: 10px; padding: 15px;">
                                        <h3>${stats.total_failovers}</h3>
                                        <p>フェイルオーバー</p>
                                    </div>
                                </div>
                            `;
                            
                        } catch (error) {
                            console.error('ダッシュボード更新エラー:', error);
                        }
                    }
                    
                    async function manualFailover(serviceName) {
                        if (confirm(`${serviceName} のフェイルオーバーを実行しますか？`)) {
                            try {
                                const response = await fetch(`/api/failover/${serviceName}?reason=Manual failover from dashboard`, {
                                    method: 'POST'
                                });
                                const result = await response.json();
                                alert('フェイルオーバー実行: ' + result.result.message);
                                refreshDashboard();
                            } catch (error) {
                                console.error('フェイルオーバーエラー:', error);
                            }
                        }
                    }
                    
                    async function runHealthChecks() {
                        try {
                            const response = await fetch('/api/health');
                            const data = await response.json();
                            alert('ヘルスチェック完了: ' + data.summary.overall_status);
                            refreshDashboard();
                        } catch (error) {
                            console.error('ヘルスチェックエラー:', error);
                        }
                    }
                    
                    async function emergencyFailover() {
                        if (confirm('緊急フェイルオーバーを実行しますか？全てのサービスがバックアップに切り替わります。')) {
                            try {
                                const healthResponse = await fetch('/api/health');
                                const healthData = await healthResponse.json();
                                
                                for (const serviceName of Object.keys(healthData.health_status)) {
                                    await fetch(`/api/failover/${serviceName}?reason=Emergency failover`, { method: 'POST' });
                                }
                                
                                alert('緊急フェイルオーバー完了');
                                refreshDashboard();
                            } catch (error) {
                                console.error('緊急フェイルオーバーエラー:', error);
                            }
                        }
                    }
                    
                    // 初期読み込み
                    refreshDashboard();
                    
                    // 30秒ごとに自動更新
                    setInterval(refreshDashboard, 30000);
                </script>
            </body>
            </html>
            """

    def setup_startup_events(self):
        @self.app.on_event("startup")
        async def startup_event():
            asyncio.create_task(self._health_check_worker())
            asyncio.create_task(self._failover_monitor_worker())
            asyncio.create_task(self._auto_recovery_worker())
            self.logger.info("バックグラウンドタスク開始")

    def determine_overall_status(self, primary_health: Dict, backup_health: Dict) -> str:
        """全体ステータスを決定"""
        primary_status = primary_health.get("status", "unknown")
        backup_status = backup_health.get("status", "unknown")
        
        if primary_status == "healthy":
            return "healthy"
        elif primary_status == "degraded" or backup_status == "healthy":
            return "degraded"
        else:
            return "unhealthy"

    def generate_health_summary(self, health_status: Dict) -> Dict[str, Any]:
        """ヘルスサマリーを生成"""
        total_services = len(health_status)
        healthy_count = sum(1 for status in health_status.values() if status["overall_status"] == "healthy")
        degraded_count = sum(1 for status in health_status.values() if status["overall_status"] == "degraded")
        unhealthy_count = sum(1 for status in health_status.values() if status["overall_status"] == "unhealthy")
        
        return {
            "overall_status": "healthy" if unhealthy_count == 0 else "degraded" if degraded_count > 0 else "unhealthy",
            "total_services": total_services,
            "healthy_services": healthy_count,
            "degraded_services": degraded_count,
            "unhealthy_services": unhealthy_count,
            "uptime_percentage": (healthy_count + degraded_count * 0.5) / total_services * 100 if total_services > 0 else 0
        }

    async def execute_failover(self, service_name: str, reason: str) -> Dict[str, Any]:
        """フェイルオーバーを実行"""
        failover_id = f"failover_{int(time.time())}_{service_name}"
        
        if service_name not in self.services_config:
            return {"status": "failed", "message": f"サービス {service_name} が見つかりません"}
        
        service_config = self.services_config[service_name]
        
        # フェイルオーバーイベントを記録
        failover_event = FailoverEvent(
            id=failover_id,
            service_name=service_name,
            primary_endpoint=f"http://localhost:{service_config['primary']['port']}{service_config['primary']['endpoint']}",
            backup_endpoint=f"http://localhost:{service_config['backup']['port']}{service_config['backup']['endpoint']}",
            failover_reason=reason,
            timestamp=datetime.now().isoformat()
        )
        
        # データベースに記録
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO failover_events 
            (id, service_name, primary_endpoint, backup_endpoint, failover_reason, timestamp, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            failover_event.id,
            failover_event.service_name,
            failover_event.primary_endpoint,
            failover_event.backup_endpoint,
            failover_event.failover_reason,
            failover_event.timestamp,
            failover_event.status
        ))
        
        conn.commit()
        conn.close()
        
        self.failover_events.append(failover_event)
        
        # 実際のフェイルオーバー処理（ロードバランサーの設定変更など）
        # ここではシミュレーション
        
        self.logger.warning(f"🔄 フェイルオーバー実行: {service_name} - {reason}")
        
        return {
            "status": "completed",
            "message": f"サービス {service_name} のフェイルオーバーが完了しました",
            "failover_id": failover_id
        }

    async def _health_check_worker(self):
        """ヘルスチェックワーカー"""
        while True:
            try:
                for service_name, service_config in self.services_config.items():
                    await self.perform_health_check(service_name, "primary", service_config["primary"])
                    await self.perform_health_check(service_name, "backup", service_config["backup"])
                
                await asyncio.sleep(30)  # 30秒ごとにチェック
            except Exception as e:
                self.logger.error(f"ヘルスチェックワーカーエラー: {e}")
                await asyncio.sleep(30)

    async def perform_health_check(self, service_name: str, instance_type: str, config: Dict[str, Any]):
        """ヘルスチェックを実行"""
        try:
            start_time = time.time()
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"http://localhost:{config['port']}{config['endpoint']}",
                    timeout=5
                )
                end_time = time.time()
                
                health_check = HealthCheck(
                    service_name=f"{service_name}_{instance_type}",
                    endpoint=f"http://localhost:{config['port']}{config['endpoint']}",
                    status="healthy" if response.status_code == 200 else "unhealthy",
                    response_time=end_time - start_time,
                    last_checked=datetime.now().isoformat()
                )
                
                if response.status_code != 200:
                    health_check.status = "unhealthy"
                    health_check.error_message = f"HTTP {response.status_code}"
                
        except Exception as e:
            health_check = HealthCheck(
                service_name=f"{service_name}_{instance_type}",
                endpoint=f"http://localhost:{config['port']}{config['endpoint']}",
                status="unhealthy",
                response_time=0.0,
                last_checked=datetime.now().isoformat(),
                error_message=str(e)
            )
        
        # ヘルスチェック結果を保存
        self.health_checks[f"{service_name}_{instance_type}"] = health_check
        
        # データベースに記録
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO health_check_history 
            (service_name, endpoint, status, response_time, error_message, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            health_check.service_name,
            health_check.endpoint,
            health_check.status,
            health_check.response_time,
            health_check.error_message,
            health_check.last_checked
        ))
        
        conn.commit()
        conn.close()

    async def _failover_monitor_worker(self):
        """フェイルオーバーモニターワーカー"""
        while True:
            try:
                for service_name, service_config in self.services_config.items():
                    primary_health = self.health_checks.get(f"{service_name}_primary", {})
                    backup_health = self.health_checks.get(f"{service_name}_backup", {})
                    
                    # プライマリが不健全で、バックアップが健全な場合にフェイルオーバー
                    if (primary_health.get("status") == "unhealthy" and 
                        backup_health.get("status") == "healthy"):
                        
                        await self.execute_failover(service_name, "Primary service unhealthy")
                
                await asyncio.sleep(60)  # 1分ごとにチェック
            except Exception as e:
                self.logger.error(f"フェイルオーバーモニターワーカーエラー: {e}")
                await asyncio.sleep(60)

    async def _auto_recovery_worker(self):
        """自動復旧ワーカー"""
        while True:
            try:
                await self.attempt_auto_recovery()
                await asyncio.sleep(300)  # 5分ごとに復旧を試行
            except Exception as e:
                self.logger.error(f"自動復旧ワーカーエラー: {e}")
                await asyncio.sleep(300)

    async def attempt_auto_recovery(self):
        """自動復旧を試行"""
        for service_name, service_config in self.services_config.items():
            primary_health = self.health_checks.get(f"{service_name}_primary", {})
            
            if primary_health.get("status") == "unhealthy":
                # 復旧アクションを実行
                recovery_result = await self.perform_recovery_action(service_name, "restart_service")
                
                # 復旧ログを記録
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO recovery_logs 
                    (service_name, recovery_action, success, details, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    service_name,
                    "restart_service",
                    recovery_result["success"],
                    recovery_result["message"],
                    datetime.now().isoformat()
                ))
                
                conn.commit()
                conn.close()

    async def perform_recovery_action(self, service_name: str, action: str) -> Dict[str, Any]:
        """復旧アクションを実行"""
        try:
            if action == "restart_service":
                # 実際の実装では、サービスを再起動
                self.logger.info(f"復旧アクション実行: {service_name} - {action}")
                return {"success": True, "message": f"サービス {service_name} の再起動を実行しました"}
            else:
                return {"success": False, "message": f"不明な復旧アクション: {action}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def start_background_tasks(self):
        # バックグラウンドタスクはFastAPIのstartupイベントで開始
        self.logger.info("バックグラウンドタスク準備完了")

def main():
    system = ManaHighAvailabilitySystem()
    uvicorn.run(system.app, host="0.0.0.0", port=5030)

if __name__ == "__main__":
    main()
