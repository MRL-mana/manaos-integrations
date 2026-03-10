#!/usr/bin/env python3
"""
Mana Notification Master - 通知統合システム
プロアクティブ監視 + LINE/Slack/デスクトップ通知
"""

import time
import requests
import os
from datetime import datetime
from pathlib import Path
import psutil

class ManaNotificationMaster:
    """統合通知システム"""
    
    def __init__(self):
        self.line_token = os.getenv("LINE_NOTIFY_TOKEN", "")
        self.slack_webhook = os.getenv("SLACK_WEBHOOK_URL", "")
        self.log_file = Path("/root/logs/notifications_master.log")
        self.log_file.parent.mkdir(exist_ok=True)
        
    def send_notification(self, title, message, priority="info"):
        """統合通知送信（LINE/Slack/ログ）"""
        self.log(f"{priority.upper()}: {title} - {message}")
        
        # 優先度に応じて送信先を決定
        if priority in ["urgent", "high"]:
            self.send_line(f"{title}\n{message}")
            self.send_slack(f"*{title}*\n{message}")
        elif priority == "medium":
            self.send_slack(f"{title}\n{message}")
        
        # デスクトップ通知（Linux）
        self._send_desktop(title, message)
        
        return {"success": True, "sent_to": self._get_channels(priority)}
    
    def send_line(self, message):
        """LINE通知"""
        if not self.line_token:
            return False
        
        try:
            headers = {"Authorization": f"Bearer {self.line_token}"}
            data = {"message": f"\n🌟 Mana\n{message}"}
            response = requests.post(
                "https://notify-api.line.me/api/notify",
                headers=headers,
                data=data,
                timeout=10
            )
            return response.status_code == 200
        except requests.RequestException:
            return False
    
    def send_slack(self, message):
        """Slack通知"""
        if not self.slack_webhook:
            return False
        
        try:
            response = requests.post(
                self.slack_webhook,
                json={"text": message},
                timeout=10
            )
            return response.status_code == 200
        except requests.RequestException:
            return False
    
    def _send_desktop(self, title, message):
        """デスクトップ通知"""
        try:
            import subprocess
            subprocess.run(
                ["notify-send", title, message],
                check=False,
                stderr=subprocess.DEVNULL
            )
        except subprocess.SubprocessError:  # type: ignore[possibly-unbound]
            pass
    
    def monitor_loop(self, interval=300):
        """プロアクティブ監視ループ（5分間隔）"""
        self.log("🚀 統合通知システム起動")
        
        while True:
            try:
                # カレンダーチェック
                self._check_calendar()
                
                # メールチェック
                self._check_email()
                
                # システムチェック
                self._check_system()
                
                # タスクチェック
                self._check_tasks()
                
            except Exception as e:
                self.log(f"エラー: {e}")
            
            time.sleep(interval)
    
    def _check_calendar(self):
        """カレンダー監視"""
        # 15分後のイベントをチェック
        # （実装時にGoogle Calendar API使用）
        pass
    
    def _check_email(self):
        """メール監視"""
        # 新着重要メールをチェック
        # （実装時にGmail API使用）
        pass
    
    def _check_system(self):
        """システム監視"""
        cpu = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent
        
        if cpu > 90:
            self.send_notification("⚠️ CPU警告", f"CPU使用率: {cpu}%", "high")
        
        if memory > 90:
            self.send_notification("⚠️ メモリ警告", f"メモリ使用率: {memory}%", "high")
        
        if disk > 95:
            self.send_notification("⚠️ ディスク警告", f"ディスク使用率: {disk}%", "urgent")
    
    def _check_tasks(self):
        """タスク監視"""
        # 期限近いタスクをチェック
        # （実装時にタスクDBと統合）
        pass
    
    def log(self, message):
        """ログ出力"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] {message}"
        print(log_msg)
        
        with open(self.log_file, 'a') as f:
            f.write(log_msg + "\n")
    
    def _get_channels(self, priority):
        """送信チャネル取得"""
        if priority in ["urgent", "high"]:
            return ["LINE", "Slack", "Desktop"]
        elif priority == "medium":
            return ["Slack", "Desktop"]
        else:
            return ["Desktop"]

def main():
    notifier = ManaNotificationMaster()
    
    print("🔔 Mana Notification Master\n")
    
    # テスト通知
    notifier.send_notification(
        "✅ システム起動",
        "統合通知システムが起動しました",
        "info"
    )
    
    print("\n✅ 統合通知システム準備完了")

if __name__ == "__main__":
    main()

