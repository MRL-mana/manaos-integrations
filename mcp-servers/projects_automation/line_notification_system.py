#!/usr/bin/env python3
"""
LINE Notify統合システム
重要な通知をLINEに送信
"""

import requests
import os
from datetime import datetime
from pathlib import Path

class LineNotifier:
    """LINE Notify統合"""
    
    def __init__(self):
        # LINE Notify トークン（設定必要）
        self.line_token = os.getenv("LINE_NOTIFY_TOKEN", "")
        self.line_api = "https://notify-api.line.me/api/notify"
        
        # Slack設定（既存）
        self.slack_webhook = os.getenv("SLACK_WEBHOOK_URL", "")
        
        # 通知履歴
        self.history_file = Path("/root/logs/notifications_history.json")
        
    def send_line(self, message):
        """LINE通知送信"""
        if not self.line_token:
            print("⚠️  LINE_NOTIFY_TOKEN未設定")
            return {"success": False, "error": "Token not set"}
        
        try:
            headers = {"Authorization": f"Bearer {self.line_token}"}
            data = {"message": f"\n🌟 Mana通知\n{message}"}
            
            response = requests.post(
                self.line_api,
                headers=headers,
                data=data,
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"✅ LINE通知送信: {message[:30]}...")
                self._save_history("LINE", message)
                return {"success": True}
            else:
                print(f"❌ LINE通知失敗: {response.status_code}")
                return {"success": False, "error": response.text}
                
        except Exception as e:
            print(f"❌ LINE通知エラー: {e}")
            return {"success": False, "error": str(e)}
    
    def send_slack(self, message):
        """Slack通知送信"""
        if not self.slack_webhook:
            print("⚠️  SLACK_WEBHOOK_URL未設定")
            return {"success": False, "error": "Webhook not set"}
        
        try:
            data = {
                "text": "🌟 Mana通知",
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": message
                        }
                    }
                ]
            }
            
            response = requests.post(
                self.slack_webhook,
                json=data,
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"✅ Slack通知送信: {message[:30]}...")
                self._save_history("Slack", message)
                return {"success": True}
            else:
                return {"success": False, "error": response.text}
                
        except Exception as e:
            print(f"❌ Slack通知エラー: {e}")
            return {"success": False, "error": str(e)}
    
    def send_both(self, message):
        """LINE＆Slack両方に送信"""
        line_result = self.send_line(message)
        slack_result = self.send_slack(message)
        
        return {
            "line": line_result,
            "slack": slack_result
        }
    
    def notify_important_email(self, email_info):
        """重要メール通知"""
        message = f"""
📧 重要メール受信

差出人: {email_info.get('from', '不明')}
件名: {email_info.get('subject', '件名なし')}
時刻: {datetime.now().strftime('%H:%M')}
"""
        return self.send_both(message)
    
    def notify_meeting_reminder(self, meeting_info):
        """会議リマインダー"""
        message = f"""
📅 会議リマインダー

{meeting_info.get('title', '会議')}
時刻: {meeting_info.get('time', '不明')}
あと15分で開始します
"""
        return self.send_both(message)
    
    def notify_task_deadline(self, task_info):
        """タスク期限通知"""
        message = f"""
⏰ タスク期限警告

タスク: {task_info.get('title', 'タスク')}
期限: {task_info.get('deadline', '不明')}
残り時間: {task_info.get('hours_left', '?')}時間
"""
        return self.send_both(message)
    
    def notify_system_alert(self, alert_type, details):
        """システムアラート"""
        icons = {
            "error": "🔴",
            "warning": "⚠️",
            "info": "ℹ️",
            "success": "✅"
        }
        
        icon = icons.get(alert_type, "📢")
        
        message = f"""
{icon} システム通知

種類: {alert_type.upper()}
内容: {details}
時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        return self.send_both(message)
    
    def _save_history(self, platform, message):
        """通知履歴保存"""
        import json
        
        history = []
        if self.history_file.exists():
            with open(self.history_file, 'r') as f:
                history = json.load(f)
        
        history.append({
            "platform": platform,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
        
        # 最新100件のみ保持
        history = history[-100:]
        
        with open(self.history_file, 'w') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)

def main():
    notifier = LineNotifier()
    
    print("🧪 LINE通知システム テスト\n")
    
    # テスト通知
    result = notifier.send_both("テスト通知：システム正常稼働中")
    print(f"\n結果: {result}")
    
    # 各種通知テスト
    notifier.notify_important_email({
        "from": "テスト送信者",
        "subject": "テストメール"
    })
    
    notifier.notify_system_alert("success", "システム起動完了")
    
    print("\n✅ テスト完了")
    print("📝 LINE Notify トークン設定:")
    print("   export LINE_NOTIFY_TOKEN='your_token_here'")
    print("   https://notify-bot.line.me/ で取得")

if __name__ == "__main__":
    main()

