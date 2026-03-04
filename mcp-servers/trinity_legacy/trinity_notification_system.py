#!/usr/bin/env python3
"""
🔔 Trinity Notification System
Discord, Ntfy, Pushover統合通知システム

Manaにリアルタイムで重要な通知を送信！
"""

import os
import asyncio
import logging
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime

import requests
from discord_webhook import DiscordWebhook, DiscordEmbed

# 設定
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class NotificationPriority(Enum):
    """通知の優先度"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

class NotificationChannel(Enum):
    """通知チャンネル"""
    DISCORD = "discord"
    NTFY = "ntfy"
    PUSHOVER = "pushover"
    ALL = "all"


class TrinityNotificationSystem:
    """Trinity統合通知システム"""
    
    def __init__(self):
        # Discord Webhook URL
        self.discord_webhook = os.getenv('DISCORD_WEBHOOK_URL', '')
        
        # Ntfy設定
        self.ntfy_topic = os.getenv('NTFY_TOPIC', 'trinity-notifications')
        self.ntfy_url = os.getenv('NTFY_URL', 'https://ntfy.sh')
        
        # Pushover設定
        self.pushover_token = os.getenv('PUSHOVER_TOKEN', '')
        self.pushover_user = os.getenv('PUSHOVER_USER', '')
        
        # 統計
        self.sent_count = 0
        self.failed_count = 0
        
    async def send_notification(
        self,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        channel: NotificationChannel = NotificationChannel.ALL,
        tags: Optional[List[str]] = None,
        url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        統合通知送信
        
        Args:
            title: 通知タイトル
            message: 通知メッセージ
            priority: 優先度
            channel: 送信チャンネル
            tags: タグリスト
            url: クリック時のURL
        """
        results = {
            "success": False,
            "channels": {},
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # 各チャンネルに送信
            if channel == NotificationChannel.ALL or channel == NotificationChannel.DISCORD:
                discord_result = await self._send_discord(title, message, priority, tags, url)
                results["channels"]["discord"] = discord_result
                
            if channel == NotificationChannel.ALL or channel == NotificationChannel.NTFY:
                ntfy_result = await self._send_ntfy(title, message, priority, tags, url)
                results["channels"]["ntfy"] = ntfy_result
                
            if channel == NotificationChannel.ALL or channel == NotificationChannel.PUSHOVER:
                pushover_result = await self._send_pushover(title, message, priority, url)
                results["channels"]["pushover"] = pushover_result
            
            # 全体の成功判定
            results["success"] = any(r.get("success") for r in results["channels"].values())
            
            if results["success"]:
                self.sent_count += 1
                logger.info(f"通知送信成功: {title}")
            else:
                self.failed_count += 1
                logger.error(f"通知送信失敗: {title}")
                
        except Exception as e:
            logger.error(f"通知送信エラー: {e}")
            results["error"] = str(e)
            self.failed_count += 1
        
        return results
    
    async def _send_discord(
        self,
        title: str,
        message: str,
        priority: NotificationPriority,
        tags: Optional[List[str]],
        url: Optional[str]
    ) -> Dict[str, Any]:
        """Discord Webhook送信"""
        if not self.discord_webhook:
            return {"success": False, "error": "Discord Webhook未設定"}
        
        try:
            webhook = DiscordWebhook(url=self.discord_webhook)
            
            # 優先度に応じた色
            colors = {
                NotificationPriority.LOW: 0x95a5a6,
                NotificationPriority.NORMAL: 0x3498db,
                NotificationPriority.HIGH: 0xf39c12,
                NotificationPriority.URGENT: 0xe74c3c
            }
            color = colors.get(priority, 0x3498db)
            
            # Embed作成
            embed = DiscordEmbed(
                title=f"🤖 Trinity: {title}",
                description=message,
                color=color
            )
            
            # タグ追加
            if tags:
                embed.add_embed_field(name="🏷️ タグ", value=", ".join(tags))
            
            # URL追加
            if url:
                embed.set_url(url)
            
            # タイムスタンプ
            embed.set_timestamp()
            
            # フッター
            embed.set_footer(text=f"Priority: {priority.value}")
            
            webhook.add_embed(embed)
            response = webhook.execute()
            
            return {"success": True, "channel": "discord"}
            
        except Exception as e:
            logger.error(f"Discord送信エラー: {e}")
            return {"success": False, "error": str(e)}
    
    async def _send_ntfy(
        self,
        title: str,
        message: str,
        priority: NotificationPriority,
        tags: Optional[List[str]],
        url: Optional[str]
    ) -> Dict[str, Any]:
        """Ntfy送信"""
        if not self.ntfy_topic:
            return {"success": False, "error": "Ntfy Topic未設定"}
        
        try:
            # 優先度マッピング
            ntfy_priorities = {
                NotificationPriority.LOW: 1,
                NotificationPriority.NORMAL: 3,
                NotificationPriority.HIGH: 4,
                NotificationPriority.URGENT: 5
            }
            
            # 日本語対応: JSON形式で送信（Headerの文字コード問題を回避）
            import json
            
            payload = {
                "topic": self.ntfy_topic,
                "title": title,
                "message": message,
                "priority": ntfy_priorities.get(priority, 3),
                "tags": tags if tags else ["trinity", "notification"]
            }
            
            if url:
                payload["click"] = url
            
            headers = {
                "Content-Type": "application/json; charset=utf-8"
            }
            
            response = requests.post(
                self.ntfy_url,
                data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
                headers=headers
            )
            
            response.raise_for_status()
            
            return {"success": True, "channel": "ntfy"}
            
        except Exception as e:
            logger.error(f"Ntfy送信エラー: {e}")
            return {"success": False, "error": str(e)}
    
    async def _send_pushover(
        self,
        title: str,
        message: str,
        priority: NotificationPriority,
        url: Optional[str]
    ) -> Dict[str, Any]:
        """Pushover送信"""
        if not self.pushover_token or not self.pushover_user:
            return {"success": False, "error": "Pushover設定未完了"}
        
        try:
            # 優先度マッピング
            pushover_priorities = {
                NotificationPriority.LOW: -1,
                NotificationPriority.NORMAL: 0,
                NotificationPriority.HIGH: 1,
                NotificationPriority.URGENT: 2
            }
            
            data = {
                "token": self.pushover_token,
                "user": self.pushover_user,
                "title": title,
                "message": message,
                "priority": pushover_priorities.get(priority, 0)
            }
            
            if url:
                data["url"] = url
            
            response = requests.post(
                "https://api.pushover.net/1/messages.json",
                data=data
            )
            
            response.raise_for_status()
            
            return {"success": True, "channel": "pushover"}
            
        except Exception as e:
            logger.error(f"Pushover送信エラー: {e}")
            return {"success": False, "error": str(e)}
    
    async def send_task_reminder(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """タスクリマインダー通知"""
        return await self.send_notification(
            title="📋 タスクリマインダー",
            message=f"「{task['title']}」の締切が近づいています！\n⏰ {task['due']}",
            priority=NotificationPriority.HIGH,
            tags=["task", "reminder"],
            url=f"http://localhost:9999/tasks/{task.get('id', '')}"
        )
    
    async def send_meeting_reminder(self, meeting: Dict[str, Any]) -> Dict[str, Any]:
        """会議リマインダー通知"""
        return await self.send_notification(
            title="📅 会議リマインダー",
            message=f"「{meeting['title']}」が{meeting['minutes']}分後に開始します！",
            priority=NotificationPriority.URGENT,
            tags=["meeting", "reminder"]
        )
    
    async def send_system_alert(self, alert: str, level: str = "warning") -> Dict[str, Any]:
        """システムアラート通知"""
        priorities = {
            "info": NotificationPriority.LOW,
            "warning": NotificationPriority.HIGH,
            "error": NotificationPriority.URGENT
        }
        
        return await self.send_notification(
            title="⚠️ システムアラート",
            message=alert,
            priority=priorities.get(level, NotificationPriority.NORMAL),
            tags=["system", level]
        )
    
    async def send_success_message(self, message: str) -> Dict[str, Any]:
        """成功メッセージ通知"""
        return await self.send_notification(
            title="✅ タスク完了",
            message=message,
            priority=NotificationPriority.NORMAL,
            tags=["success"]
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """統計情報取得"""
        return {
            "sent_count": self.sent_count,
            "failed_count": self.failed_count,
            "success_rate": self.sent_count / (self.sent_count + self.failed_count) * 100 if (self.sent_count + self.failed_count) > 0 else 0,
            "channels": {
                "discord": bool(self.discord_webhook),
                "ntfy": bool(self.ntfy_topic),
                "pushover": bool(self.pushover_token and self.pushover_user)
            }
        }


# グローバルインスタンス
notification_system = TrinityNotificationSystem()


# テスト用関数
async def test_notifications():
    """通知システムのテスト"""
    print("🔔 Trinity Notification System テスト開始\n")
    
    # テスト通知送信
    tests = [
        {
            "title": "テスト通知（通常）",
            "message": "これはテスト通知です。",
            "priority": NotificationPriority.NORMAL
        },
        {
            "title": "テスト通知（重要）",
            "message": "重要な通知のテストです！",
            "priority": NotificationPriority.HIGH
        },
        {
            "title": "テスト通知（緊急）",
            "message": "緊急通知のテストです！！",
            "priority": NotificationPriority.URGENT,
            "tags": ["test", "urgent"]
        }
    ]
    
    for test in tests:
        print(f"📤 送信中: {test['title']}")
        result = await notification_system.send_notification(**test)
        print(f"   結果: {'✅ 成功' if result['success'] else '❌ 失敗'}")
        print(f"   詳細: {result}\n")
        await asyncio.sleep(1)
    
    # 統計表示
    stats = notification_system.get_stats()
    print("\n📊 統計:")
    print(f"   送信成功: {stats['sent_count']}")
    print(f"   送信失敗: {stats['failed_count']}")
    print(f"   成功率: {stats['success_rate']:.1f}%")
    print("\n🔧 設定状況:")
    for channel, enabled in stats['channels'].items():
        print(f"   {channel}: {'✅ 有効' if enabled else '❌ 未設定'}")


if __name__ == '__main__':
    # テスト実行
    asyncio.run(test_notifications())

