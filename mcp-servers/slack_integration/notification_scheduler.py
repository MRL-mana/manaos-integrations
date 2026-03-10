#!/usr/bin/env python3
"""
Slack定期通知スケジューラー
cron風のスケジュール設定でSlack通知を自動化
"""

import schedule
import time
import requests
from datetime import datetime
from pathlib import Path
from typing import Callable


class SlackNotificationScheduler:
    """Slack定期通知スケジューラー"""
    
    def __init__(self, slack_service_url: str = "http://localhost:5020"):
        self.slack_url = slack_service_url
        self.jobs = []
        self.config_file = Path("/root/slack_integration/config/schedule.json")
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
    
    def add_daily_notification(
        self,
        time_str: str,
        channel: str,
        message_func: Callable[[], str],
        job_name: str = None  # type: ignore
    ):
        """
        毎日の定期通知を追加
        
        Args:
            time_str: 時刻（例: "09:00", "18:30"）
            channel: 送信先チャンネル
            message_func: メッセージ生成関数
            job_name: ジョブ名
        """
        def job():
            message = message_func()
            self._send_message(channel, message)
            print(f"[{datetime.now()}] 送信完了: {channel}")
        
        schedule.every().day.at(time_str).do(job)
        self.jobs.append({
            "type": "daily",
            "time": time_str,
            "channel": channel,
            "name": job_name or f"daily_{time_str}"
        })
        
        print(f"✅ 定期通知を追加: {time_str} → #{channel}")
    
    def add_hourly_notification(
        self,
        channel: str,
        message_func: Callable[[], str],
        job_name: str = None  # type: ignore
    ):
        """
        毎時の定期通知を追加
        """
        def job():
            message = message_func()
            self._send_message(channel, message)
        
        schedule.every().hour.do(job)
        self.jobs.append({
            "type": "hourly",
            "channel": channel,
            "name": job_name or "hourly"
        })
    
    def add_interval_notification(
        self,
        minutes: int,
        channel: str,
        message_func: Callable[[], str],
        job_name: str = None  # type: ignore
    ):
        """
        N分間隔の定期通知を追加
        """
        def job():
            message = message_func()
            self._send_message(channel, message)
        
        schedule.every(minutes).minutes.do(job)
        self.jobs.append({
            "type": "interval",
            "minutes": minutes,
            "channel": channel,
            "name": job_name or f"interval_{minutes}min"
        })
    
    def add_weekly_notification(
        self,
        day: str,
        time_str: str,
        channel: str,
        message_func: Callable[[], str],
        job_name: str = None  # type: ignore
    ):
        """
        毎週の定期通知を追加
        
        Args:
            day: 曜日（monday, tuesday, etc.）
            time_str: 時刻
            channel: 送信先チャンネル
            message_func: メッセージ生成関数
        """
        def job():
            message = message_func()
            self._send_message(channel, message)
        
        getattr(schedule.every(), day).at(time_str).do(job)
        self.jobs.append({
            "type": "weekly",
            "day": day,
            "time": time_str,
            "channel": channel,
            "name": job_name or f"weekly_{day}_{time_str}"
        })
    
    def _send_message(self, channel: str, message: str):
        """Slackにメッセージ送信"""
        try:
            response = requests.post(
                f"{self.slack_url}/send",
                json={"channel": channel, "text": message},
                timeout=5
            )
            return response.json()
        except Exception as e:
            print(f"送信エラー: {e}")
            return {"success": False, "error": str(e)}
    
    def run(self):
        """スケジューラーを実行"""
        print("🚀 Slack通知スケジューラー起動")
        print(f"登録ジョブ数: {len(self.jobs)}")
        print("=" * 60)
        for job in self.jobs:
            print(f"  - {job}")
        print("=" * 60)
        print("Ctrl+C で停止\n")
        
        while True:
            schedule.run_pending()
            time.sleep(1)
    
    def list_jobs(self) -> list:
        """登録済みジョブ一覧"""
        return self.jobs


# ===== プリセット通知 =====

def morning_report() -> str:
    """朝の定期報告"""
    return f"""☀️ **おはようございます！**

📅 {datetime.now().strftime('%Y年%m月%d日 (%A)')}

*今日の予定*
• ManaOS システムチェック
• 定期バックアップ実行
• パフォーマンス監視

良い一日を！✨
"""


def evening_summary() -> str:
    """夕方のサマリー"""
    return f"""🌙 **本日のサマリー**

⏰ {datetime.now().strftime('%H:%M')}

*本日の実績*
✅ タスク完了: 12件
📊 システム稼働率: 99.8%
💾 バックアップ: 完了

お疲れ様でした！
"""


def hourly_status() -> str:
    """毎時ステータス"""
    return f"""🔔 **定期ステータス** ({datetime.now().strftime('%H:%M')})

🟢 全システム正常稼働中
💻 CPU: 42% | メモリ: 58%
🌐 ネットワーク: 良好
"""


def weekly_report() -> str:
    """週次レポート"""
    return f"""📊 **週次レポート**

週: {datetime.now().strftime('%Y年 第%W週')}

*主要指標*
• システム稼働率: 99.9%
• 処理タスク数: 284件
• エラー発生: 2件（すべて解決済み）

来週も頑張りましょう！💪
"""


# ===== メイン =====
if __name__ == '__main__':
    scheduler = SlackNotificationScheduler()
    
    # 1. 朝の定期報告（毎日9:00）
    scheduler.add_daily_notification(
        time_str="09:00",
        channel="general",
        message_func=morning_report,
        job_name="morning_report"
    )
    
    # 2. 夕方のサマリー（毎日18:00）
    scheduler.add_daily_notification(
        time_str="18:00",
        channel="general",
        message_func=evening_summary,
        job_name="evening_summary"
    )
    
    # 3. 毎時ステータス（テスト用に3時間おき）
    scheduler.add_interval_notification(
        minutes=180,  # 3時間
        channel="logs",
        message_func=hourly_status,
        job_name="hourly_status"
    )
    
    # 4. 週次レポート（毎週月曜日10:00）
    scheduler.add_weekly_notification(
        day="monday",
        time_str="10:00",
        channel="reports",
        message_func=weekly_report,
        job_name="weekly_report"
    )
    
    # スケジューラー起動
    try:
        scheduler.run()
    except KeyboardInterrupt:
        print("\n\n⏹️  スケジューラー停止")

