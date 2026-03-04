#!/usr/bin/env python3
"""
Obsidian自動同期システム
Cursorでの会話、タスク、メモを自動的にObsidianに保存
"""

from datetime import datetime
from pathlib import Path
import re

class ObsidianAutoSync:
    """Obsidian自動同期"""
    
    def __init__(self, vault_path="/root/obsidian_vault"):
        self.vault_path = Path(vault_path)
        self.vault_path.mkdir(exist_ok=True)
        
        # カテゴリ別フォルダ作成
        (self.vault_path / "Daily Notes").mkdir(exist_ok=True)
        (self.vault_path / "Conversations").mkdir(exist_ok=True)
        (self.vault_path / "Tasks").mkdir(exist_ok=True)
        (self.vault_path / "Ideas").mkdir(exist_ok=True)
        (self.vault_path / "Technical").mkdir(exist_ok=True)
        (self.vault_path / "Reports").mkdir(exist_ok=True)
        
    def save_conversation(self, title, content, tags=None):
        """会話を保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{self._sanitize_filename(title)}.md"
        filepath = self.vault_path / "Conversations" / filename
        
        # Markdown形式で保存
        markdown = self._create_markdown(title, content, tags, "conversation")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(markdown)
        
        print(f"✅ 会話を保存: {filepath}")
        return str(filepath)
    
    def create_daily_note(self, date=None):
        """デイリーノート作成"""
        if date is None:
            date = datetime.now()
        
        filename = date.strftime("%Y-%m-%d") + ".md"
        filepath = self.vault_path / "Daily Notes" / filename
        
        # デイリーノートテンプレート
        template = f"""# {date.strftime('%Y年%m月%d日 (%A)')}

## 📅 今日の予定
- 

## ✅ 完了したこと
- 

## 📝 メモ
- 

## 💡 アイデア
- 

## 📊 振り返り
### Good
- 

### Bad
- 

### Next
- 

---
作成: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Tags: #daily-note #{date.strftime('%Y-%m')}
"""
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(template)
        
        print(f"✅ デイリーノート作成: {filepath}")
        return str(filepath)
    
    def save_task(self, task_title, description="", due_date=None, priority="medium"):
        """タスクを保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{self._sanitize_filename(task_title)}.md"
        filepath = self.vault_path / "Tasks" / filename
        
        # タスクMarkdown
        markdown = f"""# {task_title}

## 📋 詳細
{description}

## ⏰ 期限
{due_date or "未設定"}

## 🎯 優先度
{priority}

## ✅ ステータス
- [ ] 未着手

## 📝 メモ
- 

---
作成: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Tags: #task #{priority}-priority
"""
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(markdown)
        
        print(f"✅ タスク保存: {filepath}")
        return str(filepath)
    
    def save_idea(self, idea_title, content):
        """アイデアを保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{self._sanitize_filename(idea_title)}.md"
        filepath = self.vault_path / "Ideas" / filename
        
        markdown = self._create_markdown(idea_title, content, ["idea"], "idea")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(markdown)
        
        print(f"✅ アイデア保存: {filepath}")
        return str(filepath)
    
    def save_technical_note(self, title, content, language=None):
        """技術メモを保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{self._sanitize_filename(title)}.md"
        filepath = self.vault_path / "Technical" / filename
        
        tags = ["technical"]
        if language:
            tags.append(language.lower())
        
        markdown = self._create_markdown(title, content, tags, "technical")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(markdown)
        
        print(f"✅ 技術メモ保存: {filepath}")
        return str(filepath)
    
    def _create_markdown(self, title, content, tags=None, category=""):
        """Markdown形式作成"""
        tags_str = " ".join([f"#{tag}" for tag in (tags or [])])
        
        markdown = f"""# {title}

{content}

---
作成: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
カテゴリ: {category}
Tags: {tags_str}
"""
        return markdown
    
    def _sanitize_filename(self, name):
        """ファイル名をサニタイズ"""
        # 使えない文字を削除
        name = re.sub(r'[<>:"/\\|?*]', '', name)
        # 50文字に制限
        return name[:50]
    
    def get_stats(self):
        """統計情報取得"""
        stats = {
            "conversations": len(list((self.vault_path / "Conversations").glob("*.md"))),
            "tasks": len(list((self.vault_path / "Tasks").glob("*.md"))),
            "ideas": len(list((self.vault_path / "Ideas").glob("*.md"))),
            "technical": len(list((self.vault_path / "Technical").glob("*.md"))),
            "daily_notes": len(list((self.vault_path / "Daily Notes").glob("*.md")))
        }
        return stats

def main():
    sync = ObsidianAutoSync()
    
    print("🚀 Obsidian自動同期システム テスト\n")
    
    # デイリーノート作成
    sync.create_daily_note()
    
    # テスト保存
    sync.save_conversation(
        "システム改善の会話",
        "今日はシステムを大幅に改善した。バックアップを80%削減し、ドキュメントを整理した。",
        ["system", "improvement"]
    )
    
    sync.save_task(
        "Brave Search設定確認",
        "Cursor再起動後にBrave Searchが動作するか確認",
        "2025-10-16",
        "high"
    )
    
    # 統計表示
    stats = sync.get_stats()
    print("\n📊 Obsidian統計:")
    print(f"  会話: {stats['conversations']}件")
    print(f"  タスク: {stats['tasks']}件")
    print(f"  アイデア: {stats['ideas']}件")
    print(f"  技術メモ: {stats['technical']}件")
    print(f"  デイリーノート: {stats['daily_notes']}件")
    print("\n📁 Vault: /root/obsidian_vault")

if __name__ == "__main__":
    main()

