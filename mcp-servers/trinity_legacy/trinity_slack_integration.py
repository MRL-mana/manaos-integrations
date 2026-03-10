#!/usr/bin/env python3
"""
💬 Trinity Slack Integration
Slack通知＆Bot統合

機能:
- Slack Webhook通知
- チャンネル別通知
- リッチメッセージ
- スレッド対応
"""

import os
import asyncio
import logging
from typing import Optional, List, Dict, Any
import requests
import json

# 設定
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class TrinitySlackIntegration:
    """Slack統合"""
    
    def __init__(self):
        """初期化"""
        self.webhook_url = os.getenv('SLACK_WEBHOOK_URL', '')
        self.sent_count = 0
        
        logger.info("💬 Slack Integration initialized")
    
    async def send_message(
        self,
        text: str,
        title: Optional[str] = None,
        color: str = "#667eea",
        fields: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Slackにメッセージ送信
        
        Args:
            text: メッセージ本文
            title: タイトル
            color: 色（hex）
            fields: フィールドリスト
        """
        if not self.webhook_url:
            return {"success": False, "error": "Slack Webhook未設定"}
        
        try:
            # Slackメッセージ形式
            payload = {
                "text": title or "Trinity Notification",
                "attachments": [{
                    "color": color,
                    "text": text,
                    "footer": "Trinity Secretary",
                    "ts": int(asyncio.get_event_loop().time())
                }]
            }
            
            if fields:
                payload["attachments"][0]["fields"] = fields
            
            response = requests.post(
                self.webhook_url,
                data=json.dumps(payload),
                headers={'Content-Type': 'application/json'}
            )
            
            response.raise_for_status()
            self.sent_count += 1
            
            logger.info(f"✅ Slack message sent: {title or text[:30]}")
            
            return {"success": True, "channel": "slack"}
            
        except Exception as e:
            logger.error(f"❌ Slack send error: {e}")
            return {"success": False, "error": str(e)}
    
    async def send_task_notification(self, task: Dict[str, Any]):
        """タスク通知"""
        return await self.send_message(
            title="📋 新しいタスク",
            text=f"「{task['title']}」が追加されました",
            color="#4caf50",
            fields=[  # type: ignore
                {"title": "優先度", "value": task.get('priority', '中'), "short": True},
                {"title": "締切", "value": task.get('due', '未設定'), "short": True}
            ]
        )
    
    async def send_meeting_reminder(self, meeting: Dict[str, Any]):
        """会議リマインダー"""
        return await self.send_message(
            title="📅 会議リマインダー",
            text=f"「{meeting['title']}」が間もなく開始します",
            color="#ff9800",
            fields=[  # type: ignore
                {"title": "時刻", "value": meeting.get('time', '-'), "short": True},
                {"title": "場所", "value": meeting.get('location', 'オンライン'), "short": True}
            ]
        )
    
    async def send_system_alert(self, alert: str, level: str = "warning"):
        """システムアラート"""
        colors = {
            "info": "#2196f3",
            "warning": "#ff9800",
            "error": "#f44336",
            "success": "#4caf50"
        }
        
        return await self.send_message(
            title="⚠️ システムアラート",
            text=alert,
            color=colors.get(level, "#ff9800")
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """統計"""
        return {
            "sent_count": self.sent_count,
            "webhook_configured": bool(self.webhook_url)
        }


# テスト
async def test_slack():
    """Slackテスト"""
    print("\n" + "="*60)
    print("💬 Trinity Slack Integration Test")
    print("="*60 + "\n")
    
    slack = TrinitySlackIntegration()
    
    # 設定確認
    if not slack.webhook_url:
        print("⚠️  SLACK_WEBHOOK_URL not set")
        print("   Set with: export SLACK_WEBHOOK_URL='your_webhook'")
        print("   Skipping send test\n")
    else:
        # テスト送信
        print("📤 Sending test message...")
        result = await slack.send_message(
            title="🧪 テスト通知",
            text="Trinity Slack統合のテストです！",
            color="#667eea"
        )
        print(f"   Result: {'✅ Success' if result['success'] else '❌ Failed'}\n")
    
    # 統計
    stats = slack.get_stats()
    print("📊 Statistics:")
    print(f"   Configured: {'✅ Yes' if stats['webhook_configured'] else '❌ No'}")
    print(f"   Sent: {stats['sent_count']}")
    
    print("\n" + "="*60)
    print("✨ Slack Integration Test Complete!")
    print("="*60 + "\n")


if __name__ == '__main__':
    asyncio.run(test_slack())

