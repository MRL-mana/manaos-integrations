#!/usr/bin/env python3
"""
Trinity Secretary Advanced - 統合AI秘書システム
複数の秘書機能を統合した超高度なAI秘書
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
from sqlalchemy import create_engine, Column, String, DateTime, Text, JSON, Boolean, Integer, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sklearn.feature_extraction.text import TfidfVectorizer

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# データベース設定
DATABASE_URL = os.getenv("POSTGRES_URL", "postgresql://mana:mana_secure_2024@localhost:5432/mana_ai")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# データベースモデル
class SecretaryProfile(Base):
    __tablename__ = "secretary_profiles"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    personality = Column(String, default="professional")  # professional, friendly, casual, formal
    expertise = Column(JSON)  # 専門分野
    preferences = Column(JSON)  # ユーザー設定
    user_id = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    status = Column(String, default="pending")
    priority = Column(Integer, default=1)
    due_date = Column(DateTime)
    estimated_duration = Column(Integer)  # 分
    actual_duration = Column(Integer)  # 分
    category = Column(String)  # work, personal, urgent, routine
    tags = Column(JSON)
    user_id = Column(String, nullable=False)
    secretary_id = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    metadata = Column(JSON)

class Schedule(Base):
    __tablename__ = "schedules"
    
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    location = Column(String)
    attendees = Column(JSON)
    is_recurring = Column(Boolean, default=False)
    recurrence_pattern = Column(String)
    reminder_minutes = Column(Integer, default=15)
    user_id = Column(String, nullable=False)
    secretary_id = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    metadata = Column(JSON)

class Communication(Base):
    __tablename__ = "communications"
    
    id = Column(String, primary_key=True)
    type = Column(String, nullable=False)  # email, call, meeting, message
    subject = Column(String)
    content = Column(Text)
    sender = Column(String)
    recipient = Column(String)
    status = Column(String, default="pending")  # pending, sent, delivered, read
    priority = Column(Integer, default=1)
    user_id = Column(String, nullable=False)
    secretary_id = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    metadata = Column(JSON)

class Learning(Base):
    __tablename__ = "learning"
    
    id = Column(String, primary_key=True)
    pattern = Column(String, nullable=False)  # 学習パターン
    context = Column(Text)
    response = Column(Text)
    feedback = Column(Float)  # 0.0-1.0
    user_id = Column(String, nullable=False)
    secretary_id = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    metadata = Column(JSON)

# Pydanticモデル
class SecretaryMessage(BaseModel):
    message: str
    user_id: str = "default_user"
    secretary_id: str = "trinity"
    context: Optional[Dict[str, Any]] = None
    urgency: int = 1  # 1-5 (5が最高)

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: int = 1
    due_date: Optional[datetime] = None
    category: str = "work"
    tags: Optional[List[str]] = None
    user_id: str = "default_user"
    secretary_id: str = "trinity"

class ScheduleCreate(BaseModel):
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    location: Optional[str] = None
    attendees: Optional[List[str]] = None
    reminder_minutes: int = 15
    user_id: str = "default_user"
    secretary_id: str = "trinity"

# Trinity Secretary Advanced クラス
class TrinitySecretaryAdvanced:
    def __init__(self):
        self.db = SessionLocal()
        self.redis_client = redis.Redis(host="redis", port=6379, decode_responses=True)
        self.secretaries = {}
        self.learning_models = {}
        self.conversation_history = deque(maxlen=1000)
        
        # AIエンジンURL
        self.ai_engines = {
            "localai": "http://localai:8080",
            "anythingllm": "http://anythingllm:3001",
            "gpt_oss": "http://gpt_oss:8080"
        }
        
        # 初期化
        self._initialize_database()
        self._load_secretaries()
        self._initialize_learning_models()
        self._start_background_tasks()
    
    def _initialize_database(self):
        """データベースを初期化"""
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("Trinity Secretary データベースを初期化しました")
        except Exception as e:
            logger.error(f"データベース初期化エラー: {e}")
    
    def _load_secretaries(self):
        """秘書プロファイルを読み込み"""
        try:
            profiles = self.db.query(SecretaryProfile).all()
            for profile in profiles:
                self.secretaries[profile.id] = {
                    "name": profile.name,
                    "personality": profile.personality,
                    "expertise": profile.expertise or [],
                    "preferences": profile.preferences or {},
                    "user_id": profile.user_id
                }
            logger.info(f"{len(profiles)}個の秘書プロファイルを読み込みました")
        except Exception as e:
            logger.error(f"秘書プロファイル読み込みエラー: {e}")
    
    def _initialize_learning_models(self):
        """学習モデルを初期化"""
        try:
            # TF-IDFベクトライザー
            self.learning_models["tfidf"] = TfidfVectorizer(
                max_features=1000,
                stop_words=None,
                ngram_range=(1, 2)
            )
            logger.info("学習モデルを初期化しました")
        except Exception as e:
            logger.error(f"学習モデル初期化エラー: {e}")
    
    def _start_background_tasks(self):
        """バックグラウンドタスクを開始"""
        def run_background_tasks():
            while True:
                try:
                    self._check_reminders()
                    self._process_learning()
                    self._update_analytics()
                    time.sleep(60)  # 1分ごと
                except Exception as e:
                    logger.error(f"バックグラウンドタスクエラー: {e}")
                    time.sleep(60)
        
        background_thread = threading.Thread(target=run_background_tasks, daemon=True)
        background_thread.start()
        logger.info("バックグラウンドタスクを開始しました")
    
    async def process_message(self, message: str, user_id: str, secretary_id: str = "trinity") -> Dict[str, Any]:
        """メッセージを処理"""
        try:
            # 秘書プロファイルを取得
            secretary = self.secretaries.get(secretary_id, {
                "name": "Trinity",
                "personality": "professional",
                "expertise": ["general"],
                "preferences": {}
            })
            
            # 意図を分析
            intent = await self._analyze_intent(message, secretary)
            
            # 学習データを更新
            self._update_learning_data(message, intent, user_id, secretary_id)
            
            # 意図に基づいて処理
            if intent == "task_management":
                return await self._handle_task_management(message, user_id, secretary_id, secretary)
            elif intent == "schedule_management":
                return await self._handle_schedule_management(message, user_id, secretary_id, secretary)
            elif intent == "communication":
                return await self._handle_communication(message, user_id, secretary_id, secretary)
            elif intent == "information_request":
                return await self._handle_information_request(message, user_id, secretary_id, secretary)
            elif intent == "personal_assistance":
                return await self._handle_personal_assistance(message, user_id, secretary_id, secretary)
            else:
                return await self._handle_general_conversation(message, user_id, secretary_id, secretary)
                
        except Exception as e:
            logger.error(f"メッセージ処理エラー: {e}")
            return {
                "response": "申し訳ございません。エラーが発生しました。",
                "type": "error",
                "secretary": secretary.get("name", "Trinity"),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _analyze_intent(self, message: str, secretary: Dict[str, Any]) -> str:
        """メッセージの意図を分析"""
        message_lower = message.lower()
        
        # タスク管理キーワード
        task_keywords = ["タスク", "task", "やること", "todo", "作業", "仕事", "プロジェクト"]
        if any(keyword in message_lower for keyword in task_keywords):
            return "task_management"
        
        # スケジュール管理キーワード
        schedule_keywords = ["スケジュール", "schedule", "予定", "会議", "アポイント", "時間", "カレンダー"]
        if any(keyword in message_lower for keyword in schedule_keywords):
            return "schedule_management"
        
        # コミュニケーションキーワード
        comm_keywords = ["メール", "email", "電話", "call", "連絡", "メッセージ", "message"]
        if any(keyword in message_lower for keyword in comm_keywords):
            return "communication"
        
        # 情報要求キーワード
        info_keywords = ["情報", "info", "調べて", "検索", "search", "教えて", "知りたい"]
        if any(keyword in message_lower for keyword in info_keywords):
            return "information_request"
        
        # 個人的なアシスタンスキーワード
        personal_keywords = ["手伝って", "help", "助けて", "困って", "どうしよう", "アドバイス"]
        if any(keyword in message_lower for keyword in personal_keywords):
            return "personal_assistance"
        
        return "general_conversation"
    
    async def _handle_task_management(self, message: str, user_id: str, secretary_id: str, secretary: Dict[str, Any]) -> Dict[str, Any]:
        """タスク管理を処理"""
        try:
            # タスク作成
            if "作成" in message or "追加" in message or "create" in message.lower():
                task_info = self._extract_task_info(message)
                task = Task(
                    id=f"task_{int(time.time())}",
                    title=task_info["title"],
                    description=task_info["description"],
                    priority=task_info["priority"],
                    due_date=task_info["due_date"],
                    category=task_info["category"],
                    tags=task_info["tags"],
                    user_id=user_id,
                    secretary_id=secretary_id
                )
                self.db.add(task)
                self.db.commit()
                
                response = f"タスク「{task_info['title']}」を作成しました！"
                if task_info["due_date"]:
                    response += f" 締切は{task_info['due_date'].strftime('%Y年%m月%d日 %H:%M')}です。"
                
                return {
                    "response": response,
                    "type": "task_created",
                    "task_id": task.id,
                    "secretary": secretary["name"],
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            # タスク一覧
            elif "一覧" in message or "list" in message.lower():
                tasks = self.db.query(Task).filter(
                    Task.user_id == user_id,
                    Task.secretary_id == secretary_id
                ).all()
                
                task_list = []
                for task in tasks:
                    task_list.append({
                        "id": task.id,
                        "title": task.title,
                        "status": task.status,
                        "priority": task.priority,
                        "due_date": task.due_date.isoformat() if task.due_date else None,
                        "category": task.category
                    })
                
                response = "現在のタスク一覧です：\n"
                for task in task_list:
                    status_emoji = {"pending": "⏳", "in_progress": "🔄", "completed": "✅", "cancelled": "❌"}
                    priority_emoji = {1: "🟢", 2: "🟡", 3: "🟠", 4: "🔴", 5: "🚨"}
                    response += f"{status_emoji.get(task['status'], '❓')} {priority_emoji.get(task['priority'], '⚪')} {task['title']}\n"
                
                return {
                    "response": response,
                    "type": "task_list",
                    "tasks": task_list,
                    "secretary": secretary["name"],
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            else:
                return {
                    "response": "タスク管理について何かお手伝いできますか？タスクの作成、一覧表示、更新、完了などが可能です。",
                    "type": "task_help",
                    "secretary": secretary["name"],
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"タスク管理エラー: {e}")
            return {
                "response": "タスクの処理中にエラーが発生しました。",
                "type": "error",
                "secretary": secretary["name"],
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _handle_schedule_management(self, message: str, user_id: str, secretary_id: str, secretary: Dict[str, Any]) -> Dict[str, Any]:
        """スケジュール管理を処理"""
        try:
            # スケジュール作成
            if "作成" in message or "追加" in message or "create" in message.lower():
                schedule_info = self._extract_schedule_info(message)
                schedule = Schedule(
                    id=f"schedule_{int(time.time())}",
                    title=schedule_info["title"],
                    description=schedule_info["description"],
                    start_time=schedule_info["start_time"],
                    end_time=schedule_info["end_time"],
                    location=schedule_info["location"],
                    attendees=schedule_info["attendees"],
                    reminder_minutes=schedule_info["reminder_minutes"],
                    user_id=user_id,
                    secretary_id=secretary_id
                )
                self.db.add(schedule)
                self.db.commit()
                
                response = f"スケジュール「{schedule_info['title']}」を作成しました！"
                response += f" 開始時刻は{schedule_info['start_time'].strftime('%Y年%m月%d日 %H:%M')}です。"
                if schedule_info["location"]:
                    response += f" 場所は{schedule_info['location']}です。"
                
                return {
                    "response": response,
                    "type": "schedule_created",
                    "schedule_id": schedule.id,
                    "secretary": secretary["name"],
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            # スケジュール一覧
            elif "一覧" in message or "list" in message.lower():
                schedules = self.db.query(Schedule).filter(
                    Schedule.user_id == user_id,
                    Schedule.secretary_id == secretary_id
                ).all()
                
                schedule_list = []
                for schedule in schedules:
                    schedule_list.append({
                        "id": schedule.id,
                        "title": schedule.title,
                        "start_time": schedule.start_time.isoformat(),
                        "end_time": schedule.end_time.isoformat() if schedule.end_time else None,
                        "location": schedule.location,
                        "attendees": schedule.attendees
                    })
                
                response = "現在のスケジュール一覧です：\n"
                for schedule in schedule_list:
                    start_time = datetime.fromisoformat(schedule['start_time'])
                    response += f"📅 {start_time.strftime('%m/%d %H:%M')} - {schedule['title']}\n"
                
                return {
                    "response": response,
                    "type": "schedule_list",
                    "schedules": schedule_list,
                    "secretary": secretary["name"],
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            else:
                return {
                    "response": "スケジュール管理について何かお手伝いできますか？スケジュールの作成、一覧表示、更新、削除などが可能です。",
                    "type": "schedule_help",
                    "secretary": secretary["name"],
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"スケジュール管理エラー: {e}")
            return {
                "response": "スケジュールの処理中にエラーが発生しました。",
                "type": "error",
                "secretary": secretary["name"],
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _handle_communication(self, message: str, user_id: str, secretary_id: str, secretary: Dict[str, Any]) -> Dict[str, Any]:
        """コミュニケーションを処理"""
        try:
            # メール作成
            if "メール" in message or "email" in message.lower():
                email_info = self._extract_email_info(message)
                communication = Communication(
                    id=f"comm_{int(time.time())}",
                    type="email",
                    subject=email_info["subject"],
                    content=email_info["content"],
                    recipient=email_info["recipient"],
                    user_id=user_id,
                    secretary_id=secretary_id
                )
                self.db.add(communication)
                self.db.commit()
                
                response = f"メール「{email_info['subject']}」を作成しました！"
                if email_info["recipient"]:
                    response += f" 宛先は{email_info['recipient']}です。"
                
                return {
                    "response": response,
                    "type": "email_created",
                    "communication_id": communication.id,
                    "secretary": secretary["name"],
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            # 電話関連
            elif "電話" in message or "call" in message.lower():
                return {
                    "response": "電話に関するお手伝いをします。誰に電話をかけたいですか？",
                    "type": "phone_assistance",
                    "secretary": secretary["name"],
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            else:
                return {
                    "response": "コミュニケーションについて何かお手伝いできますか？メール、電話、メッセージなどの作成や管理が可能です。",
                    "type": "communication_help",
                    "secretary": secretary["name"],
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"コミュニケーション処理エラー: {e}")
            return {
                "response": "コミュニケーションの処理中にエラーが発生しました。",
                "type": "error",
                "secretary": secretary["name"],
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _handle_information_request(self, message: str, user_id: str, secretary_id: str, secretary: Dict[str, Any]) -> Dict[str, Any]:
        """情報要求を処理"""
        try:
            # AIエンジンに送信
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.ai_engines['gpt_oss']}/v1/chat/completions",
                    json={
                        "model": "gpt-oss-20b",
                        "messages": [{"role": "user", "content": message}],
                        "max_tokens": 1000,
                        "temperature": 0.7
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    ai_response = data["choices"][0]["message"]["content"]
                    
                    return {
                        "response": ai_response,
                        "type": "information_response",
                        "secretary": secretary["name"],
                        "ai_engine": "gpt_oss",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                else:
                    return {
                        "response": "情報の取得中にエラーが発生しました。",
                        "type": "information_error",
                        "secretary": secretary["name"],
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
        except Exception as e:
            logger.error(f"情報要求処理エラー: {e}")
            return {
                "response": "情報の取得中にエラーが発生しました。",
                "type": "error",
                "secretary": secretary["name"],
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _handle_personal_assistance(self, message: str, user_id: str, secretary_id: str, secretary: Dict[str, Any]) -> Dict[str, Any]:
        """個人的なアシスタンスを処理"""
        try:
            # 感情分析
            sentiment = self._analyze_sentiment(message)
            
            # 感情に基づいた応答
            if sentiment == "positive":
                response = f"素晴らしいですね！{secretary['name']}がお手伝いします。具体的にどのようなことでお困りですか？"
            elif sentiment == "negative":
                response = f"お疲れ様です。{secretary['name']}がサポートします。一緒に解決していきましょう。"
            else:
                response = f"はい、{secretary['name']}がお手伝いします。どのようなことでお困りですか？"
            
            return {
                "response": response,
                "type": "personal_assistance",
                "sentiment": sentiment,
                "secretary": secretary["name"],
                "timestamp": datetime.utcnow().isoformat()
            }
                
        except Exception as e:
            logger.error(f"個人的アシスタンス処理エラー: {e}")
            return {
                "response": "個人的なアシスタンスの処理中にエラーが発生しました。",
                "type": "error",
                "secretary": secretary["name"],
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _handle_general_conversation(self, message: str, user_id: str, secretary_id: str, secretary: Dict[str, Any]) -> Dict[str, Any]:
        """一般的な会話を処理"""
        try:
            # 秘書の人格に基づいた応答
            personality = secretary.get("personality", "professional")
            
            if personality == "friendly":
                greeting = "こんにちは！"
                tone = "親しみやすい"
            elif personality == "casual":
                greeting = "やあ！"
                tone = "カジュアル"
            elif personality == "formal":
                greeting = "お疲れ様です。"
                tone = "フォーマル"
            else:  # professional
                greeting = "お疲れ様です。"
                tone = "プロフェッショナル"
            
            # AIエンジンに送信
            async with httpx.AsyncClient() as client:
                prompt = f"{greeting} {secretary['name']}です。{tone}なトーンで応答してください。\n\nユーザー: {message}\n{secretary['name']}:"
                
                response = await client.post(
                    f"{self.ai_engines['localai']}/v1/chat/completions",
                    json={
                        "model": "qwen2.5:3b",
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 500,
                        "temperature": 0.8
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    ai_response = data["choices"][0]["message"]["content"]
                    
                    return {
                        "response": ai_response,
                        "type": "general_conversation",
                        "secretary": secretary["name"],
                        "personality": personality,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                else:
                    return {
                        "response": f"{greeting} {secretary['name']}です。何かお手伝いできることはありますか？",
                        "type": "general_conversation",
                        "secretary": secretary["name"],
                        "personality": personality,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
        except Exception as e:
            logger.error(f"一般会話処理エラー: {e}")
            return {
                "response": f"こんにちは！{secretary['name']}です。何かお手伝いできることはありますか？",
                "type": "general_conversation",
                "secretary": secretary["name"],
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def _extract_task_info(self, message: str) -> Dict[str, Any]:
        """メッセージからタスク情報を抽出"""
        # 簡単な抽出ロジック
        title = message[:50] if len(message) > 50 else message
        description = message
        priority = 1
        due_date = None
        category = "work"
        tags = []
        
        # 優先度の抽出
        if "重要" in message or "urgent" in message.lower():
            priority = 5
        elif "高" in message or "high" in message.lower():
            priority = 4
        elif "中" in message or "medium" in message.lower():
            priority = 3
        elif "低" in message or "low" in message.lower():
            priority = 2
        
        # カテゴリの抽出
        if "個人" in message or "personal" in message.lower():
            category = "personal"
        elif "緊急" in message or "urgent" in message.lower():
            category = "urgent"
        elif "ルーティン" in message or "routine" in message.lower():
            category = "routine"
        
        return {
            "title": title,
            "description": description,
            "priority": priority,
            "due_date": due_date,
            "category": category,
            "tags": tags
        }
    
    def _extract_schedule_info(self, message: str) -> Dict[str, Any]:
        """メッセージからスケジュール情報を抽出"""
        title = message[:50] if len(message) > 50 else message
        description = message
        start_time = datetime.utcnow() + timedelta(hours=1)  # デフォルトで1時間後
        end_time = start_time + timedelta(hours=1)  # デフォルトで1時間
        location = None
        attendees = []
        reminder_minutes = 15
        
        return {
            "title": title,
            "description": description,
            "start_time": start_time,
            "end_time": end_time,
            "location": location,
            "attendees": attendees,
            "reminder_minutes": reminder_minutes
        }
    
    def _extract_email_info(self, message: str) -> Dict[str, Any]:
        """メッセージからメール情報を抽出"""
        subject = message[:50] if len(message) > 50 else message
        content = message
        recipient = None
        
        return {
            "subject": subject,
            "content": content,
            "recipient": recipient
        }
    
    def _analyze_sentiment(self, message: str) -> str:
        """感情を分析"""
        positive_words = ["嬉しい", "楽しい", "良い", "素晴らしい", "ありがとう", "助かった"]
        negative_words = ["疲れた", "困った", "大変", "辛い", "悲しい", "怒り"]
        
        message_lower = message.lower()
        
        positive_count = sum(1 for word in positive_words if word in message_lower)
        negative_count = sum(1 for word in negative_words if word in message_lower)
        
        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"
    
    def _update_learning_data(self, message: str, intent: str, user_id: str, secretary_id: str):
        """学習データを更新"""
        try:
            learning = Learning(
                id=f"learning_{int(time.time())}",
                pattern=intent,
                context=message,
                response="",  # 後で更新
                feedback=0.5,  # デフォルト
                user_id=user_id,
                secretary_id=secretary_id
            )
            self.db.add(learning)
            self.db.commit()
        except Exception as e:
            logger.error(f"学習データ更新エラー: {e}")
    
    def _check_reminders(self):
        """リマインダーをチェック"""
        try:
            now = datetime.utcnow()
            schedules = self.db.query(Schedule).filter(
                Schedule.reminder_minutes.isnot(None),
                Schedule.start_time > now,
                Schedule.start_time <= now + timedelta(minutes=30)
            ).all()
            
            for schedule in schedules:
                # リマインダー通知を作成
                self._create_notification(
                    f"リマインダー: {schedule.title}",
                    f"{schedule.start_time.strftime('%H:%M')}に{schedule.title}があります。",
                    "info",
                    schedule.user_id
                )
        except Exception as e:
            logger.error(f"リマインダーチェックエラー: {e}")
    
    def _process_learning(self):
        """学習処理を実行"""
        try:
            # 学習データを取得
            learnings = self.db.query(Learning).filter(
                Learning.feedback.isnot(None)
            ).all()
            
            if learnings:
                # 学習モデルを更新
                contexts = [l.context for l in learnings]
                patterns = [l.pattern for l in learnings]
                
                if contexts and patterns:
                    # TF-IDFベクトライザーを学習
                    self.learning_models["tfidf"].fit(contexts)
                    logger.info("学習モデルを更新しました")
        except Exception as e:
            logger.error(f"学習処理エラー: {e}")
    
    def _update_analytics(self):
        """アナリティクスを更新"""
        try:
            # 統計情報を計算
            task_count = self.db.query(Task).count()
            schedule_count = self.db.query(Schedule).count()
            communication_count = self.db.query(Communication).count()
            
            # Redisに保存
            self.redis_client.setex("analytics:tasks", 3600, task_count)
            self.redis_client.setex("analytics:schedules", 3600, schedule_count)
            self.redis_client.setex("analytics:communications", 3600, communication_count)
        except Exception as e:
            logger.error(f"アナリティクス更新エラー: {e}")
    
    def _create_notification(self, title: str, message: str, notification_type: str, user_id: str):
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
            
            logger.info(f"通知を作成しました: {title}")
        except Exception as e:
            logger.error(f"通知作成エラー: {e}")

# Trinity Secretary インスタンス
trinity_secretary = TrinitySecretaryAdvanced()

# FastAPIアプリケーション
app = FastAPI(title="Trinity Secretary Advanced", version="1.0.0")

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
        "message": "Trinity Secretary Advanced - 統合AI秘書システム",
        "version": "1.0.0",
        "features": [
            "タスク管理",
            "スケジュール管理",
            "コミュニケーション管理",
            "情報検索",
            "個人的アシスタンス",
            "学習機能",
            "複数秘書プロファイル"
        ]
    }

@app.post("/chat")
async def chat_endpoint(secretary_message: SecretaryMessage):
    """チャットエンドポイント"""
    try:
        result = await trinity_secretary.process_message(
            secretary_message.message,
            secretary_message.user_id,
            secretary_message.secretary_id
        )
        return result
    except Exception as e:
        logger.error(f"チャットエンドポイントエラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocketエンドポイント"""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Trinity Secretaryでメッセージを処理
            result = await trinity_secretary.process_message(
                message_data["message"],
                message_data.get("user_id", "default_user"),
                message_data.get("secretary_id", "trinity")
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
    uvicorn.run(app, host="0.0.0.0", port=8086)

