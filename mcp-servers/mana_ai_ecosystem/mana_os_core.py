#!/usr/bin/env python3
"""
ManaOS Core - 統合オペレーティングシステム
Trinity自動化システムとMana秘書システムを統合したManaOS
"""

import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import threading
from collections import deque
import httpx
import redis
from sqlalchemy import create_engine, Column, String, DateTime, Text, JSON, Boolean, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import schedule
import subprocess
import psutil

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# データベース設定
DATABASE_URL = os.getenv("POSTGRES_URL", "postgresql://mana:mana_secure_2024@localhost:5432/mana_ai")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# データベースモデル
class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    status = Column(String, default="pending")  # pending, in_progress, completed, cancelled
    priority = Column(Integer, default=1)  # 1-5 (5が最高)
    due_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    user_id = Column(String, nullable=False)
    metadata = Column(JSON)

class Schedule(Base):
    __tablename__ = "schedules"
    
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    is_recurring = Column(Boolean, default=False)
    recurrence_pattern = Column(String)  # daily, weekly, monthly
    user_id = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    metadata = Column(JSON)

class Automation(Base):
    __tablename__ = "automations"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    trigger_type = Column(String, nullable=False)  # schedule, event, manual
    trigger_config = Column(JSON)
    action_type = Column(String, nullable=False)  # script, api_call, notification
    action_config = Column(JSON)
    is_active = Column(Boolean, default=True)
    user_id = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_executed = Column(DateTime)
    metadata = Column(JSON)

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String, default="info")  # info, warning, error, success
    is_read = Column(Boolean, default=False)
    user_id = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    metadata = Column(JSON)

# Pydanticモデル
class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: int = 1
    due_date: Optional[datetime] = None
    user_id: str = "default_user"

class ScheduleCreate(BaseModel):
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    is_recurring: bool = False
    recurrence_pattern: Optional[str] = None
    user_id: str = "default_user"

class AutomationCreate(BaseModel):
    name: str
    description: Optional[str] = None
    trigger_type: str
    trigger_config: Dict[str, Any]
    action_type: str
    action_config: Dict[str, Any]
    user_id: str = "default_user"

class ChatMessage(BaseModel):
    message: str
    user_id: str = "default_user"
    context: Optional[Dict[str, Any]] = None

# ManaOS Core クラス
class ManaOSCore:
    def __init__(self):
        self.db = SessionLocal()
        self.redis_client = redis.Redis(host="redis", port=6379, decode_responses=True)
        self.running_tasks = {}
        self.automations = {}
        self.notifications = deque(maxlen=1000)
        
        # AIエンジンURL
        self.ai_engines = {
            "localai": "http://localai:8080",
            "anythingllm": "http://anythingllm:3001",
            "lmstudio": "http://lmstudio:1234",
            "gpt_oss": "http://gpt_oss:8080"
        }
        
        # 初期化
        self._initialize_database()
        self._load_automations()
        self._start_scheduler()
    
    def _initialize_database(self):
        """データベースを初期化"""
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("ManaOS データベースを初期化しました")
        except Exception as e:
            logger.error(f"データベース初期化エラー: {e}")
    
    def _load_automations(self):
        """自動化スクリプトを読み込み"""
        try:
            automations = self.db.query(Automation).filter(Automation.is_active == True).all()
            for automation in automations:
                self.automations[automation.id] = automation
            logger.info(f"{len(automations)}個の自動化スクリプトを読み込みました")
        except Exception as e:
            logger.error(f"自動化スクリプト読み込みエラー: {e}")
    
    def _start_scheduler(self):
        """スケジューラーを開始"""
        def run_scheduler():
            while True:
                schedule.run_pending()
                time.sleep(1)
        
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        logger.info("ManaOS スケジューラーを開始しました")
    
    async def process_chat_message(self, message: str, user_id: str) -> Dict[str, Any]:
        """チャットメッセージを処理"""
        try:
            # 意図を分析
            intent = await self._analyze_intent(message)
            
            # 意図に基づいて処理
            if intent == "task_management":
                return await self._handle_task_management(message, user_id)
            elif intent == "schedule_management":
                return await self._handle_schedule_management(message, user_id)
            elif intent == "automation":
                return await self._handle_automation(message, user_id)
            elif intent == "notification":
                return await self._handle_notification(message, user_id)
            else:
                return await self._handle_general_chat(message, user_id)
                
        except Exception as e:
            logger.error(f"チャット処理エラー: {e}")
            return {
                "response": "申し訳ございません。エラーが発生しました。",
                "type": "error",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _analyze_intent(self, message: str) -> str:
        """メッセージの意図を分析"""
        message_lower = message.lower()
        
        # タスク管理キーワード
        task_keywords = ["タスク", "task", "やること", "todo", "作業", "仕事"]
        if any(keyword in message_lower for keyword in task_keywords):
            return "task_management"
        
        # スケジュール管理キーワード
        schedule_keywords = ["スケジュール", "schedule", "予定", "会議", "アポイント", "時間"]
        if any(keyword in message_lower for keyword in schedule_keywords):
            return "schedule_management"
        
        # 自動化キーワード
        automation_keywords = ["自動化", "automation", "スクリプト", "実行", "run"]
        if any(keyword in message_lower for keyword in automation_keywords):
            return "automation"
        
        # 通知キーワード
        notification_keywords = ["通知", "notification", "アラート", "alert", "知らせ"]
        if any(keyword in message_lower for keyword in notification_keywords):
            return "notification"
        
        return "general_chat"
    
    async def _handle_task_management(self, message: str, user_id: str) -> Dict[str, Any]:
        """タスク管理を処理"""
        try:
            # タスク作成
            if "作成" in message or "追加" in message or "create" in message.lower():
                # メッセージからタスク情報を抽出
                task_title = self._extract_task_title(message)
                task = Task(
                    id=f"task_{int(time.time())}",
                    title=task_title,
                    description=message,
                    user_id=user_id,
                    status="pending"
                )
                self.db.add(task)
                self.db.commit()
                
                return {
                    "response": f"タスク「{task_title}」を作成しました！",
                    "type": "task_created",
                    "task_id": task.id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            # タスク一覧
            elif "一覧" in message or "list" in message.lower():
                tasks = self.db.query(Task).filter(Task.user_id == user_id).all()
                task_list = []
                for task in tasks:
                    task_list.append({
                        "id": task.id,
                        "title": task.title,
                        "status": task.status,
                        "priority": task.priority,
                        "created_at": task.created_at.isoformat()
                    })
                
                return {
                    "response": "現在のタスク一覧です：\n" + "\n".join([f"- {t['title']} ({t['status']})" for t in task_list]),
                    "type": "task_list",
                    "tasks": task_list,
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            else:
                return {
                    "response": "タスク管理について何かお手伝いできますか？タスクの作成、一覧表示、更新などが可能です。",
                    "type": "task_help",
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"タスク管理エラー: {e}")
            return {
                "response": "タスクの処理中にエラーが発生しました。",
                "type": "error",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _handle_schedule_management(self, message: str, user_id: str) -> Dict[str, Any]:
        """スケジュール管理を処理"""
        try:
            # スケジュール作成
            if "作成" in message or "追加" in message or "create" in message.lower():
                schedule_title = self._extract_schedule_title(message)
                schedule = Schedule(
                    id=f"schedule_{int(time.time())}",
                    title=schedule_title,
                    description=message,
                    start_time=datetime.utcnow() + timedelta(hours=1),  # デフォルトで1時間後
                    user_id=user_id
                )
                self.db.add(schedule)
                self.db.commit()
                
                return {
                    "response": f"スケジュール「{schedule_title}」を作成しました！",
                    "type": "schedule_created",
                    "schedule_id": schedule.id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            # スケジュール一覧
            elif "一覧" in message or "list" in message.lower():
                schedules = self.db.query(Schedule).filter(Schedule.user_id == user_id).all()
                schedule_list = []
                for schedule in schedules:
                    schedule_list.append({
                        "id": schedule.id,
                        "title": schedule.title,
                        "start_time": schedule.start_time.isoformat(),
                        "is_recurring": schedule.is_recurring
                    })
                
                return {
                    "response": "現在のスケジュール一覧です：\n" + "\n".join([f"- {s['title']} ({s['start_time']})" for s in schedule_list]),
                    "type": "schedule_list",
                    "schedules": schedule_list,
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            else:
                return {
                    "response": "スケジュール管理について何かお手伝いできますか？スケジュールの作成、一覧表示、更新などが可能です。",
                    "type": "schedule_help",
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"スケジュール管理エラー: {e}")
            return {
                "response": "スケジュールの処理中にエラーが発生しました。",
                "type": "error",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _handle_automation(self, message: str, user_id: str) -> Dict[str, Any]:
        """自動化を処理"""
        try:
            # 自動化実行
            if "実行" in message or "run" in message.lower():
                automation_id = self._extract_automation_id(message)
                if automation_id in self.automations:
                    result = await self._execute_automation(automation_id)
                    return {
                        "response": f"自動化「{self.automations[automation_id].name}」を実行しました！",
                        "type": "automation_executed",
                        "result": result,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                else:
                    return {
                        "response": "指定された自動化が見つかりません。",
                        "type": "automation_not_found",
                        "timestamp": datetime.utcnow().isoformat()
                    }
            
            # 自動化一覧
            elif "一覧" in message or "list" in message.lower():
                automation_list = []
                for automation in self.automations.values():
                    automation_list.append({
                        "id": automation.id,
                        "name": automation.name,
                        "description": automation.description,
                        "trigger_type": automation.trigger_type,
                        "is_active": automation.is_active
                    })
                
                return {
                    "response": "利用可能な自動化一覧です：\n" + "\n".join([f"- {a['name']} ({a['trigger_type']})" for a in automation_list]),
                    "type": "automation_list",
                    "automations": automation_list,
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            else:
                return {
                    "response": "自動化について何かお手伝いできますか？自動化の実行、一覧表示、作成などが可能です。",
                    "type": "automation_help",
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"自動化処理エラー: {e}")
            return {
                "response": "自動化の処理中にエラーが発生しました。",
                "type": "error",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _handle_notification(self, message: str, user_id: str) -> Dict[str, Any]:
        """通知を処理"""
        try:
            # 通知一覧
            notifications = self.db.query(Notification).filter(
                Notification.user_id == user_id,
                Notification.is_read == False
            ).all()
            
            notification_list = []
            for notification in notifications:
                notification_list.append({
                    "id": notification.id,
                    "title": notification.title,
                    "message": notification.message,
                    "type": notification.type,
                    "created_at": notification.created_at.isoformat()
                })
            
            return {
                "response": f"未読通知が{len(notification_list)}件あります：\n" + "\n".join([f"- {n['title']}: {n['message']}" for n in notification_list]),
                "type": "notification_list",
                "notifications": notification_list,
                "timestamp": datetime.utcnow().isoformat()
            }
                
        except Exception as e:
            logger.error(f"通知処理エラー: {e}")
            return {
                "response": "通知の処理中にエラーが発生しました。",
                "type": "error",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _handle_general_chat(self, message: str, user_id: str) -> Dict[str, Any]:
        """一般的なチャットを処理"""
        try:
            # AIエンジンに送信
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.ai_engines['localai']}/v1/chat/completions",
                    json={
                        "model": "qwen2.5:3b",
                        "messages": [{"role": "user", "content": message}],
                        "max_tokens": 500,
                        "temperature": 0.7
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    ai_response = data["choices"][0]["message"]["content"]
                    
                    return {
                        "response": ai_response,
                        "type": "ai_chat",
                        "ai_engine": "localai",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                else:
                    return {
                        "response": "AIエンジンからの応答を取得できませんでした。",
                        "type": "ai_error",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
        except Exception as e:
            logger.error(f"AIチャットエラー: {e}")
            return {
                "response": "AIエンジンとの通信中にエラーが発生しました。",
                "type": "ai_error",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def _extract_task_title(self, message: str) -> str:
        """メッセージからタスクタイトルを抽出"""
        # 簡単な抽出ロジック
        if "タスク" in message:
            return message.split("タスク")[1].strip()[:50]
        elif "task" in message.lower():
            return message.split("task")[1].strip()[:50]
        else:
            return message[:50]
    
    def _extract_schedule_title(self, message: str) -> str:
        """メッセージからスケジュールタイトルを抽出"""
        if "スケジュール" in message:
            return message.split("スケジュール")[1].strip()[:50]
        elif "schedule" in message.lower():
            return message.split("schedule")[1].strip()[:50]
        else:
            return message[:50]
    
    def _extract_automation_id(self, message: str) -> str:
        """メッセージから自動化IDを抽出"""
        # 簡単な抽出ロジック
        words = message.split()
        for word in words:
            if word in self.automations:
                return word
        return ""
    
    async def _execute_automation(self, automation_id: str) -> Dict[str, Any]:
        """自動化を実行"""
        try:
            automation = self.automations[automation_id]
            
            if automation.action_type == "script":
                # スクリプト実行
                result = subprocess.run(
                    automation.action_config.get("command", ""),
                    shell=True,
                    capture_output=True,
                    text=True
                )
                return {
                    "status": "success" if result.returncode == 0 else "error",
                    "output": result.stdout,
                    "error": result.stderr
                }
            
            elif automation.action_type == "api_call":
                # API呼び出し
                async with httpx.AsyncClient() as client:
                    response = await client.request(
                        method=automation.action_config.get("method", "GET"),
                        url=automation.action_config.get("url", ""),
                        headers=automation.action_config.get("headers", {}),
                        json=automation.action_config.get("data", {})
                    )
                    return {
                        "status": "success" if response.status_code < 400 else "error",
                        "status_code": response.status_code,
                        "response": response.text
                    }
            
            elif automation.action_type == "notification":
                # 通知送信
                notification = Notification(
                    id=f"notif_{int(time.time())}",
                    title=automation.action_config.get("title", "自動化通知"),
                    message=automation.action_config.get("message", "自動化が実行されました"),
                    type=automation.action_config.get("type", "info"),
                    user_id=automation.user_id
                )
                self.db.add(notification)
                self.db.commit()
                
                return {
                    "status": "success",
                    "message": "通知を送信しました"
                }
            
            else:
                return {
                    "status": "error",
                    "message": "未知のアクションタイプです"
                }
                
        except Exception as e:
            logger.error(f"自動化実行エラー: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def create_notification(self, title: str, message: str, notification_type: str = "info", user_id: str = "default_user"):
        """通知を作成"""
        try:
            notification = Notification(
                id=f"notif_{int(time.time())}",
                title=title,
                message=message,
                type=notification_type,
                user_id=user_id
            )
            self.db.add(notification)
            self.db.commit()
            
            # 通知キューに追加
            self.notifications.append({
                "id": notification.id,
                "title": title,
                "message": message,
                "type": notification_type,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            logger.info(f"通知を作成しました: {title}")
            
        except Exception as e:
            logger.error(f"通知作成エラー: {e}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """システムステータスを取得"""
        try:
            # システムリソース
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # データベース統計
            task_count = self.db.query(Task).count()
            schedule_count = self.db.query(Schedule).count()
            automation_count = self.db.query(Automation).filter(Automation.is_active == True).count()
            notification_count = self.db.query(Notification).filter(Notification.is_read == False).count()
            
            return {
                "system": {
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "disk_percent": disk.percent,
                    "uptime": time.time() - psutil.boot_time()
                },
                "manaos": {
                    "tasks": task_count,
                    "schedules": schedule_count,
                    "automations": automation_count,
                    "notifications": notification_count
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"システムステータス取得エラー: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

# ManaOS インスタンス
mana_os = ManaOSCore()

# FastAPIアプリケーション
app = FastAPI(title="ManaOS", version="1.0.0")

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 接続管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
    
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

# ルート
@app.get("/")
async def root():
    return {
        "message": "ManaOS - 統合オペレーティングシステム",
        "version": "1.0.0",
        "features": [
            "Trinity自動化システム",
            "Mana秘書システム",
            "AI統合チャット",
            "タスク管理",
            "スケジュール管理",
            "通知システム"
        ]
    }

@app.get("/status")
async def get_status():
    """システムステータスを取得"""
    return mana_os.get_system_status()

@app.post("/chat")
async def chat_endpoint(chat_message: ChatMessage):
    """チャットエンドポイント"""
    try:
        result = await mana_os.process_chat_message(chat_message.message, chat_message.user_id)
        return result
    except Exception as e:
        logger.error(f"チャットエンドポイントエラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tasks")
async def create_task(task: TaskCreate):
    """タスクを作成"""
    try:
        task_obj = Task(
            id=f"task_{int(time.time())}",
            title=task.title,
            description=task.description,
            priority=task.priority,
            due_date=task.due_date,
            user_id=task.user_id
        )
        mana_os.db.add(task_obj)
        mana_os.db.commit()
        
        return {
            "status": "success",
            "task_id": task_obj.id,
            "message": f"タスク「{task.title}」を作成しました"
        }
    except Exception as e:
        logger.error(f"タスク作成エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tasks/{user_id}")
async def get_tasks(user_id: str):
    """ユーザーのタスク一覧を取得"""
    try:
        tasks = mana_os.db.query(Task).filter(Task.user_id == user_id).all()
        task_list = []
        for task in tasks:
            task_list.append({
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "status": task.status,
                "priority": task.priority,
                "due_date": task.due_date.isoformat() if task.due_date else None,  # type: ignore
                "created_at": task.created_at.isoformat()
            })
        
        return {
            "status": "success",
            "tasks": task_list
        }
    except Exception as e:
        logger.error(f"タスク取得エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/schedules")
async def create_schedule(schedule: ScheduleCreate):
    """スケジュールを作成"""
    try:
        schedule_obj = Schedule(
            id=f"schedule_{int(time.time())}",
            title=schedule.title,
            description=schedule.description,
            start_time=schedule.start_time,
            end_time=schedule.end_time,
            is_recurring=schedule.is_recurring,
            recurrence_pattern=schedule.recurrence_pattern,
            user_id=schedule.user_id
        )
        mana_os.db.add(schedule_obj)
        mana_os.db.commit()
        
        return {
            "status": "success",
            "schedule_id": schedule_obj.id,
            "message": f"スケジュール「{schedule.title}」を作成しました"
        }
    except Exception as e:
        logger.error(f"スケジュール作成エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/schedules/{user_id}")
async def get_schedules(user_id: str):
    """ユーザーのスケジュール一覧を取得"""
    try:
        schedules = mana_os.db.query(Schedule).filter(Schedule.user_id == user_id).all()
        schedule_list = []
        for schedule in schedules:
            schedule_list.append({
                "id": schedule.id,
                "title": schedule.title,
                "description": schedule.description,
                "start_time": schedule.start_time.isoformat(),
                "end_time": schedule.end_time.isoformat() if schedule.end_time else None,  # type: ignore
                "is_recurring": schedule.is_recurring,
                "recurrence_pattern": schedule.recurrence_pattern,
                "created_at": schedule.created_at.isoformat()
            })
        
        return {
            "status": "success",
            "schedules": schedule_list
        }
    except Exception as e:
        logger.error(f"スケジュール取得エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/automations")
async def create_automation(automation: AutomationCreate):
    """自動化を作成"""
    try:
        automation_obj = Automation(
            id=f"automation_{int(time.time())}",
            name=automation.name,
            description=automation.description,
            trigger_type=automation.trigger_type,
            trigger_config=automation.trigger_config,
            action_type=automation.action_type,
            action_config=automation.action_config,
            user_id=automation.user_id
        )
        mana_os.db.add(automation_obj)
        mana_os.db.commit()
        
        # 自動化をメモリに追加
        mana_os.automations[automation_obj.id] = automation_obj
        
        return {
            "status": "success",
            "automation_id": automation_obj.id,
            "message": f"自動化「{automation.name}」を作成しました"
        }
    except Exception as e:
        logger.error(f"自動化作成エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/automations/{user_id}")
async def get_automations(user_id: str):
    """ユーザーの自動化一覧を取得"""
    try:
        automations = mana_os.db.query(Automation).filter(Automation.user_id == user_id).all()
        automation_list = []
        for automation in automations:
            automation_list.append({
                "id": automation.id,
                "name": automation.name,
                "description": automation.description,
                "trigger_type": automation.trigger_type,
                "action_type": automation.action_type,
                "is_active": automation.is_active,
                "created_at": automation.created_at.isoformat()
            })
        
        return {
            "status": "success",
            "automations": automation_list
        }
    except Exception as e:
        logger.error(f"自動化取得エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/notifications")
async def create_notification(title: str, message: str, notification_type: str = "info", user_id: str = "default_user"):
    """通知を作成"""
    try:
        mana_os.create_notification(title, message, notification_type, user_id)
        return {
            "status": "success",
            "message": "通知を作成しました"
        }
    except Exception as e:
        logger.error(f"通知作成エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/notifications/{user_id}")
async def get_notifications(user_id: str):
    """ユーザーの通知一覧を取得"""
    try:
        notifications = mana_os.db.query(Notification).filter(Notification.user_id == user_id).all()
        notification_list = []
        for notification in notifications:
            notification_list.append({
                "id": notification.id,
                "title": notification.title,
                "message": notification.message,
                "type": notification.type,
                "is_read": notification.is_read,
                "created_at": notification.created_at.isoformat()
            })
        
        return {
            "status": "success",
            "notifications": notification_list
        }
    except Exception as e:
        logger.error(f"通知取得エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocketエンドポイント"""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # ManaOSでメッセージを処理
            result = await mana_os.process_chat_message(
                message_data["message"],
                message_data.get("user_id", "default_user")
            )
            
            # クライアントに送信
            await manager.send_personal_message(
                json.dumps(result, ensure_ascii=False),
                websocket
            )
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8085)

