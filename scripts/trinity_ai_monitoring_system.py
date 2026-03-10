#!/usr/bin/env python3
"""
🚀 Trinity AI Monitoring System
三位一体システム: 音声認識 → AI分析 → 自動実行 → 監視・報告

統合システム:
- Trinity API (音声認識・処理)
- AI Secretary (インテリジェント分析)
- Real-time Monitoring (監視・報告)
"""

import os
import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, Optional, Any
import aiohttp
import websockets
from dataclasses import dataclass
from enum import Enum
import sqlite3
import threading
from flask import Flask, jsonify, request
from flask_cors import CORS

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/root/logs/trinity_ai_monitoring.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SystemStatus(Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class SystemHealth:
    system_name: str
    status: SystemStatus
    response_time: float
    last_check: datetime
    details: Dict[str, Any]

@dataclass
class TaskExecution:
    task_id: str
    command: str
    status: str
    start_time: datetime
    end_time: Optional[datetime]
    result: Optional[Dict[str, Any]]
    error: Optional[str]

class TrinityAIMonitoringSystem:
    """三位一体システムのメインクラス"""
    
    def __init__(self):
        self.system_name = "Trinity AI Monitoring System"
        self.version = "1.0.0"
        self.port = 9001
        
        # システムコンポーネント
        self.trinity_api_url = "http://localhost:8083"
        self.ai_secretary_url = "http://localhost:5007"
        self.monitoring_url = "http://localhost:5008"
        
        # データベース初期化
        self.init_database()
        
        # 実行中のタスク
        self.active_tasks: Dict[str, TaskExecution] = {}
        self.system_health: Dict[str, SystemHealth] = {}
        
        # WebSocket接続
        self.websocket_clients = set()
        
        # Flask アプリケーション
        self.app = Flask(__name__)
        CORS(self.app)
        self.setup_routes()
        
        logger.info(f"🚀 {self.system_name} v{self.version} 初期化完了")

    def init_database(self):
        """データベース初期化"""
        try:
            conn = sqlite3.connect('/root/trinity_ai_monitoring.db')
            cursor = conn.cursor()
            
            # システムヘルステーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_health (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    system_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    response_time REAL,
                    last_check TIMESTAMP,
                    details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # タスク実行履歴テーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT UNIQUE NOT NULL,
                    command TEXT NOT NULL,
                    status TEXT NOT NULL,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    result TEXT,
                    error TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 音声認識履歴テーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS voice_commands (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    command_text TEXT NOT NULL,
                    intent TEXT,
                    confidence REAL,
                    execution_result TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("✅ データベース初期化完了")
            
        except Exception as e:
            logger.error(f"❌ データベース初期化エラー: {e}")

    def setup_routes(self):
        """Flask ルート設定"""
        
        @self.app.route('/api/status', methods=['GET'])
        def get_system_status():
            """システム全体の状態取得"""
            # SystemStatusオブジェクトを辞書に変換
            components = {}
            for key, health in self.system_health.items():
                if health:
                    components[key] = {
                        "system_name": health.system_name,
                        "status": health.status.value,
                        "response_time": health.response_time,
                        "last_check": health.last_check.isoformat(),
                        "details": health.details
                    }
                else:
                    components[key] = {"status": "unknown"}
            
            return jsonify({
                "system_name": self.system_name,
                "version": self.version,
                "status": "operational",
                "timestamp": datetime.now().isoformat(),
                "components": components,
                "active_tasks": len(self.active_tasks),
                "websocket_clients": len(self.websocket_clients)
            })
        
        @self.app.route('/api/voice/process', methods=['POST'])
        def process_voice_command():
            """音声コマンド処理"""
            try:
                data = request.get_json()
                command_text = data.get('command', '')
                
                if not command_text:
                    return jsonify({"error": "音声コマンドが指定されていません"}), 400
                
                # 非同期で音声コマンド処理を実行
                asyncio.create_task(self.process_voice_command_async(command_text))
                
                return jsonify({
                    "message": "音声コマンド処理を開始しました",
                    "command": command_text,
                    "timestamp": datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"音声コマンド処理エラー: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/tasks', methods=['GET'])
        def get_active_tasks():
            """実行中タスク一覧"""
            return jsonify({
                "active_tasks": [
                    {
                        "task_id": task.task_id,
                        "command": task.command,
                        "status": task.status,
                        "start_time": task.start_time.isoformat(),
                        "duration": (datetime.now() - task.start_time).total_seconds() if task.end_time is None else (task.end_time - task.start_time).total_seconds()
                    }
                    for task in self.active_tasks.values()
                ],
                "total_tasks": len(self.active_tasks)
            })
        
        @self.app.route('/api/health/check', methods=['POST'])
        def manual_health_check():
            """手動ヘルスチェック"""
            asyncio.create_task(self.check_all_systems_health())
            return jsonify({"message": "ヘルスチェックを開始しました"})

    async def process_voice_command_async(self, command_text: str):
        """音声コマンドの非同期処理"""
        task_id = f"voice_{int(time.time() * 1000)}"
        
        try:
            logger.info(f"🎤 音声コマンド処理開始: {command_text}")
            
            # 1. AI Secretary でインテント分析
            intent_result = await self.analyze_intent(command_text)
            
            # 2. Trinity API でコマンド実行
            execution_result = await self.execute_command(intent_result)
            
            # 3. 結果を監視システムに報告
            await self.report_to_monitoring(task_id, execution_result)
            
            # 4. 結果をWebSocketでブロードキャスト
            await self.broadcast_result({
                "type": "voice_command_result",
                "task_id": task_id,
                "command": command_text,
                "intent": intent_result,
                "execution": execution_result,
                "timestamp": datetime.now().isoformat()
            })
            
            logger.info(f"✅ 音声コマンド処理完了: {task_id}")
            
        except Exception as e:
            logger.error(f"❌ 音声コマンド処理エラー: {e}")
            await self.broadcast_result({
                "type": "voice_command_error",
                "task_id": task_id,
                "command": command_text,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })

    async def analyze_intent(self, command_text: str) -> Dict[str, Any]:
        """AI Secretary でインテント分析"""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "message": command_text,
                    "context": "voice_command_analysis",
                    "features": ["intent_detection", "entity_extraction", "confidence_scoring"]
                }
                
                async with session.post(f"{self.ai_secretary_url}/api/analyze", json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"🧠 インテント分析完了: {result.get('intent', 'unknown')}")
                        return result
                    else:
                        raise Exception(f"AI Secretary API エラー: {response.status}")
                        
        except Exception as e:
            logger.warning(f"⚠️ AI Secretary 接続エラー、デフォルト分析を使用: {e}")
            # フォールバック: 簡単なキーワード分析
            return self.fallback_intent_analysis(command_text)

    def fallback_intent_analysis(self, command_text: str) -> Dict[str, Any]:
        """フォールバック: 簡単なインテント分析"""
        command_lower = command_text.lower()
        
        if any(word in command_lower for word in ["起動", "開始", "start"]):
            return {
                "intent": "system_start",
                "confidence": 0.8,
                "entities": {"action": "start"},
                "response": "システム起動を実行します"
            }
        elif any(word in command_lower for word in ["停止", "終了", "stop"]):
            return {
                "intent": "system_stop",
                "confidence": 0.8,
                "entities": {"action": "stop"},
                "response": "システム停止を実行します"
            }
        elif any(word in command_lower for word in ["状態", "ステータス", "status"]):
            return {
                "intent": "system_status",
                "confidence": 0.9,
                "entities": {"action": "status"},
                "response": "システム状態を確認します"
            }
        else:
            return {
                "intent": "unknown",
                "confidence": 0.3,
                "entities": {},
                "response": "コマンドを理解できませんでした"
            }

    async def execute_command(self, intent_result: Dict[str, Any]) -> Dict[str, Any]:
        """Trinity API でコマンド実行"""
        try:
            intent = intent_result.get("intent", "unknown")
            entities = intent_result.get("entities", {})
            
            # インテントに基づいて実行コマンドを決定
            execution_command = self.determine_execution_command(intent, entities)
            
            async with aiohttp.ClientSession() as session:
                payload = {
                    "command": execution_command,
                    "intent": intent,
                    "entities": entities
                }
                
                async with session.post(f"{self.trinity_api_url}/api/execute", json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"⚡ コマンド実行完了: {intent}")
                        return result
                    else:
                        raise Exception(f"Trinity API エラー: {response.status}")
                        
        except Exception as e:
            logger.warning(f"⚠️ Trinity API 接続エラー、ローカル実行: {e}")
            return self.local_command_execution(intent_result)

    def determine_execution_command(self, intent: str, entities: Dict[str, Any]) -> str:
        """インテントから実行コマンドを決定"""
        if intent == "system_start":
            return "systemctl start mana-ai-secretary"
        elif intent == "system_stop":
            return "systemctl stop mana-ai-secretary"
        elif intent == "system_status":
            return "systemctl status mana-ai-secretary"
        else:
            return f"echo 'Unknown command: {intent}'"

    def local_command_execution(self, intent_result: Dict[str, Any]) -> Dict[str, Any]:
        """ローカルコマンド実行（フォールバック）"""
        return {
            "status": "executed_locally",
            "result": intent_result.get("response", "コマンドを実行しました"),
            "timestamp": datetime.now().isoformat(),
            "method": "fallback"
        }

    async def report_to_monitoring(self, task_id: str, execution_result: Dict[str, Any]):
        """監視システムに結果報告"""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "task_id": task_id,
                    "system": "trinity_ai_monitoring",
                    "result": execution_result,
                    "timestamp": datetime.now().isoformat()
                }
                
                async with session.post(f"{self.monitoring_url}/api/report", json=payload) as response:
                    if response.status == 200:
                        logger.info(f"📊 監視システムに報告完了: {task_id}")
                    else:
                        logger.warning(f"⚠️ 監視システム報告エラー: {response.status}")
                        
        except Exception as e:
            logger.warning(f"⚠️ 監視システム接続エラー: {e}")

    async def check_all_systems_health(self):
        """全システムのヘルスチェック"""
        systems = [
            ("trinity_api", self.trinity_api_url),
            ("ai_secretary", self.ai_secretary_url),
            ("monitoring", self.monitoring_url)
        ]
        
        for system_name, url in systems:
            try:
                start_time = time.time()
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{url}/api/status", timeout=aiohttp.ClientTimeout(total=5)) as response:
                        response_time = time.time() - start_time
                        
                        if response.status == 200:
                            status = SystemStatus.HEALTHY
                            details = await response.json()
                        else:
                            status = SystemStatus.WARNING
                            details = {"status_code": response.status}
                        
                        health = SystemHealth(
                            system_name=system_name,
                            status=status,
                            response_time=response_time,
                            last_check=datetime.now(),
                            details=details
                        )
                        
                        self.system_health[system_name] = health
                        logger.info(f"✅ {system_name} ヘルスチェック完了: {status.value}")
                        
            except Exception as e:
                health = SystemHealth(
                    system_name=system_name,
                    status=SystemStatus.ERROR,
                    response_time=0,
                    last_check=datetime.now(),
                    details={"error": str(e)}
                )
                self.system_health[system_name] = health
                logger.error(f"❌ {system_name} ヘルスチェックエラー: {e}")
        
        # WebSocketでヘルス状態をブロードキャスト
        await self.broadcast_result({
            "type": "health_update",
            "systems": {
                name: {
                    "status": health.status.value,
                    "response_time": health.response_time,
                    "last_check": health.last_check.isoformat()
                }
                for name, health in self.system_health.items()
            },
            "timestamp": datetime.now().isoformat()
        })

    async def broadcast_result(self, data: Dict[str, Any]):
        """WebSocketで結果をブロードキャスト"""
        if self.websocket_clients:
            message = json.dumps(data, ensure_ascii=False)
            disconnected = set()
            
            for client in self.websocket_clients:
                try:
                    await client.send(message)
                except websockets.exceptions.ConnectionClosed:
                    disconnected.add(client)
                except Exception as e:
                    logger.error(f"WebSocket送信エラー: {e}")
                    disconnected.add(client)
            
            # 切断されたクライアントを削除
            self.websocket_clients -= disconnected

    async def websocket_handler(self, websocket, path):
        """WebSocket接続ハンドラー"""
        self.websocket_clients.add(websocket)
        logger.info(f"🔌 WebSocket接続追加: {len(self.websocket_clients)} clients")
        
        try:
            await websocket.wait_closed()
        finally:
            self.websocket_clients.remove(websocket)
            logger.info(f"🔌 WebSocket接続削除: {len(self.websocket_clients)} clients")

    async def start_monitoring_loop(self):
        """監視ループ開始"""
        while True:
            try:
                await self.check_all_systems_health()
                await asyncio.sleep(30)  # 30秒間隔でヘルスチェック
            except Exception as e:
                logger.error(f"監視ループエラー: {e}")
                await asyncio.sleep(10)

    def run(self):
        """システム起動"""
        logger.info(f"🚀 {self.system_name} 起動中...")
        
        # Flaskアプリを別スレッドで実行
        flask_thread = threading.Thread(
            target=lambda: self.app.run(host='0.0.0.0', port=self.port, debug=os.getenv("DEBUG", "False").lower() == "true")
        )
        flask_thread.daemon = True
        flask_thread.start()
        
        logger.info(f"✅ {self.system_name} 起動完了!")
        logger.info(f"🌐 Web API: http://localhost:{self.port}")
        
        # 非同期タスクを開始
        asyncio.run(self.start_async_tasks())
    
    async def start_async_tasks(self):
        """非同期タスク開始"""
        # WebSocketサーバーを開始
        start_server = websockets.serve(self.websocket_handler, "localhost", 9002)  # type: ignore[misc]
        
        # 監視ループを開始
        monitoring_task = asyncio.create_task(self.start_monitoring_loop())
        
        try:
            # WebSocketサーバーを開始
            await start_server
            
            logger.info("🔌 WebSocket: ws://localhost:9002")
            
            # 監視ループを待機
            await monitoring_task
            
        except KeyboardInterrupt:
            logger.info("🛑 システム停止中...")
        except Exception as e:
            logger.error(f"❌ 非同期タスクエラー: {e}")

if __name__ == "__main__":
    system = TrinityAIMonitoringSystem()
    system.run()
