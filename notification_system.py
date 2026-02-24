"""
通知システム
Slack/Discord/メール通知の統合
"""

import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

import requests


class NotificationSystem:
    """通知システム"""
    
    def __init__(self):
        """初期化"""
        self.slack_webhook_url = None
        self.discord_webhook_url = None
        self.email_config = {}
        self.notification_history = []
        self.storage_path = Path("notification_system_state.json")
        self._load_state()

        # state が無い場合でも、環境変数（.env からロード済みの可能性あり）をフォールバックとして利用
        if not self.slack_webhook_url:
            self.slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL") or None
        if not self.discord_webhook_url:
            self.discord_webhook_url = os.getenv("DISCORD_WEBHOOK_URL") or None
    
    def _load_state(self):
        """状態を読み込み"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.slack_webhook_url = state.get("slack_webhook_url")
                    self.discord_webhook_url = state.get("discord_webhook_url")
                    self.email_config = state.get("email_config", {})
                    self.notification_history = state.get("history", [])[-100:]
            except Exception:
                pass
    
    def _save_state(self):
        """状態を保存"""
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "slack_webhook_url": self.slack_webhook_url,
                    "discord_webhook_url": self.discord_webhook_url,
                    "email_config": self.email_config,
                    "history": self.notification_history[-100:],
                    "last_updated": datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"状態保存エラー: {e}")
    
    def configure_slack(self, webhook_url: str):
        """
        Slackを設定
        
        Args:
            webhook_url: Slack Webhook URL
        """
        self.slack_webhook_url = webhook_url
        self._save_state()
    
    def configure_discord(self, webhook_url: str):
        """
        Discordを設定
        
        Args:
            webhook_url: Discord Webhook URL
        """
        self.discord_webhook_url = webhook_url
        self._save_state()
    
    def configure_email(
        self,
        smtp_server: str,
        smtp_port: int,
        username: str,
        password: str,
        from_email: str
    ):
        """
        メールを設定
        
        Args:
            smtp_server: SMTPサーバー
            smtp_port: SMTPポート
            username: ユーザー名
            password: パスワード
            from_email: 送信元メールアドレス
        """
        self.email_config = {
            "smtp_server": smtp_server,
            "smtp_port": smtp_port,
            "username": username,
            "password": password,
            "from_email": from_email
        }
        self._save_state()
    
    def send_slack(self, message: str, channel: Optional[str] = None) -> bool:
        """
        Slackに通知
        
        Args:
            message: メッセージ
            channel: チャンネル（オプション）
            
        Returns:
            成功時True
        """
        if not self.slack_webhook_url:
            return False
        
        try:
            payload = {"text": message}
            if channel:
                payload["channel"] = channel
            
            response = requests.post(self.slack_webhook_url, json=payload, timeout=10)
            
            if response.status_code == 200:
                self.notification_history.append({
                    "type": "slack",
                    "message": message,
                    "timestamp": datetime.now().isoformat(),
                    "success": True
                })
                self._save_state()
                return True
            else:
                return False
        except Exception as e:
            print(f"Slack通知エラー: {e}")
            return False
    
    def send_discord(self, message: str, username: Optional[str] = None) -> bool:
        """
        Discordに通知
        
        Args:
            message: メッセージ
            username: ユーザー名（オプション）
            
        Returns:
            成功時True
        """
        if not self.discord_webhook_url:
            return False
        
        try:
            payload = {"content": message}
            if username:
                payload["username"] = username
            
            response = requests.post(self.discord_webhook_url, json=payload, timeout=10)
            
            if response.status_code == 204:
                self.notification_history.append({
                    "type": "discord",
                    "message": message,
                    "timestamp": datetime.now().isoformat(),
                    "success": True
                })
                self._save_state()
                return True
            else:
                return False
        except Exception as e:
            print(f"Discord通知エラー: {e}")
            return False
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        is_html: bool = False
    ) -> bool:
        """
        メールを送信
        
        Args:
            to_email: 送信先メールアドレス
            subject: 件名
            body: 本文
            is_html: HTML形式かどうか
            
        Returns:
            成功時True
        """
        if not self.email_config:
            return False
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_config["from_email"]
            msg['To'] = to_email
            msg['Subject'] = subject
            
            if is_html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(
                self.email_config["smtp_server"],
                self.email_config["smtp_port"]
            )
            server.starttls()
            server.login(
                self.email_config["username"],
                self.email_config["password"]
            )
            server.send_message(msg)
            server.quit()
            
            self.notification_history.append({
                "type": "email",
                "to": to_email,
                "subject": subject,
                "timestamp": datetime.now().isoformat(),
                "success": True
            })
            self._save_state()
            return True
            
        except Exception as e:
            print(f"メール送信エラー: {e}")
            return False
    
    def send_notification(
        self,
        message: str,
        channels: List[str] = None,
        priority: str = "normal"
    ) -> Dict[str, bool]:
        """
        複数チャンネルに通知
        
        Args:
            message: メッセージ
            channels: チャンネルのリスト（slack, discord, email）
            priority: 優先度（low, normal, high, urgent）
            
        Returns:
            各チャンネルの送信結果
        """
        if channels is None:
            channels = ["slack", "discord"]
        
        results = {}
        
        # 優先度に応じてメッセージを装飾
        if priority == "urgent":
            message = f"🚨 URGENT: {message}"
        elif priority == "high":
            message = f"⚠️ HIGH: {message}"
        
        if "slack" in channels:
            results["slack"] = self.send_slack(message)
        
        if "discord" in channels:
            results["discord"] = self.send_discord(message)
        
        return results
    
    def notify_task_completion(
        self,
        task_name: str,
        success: bool,
        details: Optional[str] = None
    ):
        """
        タスク完了を通知
        
        Args:
            task_name: タスク名
            success: 成功かどうか
            details: 詳細（オプション）
        """
        if success:
            message = f"✅ タスク完了: {task_name}"
        else:
            message = f"❌ タスク失敗: {task_name}"
        
        if details:
            message += f"\n{details}"
        
        self.send_notification(message, priority="normal" if success else "high")
    
    def notify_alert(
        self,
        alert_type: str,
        message: str,
        severity: str = "medium"
    ):
        """
        アラートを通知
        
        Args:
            alert_type: アラートタイプ
            message: メッセージ
            severity: 深刻度（low, medium, high, critical）
        """
        priority_map = {
            "low": "low",
            "medium": "normal",
            "high": "high",
            "critical": "urgent"
        }
        
        priority = priority_map.get(severity, "normal")
        formatted_message = f"🔔 [{alert_type}] {message}"
        
        self.send_notification(formatted_message, priority=priority)


def main():
    """テスト用メイン関数"""
    print("通知システムテスト")
    print("=" * 60)
    
    notification = NotificationSystem()
    
    # Slack通知テスト（設定されている場合）
    if notification.slack_webhook_url:
        print("\nSlack通知テスト:")
        result = notification.send_slack("ManaOS通知システムのテストです")
        print(f"結果: {'成功' if result else '失敗'}")
    
    # Discord通知テスト（設定されている場合）
    if notification.discord_webhook_url:
        print("\nDiscord通知テスト:")
        result = notification.send_discord("ManaOS通知システムのテストです")
        print(f"結果: {'成功' if result else '失敗'}")
    
    # タスク完了通知テスト
    print("\nタスク完了通知テスト:")
    notification.notify_task_completion("画像生成", True, "プロンプトID: test123")
    
    # アラート通知テスト
    print("\nアラート通知テスト:")
    notification.notify_alert("CPU使用率", "CPU使用率が80%を超えました", "high")


if __name__ == "__main__":
    main()



















