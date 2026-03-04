#!/usr/bin/env python3
"""
Trinity Secretary Enhanced
AI駆動の拡張秘書システム - スマート自動化機能追加
"""

import json
import logging
import os
import re
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Any

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
import asyncio
import threading

# AI/NLP
try:
    import openai
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False

# 学習系・記憶系連携
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "secretary_learning_integration",
        "/root/trinity_automation/trinity_secretary_learning_integration.py"
    )
    learning_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(learning_module)
    secretary_learning = learning_module.get_secretary_learning()
    LEARNING_INTEGRATION_AVAILABLE = True
except Exception as e:
    LEARNING_INTEGRATION_AVAILABLE = False
    secretary_learning = None
    logger.warning(f"学習統合モジュールのロード失敗: {e}")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TrinitySecretaryEnhanced:
    def __init__(self):
        self.app = FastAPI(title="Trinity Secretary Enhanced", version="2.0.0")
        self.db_path = "/root/trinity_secretary_enhanced.db"

        # 設定
        self.config = {
            "auto_categorize_emails": True,
            "auto_generate_reports": True,
            "smart_scheduling": True,
            "task_priority_detection": True,
            "daily_report_time": "09:00",
            "weekly_report_day": "Monday"
        }

        # データベース初期化
        self.init_database()

        # ミドルウェア・ルート設定
        self.setup_middleware()
        self.setup_routes()

        # バックグラウンドタスク開始
        self.start_background_tasks()

        logger.info("🤖 Trinity Secretary Enhanced 起動完了")

    def setup_middleware(self):
        """CORS設定"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def init_database(self):
        """データベース初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # スマートタスクテーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS smart_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                priority TEXT DEFAULT 'medium',
                category TEXT,
                status TEXT DEFAULT 'pending',
                due_date TEXT,
                auto_detected BOOLEAN DEFAULT 0,
                source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
        ''')

        # メール分析テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS email_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_id TEXT,
                sender TEXT,
                subject TEXT,
                priority TEXT,
                category TEXT,
                action_required BOOLEAN DEFAULT 0,
                sentiment TEXT,
                summary TEXT,
                analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # カレンダー予定テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS calendar_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT UNIQUE,
                title TEXT,
                description TEXT,
                start_time TEXT,
                end_time TEXT,
                location TEXT,
                attendees TEXT,
                auto_created BOOLEAN DEFAULT 0,
                source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # レポートテーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_type TEXT,
                period TEXT,
                data TEXT,
                summary TEXT,
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 自動化ルールテーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS automation_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_name TEXT,
                trigger_type TEXT,
                condition TEXT,
                action TEXT,
                enabled BOOLEAN DEFAULT 1,
                last_executed TIMESTAMP,
                execution_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        conn.close()
        logger.info("データベース初期化完了")

    # === AI駆動タスク管理 ===

    def parse_natural_language_task(self, text: str) -> Dict[str, Any]:
        """自然言語からタスクを解析（新機能）"""
        try:
            # 優先度検出
            priority = "medium"
            if re.search(r'(緊急|urgent|asap|至急)', text, re.I):
                priority = "high"
            elif re.search(r'(重要|important|critical)', text, re.I):
                priority = "high"
            elif re.search(r'(低優先|low priority|後で)', text, re.I):
                priority = "low"

            # 期限検出
            due_date = None
            date_patterns = [
                (r'今日', datetime.now()),
                (r'明日', datetime.now() + timedelta(days=1)),
                (r'明後日', datetime.now() + timedelta(days=2)),
                (r'来週', datetime.now() + timedelta(weeks=1)),
                (r'(\d+)日後', None),  # 特別処理
            ]

            for pattern, date in date_patterns:
                match = re.search(pattern, text)
                if match:
                    if pattern == r'(\d+)日後':
                        days = int(match.group(1))
                        due_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
                    elif date:
                        due_date = date.strftime("%Y-%m-%d")
                    break

            # カテゴリ検出
            category = "general"
            categories = {
                "仕事": ["仕事", "work", "業務", "会議"],
                "個人": ["個人", "personal", "プライベート"],
                "学習": ["学習", "study", "勉強"],
                "買い物": ["買い物", "shopping", "購入"],
                "健康": ["健康", "health", "運動"]
            }

            for cat, keywords in categories.items():
                if any(keyword in text for keyword in keywords):
                    category = cat
                    break

            return {
                "title": text[:100],  # 最初の100文字をタイトルに
                "description": text,
                "priority": priority,
                "category": category,
                "due_date": due_date,
                "auto_detected": True
            }

        except Exception as e:
            logger.error(f"タスク解析エラー: {e}")
            return {
                "title": text[:100],
                "description": text,
                "priority": "medium",
                "category": "general"
            }

    def create_smart_task(self, text: str, source: str = "manual") -> Dict[str, Any]:
        """スマートタスク作成（新機能）"""
        try:
            # 自然言語解析
            task_data = self.parse_natural_language_task(text)
            task_data["source"] = source

            # データベースに保存
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO smart_tasks
                (title, description, priority, category, due_date, auto_detected, source)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                task_data["title"],
                task_data["description"],
                task_data["priority"],
                task_data["category"],
                task_data.get("due_date"),
                task_data.get("auto_detected", False),
                source
            ))

            task_id = cursor.lastrowid
            conn.commit()
            conn.close()

            # 学習系・記憶系に記録
            if LEARNING_INTEGRATION_AVAILABLE and secretary_learning:
                try:
                    secretary_learning.log_task_creation(task_data)
                except Exception as e:
                    logger.warning(f"学習系記録エラー: {e}")

            logger.info(f"スマートタスク作成: {task_id} - {task_data['title']}")
            return {"success": True, "task_id": task_id, "task": task_data}

        except Exception as e:
            logger.error(f"スマートタスク作成エラー: {e}")
            return {"success": False, "error": str(e)}

    def get_tasks_by_priority(self, limit: int = 20) -> List[Dict[str, Any]]:
        """優先度別タスク取得"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT * FROM smart_tasks
                WHERE status = 'pending'
                ORDER BY
                    CASE priority
                        WHEN 'high' THEN 1
                        WHEN 'medium' THEN 2
                        WHEN 'low' THEN 3
                    END,
                    due_date ASC,
                    created_at DESC
                LIMIT ?
            ''', (limit,))

            columns = [desc[0] for desc in cursor.description]
            tasks = []
            for row in cursor.fetchall():
                tasks.append(dict(zip(columns, row)))

            conn.close()
            return tasks

        except Exception as e:
            logger.error(f"タスク取得エラー: {e}")
            return []

    # === スマートメール管理 ===

    def analyze_email(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """メール分析（新機能）"""
        try:
            sender = email_data.get("sender", "")
            subject = email_data.get("subject", "")
            body = email_data.get("body", "")

            # 優先度判定
            priority = "medium"
            high_keywords = ["緊急", "urgent", "重要", "important", "至急", "asap"]
            low_keywords = ["newsletter", "広告", "お知らせ"]

            if any(keyword in (subject + body).lower() for keyword in high_keywords):
                priority = "high"
            elif any(keyword in (subject + body).lower() for keyword in low_keywords):
                priority = "low"

            # カテゴリ分類
            category = "general"
            categories = {
                "work": ["会議", "meeting", "プロジェクト", "project"],
                "personal": ["個人", "personal"],
                "finance": ["請求", "invoice", "支払い", "payment"],
                "social": ["イベント", "event", "招待"]
            }

            for cat, keywords in categories.items():
                if any(keyword in (subject + body).lower() for keyword in keywords):
                    category = cat
                    break

            # アクション要求判定
            action_required = False
            action_keywords = ["返信", "reply", "確認", "confirm", "承認", "approve"]
            if any(keyword in (subject + body).lower() for keyword in action_keywords):
                action_required = True

            # サマリー生成（簡易版）
            summary = subject[:100] if subject else body[:100]

            # データベースに保存
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO email_analysis
                (email_id, sender, subject, priority, category, action_required, summary)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                email_data.get("id", ""),
                sender,
                subject,
                priority,
                category,
                action_required,
                summary
            ))

            conn.commit()
            conn.close()

            result = {
                "priority": priority,
                "category": category,
                "action_required": action_required,
                "summary": summary
            }

            # 学習系・記憶系に記録
            if LEARNING_INTEGRATION_AVAILABLE and secretary_learning:
                try:
                    secretary_learning.log_email_analysis(email_data, result)
                except Exception as e:
                    logger.warning(f"学習系記録エラー: {e}")

            logger.info(f"メール分析完了: {subject[:50]}")
            return result

        except Exception as e:
            logger.error(f"メール分析エラー: {e}")
            return {}

    # === カレンダー自動予定追加 ===

    def parse_calendar_event(self, text: str) -> Dict[str, Any]:
        """自然言語からカレンダー予定を解析（新機能）"""
        try:
            # 日時検出
            now = datetime.now()
            start_time = None

            # 相対日時パターン
            date_patterns = [
                (r'今日\s*(\d{1,2})時', 0, None),
                (r'明日\s*(\d{1,2})時', 1, None),
                (r'(\d+)月(\d+)日\s*(\d{1,2})時', None, None),
            ]

            for pattern, days_offset, _ in date_patterns:
                match = re.search(pattern, text)
                if match:
                    if days_offset is not None:
                        # 相対日時
                        hour = int(match.group(1))
                        start_time = (now + timedelta(days=days_offset)).replace(
                            hour=hour, minute=0, second=0, microsecond=0
                        )
                    else:
                        # 絶対日時
                        if len(match.groups()) == 3:
                            month, day, hour = match.groups()
                            start_time = now.replace(
                                month=int(month), day=int(day),
                                hour=int(hour), minute=0, second=0, microsecond=0
                            )
                    break

            # デフォルトは明日10時
            if not start_time:
                start_time = (now + timedelta(days=1)).replace(hour=10, minute=0)

            # 終了時間（デフォルトは1時間後）
            end_time = start_time + timedelta(hours=1)

            # タイトル抽出
            title = text[:100]

            # 場所検出
            location = None
            location_keywords = ["at", "で", "にて", "場所:"]
            for keyword in location_keywords:
                if keyword in text:
                    location_match = re.search(f'{keyword}\\s*([^、。，.]+)', text)
                    if location_match:
                        location = location_match.group(1).strip()
                        break

            return {
                "title": title,
                "description": text,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "location": location,
                "auto_created": True
            }

        except Exception as e:
            logger.error(f"カレンダー予定解析エラー: {e}")
            return {}

    def create_calendar_event(self, text: str, source: str = "manual") -> Dict[str, Any]:
        """カレンダー予定作成（新機能）"""
        try:
            event_data = self.parse_calendar_event(text)
            if not event_data:
                return {"success": False, "error": "Failed to parse event"}

            event_data["source"] = source

            # データベースに保存
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            event_id = f"event_{int(datetime.now().timestamp())}"
            cursor.execute('''
                INSERT INTO calendar_events
                (event_id, title, description, start_time, end_time, location, auto_created, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                event_id,
                event_data["title"],
                event_data["description"],
                event_data["start_time"],
                event_data["end_time"],
                event_data.get("location"),
                event_data.get("auto_created", False),
                source
            ))

            conn.commit()
            conn.close()

            # 学習系・記憶系に記録
            if LEARNING_INTEGRATION_AVAILABLE and secretary_learning:
                try:
                    secretary_learning.log_calendar_event(event_data)
                except Exception as e:
                    logger.warning(f"学習系記録エラー: {e}")

            logger.info(f"カレンダー予定作成: {event_id} - {event_data['title']}")
            return {"success": True, "event_id": event_id, "event": event_data}

        except Exception as e:
            logger.error(f"カレンダー予定作成エラー: {e}")
            return {"success": False, "error": str(e)}

    # === 定期レポート自動生成 ===

    def generate_daily_report(self) -> Dict[str, Any]:
        """デイリーレポート生成（新機能）"""
        try:
            now = datetime.now()
            today = now.strftime("%Y-%m-%d")

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 今日のタスク統計
            cursor.execute('''
                SELECT COUNT(*),
                       SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END)
                FROM smart_tasks
                WHERE DATE(created_at) = ?
            ''', (today,))
            task_total, task_completed = cursor.fetchone()

            # 今日のメール統計
            cursor.execute('''
                SELECT COUNT(*),
                       SUM(CASE WHEN priority = 'high' THEN 1 ELSE 0 END),
                       SUM(CASE WHEN action_required = 1 THEN 1 ELSE 0 END)
                FROM email_analysis
                WHERE DATE(analyzed_at) = ?
            ''', (today,))
            email_total, email_high, email_action = cursor.fetchone()

            # 今日の予定
            cursor.execute('''
                SELECT COUNT(*) FROM calendar_events
                WHERE DATE(start_time) = ?
            ''', (today,))
            events_count = cursor.fetchone()[0]

            report_data = {
                "date": today,
                "tasks": {
                    "total": task_total or 0,
                    "completed": task_completed or 0,
                    "completion_rate": round((task_completed or 0) / (task_total or 1) * 100, 1)
                },
                "emails": {
                    "total": email_total or 0,
                    "high_priority": email_high or 0,
                    "action_required": email_action or 0
                },
                "events": {
                    "count": events_count or 0
                }
            }

            # サマリー生成
            summary = f"""
            📊 デイリーレポート - {today}

            ✅ タスク: {report_data['tasks']['completed']}/{report_data['tasks']['total']} 完了 ({report_data['tasks']['completion_rate']}%)
            📧 メール: {report_data['emails']['total']}件 (優先: {report_data['emails']['high_priority']}件)
            📅 予定: {report_data['events']['count']}件
            """.strip()

            # データベースに保存
            cursor.execute('''
                INSERT INTO reports (report_type, period, data, summary)
                VALUES (?, ?, ?, ?)
            ''', ("daily", today, json.dumps(report_data), summary))

            conn.commit()
            conn.close()

            # 学習系・記憶系に記録
            if LEARNING_INTEGRATION_AVAILABLE and secretary_learning:
                try:
                    secretary_learning.log_report_generation({
                        "report_type": "daily",
                        "period": today,
                        **report_data
                    })
                except Exception as e:
                    logger.warning(f"学習系記録エラー: {e}")

            logger.info(f"デイリーレポート生成: {today}")
            return {"success": True, "report": report_data, "summary": summary}

        except Exception as e:
            logger.error(f"デイリーレポート生成エラー: {e}")
            return {"success": False, "error": str(e)}

    def get_recent_reports(self, report_type: str = "daily", limit: int = 7) -> List[Dict[str, Any]]:
        """最近のレポート取得"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT * FROM reports
                WHERE report_type = ?
                ORDER BY generated_at DESC
                LIMIT ?
            ''', (report_type, limit))

            columns = [desc[0] for desc in cursor.description]
            reports = []
            for row in cursor.fetchall():
                report = dict(zip(columns, row))
                report["data"] = json.loads(report["data"]) if report.get("data") else {}
                reports.append(report)

            conn.close()
            return reports

        except Exception as e:
            logger.error(f"レポート取得エラー: {e}")
            return []

    # === バックグラウンドタスク ===

    def start_background_tasks(self):
        """バックグラウンドタスク開始"""
        def background_worker():
            while True:
                try:
                    now = datetime.now()

                    # デイリーレポート生成（毎日9時）
                    if (now.hour == 9 and now.minute == 0 and
                        self.config["auto_generate_reports"]):
                        self.generate_daily_report()
                        logger.info("自動デイリーレポート生成")

                    # 60秒待機
                    asyncio.run(asyncio.sleep(60))

                except Exception as e:
                    logger.error(f"バックグラウンドタスクエラー: {e}")
                    asyncio.run(asyncio.sleep(60))

        thread = threading.Thread(target=background_worker, daemon=True)
        thread.start()
        logger.info("バックグラウンドタスク開始")

    # === API ルート ===

    def setup_routes(self):
        """APIルート設定"""

        @self.app.get("/")
        def index():
            return HTMLResponse("""
            <html>
                <head><title>Trinity Secretary Enhanced</title></head>
                <body>
                    <h1>🤖 Trinity Secretary Enhanced</h1>
                    <p>AI駆動の拡張秘書システム</p>
                    <ul>
                        <li><a href="/api/status">ステータス</a></li>
                        <li><a href="/api/tasks">タスク一覧</a></li>
                        <li><a href="/api/reports/daily">デイリーレポート</a></li>
                    </ul>
                </body>
            </html>
            """)

        @self.app.get("/api/status")
        def get_status():
            return JSONResponse({
                "service": "Trinity Secretary Enhanced",
                "version": "2.0.0",
                "status": "online",
                "features": [
                    "AI駆動タスク管理",
                    "スマートメール分析",
                    "自動カレンダー予定",
                    "定期レポート生成"
                ],
                "config": self.config
            })

        @self.app.post("/api/task/create")
        async def create_task(data: dict):
            text = data.get("text", "")
            source = data.get("source", "manual")
            result = self.create_smart_task(text, source)
            return JSONResponse(result)

        @self.app.get("/api/tasks")
        def get_tasks():
            tasks = self.get_tasks_by_priority()
            return JSONResponse({"tasks": tasks})

        @self.app.post("/api/email/analyze")
        async def analyze_email(data: dict):
            result = self.analyze_email(data)
            return JSONResponse(result)

        @self.app.post("/api/calendar/create")
        async def create_event(data: dict):
            text = data.get("text", "")
            source = data.get("source", "manual")
            result = self.create_calendar_event(text, source)
            return JSONResponse(result)

        @self.app.get("/api/reports/daily")
        def get_daily_reports():
            reports = self.get_recent_reports("daily")
            return JSONResponse({"reports": reports})

        @self.app.post("/api/report/generate")
        async def generate_report():
            result = self.generate_daily_report()
            return JSONResponse(result)

def main():
    logger.info("🤖 Trinity Secretary Enhanced 起動")
    secretary = TrinitySecretaryEnhanced()
    port = int(os.getenv("TRINITY_SECRETARY_PORT", "5013"))
    uvicorn.run(secretary.app, host="0.0.0.0", port=port, log_level="info")

if __name__ == "__main__":
    main()


