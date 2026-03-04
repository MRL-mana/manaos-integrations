#!/usr/bin/env python3
"""
Mana Notification System
統合通知システム - Slack/Telegram/Email対応
"""

import os
import json
import logging
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ManaNotificationSystem:
    def __init__(self):
        # 通知チャネル設定
        self.channels = {
            "slack": {
                "enabled": os.environ.get("SLACK_WEBHOOK_URL") is not None,
                "webhook_url": os.environ.get("SLACK_WEBHOOK_URL", ""),
                "channel": os.environ.get("SLACK_CHANNEL", "#manaos-alerts")
            },
            "telegram": {
                "enabled": os.environ.get("TELEGRAM_BOT_TOKEN") is not None,
                "bot_token": os.environ.get("TELEGRAM_BOT_TOKEN", ""),
                "chat_id": os.environ.get("TELEGRAM_CHAT_ID", "")
            }
        }
        
        # 通知レベル
        self.levels = {
            "critical": "🔴 CRITICAL",
            "error": "🟠 ERROR",
            "warning": "🟡 WARNING",
            "info": "🟢 INFO",
            "success": "✅ SUCCESS"
        }
        
        logger.info("🔔 Mana Notification System 初期化完了")
    
    def send_notification(
        self, 
        title: str, 
        message: str, 
        level: str = "info",
        channels: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """通知送信"""
        results = {}
        
        # 送信するチャネル決定
        if channels is None:
            channels = ["slack", "telegram"]
        
        # 各チャネルに送信
        for channel in channels:
            if channel == "slack" and self.channels["slack"]["enabled"]:
                results["slack"] = self._send_slack(title, message, level)
            elif channel == "telegram" and self.channels["telegram"]["enabled"]:
                results["telegram"] = self._send_telegram(title, message, level)
        
        return results
    
    def _send_slack(self, title: str, message: str, level: str) -> Dict[str, Any]:
        """Slack通知"""
        try:
            webhook_url = self.channels["slack"]["webhook_url"]
            
            # カラーコード
            colors = {
                "critical": "#FF0000",
                "error": "#FF6600",
                "warning": "#FFCC00",
                "info": "#0099FF",
                "success": "#00CC66"
            }
            
            payload = {
                "channel": self.channels["slack"]["channel"],
                "username": "ManaOS Bot",
                "icon_emoji": ":robot_face:",
                "attachments": [{
                    "color": colors.get(level, "#0099FF"),
                    "title": f"{self.levels.get(level, 'INFO')} {title}",
                    "text": message,
                    "footer": "ManaOS Notification System",
                    "ts": int(datetime.now().timestamp())
                }]
            }
            
            response = requests.post(webhook_url, json=payload, timeout=5)
            
            if response.status_code == 200:
                logger.info("✅ Slack通知送信成功")
                return {"success": True, "channel": "slack"}
            else:
                logger.error(f"Slack通知失敗: {response.status_code}")
                return {"success": False, "error": response.text}
                
        except Exception as e:
            logger.error(f"Slack通知エラー: {e}")
            return {"success": False, "error": str(e)}
    
    def _send_telegram(self, title: str, message: str, level: str) -> Dict[str, Any]:
        """Telegram通知"""
        try:
            bot_token = self.channels["telegram"]["bot_token"]
            chat_id = self.channels["telegram"]["chat_id"]
            
            text = f"{self.levels.get(level, 'INFO')} *{title}*\n\n{message}"
            
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "Markdown"
            }
            
            response = requests.post(url, json=payload, timeout=5)
            
            if response.status_code == 200:
                logger.info("✅ Telegram通知送信成功")
                return {"success": True, "channel": "telegram"}
            else:
                logger.error(f"Telegram通知失敗: {response.status_code}")
                return {"success": False, "error": response.text}
                
        except Exception as e:
            logger.error(f"Telegram通知エラー: {e}")
            return {"success": False, "error": str(e)}
    
    def notify_system_status(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """システム状態通知"""
        cpu = metrics.get("cpu", {}).get("percent", 0)
        memory = metrics.get("memory", {}).get("percent", 0)
        disk = metrics.get("disk", {}).get("percent", 0)
        
        # 状態判定
        if cpu > 90 or memory > 90 or disk > 90:
            level = "critical"
            title = "システムリソース危機的状況"
        elif cpu > 80 or memory > 80 or disk > 85:
            level = "warning"
            title = "システムリソース警告"
        else:
            level = "info"
            title = "システム正常稼働中"
        
        message = f"""
CPU: {cpu:.1f}%
メモリ: {memory:.1f}%
ディスク: {disk:.1f}%
        """.strip()
        
        return self.send_notification(title, message, level)
    
    def notify_security_alert(self, score: int, issues: Dict[str, int]) -> Dict[str, Any]:
        """セキュリティアラート"""
        if score < 40:
            level = "critical"
            title = "緊急セキュリティアラート"
        elif score < 60:
            level = "warning"
            title = "セキュリティ警告"
        else:
            level = "info"
            title = "セキュリティ正常"
        
        message = f"""
セキュリティスコア: {score}/100

Critical: {issues.get('critical', 0)}件
High: {issues.get('high', 0)}件
Medium: {issues.get('medium', 0)}件
        """.strip()
        
        return self.send_notification(title, message, level)
    
    def notify_optimization_complete(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """最適化完了通知"""
        memory_freed = results.get("memory_freed_mb", 0)
        disk_freed = results.get("disk_freed_gb", 0)
        
        message = f"""
メモリ回収: {memory_freed:.2f}MB
ディスク回収: {disk_freed:.2f}GB

最適化が完了しました。
        """.strip()
        
        return self.send_notification(
            "システム最適化完了",
            message,
            "success"
        )
    
    def notify_error_detected(self, error_type: str, details: str) -> Dict[str, Any]:
        """エラー検出通知"""
        return self.send_notification(
            f"エラー検出: {error_type}",
            details,
            "error"
        )

# グローバルインスタンス
notifier = ManaNotificationSystem()

def main():
    import sys
    
    if len(sys.argv) > 2:
        title = sys.argv[1]
        message = sys.argv[2]
        level = sys.argv[3] if len(sys.argv) > 3 else "info"
        
        result = notifier.send_notification(title, message, level)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("Usage: mana_notification_system.py <title> <message> [level]")
        print("Levels: critical, error, warning, info, success")

if __name__ == "__main__":
    main()

