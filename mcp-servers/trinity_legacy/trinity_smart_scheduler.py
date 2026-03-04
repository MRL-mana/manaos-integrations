#!/usr/bin/env python3
"""
⏰ Trinity Smart Scheduler
インテリジェントなスケジュール管理＆リマインダーシステム

機能:
- Google Calendar連携
- 自動リマインダー
- 会議前通知
- タスク締切アラート
- 習慣トラッキング
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

# 設定
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class TrinitySmartScheduler:
    """スマートスケジューラー"""
    
    def __init__(
        self,
        notification_system=None,
        obsidian_connector=None
    ):
        """初期化"""
        self.notification = notification_system
        self.obsidian = obsidian_connector
        
        # リマインダー設定（分）
        self.reminder_intervals = {
            "meeting": [30, 10, 5],  # 会議: 30分前、10分前、5分前
            "task": [60, 30],  # タスク: 1時間前、30分前
            "event": [10]  # 一般イベント: 10分前
        }
        
        # 習慣トラッキング
        self.habits = []
        
        logger.info("⏰ Smart Scheduler initialized!")
    
    async def schedule_reminder(
        self,
        title: str,
        event_time: datetime,
        event_type: str = "event",
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        リマインダーをスケジュール
        
        Args:
            title: イベントタイトル
            event_time: イベント時刻
            event_type: イベントタイプ（meeting/task/event）
            description: 説明
        """
        intervals = self.reminder_intervals.get(event_type, [10])
        scheduled_reminders = []
        
        for minutes in intervals:
            reminder_time = event_time - timedelta(minutes=minutes)
            
            # 過去の時刻はスキップ
            if reminder_time < datetime.now():
                continue
            
            scheduled_reminders.append({
                "time": reminder_time,
                "minutes_before": minutes,
                "title": title,
                "description": description
            })
        
        logger.info(f"⏰ Scheduled {len(scheduled_reminders)} reminders for: {title}")
        
        return {
            "success": True,
            "event": title,
            "event_time": event_time.isoformat(),
            "reminders": scheduled_reminders
        }
    
    async def send_reminder(
        self,
        title: str,
        minutes_before: int,
        event_time: datetime,
        description: Optional[str] = None
    ):
        """リマインダー通知を送信"""
        if not self.notification:
            logger.warning("Notification system not available")
            return
        
        # 優先度判定
        from trinity_notification_system import NotificationPriority
        priority = NotificationPriority.HIGH if minutes_before <= 10 else NotificationPriority.NORMAL
        
        message = f"「{title}」が{minutes_before}分後に開始します！\n"
        message += f"⏰ {event_time.strftime('%H:%M')}"
        
        if description:
            message += f"\n📝 {description}"
        
        await self.notification.send_notification(
            title=f"⏰ {minutes_before}分前リマインダー",
            message=message,
            priority=priority,
            tags=["reminder", "schedule"]
        )
    
    async def check_upcoming_events(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        今後のイベントをチェック
        
        Args:
            hours: 何時間先まで確認するか
            
        Returns:
            イベントリスト
        """
        # 仮のイベントデータ（実際はGoogle Calendar等から取得）
        now = datetime.now()
        
        upcoming_events = [
            {
                "title": "チームミーティング",
                "time": now + timedelta(hours=3),
                "type": "meeting",
                "participants": ["Mana", "Team"]
            },
            {
                "title": "プロジェクト締切",
                "time": now + timedelta(hours=20),
                "type": "task",
                "priority": "高"
            }
        ]
        
        # 時間内のイベントのみ
        cutoff = now + timedelta(hours=hours)
        filtered_events = [e for e in upcoming_events if e['time'] <= cutoff]
        
        return filtered_events
    
    async def auto_reminder_loop(self, check_interval: int = 60):
        """
        自動リマインダーループ
        
        Args:
            check_interval: チェック間隔（秒）
        """
        logger.info(f"🔄 Auto reminder loop started (check every {check_interval}s)")
        
        try:
            while True:
                # 今後のイベントをチェック
                events = await self.check_upcoming_events(hours=24)
                
                for event in events:
                    # リマインダーをスケジュール
                    await self.schedule_reminder(
                        title=event['title'],
                        event_time=event['time'],
                        event_type=event['type']
                    )
                
                # 次のチェックまで待機
                await asyncio.sleep(check_interval)
                
        except asyncio.CancelledError:
            logger.info("🛑 Auto reminder loop stopped")
    
    async def add_habit(
        self,
        name: str,
        time: str,
        days: List[str],
        reminder_minutes: int = 5
    ) -> Dict[str, Any]:
        """
        習慣を追加
        
        Args:
            name: 習慣名
            time: 時刻（HH:MM）
            days: 曜日リスト（["月", "水", "金"]）
            reminder_minutes: リマインダー（分前）
        """
        habit = {
            "id": len(self.habits) + 1,
            "name": name,
            "time": time,
            "days": days,
            "reminder_minutes": reminder_minutes,
            "created_at": datetime.now().isoformat()
        }
        
        self.habits.append(habit)
        logger.info(f"✅ Habit added: {name} @ {time}")
        
        return {
            "success": True,
            "habit": habit,
            "message": f"習慣「{name}」を追加しました！"
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """統計情報"""
        return {
            "habits_count": len(self.habits),
            "habits": self.habits
        }


# テスト
async def test_scheduler():
    """スケジューラーのテスト"""
    print("\n" + "="*60)
    print("⏰ Trinity Smart Scheduler Test")
    print("="*60 + "\n")
    
    # 初期化（通知システムなし）
    scheduler = TrinitySmartScheduler()
    
    # テスト1: リマインダースケジュール
    print("📅 Test 1: Schedule Reminder")
    future_time = datetime.now() + timedelta(hours=2)
    result = await scheduler.schedule_reminder(
        title="重要な会議",
        event_time=future_time,
        event_type="meeting",
        description="プロジェクトレビュー"
    )
    print(f"   ✅ Scheduled {len(result['reminders'])} reminders")
    for r in result['reminders']:
        print(f"      - {r['minutes_before']}分前: {r['time'].strftime('%H:%M')}")
    print()
    
    # テスト2: 今後のイベント
    print("📊 Test 2: Upcoming Events")
    events = await scheduler.check_upcoming_events(hours=24)
    print(f"   Found {len(events)} events:")
    for e in events:
        print(f"   - {e['title']}: {e['time'].strftime('%Y-%m-%d %H:%M')}")
    print()
    
    # テスト3: 習慣追加
    print("🎯 Test 3: Add Habit")
    result = await scheduler.add_habit(
        name="朝のコーヒー",
        time="09:00",
        days=["月", "火", "水", "木", "金"],
        reminder_minutes=5
    )
    print(f"   ✅ {result['message']}")
    print()
    
    # 統計
    stats = scheduler.get_stats()
    print("📈 Statistics:")
    print(f"   Habits: {stats['habits_count']}")
    
    print("\n" + "="*60)
    print("✨ Smart Scheduler Test Complete!")
    print("="*60 + "\n")


if __name__ == '__main__':
    asyncio.run(test_scheduler())

