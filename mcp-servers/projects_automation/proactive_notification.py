#!/usr/bin/env python3
"""
プロアクティブ通知システム
重要なイベントを自動検知して通知
"""

import time
from datetime import datetime
from pathlib import Path
import json

class ProactiveNotifier:
    def __init__(self):
        self.last_check = {}
        self.notification_log = Path("/root/logs/notifications.log")
        
    def log(self, message):
        """ログ出力"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] {message}"
        print(log_msg)
        
        with open(self.notification_log, 'a') as f:
            f.write(log_msg + "\n")
    
    def check_calendar_reminders(self):
        """カレンダーリマインダー（15分前）"""
        try:
            # 今から15分後のイベントをチェック
            # Google Calendar APIで実装
            
            upcoming = [
                {"time": "10:00", "title": "チーム会議", "minutes_until": 15}
            ]
            
            for event in upcoming:
                if event['minutes_until'] <= 15:
                    self.send_notification(
                        "📅 会議リマインダー",
                        f"{event['time']} {event['title']} まで{event['minutes_until']}分"
                    )
        except Exception as e:
            self.log(f"カレンダーチェックエラー: {e}")
    
    def check_important_emails(self):
        """重要メールチェック"""
        try:
            # Gmail APIで新着メールチェック
            # 前回チェックから5分以内の新着のみ
            
            new_important = [
                {"from": "上司", "subject": "緊急: 承認お願いします"}
            ]
            
            for email in new_important:
                self.send_notification(
                    "📧 重要メール受信",
                    f"差出人: {email['from']}\n件名: {email['subject']}"
                )
        except Exception as e:
            self.log(f"メールチェックエラー: {e}")
    
    def check_system_health(self):
        """システムヘルスチェック"""
        try:
            # CPU、メモリ、ディスクをチェック
            import psutil
            
            cpu = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory().percent
            disk = psutil.disk_usage('/').percent
            
            # 警告閾値
            if cpu > 80:
                self.send_notification("⚠️ CPU警告", f"CPU使用率が高い: {cpu}%")
            
            if memory > 85:
                self.send_notification("⚠️ メモリ警告", f"メモリ使用率が高い: {memory}%")
            
            if disk > 90:
                self.send_notification("⚠️ ディスク警告", f"ディスク使用率が高い: {disk}%")
                
        except Exception as e:
            self.log(f"システムチェックエラー: {e}")
    
    def check_task_deadlines(self):
        """タスク期限チェック"""
        try:
            # タスク管理システムから期限近いタスク取得
            
            approaching_deadlines = [
                {"task": "月次レポート提出", "deadline": "明日", "hours_left": 20}
            ]
            
            for task in approaching_deadlines:
                if task['hours_left'] <= 24:
                    self.send_notification(
                        "⏰ タスク期限警告",
                        f"{task['task']} - 残り{task['hours_left']}時間"
                    )
        except Exception as e:
            self.log(f"タスクチェックエラー: {e}")
    
    def send_notification(self, title, message):
        """通知送信"""
        self.log(f"🔔 通知: {title} - {message}")
        
        # 実際の通知（実装時に追加）
        # - デスクトップ通知
        # - LINE通知
        # - Slack通知
        
        # 簡易版: ファイルに保存
        notification_file = Path("/root/notifications.json")
        
        notifications = []
        if notification_file.exists():
            with open(notification_file, 'r') as f:
                notifications = json.load(f)
        
        notifications.append({
            "timestamp": datetime.now().isoformat(),
            "title": title,
            "message": message
        })
        
        # 最新100件のみ保持
        notifications = notifications[-100:]
        
        with open(notification_file, 'w') as f:
            json.dump(notifications, f, indent=2, ensure_ascii=False)
    
    def run_monitoring_loop(self, interval=300):
        """監視ループ（5分間隔）"""
        self.log("🚀 プロアクティブ通知システム起動")
        
        while True:
            try:
                self.log("🔍 チェック実行中...")
                
                self.check_calendar_reminders()
                self.check_important_emails()
                self.check_system_health()
                self.check_task_deadlines()
                
                self.log(f"✅ チェック完了 - 次回: {interval}秒後")
                
            except Exception as e:
                self.log(f"❌ エラー: {e}")
            
            time.sleep(interval)

def main():
    notifier = ProactiveNotifier()
    
    # テスト実行
    print("🧪 テスト実行...")
    notifier.check_calendar_reminders()
    notifier.check_important_emails()
    notifier.check_system_health()
    notifier.check_task_deadlines()
    
    print("\n✅ テスト完了")
    print("📄 通知履歴: /root/notifications.json")
    
    # 本番は監視ループ実行
    # notifier.run_monitoring_loop(interval=300)

if __name__ == "__main__":
    main()

