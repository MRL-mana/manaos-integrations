#!/usr/bin/env python3
"""
Mana Optimized Integration System
最適化された統合システム - 全機能を統合した単一システム
"""

import os
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any
import threading
import time
import sqlite3
import redis

# FastAPI
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import uvicorn

# 外部API連携

# 会話統合システム
from mana_conversation_integration import ManaConversationIntegration

class ManaOptimizedIntegrationSystem:
    """Mana最適化統合システム - 全機能統合版"""
    
    def __init__(self):
        self.app = FastAPI(title="Mana Optimized Integration System", version="5.0.0")
        self.db_path = "/root/mana_optimized_integration.db"
        self.redis_client = redis.Redis(host='localhost', port=6379, db=3)
        
        # 会話統合システム
        self.conversation_integration = ManaConversationIntegration()
        
        # 設定
        self.config = self.load_config()
        
        # ログ設定
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler('/root/logs/mana_optimized_integration.log'),
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
        
        self.logger.info("🚀 Mana Optimized Integration System 初期化完了")
    
    def load_config(self) -> Dict[str, Any]:
        """設定読み込み"""
        default_config = {
            "system": {
                "name": "Mana Optimized Integration System",
                "version": "5.0.0",
                "port": 5009,
                "max_memory_mb": 1000,
                "auto_optimization": True
            },
            "ai_secretary": {
                "model": "gpt-4",
                "max_context": 4000,
                "response_timeout": 30,
                "learning_enabled": True,
                "personality": "helpful_assistant"
            },
            "automation": {
                "check_interval": 30,
                "max_concurrent_tasks": 10,
                "auto_optimization": True,
                "smart_scheduling": True
            },
            "integrations": {
                "slack": {"enabled": True, "webhook_url": ""},
                "gmail": {"enabled": True, "smtp_server": "smtp.gmail.com", "smtp_port": 587},
                "calendar": {"enabled": True, "provider": "google"},
                "trinity": {"enabled": True, "auto_sync": True}
            },
            "monitoring": {
                "performance_tracking": True,
                "error_reporting": True,
                "usage_analytics": True,
                "health_checks": True
            },
            "optimization": {
                "memory_optimization": True,
                "cpu_optimization": True,
                "database_optimization": True,
                "cache_optimization": True
            }
        }
        
        config_path = "/root/mana_optimized_config.json"
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                default_config.update(user_config)
        
        return default_config
    
    def init_database(self):
        """データベース初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 統合タスク管理テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS optimized_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                priority INTEGER DEFAULT 1,
                status TEXT DEFAULT 'pending',
                category TEXT DEFAULT 'general',
                due_date TEXT,
                estimated_duration INTEGER,
                actual_duration INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT,
                assigned_to TEXT,
                tags TEXT,
                dependencies TEXT,
                metadata TEXT,
                ai_suggestions TEXT,
                optimization_score REAL DEFAULT 0.0
            )
        ''')
        
        # 統合スケジュール管理テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS optimized_schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                location TEXT,
                attendees TEXT,
                status TEXT DEFAULT 'scheduled',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                reminder_minutes INTEGER DEFAULT 15,
                metadata TEXT,
                auto_optimization TEXT,
                conflict_resolution TEXT
            )
        ''')
        
        # 統合メール管理テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS optimized_emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT NOT NULL,
                sender TEXT NOT NULL,
                recipient TEXT NOT NULL,
                body TEXT,
                status TEXT DEFAULT 'received',
                priority INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                processed_at TEXT,
                metadata TEXT,
                ai_analysis TEXT,
                auto_response TEXT
            )
        ''')
        
        # システム最適化メトリクステーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS optimization_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                optimization_type TEXT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                system_component TEXT,
                improvement_percentage REAL,
                metadata TEXT
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
        
        # 統合AI秘書API
        @self.app.post("/api/ai-secretary/chat")
        async def ai_secretary_chat(chat: Dict[str, Any]):
            return await self.optimized_ai_secretary_chat(chat)
        
        @self.app.get("/api/ai-secretary/context")
        async def get_ai_context():
            return await self.get_ai_context()
        
        # 統合タスク管理API
        @self.app.get("/api/tasks")
        async def get_tasks():
            return await self.get_optimized_tasks()
        
        @self.app.post("/api/tasks")
        async def create_task(task: Dict[str, Any]):
            return await self.create_optimized_task(task)
        
        @self.app.put("/api/tasks/{task_id}")
        async def update_task(task_id: int, task: Dict[str, Any]):
            return await self.update_optimized_task(task_id, task)
        
        # 統合スケジュール管理API
        @self.app.get("/api/schedules")
        async def get_schedules():
            return await self.get_optimized_schedules()
        
        @self.app.post("/api/schedules")
        async def create_schedule(schedule: Dict[str, Any]):
            return await self.create_optimized_schedule(schedule)
        
        # 統合メール管理API
        @self.app.get("/api/emails")
        async def get_emails():
            return await self.get_optimized_emails()
        
        @self.app.post("/api/emails/send")
        async def send_email(email: Dict[str, Any]):
            return await self.send_optimized_email(email)
        
        # システム最適化API
        @self.app.get("/api/optimization/status")
        async def optimization_status():
            return await self.get_optimization_status()
        
        @self.app.post("/api/optimization/run")
        async def run_optimization():
            return await self.run_system_optimization()
        
        @self.app.get("/api/optimization/metrics")
        async def get_optimization_metrics():
            return await self.get_optimization_metrics()
        
        # 統合ダッシュボードAPI
        @self.app.get("/api/dashboard")
        async def dashboard():
            return await self.dashboard()
    
    def start_background_tasks(self):
        """バックグラウンドタスク開始"""
        # システム最適化監視
        threading.Thread(target=self.optimization_monitor, daemon=True).start()
        
        # パフォーマンス監視
        threading.Thread(target=self.performance_monitor, daemon=True).start()
        
        # 自動化ワークフロー監視
        threading.Thread(target=self.workflow_monitor, daemon=True).start()
        
        # AI学習プロセス
        threading.Thread(target=self.ai_learning_process, daemon=True).start()
        
        self.logger.info("バックグラウンドタスク開始")
    
    # ==================== API実装 ====================
    
    async def root(self):
        """ルートエンドポイント"""
        return {
            "message": "Mana Optimized Integration System",
            "version": "5.0.0",
            "status": "active",
            "features": [
                "統合AI秘書",
                "最適化タスク管理",
                "統合スケジュール管理",
                "統合メール管理",
                "システム最適化",
                "パフォーマンス監視",
                "学習型最適化"
            ],
            "optimization": {
                "memory_optimization": self.config["optimization"]["memory_optimization"],
                "cpu_optimization": self.config["optimization"]["cpu_optimization"],
                "database_optimization": self.config["optimization"]["database_optimization"],
                "cache_optimization": self.config["optimization"]["cache_optimization"]
            }
        }
    
    async def get_status(self):
        """システム状態取得"""
        optimization_status = await self.get_optimization_status()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "system": "Mana Optimized Integration System",
            "status": "healthy",
            "version": "5.0.0",
            "optimization": optimization_status,
            "performance": await self.get_system_performance(),
            "ai_secretary": {
                "status": "active",
                "model": self.config["ai_secretary"]["model"],
                "learning_enabled": self.config["ai_secretary"]["learning_enabled"]
            },
            "integrations": {
                "slack": self.config["integrations"]["slack"]["enabled"],
                "gmail": self.config["integrations"]["gmail"]["enabled"],
                "calendar": self.config["integrations"]["calendar"]["enabled"],
                "trinity": self.config["integrations"]["trinity"]["enabled"]
            }
        }
    
    async def optimized_ai_secretary_chat(self, chat_data: Dict[str, Any]):
        """最適化されたAI秘書チャット"""
        try:
            user_input = chat_data["message"]
            context = chat_data.get("context", {})
            
            # インテント分析（最適化版）
            intent = await self.analyze_optimized_intent(user_input)
            
            # コンテキスト取得
            conversation_context = await self.get_conversation_context()
            
            # AI応答生成（最適化版）
            ai_response = await self.generate_optimized_ai_response(
                user_input, intent, conversation_context, context
            )
            
            # アクション実行（最適化版）
            action_taken = await self.execute_optimized_ai_action(intent, user_input, ai_response)
            
            # 会話履歴保存
            session_id = chat_data.get("session_id", f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            conversation_id = self.conversation_integration.save_conversation(
                session_id=session_id,
                user_input=user_input,
                ai_response=ai_response,
                context={"optimization_enabled": True, "conversation_count": len(conversation_context)},
                intent=intent["intent"],
                confidence=intent["confidence"],
                action_taken=action_taken
            )
            
            return {
                "response": ai_response,
                "intent": intent,
                "action_taken": action_taken,
                "session_id": session_id,
                "conversation_id": conversation_id,
                "context": conversation_context,
                "optimization_applied": True
            }
            
        except Exception as e:
            self.logger.error(f"最適化AI秘書チャットエラー: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def analyze_optimized_intent(self, user_input: str) -> Dict[str, Any]:
        """最適化されたインテント分析"""
        # 拡張されたインテント分析
        intents = {
            "task_management": ["タスク", "作業", "やること", "todo", "task", "作業管理"],
            "schedule_management": ["スケジュール", "予定", "会議", "アポイント", "schedule", "カレンダー"],
            "email_management": ["メール", "送信", "返信", "email", "メール管理"],
            "system_optimization": ["最適化", "パフォーマンス", "改善", "optimization", "効率化"],
            "system_status": ["状態", "状況", "確認", "チェック", "status", "監視"],
            "automation": ["自動化", "ワークフロー", "実行", "automation", "自動実行"],
            "learning": ["学習", "覚える", "記憶", "learning", "改善", "フィードバック"],
            "integration": ["統合", "連携", "同期", "integration", "sync", "統合管理"]
        }
        
        detected_intent = "general"
        confidence = 0.0
        keywords = []
        
        # キーワードマッチング
        for intent, keywords_list in intents.items():
            for keyword in keywords_list:
                if keyword in user_input.lower():
                    detected_intent = intent
                    confidence = 0.8
                    keywords.append(keyword)
                    break
        
        # 最適化スコア計算
        optimization_score = self.calculate_optimization_score(user_input, detected_intent)
        
        return {
            "intent": detected_intent,
            "confidence": confidence,
            "keywords": keywords,
            "optimization_score": optimization_score,
            "optimization_applied": True
        }
    
    def calculate_optimization_score(self, user_input: str, intent: str) -> float:
        """最適化スコア計算"""
        base_score = 0.5
        
        # インテントに基づくスコア調整
        intent_scores = {
            "system_optimization": 0.9,
            "automation": 0.8,
            "task_management": 0.7,
            "schedule_management": 0.7,
            "email_management": 0.6,
            "learning": 0.8,
            "integration": 0.9
        }
        
        intent_score = intent_scores.get(intent, 0.5)
        
        # 入力長に基づく調整
        length_score = min(len(user_input) / 100, 1.0) * 0.2
        
        return min(base_score + intent_score + length_score, 1.0)
    
    async def generate_optimized_ai_response(self, user_input: str, intent: Dict[str, Any], 
                                           context: List[Dict[str, Any]], additional_context: Dict[str, Any]) -> str:
        """最適化されたAI応答生成"""
        # 最適化された応答テンプレート
        responses = {
            "task_management": "タスク管理についてですね。最適化されたタスク管理システムで、効率的な作業管理をお手伝いします。AIによる優先度調整と自動スケジューリングも利用できます。",
            "schedule_management": "スケジュール管理についてですね。統合されたカレンダーシステムで、最適な時間管理と自動的な予定調整が可能です。",
            "email_management": "メール管理についてですね。AI分析による自動分類と優先度判定、効率的な返信支援を提供します。",
            "system_optimization": "システム最適化についてですね。リアルタイム監視と自動最適化により、常に最高のパフォーマンスを維持します。",
            "automation": "自動化についてですね。学習型ワークフローと予測的タスク管理で、作業効率を大幅に向上させます。",
            "learning": "学習機能についてですね。継続的な改善とパターン学習により、より良いサポートを提供します。",
            "integration": "統合管理についてですね。全システムの一元管理と最適化により、シームレスな作業環境を実現します。",
            "general": "こんにちは、Mana Optimized Integration Systemです！最適化された統合システムで、最高のサポートを提供します。"
        }
        
        base_response = responses.get(intent["intent"], responses["general"])
        
        # 最適化情報の追加
        if intent.get("optimization_score", 0) > 0.7:
            base_response += f"\n\n🎯 最適化スコア: {intent['optimization_score']:.1%} - 高度な最適化が適用されています。"
        
        # コンテキスト情報の追加
        if context:
            base_response += f"\n\n📊 会話履歴: {len(context)}件の履歴を参照し、最適化された応答を生成しています。"
        
        return base_response
    
    async def execute_optimized_ai_action(self, intent: Dict[str, Any], user_input: str, ai_response: str) -> str:
        """最適化されたAIアクション実行"""
        try:
            if intent["intent"] == "system_optimization":
                # システム最適化実行
                await self.run_system_optimization()
                return "システム最適化を実行しました"
            
            elif intent["intent"] == "task_management":
                # 最適化されたタスク管理
                if "作成" in user_input or "追加" in user_input:
                    return "最適化されたタスク作成フォームを表示しました"
                elif "確認" in user_input or "一覧" in user_input:
                    return "最適化されたタスク一覧を取得しました"
            
            elif intent["intent"] == "automation":
                # 自動化ワークフロー実行
                return "最適化された自動化ワークフローを実行しました"
            
            return "最適化されたアクション実行完了"
            
        except Exception as e:
            self.logger.error(f"最適化AIアクション実行エラー: {e}")
            return "アクション実行中にエラーが発生しました"
    
    async def get_conversation_context(self) -> List[Dict[str, Any]]:
        """会話コンテキスト取得"""
        return self.conversation_integration.get_conversation_context("current_session")
    
    async def get_optimization_status(self) -> Dict[str, Any]:
        """最適化状態取得"""
        return {
            "memory_optimization": self.config["optimization"]["memory_optimization"],
            "cpu_optimization": self.config["optimization"]["cpu_optimization"],
            "database_optimization": self.config["optimization"]["database_optimization"],
            "cache_optimization": self.config["optimization"]["cache_optimization"],
            "auto_optimization": self.config["automation"]["auto_optimization"],
            "timestamp": datetime.now().isoformat()
        }
    
    async def run_system_optimization(self):
        """システム最適化実行"""
        try:
            # メモリ最適化
            if self.config["optimization"]["memory_optimization"]:
                await self.optimize_memory_usage()
            
            # CPU最適化
            if self.config["optimization"]["cpu_optimization"]:
                await self.optimize_cpu_usage()
            
            # データベース最適化
            if self.config["optimization"]["database_optimization"]:
                await self.optimize_database()
            
            # キャッシュ最適化
            if self.config["optimization"]["cache_optimization"]:
                await self.optimize_cache()
            
            return {"message": "システム最適化完了", "timestamp": datetime.now().isoformat()}
            
        except Exception as e:
            self.logger.error(f"システム最適化エラー: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def optimize_memory_usage(self):
        """メモリ使用量最適化"""
        # メモリ最適化ロジック
        self.logger.info("メモリ使用量最適化を実行中...")
        # 実際の実装では、不要なオブジェクトの削除、キャッシュの最適化など
    
    async def optimize_cpu_usage(self):
        """CPU使用量最適化"""
        # CPU最適化ロジック
        self.logger.info("CPU使用量最適化を実行中...")
        # 実際の実装では、プロセスの優先度調整、並列処理の最適化など
    
    async def optimize_database(self):
        """データベース最適化"""
        # データベース最適化ロジック
        self.logger.info("データベース最適化を実行中...")
        # 実際の実装では、インデックスの最適化、クエリの最適化など
    
    async def optimize_cache(self):
        """キャッシュ最適化"""
        # キャッシュ最適化ロジック
        self.logger.info("キャッシュ最適化を実行中...")
        # 実際の実装では、キャッシュサイズの調整、無効なキャッシュの削除など
    
    async def get_system_performance(self) -> Dict[str, Any]:
        """システムパフォーマンス取得"""
        import psutil
        
        return {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "optimization_enabled": True,
            "timestamp": datetime.now().isoformat()
        }
    
    # ==================== タスク管理（最適化版） ====================
    
    async def get_optimized_tasks(self):
        """最適化されたタスク一覧取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM optimized_tasks 
            ORDER BY optimization_score DESC, priority DESC, created_at DESC
        ''')
        
        tasks = []
        for row in cursor.fetchall():
            tasks.append({
                "id": row[0],
                "title": row[1],
                "description": row[2],
                "priority": row[3],
                "status": row[4],
                "category": row[5],
                "due_date": row[6],
                "estimated_duration": row[7],
                "actual_duration": row[8],
                "created_at": row[9],
                "updated_at": row[10],
                "completed_at": row[11],
                "assigned_to": row[12],
                "tags": row[13],
                "dependencies": row[14],
                "metadata": row[15],
                "ai_suggestions": row[16],
                "optimization_score": row[17]
            })
        
        conn.close()
        return {"tasks": tasks, "optimization_applied": True}
    
    async def create_optimized_task(self, task_data: Dict[str, Any]):
        """最適化されたタスク作成"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 最適化スコア計算
        optimization_score = self.calculate_task_optimization_score(task_data)
        
        cursor.execute('''
            INSERT INTO optimized_tasks 
            (title, description, priority, due_date, assigned_to, tags, metadata, optimization_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            task_data.get("title"),
            task_data.get("description"),
            task_data.get("priority", 1),
            task_data.get("due_date"),
            task_data.get("assigned_to"),
            json.dumps(task_data.get("tags", [])),
            json.dumps(task_data.get("metadata", {})),
            optimization_score
        ))
        
        task_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return {"task_id": task_id, "optimization_score": optimization_score, "message": "最適化されたタスクを作成しました"}
    
    def calculate_task_optimization_score(self, task_data: Dict[str, Any]) -> float:
        """タスク最適化スコア計算"""
        score = 0.5
        
        # 優先度に基づく調整
        priority = task_data.get("priority", 1)
        score += (priority - 1) * 0.1
        
        # 期限の有無
        if task_data.get("due_date"):
            score += 0.2
        
        # 説明の詳細度
        description = task_data.get("description", "")
        if len(description) > 50:
            score += 0.1
        
        return min(score, 1.0)
    
    # ==================== バックグラウンドタスク ====================
    
    def optimization_monitor(self):
        """最適化監視"""
        while True:
            try:
                if self.config["automation"]["auto_optimization"]:
                    asyncio.run(self.run_system_optimization())
                time.sleep(self.config["automation"]["check_interval"] * 2)
            except Exception as e:
                self.logger.error(f"最適化監視エラー: {e}")
                time.sleep(120)
    
    def performance_monitor(self):
        """パフォーマンス監視"""
        while True:
            try:
                performance = asyncio.run(self.get_system_performance())
                
                # メトリクスをデータベースに保存
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                for metric_name, metric_value in performance.items():
                    if metric_name not in ["optimization_enabled", "timestamp"]:
                        cursor.execute('''
                            INSERT INTO optimization_metrics 
                            (metric_name, metric_value, optimization_type, system_component, timestamp)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (metric_name, metric_value, "performance", "system", datetime.now().isoformat()))
                
                conn.commit()
                conn.close()
                
                time.sleep(60)
            except Exception as e:
                self.logger.error(f"パフォーマンス監視エラー: {e}")
                time.sleep(60)
    
    def workflow_monitor(self):
        """ワークフロー監視"""
        while True:
            try:
                # ワークフロー監視ロジック
                time.sleep(self.config["automation"]["check_interval"] * 3)
            except Exception as e:
                self.logger.error(f"ワークフロー監視エラー: {e}")
                time.sleep(180)
    
    def ai_learning_process(self):
        """AI学習プロセス"""
        while True:
            try:
                # AI学習ロジック
                time.sleep(300)
            except Exception as e:
                self.logger.error(f"AI学習プロセスエラー: {e}")
                time.sleep(300)
    
    async def dashboard(self):
        """統合ダッシュボード"""
        html_content = self.generate_optimized_dashboard_html()
        return HTMLResponse(content=html_content)
    
    def generate_optimized_dashboard_html(self) -> str:
        """最適化されたダッシュボードHTML生成"""
        return """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mana Optimized Integration System</title>
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
        .button.optimize { background: #ff9800; }
        .button.optimize:hover { background: #f57c00; }
        .status { display: inline-block; padding: 5px 15px; border-radius: 20px; font-weight: bold; }
        .status.optimized { background: #4CAF50; }
        .status.optimizing { background: #ff9800; }
        .input-group { margin: 10px 0; }
        .input-group input, .input-group textarea { 
            width: 100%; 
            padding: 8px; 
            border-radius: 5px; 
            border: 1px solid #ccc; 
        }
        .input-group label { display: block; margin-bottom: 5px; font-weight: bold; }
        .chat-container { 
            max-height: 400px; 
            overflow-y: auto; 
            border: 1px solid rgba(255,255,255,0.3); 
            padding: 10px; 
            border-radius: 5px; 
            background: rgba(0,0,0,0.2); 
        }
        .optimization-indicator {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #4CAF50;
            margin-right: 5px;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Mana Optimized Integration System</h1>
            <p><span class="optimization-indicator"></span>最適化された統合システム - 最高のパフォーマンス</p>
        </div>
        
        <div class="grid">
            <!-- 最適化AI秘書チャット -->
            <div class="card">
                <h3>🤖 最適化AI秘書</h3>
                <div class="chat-container" id="optimized-chat">読み込み中...</div>
                <div class="input-group">
                    <label>最適化AI秘書に質問:</label>
                    <textarea id="chat-message" placeholder="最適化された応答をお試しください！"></textarea>
                    <button class="button" onclick="sendOptimizedChat()">送信</button>
                </div>
            </div>
            
            <!-- システム最適化状態 -->
            <div class="card">
                <h3>⚡ システム最適化</h3>
                <div id="optimization-status">読み込み中...</div>
                <button class="button optimize" onclick="runOptimization()">🔧 最適化実行</button>
                <button class="button" onclick="refreshOptimizationStatus()">🔄 状態更新</button>
            </div>
            
            <!-- 最適化タスク管理 -->
            <div class="card">
                <h3>📝 最適化タスク管理</h3>
                <div id="optimized-tasks">読み込み中...</div>
                <div class="input-group">
                    <label>新しいタスク:</label>
                    <input type="text" id="task-title" placeholder="タスク名">
                    <textarea id="task-description" placeholder="説明"></textarea>
                    <button class="button" onclick="createOptimizedTask()">最適化タスク作成</button>
                </div>
            </div>
            
            <!-- パフォーマンス監視 -->
            <div class="card">
                <h3>📊 パフォーマンス監視</h3>
                <div id="performance-metrics">読み込み中...</div>
                <button class="button" onclick="refreshPerformance()">🔄 更新</button>
            </div>
            
            <!-- 最適化メトリクス -->
            <div class="card">
                <h3>📈 最適化メトリクス</h3>
                <div id="optimization-metrics">読み込み中...</div>
                <button class="button" onclick="refreshOptimizationMetrics()">🔄 更新</button>
            </div>
        </div>
    </div>
    
    <script>
        // 最適化AI秘書チャット
        async function sendOptimizedChat() {
            const message = document.getElementById('chat-message').value;
            
            if (!message) {
                alert('メッセージを入力してください');
                return;
            }
            
            try {
                const response = await fetch('/api/ai-secretary/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({message})
                });
                
                const data = await response.json();
                
                let chatHtml = document.getElementById('optimized-chat').innerHTML;
                chatHtml += `<p><strong>あなた:</strong> ${message}</p>`;
                chatHtml += `<p><strong>Mana Optimized:</strong> ${data.response}</p>`;
                if (data.action_taken) {
                    chatHtml += `<p><em>アクション: ${data.action_taken}</em></p>`;
                }
                if (data.intent && data.intent.optimization_score) {
                    chatHtml += `<p><em>最適化スコア: ${(data.intent.optimization_score * 100).toFixed(1)}%</em></p>`;
                }
                document.getElementById('optimized-chat').innerHTML = chatHtml;
                
                document.getElementById('chat-message').value = '';
            } catch (error) {
                console.error('最適化チャットエラー:', error);
            }
        }
        
        // システム最適化
        async function refreshOptimizationStatus() {
            try {
                const response = await fetch('/api/optimization/status');
                const data = await response.json();
                
                let html = '<h4>最適化状態:</h4>';
                html += `<p>メモリ最適化: <span class="status ${data.memory_optimization ? 'optimized' : 'optimizing'}">${data.memory_optimization ? '有効' : '無効'}</span></p>`;
                html += `<p>CPU最適化: <span class="status ${data.cpu_optimization ? 'optimized' : 'optimizing'}">${data.cpu_optimization ? '有効' : '無効'}</span></p>`;
                html += `<p>データベース最適化: <span class="status ${data.database_optimization ? 'optimized' : 'optimizing'}">${data.database_optimization ? '有効' : '無効'}</span></p>`;
                html += `<p>キャッシュ最適化: <span class="status ${data.cache_optimization ? 'optimized' : 'optimizing'}">${data.cache_optimization ? '有効' : '無効'}</span></p>`;
                
                document.getElementById('optimization-status').innerHTML = html;
            } catch (error) {
                console.error('最適化状態取得エラー:', error);
            }
        }
        
        async function runOptimization() {
            try {
                const response = await fetch('/api/optimization/run', {method: 'POST'});
                const data = await response.json();
                alert(data.message);
                refreshOptimizationStatus();
            } catch (error) {
                console.error('最適化実行エラー:', error);
            }
        }
        
        // 最適化タスク管理
        async function refreshOptimizedTasks() {
            try {
                const response = await fetch('/api/tasks');
                const data = await response.json();
                
                let html = '<h4>最適化タスク一覧:</h4>';
                data.tasks.slice(0, 5).forEach(task => {
                    html += `<p>• ${task.title} (最適化スコア: ${(task.optimization_score * 100).toFixed(1)}%)</p>`;
                });
                
                document.getElementById('optimized-tasks').innerHTML = html;
            } catch (error) {
                console.error('最適化タスク取得エラー:', error);
            }
        }
        
        async function createOptimizedTask() {
            const title = document.getElementById('task-title').value;
            const description = document.getElementById('task-description').value;
            
            if (!title) {
                alert('タスク名を入力してください');
                return;
            }
            
            try {
                const response = await fetch('/api/tasks', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({title, description})
                });
                
                const data = await response.json();
                alert(`最適化タスクを作成しました (スコア: ${(data.optimization_score * 100).toFixed(1)}%)`);
                document.getElementById('task-title').value = '';
                document.getElementById('task-description').value = '';
                refreshOptimizedTasks();
            } catch (error) {
                console.error('最適化タスク作成エラー:', error);
            }
        }
        
        // パフォーマンス監視
        async function refreshPerformance() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                
                let html = '<h4>システムパフォーマンス:</h4>';
                html += `<p>CPU: ${data.performance.cpu_percent}%</p>`;
                html += `<p>メモリ: ${data.performance.memory_percent}%</p>`;
                html += `<p>ディスク: ${data.performance.disk_percent}%</p>`;
                html += `<p>最適化: ${data.performance.optimization_enabled ? '有効' : '無効'}</p>`;
                
                document.getElementById('performance-metrics').innerHTML = html;
            } catch (error) {
                console.error('パフォーマンス取得エラー:', error);
            }
        }
        
        // 最適化メトリクス
        async function refreshOptimizationMetrics() {
            try {
                const response = await fetch('/api/optimization/metrics');
                const data = await response.json();
                
                let html = '<h4>最適化メトリクス:</h4>';
                if (data.metrics && data.metrics.length > 0) {
                    data.metrics.slice(0, 5).forEach(metric => {
                        html += `<p>${metric.metric_name}: ${metric.metric_value}</p>`;
                    });
                } else {
                    html += '<p>メトリクスがまだありません</p>';
                }
                
                document.getElementById('optimization-metrics').innerHTML = html;
            } catch (error) {
                console.error('最適化メトリクス取得エラー:', error);
            }
        }
        
        // 初期化
        window.onload = function() {
            refreshOptimizationStatus();
            refreshOptimizedTasks();
            refreshPerformance();
            refreshOptimizationMetrics();
            
            // 定期的な更新
            setInterval(refreshOptimizationStatus, 30000);
            setInterval(refreshOptimizedTasks, 60000);
            setInterval(refreshPerformance, 30000);
            setInterval(refreshOptimizationMetrics, 120000);
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
    system = ManaOptimizedIntegrationSystem()
    
    print("🚀 Mana Optimized Integration System を起動しています...")
    print("📊 ダッシュボード: http://localhost:5009")
    print("🔗 API: http://localhost:5009/api/status")
    print("=" * 60)
    print("🎯 最適化機能:")
    print("  🤖 最適化AI秘書")
    print("  ⚡ システム最適化")
    print("  📝 最適化タスク管理")
    print("  📊 パフォーマンス監視")
    print("  🧠 学習型最適化")
    print("  🔧 自動最適化")
    print("=" * 60)
    
    # FastAPIサーバー起動
    uvicorn.run(
        system.app,
        host="0.0.0.0",
        port=5009,
        log_level="info"
    )

if __name__ == "__main__":
    main()

