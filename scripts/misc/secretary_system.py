#!/usr/bin/env python3
"""
📋 ManaOS 秘書システム
スケジュール管理・リマインダー・自動報告
"""

import os
import json
import httpx
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3

# 統一モジュールのインポート
from manaos_logger import get_logger, get_service_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from manaos_timeout_config import get_timeout_config
from manaos_config_validator import ConfigValidator

from _paths import ORCHESTRATOR_PORT

# ロガーの初期化
logger = get_service_logger("secretary-system")

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("SecretarySystem")

# タイムアウト設定の取得
timeout_config = get_timeout_config()

# 設定ファイル検証の初期化
config_validator = ConfigValidator("SecretarySystem")

DEFAULT_ORCHESTRATOR_URL = f"http://127.0.0.1:{ORCHESTRATOR_PORT}"


class ReminderType(str, Enum):
    """リマインダータイプ"""
    ONCE = "once"  # 1回のみ
    DAILY = "daily"  # 毎日
    WEEKLY = "weekly"  # 毎週
    MONTHLY = "monthly"  # 毎月
    CUSTOM = "custom"  # カスタム


@dataclass
class Reminder:
    """リマインダー"""
    reminder_id: str
    title: str
    description: str
    scheduled_time: str  # ISO形式
    reminder_type: ReminderType
    enabled: bool = True
    completed: bool = False
    completed_at: Optional[str] = None
    created_at: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


@dataclass
class Report:
    """報告"""
    report_id: str
    report_type: str  # "daily", "weekly", "monthly", "custom"
    title: str
    content: str
    generated_at: str
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class SecretarySystem:
    """秘書システム"""
    
    def __init__(
        self,
        orchestrator_url: Optional[str] = None,
        db_path: Optional[Path] = None,
        config_path: Optional[Path] = None
    ):
        """
        初期化
        
        Args:
            orchestrator_url: Unified Orchestrator API URL
            db_path: データベースパス
            config_path: 設定ファイルのパス
        """
        self.orchestrator_url = orchestrator_url or DEFAULT_ORCHESTRATOR_URL
        
        self.config_path = config_path or Path(__file__).parent / "secretary_config.json"
        self.config = self._load_config()
        
        # データベース初期化
        self.db_path = db_path or Path(__file__).parent / "secretary_system.db"
        self._init_database()
        
        logger.info(f"✅ Secretary System初期化完了")
    
    def _load_config(self) -> Dict[str, Any]:
        """設定を読み込む"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # 設定ファイルの検証
                schema = {
                    "required": [],
                    "fields": {
                        "auto_report_enabled": {"type": bool, "default": True},
                        "report_schedule": {"type": str, "default": "daily"},
                        "reminder_check_interval_seconds": {"type": int, "default": 60}
                    }
                }
                
                is_valid, errors = config_validator.validate_config(config, schema, self.config_path)
                if not is_valid:
                    logger.warning(f"設定ファイル検証エラー: {errors}")
                    # エラーがあってもデフォルト設定にマージして続行
                    default_config = self._get_default_config()
                    default_config.update(config)
                    return default_config
                
                return config
            except Exception as e:
                error = error_handler.handle_exception(
                    e,
                    context={"config_file": str(self.config_path)},
                    user_message="設定ファイルの読み込みに失敗しました"
                )
                logger.warning(f"設定読み込みエラー: {error.message}")
        
        return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """デフォルト設定"""
        return {
            "auto_report_enabled": True,
            "report_schedule": "daily",
            "reminder_check_interval_seconds": 60
        }
    
    def _init_database(self):
        """データベースを初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # リマインダーテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                reminder_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                scheduled_time TEXT NOT NULL,
                reminder_type TEXT NOT NULL,
                enabled INTEGER DEFAULT 1,
                completed INTEGER DEFAULT 0,
                completed_at TEXT,
                created_at TEXT NOT NULL
            )
        """)
        
        # 報告テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                report_id TEXT PRIMARY KEY,
                report_type TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                generated_at TEXT NOT NULL,
                metadata TEXT
            )
        """)
        
        # インデックス作成
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_scheduled_time ON reminders(scheduled_time)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_enabled ON reminders(enabled)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_generated_at ON reports(generated_at DESC)")
        
        conn.commit()
        conn.close()
        logger.info(f"✅ データベース初期化完了: {self.db_path}")
    
    def add_reminder(self, reminder: Reminder) -> Reminder:
        """
        リマインダーを追加
        
        Args:
            reminder: リマインダー
        
        Returns:
            追加されたリマインダー
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO reminders 
            (reminder_id, title, description, scheduled_time, reminder_type, enabled, completed, completed_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            reminder.reminder_id,
            reminder.title,
            reminder.description,
            reminder.scheduled_time,
            reminder.reminder_type.value,
            1 if reminder.enabled else 0,
            1 if reminder.completed else 0,
            reminder.completed_at,
            reminder.created_at
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ リマインダー追加: {reminder.reminder_id}")
        return reminder
    
    def get_due_reminders(self) -> List[Reminder]:
        """
        期限が来たリマインダーを取得
        
        Returns:
            期限が来たリマインダーのリスト
        """
        now = datetime.now()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM reminders
            WHERE enabled = 1 AND completed = 0
            AND scheduled_time <= ?
            ORDER BY scheduled_time ASC
        """, (now.isoformat(),))
        
        reminders = []
        for row in cursor.fetchall():
            reminder = Reminder(
                reminder_id=row[0],
                title=row[1],
                description=row[2] or "",
                scheduled_time=row[3],
                reminder_type=ReminderType(row[4]),
                enabled=bool(row[5]),
                completed=bool(row[6]),
                completed_at=row[7],
                created_at=row[8]
            )
            reminders.append(reminder)
        
        conn.close()
        return reminders
    
    @staticmethod
    def _next_scheduled_time(scheduled_time: str, reminder_type: ReminderType) -> Optional[str]:
        """
        繰り返しリマインダーの次回予定時刻を計算する。
        ONCE / CUSTOM の場合は None を返す。
        """
        if reminder_type not in (ReminderType.DAILY, ReminderType.WEEKLY, ReminderType.MONTHLY):
            return None
        try:
            base = datetime.fromisoformat(scheduled_time)
        except Exception:
            base = datetime.now()
        if reminder_type == ReminderType.DAILY:
            next_dt = base + timedelta(days=1)
        elif reminder_type == ReminderType.WEEKLY:
            next_dt = base + timedelta(weeks=1)
        else:  # MONTHLY
            # 30日後（年月をまたぐ場合も安全）
            year = base.year + (base.month // 12)
            month = (base.month % 12) + 1
            try:
                import calendar
                last_day = calendar.monthrange(year, month)[1]
                day = min(base.day, last_day)
                next_dt = base.replace(year=year, month=month, day=day)
            except Exception:
                next_dt = base + timedelta(days=30)
        return next_dt.isoformat()

    def complete_reminder(self, reminder_id: str):
        """
        リマインダーを完了する。
        - ONCE / CUSTOM: completed フラグを立てる（従来動作）
        - DAILY / WEEKLY / MONTHLY: 次回予定時刻に再スケジュールし、
          completed は立てない（繰り返し継続）
        
        Args:
            reminder_id: リマインダーID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 現在のリマインダー情報を取得
        cursor.execute(
            "SELECT reminder_type, scheduled_time FROM reminders WHERE reminder_id = ?",
            (reminder_id,),
        )
        row = cursor.fetchone()

        if row:
            try:
                rtype = ReminderType(row[0])
            except ValueError:
                rtype = ReminderType.ONCE
            scheduled_time = row[1]
            next_time = self._next_scheduled_time(scheduled_time, rtype)

            if next_time is not None:
                # 繰り返しリマインダー → 再スケジュール
                cursor.execute(
                    """UPDATE reminders
                       SET scheduled_time = ?, completed = 0, completed_at = NULL
                       WHERE reminder_id = ?""",
                    (next_time, reminder_id),
                )
                conn.commit()
                conn.close()
                logger.info(f"🔄 リマインダー再スケジュール: {reminder_id} → {next_time}")
                return

        # ONCE / CUSTOM または行が存在しない → 完了にする
        cursor.execute(
            """UPDATE reminders
               SET completed = 1, completed_at = ?
               WHERE reminder_id = ?""",
            (datetime.now().isoformat(), reminder_id),
        )
        conn.commit()
        conn.close()
        logger.info(f"✅ リマインダー完了: {reminder_id}")
    
    def generate_daily_report(self) -> Report:
        """
        日次報告を生成
        
        Returns:
            日次報告
        """
        try:
            # Unified Orchestrator経由でシステム状態を取得
            timeout = timeout_config.get("api_call", 10.0)
            response = httpx.get(
                f"{self.orchestrator_url}/api/history",
                params={"limit": 10},
                timeout=timeout
            )
            
            execution_history = []
            if response.status_code == 200:
                execution_history = response.json().get("results", [])
            
            # 報告内容を生成
            report_content = self._format_daily_report(execution_history)
            
            report = Report(
                report_id=f"report_{datetime.now().strftime('%Y%m%d')}",
                report_type="daily",
                title=f"日次報告 - {datetime.now().strftime('%Y年%m月%d日')}",
                content=report_content,
                generated_at=datetime.now().isoformat(),
                metadata={
                    "execution_count": len(execution_history),
                    "date": datetime.now().strftime('%Y-%m-%d')
                }
            )
            
            # データベースに保存
            self._save_report(report)
            
            logger.info(f"✅ 日次報告生成完了: {report.report_id}")
            return report
        
        except Exception as e:
            error = error_handler.handle_exception(
                e,
                context={"report_type": "daily"},
                user_message="日次報告の生成に失敗しました"
            )
            logger.error(f"日次報告生成エラー: {error.message}")
            
            # エラー時も空の報告を返す
            return Report(
                report_id=f"report_{datetime.now().strftime('%Y%m%d')}",
                report_type="daily",
                title=f"日次報告 - {datetime.now().strftime('%Y年%m月%d日')}",
                content="報告の生成中にエラーが発生しました。",
                generated_at=datetime.now().isoformat()
            )
    
    def _format_daily_report(self, execution_history: List[Dict[str, Any]]) -> str:
        """
        日次報告をフォーマット
        
        Args:
            execution_history: 実行履歴
        
        Returns:
            フォーマットされた報告内容
        """
        report_lines = [
            f"# 日次報告 - {datetime.now().strftime('%Y年%m月%d日')}",
            "",
            "## 実行サマリー",
            f"- 実行回数: {len(execution_history)}回",
            ""
        ]
        
        if execution_history:
            report_lines.append("## 最近の実行")
            for i, execution in enumerate(execution_history[:5], 1):
                status = execution.get("status", "unknown")
                intent_type = execution.get("intent_type", "unknown")
                report_lines.append(f"{i}. {intent_type} - {status}")
        
        report_lines.extend([
            "",
            "## 備考",
            "詳細はUnified Orchestratorの実行履歴を参照してください。"
        ])
        
        return "\n".join(report_lines)
    
    def _save_report(self, report: Report):
        """報告を保存"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO reports
            (report_id, report_type, title, content, generated_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            report.report_id,
            report.report_type,
            report.title,
            report.content,
            report.generated_at,
            json.dumps(report.metadata, ensure_ascii=False) if report.metadata else None
        ))
        
        conn.commit()
        conn.close()
    
    def get_reports(self, report_type: Optional[str] = None, limit: int = 10) -> List[Report]:
        """
        報告一覧を取得
        
        Args:
            report_type: 報告タイプ（フィルタ）
            limit: 取得件数
        
        Returns:
            報告のリスト
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if report_type:
            cursor.execute("""
                SELECT * FROM reports
                WHERE report_type = ?
                ORDER BY generated_at DESC
                LIMIT ?
            """, (report_type, limit))
        else:
            cursor.execute("""
                SELECT * FROM reports
                ORDER BY generated_at DESC
                LIMIT ?
            """, (limit,))
        
        reports = []
        for row in cursor.fetchall():
            report = Report(
                report_id=row[0],
                report_type=row[1],
                title=row[2],
                content=row[3],
                generated_at=row[4],
                metadata=json.loads(row[5]) if row[5] else {}
            )
            reports.append(report)
        
        conn.close()
        return reports


# Flask APIサーバー
app = Flask(__name__)
CORS(app)

# グローバル秘書システムインスタンス
secretary_system = None

def init_secretary_system():
    """秘書システムを初期化"""
    global secretary_system
    if secretary_system is None:
        secretary_system = SecretarySystem()
    return secretary_system

@app.route('/health', methods=['GET'])
def health():
    """ヘルスチェック"""
    return jsonify({"status": "healthy", "service": "Secretary System"})

@app.route('/api/reminders', methods=['GET'])
def get_reminders():
    """リマインダー一覧を取得"""
    try:
        system = init_secretary_system()
        due_reminders = system.get_due_reminders()
        return jsonify({
            "reminders": [asdict(r) for r in due_reminders],
            "count": len(due_reminders)
        })
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/reminders"},
            user_message="リマインダー一覧の取得に失敗しました"
        )
        return jsonify(error.to_json_response()), 500

@app.route('/api/reminders', methods=['POST'])
def add_reminder():
    """リマインダーを追加"""
    try:
        data = request.get_json() or {}
        
        reminder = Reminder(
            reminder_id=data.get("reminder_id", f"reminder_{datetime.now().strftime('%Y%m%d_%H%M%S')}"),
            title=data.get("title", ""),
            description=data.get("description", ""),
            scheduled_time=data.get("scheduled_time", datetime.now().isoformat()),
            reminder_type=ReminderType(data.get("reminder_type", "once")),
            enabled=data.get("enabled", True)
        )
        
        if not reminder.title:
            error = error_handler.handle_exception(
                ValueError("title is required"),
                context={"endpoint": "/api/reminders"},
                user_message="タイトルが必要です"
            )
            return jsonify(error.to_json_response()), 400
        
        system = init_secretary_system()
        added_reminder = system.add_reminder(reminder)
        
        return jsonify(asdict(added_reminder))
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/reminders"},
            user_message="リマインダーの追加に失敗しました"
        )
        return jsonify(error.to_json_response()), 500

@app.route('/api/reminders/<reminder_id>/complete', methods=['POST'])
def complete_reminder(reminder_id: str):
    """リマインダーを完了"""
    try:
        system = init_secretary_system()
        system.complete_reminder(reminder_id)
        return jsonify({"status": "completed", "reminder_id": reminder_id})
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/reminders/<reminder_id>/complete", "reminder_id": reminder_id},
            user_message="リマインダーの完了処理に失敗しました"
        )
        return jsonify(error.to_json_response()), 500

@app.route('/api/reports/daily', methods=['POST'])
def generate_daily_report():
    """日次報告を生成"""
    try:
        system = init_secretary_system()
        report = system.generate_daily_report()
        return jsonify(asdict(report))
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/reports/daily"},
            user_message="日次報告の生成に失敗しました"
        )
        return jsonify(error.to_json_response()), 500

@app.route('/api/reports', methods=['GET'])
def get_reports():
    """報告一覧を取得"""
    try:
        report_type = request.args.get("type")
        limit = request.args.get("limit", 10, type=int)
        
        system = init_secretary_system()
        reports = system.get_reports(report_type, limit)
        
        return jsonify({
            "reports": [asdict(r) for r in reports],
            "count": len(reports)
        })
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/reports"},
            user_message="報告一覧の取得に失敗しました"
        )
        return jsonify(error.to_json_response()), 500


if __name__ == '__main__':
    port = int(os.getenv("PORT", 5125))
    logger.info(f"📋 Secretary System起動中... (ポート: {port})")
    init_secretary_system()
    app.run(host='0.0.0.0', port=port, debug=os.getenv("DEBUG", "False").lower() == "true")

