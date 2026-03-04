#!/usr/bin/env python3
"""
📝 Trinity Obsidian Connector
Obsidianとの完全自動連携システム

機能:
- タスク自動保存
- デイリーノート自動生成
- メモ即時同期
- テンプレート管理
- リンク自動生成
- タグ管理
"""

import asyncio
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import re

# 設定
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class ObsidianConnector:
    """Obsidian自動連携システム"""
    
    def __init__(
        self,
        vault_path: str = "/root/obsidian_vault",
        daily_notes_path: str = "Daily Notes",
        tasks_path: str = "Tasks",
        templates_path: str = "Templates"
    ):
        """
        初期化
        
        Args:
            vault_path: Obsidian Vaultのパス
            daily_notes_path: デイリーノートのパス
            tasks_path: タスクのパス
            templates_path: テンプレートのパス
        """
        self.vault_path = Path(vault_path)
        self.daily_notes_path = self.vault_path / daily_notes_path
        self.tasks_path = self.vault_path / tasks_path
        self.templates_path = self.vault_path / templates_path
        
        # ディレクトリ作成
        self._ensure_directories()
        
        # 統計
        self.notes_created = 0
        self.tasks_created = 0
        self.daily_notes_created = 0
        
        logger.info(f"📝 Obsidian Connector initialized: {vault_path}")
    
    def _ensure_directories(self):
        """必要なディレクトリを作成"""
        for path in [self.daily_notes_path, self.tasks_path, self.templates_path]:
            path.mkdir(parents=True, exist_ok=True)
    
    def create_daily_note(self, date: Optional[datetime] = None) -> Path:
        """
        デイリーノート作成
        
        Args:
            date: 日付（省略時は今日）
            
        Returns:
            作成されたファイルのパス
        """
        date = date or datetime.now()
        filename = date.strftime("%Y-%m-%d") + ".md"
        filepath = self.daily_notes_path / filename
        
        if filepath.exists():
            logger.info(f"📄 Daily note already exists: {filename}")
            return filepath
        
        # テンプレート適用
        content = f"""# {date.strftime('%Y年%m月%d日')} ({self._get_weekday_jp(date)})

## ✅ 今日のタスク
- [ ] 

## 📅 今日の予定


## 📝 メモ


## 💡 アイデア


## 🎯 振り返り


---
作成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
タグ: #daily-note #{date.strftime('%Y')} #{date.strftime('%Y-%m')}
"""
        
        filepath.write_text(content, encoding='utf-8')
        self.daily_notes_created += 1
        logger.info(f"✅ Daily note created: {filename}")
        
        return filepath
    
    def add_task(
        self,
        title: str,
        description: Optional[str] = None,
        priority: str = "中",
        due_date: Optional[datetime] = None,
        tags: Optional[List[str]] = None
    ) -> Path:
        """
        タスクを追加
        
        Args:
            title: タスクタイトル
            description: 説明
            priority: 優先度（高/中/低）
            due_date: 締切
            tags: タグリスト
            
        Returns:
            作成されたファイルのパス
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"task_{timestamp}.md"
        filepath = self.tasks_path / filename
        
        # 優先度の絵文字
        priority_emoji = {
            "高": "🔴",
            "中": "🟡",
            "低": "🟢"
        }.get(priority, "⚪")
        
        # タグ処理
        tags = tags or []
        tags.append("task")
        tags_str = " ".join([f"#{tag}" for tag in tags])
        
        # コンテンツ作成
        content = f"""# {priority_emoji} {title}

## 📋 詳細
{description or "（説明なし）"}

## ⏰ 締切
{due_date.strftime('%Y-%m-%d %H:%M') if due_date else "未設定"}

## 📊 ステータス
- [ ] 未着手
- [ ] 進行中
- [ ] 完了

## 📝 メモ


---
作成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
優先度: {priority}
タグ: {tags_str}
"""
        
        filepath.write_text(content, encoding='utf-8')
        self.tasks_created += 1
        logger.info(f"✅ Task created: {filename}")
        
        # 今日のデイリーノートにも追加
        self._add_to_daily_note(f"- [ ] [[{filepath.stem}|{title}]] {priority_emoji}")
        
        return filepath
    
    def add_note(
        self,
        title: str,
        content: str,
        tags: Optional[List[str]] = None,
        folder: Optional[str] = None
    ) -> Path:
        """
        メモを追加
        
        Args:
            title: タイトル
            content: 内容
            tags: タグリスト
            folder: 保存フォルダ（省略時はルート）
            
        Returns:
            作成されたファイルのパス
        """
        # ファイル名生成（安全な文字のみ）
        safe_title = re.sub(r'[^\w\s-]', '', title).strip()
        safe_title = re.sub(r'[-\s]+', '-', safe_title)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_title}_{timestamp}.md"
        
        # 保存先決定
        if folder:
            save_path = self.vault_path / folder
            save_path.mkdir(parents=True, exist_ok=True)
        else:
            save_path = self.vault_path
        
        filepath = save_path / filename
        
        # タグ処理
        tags = tags or []
        tags_str = " ".join([f"#{tag}" for tag in tags])
        
        # コンテンツ作成
        full_content = f"""# {title}

{content}

---
作成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
タグ: {tags_str}
"""
        
        filepath.write_text(full_content, encoding='utf-8')
        self.notes_created += 1
        logger.info(f"✅ Note created: {filename}")
        
        return filepath
    
    def add_meeting_note(
        self,
        title: str,
        date: datetime,
        participants: List[str],
        agenda: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Path:
        """
        会議メモを追加
        
        Args:
            title: 会議タイトル
            date: 日時
            participants: 参加者リスト
            agenda: 議題
            notes: メモ
            
        Returns:
            作成されたファイルのパス
        """
        timestamp = date.strftime("%Y%m%d_%H%M")
        filename = f"meeting_{timestamp}.md"
        filepath = self.vault_path / "Meetings" / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # 参加者リスト
        participants_str = "\n".join([f"- {p}" for p in participants])
        
        content = f"""# 📅 {title}

## 📋 会議情報
- 日時: {date.strftime('%Y年%m月%d日 %H:%M')}
- 場所: 

## 👥 参加者
{participants_str}

## 📝 議題
{agenda or ""}

## 💬 議事メモ
{notes or ""}

## ✅ アクションアイテム
- [ ] 

## 📎 関連リンク


---
作成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
タグ: #meeting #{date.strftime('%Y')} #{date.strftime('%Y-%m')}
"""
        
        filepath.write_text(content, encoding='utf-8')
        logger.info(f"✅ Meeting note created: {filename}")
        
        return filepath
    
    def _add_to_daily_note(self, line: str, date: Optional[datetime] = None):
        """デイリーノートに行を追加"""
        daily_note = self.create_daily_note(date)
        
        # ファイル読み込み
        content = daily_note.read_text(encoding='utf-8')
        
        # タスクセクションを見つけて追加
        if "## ✅ 今日のタスク" in content:
            content = content.replace(
                "## ✅ 今日のタスク\n- [ ] ",
                f"## ✅ 今日のタスク\n{line}\n- [ ] "
            )
        else:
            content += f"\n{line}\n"
        
        daily_note.write_text(content, encoding='utf-8')
    
    def _get_weekday_jp(self, date: datetime) -> str:
        """日本語の曜日を取得"""
        weekdays = ["月", "火", "水", "木", "金", "土", "日"]
        return weekdays[date.weekday()]
    
    def search_notes(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        ノートを検索
        
        Args:
            query: 検索クエリ
            limit: 最大結果数
            
        Returns:
            検索結果のリスト
        """
        results = []
        
        for filepath in self.vault_path.rglob("*.md"):
            try:
                content = filepath.read_text(encoding='utf-8')
                
                if query.lower() in content.lower():
                    results.append({
                        "file": str(filepath.relative_to(self.vault_path)),
                        "title": filepath.stem,
                        "path": str(filepath),
                        "modified": datetime.fromtimestamp(filepath.stat().st_mtime)
                    })
                    
                    if len(results) >= limit:
                        break
            except Exception as e:
                logger.error(f"Search error in {filepath}: {e}")
        
        return results
    
    def get_recent_notes(self, limit: int = 10) -> List[Dict[str, Any]]:
        """最近のノートを取得"""
        notes = []
        
        for filepath in self.vault_path.rglob("*.md"):
            try:
                stat = filepath.stat()
                notes.append({
                    "file": str(filepath.relative_to(self.vault_path)),
                    "title": filepath.stem,
                    "path": str(filepath),
                    "modified": datetime.fromtimestamp(stat.st_mtime)
                })
            except Exception:
                pass
        
        # 更新日時でソート
        notes.sort(key=lambda x: x['modified'], reverse=True)
        
        return notes[:limit]
    
    def get_stats(self) -> Dict[str, Any]:
        """統計情報取得"""
        total_notes = len(list(self.vault_path.rglob("*.md")))
        
        return {
            "vault_path": str(self.vault_path),
            "total_notes": total_notes,
            "notes_created": self.notes_created,
            "tasks_created": self.tasks_created,
            "daily_notes_created": self.daily_notes_created
        }


# グローバルインスタンス
obsidian = ObsidianConnector()


# テスト＆デモ
async def demo_obsidian_connector():
    """Obsidian Connectorのデモ"""
    print("\n" + "="*60)
    print("📝 Trinity Obsidian Connector - Demo")
    print("="*60 + "\n")
    
    # 1. デイリーノート作成
    print("📅 Creating daily note...")
    daily_note = obsidian.create_daily_note()
    print(f"   ✅ Created: {daily_note.name}\n")
    
    # 2. タスク追加
    print("📋 Adding tasks...")
    task1 = obsidian.add_task(
        title="Trinity秘書システムのドキュメント作成",
        description="Markdownでわかりやすく書く",
        priority="高",
        due_date=datetime.now() + timedelta(days=1),
        tags=["trinity", "documentation"]
    )
    print(f"   ✅ Task 1: {task1.name}")
    
    task2 = obsidian.add_task(
        title="Telegram Botのテスト",
        description="実機でテストする",
        priority="中",
        tags=["trinity", "telegram", "test"]
    )
    print(f"   ✅ Task 2: {task2.name}\n")
    
    # 3. メモ追加
    print("📝 Adding notes...")
    note1 = obsidian.add_note(
        title="Trinity Boost Mode完了",
        content="""## 実装完了システム

1. Telegram Bot - スマホから秘書操作
2. 通知システム - Discord/Ntfy/Pushover統合
3. 音声システム - Whisper + TTS
4. n8n自動化 - ワークフロー自動化
5. Obsidian連携 - このシステム！

すべて順番に並行で一気に実装完了！✨
""",
        tags=["trinity", "achievement", "boost-mode"]
    )
    print(f"   ✅ Note 1: {note1.name}")
    
    # 4. 会議メモ追加
    print("📅 Adding meeting note...")
    meeting = obsidian.add_meeting_note(
        title="Trinity秘書レビュー会議",
        date=datetime.now(),
        participants=["Mana", "Trinity AI"],
        agenda="実装完了システムのレビューと今後の計画",
        notes="全システム正常稼働中。次はObsidian連携の強化。"
    )
    print(f"   ✅ Meeting: {meeting.name}\n")
    
    # 5. 検索テスト
    print("🔍 Searching notes...")
    results = obsidian.search_notes("Trinity", limit=5)
    print(f"   Found {len(results)} notes:")
    for r in results[:3]:
        print(f"   - {r['title']}")
    print()
    
    # 6. 最近のノート
    print("📊 Recent notes...")
    recent = obsidian.get_recent_notes(limit=5)
    for r in recent[:3]:
        print(f"   - {r['title']} ({r['modified'].strftime('%Y-%m-%d %H:%M')})")
    print()
    
    # 7. 統計
    print("📈 Statistics:")
    stats = obsidian.get_stats()
    print(f"   Total notes: {stats['total_notes']}")
    print(f"   Created (this session): {stats['notes_created']} notes, {stats['tasks_created']} tasks")
    print(f"   Daily notes: {stats['daily_notes_created']}")
    print(f"   Vault path: {stats['vault_path']}")
    
    print("\n" + "="*60)
    print("✨ Obsidian Connector Demo Complete!")
    print("="*60 + "\n")


if __name__ == '__main__':
    asyncio.run(demo_obsidian_connector())

