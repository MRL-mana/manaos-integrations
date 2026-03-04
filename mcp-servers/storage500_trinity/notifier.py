#!/usr/bin/env python3
"""
Trinity Orchestrator - Notifier
PACTS完了時にSlack/Telegram通知を送信
"""

import os
import sys
import time
import json
import logging
from datetime import datetime
import requests

# 再利用モジュールを使用
sys.path.insert(0, '/root/trinity_legacy/reusable')
try:
    from notification import Notification, NotificationType
    from redis_helper import RedisHelper
    USE_REUSABLE = True
except ImportError:
    USE_REUSABLE = False
    logging.warning("再利用モジュールが見つかりません。簡易版を使用します。")

from ticket_manager import TicketManager

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s"
)
logger = logging.getLogger("trinity_notifier")


class TrinityNotifier:
    """Trinity Orchestrator 通知システム"""
    
    def __init__(self):
        """初期化"""
        self.ticket_manager = TicketManager()
        
        # Slack Webhook URL
        self.slack_webhook = os.getenv("SLACK_WEBHOOK_URL")
        if not self.slack_webhook:
            try:
                with open("/root/.mana_vault/slack_webhook.txt", "r") as f:
                    self.slack_webhook = f.read().strip()
            except:
                logger.warning("⚠️ Slack webhook not found")
                self.slack_webhook = None
        
        # 再利用モジュールがあれば使う
        if USE_REUSABLE and self.slack_webhook:
            try:
                os.environ["SLACK_WEBHOOK_URL"] = self.slack_webhook
                self.slack = Notification(NotificationType.SLACK)
                logger.info("✅ Slack notification initialized (reusable module)")
            except Exception as e:
                logger.warning(f"⚠️ Failed to init Slack: {e}")
                self.slack = None
        else:
            self.slack = None
        
        # 既に通知したチケットを記録（重複防止）
        self.notified_tickets = set()
        
        logger.info("✅ Trinity Notifier initialized")
    
    def send_slack(self, message: str, color: str = "good", title: str = "Trinity Orchestrator") -> bool:
        """
        Slackに通知送信
        
        Args:
            message: メッセージ
            color: 色（good/warning/danger）
            title: タイトル
            
        Returns:
            成功したらTrue
        """
        if not self.slack_webhook:
            logger.debug("Slack webhook not configured")
            return False
        
        try:
            # 再利用モジュールを使用
            if self.slack:
                if color == "good":
                    return self.slack.send_success(message, title)
                elif color == "warning":
                    return self.slack.send_warning(message, title)
                elif color == "danger":
                    return self.slack.send_error(message, title)
                else:
                    return self.slack.send(message, title)
            
            # 簡易版（fallback）
            payload = {
                "attachments": [{
                    "color": color,
                    "title": title,
                    "text": message,
                    "footer": "Trinity Orchestrator v1.0",
                    "ts": int(datetime.now().timestamp())
                }]
            }
            
            response = requests.post(self.slack_webhook, json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"❌ Slack notification failed: {e}")
            return False
    
    def notify_ticket_started(self, ticket_id: str, goal: str):
        """チケット開始通知"""
        message = f"🚀 *新しいタスク開始*\n\n*Ticket*: `{ticket_id}`\n*Goal*: {goal}"
        self.send_slack(message, color="#2196F3", title="🎯 Orchestrator Started")
        logger.info(f"📨 Sent start notification: {ticket_id}")
    
    def notify_ticket_completed(self, ticket_id: str, ticket: dict):
        """チケット完了通知"""
        status = ticket.get("final_status", "unknown")
        confidence = ticket.get("status", {}).get("confidence", 0)
        turns = ticket.get("status", {}).get("turn", 0)
        artifacts = ticket.get("artifacts", [])
        
        if status == "completed":
            emoji = "✅"
            color = "good"
            title = "🎉 Task Completed"
        else:
            emoji = "❌"
            color = "danger"
            title = "⚠️ Task Failed"
        
        files_text = "\n".join([f"• `{a['path']}`" for a in artifacts]) if artifacts else "なし"
        
        message = f"""
{emoji} *タスク完了*

*Ticket*: `{ticket_id}`
*Goal*: {ticket['goal']}
*Status*: {status.upper()}
*Confidence*: {confidence:.0%}
*Turns*: {turns}
*Files*: {len(artifacts)}個

*生成ファイル*:
{files_text}
        """.strip()
        
        self.send_slack(message, color=color, title=title)
        logger.info(f"📨 Sent completion notification: {ticket_id}")
    
    def notify_agent_action(self, ticket_id: str, role: str, action: str, result: str):
        """エージェントアクション通知（詳細モード）"""
        emoji_map = {
            "remi": "🎯",
            "luna": "⚙️",
            "mina": "🔍"
        }
        
        emoji = emoji_map.get(role, "🤖")
        
        message = f"""
{emoji} *{role.capitalize()}* が {action} を実行

*Ticket*: `{ticket_id}`
*Result*: {result}
        """.strip()
        
        self.send_slack(message, color="#FFC107", title=f"{emoji} Agent Action")
        logger.info(f"📨 Sent agent action: {role}/{action}")
    
    def monitor_tickets(self, interval: int = 30):
        """
        チケットを監視して通知（デーモンモード）
        
        Args:
            interval: チェック間隔（秒）
        """
        logger.info(f"👀 Starting ticket monitor (interval: {interval}s)")
        
        try:
            while True:
                active_tickets = self.ticket_manager.list_active_tickets()
                
                for ticket_id in active_tickets:
                    if ticket_id not in self.notified_tickets:
                        ticket = self.ticket_manager.get_ticket(ticket_id)
                        if ticket:
                            # 新規チケット
                            self.notify_ticket_started(ticket_id, ticket['goal'])
                            self.notified_tickets.add(ticket_id)
                
                # クローズ済みチケットもチェック
                closed_key = "tickets:closed"
                try:
                    redis_client = self.ticket_manager.redis_client
                    closed_tickets = list(redis_client.smembers(closed_key))
                    
                    for ticket_id in closed_tickets:
                        if ticket_id not in self.notified_tickets:
                            ticket = self.ticket_manager.get_ticket(ticket_id)
                            if ticket and ticket.get("final_status"):
                                self.notify_ticket_completed(ticket_id, ticket)
                                self.notified_tickets.add(ticket_id)
                except Exception as e:
                    logger.debug(f"Closed tickets check error: {e}")
                
                time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("👋 Ticket monitor stopped")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Trinity Orchestrator Notifier")
    parser.add_argument("--interval", type=int, default=30, help="監視間隔（秒）")
    parser.add_argument("--test", action="store_true", help="テストモード")
    
    args = parser.parse_args()
    
    notifier = TrinityNotifier()
    
    if args.test:
        # テスト通知
        logger.info("📨 Sending test notification...")
        result = notifier.send_slack(
            "Trinity Orchestrator v1.0 通知システムのテストです 🎉",
            color="good",
            title="✅ Test Notification"
        )
        if result:
            logger.info("✅ Test notification sent successfully")
        else:
            logger.error("❌ Test notification failed")
    else:
        # 監視モード
        notifier.monitor_tickets(interval=args.interval)



