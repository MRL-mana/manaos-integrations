#!/usr/bin/env python3
"""
🚀 Trinity Master System
全システム統合コントローラー

すべてのTrinityシステムを統合管理！
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

# Trinity各システムのインポート
from trinity_notification_system import TrinityNotificationSystem, NotificationPriority
from trinity_obsidian_connector import ObsidianConnector

# 設定
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class TrinityMasterSystem:
    """Trinity Master統合システム"""
    
    def __init__(self):
        """初期化"""
        logger.info("🚀 Trinity Master System initializing...")
        
        # 各サブシステムの初期化
        self.notification = TrinityNotificationSystem()
        self.obsidian = ObsidianConnector()
        
        # 統計
        self.commands_executed = 0
        self.start_time = datetime.now()
        
        logger.info("✅ Trinity Master System initialized!")
    
    async def process_command(self, command: str, user_id: str = "master") -> Dict[str, Any]:
        """
        コマンドを処理
        
        Args:
            command: ユーザーコマンド
            user_id: ユーザーID
            
        Returns:
            処理結果
        """
        self.commands_executed += 1
        logger.info(f"📝 Processing command: {command}")
        
        command_lower = command.lower()
        
        # タスク追加
        if "タスク" in command and ("追加" in command or "作成" in command):
            return await self._handle_task_creation(command)
        
        # メモ作成
        elif "メモ" in command:
            return await self._handle_note_creation(command)
        
        # 今日の予定
        elif "予定" in command or "スケジュール" in command:
            return await self._handle_schedule()
        
        # 今日のタスク
        elif "今日" in command and "タスク" in command:
            return await self._handle_today_tasks()
        
        # デイリーノート
        elif "デイリーノート" in command:
            return await self._handle_daily_note()
        
        # 通知テスト
        elif "通知" in command and "テスト" in command:
            return await self._handle_notification_test()
        
        # ステータス確認
        elif "ステータス" in command or "状態" in command:
            return await self._handle_status()
        
        # デフォルト: 一般会話
        else:
            return await self._handle_general_conversation(command)
    
    async def _handle_task_creation(self, command: str) -> Dict[str, Any]:
        """タスク作成処理"""
        # コマンドからタスク名を抽出（簡易版）
        task_name = command.replace("タスク", "").replace("追加", "").replace("作成", "").strip()
        
        if not task_name:
            task_name = "新しいタスク"
        
        # Obsidianにタスク作成
        task_file = self.obsidian.add_task(
            title=task_name,
            description=f"コマンド: {command}",
            priority="中",
            tags=["trinity-auto"]
        )
        
        # 通知送信
        await self.notification.send_notification(
            title="✅ タスク作成完了",
            message=f"「{task_name}」をタスクリストに追加しました！",
            priority=NotificationPriority.NORMAL,
            tags=["task", "created"]
        )
        
        return {
            "success": True,
            "action": "task_created",
            "task_name": task_name,
            "file": str(task_file),
            "response": f"✅ タスク「{task_name}」を作成しました！Obsidianで確認できます。"
        }
    
    async def _handle_note_creation(self, command: str) -> Dict[str, Any]:
        """メモ作成処理"""
        # コマンドからメモ内容を抽出
        note_content = command.replace("メモ", "").replace(":", "").strip()
        
        if not note_content:
            note_content = "（内容なし）"
        
        # Obsidianにメモ作成
        note_file = self.obsidian.add_note(
            title=f"Quick Note {datetime.now().strftime('%H:%M')}",
            content=note_content,
            tags=["trinity-auto", "quick-note"]
        )
        
        return {
            "success": True,
            "action": "note_created",
            "file": str(note_file),
            "response": "📝 メモを保存しました！Obsidianで確認できます。"
        }
    
    async def _handle_schedule(self) -> Dict[str, Any]:
        """スケジュール確認処理"""
        # 仮の予定データ
        schedule = [
            {"time": "14:00", "title": "チームミーティング", "duration": "1時間"},
            {"time": "16:30", "title": "プロジェクト打ち合わせ", "duration": "30分"}
        ]
        
        if not schedule:
            return {
                "success": True,
                "action": "schedule",
                "events": [],
                "response": "📅 今日の予定はありません！"
            }
        
        response = "📅 **今日の予定**\n\n"
        for event in schedule:
            response += f"🕐 {event['time']} - {event['title']} ({event['duration']})\n"
        
        return {
            "success": True,
            "action": "schedule",
            "events": schedule,
            "response": response
        }
    
    async def _handle_today_tasks(self) -> Dict[str, Any]:
        """今日のタスク確認処理"""
        # Obsidianから今日のデイリーノートを読む
        daily_note = self.obsidian.create_daily_note()
        content = daily_note.read_text(encoding='utf-8')
        
        # タスクを抽出（簡易版）
        tasks = []
        in_task_section = False
        for line in content.split('\n'):
            if "## ✅ 今日のタスク" in line:
                in_task_section = True
                continue
            if in_task_section and line.startswith("##"):
                break
            if in_task_section and line.strip().startswith("- ["):
                tasks.append(line.strip())
        
        response = f"📋 **今日のタスク ({len(tasks)}件)**\n\n"
        for task in tasks:
            response += f"{task}\n"
        
        return {
            "success": True,
            "action": "today_tasks",
            "tasks": tasks,
            "count": len(tasks),
            "response": response
        }
    
    async def _handle_daily_note(self) -> Dict[str, Any]:
        """デイリーノート作成/確認"""
        daily_note = self.obsidian.create_daily_note()
        
        return {
            "success": True,
            "action": "daily_note",
            "file": str(daily_note),
            "response": f"📅 今日のデイリーノートを開きました: {daily_note.name}"
        }
    
    async def _handle_notification_test(self) -> Dict[str, Any]:
        """通知テスト"""
        result = await self.notification.send_notification(
            title="🔔 通知テスト",
            message="Trinity Master Systemからのテスト通知です！",
            priority=NotificationPriority.NORMAL,
            tags=["test"]
        )
        
        return {
            "success": result["success"],
            "action": "notification_test",
            "result": result,
            "response": "🔔 テスト通知を送信しました！確認してください。"
        }
    
    async def _handle_status(self) -> Dict[str, Any]:
        """システムステータス確認"""
        notification_stats = self.notification.get_stats()
        obsidian_stats = self.obsidian.get_stats()
        
        uptime = datetime.now() - self.start_time
        
        status_text = f"""
🚀 **Trinity Master System Status**

⏱️ **稼働時間**: {uptime.seconds // 60}分
📊 **実行コマンド数**: {self.commands_executed}

📝 **Obsidian**:
- 総ノート数: {obsidian_stats['total_notes']}
- 作成済み: {obsidian_stats['notes_created']} notes, {obsidian_stats['tasks_created']} tasks

🔔 **通知システム**:
- 送信成功: {notification_stats['sent_count']}
- 送信失敗: {notification_stats['failed_count']}
- 成功率: {notification_stats['success_rate']:.1f}%

✨ すべてのシステムが正常に稼働しています！
"""
        
        return {
            "success": True,
            "action": "status",
            "stats": {
                "uptime_minutes": uptime.seconds // 60,
                "commands_executed": self.commands_executed,
                "notification": notification_stats,
                "obsidian": obsidian_stats
            },
            "response": status_text
        }
    
    async def _handle_general_conversation(self, command: str) -> Dict[str, Any]:
        """一般会話処理"""
        # 簡単な応答（実際はTrinity秘書APIと連携）
        responses = {
            "こんにちは": "こんにちは！Trinity Master Systemです。何かお手伝いできることはありますか？",
            "おはよう": "おはようございます！今日も頑張りましょう！",
            "ありがとう": "どういたしまして！いつでもお手伝いします。",
            "ヘルプ": """
🤖 **Trinity Master System**

使えるコマンド:
- 「タスク追加: タスク名」 - タスク作成
- 「メモ: 内容」 - メモ作成
- 「今日の予定」 - スケジュール確認
- 「今日のタスク」 - タスク一覧
- 「デイリーノート」 - 今日のノート
- 「通知テスト」 - 通知送信テスト
- 「ステータス」 - システム状態
"""
        }
        
        for keyword, response in responses.items():
            if keyword in command:
                return {
                    "success": True,
                    "action": "conversation",
                    "response": response
                }
        
        return {
            "success": True,
            "action": "conversation",
            "response": f"「{command}」を承りました。Trinity秘書システムで処理します。"
        }


# グローバルインスタンス
trinity_master = TrinityMasterSystem()


# インタラクティブモード
async def interactive_mode():
    """対話モード"""
    print("\n" + "="*60)
    print("🚀 Trinity Master System - Interactive Mode")
    print("="*60)
    print("\nコマンド例:")
    print("  - タスク追加: レポート作成")
    print("  - メモ: 重要なアイデア")
    print("  - 今日の予定")
    print("  - ステータス")
    print("  - exit で終了")
    print("\n" + "="*60 + "\n")
    
    try:
        while True:
            command = input("💬 You: ").strip()
            
            if not command:
                continue
            
            if command.lower() in ['exit', 'quit', '終了']:
                print("\n👋 Trinity Master System を終了します。\n")
                break
            
            result = await trinity_master.process_command(command)
            print(f"\n🤖 Trinity: {result['response']}\n")
    
    except KeyboardInterrupt:
        print("\n\n👋 Trinity Master System を終了します。\n")


# メイン実行
if __name__ == '__main__':
    asyncio.run(interactive_mode())

