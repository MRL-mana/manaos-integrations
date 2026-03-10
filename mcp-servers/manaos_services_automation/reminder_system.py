#!/usr/bin/env python3
"""
⏰ Trinity Reminder System
自動リマインダー機能

機能:
- 時間指定リマインダー（「30分後に通知」）
- 日時指定リマインダー（「明日10時に通知」）
- 繰り返しリマインダー（「毎日9時に通知」）
- リマインダー一覧・削除
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import json
import re
from pathlib import Path
from dataclasses import dataclass, asdict
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Reminder:
    """リマインダー"""
    id: str
    user_id: str
    message: str
    trigger_time: str  # ISO format
    created_at: str
    repeat: Optional[str] = None  # 'daily', 'weekly', 'monthly'
    status: str = 'active'  # 'active', 'completed', 'cancelled'


class ReminderSystem:
    """リマインダーシステム"""
    
    def __init__(self, bot=None):
        self.bot = bot
        self.reminders: Dict[str, Reminder] = {}
        self.reminders_file = Path('/root/.trinity_reminders.json')
        
        # 永続化されたリマインダーを読み込み
        self._load_reminders()
        
        # バックグラウンドタスク
        self.running = False
        self.check_task = None
        
        logger.info("⏰ Reminder System initialized")
    
    def _load_reminders(self):
        """リマインダーを読み込み"""
        if self.reminders_file.exists():
            try:
                with open(self.reminders_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for reminder_dict in data:
                        reminder = Reminder(**reminder_dict)
                        self.reminders[reminder.id] = reminder
                logger.info(f"  ✅ Loaded {len(self.reminders)} reminders")
            except Exception as e:
                logger.warning(f"  ⚠️ Failed to load reminders: {e}")
    
    def _save_reminders(self):
        """リマインダーを保存"""
        try:
            data = [asdict(r) for r in self.reminders.values()]
            with open(self.reminders_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"  ⚠️ Failed to save reminders: {e}")
    
    def parse_reminder_request(self, text: str) -> Dict[str, Any]:
        """
        リマインダー要求を解析
        
        例:
        - 「30分後にプレゼンの準備をリマインド」
        - 「明日10時に会議をリマインド」
        - 「毎日9時に日報をリマインド」
        """
        now = datetime.now()
        
        # 時間指定パターン
        patterns = {
            # X分後
            r'(\d+)分後に(.+)(?:をリマインド|リマインド)': lambda m: {
                'trigger_time': now + timedelta(minutes=int(m.group(1))),
                'message': m.group(2).strip(),
                'repeat': None
            },
            # X時間後
            r'(\d+)時間後に(.+)(?:をリマインド|リマインド)': lambda m: {
                'trigger_time': now + timedelta(hours=int(m.group(1))),
                'message': m.group(2).strip(),
                'repeat': None
            },
            # 明日X時
            r'明日(\d+)時に(.+)(?:をリマインド|リマインド)': lambda m: {
                'trigger_time': (now + timedelta(days=1)).replace(
                    hour=int(m.group(1)), minute=0, second=0, microsecond=0
                ),
                'message': m.group(2).strip(),
                'repeat': None
            },
            # 毎日X時
            r'毎日(\d+)時に(.+)(?:をリマインド|リマインド)': lambda m: {
                'trigger_time': now.replace(
                    hour=int(m.group(1)), minute=0, second=0, microsecond=0
                ),
                'message': m.group(2).strip(),
                'repeat': 'daily'
            },
            # 今日X時
            r'今日(\d+)時に(.+)(?:をリマインド|リマインド)': lambda m: {
                'trigger_time': now.replace(
                    hour=int(m.group(1)), minute=0, second=0, microsecond=0
                ),
                'message': m.group(2).strip(),
                'repeat': None
            },
        }
        
        for pattern, parser in patterns.items():
            match = re.search(pattern, text)
            if match:
                return parser(match)
        
        return None  # type: ignore
    
    async def create_reminder(
        self, user_id: str, message: str, trigger_time: datetime, repeat: Optional[str] = None
    ) -> Reminder:
        """リマインダーを作成"""
        reminder = Reminder(
            id=str(uuid.uuid4()),
            user_id=user_id,
            message=message,
            trigger_time=trigger_time.isoformat(),
            created_at=datetime.now().isoformat(),
            repeat=repeat,
            status='active'
        )
        
        self.reminders[reminder.id] = reminder
        self._save_reminders()
        
        logger.info(f"  ✅ Created reminder: {reminder.message} at {trigger_time}")
        
        return reminder
    
    async def get_user_reminders(self, user_id: str, status: str = 'active') -> List[Reminder]:
        """ユーザーのリマインダーを取得"""
        return [
            r for r in self.reminders.values()
            if r.user_id == user_id and r.status == status
        ]
    
    async def cancel_reminder(self, reminder_id: str) -> bool:
        """リマインダーをキャンセル"""
        if reminder_id in self.reminders:
            self.reminders[reminder_id].status = 'cancelled'
            self._save_reminders()
            logger.info(f"  ✅ Cancelled reminder: {reminder_id}")
            return True
        return False
    
    async def check_and_send_reminders(self):
        """リマインダーをチェックして送信（バックグラウンド）"""
        logger.info("⏰ Starting reminder check loop...")
        
        while self.running:
            try:
                now = datetime.now()
                
                for reminder in list(self.reminders.values()):
                    if reminder.status != 'active':
                        continue
                    
                    trigger_time = datetime.fromisoformat(reminder.trigger_time)
                    
                    # 時間になった
                    if now >= trigger_time:
                        await self._send_reminder(reminder)
                        
                        # 繰り返し設定
                        if reminder.repeat == 'daily':
                            # 次の日にスケジュール
                            new_trigger = trigger_time + timedelta(days=1)
                            reminder.trigger_time = new_trigger.isoformat()
                            logger.info(f"  🔄 Rescheduled daily reminder: {new_trigger}")
                        else:
                            # 完了
                            reminder.status = 'completed'
                        
                        self._save_reminders()
                
                # 30秒ごとにチェック
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"  ❌ Reminder check error: {e}")
                await asyncio.sleep(30)
    
    async def _send_reminder(self, reminder: Reminder):
        """リマインダーを送信"""
        try:
            if self.bot:
                # Telegramに送信
                message = f"""
⏰ **リマインダー**

{reminder.message}

📅 設定時刻: {datetime.fromisoformat(reminder.created_at).strftime('%Y-%m-%d %H:%M')}
"""
                
                # ボタン
                from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                
                keyboard = [
                    [
                        InlineKeyboardButton("✅ 完了", callback_data=f"reminder_done_{reminder.id}"),
                        InlineKeyboardButton("⏰ 5分延期", callback_data=f"reminder_snooze_{reminder.id}")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await self.bot.send_message(
                    chat_id=reminder.user_id,
                    text=message,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                
                logger.info(f"  ✅ Sent reminder to {reminder.user_id}: {reminder.message}")
            else:
                logger.warning("  ⚠️ Bot not available, cannot send reminder")
                
        except Exception as e:
            logger.error(f"  ❌ Failed to send reminder: {e}")
    
    async def snooze_reminder(self, reminder_id: str, minutes: int = 5):
        """リマインダーをスヌーズ"""
        if reminder_id in self.reminders:
            reminder = self.reminders[reminder_id]
            new_trigger = datetime.now() + timedelta(minutes=minutes)
            reminder.trigger_time = new_trigger.isoformat()
            self._save_reminders()
            logger.info(f"  ⏰ Snoozed reminder for {minutes} minutes: {reminder.message}")
            return True
        return False
    
    async def start(self):
        """バックグラウンドタスクを開始"""
        if not self.running:
            self.running = True
            self.check_task = asyncio.create_task(self.check_and_send_reminders())
            logger.info("  ✅ Reminder system started")
    
    async def stop(self):
        """バックグラウンドタスクを停止"""
        self.running = False
        if self.check_task:
            self.check_task.cancel()
            logger.info("  ✅ Reminder system stopped")
    
    def format_reminder_list(self, reminders: List[Reminder]) -> str:
        """リマインダーリストをフォーマット"""
        if not reminders:
            return "リマインダーはありません"
        
        text = "⏰ **アクティブなリマインダー**\n\n"
        
        for i, reminder in enumerate(reminders, 1):
            trigger_time = datetime.fromisoformat(reminder.trigger_time)
            time_diff = trigger_time - datetime.now()
            
            if time_diff.days > 0:
                time_str = f"{time_diff.days}日後"
            elif time_diff.seconds > 3600:
                time_str = f"{time_diff.seconds // 3600}時間後"
            else:
                time_str = f"{time_diff.seconds // 60}分後"
            
            repeat_str = " 🔄" if reminder.repeat else ""
            
            text += f"{i}. **{reminder.message}**{repeat_str}\n"
            text += f"   📅 {trigger_time.strftime('%m/%d %H:%M')} ({time_str})\n\n"
        
        return text


# テスト用
async def test_reminder_system():
    """リマインダーシステムのテスト"""
    system = ReminderSystem()
    
    print("\n" + "="*60)
    print("⏰ Reminder System - Test")
    print("="*60)
    
    # テスト1: リマインダー解析
    print("\n📝 Test 1: Parse reminder requests")
    
    test_texts = [
        "30分後にプレゼンの準備をリマインド",
        "明日10時に会議をリマインド",
        "毎日9時に日報をリマインド"
    ]
    
    for text in test_texts:
        result = system.parse_reminder_request(text)
        if result:
            print(f"  ✅ '{text}'")
            print(f"     → {result['message']} at {result['trigger_time'].strftime('%Y-%m-%d %H:%M')}")
        else:
            print(f"  ❌ '{text}' - 解析失敗")
    
    # テスト2: リマインダー作成
    print("\n📝 Test 2: Create reminder")
    
    reminder = await system.create_reminder(
        user_id="test_user",
        message="テストリマインダー",
        trigger_time=datetime.now() + timedelta(minutes=1)
    )
    
    print(f"  ✅ Created: {reminder.id}")
    print(f"     Message: {reminder.message}")
    print(f"     Trigger: {reminder.trigger_time}")
    
    # テスト3: リマインダー一覧
    print("\n📝 Test 3: List reminders")
    
    reminders = await system.get_user_reminders("test_user")
    print(f"  ✅ Found {len(reminders)} reminders")
    print(system.format_reminder_list(reminders))


if __name__ == '__main__':
    asyncio.run(test_reminder_system())



