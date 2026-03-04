#!/usr/bin/env python3
"""
Trinity v2.0 Auto Agent Watcher
各エージェントが自動でメッセージを監視して実行
"""

import sys
import time
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'core'))

from db_manager import TrinityDB

logger = logging.getLogger(__name__)


class AutoAgentWatcher:
    """エージェント自動監視"""
    
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.db = TrinityDB()
        self.last_check_time = time.time()
        
        logger.info(f"{agent_name} auto-watcher initialized")
    
    def check_for_messages(self):
        """新着メッセージをチェック"""
        messages = self.db.get_messages(to_agent=self.agent_name, unread_only=True)
        
        if messages:
            print(f"\n📬 {len(messages)} new message(s) for {self.agent_name}:")
            print("=" * 60)
            
            for msg in messages:
                print(f"\n📨 From: {msg['from_agent']}")
                print(f"💬 Message:")
                print(f"   {msg['message']}")
                print(f"⏰ Time: {msg['timestamp']}")
                print("-" * 60)
                
                # 既読にする
                self.db.mark_message_read(msg['id'])
            
            return messages
        
        return []
    
    def check_for_tasks(self):
        """新規タスクをチェック"""
        tasks = self.db.get_tasks(status='todo', assigned_to=self.agent_name)
        
        if tasks:
            print(f"\n📋 {len(tasks)} task(s) assigned to {self.agent_name}:")
            print("=" * 60)
            
            for task in tasks[:5]:  # 最新5件表示
                print(f"\n🎯 {task['id']}: {task['title']}")
                print(f"   Priority: {task['priority']}")
                print(f"   Estimated: {task.get('estimated_hours', '?')}h")
                
                if task.get('description'):
                    print(f"   Description: {task['description'][:80]}...")
                
                print("-" * 60)
            
            return tasks
        
        return []
    
    def watch(self, interval: int = 5):
        """継続監視"""
        print(f"\n👀 {self.agent_name} Auto-Watcher Started")
        print("=" * 60)
        print(f"Watching for messages and tasks...")
        print(f"Check interval: {interval} seconds")
        print("Press Ctrl+C to stop")
        print("=" * 60)
        
        try:
            while True:
                # メッセージチェック
                messages = self.check_for_messages()
                
                # タスクチェック
                tasks = self.check_for_tasks()
                
                if messages or tasks:
                    print(f"\n✨ Action required for {self.agent_name}!")
                    print("Please review the above and take action.")
                
                # 待機
                time.sleep(interval)
        
        except KeyboardInterrupt:
            print(f"\n\n✅ {self.agent_name} watcher stopped")


# ==================== 各エージェント用のエントリーポイント ====================

def watch_remi():
    """Remi監視"""
    watcher = AutoAgentWatcher('Remi')
    watcher.watch()


def watch_luna():
    """Luna監視"""
    watcher = AutoAgentWatcher('Luna')
    watcher.watch()


def watch_mina():
    """Mina監視"""
    watcher = AutoAgentWatcher('Mina')
    watcher.watch()


def watch_aria():
    """Aria監視"""
    watcher = AutoAgentWatcher('Aria')
    watcher.watch()


# ==================== メイン実行 ====================

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Trinity Auto Agent Watcher')
    parser.add_argument('agent', choices=['Remi', 'Luna', 'Mina', 'Aria'], help='Agent name')
    parser.add_argument('--interval', type=int, default=5, help='Check interval (seconds)')
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.WARNING)
    
    watcher = AutoAgentWatcher(args.agent)
    watcher.watch(interval=args.interval)











