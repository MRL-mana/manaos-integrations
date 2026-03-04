#!/usr/bin/env python3
"""
🤝 Trinity Memory Hub
トリニティ全体で記憶を共有するハブシステム

機能:
- テレグラム ⇄ Trinity Master ⇄ ManaOS v3の記憶同期
- Obsidianとの双方向連携
- AI Learning Systemへの保存
- 共有メモリストア管理
"""

import asyncio
import logging
import json
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TrinityMemoryHub:
    """トリニティ全体で記憶を共有するハブ"""
    
    def __init__(self):
        # 接続先エンドポイント
        self.trinity_master = "http://localhost:8087"
        self.manaos_orchestrator = "http://localhost:9200"
        self.manaos_ingestor = "http://localhost:9204"
        self.ai_learning = "http://localhost:8600"
        
        # Obsidian Vault
        self.obsidian_vault = Path('/root/obsidian_vault')
        self.obsidian_shared_memory = self.obsidian_vault / 'Trinity Shared Memory'
        
        # 共有メモリストア（メモリ内キャッシュ）
        self.shared_memories = {
            'mana_preferences': {},      # Manaの好み
            'mana_schedule': {},          # スケジュール
            'mana_tasks': {},             # タスク
            'mana_context': {},           # 現在の状況
            'conversation_summary': {},   # 会話サマリー
            'important_info': []          # 重要情報
        }
        
        # 共有メモリファイル（永続化）
        self.memory_file = Path('/root/.trinity_shared_memory.json')
        
        # 初期化
        self._load_shared_memory()
        self._ensure_obsidian_dirs()
        
        logger.info("🤝 Trinity Memory Hub initialized")
    
    def _load_shared_memory(self):
        """共有メモリをファイルから読み込み"""
        if self.memory_file.exists():
            try:
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    self.shared_memories = json.load(f)
                logger.info("  ✅ Loaded shared memory from file")
            except Exception as e:
                logger.warning(f"  ⚠️ Failed to load shared memory: {e}")
    
    def _save_shared_memory(self):
        """共有メモリをファイルに保存"""
        try:
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(self.shared_memories, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"  ⚠️ Failed to save shared memory: {e}")
    
    def _ensure_obsidian_dirs(self):
        """Obsidianディレクトリの作成"""
        self.obsidian_shared_memory.mkdir(exist_ok=True, parents=True)
    
    async def sync_memory_to_trinity(self, memory: Dict[str, Any]):
        """
        テレグラムでの会話をトリニティ全員に共有
        
        Args:
            memory: 共有する記憶
                {
                    'type': 'conversation' | 'task' | 'preference' | 'schedule',
                    'content': '内容',
                    'user_id': 'ユーザーID',
                    'timestamp': 'タイムスタンプ',
                    'emotion': '感情',
                    'importance': 1-10
                }
        """
        logger.info(f"🔄 Syncing memory to Trinity: {memory.get('type', 'unknown')}")
        
        memory_type = memory.get('type', 'conversation')
        
        # 1. Trinity Master Systemに送信
        await self._notify_trinity_master(memory)
        
        # 2. ManaOS v3のRemi/Luna/Minaに送信
        await self._notify_manaos_trinity(memory)
        
        # 3. Obsidianに構造化して保存
        await self._save_to_obsidian(memory)
        
        # 4. AI Learning Systemに保存
        await self._save_to_learning(memory)
        
        # 5. ローカル共有メモリに追加
        self._update_local_memory(memory)
        
        logger.info("  ✅ Memory synced to all Trinity systems")
    
    async def _notify_trinity_master(self, memory: Dict[str, Any]):
        """Trinity Master Systemに通知"""
        try:
            response = requests.post(
                f"{self.trinity_master}/api/memory/sync",
                json=memory,
                timeout=5
            )
            
            if response.status_code == 200:
                logger.info("    ✅ Trinity Master notified")
            else:
                logger.warning(f"    ⚠️ Trinity Master sync failed: {response.status_code}")
        
        except Exception as e:
            logger.warning(f"    ⚠️ Trinity Master not available: {e}")
    
    async def _notify_manaos_trinity(self, memory: Dict[str, Any]):
        """ManaOS v3に通知（Ingestor経由）"""
        try:
            response = requests.post(
                f"{self.manaos_ingestor}/ingest",
                json={
                    'type': 'trinity_shared_memory',
                    'source': 'telegram_bot',
                    'data': memory
                },
                timeout=5
            )
            
            if response.status_code == 200:
                logger.info("    ✅ ManaOS v3 notified")
            else:
                logger.warning(f"    ⚠️ ManaOS v3 sync failed: {response.status_code}")
        
        except Exception as e:
            logger.warning(f"    ⚠️ ManaOS v3 not available: {e}")
    
    async def _save_to_obsidian(self, memory: Dict[str, Any]):
        """Obsidianに保存"""
        try:
            memory_type = memory.get('type', 'conversation')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # メモリタイプごとにファイルを分ける
            if memory_type == 'conversation':
                file_path = self.obsidian_shared_memory / f"conversation_{timestamp}.md"
            elif memory_type == 'task':
                file_path = self.obsidian_vault / 'Tasks' / f"task_{timestamp}.md"
            elif memory_type == 'preference':
                file_path = self.obsidian_shared_memory / "preferences.md"
            else:
                file_path = self.obsidian_shared_memory / f"{memory_type}_{timestamp}.md"
            
            # Markdown形式で保存
            content = self._format_memory_as_markdown(memory)
            
            # ファイル書き込み
            file_path.parent.mkdir(exist_ok=True, parents=True)
            
            if memory_type == 'preference':
                # 好みは追記モード
                with open(file_path, 'a', encoding='utf-8') as f:
                    f.write(content)
            else:
                # その他は新規作成
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            
            logger.info(f"    ✅ Saved to Obsidian: {file_path.name}")
        
        except Exception as e:
            logger.warning(f"    ⚠️ Obsidian save failed: {e}")
    
    def _format_memory_as_markdown(self, memory: Dict[str, Any]) -> str:
        """記憶をMarkdown形式に変換"""
        timestamp = memory.get('timestamp', datetime.now().isoformat())
        memory_type = memory.get('type', 'conversation')
        content = memory.get('content', '')
        emotion = memory.get('emotion', 'neutral')
        importance = memory.get('importance', 5)
        
        md = f"""---
type: {memory_type}
timestamp: {timestamp}
emotion: {emotion}
importance: {importance}
---

# {memory_type.capitalize()}

## 内容
{content}

## メタデータ
- タイムスタンプ: {timestamp}
- 感情: {emotion}
- 重要度: {'⭐' * importance}

"""
        return md
    
    async def _save_to_learning(self, memory: Dict[str, Any]):
        """AI Learning Systemに保存"""
        try:
            content = memory.get('content', '')
            memory_type = memory.get('type', 'conversation')
            user_id = memory.get('user_id', 'telegram')
            importance = memory.get('importance', 5)
            
            response = requests.post(
                f"{self.ai_learning}/store",
                json={
                    'content': content,
                    'category': f'telegram_{user_id}',
                    'tags': ['trinity_shared', memory_type, memory.get('emotion', 'neutral')],
                    'importance': importance
                },
                timeout=5
            )
            
            if response.status_code == 200:
                logger.info("    ✅ Saved to AI Learning System")
            else:
                logger.warning(f"    ⚠️ AI Learning System save failed: {response.status_code}")
        
        except Exception as e:
            logger.warning(f"    ⚠️ AI Learning System not available: {e}")
    
    def _update_local_memory(self, memory: Dict[str, Any]):
        """ローカル共有メモリを更新"""
        memory_type = memory.get('type', 'conversation')
        
        if memory_type == 'preference':
            # 好みを記録
            key = memory.get('key', 'unknown')
            self.shared_memories['mana_preferences'][key] = memory.get('content', '')
        
        elif memory_type == 'task':
            # タスクを記録
            task_id = memory.get('task_id', datetime.now().isoformat())
            self.shared_memories['mana_tasks'][task_id] = memory
        
        elif memory_type == 'schedule':
            # スケジュールを記録
            event_id = memory.get('event_id', datetime.now().isoformat())
            self.shared_memories['mana_schedule'][event_id] = memory
        
        elif memory_type == 'conversation':
            # 会話サマリーを更新
            today = datetime.now().strftime('%Y-%m-%d')
            if today not in self.shared_memories['conversation_summary']:
                self.shared_memories['conversation_summary'][today] = []
            
            self.shared_memories['conversation_summary'][today].append({
                'timestamp': memory.get('timestamp', ''),
                'content': memory.get('content', '')[:100],  # 最初の100文字
                'emotion': memory.get('emotion', 'neutral')
            })
        
        # 重要情報を記録
        if memory.get('importance', 0) >= 8:
            self.shared_memories['important_info'].append(memory)
            # 最新100件のみ保持
            self.shared_memories['important_info'] = self.shared_memories['important_info'][-100:]
        
        # ファイルに保存
        self._save_shared_memory()
    
    async def retrieve_shared_context(self, user_id: str = 'telegram') -> Dict[str, Any]:
        """他のトリニティ達が持っている情報を取得"""
        logger.info("🔍 Retrieving shared context from all Trinity systems...")
        
        context = {
            'timestamp': datetime.now().isoformat(),
            'master': {},
            'manaos': {},
            'obsidian': {},
            'local': self.shared_memories
        }
        
        # Trinity Master Systemから
        try:
            response = requests.get(
                f"{self.trinity_master}/api/context",
                timeout=5
            )
            if response.status_code == 200:
                context['master'] = response.json()
                logger.info("  ✅ Retrieved from Trinity Master")
        except Exception as e:
            logger.warning(f"  ⚠️ Trinity Master context retrieval failed: {e}")
        
        # ManaOS v3から
        try:
            response = requests.get(
                f"{self.manaos_orchestrator}/context",
                timeout=5
            )
            if response.status_code == 200:
                context['manaos'] = response.json()
                logger.info("  ✅ Retrieved from ManaOS v3")
        except Exception as e:
            logger.warning(f"  ⚠️ ManaOS v3 context retrieval failed: {e}")
        
        # Obsidianから最近の情報
        context['obsidian'] = await self._get_recent_obsidian_info()
        
        logger.info("✅ Shared context retrieved")
        
        return context
    
    async def _get_recent_obsidian_info(self) -> Dict[str, Any]:
        """Obsidianから最近の情報を取得"""
        info = {
            'recent_tasks': [],
            'recent_notes': [],
            'daily_note_today': None
        }
        
        try:
            # 今日のデイリーノート
            today = datetime.now().strftime('%Y-%m-%d')
            daily_note = self.obsidian_vault / 'Daily Notes' / f'{today}.md'
            
            if daily_note.exists():
                with open(daily_note, 'r', encoding='utf-8') as f:
                    info['daily_note_today'] = f.read()
            
            # 最近のタスク（過去7日間）
            tasks_dir = self.obsidian_vault / 'Tasks'
            if tasks_dir.exists():
                recent_tasks = sorted(
                    tasks_dir.glob('*.md'),
                    key=lambda x: x.stat().st_mtime,
                    reverse=True
                )[:5]
                
                for task_file in recent_tasks:
                    with open(task_file, 'r', encoding='utf-8') as f:
                        info['recent_tasks'].append({
                            'file': task_file.name,
                            'content': f.read()[:200]  # 最初の200文字
                        })
            
            # 最近の共有メモリ
            if self.obsidian_shared_memory.exists():
                recent_memory = sorted(
                    self.obsidian_shared_memory.glob('*.md'),
                    key=lambda x: x.stat().st_mtime,
                    reverse=True
                )[:3]
                
                for memory_file in recent_memory:
                    with open(memory_file, 'r', encoding='utf-8') as f:
                        info['recent_notes'].append({
                            'file': memory_file.name,
                            'content': f.read()[:200]
                        })
        
        except Exception as e:
            logger.warning(f"  ⚠️ Obsidian info retrieval failed: {e}")
        
        return info
    
    def get_mana_preferences(self) -> Dict[str, str]:
        """Manaの好みを取得"""
        return self.shared_memories.get('mana_preferences', {})
    
    def get_conversation_summary(self, date: Optional[str] = None) -> List[Dict]:
        """会話サマリーを取得"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        return self.shared_memories.get('conversation_summary', {}).get(date, [])
    
    def get_important_info(self, limit: int = 10) -> List[Dict]:
        """重要情報を取得"""
        return self.shared_memories.get('important_info', [])[-limit:]


# テスト用
async def test_memory_hub():
    """メモリハブのテスト"""
    hub = TrinityMemoryHub()
    
    print("\n" + "="*60)
    print("Trinity Memory Hub - Test")
    print("="*60)
    
    # テスト1: メモリ同期
    print("\n📝 Test 1: Memory sync")
    test_memory = {
        'type': 'conversation',
        'content': 'テレグラムボットのテスト会話です',
        'user_id': 'test_user',
        'timestamp': datetime.now().isoformat(),
        'emotion': 'happy',
        'importance': 7
    }
    
    await hub.sync_memory_to_trinity(test_memory)
    print("✅ Memory sync completed")
    
    # テスト2: 共有コンテキスト取得
    print("\n🔍 Test 2: Retrieve shared context")
    context = await hub.retrieve_shared_context()
    print("✅ Context retrieved:")
    print(f"  - Preferences: {len(context['local']['mana_preferences'])} items")
    print(f"  - Important info: {len(context['local']['important_info'])} items")
    print(f"  - Recent Obsidian tasks: {len(context['obsidian']['recent_tasks'])} items")


if __name__ == '__main__':
    asyncio.run(test_memory_hub())



