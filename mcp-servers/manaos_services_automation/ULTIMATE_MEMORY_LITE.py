#!/usr/bin/env python3
"""
🚀 ULTIMATE MEMORY SYSTEM LITE - 軽量版（即時起動）
NumPy問題を回避し、既存システムを統合

使い方:
    python3 ULTIMATE_MEMORY_LITE.py
"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

class UltimateMemoryLite:
    """
    軽量版統合記憶システム
    
    機能:
    1. 全システム横断検索（軽量版）
    2. スマート保存
    3. 統合ダッシュボード
    """
    
    def __init__(self):
        print("🚀 Ultimate Memory System LITE 起動中...")
        
        # データベースパス
        self.dbs = {
            'ai_learning': '/root/ai_learning.db',
            'knowledge_hub': '/root/.mana_tasks.json',
            'context_memory': '/root/.ai_context_memory.json',
            'trinity_shared': '/root/.trinity_shared_memory.json',
        }
        
        # Obsidian Vault
        self.obsidian_vault = Path('/root/obsidian_vault')
        self.obsidian_vault.mkdir(exist_ok=True)
        
        # 統計
        self.stats = {}
        self._update_stats()
        
        print("✅ Ultimate Memory System LITE 準備完了")
        print(f"📊 総記憶数: {self.stats.get('total_memories', 0):,}件")
    
    def _update_stats(self):
        """統計情報を更新"""
        self.stats = {
            'ai_learning_count': 0,
            'knowledge_hub_count': 0,
            'trinity_memory_count': 0,
            'obsidian_count': 0,
            'context_memory_count': 0
        }
        
        try:
            # AI Learning SQLite
            if Path(self.dbs['ai_learning']).exists():
                conn = sqlite3.connect(self.dbs['ai_learning'])
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM knowledge")
                self.stats['ai_learning_count'] = cursor.fetchone()[0]
                conn.close()
        except sqlite3.Error:
            pass
        
        try:
            # Knowledge Hub
            if Path(self.dbs['knowledge_hub']).exists():
                with open(self.dbs['knowledge_hub'], 'r') as f:
                    tasks = json.load(f)
                    self.stats['knowledge_hub_count'] = len(tasks) if isinstance(tasks, list) else 0
        except sqlite3.Error:
            pass
        
        try:
            # Trinity Memory
            if Path(self.dbs['trinity_shared']).exists():
                with open(self.dbs['trinity_shared'], 'r') as f:
                    memory = json.load(f)
                    self.stats['trinity_memory_count'] = len(memory.get('important_info', []))
        except sqlite3.Error:
            pass
        
        try:
            # Context Memory
            if Path(self.dbs['context_memory']).exists():
                with open(self.dbs['context_memory'], 'r') as f:
                    context = json.load(f)
                    self.stats['context_memory_count'] = len(context.get('conversations', []))
        except sqlite3.Error:
            pass
        
        try:
            # Obsidian
            if self.obsidian_vault.exists():
                self.stats['obsidian_count'] = len(list(self.obsidian_vault.rglob('*.md')))
        except sqlite3.Error:
            pass
        
        # 合計
        self.stats['total_memories'] = sum([
            self.stats['ai_learning_count'],
            self.stats['knowledge_hub_count'],
            self.stats['trinity_memory_count'],
            self.stats['context_memory_count'],
            self.stats['obsidian_count']
        ])
    
    def unified_search(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """全システム横断検索"""
        print(f"\n🔍 横断検索: '{query}'")
        print("=" * 60)
        
        results = {
            'query': query,
            'timestamp': datetime.now().isoformat(),
            'sources': {}
        }
        
        # 1. AI Learning (SQLite直接検索)
        print("  📚 AI Learning System...")
        try:
            ai_results = self._search_ai_learning(query, limit)
            results['sources']['ai_learning'] = {
                'count': len(ai_results),
                'results': ai_results
            }
            print(f"    ✅ {len(ai_results)}件")
        except Exception as e:
            results['sources']['ai_learning'] = {'count': 0, 'error': str(e)}
            print(f"    ⚠️ {e}")
        
        # 2. Knowledge Hub
        print("  📝 Knowledge Hub...")
        try:
            kb_results = self._search_json(self.dbs['knowledge_hub'], query, limit, 'title')
            results['sources']['knowledge_hub'] = {
                'count': len(kb_results),
                'results': kb_results
            }
            print(f"    ✅ {len(kb_results)}件")
        except Exception as e:
            results['sources']['knowledge_hub'] = {'count': 0, 'error': str(e)}
            print(f"    ⚠️ {e}")
        
        # 3. Trinity Memory
        print("  🤝 Trinity Memory...")
        try:
            trinity_results = self._search_trinity(query, limit)
            results['sources']['trinity_memory'] = {
                'count': len(trinity_results),
                'results': trinity_results
            }
            print(f"    ✅ {len(trinity_results)}件")
        except Exception as e:
            results['sources']['trinity_memory'] = {'count': 0, 'error': str(e)}
            print(f"    ⚠️ {e}")
        
        # 4. Context Memory
        print("  🧠 Context Memory...")
        try:
            context_results = self._search_context_memory(query, limit)
            results['sources']['context_memory'] = {
                'count': len(context_results),
                'results': context_results
            }
            print(f"    ✅ {len(context_results)}件")
        except Exception as e:
            results['sources']['context_memory'] = {'count': 0, 'error': str(e)}
            print(f"    ⚠️ {e}")
        
        # 5. Obsidian
        print("  📔 Obsidian Vault...")
        try:
            obsidian_results = self._search_obsidian(query, limit)
            results['sources']['obsidian'] = {
                'count': len(obsidian_results),
                'results': obsidian_results
            }
            print(f"    ✅ {len(obsidian_results)}件")
        except Exception as e:
            results['sources']['obsidian'] = {'count': 0, 'error': str(e)}
            print(f"    ⚠️ {e}")
        
        total_hits = sum([s.get('count', 0) for s in results['sources'].values()])
        results['total_hits'] = total_hits
        
        print(f"\n✅ 総ヒット数: {total_hits}件")
        print("=" * 60)
        
        return results
    
    def _search_ai_learning(self, query: str, limit: int) -> List[Dict]:
        """AI Learning SQLiteを直接検索"""
        results = []
        if not Path(self.dbs['ai_learning']).exists():
            return results
        
        try:
            conn = sqlite3.connect(self.dbs['ai_learning'])
            cursor = conn.cursor()
            
            # LIKE検索（ベクトル検索なし）
            cursor.execute("""
                SELECT id, content, title, category, importance, created_at
                FROM knowledge
                WHERE content LIKE ? OR title LIKE ?
                LIMIT ?
            """, (f'%{query}%', f'%{query}%', limit))
            
            for row in cursor.fetchall():
                results.append({
                    'id': row[0],
                    'content': row[1][:200],
                    'title': row[2],
                    'category': row[3],
                    'importance': row[4],
                    'created_at': row[5]
                })
            
            conn.close()
        except Exception as e:
            print(f"      エラー: {e}")
        
        return results
    
    def _search_json(self, filepath: str, query: str, limit: int, search_field: str) -> List[Dict]:
        """JSON generic search"""
        results = []
        if not Path(filepath).exists():
            return results
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, list):
                items = data
            else:
                items = []
            
            query_lower = query.lower()
            for item in items:
                if search_field in item and query_lower in str(item[search_field]).lower():
                    results.append(item)
                    if len(results) >= limit:
                        break
        except Exception:
            pass
        
        return results
    
    def _search_trinity(self, query: str, limit: int) -> List[Dict]:
        """Trinity Memory検索"""
        results = []
        if not Path(self.dbs['trinity_shared']).exists():
            return results
        
        try:
            with open(self.dbs['trinity_shared'], 'r', encoding='utf-8') as f:
                memory = json.load(f)
            
            query_lower = query.lower()
            for info in memory.get('important_info', []):
                if query_lower in str(info.get('content', '')).lower():
                    results.append(info)
                    if len(results) >= limit:
                        break
        except sqlite3.Error:
            pass
        
        return results
    
    def _search_context_memory(self, query: str, limit: int) -> List[Dict]:
        """Context Memory検索"""
        results = []
        if not Path(self.dbs['context_memory']).exists():
            return results
        
        try:
            with open(self.dbs['context_memory'], 'r', encoding='utf-8') as f:
                context = json.load(f)
            
            query_lower = query.lower()
            for conv in context.get('conversations', []):
                user_msg = str(conv.get('user', '')).lower()
                ai_msg = str(conv.get('assistant', '')).lower()
                
                if query_lower in user_msg or query_lower in ai_msg:
                    results.append(conv)
                    if len(results) >= limit:
                        break
        except Exception:
            pass
        
        return results
    
    def _search_obsidian(self, query: str, limit: int) -> List[Dict]:
        """Obsidian検索"""
        results = []
        if not self.obsidian_vault.exists():
            return results
        
        try:
            query_lower = query.lower()
            for md_file in self.obsidian_vault.rglob('*.md'):
                try:
                    with open(md_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    if query_lower in content.lower():
                        results.append({
                            'file': md_file.name,
                            'path': str(md_file),
                            'preview': content[:150]
                        })
                        
                        if len(results) >= limit:
                            break
                except IOError:
                    continue
        except IOError:
            pass
        
        return results
    
    def smart_store(self, content: str, title: str = None, importance: int = 5, 
                    tags: List[str] = None, category: str = None) -> Dict:
        """スマート保存"""
        print(f"\n💾 スマート保存: '{content[:50]}...'")
        print(f"   重要度: {importance}/10")
        
        results = {
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'saved_to': []
        }
        
        # AI Learning (SQLite直接保存)
        if importance >= 5:
            try:
                knowledge_id = self._save_to_ai_learning(content, title, importance, tags, category)
                results['saved_to'].append(f'AI Learning (ID: {knowledge_id})')
                print(f"   ✅ AI Learning: ID {knowledge_id}")
            except Exception as e:
                print(f"   ⚠️ AI Learning: {e}")
        
        # Trinity Memory (重要度8以上)
        if importance >= 8:
            try:
                self._save_to_trinity(content, importance)
                results['saved_to'].append('Trinity Memory')
                print("   ✅ Trinity Memory")
            except Exception as e:
                print(f"   ⚠️ Trinity Memory: {e}")
        
        # Obsidian (重要度8以上)
        if importance >= 8:
            try:
                filename = self._save_to_obsidian(content, title)
                results['saved_to'].append(f'Obsidian ({filename})')
                print(f"   ✅ Obsidian: {filename}")
            except Exception as e:
                print(f"   ⚠️ Obsidian: {e}")
        
        print(f"✅ 保存完了: {len(results['saved_to'])}箇所")
        self._update_stats()
        
        return results
    
    def _save_to_ai_learning(self, content: str, title: str, importance: int, 
                            tags: List[str], category: str) -> int:
        """AI Learning SQLiteに直接保存（ベクトル化なし）"""
        conn = sqlite3.connect(self.dbs['ai_learning'])
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        tags_str = json.dumps(tags) if tags else None
        
        cursor.execute("""
            INSERT INTO knowledge 
            (content, title, tags, category, importance, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (content, title, tags_str, category, importance, now, now))
        
        knowledge_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return knowledge_id
    
    def _save_to_trinity(self, content: str, importance: int):
        """Trinity Memory保存"""
        filepath = Path(self.dbs['trinity_shared'])
        
        if filepath.exists():
            with open(filepath, 'r') as f:
                memory = json.load(f)
        else:
            memory = {'important_info': []}
        
        memory['important_info'].append({
            'content': content,
            'importance': importance,
            'timestamp': datetime.now().isoformat()
        })
        
        memory['important_info'] = memory['important_info'][-100:]
        
        with open(filepath, 'w') as f:
            json.dump(memory, f, ensure_ascii=False, indent=2)
    
    def _save_to_obsidian(self, content: str, title: str = None) -> str:
        """Obsidian保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        title = title or f"Memory_{timestamp}"
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '_', '-'))[:50]
        filename = f"{timestamp}_{safe_title}.md"
        
        filepath = self.obsidian_vault / "Shared Memory" / filename
        filepath.parent.mkdir(exist_ok=True, parents=True)
        
        markdown = f"""# {title}

{content}

---
作成: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(markdown)
        
        return filename
    
    def get_dashboard(self) -> str:
        """ダッシュボード表示"""
        self._update_stats()
        
        return f"""
{'='*70}
🌟 ULTIMATE MEMORY SYSTEM LITE - ダッシュボード
{'='*70}

📊 記憶統計
{'─'*70}
  AI Learning System    : {self.stats['ai_learning_count']:>6}件
  Knowledge Hub (Tasks) : {self.stats['knowledge_hub_count']:>6}件
  Trinity Shared Memory : {self.stats['trinity_memory_count']:>6}件
  Context Memory (会話) : {self.stats['context_memory_count']:>6}件
  Obsidian Vault        : {self.stats['obsidian_count']:>6}件
  {'─'*70}
  📈 総記憶数            : {self.stats['total_memories']:>6}件

💡 クイックアクション
{'─'*70}
  検索: memory.unified_search("キーワード")
  保存: memory.smart_store("内容", importance=8)

⏱️  最終更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*70}
"""


def main():
    print("""
╔════════════════════════════════════════════════════════════════╗
║       🚀 ULTIMATE MEMORY SYSTEM LITE - DEMO                    ║
║       軽量版・即時起動可能                                      ║
╚════════════════════════════════════════════════════════════════╝
    """)
    
    memory = UltimateMemoryLite()
    
    # ダッシュボード
    print(memory.get_dashboard())
    
    # デモ1: 検索
    print("\n📝 デモ1: 横断検索 - 'X280'")
    print("="*70)
    results = memory.unified_search("X280", limit=3)
    print("\n📊 検索結果サマリー:")
    for source, data in results['sources'].items():
        print(f"  {source:20s}: {data.get('count', 0)}件")
    
    # デモ2: 保存
    print("\n\n📝 デモ2: スマート保存")
    print("="*70)
    save_result = memory.smart_store(
        "Ultimate Memory System LITE デモ実行完了。軽量版で全システム統合動作確認。",
        title="LITE版デモ",
        importance=9,
        tags=["demo", "lite"],
        category="test"
    )
    
    # 最終統計
    print("\n\n📊 最終ダッシュボード")
    print("="*70)
    print(memory.get_dashboard())
    
    print("""
✅ LITE版デモ完了！

次のステップ:
  1. Python REPLで使用:
     >>> from ULTIMATE_MEMORY_LITE import UltimateMemoryLite
     >>> memory = UltimateMemoryLite()
     >>> memory.unified_search("検索ワード")
  
  2. NumPy修正後、フル版へ:
     pip install "numpy<2"
     python3 ULTIMATE_MEMORY_QUICKSTART.py
  
  3. MEGA EVOLUTION実装:
     → Phase 1-15の高度機能追加

🚀 統合記憶システム、起動中！
    """)


if __name__ == '__main__':
    main()

