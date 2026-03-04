#!/usr/bin/env python3
"""
AI文脈記憶システム
会話の文脈を記憶して賢くなる
"""

from datetime import datetime
from pathlib import Path
import json

class AIContextMemory:
    """AI文脈記憶"""
    
    def __init__(self):
        self.memory_file = Path("/root/.ai_context_memory.json")
        self.conversation_history = []
        self.user_preferences = {}
        self.load_memory()
        
    def load_memory(self):
        """メモリ読み込み"""
        if self.memory_file.exists():
            with open(self.memory_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.conversation_history = data.get("conversations", [])
                self.user_preferences = data.get("preferences", {})
    
    def save_memory(self):
        """メモリ保存"""
        data = {
            "conversations": self.conversation_history[-100:],  # 最新100件
            "preferences": self.user_preferences,
            "last_updated": datetime.now().isoformat()
        }
        
        with open(self.memory_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def add_conversation(self, user_message, ai_response, context=None):
        """会話を記憶"""
        conversation = {
            "timestamp": datetime.now().isoformat(),
            "user": user_message,
            "assistant": ai_response,
            "context": context or {}
        }
        
        self.conversation_history.append(conversation)
        self.save_memory()
        
        # 学習
        self._learn_from_conversation(user_message, ai_response)
    
    def _learn_from_conversation(self, user_message, ai_response):
        """会話から学習"""
        # よく使うキーワード
        keywords = ["予定", "メール", "タスク", "X280", "最適化"]
        
        for keyword in keywords:
            if keyword in user_message:
                count = self.user_preferences.get(f"keyword_{keyword}", 0)
                self.user_preferences[f"keyword_{keyword}"] = count + 1
        
        # 時間帯パターン
        hour = datetime.now().hour
        time_slot = f"hour_{hour}"
        count = self.user_preferences.get(time_slot, 0)
        self.user_preferences[time_slot] = count + 1
    
    def get_context_suggestions(self):
        """文脈に基づく提案"""
        suggestions = []
        
        # よく使う機能
        top_keywords = sorted(
            [(k, v) for k, v in self.user_preferences.items() if k.startswith("keyword_")],
            key=lambda x: x[1],
            reverse=True
        )[:3]
        
        for keyword, count in top_keywords:
            key = keyword.replace("keyword_", "")
            suggestions.append(f"{key}を確認")
        
        # 時間帯パターン
        current_hour = datetime.now().hour
        if 8 <= current_hour < 12:
            suggestions.insert(0, "朝のサマリーを見る")
        elif 18 <= current_hour < 24:
            suggestions.insert(0, "今日の振り返り")
        
        return suggestions
    
    def get_relevant_history(self, query, limit=5):
        """関連する過去の会話を検索"""
        relevant = []
        
        for conv in reversed(self.conversation_history):
            if query.lower() in conv["user"].lower() or query.lower() in conv["assistant"].lower():
                relevant.append(conv)
                if len(relevant) >= limit:
                    break
        
        return relevant
    
    def get_summary(self):
        """記憶サマリー"""
        total_conversations = len(self.conversation_history)
        
        # よく使う機能Top 5
        top_features = sorted(
            [(k.replace("keyword_", ""), v) for k, v in self.user_preferences.items() if k.startswith("keyword_")],
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        summary = f"""
📊 AI文脈記憶 サマリー

総会話数: {total_conversations}
記録期間: {self._get_memory_period()}

よく使う機能:
"""
        for feature, count in top_features:
            summary += f"  • {feature}: {count}回\n"
        
        summary += """
現在の提案:
"""
        for sug in self.get_context_suggestions():
            summary += f"  • {sug}\n"
        
        return summary
    
    def _get_memory_period(self):
        """記憶期間"""
        if not self.conversation_history:
            return "なし"
        
        first = datetime.fromisoformat(self.conversation_history[0]["timestamp"])
        last = datetime.fromisoformat(self.conversation_history[-1]["timestamp"])
        days = (last - first).days
        
        return f"{days}日間"

def main():
    memory = AIContextMemory()
    
    print("🧠 AI文脈記憶システム\n")
    
    # テスト会話追加
    memory.add_conversation(
        "今日の予定を教えて",
        "今日の予定は3件です...",
        {"time": "morning"}
    )
    
    memory.add_conversation(
        "メールをチェックして",
        "未読メールは12件です...",
        {"time": "morning"}
    )
    
    # サマリー表示
    print(memory.get_summary())
    
    # 提案
    print("\n💡 おすすめアクション:")
    for sug in memory.get_context_suggestions():
        print(f"  • {sug}")
    
    print("\n✅ テスト完了")
    print(f"📁 メモリ: {memory.memory_file}")

if __name__ == "__main__":
    main()

