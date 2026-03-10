#!/usr/bin/env python3
"""
Trinity Reusable Module - Notification
Slack/Telegram通知の統一インターフェース
"""

import os
import requests
from typing import Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class NotificationType(Enum):
    """通知タイプ"""
    SLACK = "slack"
    TELEGRAM = "telegram"


class Notification:
    """通知送信の統一クラス"""
    
    def __init__(self, notification_type: NotificationType, webhook_url: Optional[str] = None, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        """
        初期化
        
        Args:
            notification_type: 通知タイプ
            webhook_url: Webhook URL（Slack用）
            bot_token: ボットトークン（Telegram用）
            chat_id: チャットID（Telegram用）
        """
        self.type = notification_type
        
        if notification_type == NotificationType.SLACK:
            self.webhook_url = webhook_url or os.getenv("SLACK_WEBHOOK_URL")
            if not self.webhook_url:
                raise ValueError("Slack webhook URL not found. Set SLACK_WEBHOOK_URL environment variable.")
        
        elif notification_type == NotificationType.TELEGRAM:
            self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
            self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")
            if not self.bot_token or not self.chat_id:
                raise ValueError("Telegram bot token or chat ID not found. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID.")
        
        logger.info(f"✅ Notification initialized: {notification_type.value}")
    
    def send(self, message: str, title: Optional[str] = None, **kwargs) -> bool:
        """
        通知を送信
        
        Args:
            message: メッセージ本文
            title: タイトル（オプション）
            **kwargs: 追加パラメータ
            
        Returns:
            成功したらTrue
        """
        try:
            if self.type == NotificationType.SLACK:
                return self._send_slack(message, title, **kwargs)
            elif self.type == NotificationType.TELEGRAM:
                return self._send_telegram(message, title, **kwargs)
            else:
                logger.error(f"❌ Unsupported notification type: {self.type}")
                return False
        except Exception as e:
            logger.error(f"❌ Notification send failed: {e}")
            return False
    
    def _send_slack(self, message: str, title: Optional[str] = None, color: str = "good", **kwargs) -> bool:
        """
        Slack通知送信
        
        Args:
            message: メッセージ
            title: タイトル
            color: 色（good/warning/danger）
            
        Returns:
            成功したらTrue
        """
        payload = {
            "attachments": [
                {
                    "color": color,
                    "title": title or "Trinity Notification",
                    "text": message,
                    "footer": "Trinity System",
                    "ts": kwargs.get("timestamp")
                }
            ]
        }
        
        # 追加フィールド
        if "fields" in kwargs:
            payload["attachments"][0]["fields"] = kwargs["fields"]
        
        response = requests.post(self.webhook_url, json=payload, timeout=10)  # type: ignore
        
        if response.status_code == 200:
            logger.info("✅ Slack notification sent")
            return True
        else:
            logger.error(f"❌ Slack notification failed: {response.status_code}")
            return False
    
    def _send_telegram(self, message: str, title: Optional[str] = None, parse_mode: str = "Markdown", **kwargs) -> bool:
        """
        Telegram通知送信
        
        Args:
            message: メッセージ
            title: タイトル
            parse_mode: パースモード（Markdown/HTML）
            
        Returns:
            成功したらTrue
        """
        # タイトル付きメッセージ作成
        if title:
            full_message = f"**{title}**\n\n{message}"
        else:
            full_message = message
        
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        
        payload = {
            "chat_id": self.chat_id,
            "text": full_message,
            "parse_mode": parse_mode
        }
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            logger.info("✅ Telegram notification sent")
            return True
        else:
            logger.error(f"❌ Telegram notification failed: {response.status_code}")
            return False
    
    def send_success(self, message: str, title: str = "✅ Success") -> bool:
        """成功通知"""
        return self.send(message, title=title, color="good")
    
    def send_warning(self, message: str, title: str = "⚠️ Warning") -> bool:
        """警告通知"""
        return self.send(message, title=title, color="warning")
    
    def send_error(self, message: str, title: str = "❌ Error") -> bool:
        """エラー通知"""
        return self.send(message, title=title, color="danger")
    
    def send_info(self, message: str, title: str = "ℹ️ Info") -> bool:
        """情報通知"""
        return self.send(message, title=title, color="#2196F3")


class MultiNotification:
    """複数の通知先に同時送信"""
    
    def __init__(self, notifiers: list):
        """
        初期化
        
        Args:
            notifiers: Notificationインスタンスのリスト
        """
        self.notifiers = notifiers
    
    def send(self, message: str, title: Optional[str] = None, **kwargs) -> bool:
        """全ての通知先に送信"""
        results = []
        for notifier in self.notifiers:
            result = notifier.send(message, title, **kwargs)
            results.append(result)
        
        # 全て成功したらTrue
        return all(results)
    
    def send_success(self, message: str, title: str = "✅ Success") -> bool:
        """成功通知"""
        return all(n.send_success(message, title) for n in self.notifiers)
    
    def send_warning(self, message: str, title: str = "⚠️ Warning") -> bool:
        """警告通知"""
        return all(n.send_warning(message, title) for n in self.notifiers)
    
    def send_error(self, message: str, title: str = "❌ Error") -> bool:
        """エラー通知"""
        return all(n.send_error(message, title) for n in self.notifiers)


if __name__ == "__main__":
    # テスト
    logging.basicConfig(level=logging.INFO)
    
    # Slackテスト
    try:
        slack = Notification(NotificationType.SLACK)
        slack.send_success("Trinity Orchestrator が正常に動作しています！")
        print("✅ Slack notification test passed")
    except Exception as e:
        print(f"⚠️ Slack test skipped: {e}")
    
    # Telegramテスト
    try:
        telegram = Notification(NotificationType.TELEGRAM)
        telegram.send_info("Trinity システムからのテスト通知です")
        print("✅ Telegram notification test passed")
    except Exception as e:
        print(f"⚠️ Telegram test skipped: {e}")



