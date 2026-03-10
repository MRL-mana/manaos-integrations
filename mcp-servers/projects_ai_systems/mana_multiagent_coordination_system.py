#!/usr/bin/env python3
"""
Mana Multi-Agent Coordination System
マルチエージェント協調システム - 複数エージェントの協調動作
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Any
import threading
import time
import sqlite3
from enum import Enum

# FastAPI
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import uvicorn

class AgentType(Enum):
    MONITORING = "monitoring"
    OPTIMIZATION = "optimization"
    SECURITY = "security"
    SCALING = "scaling"
    WORKFLOW = "workflow"
    AI_SECRETARY = "ai_secretary"

class AgentStatus(Enum):
    IDLE = "idle"
    ACTIVE = "active"
    BUSY = "busy"
    ERROR = "error"
    OFFLINE = "offline"

class ManaMultiAgentCoordinationSystem:
    """Manaマルチエージェント協調システム"""
    
    def __init__(self):
        self.app = FastAPI(title="Mana Multi-Agent Coordination System", version="16.0.0")
        self.db_path = "/root/mana_multiagent_coordination.db"
        
        # エージェント管理
        self.agents = {}
        self.agent_tasks = {}
        self.coordination_rules = {}
        
        # ログ設定
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler('/root/logs/mana_multiagent_coordination.log'),
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
        
        self.logger.info("🤖 Mana Multi-Agent Coordination System 初期化完了")
    
    def init_database(self):
        """データベース初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # エージェントテーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT UNIQUE NOT NULL,
                agent_type TEXT NOT NULL,
                status TEXT NOT NULL,
                capabilities TEXT NOT NULL,
                current_task TEXT,
                last_heartbeat TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 協調タスクテーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS coordination_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT UNIQUE NOT NULL,
                task_type TEXT NOT NULL,
                priority INTEGER DEFAULT 1,
                status TEXT DEFAULT 'pending',
                assigned_agents TEXT NOT NULL,
                task_data TEXT NOT NULL,
                result TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT
            )
        ''')
        
        # エージェント通信テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agent_communications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_agent TEXT NOT NULL,
                to_agent TEXT NOT NULL,
                message_type TEXT NOT NULL,
                message_data TEXT NOT NULL,
                status TEXT DEFAULT 'sent',
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
        
        # エージェント管理API
        @self.app.post("/api/agents/register")
        async def register_agent(agent_data: Dict[str, Any]):
            return await self.register_agent(agent_data)
        
        @self.app.get("/api/agents")
        async def get_agents():
            return await self.get_agents()
        
        @self.app.post("/api/agents/{agent_id}/heartbeat")
        async def agent_heartbeat(agent_id: str, heartbeat_data: Dict[str, Any]):
            return await self.agent_heartbeat(agent_id, heartbeat_data)
        
        # 協調タスクAPI
        @self.app.post("/api/coordination/create-task")
        async def create_coordination_task(task_data: Dict[str, Any]):
            return await self.create_coordination_task(task_data)
        
        @self.app.get("/api/coordination/tasks")
        async def get_coordination_tasks():
            return await self.get_coordination_tasks()
        
        @self.app.post("/api/coordination/execute")
        async def execute_coordination(execution_data: Dict[str, Any]):
            return await self.execute_coordination(execution_data)
        
        # エージェント通信API
        @self.app.post("/api/agents/communicate")
        async def agent_communication(comm_data: Dict[str, Any]):
            return await self.agent_communication(comm_data)
        
        @self.app.get("/api/agents/communications")
        async def get_agent_communications():
            return await self.get_agent_communications()
        
        @self.app.get("/api/dashboard")
        async def dashboard():
            return await self.dashboard()
    
    def start_background_tasks(self):
        """バックグラウンドタスク開始"""
        # エージェント監視
        threading.Thread(target=self.agent_monitoring, daemon=True).start()
        
        # 協調タスク処理
        threading.Thread(target=self.coordination_processor, daemon=True).start()
        
        # エージェント通信処理
        threading.Thread(target=self.communication_processor, daemon=True).start()
        
        self.logger.info("バックグラウンドタスク開始")
    
    # ==================== API実装 ====================
    
    async def root(self):
        """ルートエンドポイント"""
        return {
            "message": "Mana Multi-Agent Coordination System",
            "version": "16.0.0",
            "status": "active",
            "features": [
                "マルチエージェント協調",
                "分散タスク処理",
                "エージェント通信",
                "協調ルール管理",
                "動的負荷分散",
                "インテリジェント協調"
            ],
            "agent_types": [agent_type.value for agent_type in AgentType]
        }
    
    async def get_status(self):
        """システム状態取得"""
        return {
            "timestamp": datetime.now().isoformat(),
            "system": "Mana Multi-Agent Coordination System",
            "status": "healthy",
            "version": "16.0.0",
            "coordination": {
                "total_agents": len(self.agents),
                "active_agents": len([a for a in self.agents.values() if a["status"] == AgentStatus.ACTIVE.value]),
                "total_tasks": await self.count_coordination_tasks(),
                "pending_tasks": await self.count_pending_tasks(),
                "completed_tasks": await self.count_completed_tasks()
            },
            "agents": self.agents
        }
    
    async def register_agent(self, agent_data: Dict[str, Any]):
        """エージェント登録"""
        try:
            agent_id = agent_data.get("agent_id")
            agent_type = agent_data.get("agent_type")
            capabilities = agent_data.get("capabilities", [])
            
            if not all([agent_id, agent_type]):
                raise HTTPException(status_code=400, detail="Agent ID and type are required")
            
            # エージェント登録
            agent_info = {
                "agent_id": agent_id,
                "agent_type": agent_type,
                "status": AgentStatus.IDLE.value,
                "capabilities": capabilities,
                "current_task": None,
                "last_heartbeat": datetime.now().isoformat(),
                "created_at": datetime.now().isoformat()
            }
            
            self.agents[agent_id] = agent_info
            
            # データベースに保存
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO agents 
                (agent_id, agent_type, status, capabilities, current_task, 
                 last_heartbeat, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                agent_id,
                agent_type,
                AgentStatus.IDLE.value,
                json.dumps(capabilities),
                None,
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"エージェント登録: {agent_id} ({agent_type})")
            
            return {
                "agent_id": agent_id,
                "agent_type": agent_type,
                "status": "registered",
                "registered_at": datetime.now().isoformat()
            }
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"エージェント登録エラー: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_agents(self):
        """エージェント一覧取得"""
        return {
            "agents": list(self.agents.values()),
            "count": len(self.agents),
            "timestamp": datetime.now().isoformat()
        }
    
    async def agent_heartbeat(self, agent_id: str, heartbeat_data: Dict[str, Any]):
        """エージェントハートビート"""
        try:
            if agent_id not in self.agents:
                raise HTTPException(status_code=404, detail="Agent not found")
            
            # ハートビート更新
            self.agents[agent_id]["last_heartbeat"] = datetime.now().isoformat()
            self.agents[agent_id]["status"] = heartbeat_data.get("status", AgentStatus.ACTIVE.value)
            self.agents[agent_id]["current_task"] = heartbeat_data.get("current_task")
            
            # データベース更新
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE agents 
                SET status = ?, current_task = ?, last_heartbeat = ?, updated_at = ?
                WHERE agent_id = ?
            ''', (
                self.agents[agent_id]["status"],
                self.agents[agent_id]["current_task"],
                self.agents[agent_id]["last_heartbeat"],
                datetime.now().isoformat(),
                agent_id
            ))
            
            conn.commit()
            conn.close()
            
            return {
                "agent_id": agent_id,
                "status": "heartbeat_received",
                "timestamp": datetime.now().isoformat()
            }
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"ハートビートエラー: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def create_coordination_task(self, task_data: Dict[str, Any]):
        """協調タスク作成"""
        try:
            task_id = task_data.get("task_id")
            task_type = task_data.get("task_type")
            priority = task_data.get("priority", 1)
            task_data_content = task_data.get("task_data", {})
            
            if not all([task_id, task_type]):
                raise HTTPException(status_code=400, detail="Task ID and type are required")
            
            # 適切なエージェントを選択
            assigned_agents = await self.select_agents_for_task(task_type, task_data_content)  # type: ignore
            
            # 協調タスク作成
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO coordination_tasks 
                (task_id, task_type, priority, assigned_agents, task_data, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                task_id,
                task_type,
                priority,
                json.dumps(assigned_agents),
                json.dumps(task_data_content),
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"協調タスク作成: {task_id} ({task_type})")
            
            return {
                "task_id": task_id,
                "task_type": task_type,
                "assigned_agents": assigned_agents,
                "status": "created",
                "created_at": datetime.now().isoformat()
            }
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"協調タスク作成エラー: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def select_agents_for_task(self, task_type: str, task_data: Dict[str, Any]) -> List[str]:
        """タスクに適したエージェント選択"""
        suitable_agents = []
        
        # タスクタイプに基づくエージェント選択
        if task_type == "monitoring":
            suitable_agents = [aid for aid, agent in self.agents.items() 
                             if agent["agent_type"] == AgentType.MONITORING.value and 
                             agent["status"] == AgentStatus.IDLE.value]
        elif task_type == "optimization":
            suitable_agents = [aid for aid, agent in self.agents.items() 
                             if agent["agent_type"] == AgentType.OPTIMIZATION.value and 
                             agent["status"] == AgentStatus.IDLE.value]
        elif task_type == "security":
            suitable_agents = [aid for aid, agent in self.agents.items() 
                             if agent["agent_type"] == AgentType.SECURITY.value and 
                             agent["status"] == AgentStatus.IDLE.value]
        elif task_type == "scaling":
            suitable_agents = [aid for aid, agent in self.agents.items() 
                             if agent["agent_type"] == AgentType.SCALING.value and 
                             agent["status"] == AgentStatus.IDLE.value]
        elif task_type == "workflow":
            suitable_agents = [aid for aid, agent in self.agents.items() 
                             if agent["agent_type"] == AgentType.WORKFLOW.value and 
                             agent["status"] == AgentStatus.IDLE.value]
        elif task_type == "ai_assistance":
            suitable_agents = [aid for aid, agent in self.agents.items() 
                             if agent["agent_type"] == AgentType.AI_SECRETARY.value and 
                             agent["status"] == AgentStatus.IDLE.value]
        
        # 複数エージェントが必要な場合は複数選択
        if len(suitable_agents) > 1:
            return suitable_agents[:2]  # 最大2つのエージェント
        elif len(suitable_agents) == 1:
            return suitable_agents
        else:
            # 適切なエージェントが見つからない場合は、利用可能なエージェントを返す
            available_agents = [aid for aid, agent in self.agents.items() 
                              if agent["status"] == AgentStatus.IDLE.value]
            return available_agents[:1] if available_agents else []
    
    async def get_coordination_tasks(self):
        """協調タスク一覧取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, task_id, task_type, priority, status, assigned_agents,
                   task_data, result, created_at, completed_at
            FROM coordination_tasks
            ORDER BY priority DESC, created_at DESC
            LIMIT 50
        ''')
        
        tasks = []
        for row in cursor.fetchall():
            tasks.append({
                "id": row[0],
                "task_id": row[1],
                "task_type": row[2],
                "priority": row[3],
                "status": row[4],
                "assigned_agents": json.loads(row[5]) if row[5] else [],
                "task_data": json.loads(row[6]) if row[6] else {},
                "result": json.loads(row[7]) if row[7] else None,
                "created_at": row[8],
                "completed_at": row[9]
            })
        
        conn.close()
        
        return {
            "coordination_tasks": tasks,
            "count": len(tasks),
            "timestamp": datetime.now().isoformat()
        }
    
    async def execute_coordination(self, execution_data: Dict[str, Any]):
        """協調実行"""
        try:
            task_id = execution_data.get("task_id")
            
            if not task_id:
                raise HTTPException(status_code=400, detail="Task ID is required")
            
            # タスク取得
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT task_type, assigned_agents, task_data
                FROM coordination_tasks
                WHERE task_id = ?
            ''', (task_id,))
            
            task = cursor.fetchone()
            if not task:
                conn.close()
                raise HTTPException(status_code=404, detail="Task not found")
            
            task_type, assigned_agents, task_data = task
            assigned_agents = json.loads(assigned_agents)
            task_data = json.loads(task_data)
            
            # 協調実行
            results = []
            for agent_id in assigned_agents:
                if agent_id in self.agents:
                    result = await self.execute_agent_task(agent_id, task_type, task_data)
                    results.append({
                        "agent_id": agent_id,
                        "result": result
                    })
            
            # 結果保存
            cursor.execute('''
                UPDATE coordination_tasks 
                SET status = ?, result = ?, completed_at = ?
                WHERE task_id = ?
            ''', (
                "completed",
                json.dumps(results),
                datetime.now().isoformat(),
                task_id
            ))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"協調実行完了: {task_id}")
            
            return {
                "task_id": task_id,
                "task_type": task_type,
                "results": results,
                "completed_at": datetime.now().isoformat()
            }
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"協調実行エラー: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def execute_agent_task(self, agent_id: str, task_type: str, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """エージェントタスク実行"""
        try:
            agent = self.agents.get(agent_id)
            if not agent:
                return {"success": False, "error": "Agent not found"}
            
            # エージェントの状態を更新
            agent["status"] = AgentStatus.BUSY.value
            agent["current_task"] = task_type
            
            # 実際のタスク実行（簡易版）
            # 実際の実装では、各エージェントのAPIを呼び出す
            result = {
                "success": True,
                "agent_id": agent_id,
                "task_type": task_type,
                "message": f"Task {task_type} executed by {agent_id}",
                "executed_at": datetime.now().isoformat()
            }
            
            # エージェントの状態を元に戻す
            agent["status"] = AgentStatus.IDLE.value
            agent["current_task"] = None
            
            return result
            
        except Exception as e:
            # エラー時も状態を元に戻す
            if agent_id in self.agents:
                self.agents[agent_id]["status"] = AgentStatus.ERROR.value
            return {"success": False, "error": str(e)}
    
    async def agent_communication(self, comm_data: Dict[str, Any]):
        """エージェント通信"""
        try:
            from_agent = comm_data.get("from_agent")
            to_agent = comm_data.get("to_agent")
            message_type = comm_data.get("message_type")
            message_data = comm_data.get("message_data", {})
            
            if not all([from_agent, to_agent, message_type]):
                raise HTTPException(status_code=400, detail="From agent, to agent, and message type are required")
            
            # 通信記録
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO agent_communications 
                (from_agent, to_agent, message_type, message_data, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                from_agent,
                to_agent,
                message_type,
                json.dumps(message_data),
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"エージェント通信: {from_agent} -> {to_agent} ({message_type})")
            
            return {
                "from_agent": from_agent,
                "to_agent": to_agent,
                "message_type": message_type,
                "status": "sent",
                "sent_at": datetime.now().isoformat()
            }
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"エージェント通信エラー: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_agent_communications(self):
        """エージェント通信履歴取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, from_agent, to_agent, message_type, message_data, 
                   status, created_at
            FROM agent_communications
            ORDER BY created_at DESC
            LIMIT 50
        ''')
        
        communications = []
        for row in cursor.fetchall():
            communications.append({
                "id": row[0],
                "from_agent": row[1],
                "to_agent": row[2],
                "message_type": row[3],
                "message_data": json.loads(row[4]) if row[4] else {},
                "status": row[5],
                "created_at": row[6]
            })
        
        conn.close()
        
        return {
            "agent_communications": communications,
            "count": len(communications),
            "timestamp": datetime.now().isoformat()
        }
    
    # ==================== バックグラウンドタスク ====================
    
    def agent_monitoring(self):
        """エージェント監視"""
        while True:
            try:
                # エージェントの状態監視
                current_time = datetime.now()
                for agent_id, agent in self.agents.items():
                    last_heartbeat = datetime.fromisoformat(agent["last_heartbeat"])
                    if (current_time - last_heartbeat).seconds > 300:  # 5分
                        agent["status"] = AgentStatus.OFFLINE.value
                        self.logger.warning(f"エージェント {agent_id} がオフラインになりました")
                
                time.sleep(60)  # 1分間隔
                
            except Exception as e:
                self.logger.error(f"エージェント監視エラー: {e}")
                time.sleep(60)
    
    def coordination_processor(self):
        """協調タスク処理"""
        while True:
            try:
                # 協調タスクの処理
                # 実際の実装では、待機中のタスクを処理
                
                time.sleep(30)  # 30秒間隔
                
            except Exception as e:
                self.logger.error(f"協調タスク処理エラー: {e}")
                time.sleep(30)
    
    def communication_processor(self):
        """通信処理"""
        while True:
            try:
                # エージェント間通信の処理
                # 実際の実装では、メッセージの配信や処理を行う
                
                time.sleep(10)  # 10秒間隔
                
            except Exception as e:
                self.logger.error(f"通信処理エラー: {e}")
                time.sleep(10)
    
    # ==================== ヘルパーメソッド ====================
    
    async def count_coordination_tasks(self) -> int:
        """協調タスク数取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM coordination_tasks')
        count = cursor.fetchone()[0]
        
        conn.close()
        return count
    
    async def count_pending_tasks(self) -> int:
        """待機中タスク数取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM coordination_tasks WHERE status = "pending"')
        count = cursor.fetchone()[0]
        
        conn.close()
        return count
    
    async def count_completed_tasks(self) -> int:
        """完了タスク数取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM coordination_tasks WHERE status = "completed"')
        count = cursor.fetchone()[0]
        
        conn.close()
        return count
    
    async def dashboard(self):
        """マルチエージェントダッシュボード"""
        html_content = self.generate_multiagent_dashboard_html()
        return HTMLResponse(content=html_content)
    
    def generate_multiagent_dashboard_html(self) -> str:
        """マルチエージェントダッシュボードHTML生成"""
        return """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mana Multi-Agent Coordination System</title>
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
        .button.coordinate { background: #9c27b0; }
        .button.coordinate:hover { background: #7b1fa2; }
        .input-group { margin: 10px 0; }
        .input-group input, .input-group textarea, .input-group select { 
            width: 100%; 
            padding: 8px; 
            border-radius: 5px; 
            border: 1px solid #ccc; 
        }
        .input-group label { display: block; margin-bottom: 5px; font-weight: bold; }
        .agent-item { 
            background: rgba(255,255,255,0.05); 
            padding: 15px; 
            margin: 10px 0; 
            border-radius: 8px; 
        }
        .status { 
            display: inline-block; 
            padding: 5px 15px; 
            border-radius: 20px; 
            font-weight: bold; 
        }
        .status.idle { background: #4CAF50; }
        .status.active { background: #2196F3; }
        .status.busy { background: #ff9800; }
        .status.error { background: #f44336; }
        .status.offline { background: #9e9e9e; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 Mana Multi-Agent Coordination System</h1>
            <p>マルチエージェント協調・分散タスク処理・エージェント通信・協調ルール管理</p>
        </div>
        
        <div class="grid">
            <!-- エージェント登録 -->
            <div class="card">
                <h3>📝 エージェント登録</h3>
                <div class="input-group">
                    <label>エージェントID:</label>
                    <input type="text" id="agent-id" placeholder="agent_001">
                </div>
                <div class="input-group">
                    <label>エージェントタイプ:</label>
                    <select id="agent-type">
                        <option value="monitoring">監視エージェント</option>
                        <option value="optimization">最適化エージェント</option>
                        <option value="security">セキュリティエージェント</option>
                        <option value="scaling">スケーリングエージェント</option>
                        <option value="workflow">ワークフローエージェント</option>
                        <option value="ai_secretary">AI秘書エージェント</option>
                    </select>
                </div>
                <div class="input-group">
                    <label>機能:</label>
                    <textarea id="capabilities" placeholder='["monitoring", "alerting"]'></textarea>
                </div>
                <button class="button coordinate" onclick="registerAgent()">エージェント登録</button>
                <div id="registration-result">登録結果がここに表示されます</div>
            </div>
            
            <!-- エージェント一覧 -->
            <div class="card">
                <h3>🤖 エージェント一覧</h3>
                <div id="agents-list">読み込み中...</div>
                <button class="button" onclick="refreshAgents()">🔄 更新</button>
            </div>
            
            <!-- 協調タスク作成 -->
            <div class="card">
                <h3>📋 協調タスク作成</h3>
                <div class="input-group">
                    <label>タスクID:</label>
                    <input type="text" id="task-id" placeholder="task_001">
                </div>
                <div class="input-group">
                    <label>タスクタイプ:</label>
                    <select id="task-type">
                        <option value="monitoring">監視タスク</option>
                        <option value="optimization">最適化タスク</option>
                        <option value="security">セキュリティタスク</option>
                        <option value="scaling">スケーリングタスク</option>
                        <option value="workflow">ワークフロータスク</option>
                        <option value="ai_assistance">AI支援タスク</option>
                    </select>
                </div>
                <div class="input-group">
                    <label>優先度:</label>
                    <input type="number" id="task-priority" placeholder="1" min="1" max="10">
                </div>
                <div class="input-group">
                    <label>タスクデータ:</label>
                    <textarea id="task-data" placeholder='{"target": "system", "action": "monitor"}'></textarea>
                </div>
                <button class="button coordinate" onclick="createCoordinationTask()">協調タスク作成</button>
                <div id="task-creation-result">作成結果がここに表示されます</div>
            </div>
            
            <!-- 協調タスク一覧 -->
            <div class="card">
                <h3>📊 協調タスク一覧</h3>
                <div id="coordination-tasks">読み込み中...</div>
                <button class="button" onclick="refreshCoordinationTasks()">🔄 更新</button>
            </div>
            
            <!-- エージェント通信 -->
            <div class="card">
                <h3>💬 エージェント通信</h3>
                <div class="input-group">
                    <label>送信元エージェント:</label>
                    <input type="text" id="from-agent" placeholder="agent_001">
                </div>
                <div class="input-group">
                    <label>送信先エージェント:</label>
                    <input type="text" id="to-agent" placeholder="agent_002">
                </div>
                <div class="input-group">
                    <label>メッセージタイプ:</label>
                    <input type="text" id="message-type" placeholder="coordination_request">
                </div>
                <div class="input-group">
                    <label>メッセージデータ:</label>
                    <textarea id="message-data" placeholder='{"request": "help", "data": "system_metrics"}'></textarea>
                </div>
                <button class="button coordinate" onclick="sendAgentCommunication()">通信送信</button>
                <div id="communication-result">送信結果がここに表示されます</div>
            </div>
            
            <!-- 通信履歴 -->
            <div class="card">
                <h3>📨 通信履歴</h3>
                <div id="communications">読み込み中...</div>
                <button class="button" onclick="refreshCommunications()">🔄 更新</button>
            </div>
        </div>
    </div>
    
    <script>
        // エージェント登録
        async function registerAgent() {
            const agentId = document.getElementById('agent-id').value;
            const agentType = document.getElementById('agent-type').value;
            const capabilities = document.getElementById('capabilities').value;
            
            if (!agentId || !agentType) {
                alert('エージェントIDとタイプを入力してください');
                return;
            }
            
            try {
                const response = await fetch('/api/agents/register', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        agent_id: agentId,
                        agent_type: agentType,
                        capabilities: JSON.parse(capabilities || '[]')
                    })
                });
                
                if (response.ok) {
                    const data = await response.json();
                    let html = `
                        <h4>エージェント登録完了:</h4>
                        <p>エージェントID: ${data.agent_id}</p>
                        <p>タイプ: ${data.agent_type}</p>
                        <p>登録時刻: ${new Date(data.registered_at).toLocaleString()}</p>
                    `;
                    
                    document.getElementById('registration-result').innerHTML = html;
                    refreshAgents();
                } else {
                    alert('エージェント登録に失敗しました');
                }
            } catch (error) {
                console.error('エージェント登録エラー:', error);
                alert('エージェント登録エラーが発生しました');
            }
        }
        
        // エージェント一覧取得
        async function refreshAgents() {
            try {
                const response = await fetch('/api/agents');
                const data = await response.json();
                
                let html = '<h4>登録済みエージェント:</h4>';
                data.agents.forEach(agent => {
                    html += `
                        <div class="agent-item">
                            <span class="status ${agent.status}">${agent.status}</span><br>
                            <strong>${agent.agent_id}</strong> (${agent.agent_type})<br>
                            機能: ${agent.capabilities.join(', ')}<br>
                            現在のタスク: ${agent.current_task || 'なし'}<br>
                            <small>最終ハートビート: ${new Date(agent.last_heartbeat).toLocaleString()}</small>
                        </div>
                    `;
                });
                
                document.getElementById('agents-list').innerHTML = html;
            } catch (error) {
                console.error('エージェント一覧取得エラー:', error);
            }
        }
        
        // 協調タスク作成
        async function createCoordinationTask() {
            const taskId = document.getElementById('task-id').value;
            const taskType = document.getElementById('task-type').value;
            const priority = document.getElementById('task-priority').value;
            const taskData = document.getElementById('task-data').value;
            
            if (!taskId || !taskType) {
                alert('タスクIDとタイプを入力してください');
                return;
            }
            
            try {
                const response = await fetch('/api/coordination/create-task', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        task_id: taskId,
                        task_type: taskType,
                        priority: parseInt(priority) || 1,
                        task_data: JSON.parse(taskData || '{}')
                    })
                });
                
                if (response.ok) {
                    const data = await response.json();
                    let html = `
                        <h4>協調タスク作成完了:</h4>
                        <p>タスクID: ${data.task_id}</p>
                        <p>タイプ: ${data.task_type}</p>
                        <p>割り当てエージェント: ${data.assigned_agents.join(', ')}</p>
                        <p>作成時刻: ${new Date(data.created_at).toLocaleString()}</p>
                    `;
                    
                    document.getElementById('task-creation-result').innerHTML = html;
                    refreshCoordinationTasks();
                } else {
                    alert('協調タスク作成に失敗しました');
                }
            } catch (error) {
                console.error('協調タスク作成エラー:', error);
                alert('協調タスク作成エラーが発生しました');
            }
        }
        
        // 協調タスク一覧取得
        async function refreshCoordinationTasks() {
            try {
                const response = await fetch('/api/coordination/tasks');
                const data = await response.json();
                
                let html = '<h4>協調タスク一覧:</h4>';
                data.coordination_tasks.slice(0, 10).forEach(task => {
                    html += `
                        <div class="agent-item">
                            <strong>${task.task_id}</strong> (${task.task_type})<br>
                            優先度: ${task.priority} | ステータス: ${task.status}<br>
                            割り当てエージェント: ${task.assigned_agents.join(', ')}<br>
                            <small>作成時刻: ${new Date(task.created_at).toLocaleString()}</small>
                        </div>
                    `;
                });
                
                document.getElementById('coordination-tasks').innerHTML = html;
            } catch (error) {
                console.error('協調タスク一覧取得エラー:', error);
            }
        }
        
        // エージェント通信送信
        async function sendAgentCommunication() {
            const fromAgent = document.getElementById('from-agent').value;
            const toAgent = document.getElementById('to-agent').value;
            const messageType = document.getElementById('message-type').value;
            const messageData = document.getElementById('message-data').value;
            
            if (!fromAgent || !toAgent || !messageType) {
                alert('送信元、送信先、メッセージタイプを入力してください');
                return;
            }
            
            try {
                const response = await fetch('/api/agents/communicate', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        from_agent: fromAgent,
                        to_agent: toAgent,
                        message_type: messageType,
                        message_data: JSON.parse(messageData || '{}')
                    })
                });
                
                if (response.ok) {
                    const data = await response.json();
                    let html = `
                        <h4>通信送信完了:</h4>
                        <p>送信元: ${data.from_agent}</p>
                        <p>送信先: ${data.to_agent}</p>
                        <p>メッセージタイプ: ${data.message_type}</p>
                        <p>送信時刻: ${new Date(data.sent_at).toLocaleString()}</p>
                    `;
                    
                    document.getElementById('communication-result').innerHTML = html;
                    refreshCommunications();
                } else {
                    alert('エージェント通信に失敗しました');
                }
            } catch (error) {
                console.error('エージェント通信エラー:', error);
                alert('エージェント通信エラーが発生しました');
            }
        }
        
        // 通信履歴取得
        async function refreshCommunications() {
            try {
                const response = await fetch('/api/agents/communications');
                const data = await response.json();
                
                let html = '<h4>通信履歴:</h4>';
                data.agent_communications.slice(0, 10).forEach(comm => {
                    html += `
                        <div class="agent-item">
                            <strong>${comm.from_agent} → ${comm.to_agent}</strong><br>
                            タイプ: ${comm.message_type}<br>
                            ステータス: ${comm.status}<br>
                            <small>${new Date(comm.created_at).toLocaleString()}</small>
                        </div>
                    `;
                });
                
                document.getElementById('communications').innerHTML = html;
            } catch (error) {
                console.error('通信履歴取得エラー:', error);
            }
        }
        
        // 初期化
        window.onload = function() {
            refreshAgents();
            refreshCoordinationTasks();
            refreshCommunications();
            
            // 定期的な更新
            setInterval(refreshAgents, 30000);
            setInterval(refreshCoordinationTasks, 30000);
            setInterval(refreshCommunications, 30000);
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
    multiagent_system = ManaMultiAgentCoordinationSystem()
    
    print("🤖 Mana Multi-Agent Coordination System を起動しています...")
    print("📊 ダッシュボード: http://localhost:5020")
    print("🔗 API: http://localhost:5020/api/status")
    print("=" * 60)
    print("🎯 マルチエージェント協調機能:")
    print("  🤖 マルチエージェント協調")
    print("  📊 分散タスク処理")
    print("  💬 エージェント通信")
    print("  📋 協調ルール管理")
    print("  ⚡ 動的負荷分散")
    print("  🧠 インテリジェント協調")
    print("=" * 60)
    
    # FastAPIサーバー起動
    uvicorn.run(
        multiagent_system.app,
        host="0.0.0.0",
        port=5020,
        log_level="info"
    )

if __name__ == "__main__":
    main()
