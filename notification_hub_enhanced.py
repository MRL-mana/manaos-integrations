#!/usr/bin/env python3
"""
🔔 Notification Hub Enhanced - 統合通知システム（拡張版）
Slack、Telegram、メール通知を統合管理
Device Health Monitorと統合
"""

import os
import json
import logging
import time
import requests
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, asdict
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 既存の通知システムをインポート
try:
    from notification_hub import NotificationHub
    NOTIFICATION_HUB_AVAILABLE = True
except ImportError:
    NOTIFICATION_HUB_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("既存のNotification Hubが利用できません")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class NotificationRule:
    """通知ルール"""
    name: str
    priority: str  # "critical", "important", "normal", "low"
    channels: List[str]  # ["slack", "telegram", "email"]
    conditions: Dict[str, Any]  # 条件（例: {"device_type": "x280", "status": "critical"}）
    enabled: bool = True


@dataclass
class NotificationHistory:
    """通知履歴"""
    notification_id: str
    timestamp: str
    priority: str
    channels: List[str]
    message: str
    success: bool
    error_message: Optional[str] = None


class NotificationHubEnhanced:
    """統合通知システム（拡張版）"""
    
    def __init__(self, config_path: str = "notification_hub_enhanced_config.json"):
        """
        初期化
        
        Args:
            config_path: 設定ファイルのパス
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
        
        # 既存のNotification Hubを初期化（オプション）
        self.base_hub = None
        self.base_notification_system = None
        if NOTIFICATION_HUB_AVAILABLE:
            try:
                self.base_hub = NotificationHub()
            except Exception as e:
                logger.debug(f"既存のNotification Hubの初期化エラー: {e}")
        
        # 既存のNotificationSystemも試す
        try:
            from notification_system import NotificationSystem
            self.base_notification_system = NotificationSystem()
        except Exception as e:
            logger.debug(f"既存のNotificationSystemの初期化エラー: {e}")
        
        # 設定を読み込む（環境変数、既存設定ファイルからも取得）
        self.slack_webhook_url = (
            os.getenv("SLACK_WEBHOOK_URL") or 
            self.config.get("slack_webhook_url") or
            self._load_from_existing_system()
        )
        self.telegram_bot_token = self.config.get("telegram_bot_token")
        self.telegram_chat_id = self.config.get("telegram_chat_id")
        self.email_config = self.config.get("email", {})
        
        # 通知ルール
        self.notification_rules: List[NotificationRule] = []
        for rule_config in self.config.get("rules", []):
            self.notification_rules.append(NotificationRule(**rule_config))
        
        # 通知履歴
        self.history_file = Path(self.config.get("history_file", "notification_history.json"))
        self.notification_history: List[NotificationHistory] = self._load_history()
        
        # 通知統計
        self.stats = {
            "total_sent": 0,
            "total_failed": 0,
            "by_channel": {
                "slack": {"sent": 0, "failed": 0},
                "telegram": {"sent": 0, "failed": 0},
                "email": {"sent": 0, "failed": 0}
            },
            "by_priority": {
                "critical": 0,
                "important": 0,
                "normal": 0,
                "low": 0
            }
        }
    
    def _load_from_existing_system(self) -> Optional[str]:
        """既存の通知システムからSlack Webhook URLを読み込む"""
        try:
            # notification_system_state.jsonから読み込み
            state_file = Path("notification_system_state.json")
            if state_file.exists():
                with open(state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    return state.get("slack_webhook_url")
            
            # SLACK_WEBHOOK_URL.mdから読み込み
            slack_url_file = Path("SLACK_WEBHOOK_URL.md")
            if slack_url_file.exists():
                content = slack_url_file.read_text(encoding='utf-8')
                # URLパターンを検索
                import re
                match = re.search(r'https://hooks\.slack\.com/services/[^\s`]+', content)
                if match:
                    return match.group(0)
        except Exception as e:
            logger.warning(f"既存システムからの設定読み込みエラー: {e}")
        return None
    
    def _load_config(self) -> Dict[str, Any]:
        """設定ファイルを読み込む"""
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # デフォルト設定を作成
            default_config = {
                "slack_webhook_url": None,
                "telegram_bot_token": None,
                "telegram_chat_id": None,
                "email": {
                    "smtp_server": "smtp.gmail.com",
                    "smtp_port": 587,
                    "username": None,
                    "password": None,
                    "from_address": None,
                    "to_addresses": []
                },
                "rules": [
                    {
                        "name": "Critical Alerts",
                        "priority": "critical",
                        "channels": ["slack", "telegram", "email"],
                        "conditions": {"status": "critical"},
                        "enabled": True
                    },
                    {
                        "name": "Device Offline",
                        "priority": "important",
                        "channels": ["slack", "telegram"],
                        "conditions": {"status": "offline"},
                        "enabled": True
                    },
                    {
                        "name": "Warning Alerts",
                        "priority": "normal",
                        "channels": ["slack"],
                        "conditions": {"status": "warning"},
                        "enabled": True
                    }
                ],
                "history_file": "notification_history.json",
                "max_history": 1000
            }
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            return default_config
    
    def _load_history(self) -> List[NotificationHistory]:
        """通知履歴を読み込む"""
        if self.history_file.exists():
            with open(self.history_file, 'r', encoding='utf-8') as f:
                history_data = json.load(f)
                return [NotificationHistory(**item) for item in history_data]
        return []
    
    def _save_history(self):
        """通知履歴を保存"""
        max_history = self.config.get("max_history", 1000)
        history_data = [asdict(h) for h in self.notification_history[-max_history:]]
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(history_data, f, indent=2, ensure_ascii=False)
    
    def _send_slack(self, message: str, priority: str = "normal") -> bool:
        """Slackに送信"""
        if not self.slack_webhook_url:
            logger.warning("Slack Webhook URLが設定されていません")
            return False
        
        # 既存のNotificationSystemを使用
        if self.base_notification_system and self.base_notification_system.slack_webhook_url:
            try:
                return self.base_notification_system.send_slack(message)
            except Exception as e:
                logger.debug(f"既存のNotificationSystem経由の送信エラー: {e}")
        
        # 直接送信
        try:
            payload = {
                "text": message,
                "username": "ManaOS Notification",
                "icon_emoji": ":bell:"
            }
            
            # 優先度に応じた色設定
            color_map = {
                "critical": "danger",
                "important": "warning",
                "normal": "good",
                "low": "#cccccc"
            }
            payload["attachments"] = [{
                "color": color_map.get(priority, "good"),
                "text": message
            }]
            
            response = requests.post(self.slack_webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            self.stats["by_channel"]["slack"]["sent"] += 1
            return True
        except Exception as e:
            logger.error(f"Slack送信エラー: {e}")
            self.stats["by_channel"]["slack"]["failed"] += 1
            return False
    
    def _send_telegram(self, message: str, priority: str = "normal") -> bool:
        """Telegramに送信"""
        if not self.telegram_bot_token or not self.telegram_chat_id:
            logger.warning("Telegram設定が不完全です")
            return False
        
        try:
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            payload = {
                "chat_id": self.telegram_chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            
            # 優先度に応じた絵文字
            emoji_map = {
                "critical": "🚨",
                "important": "⚠️",
                "normal": "ℹ️",
                "low": "📢"
            }
            payload["text"] = f"{emoji_map.get(priority, '📢')} {message}"
            
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            self.stats["by_channel"]["telegram"]["sent"] += 1
            return True
        except Exception as e:
            logger.error(f"Telegram送信エラー: {e}")
            self.stats["by_channel"]["telegram"]["failed"] += 1
            return False
    
    def _send_email(self, message: str, priority: str = "normal", subject: str = None) -> bool:
        """メールに送信"""
        email_config = self.email_config
        if not email_config.get("username") or not email_config.get("password"):
            logger.warning("メール設定が不完全です")
            return False
        
        try:
            # メール作成
            msg = MIMEMultipart()
            msg['From'] = email_config.get("from_address", email_config.get("username"))
            msg['To'] = ", ".join(email_config.get("to_addresses", []))
            msg['Subject'] = subject or f"ManaOS Notification - {priority.upper()}"
            
            msg.attach(MIMEText(message, 'plain', 'utf-8'))
            
            # SMTPサーバーに接続して送信
            server = smtplib.SMTP(email_config.get("smtp_server", "smtp.gmail.com"), 
                                 email_config.get("smtp_port", 587))
            server.starttls()
            server.login(email_config.get("username"), email_config.get("password"))
            server.send_message(msg)
            server.quit()
            
            self.stats["by_channel"]["email"]["sent"] += 1
            return True
        except Exception as e:
            logger.error(f"メール送信エラー: {e}")
            self.stats["by_channel"]["email"]["failed"] += 1
            return False
    
    def send_notification(self, message: str, priority: str = "normal", 
                         channels: Optional[List[str]] = None,
                         context: Optional[Dict[str, Any]] = None) -> bool:
        """
        通知を送信
        
        Args:
            message: メッセージ
            priority: 優先度（"critical", "important", "normal", "low"）
            channels: 送信チャネル（Noneの場合はルールに従う）
            context: コンテキスト情報（ルールマッチングに使用）
        
        Returns:
            成功時True
        """
        # ルールに基づいてチャネルを決定
        if channels is None:
            channels = self._determine_channels(priority, context)
        
        # 通知IDを生成
        notification_id = f"notif_{int(time.time())}_{len(self.notification_history)}"
        
        # 各チャネルに送信
        success_channels = []
        failed_channels = []
        
        for channel in channels:
            success = False
            if channel == "slack":
                success = self._send_slack(message, priority)
            elif channel == "telegram":
                success = self._send_telegram(message, priority)
            elif channel == "email":
                subject = context.get("subject") if context else None
                success = self._send_email(message, priority, subject)
            
            if success:
                success_channels.append(channel)
            else:
                failed_channels.append(channel)
        
        # 履歴に記録
        overall_success = len(success_channels) > 0
        history_entry = NotificationHistory(
            notification_id=notification_id,
            timestamp=datetime.now().isoformat(),
            priority=priority,
            channels=channels,
            message=message,
            success=overall_success,
            error_message=f"Failed channels: {failed_channels}" if failed_channels else None
        )
        self.notification_history.append(history_entry)
        self._save_history()
        
        # 統計を更新
        self.stats["total_sent"] += 1
        if not overall_success:
            self.stats["total_failed"] += 1
        self.stats["by_priority"][priority] = self.stats["by_priority"].get(priority, 0) + 1
        
        return overall_success
    
    def _determine_channels(self, priority: str, context: Optional[Dict[str, Any]] = None) -> List[str]:
        """ルールに基づいてチャネルを決定"""
        channels = set()
        
        # 優先度に基づくデフォルトチャネル
        priority_channels = {
            "critical": ["slack", "telegram", "email"],
            "important": ["slack", "telegram"],
            "normal": ["slack"],
            "low": ["slack"]
        }
        channels.update(priority_channels.get(priority, ["slack"]))
        
        # ルールに基づいてチャネルを追加/削除
        if context:
            for rule in self.notification_rules:
                if not rule.enabled:
                    continue
                
                # 条件をチェック
                if self._match_conditions(rule.conditions, context):
                    channels.update(rule.channels)
        
        return list(channels)
    
    def _match_conditions(self, conditions: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """条件をマッチング"""
        for key, value in conditions.items():
            if key not in context:
                return False
            if context[key] != value:
                return False
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """統計情報を取得"""
        return {
            "total_sent": self.stats["total_sent"],
            "total_failed": self.stats["total_failed"],
            "success_rate": (self.stats["total_sent"] - self.stats["total_failed"]) / max(self.stats["total_sent"], 1),
            "by_channel": self.stats["by_channel"],
            "by_priority": self.stats["by_priority"],
            "recent_notifications": [asdict(h) for h in self.notification_history[-10:]]
        }
    
    def get_status(self) -> Dict[str, Any]:
        """システム状態を取得（統一インターフェース）"""
        return self.get_stats()


def main():
    """メイン関数（テスト用）"""
    hub = NotificationHubEnhanced()
    
    # テスト通知
    hub.send_notification(
        "これはテスト通知です",
        priority="normal",
        context={"device_type": "mothership", "status": "healthy"}
    )
    
    # 統計を表示
    stats = hub.get_stats()
    print(json.dumps(stats, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

