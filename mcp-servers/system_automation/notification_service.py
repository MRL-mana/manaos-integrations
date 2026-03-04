#!/usr/bin/env python3
"""
通知サービス
メール、Telegram、ログファイルへの通知送信
"""

import json
import smtplib
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    import requests as requests_module  # type: ignore
else:  # pragma: no cover
    try:
        import requests as requests_module  # type: ignore
    except ImportError:
        requests_module = None
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class NotificationService:
    """通知サービス"""

    def __init__(self, base_path: str = "/root"):
        self.base_path = Path(base_path)
        self.config_path = self.base_path / ".notification_config.json"
        self.json_log_path = self.base_path / "logs/notifications.jsonl"

        self.default_config = {
            "email": {
                "enabled": False,
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "sender_email": "",
                "sender_password": "",
                "recipient_email": ""
            },
            "telegram": {
                "enabled": False,
                "bot_token": "",
                "chat_id": "",
                "format": "html"
            },
            "slack": {
                "enabled": False,
                "webhook_url": "",
                "username": "Mana Notification",
                "icon_emoji": ":bell:"
            },
            "log_file": {
                "enabled": True,
                "path": "logs/notifications.log"
            }
        }

        self.config = self.load_config()
        self.notification_log = []

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

    def send_email(self, subject: str, body: str) -> bool:
        """メール送信"""
        if not self.config["email"]["enabled"]:
            return False

        try:
            smtp_server = self.config["email"]["smtp_server"]
            smtp_port = self.config["email"]["smtp_port"]
            sender_email = self.config["email"]["sender_email"]
            sender_password = self.config["email"]["sender_password"]
            recipient_email = self.config["email"]["recipient_email"]

            # メッセージ作成
            message = f"""From: {sender_email}
To: {recipient_email}
Subject: {subject}

{body}
"""

            # SMTP接続
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, message)
            server.quit()

            logger.info(f"✅ メール送信成功: {recipient_email}")
            return True

        except Exception as e:
            logger.error(f"❌ メール送信エラー: {e}")
            return False

    def send_telegram(self, message: str) -> bool:
        """Telegram送信"""
        if not self.config["telegram"]["enabled"]:
            return False

        try:
            bot_token = self.config["telegram"]["bot_token"]
            chat_id = self.config["telegram"]["chat_id"]

            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            data = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML"
            }

            if requests_module is None:
                logger.error("requestsモジュールが利用できないためTelegram送信不可")
                return False

            response = requests_module.post(url, json=data, timeout=10)

            if response.status_code == 200:
                logger.info("✅ Telegram送信成功")
                return True
            else:
                logger.error(f"❌ Telegram送信エラー: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"❌ Telegram送信エラー: {e}")
            return False

    def log_notification(self, level: str, title: str, message: str):
        """ログファイルに通知を記録"""
        if not self.config["log_file"]["enabled"]:
            return

        timestamp_dt = datetime.now(timezone.utc)
        timestamp_display = timestamp_dt.astimezone().strftime("%Y-%m-%d %H:%M:%S")

        try:
            log_path = self.base_path / self.config["log_file"]["path"]
            log_path.parent.mkdir(parents=True, exist_ok=True)

            log_entry = f"[{timestamp_display}] [{level}] {title}: {message}\n"

            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(log_entry)

            # メモリにも保存（最新100件）
            self.notification_log.append({
                "timestamp": timestamp_display,
                "level": level,
                "title": title,
                "message": message
            })

            if len(self.notification_log) > 100:
                self.notification_log.pop(0)

        except Exception as e:
            logger.error(f"ログ記録エラー: {e}")

        # JSON形式でも保存
        try:
            self.json_log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.json_log_path, 'a', encoding='utf-8') as jf:
                json.dump(
                    {
                        "timestamp": timestamp_dt.isoformat(),
                        "level": level,
                        "title": title,
                        "message": message,
                    },
                    jf,
                    ensure_ascii=False,
                )
                jf.write("\n")
        except Exception as e:
            logger.error(f"JSON通知ログ書き込みエラー: {e}")

    def _normalize_level(self, level: str) -> str:
        return (level or "INFO").upper()

    def _compose_notification(self, level: str, title: str, message: str):
        level_upper = self._normalize_level(level)
        styles = {
            "CRITICAL": {"emoji": "🔴", "tag": "[CRITICAL]"},
            "WARNING": {"emoji": "⚠️", "tag": "[WARNING]"},
            "INFO": {"emoji": "ℹ️", "tag": "[INFO]"},
            "SUCCESS": {"emoji": "✅", "tag": "[SUCCESS]"},
        }
        style = styles.get(level_upper, styles["INFO"])
        emoji = style["emoji"]
        tag = style["tag"]

        plain_text = f"{emoji} {tag} {title}\n\n{message}"
        telegram_mode = self.config["telegram"].get("format", "html").lower()
        if telegram_mode == "markdown":
            telegram_text = f"*{title}*\n\n{message}"
        else:
            telegram_text = f"<b>{title}</b>\n\n{message}"

        color_map = {
            "CRITICAL": "#D00000",
            "WARNING": "#FFB20F",
            "INFO": "#36C5F0",
            "SUCCESS": "#2EB67D",
        }
        slack_payload = {
            "username": self.config["slack"].get("username", "Mana Notification"),
            "icon_emoji": self.config["slack"].get("icon_emoji", ":bell:"),
            "text": f"{emoji} {tag} {title}",
            "blocks": [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": f"{emoji} {title}"},
                },
                {"type": "section", "text": {"type": "mrkdwn", "text": message}},
            ],
            "attachments": [
                {
                    "color": color_map.get(level_upper, "#36C5F0"),
                    "mrkdwn_in": ["text"],
                    "text": message,
                }
            ],
        }
        return level_upper, plain_text, telegram_text, slack_payload

    def send_slack(self, payload: dict) -> bool:
        if not self.config["slack"]["enabled"]:
            return False
        webhook = self.config["slack"].get("webhook_url")
        if not webhook:
            logger.error("Slack webhook未設定")
            return False
        if requests_module is None:
            logger.error("requestsモジュールが利用できません")
            return False
        try:
            response = requests_module.post(webhook, json=payload, timeout=10)
            if response.status_code >= 200 and response.status_code < 300:
                logger.info("✅ Slack送信成功")
                return True
            logger.error(f"❌ Slack送信エラー: {response.status_code}")
        except Exception as e:
            logger.error(f"❌ Slack送信例外: {e}")
        return False

    def send_notification(self, level: str, title: str, message: str):
        """通知送信（全チャネル）"""
        normalized_level, plain_text, telegram_text, slack_payload = self._compose_notification(level, title, message)

        # ログファイルに記録
        self.log_notification(normalized_level, title, message)

        # メール送信
        if self.config["email"]["enabled"]:
            subject = f"[{normalized_level}] {title}"
            self.send_email(subject, plain_text)

        # Telegram送信
        if self.config["telegram"]["enabled"]:
            self.send_telegram(telegram_text)

        # Slack送信
        if self.config["slack"]["enabled"]:
            self.send_slack(slack_payload)

        # コンソール出力
        logger.info(f"📢 通知送信: [{normalized_level}] {title}")

    def send_alert(self, alert: Dict):
        """アラート通知"""
        level = alert.get("level", "INFO")
        title = f"アラート: {alert.get('type', 'Unknown')}"
        message = alert.get("message", "")

        self.send_notification(level, title, message)

    def send_system_status(self, status: Dict):
        """システムステータス通知"""
        title = "システムステータス"

        message = f"""
📊 システムステータス

CPU: {status.get('cpu_percent', 0):.1f}%
メモリ: {status.get('memory_percent', 0):.1f}%
ディスク: {status.get('disk_percent', 0):.1f}%
プロセス数: {status.get('process_count', 0)}個
"""

        self.send_notification("INFO", title, message)

    def send_maintenance_complete(self, results: Dict):
        """メンテナンス完了通知"""
        title = "メンテナンス完了"

        message = f"""
🔧 メンテナンス完了

ログローテーション: {results.get('log_rotation', {}).get('rotated', 0)}個
一時ファイル削除: {results.get('temp_cleanup', {}).get('deleted', 0)}個
データベース最適化: {results.get('database_optimization', {}).get('optimized', 0)}個
"""

        self.send_notification("INFO", title, message)

    def get_notification_history(self, limit: int = 50) -> List[Dict]:
        """通知履歴取得"""
        return self.notification_log[-limit:]


def main():
    """メイン実行"""
    service = NotificationService()

    print("=" * 60)
    print("📢 通知サービス")
    print("=" * 60)

    # ステータス表示
    print("\n📊 ステータス:")
    print(f"  メール: {'✅' if service.config['email']['enabled'] else '❌'}")
    print(f"  Telegram: {'✅' if service.config['telegram']['enabled'] else '❌'}")
    print(f"  ログファイル: {'✅' if service.config['log_file']['enabled'] else '❌'}")

    # メニュー
    print("\n実行する操作を選択:")
    print("  1. テスト通知送信")
    print("  2. アラート通知送信")
    print("  3. システムステータス通知")
    print("  4. 通知履歴表示")
    print("  5. 設定変更")
    print("  0. 終了")

    choice = input("\n選択 (0-5): ").strip()

    if choice == "1":
        print("\n📢 テスト通知送信中...")
        service.send_notification(
            "INFO",
            "テスト通知",
            "これは通知サービスのテストメッセージです。"
        )
        print("✅ 通知送信完了")

    elif choice == "2":
        alert = {
            "level": "WARNING",
            "type": "CPU",
            "message": "CPU使用率が高いです: 85%"
        }
        service.send_alert(alert)
        print("✅ アラート通知送信完了")

    elif choice == "3":
        status = {
            "cpu_percent": 45.2,
            "memory_percent": 62.8,
            "disk_percent": 73.1,
            "process_count": 156
        }
        service.send_system_status(status)
        print("✅ システムステータス通知送信完了")

    elif choice == "4":
        print("\n📋 通知履歴:")
        history = service.get_notification_history(20)
        for notif in history:
            print(f"  [{notif['timestamp']}] [{notif['level']}] {notif['title']}")

    elif choice == "5":
        print("\n⚙️ 設定変更")
        print("現在の設定:")
        print(json.dumps(service.config, indent=2, ensure_ascii=False))
        print("\n設定ファイル: " + str(service.config_path))

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()

