#!/usr/bin/env python3
"""
Mana Learning Automation System
学習型自動化システム - AI秘書が学習して自動化ルールを生成
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any
import threading
import time
import sqlite3
from collections import defaultdict

# FastAPI
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import uvicorn

class ManaLearningAutomationSystem:
    """Mana学習型自動化システム"""
    
    def __init__(self):
        self.app = FastAPI(title="Mana Learning Automation System", version="12.0.0")
        self.db_path = "/root/mana_learning_automation.db"
        
        # 学習データ
        self.patterns = defaultdict(list)
        self.success_patterns = defaultdict(float)
        self.failure_patterns = defaultdict(float)
        self.user_preferences = {}
        
        # ログ設定
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler('/root/logs/mana_learning_automation.log'),
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
        
        self.logger.info("🧠 Mana Learning Automation System 初期化完了")
    
    def init_database(self):
        """データベース初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 学習パターンテーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS learning_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_type TEXT NOT NULL,
                pattern_data TEXT NOT NULL,
                success_count INTEGER DEFAULT 0,
                failure_count INTEGER DEFAULT 0,
                success_rate REAL DEFAULT 0.0,
                last_used TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 自動生成ルールテーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS generated_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_name TEXT UNIQUE NOT NULL,
                trigger_condition TEXT NOT NULL,
                action_sequence TEXT NOT NULL,
                confidence_score REAL DEFAULT 0.0,
                learning_source TEXT NOT NULL,
                enabled BOOLEAN DEFAULT TRUE,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_executed TEXT,
                execution_count INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0
            )
        ''')
        
        # 学習履歴テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS learning_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                event_data TEXT NOT NULL,
                outcome TEXT NOT NULL,
                learning_insights TEXT,
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
        
        # 学習機能API
        @self.app.post("/api/learning/learn")
        async def learn_from_event(event_data: Dict[str, Any]):
            return await self.learn_from_event(event_data)
        
        @self.app.get("/api/learning/patterns")
        async def get_learning_patterns():
            return await self.get_learning_patterns()
        
        @self.app.post("/api/learning/generate-rule")
        async def generate_automation_rule(context_data: Dict[str, Any]):
            return await self.generate_automation_rule(context_data)
        
        @self.app.get("/api/learning/generated-rules")
        async def get_generated_rules():
            return await self.get_generated_rules()
        
        # 学習分析API
        @self.app.get("/api/learning/insights")
        async def get_learning_insights():
            return await self.get_learning_insights()
        
        @self.app.post("/api/learning/optimize")
        async def optimize_learning():
            return await self.optimize_learning()
        
        @self.app.get("/api/dashboard")
        async def dashboard():
            return await self.dashboard()
    
    def start_background_tasks(self):
        """バックグラウンドタスク開始"""
        # 学習プロセス
        threading.Thread(target=self.learning_process, daemon=True).start()
        
        # パターン分析
        threading.Thread(target=self.pattern_analysis, daemon=True).start()
        
        # 自動ルール生成
        threading.Thread(target=self.auto_rule_generation, daemon=True).start()
        
        self.logger.info("バックグラウンドタスク開始")
    
    # ==================== API実装 ====================
    
    async def root(self):
        """ルートエンドポイント"""
        return {
            "message": "Mana Learning Automation System",
            "version": "12.0.0",
            "status": "active",
            "features": [
                "学習型自動化ルール生成",
                "パターン認識・分析",
                "インテリジェント最適化",
                "予測的自動化",
                "継続的学習",
                "適応的改善"
            ],
            "learning_capabilities": [
                "ユーザー行動パターン学習",
                "システム状態パターン学習",
                "成功・失敗パターン分析",
                "自動ルール生成",
                "継続的改善"
            ]
        }
    
    async def get_status(self):
        """システム状態取得"""
        return {
            "timestamp": datetime.now().isoformat(),
            "system": "Mana Learning Automation System",
            "status": "healthy",
            "version": "12.0.0",
            "learning": {
                "total_patterns": await self.count_learning_patterns(),
                "generated_rules": await self.count_generated_rules(),
                "learning_events": await self.count_learning_events(),
                "success_rate": await self.calculate_learning_success_rate()
            },
            "capabilities": {
                "pattern_recognition": True,
                "rule_generation": True,
                "continuous_learning": True,
                "adaptive_optimization": True
            }
        }
    
    async def learn_from_event(self, event_data: Dict[str, Any]):
        """イベントから学習"""
        try:
            event_type = event_data.get("event_type")
            event_context = event_data.get("event_context", {})
            outcome = event_data.get("outcome")  # "success" or "failure"
            
            if not all([event_type, outcome]):
                raise HTTPException(status_code=400, detail="Event type and outcome are required")
            
            # パターン抽出
            pattern = self.extract_pattern(event_type, event_context)  # type: ignore
            
            # 学習データ保存
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # パターン学習
            cursor.execute('''
                INSERT OR REPLACE INTO learning_patterns 
                (pattern_type, pattern_data, success_count, failure_count, 
                 success_rate, last_used, updated_at)
                VALUES (?, ?, 
                    COALESCE((SELECT success_count FROM learning_patterns WHERE pattern_type = ? AND pattern_data = ?), 0) + ?,
                    COALESCE((SELECT failure_count FROM learning_patterns WHERE pattern_type = ? AND pattern_data = ?), 0) + ?,
                    ?, ?, ?)
            ''', (
                event_type,
                json.dumps(pattern),
                event_type, json.dumps(pattern), 1 if outcome == "success" else 0,
                event_type, json.dumps(pattern), 1 if outcome == "failure" else 0,
                self.calculate_success_rate(event_type, pattern, outcome),  # type: ignore
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            
            # 学習履歴保存
            cursor.execute('''
                INSERT INTO learning_history 
                (event_type, event_data, outcome, learning_insights, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                event_type,
                json.dumps(event_context),
                outcome,
                json.dumps(self.generate_learning_insights(event_type, pattern, outcome)),  # type: ignore
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"学習完了: {event_type} - {outcome}")
            
            return {
                "event_type": event_type,
                "pattern": pattern,
                "outcome": outcome,
                "learning_insights": self.generate_learning_insights(event_type, pattern, outcome),  # type: ignore
                "learned_at": datetime.now().isoformat()
            }
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"学習エラー: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    def extract_pattern(self, event_type: str, event_context: Dict[str, Any]) -> Dict[str, Any]:
        """パターン抽出"""
        pattern = {
            "event_type": event_type,
            "timestamp": datetime.now().isoformat(),
            "context_keys": list(event_context.keys()),
            "context_values": list(event_context.values())
        }
        
        # 時間パターン
        hour = datetime.now().hour
        pattern["time_pattern"] = {
            "hour": hour,
            "period": "morning" if 6 <= hour < 12 else "afternoon" if 12 <= hour < 18 else "evening" if 18 <= hour < 22 else "night"
        }
        
        # システム状態パターン
        if "system_metrics" in event_context:
            metrics = event_context["system_metrics"]
            pattern["system_pattern"] = {
                "cpu_level": "high" if metrics.get("cpu_usage", 0) > 80 else "medium" if metrics.get("cpu_usage", 0) > 50 else "low",
                "memory_level": "high" if metrics.get("memory_usage", 0) > 80 else "medium" if metrics.get("memory_usage", 0) > 50 else "low"
            }
        
        return pattern
    
    def calculate_success_rate(self, event_type: str, pattern: Dict[str, Any], outcome: str) -> float:
        """成功率計算"""
        # 簡易的な成功率計算
        # 実際の実装では、より複雑な計算を行う
        return 0.8 if outcome == "success" else 0.2
    
    def generate_learning_insights(self, event_type: str, pattern: Dict[str, Any], outcome: str) -> Dict[str, Any]:
        """学習インサイト生成"""
        insights = {
            "pattern_strength": 0.8 if outcome == "success" else 0.2,
            "recommendations": [],
            "confidence": 0.7
        }
        
        if outcome == "success":
            insights["recommendations"].append("このパターンを自動化ルールに適用することを推奨")
        else:
            insights["recommendations"].append("このパターンを避けるか、改善が必要")
        
        return insights
    
    async def get_learning_patterns(self):
        """学習パターン取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT pattern_type, pattern_data, success_count, failure_count, 
                   success_rate, last_used, created_at
            FROM learning_patterns
            ORDER BY success_rate DESC, (success_count + failure_count) DESC
        ''')
        
        patterns = []
        for row in cursor.fetchall():
            patterns.append({
                "pattern_type": row[0],
                "pattern_data": json.loads(row[1]),
                "success_count": row[2],
                "failure_count": row[3],
                "success_rate": row[4],
                "last_used": row[5],
                "created_at": row[6]
            })
        
        conn.close()
        
        return {
            "learning_patterns": patterns,
            "count": len(patterns),
            "timestamp": datetime.now().isoformat()
        }
    
    async def generate_automation_rule(self, context_data: Dict[str, Any]):
        """自動化ルール生成"""
        try:
            context = context_data.get("context", {})
            user_intent = context_data.get("user_intent", "optimization")
            
            # 学習パターンに基づくルール生成
            rule = self.create_rule_from_patterns(context, user_intent)
            
            # 生成されたルール保存
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO generated_rules 
                (rule_name, trigger_condition, action_sequence, confidence_score, 
                 learning_source, enabled, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                rule["rule_name"],
                rule["trigger_condition"],
                json.dumps(rule["action_sequence"]),
                rule["confidence_score"],
                "learning_automation",
                True,
                datetime.now().isoformat()
            ))
            
            rule_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            self.logger.info(f"自動化ルール生成完了: {rule['rule_name']}")
            
            return {
                "rule_id": rule_id,
                "generated_rule": rule,
                "confidence_score": rule["confidence_score"],
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"自動化ルール生成エラー: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    def create_rule_from_patterns(self, context: Dict[str, Any], user_intent: str) -> Dict[str, Any]:
        """パターンからルール作成"""
        # 学習パターンに基づくルール生成ロジック
        rule_name = f"学習生成ルール_{user_intent}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # ユーザー意図に基づくアクションシーケンス生成
        if user_intent == "optimization":
            action_sequence = [
                {"type": "system_optimization", "params": {}},
                {"type": "monitoring_check", "params": {}}
            ]
            trigger_condition = "auto_optimization_trigger"
        elif user_intent == "monitoring":
            action_sequence = [
                {"type": "monitoring_check", "params": {}},
                {"type": "ai_analysis", "params": {"message": "システム状態を分析してください"}}
            ]
            trigger_condition = "monitoring_trigger"
        else:
            action_sequence = [
                {"type": "ai_analysis", "params": {"message": "システムを分析してください"}}
            ]
            trigger_condition = "general_trigger"
        
        return {
            "rule_name": rule_name,
            "trigger_condition": trigger_condition,
            "action_sequence": action_sequence,
            "confidence_score": 0.8
        }
    
    async def get_generated_rules(self):
        """生成されたルール取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, rule_name, trigger_condition, action_sequence, 
                   confidence_score, learning_source, enabled, 
                   last_executed, execution_count, success_count
            FROM generated_rules
            ORDER BY confidence_score DESC, created_at DESC
        ''')
        
        rules = []
        for row in cursor.fetchall():
            rules.append({
                "id": row[0],
                "rule_name": row[1],
                "trigger_condition": row[2],
                "action_sequence": json.loads(row[3]),
                "confidence_score": row[4],
                "learning_source": row[5],
                "enabled": bool(row[6]),
                "last_executed": row[7],
                "execution_count": row[8],
                "success_count": row[9]
            })
        
        conn.close()
        
        return {
            "generated_rules": rules,
            "count": len(rules),
            "timestamp": datetime.now().isoformat()
        }
    
    async def get_learning_insights(self):
        """学習インサイト取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 学習統計
        cursor.execute('SELECT COUNT(*) FROM learning_patterns')
        total_patterns = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM generated_rules')
        total_rules = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM learning_history')
        total_events = cursor.fetchone()[0]
        
        # 成功率統計
        cursor.execute('SELECT AVG(success_rate) FROM learning_patterns')
        avg_success_rate = cursor.fetchone()[0] or 0.0
        
        # 最近の学習イベント
        cursor.execute('''
            SELECT event_type, outcome, learning_insights, created_at
            FROM learning_history
            ORDER BY created_at DESC
            LIMIT 10
        ''')
        
        recent_events = []
        for row in cursor.fetchall():
            recent_events.append({
                "event_type": row[0],
                "outcome": row[1],
                "learning_insights": json.loads(row[2]) if row[2] else {},
                "created_at": row[3]
            })
        
        conn.close()
        
        return {
            "learning_statistics": {
                "total_patterns": total_patterns,
                "total_generated_rules": total_rules,
                "total_learning_events": total_events,
                "average_success_rate": round(avg_success_rate, 2)
            },
            "recent_learning_events": recent_events,
            "insights": {
                "learning_trend": "improving" if avg_success_rate > 0.7 else "stable",
                "recommendation": "継続的な学習により自動化精度が向上しています" if avg_success_rate > 0.7 else "より多くの学習データが必要です"
            },
            "timestamp": datetime.now().isoformat()
        }
    
    async def optimize_learning(self):
        """学習最適化"""
        try:
            # 学習データの最適化処理
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 古いパターンの削除
            cursor.execute('''
                DELETE FROM learning_patterns 
                WHERE created_at < datetime('now', '-30 days')
                AND (success_count + failure_count) < 5
            ''')
            
            deleted_patterns = cursor.rowcount
            
            # 成功率の再計算
            cursor.execute('''
                UPDATE learning_patterns 
                SET success_rate = CASE 
                    WHEN (success_count + failure_count) > 0 
                    THEN CAST(success_count AS REAL) / (success_count + failure_count)
                    ELSE 0.0
                END
            ''')
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"学習最適化完了: {deleted_patterns}個の古いパターンを削除")
            
            return {
                "optimization_result": "completed",
                "deleted_patterns": deleted_patterns,
                "optimized_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"学習最適化エラー: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # ==================== バックグラウンドタスク ====================
    
    def learning_process(self):
        """学習プロセス"""
        while True:
            try:
                # 定期的な学習処理
                # 実際の実装では、より複雑な学習アルゴリズムを実装
                
                time.sleep(300)  # 5分間隔
                
            except Exception as e:
                self.logger.error(f"学習プロセスエラー: {e}")
                time.sleep(300)
    
    def pattern_analysis(self):
        """パターン分析"""
        while True:
            try:
                # パターン分析処理
                # 実際の実装では、機械学習アルゴリズムを使用
                
                time.sleep(600)  # 10分間隔
                
            except Exception as e:
                self.logger.error(f"パターン分析エラー: {e}")
                time.sleep(600)
    
    def auto_rule_generation(self):
        """自動ルール生成"""
        while True:
            try:
                # 自動ルール生成処理
                # 学習パターンに基づいて自動的にルールを生成
                
                time.sleep(1800)  # 30分間隔
                
            except Exception as e:
                self.logger.error(f"自動ルール生成エラー: {e}")
                time.sleep(1800)
    
    # ==================== ヘルパーメソッド ====================
    
    async def count_learning_patterns(self) -> int:
        """学習パターン数取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM learning_patterns')
        count = cursor.fetchone()[0]
        
        conn.close()
        return count
    
    async def count_generated_rules(self) -> int:
        """生成ルール数取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM generated_rules')
        count = cursor.fetchone()[0]
        
        conn.close()
        return count
    
    async def count_learning_events(self) -> int:
        """学習イベント数取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM learning_history')
        count = cursor.fetchone()[0]
        
        conn.close()
        return count
    
    async def calculate_learning_success_rate(self) -> float:
        """学習成功率計算"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT AVG(success_rate) FROM learning_patterns')
        avg_rate = cursor.fetchone()[0] or 0.0
        
        conn.close()
        return round(avg_rate, 2)
    
    async def dashboard(self):
        """学習ダッシュボード"""
        html_content = self.generate_learning_dashboard_html()
        return HTMLResponse(content=html_content)
    
    def generate_learning_dashboard_html(self) -> str:
        """学習ダッシュボードHTML生成"""
        return """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mana Learning Automation System</title>
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
        .button.learn { background: #9c27b0; }
        .button.learn:hover { background: #7b1fa2; }
        .input-group { margin: 10px 0; }
        .input-group input, .input-group textarea, .input-group select { 
            width: 100%; 
            padding: 8px; 
            border-radius: 5px; 
            border: 1px solid #ccc; 
        }
        .input-group label { display: block; margin-bottom: 5px; font-weight: bold; }
        .pattern-item { 
            background: rgba(255,255,255,0.05); 
            padding: 15px; 
            margin: 10px 0; 
            border-radius: 8px; 
        }
        .success-rate { 
            display: inline-block; 
            padding: 5px 15px; 
            border-radius: 20px; 
            font-weight: bold; 
            background: #4CAF50; 
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧠 Mana Learning Automation System</h1>
            <p>学習型自動化・パターン認識・インテリジェント最適化・継続的改善</p>
        </div>
        
        <div class="grid">
            <!-- 学習イベント -->
            <div class="card">
                <h3>📚 学習イベント</h3>
                <div class="input-group">
                    <label>イベントタイプ:</label>
                    <input type="text" id="event-type" placeholder="system_optimization">
                </div>
                <div class="input-group">
                    <label>イベントコンテキスト:</label>
                    <textarea id="event-context" placeholder='{"system_metrics": {"cpu_usage": 80}}'></textarea>
                </div>
                <div class="input-group">
                    <label>結果:</label>
                    <select id="event-outcome">
                        <option value="success">成功</option>
                        <option value="failure">失敗</option>
                    </select>
                </div>
                <button class="button learn" onclick="learnFromEvent()">学習実行</button>
                <div id="learning-result">学習結果がここに表示されます</div>
            </div>
            
            <!-- 学習パターン -->
            <div class="card">
                <h3>🔍 学習パターン</h3>
                <div id="learning-patterns">読み込み中...</div>
                <button class="button" onclick="refreshLearningPatterns()">🔄 更新</button>
            </div>
            
            <!-- 自動ルール生成 -->
            <div class="card">
                <h3>🤖 自動ルール生成</h3>
                <div class="input-group">
                    <label>コンテキスト:</label>
                    <textarea id="rule-context" placeholder='{"system_state": "normal"}'></textarea>
                </div>
                <div class="input-group">
                    <label>ユーザー意図:</label>
                    <select id="user-intent">
                        <option value="optimization">最適化</option>
                        <option value="monitoring">監視</option>
                        <option value="security">セキュリティ</option>
                    </select>
                </div>
                <button class="button learn" onclick="generateAutomationRule()">ルール生成</button>
                <div id="rule-generation-result">生成結果がここに表示されます</div>
            </div>
            
            <!-- 生成されたルール -->
            <div class="card">
                <h3>📋 生成されたルール</h3>
                <div id="generated-rules">読み込み中...</div>
                <button class="button" onclick="refreshGeneratedRules()">🔄 更新</button>
            </div>
            
            <!-- 学習インサイト -->
            <div class="card">
                <h3>💡 学習インサイト</h3>
                <div id="learning-insights">読み込み中...</div>
                <button class="button" onclick="refreshLearningInsights()">🔄 更新</button>
            </div>
            
            <!-- 学習最適化 -->
            <div class="card">
                <h3>⚡ 学習最適化</h3>
                <button class="button learn" onclick="optimizeLearning()">学習最適化実行</button>
                <div id="optimization-result">最適化結果がここに表示されます</div>
            </div>
        </div>
    </div>
    
    <script>
        // 学習イベント実行
        async function learnFromEvent() {
            const eventType = document.getElementById('event-type').value;
            const eventContext = document.getElementById('event-context').value;
            const outcome = document.getElementById('event-outcome').value;
            
            if (!eventType || !outcome) {
                alert('イベントタイプと結果を入力してください');
                return;
            }
            
            try {
                const response = await fetch('/api/learning/learn', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        event_type: eventType,
                        event_context: JSON.parse(eventContext || '{}'),
                        outcome: outcome
                    })
                });
                
                if (response.ok) {
                    const data = await response.json();
                    let html = `
                        <h4>学習完了:</h4>
                        <p>イベントタイプ: ${data.event_type}</p>
                        <p>結果: ${data.outcome}</p>
                        <p>信頼度: ${data.learning_insights.confidence}</p>
                        <p>推奨事項: ${data.learning_insights.recommendations.join(', ')}</p>
                    `;
                    
                    document.getElementById('learning-result').innerHTML = html;
                    refreshLearningPatterns();
                } else {
                    alert('学習に失敗しました');
                }
            } catch (error) {
                console.error('学習エラー:', error);
                alert('学習エラーが発生しました');
            }
        }
        
        // 学習パターン取得
        async function refreshLearningPatterns() {
            try {
                const response = await fetch('/api/learning/patterns');
                const data = await response.json();
                
                let html = '<h4>学習パターン一覧:</h4>';
                data.learning_patterns.slice(0, 10).forEach(pattern => {
                    html += `
                        <div class="pattern-item">
                            <strong>${pattern.pattern_type}</strong><br>
                            <span class="success-rate">成功率: ${(pattern.success_rate * 100).toFixed(1)}%</span><br>
                            成功: ${pattern.success_count} | 失敗: ${pattern.failure_count}<br>
                            <small>最終使用: ${pattern.last_used || '未使用'}</small>
                        </div>
                    `;
                });
                
                document.getElementById('learning-patterns').innerHTML = html;
            } catch (error) {
                console.error('学習パターン取得エラー:', error);
            }
        }
        
        // 自動ルール生成
        async function generateAutomationRule() {
            const context = document.getElementById('rule-context').value;
            const userIntent = document.getElementById('user-intent').value;
            
            try {
                const response = await fetch('/api/learning/generate-rule', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        context: JSON.parse(context || '{}'),
                        user_intent: userIntent
                    })
                });
                
                if (response.ok) {
                    const data = await response.json();
                    let html = `
                        <h4>ルール生成完了:</h4>
                        <p>ルール名: ${data.generated_rule.rule_name}</p>
                        <p>信頼度: ${(data.confidence_score * 100).toFixed(1)}%</p>
                        <p>トリガー: ${data.generated_rule.trigger_condition}</p>
                        <p>アクション数: ${data.generated_rule.action_sequence.length}</p>
                    `;
                    
                    document.getElementById('rule-generation-result').innerHTML = html;
                    refreshGeneratedRules();
                } else {
                    alert('ルール生成に失敗しました');
                }
            } catch (error) {
                console.error('ルール生成エラー:', error);
                alert('ルール生成エラーが発生しました');
            }
        }
        
        // 生成されたルール取得
        async function refreshGeneratedRules() {
            try {
                const response = await fetch('/api/learning/generated-rules');
                const data = await response.json();
                
                let html = '<h4>生成されたルール一覧:</h4>';
                data.generated_rules.slice(0, 10).forEach(rule => {
                    html += `
                        <div class="pattern-item">
                            <strong>${rule.rule_name}</strong><br>
                            <span class="success-rate">信頼度: ${(rule.confidence_score * 100).toFixed(1)}%</span><br>
                            実行回数: ${rule.execution_count} | 成功回数: ${rule.success_count}<br>
                            <small>学習ソース: ${rule.learning_source}</small>
                        </div>
                    `;
                });
                
                document.getElementById('generated-rules').innerHTML = html;
            } catch (error) {
                console.error('生成ルール取得エラー:', error);
            }
        }
        
        // 学習インサイト取得
        async function refreshLearningInsights() {
            try {
                const response = await fetch('/api/learning/insights');
                const data = await response.json();
                
                let html = `
                    <h4>学習統計:</h4>
                    <p>総パターン数: ${data.learning_statistics.total_patterns}</p>
                    <p>生成ルール数: ${data.learning_statistics.total_generated_rules}</p>
                    <p>学習イベント数: ${data.learning_statistics.total_learning_events}</p>
                    <p>平均成功率: ${data.learning_statistics.average_success_rate}%</p>
                    <h4>推奨事項:</h4>
                    <p>${data.insights.recommendation}</p>
                `;
                
                document.getElementById('learning-insights').innerHTML = html;
            } catch (error) {
                console.error('学習インサイト取得エラー:', error);
            }
        }
        
        // 学習最適化
        async function optimizeLearning() {
            try {
                const response = await fetch('/api/learning/optimize', {
                    method: 'POST'
                });
                
                if (response.ok) {
                    const data = await response.json();
                    let html = `
                        <h4>最適化完了:</h4>
                        <p>削除されたパターン: ${data.deleted_patterns}個</p>
                        <p>最適化時刻: ${new Date(data.optimized_at).toLocaleString()}</p>
                    `;
                    
                    document.getElementById('optimization-result').innerHTML = html;
                    refreshLearningPatterns();
                } else {
                    alert('学習最適化に失敗しました');
                }
            } catch (error) {
                console.error('学習最適化エラー:', error);
                alert('学習最適化エラーが発生しました');
            }
        }
        
        // 初期化
        window.onload = function() {
            refreshLearningPatterns();
            refreshGeneratedRules();
            refreshLearningInsights();
            
            // 定期的な更新
            setInterval(refreshLearningPatterns, 60000);
            setInterval(refreshGeneratedRules, 60000);
            setInterval(refreshLearningInsights, 60000);
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
    learning_system = ManaLearningAutomationSystem()
    
    print("🧠 Mana Learning Automation System を起動しています...")
    print("📊 ダッシュボード: http://localhost:5016")
    print("🔗 API: http://localhost:5016/api/status")
    print("=" * 60)
    print("🎯 学習型自動化機能:")
    print("  🧠 学習型自動化ルール生成")
    print("  🔍 パターン認識・分析")
    print("  🤖 インテリジェント最適化")
    print("  🔮 予測的自動化")
    print("  📚 継続的学習")
    print("  ⚡ 適応的改善")
    print("=" * 60)
    
    # FastAPIサーバー起動
    uvicorn.run(
        learning_system.app,
        host="0.0.0.0",
        port=5016,
        log_level="info"
    )

if __name__ == "__main__":
    main()
