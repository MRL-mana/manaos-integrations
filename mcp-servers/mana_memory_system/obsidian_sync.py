#!/usr/bin/env python3
"""
Obsidian自動同期システム
ホットメモリからObsidianへの自動転送

転送ルール:
- 重要度7以上: 即座に転送
- 重要度7-8: 毎時間バッチ処理
- 重要度9以上: リアルタイム転送
"""

import json
import sqlite3
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import logging
import re

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/root/.mana_memory/obsidian_sync.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 設定
MEMORY_DIR = Path("/root/.mana_memory")
DB_PATH = MEMORY_DIR / "hot_memory.db"
OBSIDIAN_VAULT = Path("/root/Obsidian/ManaOS_Chronicle")
OBSIDIAN_MEMORIES = OBSIDIAN_VAULT / "Memories"
OBSIDIAN_DAILY = OBSIDIAN_MEMORIES / "Daily"
OBSIDIAN_CONVERSATIONS = OBSIDIAN_MEMORIES / "Conversations"
OBSIDIAN_KNOWLEDGE = OBSIDIAN_MEMORIES / "Knowledge"
OBSIDIAN_PROJECTS = OBSIDIAN_MEMORIES / "Projects"
SYNC_STATE_FILE = MEMORY_DIR / "obsidian_sync_state.json"


class ObsidianSync:
    """Obsidian自動同期システム"""

    def __init__(self):
        self._ensure_directories()
        self.sync_state = self._load_sync_state()

    def _ensure_directories(self):
        """Obsidianディレクトリ構造を確保"""
        for dir_path in [OBSIDIAN_MEMORIES, OBSIDIAN_DAILY, OBSIDIAN_CONVERSATIONS,
                        OBSIDIAN_KNOWLEDGE, OBSIDIAN_PROJECTS]:
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"ディレクトリ確認: {dir_path}")

    def _load_sync_state(self) -> Dict:
        """同期状態を読み込み"""
        if SYNC_STATE_FILE.exists():
            try:
                with open(SYNC_STATE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"同期状態読み込みエラー: {e}")
        return {
            'last_sync_time': None,
            'synced_memory_ids': [],
            'last_daily_note_date': None
        }

    def _save_sync_state(self):
        """同期状態を保存"""
        try:
            with open(SYNC_STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.sync_state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"同期状態保存エラー: {e}")

    def _get_memories_to_sync(self, importance_min: int = 7,
                              realtime: bool = False) -> List[Dict]:
        """同期対象の記憶を取得"""
        if not DB_PATH.exists():
            logger.warning("データベースが存在しません")
            return []

        try:
            conn = sqlite3.connect(str(DB_PATH))
            conn.row_factory = sqlite3.Row

            # 既に同期済みのIDを除外
            synced_ids = self.sync_state.get('synced_memory_ids', [])

            if synced_ids:
                placeholders = ','.join(['?'] * len(synced_ids))
                query = f"""
                    SELECT * FROM memories
                    WHERE importance >= ?
                    AND id NOT IN ({placeholders})
                    ORDER BY importance DESC, created_at DESC
                """
                params = [importance_min] + synced_ids
            else:
                query = """
                    SELECT * FROM memories
                    WHERE importance >= ?
                    ORDER BY importance DESC, created_at DESC
                """
                params = [importance_min]

            # リアルタイムモードの場合は最新10件のみ
            if realtime:
                query += " LIMIT 10"

            rows = conn.execute(query, params).fetchall()
            memories = [dict(row) for row in rows]

            conn.close()
            return memories
        except Exception as e:
            logger.error(f"記憶取得エラー: {e}")
            return []

    def _get_conversations_to_sync(self, importance_min: int = 7) -> List[Dict]:
        """同期対象の会話を取得"""
        if not DB_PATH.exists():
            return []

        try:
            conn = sqlite3.connect(str(DB_PATH))
            conn.row_factory = sqlite3.Row

            query = """
                SELECT * FROM conversations
                WHERE importance >= ?
                ORDER BY timestamp DESC
                LIMIT 50
            """
            rows = conn.execute(query, [importance_min]).fetchall()
            conversations = [dict(row) for row in rows]

            conn.close()
            return conversations
        except Exception as e:
            logger.error(f"会話取得エラー: {e}")
            return []

    def _generate_markdown(self, memory: Dict, file_type: str = "memory") -> str:
        """Markdownを生成（PIIマスク対応）"""
        created_at = memory.get('created_at', datetime.now().isoformat())
        try:
            dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            date_str = dt.strftime('%Y-%m-%d')
            time_str = dt.strftime('%H:%M:%S')
        except IOError as e:
            date_str = datetime.now().strftime('%Y-%m-%d')
            time_str = datetime.now().strftime('%H:%M:%S')

        # PIIマスク
        content = memory.get('content', '')
        importance = memory.get('importance', 5)
        category = memory.get('category', 'general')

        try:
            sys.path.insert(0, '/root/.mana_memory')
            from pii_mask import mask_memory_for_obsidian
            content, is_masked = mask_memory_for_obsidian(content, importance, category)
            if is_masked:
                logger.debug("PIIマスク適用")
        except Exception as e:
            logger.debug(f"PIIマスクスキップ: {e}")

        # フロントマター
        frontmatter = f"""---
created: {created_at}
importance: {importance}
category: {category}
source: {memory.get('source', 'unknown')}
---

"""

        # タイトル生成
        title = self._extract_title(content)

        # タグ生成
        tags = self._generate_tags(memory)

        # リンク生成
        links = self._generate_links(memory)

        # 本文
        body = f"# {title}\n\n"
        body += f"{content}\n\n"

        # メタデータ
        if memory.get('metadata'):
            try:
                metadata = json.loads(memory['metadata']) if isinstance(memory['metadata'], str) else memory['metadata']
                if metadata:
                    body += "## 📝 メタデータ\n\n"
                    for key, value in metadata.items():
                        body += f"- **{key}**: {value}\n"
                    body += "\n"
            except Exception as e:
                pass

        # フッター
        footer = f"\n---\n"
        footer += f"作成: {date_str} {time_str}\n"
        if tags:
            footer += f"Tags: {tags}\n"
        if links:
            footer += f"関連: {links}\n"

        return frontmatter + body + footer

    def _extract_title(self, content: str, max_length: int = 50) -> str:
        """タイトルを抽出"""
        if not content:
            return "無題の記憶"

        # 最初の行をタイトル候補に
        lines = content.split('\n')
        title_candidate = lines[0].strip()

        # 長すぎる場合は切り詰め
        if len(title_candidate) > max_length:
            title_candidate = title_candidate[:max_length] + "..."

        # Markdown記号を除去
        title_candidate = re.sub(r'[#*_`\[\]]', '', title_candidate)

        return title_candidate or "無題の記憶"

    def _generate_tags(self, memory: Dict) -> str:
        """タグを生成"""
        tags = []

        # 重要度タグ
        importance = memory.get('importance', 5)
        if importance >= 9:
            tags.append("#important")
        elif importance >= 7:
            tags.append("#significant")

        # カテゴリタグ
        category = memory.get('category')
        if category:
            tags.append(f"#{category}")

        # ソースタグ
        source = memory.get('source')
        if source:
            tags.append(f"#{source}")

        # タイプタグ
        tags.append("#memory")

        return " ".join(tags)

    def _generate_links(self, memory: Dict) -> str:
        """リンクを生成"""
        links = []

        category = memory.get('category')
        if category:
            links.append(f"[[{category}]]")

        return " ".join(links)

    def _get_file_path(self, memory: Dict, file_type: str = "memory") -> Path:
        """ファイルパスを生成"""
        created_at = memory.get('created_at', datetime.now().isoformat())
        try:
            dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            date_str = dt.strftime('%Y%m%d')
            time_str = dt.strftime('%H%M%S')
        except IOError as e:
            date_str = datetime.now().strftime('%Y%m%d')
            time_str = datetime.now().strftime('%H%M%S')

        # ファイル名生成
        content = memory.get('content', '')
        title = self._extract_title(content, max_length=30)
        safe_title = re.sub(r'[^\w\s-]', '', title).strip()
        safe_title = re.sub(r'[-\s]+', '_', safe_title)

        filename = f"{date_str}_{time_str}_{safe_title}.md"

        # カテゴリ別ディレクトリ
        category = memory.get('category', 'general')
        if category == 'project':
            dir_path = OBSIDIAN_PROJECTS
        elif category == 'knowledge' or category == 'learning':
            dir_path = OBSIDIAN_KNOWLEDGE
        else:
            dir_path = OBSIDIAN_MEMORIES

        return dir_path / filename

    def sync_memory(self, memory: Dict) -> bool:
        """記憶をObsidianに同期"""
        try:
            # Markdown生成
            markdown = self._generate_markdown(memory)

            # ファイルパス生成
            file_path = self._get_file_path(memory)

            # 重複チェック
            if file_path.exists():
                logger.debug(f"ファイルが既に存在します: {file_path}")
                return True

            # ファイル書き込み
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(markdown)

            logger.info(f"✅ Obsidianに同期: {file_path.name}")

            # 同期状態を更新
            memory_id = memory.get('id')
            if memory_id:
                if 'synced_memory_ids' not in self.sync_state:
                    self.sync_state['synced_memory_ids'] = []
                if memory_id not in self.sync_state['synced_memory_ids']:
                    self.sync_state['synced_memory_ids'].append(memory_id)

            return True
        except Exception as e:
            logger.error(f"同期エラー: {e}")
            return False

    def sync_conversation(self, conversation: Dict) -> bool:
        """会話をObsidianに同期"""
        try:
            # 会話をMarkdown形式に変換
            timestamp = conversation.get('timestamp', datetime.now().isoformat())
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                date_str = dt.strftime('%Y-%m-%d')
                time_str = dt.strftime('%H:%M:%S')
            except Exception as e:
                date_str = datetime.now().strftime('%Y-%m-%d')
                time_str = datetime.now().strftime('%H:%M:%S')

            markdown = f"""---
created: {timestamp}
importance: {conversation.get('importance', 5)}
emotion: {conversation.get('emotion', 'neutral')}
---

# 会話 - {date_str} {time_str}

## ユーザー
{conversation.get('user_message', '')}

## アシスタント
{conversation.get('assistant_message', '')}

---
作成: {date_str} {time_str}
Tags: #conversation #memory
"""

            # ファイルパス生成
            filename = f"{date_str.replace('-', '')}_{time_str.replace(':', '')}_conversation.md"
            file_path = OBSIDIAN_CONVERSATIONS / filename

            # 重複チェック
            if file_path.exists():
                logger.debug(f"会話ファイルが既に存在します: {file_path}")
                return True

            # ファイル書き込み
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(markdown)

            logger.info(f"✅ 会話をObsidianに同期: {file_path.name}")
            return True
        except Exception as e:
            logger.error(f"会話同期エラー: {e}")
            return False

    def sync_daily_note(self, date: Optional[str] = None) -> bool:
        """日次ノートを生成"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')

        # 既に今日のノートがあるか確認
        if self.sync_state.get('last_daily_note_date') == date:
            logger.debug(f"今日の日次ノートは既に作成済み: {date}")
            return True

        try:
            # 今日の記憶を取得
            memories = self._get_memories_to_sync(importance_min=5)
            today_memories = [m for m in memories if m.get('created_at', '').startswith(date)]

            # 今日の会話を取得
            conversations = self._get_conversations_to_sync(importance_min=5)
            today_conversations = [c for c in conversations if c.get('timestamp', '').startswith(date)]

            # Markdown生成
            markdown = f"""---
created: {date}
type: daily-note
tags: [daily, memory, {date.replace('-', '-')}]
---

# 📅 {date} - Mana日次ノート

## ✅ 今日の記憶

"""

            if today_memories:
                for mem in today_memories[:10]:  # 最新10件
                    markdown += f"- [[{self._extract_title(mem.get('content', ''), 30)}]] - 重要度: {mem.get('importance', 5)}\n"
            else:
                markdown += "- 今日の記憶はありません\n"

            markdown += "\n## 💬 今日の会話\n\n"

            if today_conversations:
                for conv in today_conversations[:5]:  # 最新5件
                    markdown += f"- {conv.get('user_message', '')[:50]}...\n"
            else:
                markdown += "- 今日の会話はありません\n"

            markdown += f"\n---\n作成: {date}\n"

            # ファイル書き込み
            filename = f"{date.replace('-', '')}_daily.md"
            file_path = OBSIDIAN_DAILY / filename

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(markdown)

            logger.info(f"✅ 日次ノート作成: {file_path.name}")

            # 同期状態を更新
            self.sync_state['last_daily_note_date'] = date

            return True
        except Exception as e:
            logger.error(f"日次ノート作成エラー: {e}")
            return False

    def sync_all(self, realtime: bool = False):
        """全同期実行"""
        logger.info("🔄 Obsidian自動同期開始")

        # 重要度7以上の記憶を同期
        importance_min = 9 if realtime else 7
        memories = self._get_memories_to_sync(importance_min=importance_min, realtime=realtime)

        logger.info(f"📊 同期対象: {len(memories)}件の記憶")

        synced_count = 0
        for memory in memories:
            if self.sync_memory(memory):
                synced_count += 1

        # 重要度7以上の会話を同期
        conversations = self._get_conversations_to_sync(importance_min=importance_min)
        logger.info(f"📊 同期対象: {len(conversations)}件の会話")

        for conversation in conversations:
            if self.sync_conversation(conversation):
                synced_count += 1

        # 日次ノート生成
        self.sync_daily_note()

        # 同期状態を保存
        self.sync_state['last_sync_time'] = datetime.now().isoformat()
        self._save_sync_state()

        logger.info(f"✅ 同期完了: {synced_count}件同期しました")
        return synced_count


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Obsidian自動同期システム')
    parser.add_argument('--realtime', action='store_true', help='リアルタイムモード（重要度9以上のみ）')
    parser.add_argument('--daily-only', action='store_true', help='日次ノートのみ生成')
    args = parser.parse_args()

    sync = ObsidianSync()

    if args.daily_only:
        sync.sync_daily_note()
    else:
        sync.sync_all(realtime=args.realtime)


if __name__ == '__main__':
    main()


