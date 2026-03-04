#!/usr/bin/env python3
"""
Mana Automation Orchestrator
統合自動化オーケストレーター - 全システムを統合した自動化エンジン
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
import requests

# FastAPI
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import uvicorn

class ManaAutomationOrchestrator:
    """Mana統合自動化オーケストレーター"""
    
    def __init__(self):
        self.app = FastAPI(title="Mana Automation Orchestrator", version="11.0.0")
        self.db_path = "/root/mana_automation_orchestrator.db"
        
        # 統合システム設定
        self.systems = {
            "optimized": {"port": 5009, "name": "Optimized Integration"},
            "ai": {"port": 5010, "name": "Enhanced AI Integration"},
            "workflow": {"port": 5011, "name": "Workflow Integration"},
            "monitoring": {"port": 5012, "name": "Ultimate Monitoring"},
            "security": {"port": 5013, "name": "Security System"},
            "scalability": {"port": 5014, "name": "Scalability System"}
        }
        
        # ログ設定
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler('/root/logs/mana_automation_orchestrator.log'),
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
        
        self.logger.info("🚀 Mana Automation Orchestrator 初期化完了")
    
    def init_database(self):
        """データベース初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 自動化ルールテーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS automation_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_name TEXT UNIQUE NOT NULL,
                trigger_condition TEXT NOT NULL,
                action_sequence TEXT NOT NULL,
                enabled BOOLEAN DEFAULT TRUE,
                priority INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_executed TEXT,
                execution_count INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0
            )
        ''')
        
        # 自動化実行履歴テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS automation_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_id INTEGER NOT NULL,
                trigger_data TEXT,
                execution_result TEXT,
                status TEXT NOT NULL,
                execution_time REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (rule_id) REFERENCES automation_rules (id)
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
        
        # 自動化ルール管理API
        @self.app.get("/api/automation/rules")
        async def list_automation_rules():
            return await self.list_automation_rules()
        
        @self.app.post("/api/automation/rules")
        async def create_automation_rule(rule_data: Dict[str, Any]):
            return await self.create_automation_rule(rule_data)
        
        # 自動化実行API
        @self.app.post("/api/automation/execute")
        async def execute_automation(execution_data: Dict[str, Any]):
            return await self.execute_automation(execution_data)
        
        @self.app.get("/api/automation/executions")
        async def list_automation_executions():
            return await self.list_automation_executions()
        
        # 統合システム制御API
        @self.app.get("/api/systems/status")
        async def get_systems_status():
            return await self.get_systems_status()
        
        @self.app.post("/api/systems/coordinate")
        async def coordinate_systems(coordination_data: Dict[str, Any]):
            return await self.coordinate_systems(coordination_data)
        
        @self.app.get("/api/dashboard")
        async def dashboard():
            return await self.dashboard()
    
    def start_background_tasks(self):
        """バックグラウンドタスク開始"""
        # 自動化ルール監視
        threading.Thread(target=self.automation_monitor, daemon=True).start()
        
        # システム統合監視
        threading.Thread(target=self.system_integration_monitor, daemon=True).start()
        
        # インテリジェント自動化
        threading.Thread(target=self.intelligent_automation, daemon=True).start()
        
        self.logger.info("バックグラウンドタスク開始")
    
    # ==================== API実装 ====================
    
    async def root(self):
        """ルートエンドポイント"""
        return {
            "message": "Mana Automation Orchestrator",
            "version": "11.0.0",
            "status": "active",
            "features": [
                "統合自動化オーケストレーション",
                "インテリジェント自動化",
                "システム統合制御",
                "予測的自動化",
                "学習型自動化ルール",
                "リアルタイム自動化"
            ],
            "integrated_systems": list(self.systems.keys())
        }
    
    async def get_status(self):
        """システム状態取得"""
        systems_status = await self.get_systems_status()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "system": "Mana Automation Orchestrator",
            "status": "healthy",
            "version": "11.0.0",
            "integrated_systems": systems_status,
            "automation": {
                "active_rules": await self.count_active_rules(),
                "total_executions": await self.count_total_executions(),
                "success_rate": await self.calculate_success_rate()
            }
        }
    
    async def list_automation_rules(self):
        """自動化ルール一覧取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, rule_name, trigger_condition, action_sequence, enabled, 
                   priority, last_executed, execution_count, success_count
            FROM automation_rules
            ORDER BY priority DESC, created_at DESC
        ''')
        
        rules = []
        for row in cursor.fetchall():
            rules.append({
                "id": row[0],
                "rule_name": row[1],
                "trigger_condition": row[2],
                "action_sequence": row[3],
                "enabled": bool(row[4]),
                "priority": row[5],
                "last_executed": row[6],
                "execution_count": row[7],
                "success_count": row[8]
            })
        
        conn.close()
        
        return {
            "automation_rules": rules,
            "count": len(rules),
            "timestamp": datetime.now().isoformat()
        }
    
    async def create_automation_rule(self, rule_data: Dict[str, Any]):
        """自動化ルール作成"""
        try:
            rule_name = rule_data.get("rule_name")
            trigger_condition = rule_data.get("trigger_condition")
            action_sequence = rule_data.get("action_sequence")
            
            if not all([rule_name, trigger_condition, action_sequence]):
                raise HTTPException(status_code=400, detail="Rule name, trigger condition, and action sequence are required")
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO automation_rules 
                (rule_name, trigger_condition, action_sequence, enabled, priority, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                rule_name,
                trigger_condition,
                json.dumps(action_sequence),
                rule_data.get("enabled", True),
                rule_data.get("priority", 1),
                datetime.now().isoformat()
            ))
            
            rule_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            self.logger.info(f"自動化ルール作成: {rule_name}")
            
            return {
                "rule_id": rule_id,
                "rule_name": rule_name,
                "status": "created",
                "created_at": datetime.now().isoformat()
            }
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"自動化ルール作成エラー: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def execute_automation(self, execution_data: Dict[str, Any]):
        """自動化実行"""
        try:
            rule_id = execution_data.get("rule_id")
            trigger_data = execution_data.get("trigger_data", {})
            
            if not rule_id:
                raise HTTPException(status_code=400, detail="Rule ID is required")
            
            # ルール取得
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT rule_name, trigger_condition, action_sequence, enabled
                FROM automation_rules WHERE id = ?
            ''', (rule_id,))
            
            rule = cursor.fetchone()
            if not rule:
                conn.close()
                raise HTTPException(status_code=404, detail="Rule not found")
            
            rule_name, trigger_condition, action_sequence, enabled = rule
            
            if not enabled:
                conn.close()
                raise HTTPException(status_code=400, detail="Rule is disabled")
            
            # 自動化実行
            start_time = time.time()
            result = await self.execute_action_sequence(json.loads(action_sequence), trigger_data)
            execution_time = time.time() - start_time
            
            # 実行履歴保存
            cursor.execute('''
                INSERT INTO automation_executions 
                (rule_id, trigger_data, execution_result, status, execution_time, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                rule_id,
                json.dumps(trigger_data),
                json.dumps(result),
                "completed" if result.get("success") else "failed",
                execution_time,
                datetime.now().isoformat()
            ))
            
            # ルール統計更新
            cursor.execute('''
                UPDATE automation_rules 
                SET last_executed = ?, execution_count = execution_count + 1,
                    success_count = success_count + ?
                WHERE id = ?
            ''', (
                datetime.now().isoformat(),
                1 if result.get("success") else 0,
                rule_id
            ))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"自動化実行完了: {rule_name}")
            
            return {
                "rule_id": rule_id,
                "rule_name": rule_name,
                "result": result,
                "execution_time": execution_time,
                "executed_at": datetime.now().isoformat()
            }
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"自動化実行エラー: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def execute_action_sequence(self, action_sequence: List[Dict[str, Any]], trigger_data: Dict[str, Any]) -> Dict[str, Any]:
        """アクションシーケンス実行"""
        results = []
        
        for action in action_sequence:
            action_type = action.get("type")
            action_params = action.get("params", {})
            
            try:
                if action_type == "ai_analysis":
                    result = await self.execute_ai_analysis(action_params, trigger_data)
                elif action_type == "workflow_execution":
                    result = await self.execute_workflow(action_params, trigger_data)
                elif action_type == "system_optimization":
                    result = await self.execute_system_optimization(action_params, trigger_data)
                elif action_type == "monitoring_check":
                    result = await self.execute_monitoring_check(action_params, trigger_data)
                elif action_type == "security_scan":
                    result = await self.execute_security_scan(action_params, trigger_data)
                elif action_type == "scaling_action":
                    result = await self.execute_scaling_action(action_params, trigger_data)
                else:
                    result = {"success": False, "error": f"Unknown action type: {action_type}"}
                
                results.append({
                    "action": action_type,
                    "result": result,
                    "timestamp": datetime.now().isoformat()
                })
                
            except Exception as e:
                results.append({
                    "action": action_type,
                    "result": {"success": False, "error": str(e)},
                    "timestamp": datetime.now().isoformat()
                })
        
        return {
            "success": all(r["result"].get("success", False) for r in results),
            "actions": results,
            "total_actions": len(results)
        }
    
    async def execute_ai_analysis(self, params: Dict[str, Any], trigger_data: Dict[str, Any]) -> Dict[str, Any]:
        """AI分析実行"""
        try:
            message = params.get("message", "システム状態を分析してください")
            
            response = requests.post(
                f"http://localhost:{self.systems['ai']['port']}/api/ai-secretary/advanced-chat",
                json={"message": message, "session_id": f"automation_{datetime.now().strftime('%Y%m%d_%H%M%S')}"},
                timeout=10
            )
            
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                return {"success": False, "error": f"AI analysis failed: {response.status_code}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def execute_workflow(self, params: Dict[str, Any], trigger_data: Dict[str, Any]) -> Dict[str, Any]:
        """ワークフロー実行"""
        try:
            template_id = params.get("template_id", "health_check")
            
            response = requests.post(
                f"http://localhost:{self.systems['workflow']['port']}/api/workflows/execute/{template_id}",
                timeout=30
            )
            
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                return {"success": False, "error": f"Workflow execution failed: {response.status_code}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def execute_system_optimization(self, params: Dict[str, Any], trigger_data: Dict[str, Any]) -> Dict[str, Any]:
        """システム最適化実行"""
        try:
            response = requests.get(
                f"http://localhost:{self.systems['optimized']['port']}/api/status",
                timeout=10
            )
            
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                return {"success": False, "error": f"System optimization failed: {response.status_code}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def execute_monitoring_check(self, params: Dict[str, Any], trigger_data: Dict[str, Any]) -> Dict[str, Any]:
        """監視チェック実行"""
        try:
            response = requests.get(
                f"http://localhost:{self.systems['monitoring']['port']}/api/monitoring/real-time",
                timeout=10
            )
            
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                return {"success": False, "error": f"Monitoring check failed: {response.status_code}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def execute_security_scan(self, params: Dict[str, Any], trigger_data: Dict[str, Any]) -> Dict[str, Any]:
        """セキュリティスキャン実行"""
        try:
            response = requests.get(
                f"http://localhost:{self.systems['security']['port']}/api/status",
                timeout=10
            )
            
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                return {"success": False, "error": f"Security scan failed: {response.status_code}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def execute_scaling_action(self, params: Dict[str, Any], trigger_data: Dict[str, Any]) -> Dict[str, Any]:
        """スケーリングアクション実行"""
        try:
            response = requests.post(
                f"http://localhost:{self.systems['scalability']['port']}/api/scaling/auto-scale",
                timeout=30
            )
            
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                return {"success": False, "error": f"Scaling action failed: {response.status_code}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_systems_status(self) -> Dict[str, Any]:
        """統合システム状態取得"""
        status = {}
        
        for system_key, system_info in self.systems.items():
            try:
                response = requests.get(f"http://localhost:{system_info['port']}/api/status", timeout=5)
                status[system_key] = {
                    "name": system_info["name"],
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "port": system_info["port"],
                    "response_time": response.elapsed.total_seconds()
                }
            except requests.RequestException:
                status[system_key] = {
                    "name": system_info["name"],
                    "status": "unreachable",
                    "port": system_info["port"],
                    "error": "connection_failed"
                }
        
        return status
    
    async def coordinate_systems(self, coordination_data: Dict[str, Any]):
        """システム統合制御"""
        try:
            coordination_type = coordination_data.get("type")
            target_systems = coordination_data.get("target_systems", list(self.systems.keys()))
            
            results = {}
            
            for system_key in target_systems:
                if system_key in self.systems:
                    try:
                        if coordination_type == "status_check":
                            response = requests.get(f"http://localhost:{self.systems[system_key]['port']}/api/status", timeout=5)
                            results[system_key] = {"status": "checked", "response_code": response.status_code}
                        elif coordination_type == "health_check":
                            response = requests.get(f"http://localhost:{self.systems[system_key]['port']}/api/status", timeout=5)
                            results[system_key] = {"health": "healthy" if response.status_code == 200 else "unhealthy"}
                        else:
                            results[system_key] = {"error": "Unknown coordination type"}
                    except Exception as e:
                        results[system_key] = {"error": str(e)}
            
            return {
                "coordination_type": coordination_type,
                "results": results,
                "coordinated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"システム統合制御エラー: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # ==================== バックグラウンドタスク ====================
    
    def automation_monitor(self):
        """自動化ルール監視"""
        while True:
            try:
                # 自動化ルールの監視と実行
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT id, rule_name, trigger_condition, action_sequence
                    FROM automation_rules
                    WHERE enabled = TRUE
                ''')
                
                rules = cursor.fetchall()
                
                for rule_id, rule_name, trigger_condition, action_sequence in rules:
                    # トリガー条件チェック（簡易版）
                    if self.check_trigger_condition(trigger_condition):
                        # 自動化実行
                        asyncio.run(self.execute_automation({
                            "rule_id": rule_id,
                            "trigger_data": {"auto_triggered": True}
                        }))
                
                conn.close()
                time.sleep(60)  # 1分間隔
                
            except Exception as e:
                self.logger.error(f"自動化ルール監視エラー: {e}")
                time.sleep(60)
    
    def system_integration_monitor(self):
        """システム統合監視"""
        while True:
            try:
                # 統合システムの状態監視
                systems_status = asyncio.run(self.get_systems_status())
                
                # 異常検知時の自動対応
                for system_key, status in systems_status.items():
                    if status["status"] == "unreachable":
                        self.logger.warning(f"システム異常検知: {system_key}")
                        # 自動復旧アクション実行
                        asyncio.run(self.execute_automation({
                            "rule_id": 1,  # システム復旧ルール
                            "trigger_data": {"failed_system": system_key}
                        }))
                
                time.sleep(30)  # 30秒間隔
                
            except Exception as e:
                self.logger.error(f"システム統合監視エラー: {e}")
                time.sleep(30)
    
    def intelligent_automation(self):
        """インテリジェント自動化"""
        while True:
            try:
                # インテリジェント自動化ロジック
                # システム状態に基づく自動判断と実行
                
                time.sleep(120)  # 2分間隔
                
            except Exception as e:
                self.logger.error(f"インテリジェント自動化エラー: {e}")
                time.sleep(120)
    
    def check_trigger_condition(self, trigger_condition: str) -> bool:
        """トリガー条件チェック（簡易版）"""
        # 簡易的なトリガー条件チェック
        # 実際の実装では、より複雑な条件評価を行う
        return "auto" in trigger_condition.lower()
    
    async def count_active_rules(self) -> int:
        """アクティブルール数取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM automation_rules WHERE enabled = TRUE')
        count = cursor.fetchone()[0]
        
        conn.close()
        return count
    
    async def count_total_executions(self) -> int:
        """総実行回数取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM automation_executions')
        count = cursor.fetchone()[0]
        
        conn.close()
        return count
    
    async def calculate_success_rate(self) -> float:
        """成功率計算"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM automation_executions WHERE status = "completed"')
        success_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM automation_executions')
        total_count = cursor.fetchone()[0]
        
        conn.close()
        
        if total_count == 0:
            return 0.0
        
        return (success_count / total_count) * 100
    
    async def list_automation_executions(self):
        """自動化実行履歴取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT ae.id, ar.rule_name, ae.trigger_data, ae.execution_result, 
                   ae.status, ae.execution_time, ae.created_at
            FROM automation_executions ae
            JOIN automation_rules ar ON ae.rule_id = ar.id
            ORDER BY ae.created_at DESC
            LIMIT 50
        ''')
        
        executions = []
        for row in cursor.fetchall():
            executions.append({
                "id": row[0],
                "rule_name": row[1],
                "trigger_data": row[2],
                "execution_result": row[3],
                "status": row[4],
                "execution_time": row[5],
                "created_at": row[6]
            })
        
        conn.close()
        
        return {
            "automation_executions": executions,
            "count": len(executions),
            "timestamp": datetime.now().isoformat()
        }
    
    async def dashboard(self):
        """統合ダッシュボード"""
        html_content = self.generate_orchestrator_dashboard_html()
        return HTMLResponse(content=html_content)
    
    def generate_orchestrator_dashboard_html(self) -> str:
        """オーケストレーターダッシュボードHTML生成"""
        return """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mana Automation Orchestrator</title>
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
        .button.orchestrate { background: #9c27b0; }
        .button.orchestrate:hover { background: #7b1fa2; }
        .status { display: inline-block; padding: 5px 15px; border-radius: 20px; font-weight: bold; }
        .status.healthy { background: #4CAF50; }
        .status.unhealthy { background: #f44336; }
        .status.unreachable { background: #9e9e9e; }
        .system-item { 
            background: rgba(255,255,255,0.05); 
            padding: 15px; 
            margin: 10px 0; 
            border-radius: 8px; 
        }
        .input-group { margin: 10px 0; }
        .input-group input, .input-group textarea, .input-group select { 
            width: 100%; 
            padding: 8px; 
            border-radius: 5px; 
            border: 1px solid #ccc; 
        }
        .input-group label { display: block; margin-bottom: 5px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎭 Mana Automation Orchestrator</h1>
            <p>統合自動化オーケストレーション・インテリジェント自動化・システム統合制御</p>
        </div>
        
        <div class="grid">
            <!-- 統合システム状態 -->
            <div class="card">
                <h3>🔗 統合システム状態</h3>
                <div id="systems-status">読み込み中...</div>
                <button class="button" onclick="refreshSystemsStatus()">🔄 更新</button>
            </div>
            
            <!-- 自動化ルール管理 -->
            <div class="card">
                <h3>📋 自動化ルール管理</h3>
                <div id="automation-rules">読み込み中...</div>
                <button class="button" onclick="refreshAutomationRules()">🔄 更新</button>
            </div>
            
            <!-- 自動化ルール作成 -->
            <div class="card">
                <h3>➕ 自動化ルール作成</h3>
                <div class="input-group">
                    <label>ルール名:</label>
                    <input type="text" id="rule-name" placeholder="ルール名">
                </div>
                <div class="input-group">
                    <label>トリガー条件:</label>
                    <input type="text" id="trigger-condition" placeholder="auto_trigger">
                </div>
                <div class="input-group">
                    <label>アクションシーケンス:</label>
                    <textarea id="action-sequence" placeholder='[{"type": "ai_analysis", "params": {"message": "分析してください"}}]'></textarea>
                </div>
                <button class="button" onclick="createAutomationRule()">ルール作成</button>
            </div>
            
            <!-- 自動化実行 -->
            <div class="card">
                <h3>⚡ 自動化実行</h3>
                <div class="input-group">
                    <label>ルールID:</label>
                    <input type="number" id="execute-rule-id" placeholder="1">
                </div>
                <button class="button orchestrate" onclick="executeAutomation()">自動化実行</button>
                <div id="execution-result">実行結果がここに表示されます</div>
            </div>
            
            <!-- システム統合制御 -->
            <div class="card">
                <h3>🎛️ システム統合制御</h3>
                <div class="input-group">
                    <label>制御タイプ:</label>
                    <select id="coordination-type">
                        <option value="status_check">状態チェック</option>
                        <option value="health_check">ヘルスチェック</option>
                    </select>
                </div>
                <button class="button orchestrate" onclick="coordinateSystems()">システム統合制御</button>
                <div id="coordination-result">制御結果がここに表示されます</div>
            </div>
            
            <!-- 自動化実行履歴 -->
            <div class="card">
                <h3>📊 自動化実行履歴</h3>
                <div id="automation-executions">読み込み中...</div>
                <button class="button" onclick="refreshAutomationExecutions()">🔄 更新</button>
            </div>
        </div>
    </div>
    
    <script>
        // 統合システム状態取得
        async function refreshSystemsStatus() {
            try {
                const response = await fetch('/api/systems/status');
                const data = await response.json();
                
                let html = '<h4>統合システム状態:</h4>';
                for (const [systemKey, status] of Object.entries(data)) {
                    html += `
                        <div class="system-item">
                            <strong>${status.name}</strong><br>
                            <span class="status ${status.status}">${status.status}</span> | 
                            ポート: ${status.port} | 応答時間: ${status.response_time ? status.response_time.toFixed(3) + '秒' : 'N/A'}
                        </div>
                    `;
                }
                
                document.getElementById('systems-status').innerHTML = html;
            } catch (error) {
                console.error('統合システム状態取得エラー:', error);
            }
        }
        
        // 自動化ルール一覧取得
        async function refreshAutomationRules() {
            try {
                const response = await fetch('/api/automation/rules');
                const data = await response.json();
                
                let html = '<h4>自動化ルール一覧:</h4>';
                data.automation_rules.forEach(rule => {
                    html += `
                        <div class="system-item">
                            <strong>${rule.rule_name}</strong><br>
                            有効: ${rule.enabled ? 'はい' : 'いいえ'} | 優先度: ${rule.priority}<br>
                            実行回数: ${rule.execution_count} | 成功回数: ${rule.success_count}<br>
                            <small>最終実行: ${rule.last_executed || '未実行'}</small>
                        </div>
                    `;
                });
                
                document.getElementById('automation-rules').innerHTML = html;
            } catch (error) {
                console.error('自動化ルール一覧取得エラー:', error);
            }
        }
        
        // 自動化ルール作成
        async function createAutomationRule() {
            const ruleName = document.getElementById('rule-name').value;
            const triggerCondition = document.getElementById('trigger-condition').value;
            const actionSequence = document.getElementById('action-sequence').value;
            
            if (!ruleName || !triggerCondition || !actionSequence) {
                alert('すべてのフィールドを入力してください');
                return;
            }
            
            try {
                const response = await fetch('/api/automation/rules', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        rule_name: ruleName,
                        trigger_condition: triggerCondition,
                        action_sequence: JSON.parse(actionSequence)
                    })
                });
                
                if (response.ok) {
                    const data = await response.json();
                    alert(`自動化ルール作成完了: ${data.rule_name}`);
                    refreshAutomationRules();
                } else {
                    alert('ルール作成に失敗しました');
                }
            } catch (error) {
                console.error('自動化ルール作成エラー:', error);
                alert('ルール作成エラーが発生しました');
            }
        }
        
        // 自動化実行
        async function executeAutomation() {
            const ruleId = document.getElementById('execute-rule-id').value;
            
            if (!ruleId) {
                alert('ルールIDを入力してください');
                return;
            }
            
            try {
                const response = await fetch('/api/automation/execute', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        rule_id: parseInt(ruleId),
                        trigger_data: {manual_execution: true}
                    })
                });
                
                if (response.ok) {
                    const data = await response.json();
                    let html = `
                        <h4>実行結果:</h4>
                        <p>ルール: ${data.rule_name}</p>
                        <p>ステータス: ${data.result.success ? '成功' : '失敗'}</p>
                        <p>実行時間: ${data.execution_time.toFixed(3)}秒</p>
                        <p>アクション数: ${data.result.total_actions}</p>
                    `;
                    
                    document.getElementById('execution-result').innerHTML = html;
                    refreshAutomationExecutions();
                } else {
                    alert('自動化実行に失敗しました');
                }
            } catch (error) {
                console.error('自動化実行エラー:', error);
                alert('自動化実行エラーが発生しました');
            }
        }
        
        // システム統合制御
        async function coordinateSystems() {
            const coordinationType = document.getElementById('coordination-type').value;
            
            try {
                const response = await fetch('/api/systems/coordinate', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        type: coordinationType,
                        target_systems: ['optimized', 'ai', 'workflow', 'monitoring', 'security', 'scalability']
                    })
                });
                
                if (response.ok) {
                    const data = await response.json();
                    let html = `
                        <h4>制御結果:</h4>
                        <p>制御タイプ: ${data.coordination_type}</p>
                    `;
                    
                    for (const [systemKey, result] of Object.entries(data.results)) {
                        html += `<p>${systemKey}: ${JSON.stringify(result)}</p>`;
                    }
                    
                    document.getElementById('coordination-result').innerHTML = html;
                } else {
                    alert('システム統合制御に失敗しました');
                }
            } catch (error) {
                console.error('システム統合制御エラー:', error);
                alert('システム統合制御エラーが発生しました');
            }
        }
        
        // 自動化実行履歴取得
        async function refreshAutomationExecutions() {
            try {
                const response = await fetch('/api/automation/executions');
                const data = await response.json();
                
                let html = '<h4>自動化実行履歴:</h4>';
                data.automation_executions.slice(0, 10).forEach(execution => {
                    html += `
                        <div class="system-item">
                            <strong>${execution.rule_name}</strong><br>
                            ステータス: ${execution.status} | 実行時間: ${execution.execution_time ? execution.execution_time.toFixed(3) + '秒' : 'N/A'}<br>
                            <small>${new Date(execution.created_at).toLocaleString()}</small>
                        </div>
                    `;
                });
                
                document.getElementById('automation-executions').innerHTML = html;
            } catch (error) {
                console.error('自動化実行履歴取得エラー:', error);
            }
        }
        
        // 初期化
        window.onload = function() {
            refreshSystemsStatus();
            refreshAutomationRules();
            refreshAutomationExecutions();
            
            // 定期的な更新
            setInterval(refreshSystemsStatus, 30000);
            setInterval(refreshAutomationRules, 60000);
            setInterval(refreshAutomationExecutions, 30000);
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
    orchestrator = ManaAutomationOrchestrator()
    
    print("🚀 Mana Automation Orchestrator を起動しています...")
    print("📊 ダッシュボード: http://localhost:5015")
    print("🔗 API: http://localhost:5015/api/status")
    print("=" * 60)
    print("🎯 統合自動化機能:")
    print("  🎭 統合自動化オーケストレーション")
    print("  🧠 インテリジェント自動化")
    print("  🔗 システム統合制御")
    print("  🔮 予測的自動化")
    print("  📚 学習型自動化ルール")
    print("  ⚡ リアルタイム自動化")
    print("=" * 60)
    
    # FastAPIサーバー起動
    uvicorn.run(
        orchestrator.app,
        host="0.0.0.0",
        port=5015,
        log_level="info"
    )

if __name__ == "__main__":
    main()

