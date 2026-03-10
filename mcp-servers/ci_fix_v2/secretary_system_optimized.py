#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📋 ManaOS 秘書システム（最適化版）
データベース接続プールとキャッシュシステムを使用
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

# 統一モジュールのインポート
from manaos_logger import get_logger, get_service_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from manaos_timeout_config import get_timeout_config
from manaos_config_validator import ConfigValidator

# 最適化モジュールのインポート
from database_connection_pool import get_pool
from unified_cache_system import get_unified_cache
from config_cache import get_config_cache

# ロガーの初期化
logger = get_service_logger("secretary-system-optimized")

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("SecretarySystem")

# タイムアウト設定の取得
timeout_config = get_timeout_config()

# 設定ファイル検証の初期化
config_validator = ConfigValidator("SecretarySystem")

# キャッシュシステムの取得
cache_system = get_unified_cache()
config_cache = get_config_cache()


class ReminderType(str, Enum):
    """リマインダータイプ"""
    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"


@dataclass
class Reminder:
    """リマインダー"""
    reminder_id: str
    title: str
    description: str
    scheduled_time: str
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
    report_type: str
    title: str
    content: str
    generated_at: str
    metadata: Dict[str, Any] = None  # type: ignore
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class SecretarySystemOptimized:
    """秘書システム（最適化版）"""
    
    def __init__(
        self,
        orchestrator_url: str = "http://127.0.0.1:5106",
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
        self.orchestrator_url = orchestrator_url
        
        self.config_path = config_path or Path(__file__).parent / "secretary_config.json"
        self.config = self._load_config()
        
        # データベース初期化（接続プール使用）
        self.db_path = db_path or Path(__file__).parent / "secretary_system.db"
        self.db_pool = get_pool(str(self.db_path), max_connections=10)
        self._init_database()
        
        logger.info(f"✅ Secretary System（最適化版）初期化完了")
    
    def _load_config(self) -> Dict[str, Any]:
        """設定を読み込む（キャッシュ使用）"""
        return config_cache.get_config(
            str(self.config_path),
            default=self._get_default_config()
        )
    
    def _get_default_config(self) -> Dict[str, Any]:
        """デフォルト設定"""
        return {
            "auto_report_enabled": True,
            "report_schedule": "daily",
            "reminder_check_interval_seconds": 60
        }
    
    def _init_database(self):
        """データベースを初期化（接続プール使用）"""
        with self.db_pool.get_connection() as conn:
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
        
        logger.info(f"✅ データベース初期化完了: {self.db_path}")
    
    def add_reminder(self, reminder: Reminder) -> Reminder:
        """
        リマインダーを追加（最適化版）
        
        Args:
            reminder: リマインダー
        
        Returns:
            追加されたリマインダー
        """
        with self.db_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO reminders (
                    reminder_id, title, description, scheduled_time,
                    reminder_type, enabled, completed, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                reminder.reminder_id,
                reminder.title,
                reminder.description,
                reminder.scheduled_time,
                reminder.reminder_type.value,
                1 if reminder.enabled else 0,
                0,
                reminder.created_at
            ))
            conn.commit()
        
        # キャッシュを無効化
        cache_system.clear("reminders")
        
        logger.info(f"✅ リマインダー追加: {reminder.reminder_id}")
        return reminder
    
    def get_pending_reminders(self, limit: int = 10) -> List[Reminder]:
        """
        保留中のリマインダーを取得（最適化版）
        
        Args:
            limit: 最大件数
        
        Returns:
            リマインダーのリスト
        """
        # キャッシュから取得
        cache_key = f"pending_reminders:{limit}"
        cached = cache_system.get("reminders", cache_key=cache_key)
        if cached:
            return [Reminder(**r) for r in cached]
        
        now = datetime.now().isoformat()
        
        with self.db_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM reminders
                WHERE enabled = 1 AND completed = 0 AND scheduled_time <= ?
                ORDER BY scheduled_time ASC
                LIMIT ?
            """, (now, limit))
            
            reminders = []
            for row in cursor.fetchall():
                reminders.append(Reminder(
                    reminder_id=row[0],
                    title=row[1],
                    description=row[2] or "",
                    scheduled_time=row[3],
                    reminder_type=ReminderType(row[4]),
                    enabled=bool(row[5]),
                    completed=bool(row[6]),
                    completed_at=row[7],
                    created_at=row[8]
                ))
        
        # キャッシュに保存
        cache_system.set("reminders", [asdict(r) for r in reminders], cache_key=cache_key, ttl_seconds=60)
        
        return reminders
    
    def add_report(self, report: Report) -> Report:
        """
        報告を追加（最適化版）
        
        Args:
            report: 報告
        
        Returns:
            追加された報告
        """
        with self.db_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO reports (
                    report_id, report_type, title, content, generated_at, metadata
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                report.report_id,
                report.report_type,
                report.title,
                report.content,
                report.generated_at,
                json.dumps(report.metadata or {})
            ))
            conn.commit()
        
        # キャッシュを無効化
        cache_system.clear("reports")
        
        logger.info(f"✅ 報告追加: {report.report_id}")
        return report
    
    def get_recent_reports(self, report_type: Optional[str] = None, limit: int = 10) -> List[Report]:
        """
        最近の報告を取得（最適化版）
        
        Args:
            report_type: 報告タイプ（Noneの場合はすべて）
            limit: 最大件数
        
        Returns:
            報告のリスト
        """
        # キャッシュから取得
        cache_key = f"recent_reports:{report_type}:{limit}"
        cached = cache_system.get("reports", cache_key=cache_key)
        if cached:
            return [Report(**r) for r in cached]
        
        with self.db_pool.get_connection() as conn:
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
                reports.append(Report(
                    report_id=row[0],
                    report_type=row[1],
                    title=row[2],
                    content=row[3],
                    generated_at=row[4],
                    metadata=json.loads(row[5] or "{}")
                ))
        
        # キャッシュに保存
        cache_system.set("reports", [asdict(r) for r in reports], cache_key=cache_key, ttl_seconds=300)
        
        return reports


def main():
    """テスト用メイン関数"""
    print("秘書システム（最適化版）テスト")
    print("=" * 60)
    
    secretary = SecretarySystemOptimized()
    
    # リマインダーを追加
    reminder = Reminder(
        reminder_id="test_1",
        title="テストリマインダー",
        description="テスト用",
        scheduled_time=datetime.now().isoformat(),
        reminder_type=ReminderType.ONCE
    )
    secretary.add_reminder(reminder)
    
    # 保留中のリマインダーを取得
    pending = secretary.get_pending_reminders()
    print(f"保留中のリマインダー: {len(pending)}件")


if __name__ == "__main__":
    main()






















