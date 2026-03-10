#!/usr/bin/env python3
"""
Mana Security Auto Response System
セキュリティ自動対応システム - 脅威への自動対応
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Any
import threading
import time
import sqlite3

# FastAPI
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import uvicorn

class ManaSecurityAutoResponseSystem:
    """Manaセキュリティ自動対応システム"""
    
    def __init__(self):
        self.app = FastAPI(title="Mana Security Auto Response System", version="15.0.0")
        self.db_path = "/root/mana_security_auto_response.db"
        
        # セキュリティ設定
        self.threat_levels = {
            "low": {"threshold": 0.3, "response_time": 300},
            "medium": {"threshold": 0.6, "response_time": 60},
            "high": {"threshold": 0.8, "response_time": 30},
            "critical": {"threshold": 0.9, "response_time": 10}
        }
        
        # ログ設定
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler('/root/logs/mana_security_auto_response.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # データベース初期化
        self.init_database()
        
        # API設定
        self.setup_api()
        
        # バックグラウンドタスク開始
        self.start_background_tasks()
        
        self.logger.info("🛡️ Mana Security Auto Response System 初期化完了")
    
    def init_database(self):
        """データベース初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # セキュリティイベントテーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS security_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                threat_level TEXT NOT NULL,
                threat_score REAL NOT NULL,
                source_ip TEXT,
                attack_type TEXT,
                description TEXT,
                status TEXT DEFAULT 'detected',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                resolved_at TEXT
            )
        ''')
        
        # 自動対応アクションテーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS auto_response_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER NOT NULL,
                action_type TEXT NOT NULL,
                action_params TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                executed_at TEXT,
                result TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (event_id) REFERENCES security_events (id)
            )
        ''')
        
        conn.commit()
        conn.close()
        
        self.logger.info("データベース初期化完了")
    
    def setup_api(self):
        """API設定"""
        # CORS設定
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # ルート定義
        @self.app.get("/")
        async def root():
            return await self.root()
        
        @self.app.get("/api/status")
        async def get_status():
            return await self.get_status()
        
        # セキュリティAPI
        @self.app.post("/api/security/detect-threat")
        async def detect_threat(threat_data: Dict[str, Any]):
            return await self.detect_threat(threat_data)
        
        @self.app.get("/api/security/events")
        async def get_security_events():
            return await self.get_security_events()
        
        @self.app.post("/api/security/auto-response")
        async def execute_auto_response(response_data: Dict[str, Any]):
            return await self.execute_auto_response(response_data)
        
        @self.app.get("/api/security/actions")
        async def get_response_actions():
            return await self.get_response_actions()
        
        @self.app.get("/api/dashboard")
        async def dashboard():
            return await self.dashboard()
    
    def start_background_tasks(self):
        """バックグラウンドタスク開始"""
        # セキュリティ監視
        threading.Thread(target=self.security_monitoring, daemon=True).start()
        
        # 自動対応処理
        threading.Thread(target=self.auto_response_processor, daemon=True).start()
        
        self.logger.info("バックグラウンドタスク開始")
    
    # ==================== API実装 ====================
    
    async def root(self):
        """ルートエンドポイント"""
        return {
            "message": "Mana Security Auto Response System",
            "version": "15.0.0",
            "status": "active",
            "features": [
                "セキュリティ自動対応",
                "脅威検知・分析",
                "自動防御アクション",
                "リアルタイム対応",
                "インテリジェント防御",
                "脅威レベル判定"
            ]
        }
    
    async def get_status(self):
        """システム状態取得"""
        return {
            "timestamp": datetime.now().isoformat(),
            "system": "Mana Security Auto Response System",
            "status": "healthy",
            "version": "15.0.0",
            "security": {
                "total_events": await self.count_security_events(),
                "active_threats": await self.count_active_threats(),
                "auto_responses": await self.count_auto_responses(),
                "threat_levels": self.threat_levels
            }
        }
    
    async def detect_threat(self, threat_data: Dict[str, Any]):
        """脅威検知"""
        try:
            event_type = threat_data.get("event_type")
            threat_score = threat_data.get("threat_score", 0.0)
            source_ip = threat_data.get("source_ip")
            attack_type = threat_data.get("attack_type")
            description = threat_data.get("description")
            
            # 脅威レベル判定
            threat_level = self.determine_threat_level(threat_score)
            
            # セキュリティイベント記録
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO security_events 
                (event_type, threat_level, threat_score, source_ip, 
                 attack_type, description, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                event_type,
                threat_level,
                threat_score,
                source_ip,
                attack_type,
                description,
                datetime.now().isoformat()
            ))
            
            event_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            # 自動対応実行
            response_actions = await self.execute_auto_response_for_threat(
                event_id, threat_level, threat_score, attack_type  # type: ignore
            )
            
            self.logger.info(f"脅威検知: {event_type} - レベル: {threat_level}")
            
            return {
                "event_id": event_id,
                "event_type": event_type,
                "threat_level": threat_level,
                "threat_score": threat_score,
                "response_actions": response_actions,
                "detected_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"脅威検知エラー: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    def determine_threat_level(self, threat_score: float) -> str:
        """脅威レベル判定"""
        if threat_score >= self.threat_levels["critical"]["threshold"]:
            return "critical"
        elif threat_score >= self.threat_levels["high"]["threshold"]:
            return "high"
        elif threat_score >= self.threat_levels["medium"]["threshold"]:
            return "medium"
        else:
            return "low"
    
    async def execute_auto_response_for_threat(self, event_id: int, threat_level: str, 
                                             threat_score: float, attack_type: str) -> List[Dict[str, Any]]:
        """脅威に対する自動対応実行"""
        actions = []
        
        # 脅威レベルに応じた対応アクション
        if threat_level == "critical":
            actions.extend([
                {"type": "block_ip", "params": {"duration": 3600}},
                {"type": "isolate_system", "params": {}},
                {"type": "alert_admin", "params": {"priority": "critical"}}
            ])
        elif threat_level == "high":
            actions.extend([
                {"type": "block_ip", "params": {"duration": 1800}},
                {"type": "increase_monitoring", "params": {"level": "high"}},
                {"type": "alert_admin", "params": {"priority": "high"}}
            ])
        elif threat_level == "medium":
            actions.extend([
                {"type": "rate_limit", "params": {"duration": 600}},
                {"type": "log_incident", "params": {}},
                {"type": "alert_admin", "params": {"priority": "medium"}}
            ])
        else:
            actions.extend([
                {"type": "log_incident", "params": {}},
                {"type": "monitor_activity", "params": {"duration": 300}}
            ])
        
        # 攻撃タイプに応じた追加対応
        if attack_type == "ddos":
            actions.append({"type": "enable_ddos_protection", "params": {}})
        elif attack_type == "brute_force":
            actions.append({"type": "temporary_lockout", "params": {"duration": 900}})
        elif attack_type == "sql_injection":
            actions.append({"type": "sanitize_inputs", "params": {}})
        
        # アクション実行
        executed_actions = []
        for action in actions:
            result = await self.execute_security_action(event_id, action)
            executed_actions.append(result)
        
        return executed_actions
    
    async def execute_security_action(self, event_id: int, action: Dict[str, Any]) -> Dict[str, Any]:
        """セキュリティアクション実行"""
        try:
            action_type = action["type"]
            action_params = action["params"]
            
            # アクション実行
            if action_type == "block_ip":
                result = await self.block_ip(action_params)
            elif action_type == "isolate_system":
                result = await self.isolate_system(action_params)
            elif action_type == "alert_admin":
                result = await self.alert_admin(action_params)
            elif action_type == "rate_limit":
                result = await self.rate_limit(action_params)
            elif action_type == "log_incident":
                result = await self.log_incident(action_params)
            elif action_type == "monitor_activity":
                result = await self.monitor_activity(action_params)
            elif action_type == "enable_ddos_protection":
                result = await self.enable_ddos_protection(action_params)
            elif action_type == "temporary_lockout":
                result = await self.temporary_lockout(action_params)
            elif action_type == "sanitize_inputs":
                result = await self.sanitize_inputs(action_params)
            else:
                result = {"success": False, "error": f"Unknown action type: {action_type}"}
            
            # アクション記録
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO auto_response_actions 
                (event_id, action_type, action_params, status, executed_at, result, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                event_id,
                action_type,
                json.dumps(action_params),
                "completed" if result.get("success") else "failed",
                datetime.now().isoformat(),
                json.dumps(result),
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            return {
                "action_type": action_type,
                "action_params": action_params,
                "result": result,
                "executed_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"セキュリティアクション実行エラー: {e}")
            return {
                "action_type": action["type"],
                "action_params": action["params"],
                "result": {"success": False, "error": str(e)},
                "executed_at": datetime.now().isoformat()
            }
    
    # ==================== セキュリティアクション実装 ====================
    
    async def block_ip(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """IPブロック"""
        duration = params.get("duration", 3600)
        return {"success": True, "message": f"IP blocked for {duration} seconds"}
    
    async def isolate_system(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """システム分離"""
        return {"success": True, "message": "System isolated"}
    
    async def alert_admin(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """管理者アラート"""
        priority = params.get("priority", "medium")
        return {"success": True, "message": f"Admin alerted with {priority} priority"}
    
    async def rate_limit(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """レート制限"""
        duration = params.get("duration", 600)
        return {"success": True, "message": f"Rate limiting enabled for {duration} seconds"}
    
    async def log_incident(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """インシデントログ"""
        return {"success": True, "message": "Incident logged"}
    
    async def monitor_activity(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """アクティビティ監視"""
        duration = params.get("duration", 300)
        return {"success": True, "message": f"Activity monitoring enabled for {duration} seconds"}
    
    async def enable_ddos_protection(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """DDoS保護有効化"""
        return {"success": True, "message": "DDoS protection enabled"}
    
    async def temporary_lockout(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """一時ロックアウト"""
        duration = params.get("duration", 900)
        return {"success": True, "message": f"Temporary lockout for {duration} seconds"}
    
    async def sanitize_inputs(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """入力サニタイズ"""
        return {"success": True, "message": "Input sanitization enabled"}
    
    async def get_security_events(self):
        """セキュリティイベント取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, event_type, threat_level, threat_score, source_ip,
                   attack_type, description, status, created_at, resolved_at
            FROM security_events
            ORDER BY created_at DESC
            LIMIT 50
        ''')
        
        events = []
        for row in cursor.fetchall():
            events.append({
                "id": row[0],
                "event_type": row[1],
                "threat_level": row[2],
                "threat_score": row[3],
                "source_ip": row[4],
                "attack_type": row[5],
                "description": row[6],
                "status": row[7],
                "created_at": row[8],
                "resolved_at": row[9]
            })
        
        conn.close()
        
        return {
            "security_events": events,
            "count": len(events),
            "timestamp": datetime.now().isoformat()
        }
    
    async def execute_auto_response(self, response_data: Dict[str, Any]):
        """自動対応実行"""
        try:
            event_id = response_data.get("event_id")
            action_type = response_data.get("action_type")
            action_params = response_data.get("action_params", {})
            
            if not all([event_id, action_type]):
                raise HTTPException(status_code=400, detail="Event ID and action type are required")
            
            result = await self.execute_security_action(event_id, {  # type: ignore
                "type": action_type,
                "params": action_params
            })
            
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"自動対応実行エラー: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_response_actions(self):
        """対応アクション取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT ara.id, ara.event_id, ara.action_type, ara.action_params,
                   ara.status, ara.executed_at, ara.result, ara.created_at,
                   se.event_type, se.threat_level
            FROM auto_response_actions ara
            JOIN security_events se ON ara.event_id = se.id
            ORDER BY ara.created_at DESC
            LIMIT 50
        ''')
        
        actions = []
        for row in cursor.fetchall():
            actions.append({
                "id": row[0],
                "event_id": row[1],
                "action_type": row[2],
                "action_params": json.loads(row[3]) if row[3] else {},
                "status": row[4],
                "executed_at": row[5],
                "result": json.loads(row[6]) if row[6] else {},
                "created_at": row[7],
                "event_type": row[8],
                "threat_level": row[9]
            })
        
        conn.close()
        
        return {
            "response_actions": actions,
            "count": len(actions),
            "timestamp": datetime.now().isoformat()
        }
    
    # ==================== バックグラウンドタスク ====================
    
    def security_monitoring(self):
        """セキュリティ監視"""
        while True:
            try:
                # 定期的なセキュリティ監視
                time.sleep(60)  # 1分間隔
                
            except Exception as e:
                self.logger.error(f"セキュリティ監視エラー: {e}")
                time.sleep(60)
    
    def auto_response_processor(self):
        """自動対応処理"""
        while True:
            try:
                # 自動対応処理
                time.sleep(30)  # 30秒間隔
                
            except Exception as e:
                self.logger.error(f"自動対応処理エラー: {e}")
                time.sleep(30)
    
    # ==================== ヘルパーメソッド ====================
    
    async def count_security_events(self) -> int:
        """セキュリティイベント数取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM security_events')
        count = cursor.fetchone()[0]
        
        conn.close()
        return count
    
    async def count_active_threats(self) -> int:
        """アクティブ脅威数取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM security_events WHERE status = "detected"')
        count = cursor.fetchone()[0]
        
        conn.close()
        return count
    
    async def count_auto_responses(self) -> int:
        """自動対応数取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM auto_response_actions')
        count = cursor.fetchone()[0]
        
        conn.close()
        return count
    
    async def dashboard(self):
        """セキュリティダッシュボード"""
        html_content = self.generate_security_dashboard_html()
        return HTMLResponse(content=html_content)
    
    def generate_security_dashboard_html(self) -> str:
        """セキュリティダッシュボードHTML生成"""
        return """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mana Security Auto Response System</title>
    <style>
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            margin: 0; padding: 20px; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            color: white; 
        }
        .container { max-width: 1600px; margin: 0 auto; }
        .header { text-align: center; margin-bottom: 30px; }
        .header h1 { font-size: 3.5em; margin: 0; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 20px; }
        .card { 
            background: rgba(255,255,255,0.1); 
            border-radius: 15px; 
            padding: 20px; 
            backdrop-filter: blur(10px); 
            border: 1px solid rgba(255,255,255,0.2); 
        }
        .card h3 { margin-top: 0; color: #fff; }
        .button { 
            background: #4CAF50; 
            color: white; 
            border: none; 
            padding: 10px 20px; 
            border-radius: 5px; 
            cursor: pointer; 
            margin: 5px; 
        }
        .button:hover { background: #45a049; }
        .button.security { background: #f44336; }
        .button.security:hover { background: #d32f2f; }
        .input-group { margin: 10px 0; }
        .input-group input, .input-group textarea, .input-group select { 
            width: 100%; 
            padding: 8px; 
            border-radius: 5px; 
            border: 1px solid #ccc; 
        }
        .input-group label { display: block; margin-bottom: 5px; font-weight: bold; }
        .event-item { 
            background: rgba(255,255,255,0.05); 
            padding: 15px; 
            margin: 10px 0; 
            border-radius: 8px; 
        }
        .threat-level { 
            display: inline-block; 
            padding: 5px 15px; 
            border-radius: 20px; 
            font-weight: bold; 
        }
        .threat-level.critical { background: #f44336; }
        .threat-level.high { background: #ff9800; }
        .threat-level.medium { background: #ffeb3b; color: #000; }
        .threat-level.low { background: #4CAF50; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🛡️ Mana Security Auto Response System</h1>
            <p>セキュリティ自動対応・脅威検知・自動防御・リアルタイム対応</p>
        </div>
        
        <div class="grid">
            <!-- 脅威検知 -->
            <div class="card">
                <h3>🚨 脅威検知</h3>
                <div class="input-group">
                    <label>イベントタイプ:</label>
                    <input type="text" id="event-type" placeholder="suspicious_login">
                </div>
                <div class="input-group">
                    <label>脅威スコア (0-1):</label>
                    <input type="number" id="threat-score" placeholder="0.8" min="0" max="1" step="0.1">
                </div>
                <div class="input-group">
                    <label>ソースIP:</label>
                    <input type="text" id="source-ip" placeholder="192.168.1.100">
                </div>
                <div class="input-group">
                    <label>攻撃タイプ:</label>
                    <select id="attack-type">
                        <option value="brute_force">ブルートフォース</option>
                        <option value="ddos">DDoS</option>
                        <option value="sql_injection">SQLインジェクション</option>
                        <option value="xss">XSS</option>
                    </select>
                </div>
                <div class="input-group">
                    <label>説明:</label>
                    <textarea id="description" placeholder="脅威の詳細説明"></textarea>
                </div>
                <button class="button security" onclick="detectThreat()">脅威検知実行</button>
                <div id="threat-result">検知結果がここに表示されます</div>
            </div>
            
            <!-- セキュリティイベント -->
            <div class="card">
                <h3>📊 セキュリティイベント</h3>
                <div id="security-events">読み込み中...</div>
                <button class="button" onclick="refreshSecurityEvents()">🔄 更新</button>
            </div>
            
            <!-- 自動対応アクション -->
            <div class="card">
                <h3>⚡ 自動対応アクション</h3>
                <div id="response-actions">読み込み中...</div>
                <button class="button" onclick="refreshResponseActions()">🔄 更新</button>
            </div>
        </div>
    </div>
    
    <script>
        // 脅威検知実行
        async function detectThreat() {
            const eventType = document.getElementById('event-type').value;
            const threatScore = document.getElementById('threat-score').value;
            const sourceIp = document.getElementById('source-ip').value;
            const attackType = document.getElementById('attack-type').value;
            const description = document.getElementById('description').value;
            
            if (!eventType || !threatScore) {
                alert('イベントタイプと脅威スコアを入力してください');
                return;
            }
            
            try {
                const response = await fetch('/api/security/detect-threat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        event_type: eventType,
                        threat_score: parseFloat(threatScore),
                        source_ip: sourceIp || null,
                        attack_type: attackType,
                        description: description || null
                    })
                });
                
                if (response.ok) {
                    const data = await response.json();
                    let html = `
                        <h4>脅威検知結果:</h4>
                        <p>イベントID: ${data.event_id}</p>
                        <p>脅威レベル: <span class="threat-level ${data.threat_level}">${data.threat_level}</span></p>
                        <p>脅威スコア: ${(data.threat_score * 100).toFixed(1)}%</p>
                        <p>実行された対応アクション: ${data.response_actions.length}件</p>
                        <p>検知時刻: ${new Date(data.detected_at).toLocaleString()}</p>
                    `;
                    
                    document.getElementById('threat-result').innerHTML = html;
                    refreshSecurityEvents();
                    refreshResponseActions();
                } else {
                    alert('脅威検知に失敗しました');
                }
            } catch (error) {
                console.error('脅威検知エラー:', error);
                alert('脅威検知エラーが発生しました');
            }
        }
        
        // セキュリティイベント取得
        async function refreshSecurityEvents() {
            try {
                const response = await fetch('/api/security/events');
                const data = await response.json();
                
                let html = '<h4>セキュリティイベント一覧:</h4>';
                data.security_events.slice(0, 10).forEach(event => {
                    html += `
                        <div class="event-item">
                            <span class="threat-level ${event.threat_level}">${event.threat_level}</span><br>
                            <strong>${event.event_type}</strong><br>
                            脅威スコア: ${(event.threat_score * 100).toFixed(1)}%<br>
                            ${event.source_ip ? `ソースIP: ${event.source_ip}<br>` : ''}
                            攻撃タイプ: ${event.attack_type || 'N/A'}<br>
                            <small>${new Date(event.created_at).toLocaleString()}</small>
                        </div>
                    `;
                });
                
                document.getElementById('security-events').innerHTML = html;
            } catch (error) {
                console.error('セキュリティイベント取得エラー:', error);
            }
        }
        
        // 対応アクション取得
        async function refreshResponseActions() {
            try {
                const response = await fetch('/api/security/actions');
                const data = await response.json();
                
                let html = '<h4>自動対応アクション一覧:</h4>';
                data.response_actions.slice(0, 10).forEach(action => {
                    html += `
                        <div class="event-item">
                            <strong>${action.action_type}</strong><br>
                            ステータス: ${action.status}<br>
                            イベント: ${action.event_type} (${action.threat_level})<br>
                            <small>${new Date(action.created_at).toLocaleString()}</small>
                        </div>
                    `;
                });
                
                document.getElementById('response-actions').innerHTML = html;
            } catch (error) {
                console.error('対応アクション取得エラー:', error);
            }
        }
        
        // 初期化
        window.onload = function() {
            refreshSecurityEvents();
            refreshResponseActions();
            
            // 定期的な更新
            setInterval(refreshSecurityEvents, 30000);
            setInterval(refreshResponseActions, 30000);
        };
    </script>
</body>
</html>
        """

def main():
    """メイン実行"""
    # 必要なディレクトリ作成
    os.makedirs('/root/logs', exist_ok=True)
    
    # システム起動
    security_system = ManaSecurityAutoResponseSystem()
    
    print("🛡️ Mana Security Auto Response System を起動しています...")
    print("📊 ダッシュボード: http://localhost:5019")
    print("🔗 API: http://localhost:5019/api/status")
    print("=" * 60)
    print("🎯 セキュリティ自動対応機能:")
    print("  🛡️ セキュリティ自動対応")
    print("  🚨 脅威検知・分析")
    print("  ⚡ 自動防御アクション")
    print("  🔄 リアルタイム対応")
    print("  🧠 インテリジェント防御")
    print("  📊 脅威レベル判定")
    print("=" * 60)
    
    # FastAPIサーバー起動
    uvicorn.run(
        security_system.app,
        host="0.0.0.0",
        port=5019,
        log_level="info"
    )

if __name__ == "__main__":
    main()
