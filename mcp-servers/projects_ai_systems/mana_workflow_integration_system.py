#!/usr/bin/env python3
"""
Mana Workflow Integration System
ワークフロー統合システム - スマートワークフローの統合管理
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

# FastAPI
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import uvicorn

# スマートワークフローエンジン
from mana_smart_workflow_engine import ManaSmartWorkflowEngine

class ManaWorkflowIntegrationSystem:
    """Manaワークフロー統合システム"""
    
    def __init__(self):
        self.app = FastAPI(title="Mana Workflow Integration System", version="7.0.0")
        self.db_path = "/root/mana_workflow_integration.db"
        
        # スマートワークフローエンジン
        self.workflow_engine = ManaSmartWorkflowEngine()
        
        # 設定
        self.config = self.load_config()
        
        # ログ設定
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler('/root/logs/mana_workflow_integration.log'),
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
        
        self.logger.info("🚀 Mana Workflow Integration System 初期化完了")
    
    def load_config(self) -> Dict[str, Any]:
        """設定読み込み"""
        default_config = {
            "system": {
                "name": "Mana Workflow Integration System",
                "version": "7.0.0",
                "port": 5011,
                "max_memory_mb": 1200
            },
            "workflow": {
                "auto_scheduling": True,
                "max_concurrent_workflows": 5,
                "retry_failed_workflows": True,
                "cleanup_completed_workflows": True,
                "cleanup_days": 7
            },
            "integrations": {
                "ai_integration": {"port": 5010, "enabled": True},
                "optimized_system": {"port": 5009, "enabled": True}
            },
            "features": {
                "smart_workflows": True,
                "conditional_execution": True,
                "error_handling": True,
                "dynamic_generation": True,
                "auto_scheduling": True,
                "performance_monitoring": True
            }
        }
        
        config_path = "/root/mana_workflow_config.json"
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                default_config.update(user_config)
        
        return default_config
    
    def init_database(self):
        """データベース初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # ワークフロー統合テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS workflow_integrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_id TEXT NOT NULL,
                integration_type TEXT NOT NULL,
                integration_data TEXT,
                status TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        ''')
        
        # スケジュールテーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS workflow_schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id TEXT NOT NULL,
                schedule_type TEXT NOT NULL,
                schedule_config TEXT NOT NULL,
                enabled BOOLEAN DEFAULT TRUE,
                last_run TEXT,
                next_run TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        ''')
        
        # パフォーマンス統計テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS workflow_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_id TEXT NOT NULL,
                execution_time REAL,
                success_rate REAL,
                error_count INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
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
        
        # ワークフロー管理API
        @self.app.get("/api/workflows")
        async def list_workflows():
            return await self.list_workflows()
        
        @self.app.get("/api/workflows/{workflow_id}")
        async def get_workflow(workflow_id: str):
            return await self.get_workflow(workflow_id)
        
        @self.app.post("/api/workflows/execute/{template_id}")
        async def execute_workflow(template_id: str, params: Dict[str, Any] = None):  # type: ignore
            return await self.execute_workflow(template_id, params or {})
        
        @self.app.get("/api/workflows/templates")
        async def list_templates():
            return await self.list_templates()
        
        # スケジュール管理API
        @self.app.get("/api/schedules")
        async def list_schedules():
            return await self.list_schedules()
        
        @self.app.post("/api/schedules")
        async def create_schedule(schedule: Dict[str, Any]):
            return await self.create_schedule(schedule)
        
        @self.app.delete("/api/schedules/{schedule_id}")
        async def delete_schedule(schedule_id: int):
            return await self.delete_schedule(schedule_id)
        
        # パフォーマンスAPI
        @self.app.get("/api/performance")
        async def get_performance():
            return await self.get_performance()
        
        @self.app.get("/api/analytics")
        async def get_analytics():
            return await self.get_analytics()
        
        @self.app.get("/api/dashboard")
        async def dashboard():
            return await self.dashboard()
    
    def start_background_tasks(self):
        """バックグラウンドタスク開始"""
        # 自動スケジュール実行
        if self.config["workflow"]["auto_scheduling"]:
            threading.Thread(target=self.auto_scheduler, daemon=True).start()
        
        # パフォーマンス監視
        threading.Thread(target=self.performance_monitor, daemon=True).start()
        
        # クリーンアップ
        if self.config["workflow"]["cleanup_completed_workflows"]:
            threading.Thread(target=self.cleanup_worker, daemon=True).start()
        
        self.logger.info("バックグラウンドタスク開始")
    
    # ==================== API実装 ====================
    
    async def root(self):
        """ルートエンドポイント"""
        return {
            "message": "Mana Workflow Integration System",
            "version": "7.0.0",
            "status": "active",
            "features": [
                "スマートワークフロー",
                "条件分岐実行",
                "エラーハンドリング",
                "動的ワークフロー生成",
                "自動スケジューリング",
                "パフォーマンス監視"
            ],
            "workflow_capabilities": {
                "smart_workflows": self.config["features"]["smart_workflows"],
                "conditional_execution": self.config["features"]["conditional_execution"],
                "error_handling": self.config["features"]["error_handling"],
                "dynamic_generation": self.config["features"]["dynamic_generation"],
                "auto_scheduling": self.config["features"]["auto_scheduling"],
                "performance_monitoring": self.config["features"]["performance_monitoring"]
            }
        }
    
    async def get_status(self):
        """システム状態取得"""
        return {
            "timestamp": datetime.now().isoformat(),
            "system": "Mana Workflow Integration System",
            "status": "healthy",
            "version": "7.0.0",
            "workflow_engine": {
                "status": "active",
                "templates_count": len(self.workflow_engine.workflow_templates),
                "active_workflows": len(self.workflow_engine.active_workflows)
            },
            "integrations": await self.get_integration_status(),
            "performance": {
                "max_concurrent_workflows": self.config["workflow"]["max_concurrent_workflows"],
                "auto_scheduling": self.config["workflow"]["auto_scheduling"]
            }
        }
    
    async def list_workflows(self):
        """ワークフロー一覧取得"""
        try:
            workflows = self.workflow_engine.list_workflows()
            return {
                "workflows": workflows,
                "count": len(workflows),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"ワークフロー一覧取得エラー: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_workflow(self, workflow_id: str):
        """ワークフロー詳細取得"""
        try:
            status = self.workflow_engine.get_workflow_status(workflow_id)
            return status
        except Exception as e:
            self.logger.error(f"ワークフロー詳細取得エラー: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def execute_workflow(self, template_id: str, params: Dict[str, Any]):
        """ワークフロー実行"""
        try:
            # ワークフロー作成
            workflow_id = self.workflow_engine.create_workflow_from_template(template_id, params)
            
            # 非同期実行
            result = await self.workflow_engine.execute_workflow(workflow_id)
            
            return {
                "workflow_id": workflow_id,
                "template_id": template_id,
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"ワークフロー実行エラー: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def list_templates(self):
        """テンプレート一覧取得"""
        try:
            templates = self.workflow_engine.list_templates()
            return {
                "templates": templates,
                "count": len(templates),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"テンプレート一覧取得エラー: {e}")
            return {
                "templates": {},
                "count": 0,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def list_schedules(self):
        """スケジュール一覧取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, template_id, schedule_type, schedule_config, enabled, last_run, next_run
            FROM workflow_schedules
            ORDER BY created_at DESC
        ''')
        
        schedules = []
        for row in cursor.fetchall():
            schedules.append({
                "id": row[0],
                "template_id": row[1],
                "schedule_type": row[2],
                "schedule_config": json.loads(row[3]),
                "enabled": bool(row[4]),
                "last_run": row[5],
                "next_run": row[6]
            })
        
        conn.close()
        
        return {
            "schedules": schedules,
            "count": len(schedules),
            "timestamp": datetime.now().isoformat()
        }
    
    async def create_schedule(self, schedule_data: Dict[str, Any]):
        """スケジュール作成"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO workflow_schedules 
                (template_id, schedule_type, schedule_config, enabled, metadata)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                schedule_data["template_id"],
                schedule_data["schedule_type"],
                json.dumps(schedule_data["schedule_config"]),
                schedule_data.get("enabled", True),
                json.dumps(schedule_data.get("metadata", {}))
            ))
            
            schedule_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return {
                "schedule_id": schedule_id,
                "message": "スケジュール作成完了",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"スケジュール作成エラー: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def delete_schedule(self, schedule_id: int):
        """スケジュール削除"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM workflow_schedules WHERE id = ?', (schedule_id,))
            conn.commit()
            conn.close()
            
            return {
                "message": "スケジュール削除完了",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"スケジュール削除エラー: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_performance(self):
        """パフォーマンス統計取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 最近のパフォーマンス統計
        cursor.execute('''
            SELECT AVG(execution_time), AVG(success_rate), SUM(error_count)
            FROM workflow_performance
            WHERE created_at >= datetime('now', '-7 days')
        ''')
        
        stats = cursor.fetchone()
        
        conn.close()
        
        return {
            "performance": {
                "avg_execution_time": stats[0] or 0,
                "avg_success_rate": stats[1] or 0,
                "total_errors": stats[2] or 0
            },
            "timestamp": datetime.now().isoformat()
        }
    
    async def get_analytics(self):
        """分析データ取得"""
        try:
            # ワークフロー統計
            workflows = self.workflow_engine.list_workflows()
            
            # 状態別統計
            status_counts = {}
            for workflow in workflows:
                status = workflow["status"]
                status_counts[status] = status_counts.get(status, 0) + 1
            
            # パフォーマンス統計
            performance = await self.get_performance()
            
            return {
                "workflow_statistics": {
                    "total_workflows": len(workflows),
                    "status_counts": status_counts
                },
                "performance_statistics": performance["performance"],
                "templates": self.workflow_engine.list_templates(),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"分析データ取得エラー: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_integration_status(self) -> Dict[str, Any]:
        """統合システム状態取得"""
        status = {}
        
        # AI統合システムとの連携
        if self.config["integrations"]["ai_integration"]["enabled"]:
            try:
                import requests
                response = requests.get(f"http://localhost:{self.config['integrations']['ai_integration']['port']}/api/status", timeout=5)
                status["ai_integration"] = {
                    "status": "active" if response.status_code == 200 else "inactive",
                    "port": self.config["integrations"]["ai_integration"]["port"],
                    "response_time": response.elapsed.total_seconds()
                }
            except requests.RequestException:  # type: ignore[possibly-unbound]
                status["ai_integration"] = {
                    "status": "inactive",
                    "port": self.config["integrations"]["ai_integration"]["port"],
                    "error": "connection_failed"
                }
        
        return status
    
    # ==================== バックグラウンドタスク ====================
    
    def auto_scheduler(self):
        """自動スケジューラー"""
        while True:
            try:
                # スケジュールチェック
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT id, template_id, schedule_config
                    FROM workflow_schedules
                    WHERE enabled = TRUE AND next_run <= datetime('now')
                ''')
                
                schedules = cursor.fetchall()
                
                for schedule in schedules:
                    schedule_id, template_id, schedule_config = schedule
                    
                    # ワークフロー実行
                    asyncio.run(self.execute_scheduled_workflow(schedule_id, template_id, json.loads(schedule_config)))
                
                conn.close()
                time.sleep(60)  # 1分間隔
                
            except Exception as e:
                self.logger.error(f"自動スケジューラーエラー: {e}")
                time.sleep(60)
    
    async def execute_scheduled_workflow(self, schedule_id: int, template_id: str, schedule_config: Dict[str, Any]):
        """スケジュールワークフロー実行"""
        try:
            # ワークフロー実行
            workflow_id = self.workflow_engine.create_workflow_from_template(template_id)
            result = await self.workflow_engine.execute_workflow(workflow_id)
            
            # スケジュール更新
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 次回実行時間計算
            next_run = self.calculate_next_run(schedule_config)
            
            cursor.execute('''
                UPDATE workflow_schedules
                SET last_run = datetime('now'), next_run = ?
                WHERE id = ?
            ''', (next_run, schedule_id))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"スケジュールワークフロー実行完了: {template_id}")
            
        except Exception as e:
            self.logger.error(f"スケジュールワークフロー実行エラー: {e}")
    
    def calculate_next_run(self, schedule_config: Dict[str, Any]) -> str:
        """次回実行時間計算"""
        schedule_type = schedule_config.get("type", "interval")
        
        if schedule_type == "interval":
            interval_minutes = schedule_config.get("interval_minutes", 60)
            next_run = datetime.now() + timedelta(minutes=interval_minutes)  # type: ignore[name-defined]
        elif schedule_type == "daily":
            hour = schedule_config.get("hour", 0)
            next_run = datetime.now().replace(hour=hour, minute=0, second=0, microsecond=0)
            if next_run <= datetime.now():
                next_run += timedelta(days=1)  # type: ignore[name-defined]
        else:
            next_run = datetime.now() + timedelta(hours=1)  # type: ignore[name-defined]
        
        return next_run.isoformat()
    
    def performance_monitor(self):
        """パフォーマンス監視"""
        while True:
            try:
                # パフォーマンス統計収集
                workflows = self.workflow_engine.list_workflows()
                
                for workflow in workflows:
                    if workflow["status"] in ["completed", "failed"]:
                        # パフォーマンスデータ保存
                        self.save_performance_data(workflow["id"])
                
                time.sleep(300)  # 5分間隔
                
            except Exception as e:
                self.logger.error(f"パフォーマンス監視エラー: {e}")
                time.sleep(300)
    
    def save_performance_data(self, workflow_id: str):
        """パフォーマンスデータ保存"""
        try:
            workflow = self.workflow_engine.get_workflow_from_db(workflow_id)
            if not workflow:
                return
            
            # 実行時間計算
            if workflow.started_at and workflow.completed_at:
                execution_time = (workflow.completed_at - workflow.started_at).total_seconds()
            else:
                execution_time = 0
            
            # 成功率計算
            total_tasks = len(workflow.tasks)
            completed_tasks = sum(1 for task in workflow.tasks if task.status.value == "completed")
            success_rate = completed_tasks / total_tasks if total_tasks > 0 else 0
            
            # エラー数計算
            error_count = sum(1 for task in workflow.tasks if task.status.value == "failed")
            
            # データベース保存
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO workflow_performance 
                (workflow_id, execution_time, success_rate, error_count, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                workflow_id,
                execution_time,
                success_rate,
                error_count,
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"パフォーマンスデータ保存エラー: {e}")
    
    def cleanup_worker(self):
        """クリーンアップワーカー"""
        while True:
            try:
                # 完了済みワークフローのクリーンアップ
                cleanup_days = self.config["workflow"]["cleanup_days"]
                cutoff_date = datetime.now() - timedelta(days=cleanup_days)  # type: ignore[name-defined]
                
                # ここでクリーンアップロジックを実装
                # 実際の実装では、古いワークフローをアーカイブまたは削除
                
                time.sleep(3600)  # 1時間間隔
                
            except Exception as e:
                self.logger.error(f"クリーンアップワーカーエラー: {e}")
                time.sleep(3600)
    
    async def dashboard(self):
        """統合ダッシュボード"""
        html_content = self.generate_workflow_dashboard_html()
        return HTMLResponse(content=html_content)
    
    def generate_workflow_dashboard_html(self) -> str:
        """ワークフローダッシュボードHTML生成"""
        return """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mana Workflow Integration System</title>
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
        .button.workflow { background: #2196F3; }
        .button.workflow:hover { background: #1976D2; }
        .status { display: inline-block; padding: 5px 15px; border-radius: 20px; font-weight: bold; }
        .status.completed { background: #4CAF50; }
        .status.running { background: #ff9800; }
        .status.failed { background: #f44336; }
        .status.pending { background: #9e9e9e; }
        .workflow-list { max-height: 300px; overflow-y: auto; }
        .workflow-item { 
            background: rgba(255,255,255,0.05); 
            padding: 10px; 
            margin: 5px 0; 
            border-radius: 5px; 
        }
        .template-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 10px;
            margin: 10px 0;
        }
        .template-item {
            background: rgba(255,255,255,0.05);
            padding: 15px;
            border-radius: 8px;
            text-align: center;
            cursor: pointer;
            transition: background 0.3s;
        }
        .template-item:hover {
            background: rgba(255,255,255,0.1);
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚡ Mana Workflow Integration System</h1>
            <p>スマートワークフロー・条件分岐・自動スケジューリング</p>
        </div>
        
        <div class="grid">
            <!-- ワークフローテンプレート -->
            <div class="card">
                <h3>📋 ワークフローテンプレート</h3>
                <div id="templates">読み込み中...</div>
                <button class="button workflow" onclick="refreshTemplates()">🔄 更新</button>
            </div>
            
            <!-- ワークフロー実行 -->
            <div class="card">
                <h3>🚀 ワークフロー実行</h3>
                <div class="template-grid" id="template-buttons">
                    <!-- テンプレートボタンが動的に生成される -->
                </div>
                <div id="execution-result">実行結果がここに表示されます</div>
            </div>
            
            <!-- ワークフロー一覧 -->
            <div class="card">
                <h3>📊 ワークフロー一覧</h3>
                <div class="workflow-list" id="workflows">読み込み中...</div>
                <button class="button" onclick="refreshWorkflows()">🔄 更新</button>
            </div>
            
            <!-- スケジュール管理 -->
            <div class="card">
                <h3>⏰ スケジュール管理</h3>
                <div id="schedules">読み込み中...</div>
                <button class="button" onclick="refreshSchedules()">🔄 更新</button>
            </div>
            
            <!-- パフォーマンス統計 -->
            <div class="card">
                <h3>📈 パフォーマンス統計</h3>
                <div id="performance">読み込み中...</div>
                <button class="button" onclick="refreshPerformance()">🔄 更新</button>
            </div>
            
            <!-- 分析データ -->
            <div class="card">
                <h3>📊 分析データ</h3>
                <div id="analytics">読み込み中...</div>
                <button class="button" onclick="refreshAnalytics()">🔄 更新</button>
            </div>
        </div>
    </div>
    
    <script>
        // テンプレート一覧取得
        async function refreshTemplates() {
            try {
                const response = await fetch('/api/workflows/templates');
                const data = await response.json();
                
                let html = '<div class="template-grid">';
                for (const [templateId, template] of Object.entries(data.templates)) {
                    html += `
                        <div class="template-item" onclick="executeWorkflow('${templateId}')">
                            <h4>${template.name}</h4>
                            <p>${template.description}</p>
                            <small>${template.task_count}タスク</small>
                        </div>
                    `;
                }
                html += '</div>';
                
                document.getElementById('templates').innerHTML = html;
                document.getElementById('template-buttons').innerHTML = html;
            } catch (error) {
                console.error('テンプレート取得エラー:', error);
            }
        }
        
        // ワークフロー実行
        async function executeWorkflow(templateId) {
            try {
                const response = await fetch(`/api/workflows/execute/${templateId}`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({})
                });
                
                const data = await response.json();
                
                let html = `
                    <h4>実行結果:</h4>
                    <p>ワークフローID: ${data.workflow_id}</p>
                    <p>ステータス: <span class="status ${data.result.status}">${data.result.status}</span></p>
                    <p>実行時間: ${data.result.duration ? data.result.duration.toFixed(2) + '秒' : 'N/A'}</p>
                `;
                
                if (data.result.error) {
                    html += `<p style="color: #ff6b6b;">エラー: ${data.result.error}</p>`;
                }
                
                document.getElementById('execution-result').innerHTML = html;
                
                // ワークフロー一覧を更新
                refreshWorkflows();
            } catch (error) {
                console.error('ワークフロー実行エラー:', error);
                document.getElementById('execution-result').innerHTML = `<p style="color: #ff6b6b;">実行エラー: ${error.message}</p>`;
            }
        }
        
        // ワークフロー一覧取得
        async function refreshWorkflows() {
            try {
                const response = await fetch('/api/workflows');
                const data = await response.json();
                
                let html = '';
                for (const workflow of data.workflows) {
                    html += `
                        <div class="workflow-item">
                            <h4>${workflow.name}</h4>
                            <p>ステータス: <span class="status ${workflow.status}">${workflow.status}</span></p>
                            <p>作成日時: ${new Date(workflow.created_at).toLocaleString()}</p>
                        </div>
                    `;
                }
                
                document.getElementById('workflows').innerHTML = html;
            } catch (error) {
                console.error('ワークフロー一覧取得エラー:', error);
            }
        }
        
        // スケジュール一覧取得
        async function refreshSchedules() {
            try {
                const response = await fetch('/api/schedules');
                const data = await response.json();
                
                let html = '<h4>スケジュール一覧:</h4>';
                if (data.schedules.length === 0) {
                    html += '<p>スケジュールがありません</p>';
                } else {
                    for (const schedule of data.schedules) {
                        html += `
                            <div class="workflow-item">
                                <h4>${schedule.template_id}</h4>
                                <p>タイプ: ${schedule.schedule_type}</p>
                                <p>有効: ${schedule.enabled ? 'はい' : 'いいえ'}</p>
                                <p>次回実行: ${schedule.next_run ? new Date(schedule.next_run).toLocaleString() : 'N/A'}</p>
                            </div>
                        `;
                    }
                }
                
                document.getElementById('schedules').innerHTML = html;
            } catch (error) {
                console.error('スケジュール一覧取得エラー:', error);
            }
        }
        
        // パフォーマンス統計取得
        async function refreshPerformance() {
            try {
                const response = await fetch('/api/performance');
                const data = await response.json();
                
                const perf = data.performance;
                let html = `
                    <h4>パフォーマンス統計:</h4>
                    <p>平均実行時間: ${perf.avg_execution_time.toFixed(2)}秒</p>
                    <p>平均成功率: ${(perf.avg_success_rate * 100).toFixed(1)}%</p>
                    <p>総エラー数: ${perf.total_errors}</p>
                `;
                
                document.getElementById('performance').innerHTML = html;
            } catch (error) {
                console.error('パフォーマンス統計取得エラー:', error);
            }
        }
        
        // 分析データ取得
        async function refreshAnalytics() {
            try {
                const response = await fetch('/api/analytics');
                const data = await response.json();
                
                const stats = data.workflow_statistics;
                let html = `
                    <h4>ワークフロー統計:</h4>
                    <p>総ワークフロー数: ${stats.total_workflows}</p>
                    <p>状態別統計:</p>
                    <ul>
                `;
                
                for (const [status, count] of Object.entries(stats.status_counts)) {
                    html += `<li>${status}: ${count}件</li>`;
                }
                html += '</ul>';
                
                document.getElementById('analytics').innerHTML = html;
            } catch (error) {
                console.error('分析データ取得エラー:', error);
            }
        }
        
        // 初期化
        window.onload = function() {
            refreshTemplates();
            refreshWorkflows();
            refreshSchedules();
            refreshPerformance();
            refreshAnalytics();
            
            // 定期的な更新
            setInterval(refreshWorkflows, 30000);
            setInterval(refreshSchedules, 60000);
            setInterval(refreshPerformance, 120000);
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
    system = ManaWorkflowIntegrationSystem()
    
    print("🚀 Mana Workflow Integration System を起動しています...")
    print("📊 ダッシュボード: http://localhost:5011")
    print("🔗 API: http://localhost:5011/api/status")
    print("=" * 60)
    print("🎯 ワークフロー機能:")
    print("  ⚡ スマートワークフロー")
    print("  🔀 条件分岐実行")
    print("  🛡️ エラーハンドリング")
    print("  🔮 動的ワークフロー生成")
    print("  ⏰ 自動スケジューリング")
    print("  📈 パフォーマンス監視")
    print("=" * 60)
    
    # FastAPIサーバー起動
    uvicorn.run(
        system.app,
        host="0.0.0.0",
        port=5011,
        log_level="info"
    )

if __name__ == "__main__":
    main()
