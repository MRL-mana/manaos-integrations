#!/usr/bin/env python3
"""
Webhook統合システム
外部サービスとの連携、イベント通知、API連携
"""

import requests
import json
from datetime import datetime
from pathlib import Path
from typing import Dict
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WebhookIntegration:
    """Webhook統合システム"""
    
    def __init__(self, base_path: str = "/root"):
        self.base_path = Path(base_path)
        self.config_path = self.base_path / ".webhook_config.json"
        self.log_path = self.base_path / "logs" / "webhook.log"
        
        self.default_config = {
            "enabled": True,
            "webhooks": {
                "discord": {
                    "enabled": False,
                    "url": "",
                    "events": ["alert", "maintenance", "backup"]
                },
                "slack": {
                    "enabled": False,
                    "url": "",
                    "events": ["alert", "maintenance", "backup"]
                },
                "teams": {
                    "enabled": False,
                    "url": "",
                    "events": ["alert", "maintenance"]
                },
                "custom": {
                    "enabled": False,
                    "url": "",
                    "method": "POST",
                    "headers": {},
                    "events": ["all"]
                }
            },
            "retry": {
                "max_attempts": 3,
                "timeout": 10
            }
        }
        
        self.config = self.load_config()
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        
    def load_config(self) -> dict:
        """設定を読み込む"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"設定読み込みエラー: {e}")
                return self.default_config
        return self.default_config
    
    def save_config(self):
        """設定を保存"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"設定保存エラー: {e}")
    
    def log(self, message: str):
        """ログ記録"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        
        try:
            with open(self.log_path, 'a', encoding='utf-8') as f:
                f.write(log_message)
        except Exception as e:
            logger.error(f"ログ記録エラー: {e}")
    
    def send_discord_webhook(self, title: str, description: str, color: int = 0x00ff00) -> bool:
        """Discord Webhook送信"""
        if not self.config["webhooks"]["discord"]["enabled"]:
            return False
        
        webhook_url = self.config["webhooks"]["discord"]["url"]
        if not webhook_url:
            return False
        
        payload = {
            "embeds": [{
                "title": title,
                "description": description,
                "color": color,
                "timestamp": datetime.now().isoformat()
            }]
        }
        
        return self._send_webhook(webhook_url, payload)
    
    def send_slack_webhook(self, text: str, channel: str = None) -> bool:  # type: ignore
        """Slack Webhook送信"""
        if not self.config["webhooks"]["slack"]["enabled"]:
            return False
        
        webhook_url = self.config["webhooks"]["slack"]["url"]
        if not webhook_url:
            return False
        
        payload = {
            "text": text,
            "username": "ManaOS",
            "icon_emoji": ":robot_face:"
        }
        
        if channel:
            payload["channel"] = channel
        
        return self._send_webhook(webhook_url, payload)
    
    def send_teams_webhook(self, title: str, text: str, theme_color: str = "0078D4") -> bool:
        """Microsoft Teams Webhook送信"""
        if not self.config["webhooks"]["teams"]["enabled"]:
            return False
        
        webhook_url = self.config["webhooks"]["teams"]["url"]
        if not webhook_url:
            return False
        
        payload = {
            "@type": "MessageCard",
            "@context": "https://schema.org/extensions",
            "summary": title,
            "themeColor": theme_color,
            "title": title,
            "text": text
        }
        
        return self._send_webhook(webhook_url, payload)
    
    def send_custom_webhook(self, data: dict) -> bool:
        """カスタムWebhook送信"""
        if not self.config["webhooks"]["custom"]["enabled"]:
            return False
        
        webhook_url = self.config["webhooks"]["custom"]["url"]
        if not webhook_url:
            return False
        
        return self._send_webhook(webhook_url, data)
    
    def _send_webhook(self, url: str, payload: dict, attempt: int = 1) -> bool:
        """Webhook送信（再試行付き）"""
        try:
            response = requests.post(
                url,
                json=payload,
                timeout=self.config["retry"]["timeout"],
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "ManaOS-Webhook/1.0"
                }
            )
            
            if response.status_code in [200, 201, 204]:
                logger.info(f"✅ Webhook送信成功: {url}")
                self.log(f"Webhook送信成功: {url}")
                return True
            else:
                logger.warning(f"⚠️ Webhook送信失敗: {response.status_code}")
                self.log(f"Webhook送信失敗: {response.status_code}")
                
                # 再試行
                if attempt < self.config["retry"]["max_attempts"]:
                    logger.info(f"再試行 {attempt + 1}/{self.config['retry']['max_attempts']}")
                    return self._send_webhook(url, payload, attempt + 1)
                
                return False
        
        except Exception as e:
            logger.error(f"Webhook送信エラー: {e}")
            self.log(f"Webhook送信エラー: {e}")
            
            # 再試行
            if attempt < self.config["retry"]["max_attempts"]:
                logger.info(f"再試行 {attempt + 1}/{self.config['retry']['max_attempts']}")
                return self._send_webhook(url, payload, attempt + 1)
            
            return False
    
    def send_alert(self, severity: str, message: str, details: dict = None):  # type: ignore
        """アラート通知"""
        color_map = {
            "critical": 0xff0000,
            "high": 0xff6600,
            "medium": 0xffaa00,
            "low": 0x00aaff
        }
        
        color = color_map.get(severity.lower(), 0x00ff00)
        
        # Discord
        if "alert" in self.config["webhooks"]["discord"]["events"]:
            self.send_discord_webhook(
                f"⚠️ アラート: {severity.upper()}",
                f"{message}\n\n詳細: {json.dumps(details, ensure_ascii=False) if details else 'なし'}",
                color
            )
        
        # Slack
        if "alert" in self.config["webhooks"]["slack"]["events"]:
            self.send_slack_webhook(
                f"⚠️ *アラート: {severity.upper()}*\n{message}"
            )
        
        # Teams
        if "alert" in self.config["webhooks"]["teams"]["events"]:
            self.send_teams_webhook(
                f"アラート: {severity.upper()}",
                message,
                theme_color="FF0000"
            )
    
    def send_maintenance_notification(self, status: str, details: dict = None):  # type: ignore
        """メンテナンス通知"""
        # Discord
        if "maintenance" in self.config["webhooks"]["discord"]["events"]:
            self.send_discord_webhook(
                f"🔧 メンテナンス: {status}",
                f"ステータス: {status}\n\n詳細: {json.dumps(details, ensure_ascii=False) if details else 'なし'}",
                0x00aaff
            )
        
        # Slack
        if "maintenance" in self.config["webhooks"]["slack"]["events"]:
            self.send_slack_webhook(
                f"🔧 *メンテナンス: {status}*\nステータス: {status}"
            )
        
        # Teams
        if "maintenance" in self.config["webhooks"]["teams"]["events"]:
            self.send_teams_webhook(
                f"メンテナンス: {status}",
                f"ステータス: {status}",
                theme_color="0078D4"
            )
    
    def send_backup_notification(self, status: str, backup_info: dict = None):  # type: ignore
        """バックアップ通知"""
        # Discord
        if "backup" in self.config["webhooks"]["discord"]["events"]:
            self.send_discord_webhook(
                f"💾 バックアップ: {status}",
                f"ステータス: {status}\n\n詳細: {json.dumps(backup_info, ensure_ascii=False) if backup_info else 'なし'}",
                0x00ff00
            )
        
        # Slack
        if "backup" in self.config["webhooks"]["slack"]["events"]:
            self.send_slack_webhook(
                f"💾 *バックアップ: {status}*\nステータス: {status}"
            )
    
    def send_custom_event(self, event_type: str, data: dict):
        """カスタムイベント通知"""
        # カスタムWebhook
        if "all" in self.config["webhooks"]["custom"]["events"] or event_type in self.config["webhooks"]["custom"]["events"]:
            self.send_custom_webhook({
                "event_type": event_type,
                "timestamp": datetime.now().isoformat(),
                "data": data
            })
    
    def test_webhooks(self) -> Dict:
        """Webhookテスト"""
        logger.info("🧪 Webhookテスト開始...")
        
        results = {
            "discord": False,
            "slack": False,
            "teams": False,
            "custom": False
        }
        
        # Discordテスト
        if self.config["webhooks"]["discord"]["enabled"]:
            results["discord"] = self.send_discord_webhook(
                "🧪 テスト通知",
                "これはWebhookのテストメッセージです。",
                0x00ff00
            )
        
        # Slackテスト
        if self.config["webhooks"]["slack"]["enabled"]:
            results["slack"] = self.send_slack_webhook(
                "🧪 *テスト通知*\nこれはWebhookのテストメッセージです。"
            )
        
        # Teamsテスト
        if self.config["webhooks"]["teams"]["enabled"]:
            results["teams"] = self.send_teams_webhook(
                "テスト通知",
                "これはWebhookのテストメッセージです。"
            )
        
        # カスタムWebhookテスト
        if self.config["webhooks"]["custom"]["enabled"]:
            results["custom"] = self.send_custom_webhook({
                "test": True,
                "message": "これはWebhookのテストメッセージです。"
            })
        
        logger.info(f"✅ Webhookテスト完了: {sum(results.values())}/{len(results)} 成功")
        
        return results


def main():
    """メイン実行"""
    webhook = WebhookIntegration()
    
    print("=" * 60)
    print("🌐 Webhook統合システム")
    print("=" * 60)
    
    print("\n📊 Webhook設定:")
    for name, config in webhook.config["webhooks"].items():
        status = "✅" if config["enabled"] else "❌"
        print(f"  {status} {name.capitalize()}")
    
    print("\n実行する操作を選択:")
    print("  1. Webhookテスト")
    print("  2. アラート通知送信")
    print("  3. メンテナンス通知送信")
    print("  4. バックアップ通知送信")
    print("  5. カスタムイベント送信")
    print("  0. 終了")
    
    choice = input("\n選択 (0-5): ").strip()
    
    if choice == "1":
        print("\n🧪 Webhookテスト実行中...")
        results = webhook.test_webhooks()
        
        print("\n📊 テスト結果:")
        for name, success in results.items():
            status = "✅" if success else "❌"
            print(f"  {status} {name.capitalize()}")
    
    elif choice == "2":
        print("\n⚠️ アラート通知送信中...")
        webhook.send_alert("medium", "これはテストアラートです。")
        print("✅ 送信完了")
    
    elif choice == "3":
        print("\n🔧 メンテナンス通知送信中...")
        webhook.send_maintenance_notification("完了", {"duration": "5分"})
        print("✅ 送信完了")
    
    elif choice == "4":
        print("\n💾 バックアップ通知送信中...")
        webhook.send_backup_notification("成功", {"size": "100MB"})
        print("✅ 送信完了")
    
    elif choice == "5":
        print("\n📤 カスタムイベント送信中...")
        webhook.send_custom_event("test", {"message": "テストデータ"})
        print("✅ 送信完了")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()

