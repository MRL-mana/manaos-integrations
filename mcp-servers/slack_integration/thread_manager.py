#!/usr/bin/env python3
"""
Slackスレッド管理システム
会話の追跡・コンテキスト保持
"""

import json
import requests
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any


class SlackThreadManager:
    """Slackスレッド管理"""
    
    def __init__(self, slack_service_url: str = "http://localhost:5020"):
        self.slack_url = slack_service_url
        self.threads_file = Path("/root/slack_integration/data/threads.json")
        self.threads_file.parent.mkdir(parents=True, exist_ok=True)
        self.threads = self._load_threads()
    
    def _load_threads(self) -> dict:
        """スレッド情報をロード"""
        if self.threads_file.exists():
            with open(self.threads_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _save_threads(self):
        """スレッド情報を保存"""
        with open(self.threads_file, 'w', encoding='utf-8') as f:
            json.dump(self.threads, f, ensure_ascii=False, indent=2)
    
    def create_thread(
        self,
        channel: str,
        initial_message: str,
        thread_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        新しいスレッドを作成
        
        Args:
            channel: チャンネル名
            initial_message: 最初のメッセージ
            thread_id: スレッドID（省略時は自動生成）
        
        Returns:
            {"thread_id": "xxx", "ts": "xxx", "success": True}
        """
        # 最初のメッセージを送信
        response = requests.post(
            f"{self.slack_url}/send",
            json={"channel": channel, "text": initial_message},
            timeout=5
        )
        
        result = response.json()
        
        if result.get("success"):
            ts = result.get("ts")
            thread_id = thread_id or f"thread_{int(datetime.now().timestamp())}"
            
            # スレッド情報を記録
            self.threads[thread_id] = {
                "channel": channel,
                "thread_ts": ts,
                "created_at": datetime.now().isoformat(),
                "messages": [
                    {
                        "ts": ts,
                        "text": initial_message,
                        "timestamp": datetime.now().isoformat()
                    }
                ]
            }
            self._save_threads()
            
            return {
                "thread_id": thread_id,
                "ts": ts,
                "success": True
            }
        
        return result
    
    def reply_to_thread(
        self,
        thread_id: str,
        message: str
    ) -> Dict[str, Any]:
        """
        スレッドに返信
        
        Args:
            thread_id: スレッドID
            message: 返信メッセージ
        
        Returns:
            送信結果
        """
        if thread_id not in self.threads:
            return {"success": False, "error": "Thread not found"}
        
        thread_info = self.threads[thread_id]
        channel = thread_info["channel"]
        thread_ts = thread_info["thread_ts"]
        
        # スレッドに返信
        response = requests.post(
            f"{self.slack_url}/send",
            json={
                "channel": channel,
                "text": message,
                "thread_ts": thread_ts
            },
            timeout=5
        )
        
        result = response.json()
        
        if result.get("success"):
            # メッセージを記録
            self.threads[thread_id]["messages"].append({
                "ts": result.get("ts"),
                "text": message,
                "timestamp": datetime.now().isoformat()
            })
            self._save_threads()
        
        return result
    
    def get_thread_history(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """スレッドの履歴を取得"""
        return self.threads.get(thread_id)
    
    def list_active_threads(self) -> List[Dict[str, Any]]:
        """アクティブなスレッド一覧"""
        return [
            {
                "thread_id": tid,
                "channel": info["channel"],
                "created_at": info["created_at"],
                "message_count": len(info["messages"])
            }
            for tid, info in self.threads.items()
        ]
    
    def close_thread(self, thread_id: str, closing_message: Optional[str] = None):
        """
        スレッドをクローズ
        
        Args:
            thread_id: スレッドID
            closing_message: 最後に送信するメッセージ
        """
        if thread_id not in self.threads:
            return {"success": False, "error": "Thread not found"}
        
        if closing_message:
            self.reply_to_thread(thread_id, closing_message)
        
        # アーカイブに移動
        self.threads[thread_id]["closed_at"] = datetime.now().isoformat()
        self.threads[thread_id]["status"] = "closed"
        self._save_threads()
        
        return {"success": True, "thread_id": thread_id}


class ConversationManager:
    """会話コンテキスト管理"""
    
    def __init__(self):
        self.thread_manager = SlackThreadManager()
        self.contexts = {}
    
    def start_conversation(
        self,
        channel: str,
        topic: str,
        user: str
    ) -> str:
        """
        会話を開始
        
        Returns:
            thread_id
        """
        thread_id = f"conv_{topic}_{int(datetime.now().timestamp())}"
        
        initial_message = f"🗣️ **{topic}** について会話を開始しました\n_by @{user}_"
        
        result = self.thread_manager.create_thread(
            channel=channel,
            initial_message=initial_message,
            thread_id=thread_id
        )
        
        if result.get("success"):
            self.contexts[thread_id] = {
                "topic": topic,
                "user": user,
                "started_at": datetime.now().isoformat(),
                "turns": 0
            }
        
        return thread_id
    
    def continue_conversation(
        self,
        thread_id: str,
        message: str,
        speaker: str = "system"
    ):
        """会話を続ける"""
        if thread_id in self.contexts:
            self.contexts[thread_id]["turns"] += 1
        
        formatted_message = f"**{speaker}**: {message}"
        return self.thread_manager.reply_to_thread(thread_id, formatted_message)
    
    def end_conversation(
        self,
        thread_id: str,
        summary: Optional[str] = None
    ):
        """会話を終了"""
        if thread_id in self.contexts:
            turns = self.contexts[thread_id]["turns"]
            closing_msg = summary or f"✅ 会話終了（{turns}ターン）"
            
            self.thread_manager.close_thread(thread_id, closing_msg)
            del self.contexts[thread_id]


# ===== 使用例 =====
if __name__ == '__main__':
    # スレッド管理のテスト
    print("📝 スレッド管理システムのテスト\n")
    
    manager = SlackThreadManager()
    
    # 1. 新しいスレッドを作成
    print("1. スレッド作成...")
    result = manager.create_thread(
        channel="general",
        initial_message="🧵 新しい会話スレッドを開始しました！"
    )
    thread_id = result.get("thread_id")
    print(f"   ✅ Thread ID: {thread_id}\n")
    
    # 2. スレッドに返信
    print("2. スレッドに返信...")
    manager.reply_to_thread(thread_id, "これは2番目のメッセージです")  # type: ignore
    manager.reply_to_thread(thread_id, "これは3番目のメッセージです")  # type: ignore
    print("   ✅ 返信完了\n")
    
    # 3. スレッド履歴を取得
    print("3. スレッド履歴:")
    history = manager.get_thread_history(thread_id)  # type: ignore
    for i, msg in enumerate(history["messages"], 1):  # type: ignore[index]
        print(f"   {i}. {msg['text'][:50]}...")
    print()
    
    # 4. アクティブスレッド一覧
    print("4. アクティブスレッド一覧:")
    active = manager.list_active_threads()
    for thread in active:
        print(f"   - {thread['thread_id']}: {thread['message_count']}件のメッセージ")
    print()
    
    # 5. 会話管理のテスト
    print("5. 会話管理テスト...")
    conv = ConversationManager()
    conv_id = conv.start_conversation(
        channel="general",
        topic="ManaOS機能改善",
        user="mana"
    )
    
    conv.continue_conversation(conv_id, "GPU統合について検討中です", "mana")
    conv.continue_conversation(conv_id, "RunPod APIの実装を進めています", "system")
    conv.end_conversation(conv_id, "📋 決定事項: RunPod統合を優先実装")
    print("   ✅ 会話完了\n")
    
    print("✨ テスト完了！Slackを確認してください。")

