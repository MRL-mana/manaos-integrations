#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📊 File Secretary - Sheets集計（週報生成）
Rows統合を使用して週報を自動生成
"""

import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from manaos_logger import get_logger, get_service_logger
from file_secretary_db import FileSecretaryDB
from file_secretary_schemas import FileStatus, FileType

logger = get_service_logger("file-secretary-sheets")

# Rows統合をインポート
try:
    from rows_integration import RowsIntegration
    ROWS_AVAILABLE = True
except ImportError:
    ROWS_AVAILABLE = False
    logger.warning("Rows統合モジュールが見つかりません")


class FileSecretarySheets:
    """ファイル秘書Sheets集計"""
    
    def __init__(self, db: FileSecretaryDB, spreadsheet_id: Optional[str] = None):
        """
        初期化
        
        Args:
            db: FileSecretaryDBインスタンス
            spreadsheet_id: RowsスプレッドシートID（Noneの場合は環境変数から取得）
        """
        self.db = db
        self.spreadsheet_id = spreadsheet_id or os.getenv("FILE_SECRETARY_SPREADSHEET_ID")
        self.rows_integration = None
        
        if ROWS_AVAILABLE:
            try:
                api_key = os.getenv("ROWS_API_KEY")
                if api_key:
                    self.rows_integration = RowsIntegration(api_key=api_key)
                    if self.rows_integration.is_available():
                        logger.info("✅ Rows統合初期化完了")
                    else:
                        logger.warning("⚠️ Rows統合が利用できません")
                else:
                    logger.warning("⚠️ ROWS_API_KEYが設定されていません")
            except Exception as e:
                logger.error(f"❌ Rows統合初期化エラー: {e}")
    
    def generate_weekly_report(self, week_start: Optional[datetime] = None) -> Dict[str, Any]:
        """
        週報を生成
        
        Args:
            week_start: 週の開始日（Noneの場合は今週）
            
        Returns:
            週報データ
        """
        if not week_start:
            # 今週の月曜日を計算
            today = datetime.now()
            days_since_monday = today.weekday()
            week_start = today - timedelta(days=days_since_monday)
            week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        
        week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
        
        # 週間のファイル統計を取得
        stats = self._get_weekly_stats(week_start, week_end)
        
        # 週報データを作成
        report_data = {
            "週開始日": week_start.strftime("%Y-%m-%d"),
            "週終了日": week_end.strftime("%Y-%m-%d"),
            "新規ファイル数": stats["new_count"],
            "整理済みファイル数": stats["organized_count"],
            "PDF数": stats["by_type"].get("pdf", 0),
            "画像数": stats["by_type"].get("image", 0),
            "Excel数": stats["by_type"].get("xlsx", 0),
            "その他": stats["by_type"].get("other", 0),
            "日報タグ数": stats["tag_counts"].get("日報", 0),
            "クーポンタグ数": stats["tag_counts"].get("クーポン", 0),
            "生成日時": datetime.now().isoformat()
        }
        
        # Rowsに送信
        if self.rows_integration and self.spreadsheet_id:
            try:
                result = self.rows_integration.send_to_rows(
                    spreadsheet_id=self.spreadsheet_id,
                    data=report_data,
                    sheet_name="週報",
                    append=True
                )
                logger.info(f"✅ 週報をRowsに送信: {week_start.strftime('%Y-%m-%d')}")
                report_data["rows_result"] = result
            except Exception as e:
                logger.error(f"❌ 週報送信エラー: {e}")
                report_data["rows_error"] = str(e)
        
        return report_data
    
    def _get_weekly_stats(self, week_start: datetime, week_end: datetime) -> Dict[str, Any]:
        """
        週間統計を取得
        
        Args:
            week_start: 週の開始日時
            week_end: 週の終了日時
            
        Returns:
            統計データ
        """
        # データベースから該当期間のファイルを取得
        # 簡易版：全ファイルを取得してフィルタリング
        all_files = self.db.get_files_by_status(FileStatus.ARCHIVED, limit=1000)
        
        new_count = 0
        organized_count = 0
        by_type = {}
        tag_counts = {}
        
        week_start_iso = week_start.isoformat()
        week_end_iso = week_end.isoformat()
        
        for file_record in all_files:
            # 週内かチェック
            if week_start_iso <= file_record.created_at <= week_end_iso:
                new_count += 1
            
            # 整理済みかチェック（archivedステータス）
            if file_record.status == FileStatus.ARCHIVED:
                # 監査ログから整理日時を確認
                for log_entry in file_record.audit_log:
                    if log_entry.action.value == "archived":
                        log_time = datetime.fromisoformat(log_entry.timestamp.replace('Z', '+00:00'))
                        if week_start <= log_time.replace(tzinfo=None) <= week_end:
                            organized_count += 1
                            break
            
            # タイプ別カウント
            if file_record.type:
                type_name = file_record.type.value
                by_type[type_name] = by_type.get(type_name, 0) + 1
            
            # タグ別カウント
            for tag in file_record.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        return {
            "new_count": new_count,
            "organized_count": organized_count,
            "by_type": by_type,
            "tag_counts": tag_counts
        }
    
    def send_to_slack(self, report_data: Dict[str, Any]) -> bool:
        """
        週報をSlackに送信
        
        Args:
            report_data: 週報データ
            
        Returns:
            成功したかどうか
        """
        try:
            from slack_integration import send_to_slack
            
            report_text = f"""📊 週報 ({report_data['週開始日']} 〜 {report_data['週終了日']})

📁 ファイル統計:
・新規: {report_data['新規ファイル数']}件
・整理済み: {report_data['整理済みファイル数']}件

📄 種類別:
・PDF: {report_data['PDF数']}件
・画像: {report_data['画像数']}件
・Excel: {report_data['Excel数']}件
・その他: {report_data['その他']}件

🏷️ タグ別:
・日報: {report_data['日報タグ数']}件
・クーポン: {report_data['クーポンタグ数']}件
"""
            
            return send_to_slack(report_text)
        except Exception as e:
            logger.error(f"❌ Slack送信エラー: {e}")
            return False






















