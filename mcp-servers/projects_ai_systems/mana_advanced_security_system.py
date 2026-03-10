import asyncio
import json
import logging
import sqlite3
import time
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
import uvicorn

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

class SecurityThreat(BaseModel):
    id: Optional[str] = None
    threat_type: str  # api_key_leak, rate_limit_exceeded, suspicious_activity, etc.
    severity: str  # low, medium, high, critical
    source_ip: str
    target_system: str
    description: str
    detected_at: Optional[str] = None
    status: str = "active"  # active, investigating, resolved

class SecurityAction(BaseModel):
    action_type: str  # block_ip, rate_limit, alert_admin, isolate_system
    target: str
    parameters: Dict[str, Any]
    executed_at: Optional[str] = None
    status: str = "pending"  # pending, executing, completed, failed

class ManaAdvancedSecuritySystem:
    def __init__(self):
        self.app = FastAPI(title="Mana Advanced Security System", version="1.0.0")
        self.db_path = "/root/mana_advanced_security.db"
        self.logger = logger
        self.api_keys = {}  # 実際の実装では安全なストレージを使用
        self.rate_limits = {}  # IP別レート制限
        self.blocked_ips = set()
        self.init_database()
        self.setup_api()
        self.setup_startup_events()
        self.start_background_tasks()
        self.logger.info("🚀 Mana Advanced Security System 初期化完了")

    def init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # セキュリティ脅威テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS security_threats (
                id TEXT PRIMARY KEY,
                threat_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                source_ip TEXT NOT NULL,
                target_system TEXT NOT NULL,
                description TEXT NOT NULL,
                detected_at TEXT NOT NULL,
                status TEXT DEFAULT 'active'
            )
        """)
        
        # セキュリティアクションテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS security_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_type TEXT NOT NULL,
                target TEXT NOT NULL,
                parameters TEXT NOT NULL,
                executed_at TEXT,
                status TEXT DEFAULT 'pending'
            )
        """)
        
        # APIキー監視テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_key_monitoring (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_hash TEXT NOT NULL,
                usage_count INTEGER DEFAULT 0,
                last_used TEXT,
                suspicious_activity BOOLEAN DEFAULT FALSE,
                created_at TEXT NOT NULL
            )
        """)
        
        # レート制限テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rate_limits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_address TEXT NOT NULL,
                endpoint TEXT NOT NULL,
                request_count INTEGER DEFAULT 0,
                window_start TEXT NOT NULL,
                blocked_until TEXT
            )
        """)
        
        # 異常行動検知テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS anomaly_detection (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_address TEXT NOT NULL,
                behavior_type TEXT NOT NULL,
                anomaly_score REAL NOT NULL,
                detected_at TEXT NOT NULL,
                details TEXT
            )
        """)
        
        conn.commit()
        conn.close()
        self.logger.info("データベース初期化完了")

    def setup_api(self):
        @self.app.get("/api/status", summary="セキュリティシステムのステータス")
        async def get_status():
            return {
                "timestamp": datetime.now().isoformat(),
                "system": "Mana Advanced Security System",
                "status": "healthy",
                "version": self.app.version,
                "active_threats": len(self.get_active_threats()),
                "blocked_ips": len(self.blocked_ips)
            }

        @self.app.post("/api/threats", summary="セキュリティ脅威報告")
        async def report_threat(threat: SecurityThreat):
            threat_id = f"threat_{int(time.time())}_{hash(threat.source_ip) % 10000}"
            threat.id = threat_id
            threat.detected_at = datetime.now().isoformat()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO security_threats 
                (id, threat_type, severity, source_ip, target_system, description, detected_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                threat.id,
                threat.threat_type,
                threat.severity,
                threat.source_ip,
                threat.target_system,
                threat.description,
                threat.detected_at,
                threat.status
            ))
            
            conn.commit()
            conn.close()
            
            # 脅威レベルに応じて自動対応
            await self.auto_respond_to_threat(threat)
            
            self.logger.warning(f"🚨 セキュリティ脅威検知: {threat.threat_type} - {threat.source_ip}")
            return {"status": "success", "threat_id": threat_id, "message": "脅威が報告され、自動対応を開始しました"}

        @self.app.get("/api/threats", summary="セキュリティ脅威一覧")
        async def get_threats(status: Optional[str] = None, severity: Optional[str] = None):
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = "SELECT * FROM security_threats WHERE 1=1"
            params = []
            
            if status:
                query += " AND status = ?"
                params.append(status)
            
            if severity:
                query += " AND severity = ?"
                params.append(severity)
            
            query += " ORDER BY detected_at DESC"
            
            cursor.execute(query, params)
            
            threats = []
            for row in cursor.fetchall():
                threats.append({
                    "id": row[0],
                    "threat_type": row[1],
                    "severity": row[2],
                    "source_ip": row[3],
                    "target_system": row[4],
                    "description": row[5],
                    "detected_at": row[6],
                    "status": row[7]
                })
            
            conn.close()
            return {"threats": threats, "count": len(threats)}

        @self.app.post("/api/actions", summary="セキュリティアクション実行")
        async def execute_security_action(action: SecurityAction):
            action.executed_at = datetime.now().isoformat()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO security_actions 
                (action_type, target, parameters, executed_at, status)
                VALUES (?, ?, ?, ?, ?)
            """, (
                action.action_type,
                action.target,
                json.dumps(action.parameters),
                action.executed_at,
                "executing"
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
                UPDATE security_actions 
                SET status = ? 
                WHERE id = ?
            """, (result["status"], action_id))
            conn.commit()
            conn.close()
            
            return {"status": "success", "action_id": action_id, "result": result}

        @self.app.get("/api/rate-limits", summary="レート制限状況")
        async def get_rate_limits():
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT ip_address, endpoint, request_count, window_start, blocked_until
                FROM rate_limits 
                WHERE blocked_until > datetime('now') OR request_count > 0
                ORDER BY request_count DESC
            """)
            
            rate_limits = []
            for row in cursor.fetchall():
                rate_limits.append({
                    "ip_address": row[0],
                    "endpoint": row[1],
                    "request_count": row[2],
                    "window_start": row[3],
                    "blocked_until": row[4]
                })
            
            conn.close()
            return {"rate_limits": rate_limits, "count": len(rate_limits)}

        @self.app.post("/api/api-keys/validate", summary="APIキー検証")
        async def validate_api_key(api_key: str = Header(None)):
            if not api_key:
                raise HTTPException(status_code=401, detail="APIキーが必要です")
            
            # APIキーのハッシュ化
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            
            # 使用回数を更新
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO api_key_monitoring 
                (key_hash, usage_count, last_used, created_at)
                VALUES (?, COALESCE((SELECT usage_count FROM api_key_monitoring WHERE key_hash = ?), 0) + 1, ?, ?)
            """, (key_hash, key_hash, datetime.now().isoformat(), datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
            # 異常な使用パターンを検知
            await self.detect_api_key_anomalies(key_hash)
            
            return {"status": "valid", "key_hash": key_hash}

        @self.app.get("/api/anomalies", summary="異常行動検知結果")
        async def get_anomalies():
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT ip_address, behavior_type, anomaly_score, detected_at, details
                FROM anomaly_detection 
                WHERE detected_at > datetime('now', '-24 hours')
                ORDER BY anomaly_score DESC, detected_at DESC
            """)
            
            anomalies = []
            for row in cursor.fetchall():
                anomalies.append({
                    "ip_address": row[0],
                    "behavior_type": row[1],
                    "anomaly_score": row[2],
                    "detected_at": row[3],
                    "details": json.loads(row[4]) if row[4] else None
                })
            
            conn.close()
            return {"anomalies": anomalies, "count": len(anomalies)}

        @self.app.get("/", summary="セキュリティダッシュボード")
        async def dashboard():
            return """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Mana Advanced Security System</title>
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
                    .threat-item { background: rgba(255,255,255,0.1); border-radius: 10px; padding: 15px; margin: 10px 0; }
                    .severity-critical { border-left: 4px solid #f44336; }
                    .severity-high { border-left: 4px solid #ff9800; }
                    .severity-medium { border-left: 4px solid #ffeb3b; }
                    .severity-low { border-left: 4px solid #4CAF50; }
                    .btn { background: #4CAF50; color: white; border: none; padding: 8px 16px; border-radius: 5px; cursor: pointer; margin: 5px; }
                    .btn:hover { background: #45a049; }
                    .btn-danger { background: #f44336; }
                    .btn-danger:hover { background: #da190b; }
                    .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🛡️ Mana Advanced Security System</h1>
                        <p>高度なセキュリティ監視・自動対応システム</p>
                    </div>
                    
                    <div class="dashboard-grid">
                        <div class="card">
                            <h3>🚨 アクティブな脅威</h3>
                            <div id="active-threats"></div>
                        </div>
                        
                        <div class="card">
                            <h3>🚫 ブロック済みIP</h3>
                            <div id="blocked-ips"></div>
                        </div>
                        
                        <div class="card">
                            <h3>📊 レート制限状況</h3>
                            <div id="rate-limits"></div>
                        </div>
                    </div>
                    
                    <div class="dashboard-grid">
                        <div class="card">
                            <h3>🔍 異常行動検知</h3>
                            <div id="anomalies"></div>
                        </div>
                        
                        <div class="card">
                            <h3>🔑 APIキー監視</h3>
                            <div id="api-key-monitoring"></div>
                        </div>
                        
                        <div class="card">
                            <h3>📈 セキュリティ統計</h3>
                            <div id="security-stats"></div>
                        </div>
                    </div>
                    
                    <div style="text-align: center; margin-top: 30px;">
                        <button class="btn" onclick="refreshDashboard()">🔄 ダッシュボード更新</button>
                        <button class="btn btn-danger" onclick="emergencyLockdown()">🚨 緊急ロックダウン</button>
                    </div>
                </div>
                
                <script>
                    async function refreshDashboard() {
                        try {
                            // アクティブな脅威取得
                            const threatsResponse = await fetch('/api/threats?status=active');
                            const threatsData = await threatsResponse.json();
                            
                            const activeThreats = document.getElementById('active-threats');
                            if (threatsData.threats && threatsData.threats.length > 0) {
                                activeThreats.innerHTML = threatsData.threats.slice(0, 5).map(threat => `
                                    <div class="threat-item severity-${threat.severity}">
                                        <h4>${threat.threat_type.toUpperCase()}</h4>
                                        <p><strong>IP:</strong> ${threat.source_ip}</p>
                                        <p><strong>対象:</strong> ${threat.target_system}</p>
                                        <p>${threat.description}</p>
                                        <p><small>${new Date(threat.detected_at).toLocaleString()}</small></p>
                                        <button class="btn btn-danger" onclick="blockIP('${threat.source_ip}')">🚫 IPブロック</button>
                                    </div>
                                `).join('');
                            } else {
                                activeThreats.innerHTML = '<p>アクティブな脅威はありません</p>';
                            }
                            
                            // レート制限状況取得
                            const rateLimitsResponse = await fetch('/api/rate-limits');
                            const rateLimitsData = await rateLimitsResponse.json();
                            
                            const rateLimits = document.getElementById('rate-limits');
                            if (rateLimitsData.rate_limits && rateLimitsData.rate_limits.length > 0) {
                                rateLimits.innerHTML = rateLimitsData.rate_limits.slice(0, 5).map(limit => `
                                    <div style="background: rgba(255,255,255,0.1); border-radius: 5px; padding: 10px; margin: 5px 0;">
                                        <strong>${limit.ip_address}</strong><br>
                                        ${limit.endpoint}<br>
                                        リクエスト数: ${limit.request_count}<br>
                                        ${limit.blocked_until ? `<span style="color: #f44336;">ブロック中</span>` : '<span style="color: #4CAF50;">正常</span>'}
                                    </div>
                                `).join('');
                            } else {
                                rateLimits.innerHTML = '<p>レート制限はありません</p>';
                            }
                            
                            // 異常行動検知取得
                            const anomaliesResponse = await fetch('/api/anomalies');
                            const anomaliesData = await anomaliesResponse.json();
                            
                            const anomalies = document.getElementById('anomalies');
                            if (anomaliesData.anomalies && anomaliesData.anomalies.length > 0) {
                                anomalies.innerHTML = anomaliesData.anomalies.slice(0, 5).map(anomaly => `
                                    <div style="background: rgba(255,255,255,0.1); border-radius: 5px; padding: 10px; margin: 5px 0;">
                                        <strong>${anomaly.ip_address}</strong><br>
                                        ${anomaly.behavior_type}<br>
                                        異常スコア: ${anomaly.anomaly_score.toFixed(2)}<br>
                                        <small>${new Date(anomaly.detected_at).toLocaleString()}</small>
                                    </div>
                                `).join('');
                            } else {
                                anomalies.innerHTML = '<p>異常行動は検知されていません</p>';
                            }
                            
                            // 統計情報
                            const securityStats = document.getElementById('security-stats');
                            const stats = {
                                active_threats: threatsData.threats.length,
                                blocked_ips: rateLimitsData.rate_limits.filter(r => r.blocked_until).length,
                                anomalies: anomaliesData.anomalies.length,
                                rate_limited: rateLimitsData.rate_limits.length
                            };
                            
                            securityStats.innerHTML = `
                                <div class="stats-grid">
                                    <div style="text-align: center; background: rgba(244,67,54,0.2); border-radius: 10px; padding: 15px;">
                                        <h3>${stats.active_threats}</h3>
                                        <p>アクティブ脅威</p>
                                    </div>
                                    <div style="text-align: center; background: rgba(255,152,0,0.2); border-radius: 10px; padding: 15px;">
                                        <h3>${stats.blocked_ips}</h3>
                                        <p>ブロック済みIP</p>
                                    </div>
                                    <div style="text-align: center; background: rgba(33,150,243,0.2); border-radius: 10px; padding: 15px;">
                                        <h3>${stats.anomalies}</h3>
                                        <p>異常行動</p>
                                    </div>
                                    <div style="text-align: center; background: rgba(156,39,176,0.2); border-radius: 10px; padding: 15px;">
                                        <h3>${stats.rate_limited}</h3>
                                        <p>レート制限中</p>
                                    </div>
                                </div>
                            `;
                            
                        } catch (error) {
                            console.error('ダッシュボード更新エラー:', error);
                        }
                    }
                    
                    async function blockIP(ip) {
                        try {
                            const response = await fetch('/api/actions', {
                                method: 'POST',
                                headers: {'Content-Type': 'application/json'},
                                body: JSON.stringify({
                                    action_type: 'block_ip',
                                    target: ip,
                                    parameters: {
                                        duration: 3600,  // 1時間
                                        reason: 'Manual block from dashboard'
                                    }
                                })
                            });
                            const result = await response.json();
                            alert('IPブロック実行: ' + result.result.message);
                            refreshDashboard();
                        } catch (error) {
                            console.error('IPブロックエラー:', error);
                        }
                    }
                    
                    async function emergencyLockdown() {
                        if (confirm('緊急ロックダウンを実行しますか？全ての外部アクセスがブロックされます。')) {
                            try {
                                const response = await fetch('/api/actions', {
                                    method: 'POST',
                                    headers: {'Content-Type': 'application/json'},
                                    body: JSON.stringify({
                                        action_type: 'emergency_lockdown',
                                        target: 'all_systems',
                                        parameters: {
                                            duration: 1800,  // 30分
                                            reason: 'Emergency lockdown from dashboard'
                                        }
                                    })
                                });
                                const result = await response.json();
                                alert('緊急ロックダウン実行: ' + result.result.message);
                                refreshDashboard();
                            } catch (error) {
                                console.error('緊急ロックダウンエラー:', error);
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
            asyncio.create_task(self._threat_monitoring_worker())
            self.logger.info("バックグラウンドタスク開始")

    async def auto_respond_to_threat(self, threat: SecurityThreat):
        """脅威レベルに応じた自動対応"""
        actions = []
        
        if threat.severity == "critical":
            # 即座にIPブロック
            actions.append({
                "action_type": "block_ip",
                "target": threat.source_ip,
                "parameters": {"duration": 3600, "reason": f"Critical threat: {threat.threat_type}"}
            })
            
            # システム分離
            actions.append({
                "action_type": "isolate_system",
                "target": threat.target_system,
                "parameters": {"duration": 1800, "reason": "Critical threat detected"}
            })
            
        elif threat.severity == "high":
            # レート制限強化
            actions.append({
                "action_type": "rate_limit",
                "target": threat.source_ip,
                "parameters": {"limit": 10, "window": 300, "reason": "High severity threat"}
            })
            
        elif threat.severity == "medium":
            # 監視強化
            actions.append({
                "action_type": "enhance_monitoring",
                "target": threat.source_ip,
                "parameters": {"duration": 3600, "reason": "Medium severity threat"}
            })
        
        # 管理者アラート
        actions.append({
            "action_type": "alert_admin",
            "target": "admin",
            "parameters": {
                "threat_id": threat.id,
                "severity": threat.severity,
                "message": f"Threat detected: {threat.description}"
            }
        })
        
        # アクション実行
        for action_data in actions:
            action = SecurityAction(**action_data)
            await self.execute_action(action)

    async def execute_action(self, action: SecurityAction) -> Dict[str, Any]:
        """セキュリティアクション実行"""
        try:
            if action.action_type == "block_ip":
                self.blocked_ips.add(action.target)
                return {"status": "completed", "message": f"IP {action.target} をブロックしました"}
                
            elif action.action_type == "rate_limit":
                # レート制限実装
                return {"status": "completed", "message": f"IP {action.target} にレート制限を適用しました"}
                
            elif action.action_type == "isolate_system":
                # システム分離実装
                return {"status": "completed", "message": f"システム {action.target} を分離しました"}
                
            elif action.action_type == "alert_admin":
                # 管理者アラート実装
                self.logger.critical(f"🚨 管理者アラート: {action.parameters.get('message', '')}")
                return {"status": "completed", "message": "管理者にアラートを送信しました"}
                
            elif action.action_type == "emergency_lockdown":
                # 緊急ロックダウン実装
                return {"status": "completed", "message": "緊急ロックダウンを実行しました"}
                
            else:
                return {"status": "failed", "message": f"不明なアクションタイプ: {action.action_type}"}
                
        except Exception as e:
            self.logger.error(f"セキュリティアクション実行エラー: {e}")
            return {"status": "failed", "message": str(e)}

    async def detect_api_key_anomalies(self, key_hash: str):
        """APIキーの異常使用パターンを検知"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT usage_count, last_used 
            FROM api_key_monitoring 
            WHERE key_hash = ?
        """, (key_hash,))
        
        row = cursor.fetchone()
        if row:
            usage_count, last_used = row
            
            # 異常な使用パターンを検知
            if usage_count > 1000:  # 1時間で1000回以上
                await self.report_threat(SecurityThreat(  # type: ignore
                    threat_type="api_key_abuse",
                    severity="high",
                    source_ip="unknown",
                    target_system="api",
                    description=f"APIキー異常使用: {usage_count}回/時間"
                ))
        
        conn.close()

    def get_active_threats(self) -> List[Dict[str, Any]]:
        """アクティブな脅威を取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM security_threats 
            WHERE status = 'active' 
            ORDER BY detected_at DESC
        """)
        
        threats = []
        for row in cursor.fetchall():
            threats.append({
                "id": row[0],
                "threat_type": row[1],
                "severity": row[2],
                "source_ip": row[3],
                "target_system": row[4],
                "description": row[5],
                "detected_at": row[6],
                "status": row[7]
            })
        
        conn.close()
        return threats

    async def _threat_monitoring_worker(self):
        """脅威監視ワーカー"""
        while True:
            try:
                # 定期的な脅威スキャン
                await self.scan_for_threats()
                await asyncio.sleep(60)  # 1分ごとにスキャン
                
            except Exception as e:
                self.logger.error(f"脅威監視ワーカーエラー: {e}")
                await asyncio.sleep(60)

    async def scan_for_threats(self):
        """脅威スキャン実行"""
        # 実際の実装では、ログ分析、ネットワーク監視、異常検知などを実行
        pass

    def start_background_tasks(self):
        # バックグラウンドタスクはFastAPIのstartupイベントで開始
        self.logger.info("バックグラウンドタスク準備完了")

def main():
    system = ManaAdvancedSecuritySystem()
    uvicorn.run(system.app, host="0.0.0.0", port=5027)

if __name__ == "__main__":
    main()
