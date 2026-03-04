import asyncio
import json
import logging
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import httpx
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

class LogEntry(BaseModel):
    timestamp: str
    system: str
    level: str
    message: str
    details: Optional[Dict[str, Any]] = None

class SystemMetrics(BaseModel):
    system: str
    cpu_usage: float
    memory_usage: float
    response_time: float
    status: str
    last_checked: str

class ManaCentralizedMonitoringSystem:
    def __init__(self):
        self.app = FastAPI(title="Mana Centralized Monitoring System", version="1.0.0")
        self.db_path = "/root/mana_centralized_monitoring.db"
        self.logger = logger
        self.systems_config = self.load_systems_config()
        self.init_database()
        self.setup_api()
        self.setup_startup_events()
        self.start_background_tasks()
        self.logger.info("🚀 Mana Centralized Monitoring System 初期化完了")

    def load_systems_config(self) -> Dict[str, Any]:
        return {
            "trinity": {"port": 5005, "name": "Trinity ManaOS Integration"},
            "optimized": {"port": 5009, "name": "Mana Optimized Integration"},
            "ai": {"port": 5010, "name": "Mana Enhanced AI Integration"},
            "workflow": {"port": 5011, "name": "Mana Workflow Integration"},
            "monitoring": {"port": 5012, "name": "Mana Ultimate Monitoring"},
            "security": {"port": 5013, "name": "Mana Security System"},
            "scalability": {"port": 5014, "name": "Mana Scalability System"},
            "orchestrator": {"port": 5015, "name": "Mana Automation Orchestrator"},
            "learning": {"port": 5016, "name": "Mana Learning Automation"},
            "predictive": {"port": 5017, "name": "Mana Predictive Maintenance"},
            "dynamic_scaling": {"port": 5018, "name": "Mana Dynamic Scaling"},
            "security_auto": {"port": 5019, "name": "Mana Security Auto Response"},
            "multiagent": {"port": 5020, "name": "Mana Multi-Agent Coordination"},
            "timeseries": {"port": 5021, "name": "Mana Time Series Prediction"},
            "realtime": {"port": 5022, "name": "Mana Real-time Decision"},
            "self_healing": {"port": 5023, "name": "Mana Self-Healing"},
            "manaos": {"port": 5024, "name": "ManaOS Ultimate Integration"}
        }

    def init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # ログテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                system TEXT NOT NULL,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                details TEXT
            )
        """)
        
        # メトリクステーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                system TEXT NOT NULL,
                cpu_usage REAL,
                memory_usage REAL,
                response_time REAL,
                status TEXT
            )
        """)
        
        # アラートテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                system TEXT NOT NULL,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                resolved BOOLEAN DEFAULT FALSE
            )
        """)
        
        conn.commit()
        conn.close()
        self.logger.info("データベース初期化完了")

    def setup_api(self):
        @self.app.get("/api/status", summary="監視システムのステータス")
        async def get_status():
            return {
                "timestamp": datetime.now().isoformat(),
                "system": "Mana Centralized Monitoring System",
                "status": "healthy",
                "version": self.app.version,
                "monitored_systems": len(self.systems_config)
            }

        @self.app.get("/api/dashboard", summary="統合ダッシュボード")
        async def get_dashboard():
            dashboard_data = {
                "timestamp": datetime.now().isoformat(),
                "systems": {},
                "alerts": [],
                "metrics": {}
            }
            
            # 各システムのステータス取得
            for sys_id, sys_config in self.systems_config.items():
                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.get(f"http://localhost:{sys_config['port']}/api/status", timeout=5)
                        response.raise_for_status()
                        dashboard_data["systems"][sys_id] = {
                            "name": sys_config["name"],
                            "status": "healthy",
                            "port": sys_config["port"],
                            "response_time": response.elapsed.total_seconds()
                        }
                except Exception as e:
                    dashboard_data["systems"][sys_id] = {
                        "name": sys_config["name"],
                        "status": "unhealthy",
                        "port": sys_config["port"],
                        "error": str(e)
                    }
            
            # アラート取得
            dashboard_data["alerts"] = self.get_recent_alerts()
            
            # メトリクス取得
            dashboard_data["metrics"] = self.get_system_metrics()
            
            return dashboard_data

        @self.app.get("/api/logs", summary="システムログ取得")
        async def get_logs(system: Optional[str] = None, limit: int = 100):
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if system:
                cursor.execute("""
                    SELECT timestamp, system, level, message, details 
                    FROM system_logs 
                    WHERE system = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, (system, limit))
            else:
                cursor.execute("""
                    SELECT timestamp, system, level, message, details 
                    FROM system_logs 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, (limit,))
            
            logs = []
            for row in cursor.fetchall():
                logs.append({
                    "timestamp": row[0],
                    "system": row[1],
                    "level": row[2],
                    "message": row[3],
                    "details": json.loads(row[4]) if row[4] else None
                })
            
            conn.close()
            return {"logs": logs, "count": len(logs)}

        @self.app.get("/api/metrics", summary="システムメトリクス取得")
        async def get_metrics(system: Optional[str] = None, hours: int = 24):
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            since_time = (datetime.now() - timedelta(hours=hours)).isoformat()
            
            if system:
                cursor.execute("""
                    SELECT timestamp, system, cpu_usage, memory_usage, response_time, status
                    FROM system_metrics 
                    WHERE system = ? AND timestamp > ?
                    ORDER BY timestamp DESC
                """, (system, since_time))
            else:
                cursor.execute("""
                    SELECT timestamp, system, cpu_usage, memory_usage, response_time, status
                    FROM system_metrics 
                    WHERE timestamp > ?
                    ORDER BY timestamp DESC
                """, (since_time,))
            
            metrics = []
            for row in cursor.fetchall():
                metrics.append({
                    "timestamp": row[0],
                    "system": row[1],
                    "cpu_usage": row[2],
                    "memory_usage": row[3],
                    "response_time": row[4],
                    "status": row[5]
                })
            
            conn.close()
            return {"metrics": metrics, "count": len(metrics)}

        @self.app.get("/api/alerts", summary="アラート取得")
        async def get_alerts(resolved: bool = False):
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT timestamp, system, level, message, resolved
                FROM alerts 
                WHERE resolved = ?
                ORDER BY timestamp DESC
            """, (resolved,))
            
            alerts = []
            for row in cursor.fetchall():
                alerts.append({
                    "timestamp": row[0],
                    "system": row[1],
                    "level": row[2],
                    "message": row[3],
                    "resolved": bool(row[4])
                })
            
            conn.close()
            return {"alerts": alerts, "count": len(alerts)}

        @self.app.post("/api/logs", summary="ログエントリ追加")
        async def add_log_entry(log_entry: LogEntry):
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO system_logs (timestamp, system, level, message, details)
                VALUES (?, ?, ?, ?, ?)
            """, (
                log_entry.timestamp,
                log_entry.system,
                log_entry.level,
                log_entry.message,
                json.dumps(log_entry.details) if log_entry.details else None
            ))
            
            conn.commit()
            conn.close()
            
            # エラーレベルのログはアラートとして記録
            if log_entry.level in ["ERROR", "CRITICAL"]:
                self.create_alert(log_entry.system, log_entry.level, log_entry.message)
            
            return {"status": "success", "message": "ログエントリが追加されました"}

        @self.app.get("/", summary="監視ダッシュボード")
        async def dashboard():
            return """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Mana Centralized Monitoring Dashboard</title>
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
                    .status-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }
                    .status-item { background: rgba(255,255,255,0.1); border-radius: 10px; padding: 15px; text-align: center; }
                    .status-healthy { border-left: 4px solid #4CAF50; }
                    .status-unhealthy { border-left: 4px solid #f44336; }
                    .metrics-chart { background: rgba(255,255,255,0.1); border-radius: 10px; padding: 20px; margin-top: 20px; }
                    .refresh-btn { background: #4CAF50; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; font-size: 16px; }
                    .refresh-btn:hover { background: #45a049; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🚀 Mana Centralized Monitoring Dashboard</h1>
                        <p>全19システムの統合監視・ログ管理システム</p>
                    </div>
                    
                    <div class="dashboard-grid">
                        <div class="card">
                            <h3>📊 システムステータス</h3>
                            <div id="systems-status" class="status-grid"></div>
                        </div>
                        
                        <div class="card">
                            <h3>🚨 最近のアラート</h3>
                            <div id="recent-alerts"></div>
                        </div>
                        
                        <div class="card">
                            <h3>📈 システムメトリクス</h3>
                            <div id="system-metrics"></div>
                        </div>
                    </div>
                    
                    <div class="card">
                        <h3>📋 最近のログ</h3>
                        <div id="recent-logs"></div>
                    </div>
                    
                    <div style="text-align: center; margin-top: 30px;">
                        <button class="refresh-btn" onclick="refreshDashboard()">🔄 ダッシュボード更新</button>
                    </div>
                </div>
                
                <script>
                    async function refreshDashboard() {
                        try {
                            const response = await fetch('/api/dashboard');
                            const data = await response.json();
                            
                            // システムステータス更新
                            const systemsStatus = document.getElementById('systems-status');
                            systemsStatus.innerHTML = '';
                            
                            for (const [sysId, sysData] of Object.entries(data.systems)) {
                                const statusClass = sysData.status === 'healthy' ? 'status-healthy' : 'status-unhealthy';
                                const statusIcon = sysData.status === 'healthy' ? '✅' : '❌';
                                
                                systemsStatus.innerHTML += `
                                    <div class="status-item ${statusClass}">
                                        <h4>${statusIcon} ${sysData.name}</h4>
                                        <p>ポート: ${sysData.port}</p>
                                        <p>ステータス: ${sysData.status}</p>
                                        ${sysData.response_time ? `<p>応答時間: ${sysData.response_time.toFixed(3)}s</p>` : ''}
                                    </div>
                                `;
                            }
                            
                            // アラート更新
                            const recentAlerts = document.getElementById('recent-alerts');
                            if (data.alerts && data.alerts.length > 0) {
                                recentAlerts.innerHTML = data.alerts.slice(0, 5).map(alert => `
                                    <div style="background: rgba(244,67,54,0.2); border-radius: 5px; padding: 10px; margin: 5px 0;">
                                        <strong>${alert.level}</strong> - ${alert.system}<br>
                                        ${alert.message}<br>
                                        <small>${new Date(alert.timestamp).toLocaleString()}</small>
                                    </div>
                                `).join('');
                            } else {
                                recentAlerts.innerHTML = '<p>アラートなし</p>';
                            }
                            
                            // メトリクス更新
                            const systemMetrics = document.getElementById('system-metrics');
                            if (data.metrics && Object.keys(data.metrics).length > 0) {
                                systemMetrics.innerHTML = Object.entries(data.metrics).map(([sys, metrics]) => `
                                    <div style="background: rgba(255,255,255,0.1); border-radius: 5px; padding: 10px; margin: 5px 0;">
                                        <strong>${sys}</strong><br>
                                        CPU: ${metrics.cpu_usage?.toFixed(1) || 'N/A'}%<br>
                                        メモリ: ${metrics.memory_usage?.toFixed(1) || 'N/A'}%<br>
                                        応答時間: ${metrics.response_time?.toFixed(3) || 'N/A'}s
                                    </div>
                                `).join('');
                            } else {
                                systemMetrics.innerHTML = '<p>メトリクスデータなし</p>';
                            }
                            
                        } catch (error) {
                            console.error('ダッシュボード更新エラー:', error);
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
            asyncio.create_task(self._metrics_collection_worker())
            self.logger.info("バックグラウンドタスク開始")

    def get_recent_alerts(self, limit: int = 10) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT timestamp, system, level, message
            FROM alerts 
            WHERE resolved = FALSE
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (limit,))
        
        alerts = []
        for row in cursor.fetchall():
            alerts.append({
                "timestamp": row[0],
                "system": row[1],
                "level": row[2],
                "message": row[3]
            })
        
        conn.close()
        return alerts

    def get_system_metrics(self) -> Dict[str, Any]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT system, AVG(cpu_usage), AVG(memory_usage), AVG(response_time)
            FROM system_metrics 
            WHERE timestamp > datetime('now', '-1 hour')
            GROUP BY system
        """)
        
        metrics = {}
        for row in cursor.fetchall():
            metrics[row[0]] = {
                "cpu_usage": row[1],
                "memory_usage": row[2],
                "response_time": row[3]
            }
        
        conn.close()
        return metrics

    def create_alert(self, system: str, level: str, message: str):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO alerts (timestamp, system, level, message)
            VALUES (?, ?, ?, ?)
        """, (datetime.now().isoformat(), system, level, message))
        
        conn.commit()
        conn.close()
        
        self.logger.warning(f"🚨 アラート作成: {system} - {level} - {message}")

    async def _metrics_collection_worker(self):
        while True:
            try:
                for sys_id, sys_config in self.systems_config.items():
                    try:
                        async with httpx.AsyncClient() as client:
                            start_time = time.time()
                            response = await client.get(f"http://localhost:{sys_config['port']}/api/status", timeout=5)
                            end_time = time.time()
                            
                            if response.status_code == 200:
                                # メトリクスをデータベースに保存
                                conn = sqlite3.connect(self.db_path)
                                cursor = conn.cursor()
                                
                                cursor.execute("""
                                    INSERT INTO system_metrics (timestamp, system, cpu_usage, memory_usage, response_time, status)
                                    VALUES (?, ?, ?, ?, ?, ?)
                                """, (
                                    datetime.now().isoformat(),
                                    sys_id,
                                    0.0,  # CPU使用率（実際の実装ではpsutil等を使用）
                                    0.0,  # メモリ使用率
                                    end_time - start_time,
                                    "healthy"
                                ))
                                
                                conn.commit()
                                conn.close()
                                
                    except Exception as e:
                        self.logger.error(f"メトリクス収集エラー {sys_id}: {e}")
                        
            except Exception as e:
                self.logger.error(f"メトリクス収集ワーカーエラー: {e}")
            
            await asyncio.sleep(30)  # 30秒ごとに収集

    def start_background_tasks(self):
        # バックグラウンドタスクはFastAPIのstartupイベントで開始
        self.logger.info("バックグラウンドタスク準備完了")

def main():
    system = ManaCentralizedMonitoringSystem()
    uvicorn.run(system.app, host="0.0.0.0", port=5025)

if __name__ == "__main__":
    main()
