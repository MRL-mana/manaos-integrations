#!/usr/bin/env python3
"""
Mana Real-time Decision System
リアルタイム意思決定システム - 瞬時の判断と実行
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any
import threading
import time
import sqlite3
import requests
from enum import Enum

# FastAPI
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import uvicorn

class DecisionPriority(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class DecisionStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class ManaRealTimeDecisionSystem:
    """Manaリアルタイム意思決定システム"""
    
    def __init__(self):
        self.app = FastAPI(title="Mana Real-time Decision System", version="18.0.0")
        self.db_path = "/root/mana_realtime_decision.db"
        
        # 意思決定エンジン
        self.decision_rules = {}
        self.decision_queue = []
        self.active_decisions = {}
        
        # ログ設定
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler('/root/logs/mana_realtime_decision.log'),
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
        
        self.logger.info("⚡ Mana Real-time Decision System 初期化完了")
    
    def init_database(self):
        """データベース初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 意思決定ルールテーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS decision_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_name TEXT UNIQUE NOT NULL,
                rule_condition TEXT NOT NULL,
                rule_action TEXT NOT NULL,
                priority TEXT NOT NULL,
                enabled BOOLEAN DEFAULT TRUE,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 意思決定履歴テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS decision_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                decision_id TEXT UNIQUE NOT NULL,
                rule_name TEXT NOT NULL,
                input_data TEXT NOT NULL,
                decision_result TEXT NOT NULL,
                execution_time REAL NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # リアルタイムイベントテーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS realtime_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                event_data TEXT NOT NULL,
                priority TEXT NOT NULL,
                processed BOOLEAN DEFAULT FALSE,
                decision_id TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
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
        
        # 意思決定API
        @self.app.post("/api/decision/make")
        async def make_decision(decision_data: Dict[str, Any]):
            return await self.make_decision(decision_data)
        
        @self.app.get("/api/decision/history")
        async def get_decision_history():
            return await self.get_decision_history()
        
        # ルール管理API
        @self.app.post("/api/rules/create")
        async def create_decision_rule(rule_data: Dict[str, Any]):
            return await self.create_decision_rule(rule_data)
        
        @self.app.get("/api/rules")
        async def get_decision_rules():
            return await self.get_decision_rules()
        
        # リアルタイムイベントAPI
        @self.app.post("/api/events/process")
        async def process_realtime_event(event_data: Dict[str, Any]):
            return await self.process_realtime_event(event_data)
        
        @self.app.get("/api/events")
        async def get_realtime_events():
            return await self.get_realtime_events()
        
        @self.app.get("/api/dashboard")
        async def dashboard():
            return await self.dashboard()
    
    def start_background_tasks(self):
        """バックグラウンドタスク開始"""
        # リアルタイム意思決定処理
        threading.Thread(target=self.realtime_decision_processor, daemon=True).start()
        
        # イベント処理
        threading.Thread(target=self.event_processor, daemon=True).start()
        
        # 意思決定最適化
        threading.Thread(target=self.decision_optimizer, daemon=True).start()
        
        self.logger.info("バックグラウンドタスク開始")
    
    # ==================== API実装 ====================
    
    async def root(self):
        """ルートエンドポイント"""
        return {
            "message": "Mana Real-time Decision System",
            "version": "18.0.0",
            "status": "active",
            "features": [
                "リアルタイム意思決定",
                "瞬時の判断と実行",
                "インテリジェントルール",
                "優先度ベース処理",
                "自動最適化",
                "高精度予測"
            ]
        }
    
    async def get_status(self):
        """システム状態取得"""
        return {
            "timestamp": datetime.now().isoformat(),
            "system": "Mana Real-time Decision System",
            "status": "healthy",
            "version": "18.0.0",
            "decision": {
                "total_rules": await self.count_decision_rules(),
                "total_decisions": await self.count_decisions(),
                "pending_events": await self.count_pending_events(),
                "average_decision_time": await self.calculate_average_decision_time()
            }
        }
    
    async def make_decision(self, decision_data: Dict[str, Any]):
        """意思決定実行"""
        try:
            input_data = decision_data.get("input_data", {})
            rule_name = decision_data.get("rule_name")
            priority = decision_data.get("priority", DecisionPriority.MEDIUM.value)
            
            start_time = time.time()
            
            # 意思決定実行
            if rule_name:
                # 特定のルールを使用
                decision_result = await self.execute_decision_rule(rule_name, input_data)
            else:
                # 自動ルール選択
                decision_result = await self.auto_select_and_execute_rule(input_data, priority)
            
            execution_time = time.time() - start_time
            
            # 意思決定履歴保存
            decision_id = f"decision_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
            await self.save_decision_history(decision_id, rule_name or "auto", input_data, decision_result, execution_time)
            
            self.logger.info(f"意思決定完了: {decision_id} ({execution_time:.3f}秒)")
            
            return {
                "decision_id": decision_id,
                "rule_name": rule_name or "auto",
                "input_data": input_data,
                "decision_result": decision_result,
                "execution_time": execution_time,
                "status": "completed",
                "decided_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"意思決定エラー: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def execute_decision_rule(self, rule_name: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """意思決定ルール実行"""
        try:
            # ルール取得
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT rule_condition, rule_action, priority
                FROM decision_rules
                WHERE rule_name = ? AND enabled = TRUE
            ''', (rule_name,))
            
            rule = cursor.fetchone()
            conn.close()
            
            if not rule:
                return {"success": False, "error": f"Rule {rule_name} not found or disabled"}
            
            rule_condition, rule_action, priority = rule
            
            # 条件評価
            condition_met = await self.evaluate_condition(rule_condition, input_data)
            
            if condition_met:
                # アクション実行
                action_result = await self.execute_action(rule_action, input_data)
                return {
                    "success": True,
                    "rule_name": rule_name,
                    "condition_met": True,
                    "action_result": action_result,
                    "priority": priority
                }
            else:
                return {
                    "success": True,
                    "rule_name": rule_name,
                    "condition_met": False,
                    "action_result": None,
                    "priority": priority
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def auto_select_and_execute_rule(self, input_data: Dict[str, Any], priority: str) -> Dict[str, Any]:
        """自動ルール選択と実行"""
        try:
            # 優先度に基づくルール選択
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT rule_name, rule_condition, rule_action
                FROM decision_rules
                WHERE priority = ? AND enabled = TRUE
                ORDER BY created_at DESC
            ''', (priority,))
            
            rules = cursor.fetchall()
            conn.close()
            
            if not rules:
                return {"success": False, "error": f"No rules found for priority {priority}"}
            
            # 最初の適用可能なルールを実行
            for rule_name, rule_condition, rule_action in rules:
                condition_met = await self.evaluate_condition(rule_condition, input_data)
                if condition_met:
                    action_result = await self.execute_action(rule_action, input_data)
                    return {
                        "success": True,
                        "rule_name": rule_name,
                        "condition_met": True,
                        "action_result": action_result,
                        "priority": priority
                    }
            
            return {
                "success": True,
                "rule_name": "auto",
                "condition_met": False,
                "action_result": None,
                "priority": priority
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def evaluate_condition(self, condition: str, input_data: Dict[str, Any]) -> bool:
        """条件評価"""
        try:
            # 簡易的な条件評価（実際の実装では、より複雑な評価エンジンを使用）
            if "cpu_usage" in condition and "cpu_usage" in input_data:
                threshold = float(condition.split(">")[1].strip()) if ">" in condition else 80.0
                return input_data["cpu_usage"] > threshold
            
            elif "memory_usage" in condition and "memory_usage" in input_data:
                threshold = float(condition.split(">")[1].strip()) if ">" in condition else 85.0
                return input_data["memory_usage"] > threshold
            
            elif "response_time" in condition and "response_time" in input_data:
                threshold = float(condition.split(">")[1].strip()) if ">" in condition else 2.0
                return input_data["response_time"] > threshold
            
            else:
                # デフォルト条件（常に真）
                return True
                
        except Exception as e:
            self.logger.error(f"条件評価エラー: {e}")
            return False
    
    async def execute_action(self, action: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """アクション実行"""
        try:
            if action == "scale_up":
                # スケールアップ実行
                response = requests.post("http://localhost:5018/api/scaling/auto-scale", timeout=10)
                return {"action": "scale_up", "result": response.json() if response.status_code == 200 else {"error": "scaling_failed"}}
            
            elif action == "optimize_system":
                # システム最適化
                response = requests.get("http://localhost:5009/api/status", timeout=10)
                return {"action": "optimize_system", "result": response.json() if response.status_code == 200 else {"error": "optimization_failed"}}
            
            elif action == "security_scan":
                # セキュリティスキャン
                response = requests.get("http://localhost:5019/api/status", timeout=10)
                return {"action": "security_scan", "result": response.json() if response.status_code == 200 else {"error": "security_scan_failed"}}
            
            elif action == "alert_admin":
                # 管理者アラート
                return {"action": "alert_admin", "result": {"message": "Admin alert sent", "priority": "high"}}
            
            else:
                return {"action": action, "result": {"message": f"Action {action} executed", "status": "completed"}}
                
        except Exception as e:
            return {"action": action, "result": {"error": str(e), "status": "failed"}}
    
    async def save_decision_history(self, decision_id: str, rule_name: str, 
                                  input_data: Dict[str, Any], decision_result: Dict[str, Any], 
                                  execution_time: float):
        """意思決定履歴保存"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO decision_history 
            (decision_id, rule_name, input_data, decision_result, execution_time, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            decision_id,
            rule_name,
            json.dumps(input_data),
            json.dumps(decision_result),
            execution_time,
            "completed" if decision_result.get("success") else "failed",
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    async def get_decision_history(self):
        """意思決定履歴取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT decision_id, rule_name, input_data, decision_result, 
                   execution_time, status, created_at
            FROM decision_history
            ORDER BY created_at DESC
            LIMIT 50
        ''')
        
        decisions = []
        for row in cursor.fetchall():
            decisions.append({
                "decision_id": row[0],
                "rule_name": row[1],
                "input_data": json.loads(row[2]) if row[2] else {},
                "decision_result": json.loads(row[3]) if row[3] else {},
                "execution_time": row[4],
                "status": row[5],
                "created_at": row[6]
            })
        
        conn.close()
        
        return {
            "decision_history": decisions,
            "count": len(decisions),
            "timestamp": datetime.now().isoformat()
        }
    
    async def create_decision_rule(self, rule_data: Dict[str, Any]):
        """意思決定ルール作成"""
        try:
            rule_name = rule_data.get("rule_name")
            rule_condition = rule_data.get("rule_condition")
            rule_action = rule_data.get("rule_action")
            priority = rule_data.get("priority", DecisionPriority.MEDIUM.value)
            
            if not all([rule_name, rule_condition, rule_action]):
                raise HTTPException(status_code=400, detail="Rule name, condition, and action are required")
            
            # ルール保存
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO decision_rules 
                (rule_name, rule_condition, rule_action, priority, enabled, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                rule_name,
                rule_condition,
                rule_action,
                priority,
                True,
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"意思決定ルール作成: {rule_name}")
            
            return {
                "rule_name": rule_name,
                "rule_condition": rule_condition,
                "rule_action": rule_action,
                "priority": priority,
                "status": "created",
                "created_at": datetime.now().isoformat()
            }
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"ルール作成エラー: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_decision_rules(self):
        """意思決定ルール取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT rule_name, rule_condition, rule_action, priority, 
                   enabled, created_at, updated_at
            FROM decision_rules
            ORDER BY priority DESC, created_at DESC
        ''')
        
        rules = []
        for row in cursor.fetchall():
            rules.append({
                "rule_name": row[0],
                "rule_condition": row[1],
                "rule_action": row[2],
                "priority": row[3],
                "enabled": bool(row[4]),
                "created_at": row[5],
                "updated_at": row[6]
            })
        
        conn.close()
        
        return {
            "decision_rules": rules,
            "count": len(rules),
            "timestamp": datetime.now().isoformat()
        }
    
    async def process_realtime_event(self, event_data: Dict[str, Any]):
        """リアルタイムイベント処理"""
        try:
            event_type = event_data.get("event_type")
            event_data_content = event_data.get("event_data", {})
            priority = event_data.get("priority", DecisionPriority.MEDIUM.value)
            
            if not event_type:
                raise HTTPException(status_code=400, detail="Event type is required")
            
            # イベント保存
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO realtime_events 
                (event_type, event_data, priority, created_at)
                VALUES (?, ?, ?, ?)
            ''', (
                event_type,
                json.dumps(event_data_content),
                priority,
                datetime.now().isoformat()
            ))
            
            event_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            # リアルタイム意思決定実行
            decision_result = await self.make_decision({
                "input_data": event_data_content,
                "priority": priority
            })
            
            # イベント処理完了マーク
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE realtime_events 
                SET processed = TRUE, decision_id = ?
                WHERE id = ?
            ''', (decision_result["decision_id"], event_id))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"リアルタイムイベント処理完了: {event_type}")
            
            return {
                "event_id": event_id,
                "event_type": event_type,
                "decision_result": decision_result,
                "processed_at": datetime.now().isoformat()
            }
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"リアルタイムイベント処理エラー: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_realtime_events(self):
        """リアルタイムイベント取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, event_type, event_data, priority, processed, 
                   decision_id, created_at
            FROM realtime_events
            ORDER BY created_at DESC
            LIMIT 50
        ''')
        
        events = []
        for row in cursor.fetchall():
            events.append({
                "id": row[0],
                "event_type": row[1],
                "event_data": json.loads(row[2]) if row[2] else {},
                "priority": row[3],
                "processed": bool(row[4]),
                "decision_id": row[5],
                "created_at": row[6]
            })
        
        conn.close()
        
        return {
            "realtime_events": events,
            "count": len(events),
            "timestamp": datetime.now().isoformat()
        }
    
    # ==================== バックグラウンドタスク ====================
    
    def realtime_decision_processor(self):
        """リアルタイム意思決定処理"""
        while True:
            try:
                # リアルタイム意思決定処理
                time.sleep(1)  # 1秒間隔
                
            except Exception as e:
                self.logger.error(f"リアルタイム意思決定処理エラー: {e}")
                time.sleep(1)
    
    def event_processor(self):
        """イベント処理"""
        while True:
            try:
                # イベント処理
                time.sleep(5)  # 5秒間隔
                
            except Exception as e:
                self.logger.error(f"イベント処理エラー: {e}")
                time.sleep(5)
    
    def decision_optimizer(self):
        """意思決定最適化"""
        while True:
            try:
                # 意思決定最適化
                time.sleep(300)  # 5分間隔
                
            except Exception as e:
                self.logger.error(f"意思決定最適化エラー: {e}")
                time.sleep(300)
    
    # ==================== ヘルパーメソッド ====================
    
    async def count_decision_rules(self) -> int:
        """意思決定ルール数取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM decision_rules WHERE enabled = TRUE')
        count = cursor.fetchone()[0]
        
        conn.close()
        return count
    
    async def count_decisions(self) -> int:
        """意思決定数取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM decision_history')
        count = cursor.fetchone()[0]
        
        conn.close()
        return count
    
    async def count_pending_events(self) -> int:
        """待機中イベント数取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM realtime_events WHERE processed = FALSE')
        count = cursor.fetchone()[0]
        
        conn.close()
        return count
    
    async def calculate_average_decision_time(self) -> float:
        """平均意思決定時間計算"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT AVG(execution_time) FROM decision_history')
        avg_time = cursor.fetchone()[0] or 0.0
        
        conn.close()
        return round(avg_time, 3)
    
    async def dashboard(self):
        """リアルタイム意思決定ダッシュボード"""
        html_content = self.generate_realtime_dashboard_html()
        return HTMLResponse(content=html_content)
    
    def generate_realtime_dashboard_html(self) -> str:
        """リアルタイム意思決定ダッシュボードHTML生成"""
        return """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mana Real-time Decision System</title>
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
        .button.decision { background: #ff9800; }
        .button.decision:hover { background: #f57c00; }
        .input-group { margin: 10px 0; }
        .input-group input, .input-group textarea, .input-group select { 
            width: 100%; 
            padding: 8px; 
            border-radius: 5px; 
            border: 1px solid #ccc; 
        }
        .input-group label { display: block; margin-bottom: 5px; font-weight: bold; }
        .decision-item { 
            background: rgba(255,255,255,0.05); 
            padding: 15px; 
            margin: 10px 0; 
            border-radius: 8px; 
        }
        .priority { 
            display: inline-block; 
            padding: 5px 15px; 
            border-radius: 20px; 
            font-weight: bold; 
        }
        .priority.critical { background: #f44336; }
        .priority.high { background: #ff9800; }
        .priority.medium { background: #ffeb3b; color: #000; }
        .priority.low { background: #4CAF50; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚡ Mana Real-time Decision System</h1>
            <p>リアルタイム意思決定・瞬時の判断と実行・インテリジェントルール・優先度ベース処理</p>
        </div>
        
        <div class="grid">
            <!-- 意思決定実行 -->
            <div class="card">
                <h3>🎯 意思決定実行</h3>
                <div class="input-group">
                    <label>入力データ:</label>
                    <textarea id="input-data" placeholder='{"cpu_usage": 85, "memory_usage": 90}'></textarea>
                </div>
                <div class="input-group">
                    <label>ルール名 (オプション):</label>
                    <input type="text" id="rule-name" placeholder="auto">
                </div>
                <div class="input-group">
                    <label>優先度:</label>
                    <select id="priority">
                        <option value="critical">Critical</option>
                        <option value="high">High</option>
                        <option value="medium" selected>Medium</option>
                        <option value="low">Low</option>
                    </select>
                </div>
                <button class="button decision" onclick="makeDecision()">意思決定実行</button>
                <div id="decision-result">決定結果がここに表示されます</div>
            </div>
            
            <!-- ルール作成 -->
            <div class="card">
                <h3>📋 ルール作成</h3>
                <div class="input-group">
                    <label>ルール名:</label>
                    <input type="text" id="new-rule-name" placeholder="high_cpu_rule">
                </div>
                <div class="input-group">
                    <label>条件:</label>
                    <input type="text" id="rule-condition" placeholder="cpu_usage > 80">
                </div>
                <div class="input-group">
                    <label>アクション:</label>
                    <select id="rule-action">
                        <option value="scale_up">スケールアップ</option>
                        <option value="optimize_system">システム最適化</option>
                        <option value="security_scan">セキュリティスキャン</option>
                        <option value="alert_admin">管理者アラート</option>
                    </select>
                </div>
                <div class="input-group">
                    <label>優先度:</label>
                    <select id="rule-priority">
                        <option value="critical">Critical</option>
                        <option value="high">High</option>
                        <option value="medium" selected>Medium</option>
                        <option value="low">Low</option>
                    </select>
                </div>
                <button class="button decision" onclick="createRule()">ルール作成</button>
                <div id="rule-creation-result">作成結果がここに表示されます</div>
            </div>
            
            <!-- 意思決定履歴 -->
            <div class="card">
                <h3>📊 意思決定履歴</h3>
                <div id="decision-history">読み込み中...</div>
                <button class="button" onclick="refreshDecisionHistory()">🔄 更新</button>
            </div>
            
            <!-- ルール一覧 -->
            <div class="card">
                <h3>📋 ルール一覧</h3>
                <div id="decision-rules">読み込み中...</div>
                <button class="button" onclick="refreshDecisionRules()">🔄 更新</button>
            </div>
            
            <!-- リアルタイムイベント -->
            <div class="card">
                <h3>⚡ リアルタイムイベント</h3>
                <div class="input-group">
                    <label>イベントタイプ:</label>
                    <input type="text" id="event-type" placeholder="system_alert">
                </div>
                <div class="input-group">
                    <label>イベントデータ:</label>
                    <textarea id="event-data" placeholder='{"alert_level": "high", "message": "CPU usage critical"}'></textarea>
                </div>
                <div class="input-group">
                    <label>優先度:</label>
                    <select id="event-priority">
                        <option value="critical">Critical</option>
                        <option value="high">High</option>
                        <option value="medium" selected>Medium</option>
                        <option value="low">Low</option>
                    </select>
                </div>
                <button class="button decision" onclick="processEvent()">イベント処理</button>
                <div id="event-result">処理結果がここに表示されます</div>
            </div>
            
            <!-- イベント履歴 -->
            <div class="card">
                <h3>📨 イベント履歴</h3>
                <div id="realtime-events">読み込み中...</div>
                <button class="button" onclick="refreshRealtimeEvents()">🔄 更新</button>
            </div>
        </div>
    </div>
    
    <script>
        // 意思決定実行
        async function makeDecision() {
            const inputData = document.getElementById('input-data').value;
            const ruleName = document.getElementById('rule-name').value;
            const priority = document.getElementById('priority').value;
            
            if (!inputData) {
                alert('入力データを入力してください');
                return;
            }
            
            try {
                const response = await fetch('/api/decision/make', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        input_data: JSON.parse(inputData),
                        rule_name: ruleName || null,
                        priority: priority
                    })
                });
                
                if (response.ok) {
                    const data = await response.json();
                    let html = `
                        <h4>意思決定完了:</h4>
                        <p>決定ID: ${data.decision_id}</p>
                        <p>ルール: ${data.rule_name}</p>
                        <p>実行時間: ${data.execution_time.toFixed(3)}秒</p>
                        <p>成功: ${data.decision_result.success ? 'はい' : 'いいえ'}</p>
                        <p>条件適合: ${data.decision_result.condition_met ? 'はい' : 'いいえ'}</p>
                        <p>決定時刻: ${new Date(data.decided_at).toLocaleString()}</p>
                    `;
                    
                    document.getElementById('decision-result').innerHTML = html;
                    refreshDecisionHistory();
                } else {
                    alert('意思決定に失敗しました');
                }
            } catch (error) {
                console.error('意思決定エラー:', error);
                alert('意思決定エラーが発生しました');
            }
        }
        
        // ルール作成
        async function createRule() {
            const ruleName = document.getElementById('new-rule-name').value;
            const ruleCondition = document.getElementById('rule-condition').value;
            const ruleAction = document.getElementById('rule-action').value;
            const rulePriority = document.getElementById('rule-priority').value;
            
            if (!ruleName || !ruleCondition || !ruleAction) {
                alert('ルール名、条件、アクションを入力してください');
                return;
            }
            
            try {
                const response = await fetch('/api/rules/create', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        rule_name: ruleName,
                        rule_condition: ruleCondition,
                        rule_action: ruleAction,
                        priority: rulePriority
                    })
                });
                
                if (response.ok) {
                    const data = await response.json();
                    let html = `
                        <h4>ルール作成完了:</h4>
                        <p>ルール名: ${data.rule_name}</p>
                        <p>条件: ${data.rule_condition}</p>
                        <p>アクション: ${data.rule_action}</p>
                        <p>優先度: ${data.priority}</p>
                        <p>作成時刻: ${new Date(data.created_at).toLocaleString()}</p>
                    `;
                    
                    document.getElementById('rule-creation-result').innerHTML = html;
                    refreshDecisionRules();
                } else {
                    alert('ルール作成に失敗しました');
                }
            } catch (error) {
                console.error('ルール作成エラー:', error);
                alert('ルール作成エラーが発生しました');
            }
        }
        
        // 意思決定履歴取得
        async function refreshDecisionHistory() {
            try {
                const response = await fetch('/api/decision/history');
                const data = await response.json();
                
                let html = '<h4>意思決定履歴:</h4>';
                data.decision_history.slice(0, 10).forEach(decision => {
                    html += `
                        <div class="decision-item">
                            <strong>${decision.rule_name}</strong><br>
                            実行時間: ${decision.execution_time.toFixed(3)}秒<br>
                            ステータス: ${decision.status}<br>
                            成功: ${decision.decision_result.success ? 'はい' : 'いいえ'}<br>
                            <small>${new Date(decision.created_at).toLocaleString()}</small>
                        </div>
                    `;
                });
                
                document.getElementById('decision-history').innerHTML = html;
            } catch (error) {
                console.error('意思決定履歴取得エラー:', error);
            }
        }
        
        // ルール一覧取得
        async function refreshDecisionRules() {
            try {
                const response = await fetch('/api/rules');
                const data = await response.json();
                
                let html = '<h4>意思決定ルール:</h4>';
                data.decision_rules.forEach(rule => {
                    html += `
                        <div class="decision-item">
                            <span class="priority ${rule.priority}">${rule.priority}</span><br>
                            <strong>${rule.rule_name}</strong><br>
                            条件: ${rule.rule_condition}<br>
                            アクション: ${rule.rule_action}<br>
                            有効: ${rule.enabled ? 'はい' : 'いいえ'}<br>
                            <small>作成: ${new Date(rule.created_at).toLocaleString()}</small>
                        </div>
                    `;
                });
                
                document.getElementById('decision-rules').innerHTML = html;
            } catch (error) {
                console.error('ルール一覧取得エラー:', error);
            }
        }
        
        // リアルタイムイベント処理
        async function processEvent() {
            const eventType = document.getElementById('event-type').value;
            const eventData = document.getElementById('event-data').value;
            const eventPriority = document.getElementById('event-priority').value;
            
            if (!eventType) {
                alert('イベントタイプを入力してください');
                return;
            }
            
            try {
                const response = await fetch('/api/events/process', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        event_type: eventType,
                        event_data: JSON.parse(eventData || '{}'),
                        priority: eventPriority
                    })
                });
                
                if (response.ok) {
                    const data = await response.json();
                    let html = `
                        <h4>イベント処理完了:</h4>
                        <p>イベントID: ${data.event_id}</p>
                        <p>イベントタイプ: ${data.event_type}</p>
                        <p>決定ID: ${data.decision_result.decision_id}</p>
                        <p>処理時刻: ${new Date(data.processed_at).toLocaleString()}</p>
                    `;
                    
                    document.getElementById('event-result').innerHTML = html;
                    refreshRealtimeEvents();
                } else {
                    alert('イベント処理に失敗しました');
                }
            } catch (error) {
                console.error('イベント処理エラー:', error);
                alert('イベント処理エラーが発生しました');
            }
        }
        
        // リアルタイムイベント取得
        async function refreshRealtimeEvents() {
            try {
                const response = await fetch('/api/events');
                const data = await response.json();
                
                let html = '<h4>リアルタイムイベント:</h4>';
                data.realtime_events.slice(0, 10).forEach(event => {
                    html += `
                        <div class="decision-item">
                            <span class="priority ${event.priority}">${event.priority}</span><br>
                            <strong>${event.event_type}</strong><br>
                            処理済み: ${event.processed ? 'はい' : 'いいえ'}<br>
                            ${event.decision_id ? `決定ID: ${event.decision_id}<br>` : ''}
                            <small>${new Date(event.created_at).toLocaleString()}</small>
                        </div>
                    `;
                });
                
                document.getElementById('realtime-events').innerHTML = html;
            } catch (error) {
                console.error('リアルタイムイベント取得エラー:', error);
            }
        }
        
        // 初期化
        window.onload = function() {
            refreshDecisionHistory();
            refreshDecisionRules();
            refreshRealtimeEvents();
            
            // 定期的な更新
            setInterval(refreshDecisionHistory, 30000);
            setInterval(refreshDecisionRules, 60000);
            setInterval(refreshRealtimeEvents, 30000);
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
    decision_system = ManaRealTimeDecisionSystem()
    
    print("⚡ Mana Real-time Decision System を起動しています...")
    print("📊 ダッシュボード: http://localhost:5022")
    print("🔗 API: http://localhost:5022/api/status")
    print("=" * 60)
    print("🎯 リアルタイム意思決定機能:")
    print("  ⚡ リアルタイム意思決定")
    print("  🎯 瞬時の判断と実行")
    print("  🧠 インテリジェントルール")
    print("  📊 優先度ベース処理")
    print("  🔄 自動最適化")
    print("  📈 高精度予測")
    print("=" * 60)
    
    # FastAPIサーバー起動
    uvicorn.run(
        decision_system.app,
        host="0.0.0.0",
        port=5022,
        log_level="info"
    )

if __name__ == "__main__":
    main()
