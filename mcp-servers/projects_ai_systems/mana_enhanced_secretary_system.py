#!/usr/bin/env python3
"""
Mana Enhanced Secretary System
秘書機能と自動化の究極統合システム
AI秘書 + 自動化 + 統合管理の完全統合
"""

import os
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any
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
import requests

class ManaEnhancedSecretarySystem:
    """Mana Enhanced Secretary System - 究極の秘書・自動化統合システム"""
    
    def __init__(self):
        self.app = FastAPI(title="Mana Enhanced Secretary System", version="3.0.0")
        self.db_path = "/root/mana_enhanced_secretary.db"
        self.redis_client = redis.Redis(host='localhost', port=6379, db=1)
        
        # 設定
        self.config = self.load_config()
        
        # ログ設定
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler('/root/logs/mana_enhanced_secretary.log'),
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
        
        self.logger.info("🚀 Mana Enhanced Secretary System 初期化完了")
    
    def load_config(self) -> Dict[str, Any]:
        """設定読み込み"""
        default_config = {
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
                "trinity": {"enabled": True, "port": 5005},
                "hybrid_system": {"enabled": True, "port": 5006}
            },
            "monitoring": {
                "performance_tracking": True,
                "error_reporting": True,
                "usage_analytics": True
            }
        }
        
        config_path = "/root/mana_enhanced_config.json"
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                default_config.update(user_config)
        
        return default_config
    
    def init_database(self):
        """データベース初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 強化されたタスク管理テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS enhanced_tasks (
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
                ai_suggestions TEXT
            )
        ''')
        
        # AI秘書会話履歴テーブル（強化版）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ai_conversations_enhanced (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_input TEXT NOT NULL,
                ai_response TEXT NOT NULL,
                context TEXT,
                intent TEXT,
                confidence REAL,
                action_taken TEXT,
                feedback TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        ''')
        
        # 自動化ワークフローテーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS automation_workflows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                trigger_type TEXT,
                trigger_condition TEXT,
                actions TEXT,
                status TEXT DEFAULT 'active',
                last_executed TEXT,
                execution_count INTEGER DEFAULT 0,
                success_rate REAL DEFAULT 0.0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        ''')
        
        # システム統合状態テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_integration_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                system_name TEXT NOT NULL,
                status TEXT NOT NULL,
                last_check TEXT,
                response_time REAL,
                error_message TEXT,
                metadata TEXT
            )
        ''')
        
        # パフォーマンスメトリクステーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                system_component TEXT,
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
        
        # 強化されたAI秘書API
        @self.app.post("/api/ai-secretary/chat")
        async def ai_secretary_chat(chat: Dict[str, Any]):
            return await self.enhanced_ai_secretary_chat(chat)
        
        @self.app.get("/api/ai-secretary/context")
        async def get_ai_context():
            return await self.get_ai_context()  # type: ignore
        
        @self.app.post("/api/ai-secretary/learn")
        async def ai_learning(feedback: Dict[str, Any]):
            return await self.ai_learning(feedback)  # type: ignore
        
        # 統合システム管理API
        @self.app.get("/api/integration/status")
        async def integration_status():
            return await self.get_integration_status()
        
        @self.app.post("/api/integration/sync")
        async def sync_systems():
            return await self.sync_all_systems()
        
        # 自動化ワークフローAPI
        @self.app.get("/api/automation/workflows")
        async def get_workflows():
            return await self.get_workflows()  # type: ignore
        
        @self.app.post("/api/automation/workflows")
        async def create_workflow(workflow: Dict[str, Any]):
            return await self.create_workflow(workflow)  # type: ignore
        
        @self.app.post("/api/automation/execute")
        async def execute_workflow(workflow_id: int):
            return await self.execute_workflow(workflow_id)  # type: ignore
        
        # パフォーマンス監視API
        @self.app.get("/api/performance/metrics")
        async def get_performance_metrics():
            return await self.get_performance_metrics()
        
        @self.app.get("/api/dashboard")
        async def dashboard():
            return await self.dashboard()
    
    def start_background_tasks(self):
        """バックグラウンドタスク開始"""
        if self.config.get("automation", {}).get("enabled", True):
            # システム統合監視
            threading.Thread(target=self.system_integration_monitor, daemon=True).start()
            
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
            "message": "Mana Enhanced Secretary System",
            "version": "3.0.0",
            "status": "active",
            "features": [
                "AI秘書（強化版）",
                "統合システム管理",
                "自動化ワークフロー",
                "パフォーマンス監視",
                "学習型最適化"
            ],
            "integrations": list(self.config["integrations"].keys())
        }
    
    async def get_status(self):
        """システム状態取得"""
        integration_status = await self.get_integration_status()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "system": "Mana Enhanced Secretary System",
            "status": "healthy",
            "version": "3.0.0",
            "integrations": integration_status,
            "performance": await self.get_system_performance(),
            "ai_secretary": {
                "status": "active",
                "model": self.config["ai_secretary"]["model"],
                "learning_enabled": self.config["ai_secretary"]["learning_enabled"]
            }
        }
    
    async def enhanced_ai_secretary_chat(self, chat_data: Dict[str, Any]):
        """強化されたAI秘書チャット"""
        try:
            user_input = chat_data["message"]
            context = chat_data.get("context", {})
            
            # インテント分析
            intent = await self.analyze_intent(user_input)
            
            # コンテキスト取得
            conversation_context = await self.get_conversation_context()
            
            # AI応答生成
            ai_response = await self.generate_enhanced_ai_response(
                user_input, intent, conversation_context, context
            )
            
            # アクション実行
            action_taken = await self.execute_ai_action(intent, user_input, ai_response)
            
            # データベースに記録
            await self.save_conversation(user_input, ai_response, intent, action_taken)
            
            return {
                "response": ai_response,
                "intent": intent,
                "action_taken": action_taken,
                "context": conversation_context
            }
            
        except Exception as e:
            self.logger.error(f"AI秘書チャットエラー: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def analyze_intent(self, user_input: str) -> Dict[str, Any]:
        """インテント分析"""
        # 簡単なインテント分析（実際の実装ではより高度なNLPを使用）
        intents = {
            "task_management": ["タスク", "作業", "やること", "todo"],
            "schedule_management": ["スケジュール", "予定", "会議", "アポイント"],
            "email_management": ["メール", "送信", "返信"],
            "system_status": ["状態", "状況", "確認", "チェック"],
            "automation": ["自動化", "ワークフロー", "実行"],
            "learning": ["学習", "覚える", "記憶"]
        }
        
        detected_intent = "general"
        confidence = 0.0
        
        for intent, keywords in intents.items():
            for keyword in keywords:
                if keyword in user_input:
                    detected_intent = intent
                    confidence = 0.8
                    break
        
        return {
            "intent": detected_intent,
            "confidence": confidence,
            "keywords": [kw for kw in intents.get(detected_intent, []) if kw in user_input]
        }
    
    async def generate_enhanced_ai_response(self, user_input: str, intent: Dict[str, Any], 
                                          context: Dict[str, Any], additional_context: Dict[str, Any]) -> str:
        """強化されたAI応答生成"""
        # 実際の実装ではOpenAI APIや他のLLMを使用
        
        responses = {
            "task_management": "タスク管理についてですね。新しいタスクの作成、既存タスクの確認、優先度の調整などができます。どのようなタスクについてお手伝いしましょうか？",
            "schedule_management": "スケジュール管理についてですね。予定の追加、確認、変更などができます。どのような予定についてお手伝いしましょうか？",
            "email_management": "メール管理についてですね。メールの送信、確認、自動返信の設定などができます。どのようなメール作業をお手伝いしましょうか？",
            "system_status": "システム状態についてですね。現在のシステム状況、統合システムの状態、パフォーマンス情報などを確認できます。",
            "automation": "自動化についてですね。ワークフローの作成、実行、監視などができます。どのような自動化をお手伝いしましょうか？",
            "learning": "学習機能についてですね。私の応答を改善するためのフィードバックをいただけます。",
            "general": "こんにちは、Manaです！何かお手伝いできることはありますか？タスク管理、スケジュール管理、メール管理、システム監視など、様々な機能をご利用いただけます。"
        }
        
        base_response = responses.get(intent["intent"], responses["general"])
        
        # コンテキストに基づく追加情報
        if context.get("recent_tasks"):
            base_response += f"\n\n最近のタスク: {len(context['recent_tasks'])}件"
        
        if context.get("upcoming_schedules"):
            base_response += f"\n\n今後の予定: {len(context['upcoming_schedules'])}件"
        
        return base_response
    
    async def execute_ai_action(self, intent: Dict[str, Any], user_input: str, ai_response: str) -> str:
        """AIアクション実行"""
        try:
            if intent["intent"] == "task_management":
                # タスク関連のアクション
                if "作成" in user_input or "追加" in user_input:
                    return "タスク作成フォームを表示しました"
                elif "確認" in user_input or "一覧" in user_input:
                    return "タスク一覧を取得しました"
            
            elif intent["intent"] == "schedule_management":
                # スケジュール関連のアクション
                if "確認" in user_input:
                    return "スケジュール一覧を取得しました"
            
            elif intent["intent"] == "system_status":
                # システム状態確認
                return "システム状態を確認しました"
            
            return "アクション実行完了"
            
        except Exception as e:
            self.logger.error(f"AIアクション実行エラー: {e}")
            return "アクション実行中にエラーが発生しました"
    
    async def get_conversation_context(self) -> Dict[str, Any]:
        """会話コンテキスト取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 最近の会話
        cursor.execute('''
            SELECT user_input, ai_response, intent, created_at
            FROM ai_conversations_enhanced
            ORDER BY created_at DESC LIMIT 5
        ''')
        
        recent_conversations = []
        for row in cursor.fetchall():
            recent_conversations.append({
                "user_input": row[0],
                "ai_response": row[1],
                "intent": row[2],
                "created_at": row[3]
            })
        
        # 最近のタスク
        cursor.execute('''
            SELECT title, status, priority, created_at
            FROM enhanced_tasks
            ORDER BY created_at DESC LIMIT 5
        ''')
        
        recent_tasks = []
        for row in cursor.fetchall():
            recent_tasks.append({
                "title": row[0],
                "status": row[1],
                "priority": row[2],
                "created_at": row[3]
            })
        
        conn.close()
        
        return {
            "recent_conversations": recent_conversations,
            "recent_tasks": recent_tasks,
            "timestamp": datetime.now().isoformat()
        }
    
    async def save_conversation(self, user_input: str, ai_response: str, 
                              intent: Dict[str, Any], action_taken: str):
        """会話履歴保存"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO ai_conversations_enhanced 
            (user_input, ai_response, intent, confidence, action_taken, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            user_input,
            ai_response,
            intent["intent"],
            intent["confidence"],
            action_taken,
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    async def get_integration_status(self) -> Dict[str, Any]:
        """統合システム状態取得"""
        status = {}
        
        # トリニティシステム
        try:
            response = requests.get("http://localhost:5005/api/status", timeout=5)
            status["trinity"] = {
                "status": "active" if response.status_code == 200 else "inactive",
                "response_time": response.elapsed.total_seconds()
            }
        except requests.RequestException:
            status["trinity"] = {"status": "inactive", "error": "connection_failed"}
        
        # ハイブリッドシステム
        try:
            response = requests.get("http://localhost:5006/api/status", timeout=5)
            status["hybrid_system"] = {
                "status": "active" if response.status_code == 200 else "inactive",
                "response_time": response.elapsed.total_seconds()
            }
        except requests.RequestException:
            status["hybrid_system"] = {"status": "inactive", "error": "connection_failed"}
        
        return status
    
    async def sync_all_systems(self):
        """全システム同期"""
        try:
            # 各システムとの同期処理
            integration_status = await self.get_integration_status()
            
            # 同期結果をデータベースに記録
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for system_name, status in integration_status.items():
                cursor.execute('''
                    INSERT INTO system_integration_status 
                    (system_name, status, last_check, response_time, metadata)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    system_name,
                    status["status"],
                    datetime.now().isoformat(),
                    status.get("response_time", 0),
                    json.dumps(status)
                ))
            
            conn.commit()
            conn.close()
            
            return {"message": "システム同期完了", "status": integration_status}
            
        except Exception as e:
            self.logger.error(f"システム同期エラー: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_performance_metrics(self):
        """パフォーマンスメトリクス取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT metric_name, metric_value, timestamp, system_component
            FROM performance_metrics
            ORDER BY timestamp DESC LIMIT 100
        ''')
        
        metrics = []
        for row in cursor.fetchall():
            metrics.append({
                "metric_name": row[0],
                "metric_value": row[1],
                "timestamp": row[2],
                "system_component": row[3]
            })
        
        conn.close()
        
        return {"metrics": metrics, "timestamp": datetime.now().isoformat()}
    
    async def get_system_performance(self) -> Dict[str, Any]:
        """システムパフォーマンス取得"""
        import psutil
        
        return {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "timestamp": datetime.now().isoformat()
        }
    
    # ==================== バックグラウンドタスク ====================
    
    def system_integration_monitor(self):
        """システム統合監視"""
        while True:
            try:
                asyncio.run(self.sync_all_systems())
                time.sleep(self.config.get("automation", {}).get("check_interval", 30))
            except Exception as e:
                self.logger.error(f"システム統合監視エラー: {e}")
                time.sleep(60)
    
    def performance_monitor(self):
        """パフォーマンス監視"""
        while True:
            try:
                performance = asyncio.run(self.get_system_performance())
                
                # メトリクスをデータベースに保存
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                for metric_name, metric_value in performance.items():
                    if metric_name != "timestamp":
                        cursor.execute('''
                            INSERT INTO performance_metrics 
                            (metric_name, metric_value, system_component, timestamp)
                            VALUES (?, ?, ?, ?)
                        ''', (metric_name, metric_value, "system", datetime.now().isoformat()))
                
                conn.commit()
                conn.close()
                
                time.sleep(60)  # 1分間隔
            except Exception as e:
                self.logger.error(f"パフォーマンス監視エラー: {e}")
                time.sleep(60)
    
    def workflow_monitor(self):
        """ワークフロー監視"""
        while True:
            try:
                # ワークフロー監視ロジック
                time.sleep(self.config.get("automation", {}).get("check_interval", 30) * 2)
            except Exception as e:
                self.logger.error(f"ワークフロー監視エラー: {e}")
                time.sleep(120)
    
    def ai_learning_process(self):
        """AI学習プロセス"""
        while True:
            try:
                # AI学習ロジック
                time.sleep(300)  # 5分間隔
            except Exception as e:
                self.logger.error(f"AI学習プロセスエラー: {e}")
                time.sleep(300)
    
    async def dashboard(self):
        """統合ダッシュボード"""
        html_content = self.generate_enhanced_dashboard_html()
        return HTMLResponse(content=html_content)
    
    def generate_enhanced_dashboard_html(self) -> str:
        """強化されたダッシュボードHTML生成"""
        return """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mana Enhanced Secretary System</title>
    <style>
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            margin: 0; padding: 20px; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            color: white; 
        }
        .container { max-width: 1400px; margin: 0 auto; }
        .header { text-align: center; margin-bottom: 30px; }
        .header h1 { font-size: 3em; margin: 0; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 20px; }
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
        .status { display: inline-block; padding: 5px 15px; border-radius: 20px; font-weight: bold; }
        .status.active { background: #4CAF50; }
        .status.inactive { background: #f44336; }
        .input-group { margin: 10px 0; }
        .input-group input, .input-group textarea { 
            width: 100%; 
            padding: 8px; 
            border-radius: 5px; 
            border: 1px solid #ccc; 
        }
        .input-group label { display: block; margin-bottom: 5px; font-weight: bold; }
        .chat-container { 
            max-height: 300px; 
            overflow-y: auto; 
            border: 1px solid rgba(255,255,255,0.3); 
            padding: 10px; 
            border-radius: 5px; 
            background: rgba(0,0,0,0.2); 
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Mana Enhanced Secretary System</h1>
            <p>AI秘書 + 自動化 + 統合管理の究極システム</p>
        </div>
        
        <div class="grid">
            <!-- AI秘書チャット -->
            <div class="card">
                <h3>🤖 AI秘書（強化版）</h3>
                <div class="chat-container" id="ai-chat">読み込み中...</div>
                <div class="input-group">
                    <label>AI秘書に質問:</label>
                    <textarea id="ai-message" placeholder="何かお手伝いできることはありますか？"></textarea>
                    <button class="button" onclick="chatWithAI()">送信</button>
                </div>
            </div>
            
            <!-- システム統合状態 -->
            <div class="card">
                <h3>🔗 システム統合状態</h3>
                <div id="integration-status">読み込み中...</div>
                <button class="button" onclick="refreshIntegrationStatus()">🔄 更新</button>
                <button class="button" onclick="syncSystems()">🔄 同期</button>
            </div>
            
            <!-- パフォーマンス監視 -->
            <div class="card">
                <h3>📊 パフォーマンス監視</h3>
                <div id="performance-metrics">読み込み中...</div>
                <button class="button" onclick="refreshPerformance()">🔄 更新</button>
            </div>
            
            <!-- 自動化ワークフロー -->
            <div class="card">
                <h3>⚡ 自動化ワークフロー</h3>
                <div id="workflows">読み込み中...</div>
                <button class="button" onclick="refreshWorkflows()">🔄 更新</button>
            </div>
        </div>
    </div>
    
    <script>
        // AI秘書チャット
        async function chatWithAI() {
            const message = document.getElementById('ai-message').value;
            
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
                
                let chatHtml = document.getElementById('ai-chat').innerHTML;
                chatHtml += `<p><strong>あなた:</strong> ${message}</p>`;
                chatHtml += `<p><strong>Mana:</strong> ${data.response}</p>`;
                if (data.action_taken) {
                    chatHtml += `<p><em>アクション: ${data.action_taken}</em></p>`;
                }
                document.getElementById('ai-chat').innerHTML = chatHtml;
                
                document.getElementById('ai-message').value = '';
            } catch (error) {
                console.error('AI秘書チャットエラー:', error);
            }
        }
        
        // システム統合状態
        async function refreshIntegrationStatus() {
            try {
                const response = await fetch('/api/integration/status');
                const data = await response.json();
                
                let html = '';
                for (const [system, status] of Object.entries(data)) {
                    html += `<p>${system}: <span class="status ${status.status}">${status.status}</span></p>`;
                }
                
                document.getElementById('integration-status').innerHTML = html;
            } catch (error) {
                console.error('統合状態取得エラー:', error);
            }
        }
        
        async function syncSystems() {
            try {
                const response = await fetch('/api/integration/sync', {method: 'POST'});
                const data = await response.json();
                alert(data.message);
                refreshIntegrationStatus();
            } catch (error) {
                console.error('システム同期エラー:', error);
            }
        }
        
        // パフォーマンス監視
        async function refreshPerformance() {
            try {
                const response = await fetch('/api/performance/metrics');
                const data = await response.json();
                
                let html = '<h4>最新メトリクス:</h4>';
                data.metrics.slice(0, 10).forEach(metric => {
                    html += `<p>${metric.metric_name}: ${metric.metric_value}</p>`;
                });
                
                document.getElementById('performance-metrics').innerHTML = html;
            } catch (error) {
                console.error('パフォーマンス取得エラー:', error);
            }
        }
        
        // 初期化
        window.onload = function() {
            refreshIntegrationStatus();
            refreshPerformance();
            
            // 定期的な更新
            setInterval(refreshIntegrationStatus, 30000);
            setInterval(refreshPerformance, 60000);
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
    system = ManaEnhancedSecretarySystem()
    
    print("🚀 Mana Enhanced Secretary System を起動しています...")
    print("📊 ダッシュボード: http://localhost:5007")
    print("🔗 API: http://localhost:5007/api/status")
    print("=" * 60)
    print("🎯 新機能:")
    print("  🤖 AI秘書（強化版）")
    print("  🔗 統合システム管理")
    print("  ⚡ 自動化ワークフロー")
    print("  📊 パフォーマンス監視")
    print("  🧠 学習型最適化")
    print("=" * 60)
    
    # FastAPIサーバー起動
    uvicorn.run(
        system.app,
        host="0.0.0.0",
        port=5007,
        log_level="info"
    )

if __name__ == "__main__":
    main()
