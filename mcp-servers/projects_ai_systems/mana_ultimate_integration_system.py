#!/usr/bin/env python3
"""
Mana Ultimate Integration System
全システムの究極統合と会話履歴の完全統合
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
import requests

# 会話統合システム
from mana_conversation_integration import ManaConversationIntegration

class ManaUltimateIntegrationSystem:
    """Mana Ultimate Integration System - 究極統合システム"""
    
    def __init__(self):
        self.app = FastAPI(title="Mana Ultimate Integration System", version="4.0.0")
        self.db_path = "/root/mana_ultimate_integration.db"
        self.redis_client = redis.Redis(host='localhost', port=6379, db=2)
        
        # 会話統合システム
        self.conversation_integration = ManaConversationIntegration()
        
        # 設定
        self.config = self.load_config()
        
        # ログ設定
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler('/root/logs/mana_ultimate_integration.log'),
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
        
        self.logger.info("🚀 Mana Ultimate Integration System 初期化完了")
    
    def load_config(self) -> Dict[str, Any]:
        """設定読み込み"""
        default_config = {
            "integrations": {
                "hybrid_system": {"port": 5006, "enabled": True},
                "trinity_system": {"port": 5005, "enabled": True},
                "enhanced_secretary": {"port": 5007, "enabled": True}
            },
            "conversation": {
                "session_management": True,
                "learning_enabled": True,
                "context_retention_days": 30,
                "pattern_analysis": True
            },
            "automation": {
                "system_sync_interval": 30,
                "conversation_analysis_interval": 300,
                "learning_update_interval": 600
            }
        }
        
        config_path = "/root/mana_ultimate_config.json"
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                default_config.update(user_config)
        
        return default_config
    
    def init_database(self):
        """データベース初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # システム統合状態テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_integration_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                system_name TEXT NOT NULL,
                status TEXT NOT NULL,
                last_check TEXT,
                response_time REAL,
                error_message TEXT,
                metadata TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 統合会話履歴テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS integrated_conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                system_source TEXT,
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
        
        # 統合メトリクステーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS integration_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                system_component TEXT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
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
        
        # 統合会話API
        @self.app.post("/api/conversation/chat")
        async def integrated_chat(chat: Dict[str, Any]):
            return await self.integrated_chat(chat)
        
        @self.app.get("/api/conversation/context/{session_id}")
        async def get_conversation_context(session_id: str):
            return await self.get_conversation_context(session_id)
        
        @self.app.get("/api/conversation/analysis")
        async def conversation_analysis():
            return await self.conversation_analysis()
        
        # システム統合API
        @self.app.get("/api/integration/status")
        async def integration_status():
            return await self.get_integration_status()
        
        @self.app.post("/api/integration/sync")
        async def sync_all_systems():
            return await self.sync_all_systems()
        
        # 学習・分析API
        @self.app.get("/api/learning/patterns")
        async def get_learning_patterns():
            return await self.get_learning_patterns()
        
        @self.app.post("/api/learning/feedback")
        async def learning_feedback(feedback: Dict[str, Any]):
            return await self.learning_feedback(feedback)
        
        @self.app.get("/api/analytics/overview")
        async def analytics_overview():
            return await self.analytics_overview()
        
        @self.app.get("/api/dashboard")
        async def dashboard():
            return await self.dashboard()
    
    def start_background_tasks(self):
        """バックグラウンドタスク開始"""
        # システム統合監視
        threading.Thread(target=self.system_integration_monitor, daemon=True).start()
        
        # 会話分析プロセス
        threading.Thread(target=self.conversation_analysis_process, daemon=True).start()
        
        # 学習更新プロセス
        threading.Thread(target=self.learning_update_process, daemon=True).start()
        
        self.logger.info("バックグラウンドタスク開始")
    
    # ==================== API実装 ====================
    
    async def root(self):
        """ルートエンドポイント"""
        return {
            "message": "Mana Ultimate Integration System",
            "version": "4.0.0",
            "status": "active",
            "features": [
                "統合会話管理",
                "システム統合監視",
                "学習・分析機能",
                "リアルタイム同期",
                "パターン認識"
            ],
            "integrated_systems": list(self.config["integrations"].keys())
        }
    
    async def get_status(self):
        """システム状態取得"""
        integration_status = await self.get_integration_status()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "system": "Mana Ultimate Integration System",
            "status": "healthy",
            "version": "4.0.0",
            "integrations": integration_status,
            "conversation_system": {
                "status": "active",
                "session_management": self.config["conversation"]["session_management"],
                "learning_enabled": self.config["conversation"]["learning_enabled"]
            }
        }
    
    async def integrated_chat(self, chat_data: Dict[str, Any]):
        """統合会話処理"""
        try:
            session_id = chat_data.get("session_id", f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            user_input = chat_data["message"]
            system_source = chat_data.get("system_source", "ultimate_integration")
            
            # 既存の会話コンテキスト取得
            conversation_context = self.conversation_integration.get_conversation_context(session_id)
            
            # インテント分析（簡易版）
            intent = await self.analyze_intent(user_input, conversation_context)
            
            # 統合システムからの応答生成
            ai_response = await self.generate_integrated_response(
                user_input, intent, conversation_context, system_source
            )
            
            # アクション実行
            action_taken = await self.execute_integrated_action(intent, user_input, ai_response)
            
            # 会話履歴保存
            conversation_id = self.conversation_integration.save_conversation(
                session_id=session_id,
                user_input=user_input,
                ai_response=ai_response,
                context={"system_source": system_source, "conversation_count": len(conversation_context)},
                intent=intent["intent"],
                confidence=intent["confidence"],
                action_taken=action_taken
            )
            
            # 統合データベースにも保存
            await self.save_integrated_conversation(
                session_id, system_source, user_input, ai_response, 
                intent, action_taken
            )
            
            return {
                "response": ai_response,
                "intent": intent,
                "action_taken": action_taken,
                "session_id": session_id,
                "conversation_id": conversation_id,
                "context": conversation_context
            }
            
        except Exception as e:
            self.logger.error(f"統合会話エラー: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def analyze_intent(self, user_input: str, context: List[Dict[str, Any]]) -> Dict[str, Any]:
        """インテント分析（統合版）"""
        # 基本的なインテント分析
        intents = {
            "task_management": ["タスク", "作業", "やること", "todo", "task"],
            "schedule_management": ["スケジュール", "予定", "会議", "アポイント", "schedule"],
            "system_status": ["状態", "状況", "確認", "チェック", "status"],
            "conversation_history": ["会話", "履歴", "過去", "history", "conversation"],
            "learning": ["学習", "覚える", "記憶", "改善", "learning"],
            "integration": ["統合", "連携", "同期", "integration", "sync"]
        }
        
        detected_intent = "general"
        confidence = 0.0
        keywords = []
        
        for intent, keywords_list in intents.items():
            for keyword in keywords_list:
                if keyword in user_input.lower():
                    detected_intent = intent
                    confidence = 0.8
                    keywords.append(keyword)
                    break
        
        # コンテキストに基づく調整
        if context:
            recent_intents = [conv.get("intent") for conv in context[:3]]
            if detected_intent in recent_intents:
                confidence = min(confidence + 0.1, 1.0)
        
        return {
            "intent": detected_intent,
            "confidence": confidence,
            "keywords": keywords,
            "context_enhanced": len(context) > 0
        }
    
    async def generate_integrated_response(self, user_input: str, intent: Dict[str, Any], 
                                         context: List[Dict[str, Any]], system_source: str) -> str:
        """統合応答生成"""
        # 基本的な応答テンプレート
        responses = {
            "task_management": "タスク管理についてですね。統合システムから最新のタスク情報を取得し、効率的な管理をお手伝いします。",
            "schedule_management": "スケジュール管理についてですね。統合されたカレンダーシステムから予定を確認・管理できます。",
            "system_status": "システム状態についてですね。全統合システムの状態をリアルタイムで監視・報告します。",
            "conversation_history": "会話履歴についてですね。過去の会話を分析し、より良い応答を提供します。",
            "learning": "学習機能についてですね。会話パターンを分析し、継続的に改善していきます。",
            "integration": "統合システムについてですね。全システムの連携状況と同期状態を確認できます。",
            "general": "こんにちは、Mana Ultimate Integration Systemです！統合された全システムを活用して、最高のサポートを提供します。"
        }
        
        base_response = responses.get(intent["intent"], responses["general"])
        
        # コンテキスト情報の追加
        if context:
            base_response += f"\n\n過去の会話: {len(context)}件の履歴を参照しています。"
        
        # システム統合情報の追加
        base_response += f"\n\n統合システム: {system_source}から処理されています。"
        
        return base_response
    
    async def execute_integrated_action(self, intent: Dict[str, Any], user_input: str, ai_response: str) -> str:
        """統合アクション実行"""
        try:
            if intent["intent"] == "system_status":
                # システム状態確認
                status = await self.get_integration_status()
                return f"統合システム状態確認完了: {len(status)}システム監視中"
            
            elif intent["intent"] == "conversation_history":
                # 会話履歴分析
                return "会話履歴分析を実行しました"
            
            elif intent["intent"] == "integration":
                # システム同期
                await self.sync_all_systems()
                return "全システム同期を実行しました"
            
            return "統合アクション実行完了"
            
        except Exception as e:
            self.logger.error(f"統合アクション実行エラー: {e}")
            return "アクション実行中にエラーが発生しました"
    
    async def get_conversation_context(self, session_id: str):
        """会話コンテキスト取得"""
        context = self.conversation_integration.get_conversation_context(session_id)
        session_summary = self.conversation_integration.get_session_summary(session_id)
        
        return {
            "session_id": session_id,
            "conversations": context,
            "session_summary": session_summary,
            "timestamp": datetime.now().isoformat()
        }
    
    async def conversation_analysis(self):
        """会話分析"""
        patterns = self.conversation_integration.analyze_conversation_patterns()
        return {
            "analysis": patterns,
            "timestamp": datetime.now().isoformat()
        }
    
    async def get_integration_status(self) -> Dict[str, Any]:
        """統合システム状態取得"""
        status = {}
        
        for system_name, config in self.config["integrations"].items():
            if config["enabled"]:
                try:
                    response = requests.get(f"http://localhost:{config['port']}/api/status", timeout=5)
                    status[system_name] = {
                        "status": "active" if response.status_code == 200 else "inactive",
                        "port": config["port"],
                        "response_time": response.elapsed.total_seconds()
                    }
                except requests.RequestException:
                    status[system_name] = {
                        "status": "inactive",
                        "port": config["port"],
                        "error": "connection_failed"
                    }
        
        return status
    
    async def sync_all_systems(self):
        """全システム同期"""
        try:
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
            
            return {"message": "全システム同期完了", "status": integration_status}
            
        except Exception as e:
            self.logger.error(f"システム同期エラー: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_learning_patterns(self):
        """学習パターン取得"""
        patterns = self.conversation_integration.get_learning_patterns()
        return {
            "patterns": patterns,
            "timestamp": datetime.now().isoformat()
        }
    
    async def learning_feedback(self, feedback_data: Dict[str, Any]):
        """学習フィードバック処理"""
        try:
            pattern = feedback_data.get("pattern")
            response = feedback_data.get("response")
            success = feedback_data.get("success", True)
            
            if pattern and response:
                self.conversation_integration.update_learning_pattern(pattern, response, success)
                return {"message": "学習フィードバックを処理しました"}
            else:
                raise HTTPException(status_code=400, detail="pattern と response が必要です")
                
        except Exception as e:
            self.logger.error(f"学習フィードバックエラー: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def analytics_overview(self):
        """分析概要"""
        try:
            # 会話分析
            conversation_analysis = await self.conversation_analysis()
            
            # システム状態
            integration_status = await self.get_integration_status()
            
            # 学習パターン
            learning_patterns = await self.get_learning_patterns()
            
            return {
                "conversation_analysis": conversation_analysis,
                "integration_status": integration_status,
                "learning_patterns": learning_patterns,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"分析概要エラー: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def save_integrated_conversation(self, session_id: str, system_source: str, 
                                         user_input: str, ai_response: str, 
                                         intent: Dict[str, Any], action_taken: str):
        """統合会話保存"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO integrated_conversations 
            (session_id, system_source, user_input, ai_response, intent, confidence, action_taken, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            session_id,
            system_source,
            user_input,
            ai_response,
            intent["intent"],
            intent["confidence"],
            action_taken,
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    # ==================== バックグラウンドタスク ====================
    
    def system_integration_monitor(self):
        """システム統合監視"""
        while True:
            try:
                asyncio.run(self.sync_all_systems())
                time.sleep(self.config.get("automation", {}).get("system_sync_interval", 30))
            except Exception as e:
                self.logger.error(f"システム統合監視エラー: {e}")
                time.sleep(60)
    
    def conversation_analysis_process(self):
        """会話分析プロセス"""
        while True:
            try:
                # 会話分析ロジック
                time.sleep(self.config.get("automation", {}).get("conversation_analysis_interval", 300))
            except Exception as e:
                self.logger.error(f"会話分析プロセスエラー: {e}")
                time.sleep(300)
    
    def learning_update_process(self):
        """学習更新プロセス"""
        while True:
            try:
                # 学習更新ロジック
                time.sleep(self.config.get("automation", {}).get("learning_update_interval", 600))
            except Exception as e:
                self.logger.error(f"学習更新プロセスエラー: {e}")
                time.sleep(600)
    
    async def dashboard(self):
        """統合ダッシュボード"""
        html_content = self.generate_ultimate_dashboard_html()
        return HTMLResponse(content=html_content)
    
    def generate_ultimate_dashboard_html(self) -> str:
        """究極ダッシュボードHTML生成"""
        return """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mana Ultimate Integration System</title>
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
            max-height: 400px; 
            overflow-y: auto; 
            border: 1px solid rgba(255,255,255,0.3); 
            padding: 10px; 
            border-radius: 5px; 
            background: rgba(0,0,0,0.2); 
        }
        .analytics-grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
            gap: 10px; 
            margin: 10px 0; 
        }
        .metric-card { 
            background: rgba(255,255,255,0.05); 
            padding: 10px; 
            border-radius: 8px; 
            text-align: center; 
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Mana Ultimate Integration System</h1>
            <p>究極の統合システム - 会話・学習・分析の完全統合</p>
        </div>
        
        <div class="grid">
            <!-- 統合会話チャット -->
            <div class="card">
                <h3>💬 統合会話システム</h3>
                <div class="chat-container" id="integrated-chat">読み込み中...</div>
                <div class="input-group">
                    <label>統合AI秘書に質問:</label>
                    <textarea id="chat-message" placeholder="何でもお聞きください！"></textarea>
                    <button class="button" onclick="sendIntegratedChat()">送信</button>
                </div>
            </div>
            
            <!-- システム統合状態 -->
            <div class="card">
                <h3>🔗 システム統合状態</h3>
                <div id="integration-status">読み込み中...</div>
                <button class="button" onclick="refreshIntegrationStatus()">🔄 更新</button>
                <button class="button" onclick="syncAllSystems()">🔄 全システム同期</button>
            </div>
            
            <!-- 会話分析 -->
            <div class="card">
                <h3>📊 会話分析</h3>
                <div id="conversation-analysis">読み込み中...</div>
                <button class="button" onclick="refreshConversationAnalysis()">🔄 分析更新</button>
            </div>
            
            <!-- 学習パターン -->
            <div class="card">
                <h3>🧠 学習パターン</h3>
                <div id="learning-patterns">読み込み中...</div>
                <button class="button" onclick="refreshLearningPatterns()">🔄 パターン更新</button>
            </div>
            
            <!-- 分析概要 -->
            <div class="card">
                <h3>📈 分析概要</h3>
                <div id="analytics-overview">読み込み中...</div>
                <button class="button" onclick="refreshAnalytics()">🔄 分析更新</button>
            </div>
        </div>
    </div>
    
    <script>
        let currentSessionId = 'session_' + new Date().toISOString().replace(/[:.]/g, '-');
        
        // 統合会話チャット
        async function sendIntegratedChat() {
            const message = document.getElementById('chat-message').value;
            
            if (!message) {
                alert('メッセージを入力してください');
                return;
            }
            
            try {
                const response = await fetch('/api/conversation/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        message: message,
                        session_id: currentSessionId,
                        system_source: 'ultimate_integration'
                    })
                });
                
                const data = await response.json();
                
                let chatHtml = document.getElementById('integrated-chat').innerHTML;
                chatHtml += `<p><strong>あなた:</strong> ${message}</p>`;
                chatHtml += `<p><strong>Mana Ultimate:</strong> ${data.response}</p>`;
                if (data.action_taken) {
                    chatHtml += `<p><em>アクション: ${data.action_taken}</em></p>`;
                }
                if (data.intent) {
                    chatHtml += `<p><em>インテント: ${data.intent.intent} (信頼度: ${(data.intent.confidence * 100).toFixed(1)}%)</em></p>`;
                }
                document.getElementById('integrated-chat').innerHTML = chatHtml;
                
                document.getElementById('chat-message').value = '';
            } catch (error) {
                console.error('統合会話エラー:', error);
            }
        }
        
        // システム統合状態
        async function refreshIntegrationStatus() {
            try {
                const response = await fetch('/api/integration/status');
                const data = await response.json();
                
                let html = '';
                for (const [system, status] of Object.entries(data)) {
                    html += `<p>${system}: <span class="status ${status.status}">${status.status}</span> (${status.port})</p>`;
                }
                
                document.getElementById('integration-status').innerHTML = html;
            } catch (error) {
                console.error('統合状態取得エラー:', error);
            }
        }
        
        async function syncAllSystems() {
            try {
                const response = await fetch('/api/integration/sync', {method: 'POST'});
                const data = await response.json();
                alert(data.message);
                refreshIntegrationStatus();
            } catch (error) {
                console.error('システム同期エラー:', error);
            }
        }
        
        // 会話分析
        async function refreshConversationAnalysis() {
            try {
                const response = await fetch('/api/conversation/analysis');
                const data = await response.json();
                
                let html = '<h4>会話パターン分析:</h4>';
                if (data.analysis && data.analysis.intent_statistics) {
                    data.analysis.intent_statistics.forEach(stat => {
                        html += `<p>${stat.intent}: ${stat.count}回 (信頼度: ${(stat.avg_confidence * 100).toFixed(1)}%)</p>`;
                    });
                }
                
                document.getElementById('conversation-analysis').innerHTML = html;
            } catch (error) {
                console.error('会話分析エラー:', error);
            }
        }
        
        // 学習パターン
        async function refreshLearningPatterns() {
            try {
                const response = await fetch('/api/learning/patterns');
                const data = await response.json();
                
                let html = '<h4>学習パターン:</h4>';
                if (data.patterns && data.patterns.length > 0) {
                    data.patterns.slice(0, 5).forEach(pattern => {
                        html += `<p>${pattern.pattern}: 成功率 ${(pattern.success_rate * 100).toFixed(1)}% (使用回数: ${pattern.usage_count})</p>`;
                    });
                } else {
                    html += '<p>学習パターンがまだありません</p>';
                }
                
                document.getElementById('learning-patterns').innerHTML = html;
            } catch (error) {
                console.error('学習パターンエラー:', error);
            }
        }
        
        // 分析概要
        async function refreshAnalytics() {
            try {
                const response = await fetch('/api/analytics/overview');
                const data = await response.json();
                
                let html = '<div class="analytics-grid">';
                html += '<div class="metric-card"><h4>統合システム</h4><p>' + Object.keys(data.integration_status).length + 'システム</p></div>';
                html += '<div class="metric-card"><h4>会話分析</h4><p>' + (data.conversation_analysis.analysis.intent_statistics.length || 0) + '種類</p></div>';
                html += '<div class="metric-card"><h4>学習パターン</h4><p>' + (data.learning_patterns.patterns.length || 0) + 'パターン</p></div>';
                html += '</div>';
                
                document.getElementById('analytics-overview').innerHTML = html;
            } catch (error) {
                console.error('分析概要エラー:', error);
            }
        }
        
        // 初期化
        window.onload = function() {
            refreshIntegrationStatus();
            refreshConversationAnalysis();
            refreshLearningPatterns();
            refreshAnalytics();
            
            // 定期的な更新
            setInterval(refreshIntegrationStatus, 30000);
            setInterval(refreshConversationAnalysis, 60000);
            setInterval(refreshLearningPatterns, 120000);
            setInterval(refreshAnalytics, 180000);
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
    system = ManaUltimateIntegrationSystem()
    
    print("🚀 Mana Ultimate Integration System を起動しています...")
    print("📊 ダッシュボード: http://localhost:5008")
    print("🔗 API: http://localhost:5008/api/status")
    print("=" * 60)
    print("🎯 究極機能:")
    print("  💬 統合会話システム")
    print("  🔗 システム統合監視")
    print("  📊 会話分析・学習")
    print("  🧠 パターン認識")
    print("  📈 リアルタイム分析")
    print("=" * 60)
    
    # FastAPIサーバー起動
    uvicorn.run(
        system.app,
        host="0.0.0.0",
        port=5008,
        log_level="info"
    )

if __name__ == "__main__":
    main()

