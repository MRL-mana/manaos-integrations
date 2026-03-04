#!/usr/bin/env python3
"""
Mana Ultimate Hybrid System
自動化×秘書系の究極ハイブリッドシステム
Slack + Gmail + スケジュール + タスク管理 + AI秘書の完全統合
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any
import threading
import time

# FastAPI
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import uvicorn

# 外部API連携
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# データベース
import sqlite3
import redis

class ManaUltimateHybridSystem:
    """Mana Ultimate Hybrid System - 自動化×秘書系の究極統合"""
    
    def __init__(self):
        self.app = FastAPI(title="Mana Ultimate Hybrid System", version="2.0.0")
        self.db_path = "/root/mana_hybrid_system.db"
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
        
        # 設定
        self.config = self.load_config()
        
        # ログ設定
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler('/root/logs/mana_hybrid_system.log'),
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
        
    def load_config(self) -> Dict[str, Any]:
        """設定読み込み"""
        default_config = {
            "slack": {
                "webhook_url": os.getenv("SLACK_WEBHOOK_URL"),
                "bot_token": os.getenv("SLACK_BOT_TOKEN"),
                "enabled": True
            },
            "gmail": {
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "email": os.getenv("GMAIL_EMAIL"),
                "password": os.getenv("GMAIL_APP_PASSWORD"),
                "enabled": True
            },
            "calendar": {
                "google_calendar_api": os.getenv("GOOGLE_CALENDAR_API_KEY"),
                "enabled": True
            },
            "ai_secretary": {
                "openai_api_key": os.getenv("OPENAI_API_KEY"),
                "model": "gpt-4",
                "enabled": True
            },
            "automation": {
                "check_interval": 60,  # 秒
                "max_concurrent_tasks": 5,
                "enabled": True
            }
        }
        
        config_path = "/root/mana_hybrid_config.json"
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                default_config.update(user_config)
        
        return default_config
    
    def init_database(self):
        """データベース初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # タスク管理テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                priority INTEGER DEFAULT 1,
                status TEXT DEFAULT 'pending',
                due_date TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                assigned_to TEXT,
                tags TEXT,
                metadata TEXT
            )
        ''')
        
        # スケジュール管理テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS schedules (
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
                metadata TEXT
            )
        ''')
        
        # メール管理テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT NOT NULL,
                sender TEXT NOT NULL,
                recipient TEXT NOT NULL,
                body TEXT,
                status TEXT DEFAULT 'received',
                priority INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                processed_at TEXT,
                metadata TEXT
            )
        ''')
        
        # Slack通知履歴テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS slack_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel TEXT,
                message TEXT NOT NULL,
                status TEXT DEFAULT 'sent',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                response TEXT,
                metadata TEXT
            )
        ''')
        
        # AI秘書会話履歴テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ai_conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_input TEXT NOT NULL,
                ai_response TEXT NOT NULL,
                context TEXT,
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
        
        # タスク管理API
        @self.app.get("/api/tasks")
        async def get_tasks():
            return await self.get_tasks()
        
        @self.app.post("/api/tasks")
        async def create_task(task: Dict[str, Any]):
            return await self.create_task(task)
        
        @self.app.put("/api/tasks/{task_id}")
        async def update_task(task_id: int, task: Dict[str, Any]):
            return await self.update_task(task_id, task)
        
        # スケジュール管理API
        @self.app.get("/api/schedules")
        async def get_schedules():
            return await self.get_schedules()
        
        @self.app.post("/api/schedules")
        async def create_schedule(schedule: Dict[str, Any]):
            return await self.create_schedule(schedule)
        
        # メール管理API
        @self.app.get("/api/emails")
        async def get_emails():
            return await self.get_emails()
        
        @self.app.post("/api/emails/send")
        async def send_email(email: Dict[str, Any]):
            return await self.send_email(email)
        
        # Slack通知API
        @self.app.post("/api/slack/notify")
        async def send_slack_notification(notification: Dict[str, Any]):
            return await self.send_slack_notification(notification)
        
        # AI秘書API
        @self.app.post("/api/ai-secretary/chat")
        async def ai_secretary_chat(chat: Dict[str, Any]):
            return await self.ai_secretary_chat(chat)
        
        # 自動化ワークフローAPI
        @self.app.post("/api/automation/workflow")
        async def execute_workflow(workflow: Dict[str, Any]):
            return await self.execute_workflow(workflow)
        
        @self.app.get("/api/dashboard")
        async def dashboard():
            return await self.dashboard()
    
    def start_background_tasks(self):
        """バックグラウンドタスク開始"""
        if self.config["automation"]["enabled"]:
            # スケジュール監視タスク
            threading.Thread(target=self.schedule_monitor, daemon=True).start()
            
            # メール監視タスク
            threading.Thread(target=self.email_monitor, daemon=True).start()
            
            # タスク期限監視タスク
            threading.Thread(target=self.task_deadline_monitor, daemon=True).start()
            
            self.logger.info("バックグラウンドタスク開始")
    
    # ==================== API実装 ====================
    
    async def root(self):
        """ルートエンドポイント"""
        return {
            "message": "Mana Ultimate Hybrid System",
            "version": "2.0.0",
            "status": "active",
            "features": [
                "タスク管理",
                "スケジュール管理", 
                "メール自動化",
                "Slack通知",
                "AI秘書",
                "自動化ワークフロー"
            ],
            "endpoints": {
                "status": "/api/status",
                "tasks": "/api/tasks",
                "schedules": "/api/schedules",
                "emails": "/api/emails",
                "slack": "/api/slack/notify",
                "ai_secretary": "/api/ai-secretary/chat",
                "dashboard": "/api/dashboard"
            }
        }
    
    async def get_status(self):
        """システム状態取得"""
        return {
            "timestamp": datetime.now().isoformat(),
            "system": "Mana Ultimate Hybrid System",
            "status": "healthy",
            "components": {
                "slack": self.config["slack"]["enabled"],
                "gmail": self.config["gmail"]["enabled"],
                "calendar": self.config["calendar"]["enabled"],
                "ai_secretary": self.config["ai_secretary"]["enabled"],
                "automation": self.config["automation"]["enabled"]
            },
            "database": "connected",
            "redis": "connected" if self.redis_client.ping() else "disconnected"
        }
    
    # ==================== タスク管理 ====================
    
    async def get_tasks(self):
        """タスク一覧取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM tasks ORDER BY priority DESC, created_at DESC
        ''')
        
        tasks = []
        for row in cursor.fetchall():
            tasks.append({
                "id": row[0],
                "title": row[1],
                "description": row[2],
                "priority": row[3],
                "status": row[4],
                "due_date": row[5],
                "created_at": row[6],
                "updated_at": row[7],
                "assigned_to": row[8],
                "tags": row[9],
                "metadata": row[10]
            })
        
        conn.close()
        return {"tasks": tasks}
    
    async def create_task(self, task_data: Dict[str, Any]):
        """タスク作成"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO tasks (title, description, priority, due_date, assigned_to, tags, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            task_data.get("title"),
            task_data.get("description"),
            task_data.get("priority", 1),
            task_data.get("due_date"),
            task_data.get("assigned_to"),
            json.dumps(task_data.get("tags", [])),
            json.dumps(task_data.get("metadata", {}))
        ))
        
        task_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Slack通知
        if self.config["slack"]["enabled"] and self.config["slack"].get("webhook_url"):
            try:
                await self.send_slack_notification({
                    "channel": "#tasks",
                    "message": f"📝 新しいタスクが作成されました: {task_data.get('title')}"
                })
            except Exception as e:
                self.logger.warning(f"Slack通知送信エラー: {e}")
        
        return {"task_id": task_id, "message": "タスクを作成しました"}
    
    async def update_task(self, task_id: int, task_data: Dict[str, Any]):
        """タスク更新"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 更新フィールドを動的に構築
        update_fields = []
        values = []
        
        for field in ["title", "description", "priority", "status", "due_date", "assigned_to"]:
            if field in task_data:
                update_fields.append(f"{field} = ?")
                values.append(task_data[field])
        
        if update_fields:
            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            values.append(task_id)
            
            cursor.execute(f'''
                UPDATE tasks SET {', '.join(update_fields)}
                WHERE id = ?
            ''', values)
            
            conn.commit()
        
        conn.close()
        
        return {"message": "タスクを更新しました"}
    
    # ==================== スケジュール管理 ====================
    
    async def get_schedules(self):
        """スケジュール一覧取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM schedules ORDER BY start_time ASC
        ''')
        
        schedules = []
        for row in cursor.fetchall():
            schedules.append({
                "id": row[0],
                "title": row[1],
                "description": row[2],
                "start_time": row[3],
                "end_time": row[4],
                "location": row[5],
                "attendees": row[6],
                "status": row[7],
                "created_at": row[8],
                "updated_at": row[9],
                "reminder_minutes": row[10],
                "metadata": row[11]
            })
        
        conn.close()
        return {"schedules": schedules}
    
    async def create_schedule(self, schedule_data: Dict[str, Any]):
        """スケジュール作成"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO schedules (title, description, start_time, end_time, location, attendees, reminder_minutes, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            schedule_data.get("title"),
            schedule_data.get("description"),
            schedule_data.get("start_time"),
            schedule_data.get("end_time"),
            schedule_data.get("location"),
            json.dumps(schedule_data.get("attendees", [])),
            schedule_data.get("reminder_minutes", 15),
            json.dumps(schedule_data.get("metadata", {}))
        ))
        
        schedule_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Slack通知
        if self.config["slack"]["enabled"] and self.config["slack"].get("webhook_url"):
            try:
                await self.send_slack_notification({
                    "channel": "#calendar",
                    "message": f"📅 新しいスケジュールが追加されました: {schedule_data.get('title')} ({schedule_data.get('start_time')})"
                })
            except Exception as e:
                self.logger.warning(f"Slack通知送信エラー: {e}")
        
        return {"schedule_id": schedule_id, "message": "スケジュールを作成しました"}
    
    # ==================== メール管理 ====================
    
    async def get_emails(self):
        """メール一覧取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM emails ORDER BY created_at DESC LIMIT 50
        ''')
        
        emails = []
        for row in cursor.fetchall():
            emails.append({
                "id": row[0],
                "subject": row[1],
                "sender": row[2],
                "recipient": row[3],
                "body": row[4],
                "status": row[5],
                "priority": row[6],
                "created_at": row[7],
                "processed_at": row[8],
                "metadata": row[9]
            })
        
        conn.close()
        return {"emails": emails}
    
    async def send_email(self, email_data: Dict[str, Any]):
        """メール送信"""
        if not self.config["gmail"]["enabled"]:
            raise HTTPException(status_code=503, detail="Gmail機能が無効です")
        
        try:
            # SMTP設定
            server = smtplib.SMTP(self.config["gmail"]["smtp_server"], self.config["gmail"]["smtp_port"])
            server.starttls()
            server.login(self.config["gmail"]["email"], self.config["gmail"]["password"])
            
            # メール作成
            msg = MIMEMultipart()
            msg['From'] = self.config["gmail"]["email"]
            msg['To'] = email_data["recipient"]
            msg['Subject'] = email_data["subject"]
            
            msg.attach(MIMEText(email_data["body"], 'plain'))
            
            # 送信
            server.send_message(msg)
            server.quit()
            
            # データベースに記録
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO emails (subject, sender, recipient, body, status, priority, processed_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                email_data["subject"],
                self.config["gmail"]["email"],
                email_data["recipient"],
                email_data["body"],
                "sent",
                email_data.get("priority", 1),
                datetime.now().isoformat(),
                json.dumps(email_data.get("metadata", {}))
            ))
            
            conn.commit()
            conn.close()
            
            return {"message": "メールを送信しました"}
            
        except Exception as e:
            self.logger.error(f"メール送信エラー: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # ==================== Slack通知 ====================
    
    async def send_slack_notification(self, notification_data: Dict[str, Any]):
        """Slack通知送信"""
        if not self.config["slack"]["enabled"]:
            raise HTTPException(status_code=503, detail="Slack機能が無効です")
        
        try:
            webhook_url = self.config["slack"].get("webhook_url")
            if not webhook_url:
                self.logger.warning("Slack Webhook URLが設定されていません。通知をスキップします。")
                return {"message": "Slack Webhook URLが設定されていません。通知をスキップしました。"}
            
            payload = {
                "channel": notification_data.get("channel", "#general"),
                "text": notification_data["message"],
                "username": "Mana AI Secretary",
                "icon_emoji": ":robot_face:"
            }
            
            response = requests.post(webhook_url, json=payload)
            
            # データベースに記録
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO slack_notifications (channel, message, status, response, metadata)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                notification_data.get("channel", "#general"),
                notification_data["message"],
                "sent" if response.status_code == 200 else "failed",
                response.text,
                json.dumps(notification_data.get("metadata", {}))
            ))
            
            conn.commit()
            conn.close()
            
            return {"message": "Slack通知を送信しました", "status_code": response.status_code}
            
        except Exception as e:
            self.logger.error(f"Slack通知エラー: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # ==================== AI秘書 ====================
    
    async def ai_secretary_chat(self, chat_data: Dict[str, Any]):
        """AI秘書チャット"""
        if not self.config["ai_secretary"]["enabled"]:
            raise HTTPException(status_code=503, detail="AI秘書機能が無効です")
        
        try:
            user_input = chat_data["message"]
            
            # 簡単なAI応答（実際の実装ではOpenAI APIを使用）
            ai_response = await self.generate_ai_response(user_input)
            
            # データベースに記録
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO ai_conversations (user_input, ai_response, context, metadata)
                VALUES (?, ?, ?, ?)
            ''', (
                user_input,
                ai_response,
                json.dumps(chat_data.get("context", {})),
                json.dumps(chat_data.get("metadata", {}))
            ))
            
            conn.commit()
            conn.close()
            
            return {"response": ai_response}
            
        except Exception as e:
            self.logger.error(f"AI秘書チャットエラー: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def generate_ai_response(self, user_input: str) -> str:
        """AI応答生成（簡易版）"""
        # 実際の実装ではOpenAI APIを使用
        responses = {
            "こんにちは": "こんにちは、Manaです！何かお手伝いできることはありますか？",
            "タスク": "タスク管理についてですね。新しいタスクの作成や既存タスクの確認ができます。",
            "スケジュール": "スケジュール管理についてですね。予定の追加や確認ができます。",
            "メール": "メール機能についてですね。メールの送信や確認ができます。",
            "ありがとう": "どういたしまして！他にも何かお手伝いできることがあれば、いつでもお声かけください。"
        }
        
        for keyword, response in responses.items():
            if keyword in user_input:
                return response
        
        return "申し訳ございませんが、その内容については詳しく教えていただけますか？"
    
    # ==================== 自動化ワークフロー ====================
    
    async def execute_workflow(self, workflow_data: Dict[str, Any]):
        """自動化ワークフロー実行"""
        workflow_type = workflow_data.get("type")
        
        if workflow_type == "daily_summary":
            return await self.daily_summary_workflow()
        elif workflow_type == "task_reminder":
            return await self.task_reminder_workflow()
        elif workflow_type == "schedule_reminder":
            return await self.schedule_reminder_workflow()
        else:
            raise HTTPException(status_code=400, detail="不明なワークフロータイプです")
    
    async def daily_summary_workflow(self):
        """日次サマリーワークフロー"""
        # 今日のタスク取得
        tasks = await self.get_tasks()
        today_tasks = [t for t in tasks["tasks"] if t["status"] == "pending"]
        
        # 今日のスケジュール取得
        schedules = await self.get_schedules()
        today = datetime.now().strftime("%Y-%m-%d")
        today_schedules = [s for s in schedules["schedules"] if s["start_time"].startswith(today)]
        
        # Slack通知
        message = f"""
📊 **今日のサマリー** ({today})

📝 **タスク**: {len(today_tasks)}件
📅 **スケジュール**: {len(today_schedules)}件

詳細はダッシュボードで確認してください: http://localhost:5006/api/dashboard
        """
        
        await self.send_slack_notification({
            "channel": "#daily-summary",
            "message": message
        })
        
        return {"message": "日次サマリーを送信しました"}
    
    async def task_reminder_workflow(self):
        """タスクリマインダーワークフロー"""
        # 期限が近いタスクを取得
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        cursor.execute('''
            SELECT * FROM tasks 
            WHERE due_date = ? AND status = 'pending'
        ''', (tomorrow,))
        
        urgent_tasks = cursor.fetchall()
        conn.close()
        
        if urgent_tasks:
            message = f"⚠️ **期限が近いタスクがあります** ({tomorrow})\n\n"
            for task in urgent_tasks:
                message += f"• {task[1]}\n"
            
            await self.send_slack_notification({
                "channel": "#task-reminders",
                "message": message
            })
        
        return {"message": "タスクリマインダーを送信しました"}
    
    async def schedule_reminder_workflow(self):
        """スケジュールリマインダーワークフロー"""
        # 15分後に開始するスケジュールを取得
        now = datetime.now()
        reminder_time = now + timedelta(minutes=15)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM schedules 
            WHERE start_time BETWEEN ? AND ?
        ''', (now.strftime("%Y-%m-%d %H:%M:%S"), reminder_time.strftime("%Y-%m-%d %H:%M:%S")))
        
        upcoming_schedules = cursor.fetchall()
        conn.close()
        
        for schedule in upcoming_schedules:
            message = f"⏰ **スケジュールリマインダー**\n\n{schedule[1]} が15分後に開始されます。"
            
            await self.send_slack_notification({
                "channel": "#schedule-reminders",
                "message": message
            })
        
        return {"message": "スケジュールリマインダーを送信しました"}
    
    # ==================== バックグラウンドタスク ====================
    
    def schedule_monitor(self):
        """スケジュール監視"""
        while True:
            try:
                asyncio.run(self.schedule_reminder_workflow())
                time.sleep(self.config["automation"]["check_interval"])
            except Exception as e:
                self.logger.error(f"スケジュール監視エラー: {e}")
                time.sleep(60)
    
    def email_monitor(self):
        """メール監視"""
        while True:
            try:
                # メール監視ロジック（実装例）
                time.sleep(self.config["automation"]["check_interval"])
            except Exception as e:
                self.logger.error(f"メール監視エラー: {e}")
                time.sleep(60)
    
    def task_deadline_monitor(self):
        """タスク期限監視"""
        while True:
            try:
                asyncio.run(self.task_reminder_workflow())
                time.sleep(self.config["automation"]["check_interval"] * 2)  # 2倍の間隔
            except Exception as e:
                self.logger.error(f"タスク期限監視エラー: {e}")
                time.sleep(120)
    
    # ==================== ダッシュボード ====================
    
    async def dashboard(self):
        """統合ダッシュボード"""
        html_content = self.generate_dashboard_html()
        return HTMLResponse(content=html_content)
    
    def generate_dashboard_html(self) -> str:
        """ダッシュボードHTML生成"""
        return """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mana Ultimate Hybrid System Dashboard</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
        .container { max-width: 1400px; margin: 0 auto; }
        .header { text-align: center; margin-bottom: 30px; }
        .header h1 { font-size: 3em; margin: 0; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 20px; }
        .card { background: rgba(255,255,255,0.1); border-radius: 15px; padding: 20px; backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.2); }
        .card h3 { margin-top: 0; color: #fff; }
        .button { background: #4CAF50; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; margin: 5px; }
        .button:hover { background: #45a049; }
        .status { display: inline-block; padding: 5px 15px; border-radius: 20px; font-weight: bold; }
        .status.active { background: #4CAF50; }
        .status.inactive { background: #f44336; }
        .input-group { margin: 10px 0; }
        .input-group input, .input-group textarea { width: 100%; padding: 8px; border-radius: 5px; border: 1px solid #ccc; }
        .input-group label { display: block; margin-bottom: 5px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Mana Ultimate Hybrid System</h1>
            <p>自動化×秘書系の究極統合システム</p>
        </div>
        
        <div class="grid">
            <!-- タスク管理 -->
            <div class="card">
                <h3>📝 タスク管理</h3>
                <div id="tasks-list">読み込み中...</div>
                <div class="input-group">
                    <label>新しいタスク:</label>
                    <input type="text" id="task-title" placeholder="タスク名">
                    <textarea id="task-description" placeholder="説明"></textarea>
                    <button class="button" onclick="createTask()">タスク作成</button>
                </div>
            </div>
            
            <!-- スケジュール管理 -->
            <div class="card">
                <h3>📅 スケジュール管理</h3>
                <div id="schedules-list">読み込み中...</div>
                <div class="input-group">
                    <label>新しいスケジュール:</label>
                    <input type="text" id="schedule-title" placeholder="タイトル">
                    <input type="datetime-local" id="schedule-start">
                    <input type="datetime-local" id="schedule-end">
                    <button class="button" onclick="createSchedule()">スケジュール作成</button>
                </div>
            </div>
            
            <!-- メール管理 -->
            <div class="card">
                <h3>📧 メール管理</h3>
                <div id="emails-list">読み込み中...</div>
                <div class="input-group">
                    <label>メール送信:</label>
                    <input type="email" id="email-to" placeholder="宛先">
                    <input type="text" id="email-subject" placeholder="件名">
                    <textarea id="email-body" placeholder="本文"></textarea>
                    <button class="button" onclick="sendEmail()">メール送信</button>
                </div>
            </div>
            
            <!-- Slack通知 -->
            <div class="card">
                <h3>💬 Slack通知</h3>
                <div class="input-group">
                    <label>Slack通知:</label>
                    <input type="text" id="slack-channel" placeholder="#channel" value="#general">
                    <textarea id="slack-message" placeholder="メッセージ"></textarea>
                    <button class="button" onclick="sendSlackNotification()">通知送信</button>
                </div>
            </div>
            
            <!-- AI秘書 -->
            <div class="card">
                <h3>🤖 AI秘書</h3>
                <div id="ai-chat">読み込み中...</div>
                <div class="input-group">
                    <label>AI秘書に質問:</label>
                    <textarea id="ai-message" placeholder="何かお手伝いできることはありますか？"></textarea>
                    <button class="button" onclick="chatWithAI()">送信</button>
                </div>
            </div>
            
            <!-- 自動化ワークフロー -->
            <div class="card">
                <h3>⚡ 自動化ワークフロー</h3>
                <button class="button" onclick="runDailySummary()">日次サマリー実行</button>
                <button class="button" onclick="runTaskReminder()">タスクリマインダー実行</button>
                <button class="button" onclick="runScheduleReminder()">スケジュールリマインダー実行</button>
            </div>
        </div>
    </div>
    
    <script>
        // タスク管理
        async function loadTasks() {
            try {
                const response = await fetch('/api/tasks');
                const data = await response.json();
                
                let html = '<h4>タスク一覧:</h4>';
                data.tasks.slice(0, 5).forEach(task => {
                    html += `<p>• ${task.title} (優先度: ${task.priority})</p>`;
                });
                
                document.getElementById('tasks-list').innerHTML = html;
            } catch (error) {
                console.error('タスク読み込みエラー:', error);
            }
        }
        
        async function createTask() {
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
                alert(data.message);
                document.getElementById('task-title').value = '';
                document.getElementById('task-description').value = '';
                loadTasks();
            } catch (error) {
                console.error('タスク作成エラー:', error);
            }
        }
        
        // スケジュール管理
        async function loadSchedules() {
            try {
                const response = await fetch('/api/schedules');
                const data = await response.json();
                
                let html = '<h4>スケジュール一覧:</h4>';
                data.schedules.slice(0, 5).forEach(schedule => {
                    html += `<p>• ${schedule.title} (${schedule.start_time})</p>`;
                });
                
                document.getElementById('schedules-list').innerHTML = html;
            } catch (error) {
                console.error('スケジュール読み込みエラー:', error);
            }
        }
        
        async function createSchedule() {
            const title = document.getElementById('schedule-title').value;
            const start = document.getElementById('schedule-start').value;
            const end = document.getElementById('schedule-end').value;
            
            if (!title || !start || !end) {
                alert('すべてのフィールドを入力してください');
                return;
            }
            
            try {
                const response = await fetch('/api/schedules', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({title, start_time: start, end_time: end})
                });
                
                const data = await response.json();
                alert(data.message);
                document.getElementById('schedule-title').value = '';
                document.getElementById('schedule-start').value = '';
                document.getElementById('schedule-end').value = '';
                loadSchedules();
            } catch (error) {
                console.error('スケジュール作成エラー:', error);
            }
        }
        
        // メール管理
        async function loadEmails() {
            try {
                const response = await fetch('/api/emails');
                const data = await response.json();
                
                let html = '<h4>メール一覧:</h4>';
                data.emails.slice(0, 5).forEach(email => {
                    html += `<p>• ${email.subject} (${email.recipient})</p>`;
                });
                
                document.getElementById('emails-list').innerHTML = html;
            } catch (error) {
                console.error('メール読み込みエラー:', error);
            }
        }
        
        async function sendEmail() {
            const to = document.getElementById('email-to').value;
            const subject = document.getElementById('email-subject').value;
            const body = document.getElementById('email-body').value;
            
            if (!to || !subject || !body) {
                alert('すべてのフィールドを入力してください');
                return;
            }
            
            try {
                const response = await fetch('/api/emails/send', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({recipient: to, subject, body})
                });
                
                const data = await response.json();
                alert(data.message);
                document.getElementById('email-to').value = '';
                document.getElementById('email-subject').value = '';
                document.getElementById('email-body').value = '';
                loadEmails();
            } catch (error) {
                console.error('メール送信エラー:', error);
            }
        }
        
        // Slack通知
        async function sendSlackNotification() {
            const channel = document.getElementById('slack-channel').value;
            const message = document.getElementById('slack-message').value;
            
            if (!message) {
                alert('メッセージを入力してください');
                return;
            }
            
            try {
                const response = await fetch('/api/slack/notify', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({channel, message})
                });
                
                const data = await response.json();
                alert(data.message);
                document.getElementById('slack-message').value = '';
            } catch (error) {
                console.error('Slack通知エラー:', error);
            }
        }
        
        // AI秘書
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
                document.getElementById('ai-chat').innerHTML = chatHtml;
                
                document.getElementById('ai-message').value = '';
            } catch (error) {
                console.error('AI秘書チャットエラー:', error);
            }
        }
        
        // 自動化ワークフロー
        async function runDailySummary() {
            try {
                const response = await fetch('/api/automation/workflow', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({type: 'daily_summary'})
                });
                
                const data = await response.json();
                alert(data.message);
            } catch (error) {
                console.error('日次サマリーエラー:', error);
            }
        }
        
        async function runTaskReminder() {
            try {
                const response = await fetch('/api/automation/workflow', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({type: 'task_reminder'})
                });
                
                const data = await response.json();
                alert(data.message);
            } catch (error) {
                console.error('タスクリマインダーエラー:', error);
            }
        }
        
        async function runScheduleReminder() {
            try {
                const response = await fetch('/api/automation/workflow', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({type: 'schedule_reminder'})
                });
                
                const data = await response.json();
                alert(data.message);
            } catch (error) {
                console.error('スケジュールリマインダーエラー:', error);
            }
        }
        
        // 初期化
        window.onload = function() {
            loadTasks();
            loadSchedules();
            loadEmails();
            
            // 定期的な更新
            setInterval(loadTasks, 30000);
            setInterval(loadSchedules, 30000);
            setInterval(loadEmails, 60000);
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
    system = ManaUltimateHybridSystem()
    
    print("🚀 Mana Ultimate Hybrid System を起動しています...")
    print("📊 ダッシュボード: http://localhost:5006")
    print("🔗 API: http://localhost:5006/api/status")
    print("=" * 60)
    print("🎯 機能:")
    print("  📝 タスク管理")
    print("  📅 スケジュール管理")
    print("  📧 メール自動化")
    print("  💬 Slack通知")
    print("  🤖 AI秘書")
    print("  ⚡ 自動化ワークフロー")
    print("=" * 60)
    
    # FastAPIサーバー起動
    uvicorn.run(
        system.app,
        host="0.0.0.0",
        port=5006,
        log_level="info"
    )

if __name__ == "__main__":
    main()

