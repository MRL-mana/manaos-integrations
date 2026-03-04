#!/usr/bin/env python3
"""
Mana Knowledge Hub - 知識統合システム
Obsidian + タスク管理 + AI記憶 + 会話履歴
"""

import json
from datetime import datetime
from pathlib import Path
import re

class ManaKnowledgeHub:
    """統合知識管理システム"""
    
    def __init__(self):
        # Obsidian Vault
        self.vault = Path("/root/obsidian_vault")
        self.vault.mkdir(exist_ok=True)
        
        # サブディレクトリ
        self.daily_notes = self.vault / "Daily Notes"
        self.conversations = self.vault / "Conversations"
        self.tasks_dir = self.vault / "Tasks"
        self.ideas = self.vault / "Ideas"
        
        for d in [self.daily_notes, self.conversations, self.tasks_dir, self.ideas]:
            d.mkdir(exist_ok=True)
        
        # タスクDB
        self.tasks_db = Path("/root/.mana_tasks.json")
        
        # AI記憶
        self.memory_db = Path("/root/.ai_context_memory.json")
        
        self.load_all()
    
    def load_all(self):
        """全データ読み込み"""
        # タスク読み込み
        if self.tasks_db.exists():
            with open(self.tasks_db, 'r') as f:
                self.tasks = json.load(f)
        else:
            self.tasks = []
        
        # 記憶読み込み
        if self.memory_db.exists():
            with open(self.memory_db, 'r') as f:
                memory_data = json.load(f)
                self.conversations_history = memory_data.get("conversations", [])
                self.preferences = memory_data.get("preferences", {})
        else:
            self.conversations_history = []
            self.preferences = {}
    
    def save_all(self):
        """全データ保存"""
        # タスク保存
        with open(self.tasks_db, 'w') as f:
            json.dump(self.tasks, f, indent=2, ensure_ascii=False)
        
        # 記憶保存
        memory_data = {
            "conversations": self.conversations_history[-100:],
            "preferences": self.preferences,
            "last_updated": datetime.now().isoformat()
        }
        with open(self.memory_db, 'w') as f:
            json.dump(memory_data, f, indent=2, ensure_ascii=False)
    
    def save_to_obsidian(self, content, title=None, category="Conversations"):
        """Obsidianに保存（統合メソッド）"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        title = title or f"Note_{timestamp}"
        filename = f"{timestamp}_{self._sanitize(title)}.md"
        
        target_dir = self.vault / category
        target_dir.mkdir(exist_ok=True)
        
        markdown = f"""# {title}

{content}

---
作成: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
カテゴリ: {category}
"""
        
        filepath = target_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(markdown)
        
        return str(filepath)
    
    def create_daily_note(self):
        """デイリーノート作成"""
        date = datetime.now()
        filename = date.strftime("%Y-%m-%d.md")
        filepath = self.daily_notes / filename
        
        if filepath.exists():
            return str(filepath)
        
        template = f"""# {date.strftime('%Y年%m月%d日 (%A)')}

## 📅 予定
{self._get_today_events()}

## ✅ タスク
{self._get_today_tasks()}

## 📝 メモ
- 

## 💡 学んだこと
- 

---
作成: {datetime.now().strftime('%H:%M:%S')}
"""
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(template)
        
        return str(filepath)
    
    def add_task(self, title, deadline=None, priority=None):
        """タスク追加（統合）"""
        task = {
            "id": datetime.now().strftime("%Y%m%d%H%M%S"),
            "title": title,
            "deadline": deadline,
            "priority": priority or self._calc_priority(deadline),
            "status": "pending",
            "created_at": datetime.now().isoformat()
        }
        
        self.tasks.append(task)
        self.save_all()
        
        # Obsidianにも保存
        self.save_to_obsidian(
            f"**優先度**: {task['priority']}\n**期限**: {deadline or '未設定'}",
            title,
            "Tasks"
        )
        
        return task
    
    def get_dashboard(self):
        """統合ダッシュボード"""
        pending_tasks = [t for t in self.tasks if t['status'] == 'pending']
        
        # 優先度別
        urgent = [t for t in pending_tasks if t['priority'] == 'urgent']
        high = [t for t in pending_tasks if t['priority'] == 'high']
        
        dashboard = f"""
🌟 Mana Knowledge Hub Dashboard
{'='*60}

📅 今日: {datetime.now().strftime('%Y年%m月%d日')}

✅ タスク状況:
  🔴 緊急: {len(urgent)}件
  🟡 重要: {len(high)}件
  📊 合計: {len(pending_tasks)}件

📝 Obsidian統計:
  会話: {len(list(self.conversations.glob('*.md')))}件
  デイリーノート: {len(list(self.daily_notes.glob('*.md')))}件
  
🧠 AI記憶:
  総会話: {len(self.conversations_history)}件
  よく使う機能: {self._get_top_features()}
"""
        return dashboard
    
    def _get_today_events(self):
        """今日の予定（簡易版）"""
        return "- 燃えるゴミ\n- （Google Calendarと統合予定）"
    
    def _get_today_tasks(self):
        """今日のタスク"""
        pending = [t for t in self.tasks if t['status'] == 'pending'][:5]
        if not pending:
            return "- なし"
        return "\n".join([f"- [ ] {t['title']}" for t in pending])
    
    def _calc_priority(self, deadline):
        """優先度計算"""
        if not deadline:
            return "medium"
        # 簡易実装
        return "high"
    
    def _get_top_features(self):
        """よく使う機能"""
        top = sorted(
            [(k.replace("keyword_", ""), v) for k, v in self.preferences.items() if k.startswith("keyword_")],
            key=lambda x: x[1],
            reverse=True
        )[:3]
        return ", ".join([f[0] for f in top]) if top else "データ収集中"
    
    def _sanitize(self, name):
        """ファイル名サニタイズ"""
        return re.sub(r'[<>:"/\\|?*]', '', name)[:50]

# グローバルインスタンス
knowledge_hub = ManaKnowledgeHub()

def main():
    print("🧠 Mana Knowledge Hub Master\n")
    print(knowledge_hub.get_dashboard())
    
    print("\n✅ 統合知識管理システム準備完了")
    print("📁 Obsidian Vault: /root/obsidian_vault/")
    print("📊 タスクDB: /root/.mana_tasks.json")
    print("🧠 記憶DB: /root/.ai_context_memory.json")

if __name__ == "__main__":
    main()

