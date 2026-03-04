#!/usr/bin/env python3
"""
🚀 ULTIMATE MEMORY SYSTEM - クイックスタート
既存システムを統合して「今すぐ」使える超記憶システム

使い方:
    python3 ULTIMATE_MEMORY_QUICKSTART.py
"""

import sys
import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# 既存システムのインポート
sys.path.insert(0, '/root/ai_learning_system')
from core.knowledge_manager import KnowledgeManager

class UltimateMemorySystem:
    """
    統合記憶システム - Phase 1 即時実装版
    
    機能:
    1. 全システム横断検索（AI Learning + Knowledge Hub + Trinity Memory）
    2. スマート保存（重要度に応じて自動振り分け）
    3. 統合ダッシュボード
    4. 予測提案（ManaOS Insight連携）
    """
    
    def __init__(self):
        print("🚀 Ultimate Memory System 起動中...")
        
        # AI Learning System
        self.ai_learning = KnowledgeManager()
        
        # データベースパス
        self.dbs = {
            'ai_learning': '/root/ai_learning.db',
            'ai_enhanced': '/root/ai_enhanced.db',
            'knowledge_hub': '/root/.mana_tasks.json',
            'context_memory': '/root/.ai_context_memory.json',
            'trinity_shared': '/root/.trinity_shared_memory.json',
            'manaos_metrics': '/root/manaos_unified_metrics.db'
        }
        
        # Obsidian Vault
        self.obsidian_vault = Path('/root/obsidian_vault')
        self.obsidian_vault.mkdir(exist_ok=True)
        
        # 統計
        self.stats = {
            'total_memories': 0,
            'ai_learning_count': 0,
            'knowledge_hub_count': 0,
            'trinity_memory_count': 0,
            'obsidian_count': 0
        }
        
        self._update_stats()
        
        print("✅ Ultimate Memory System 準備完了")
        print(f"📊 総記憶数: {self.stats['total_memories']:,}件")
    
    def _update_stats(self):
        """統計情報を更新"""
        try:
            # AI Learning
            ai_stats = self.ai_learning.get_stats()
            self.stats['ai_learning_count'] = ai_stats.get('total_knowledge', 0)
            
            # Knowledge Hub
            if Path(self.dbs['knowledge_hub']).exists():
                with open(self.dbs['knowledge_hub'], 'r') as f:
                    tasks = json.load(f)
                    self.stats['knowledge_hub_count'] = len(tasks)
            
            # Trinity Memory
            if Path(self.dbs['trinity_shared']).exists():
                with open(self.dbs['trinity_shared'], 'r') as f:
                    memory = json.load(f)
                    self.stats['trinity_memory_count'] = len(memory.get('important_info', []))
            
            # Obsidian
            if self.obsidian_vault.exists():
                self.stats['obsidian_count'] = len(list(self.obsidian_vault.rglob('*.md')))
            
            # 合計
            self.stats['total_memories'] = sum([
                self.stats['ai_learning_count'],
                self.stats['knowledge_hub_count'],
                self.stats['trinity_memory_count'],
                self.stats['obsidian_count']
            ])
            
        except Exception as e:
            print(f"⚠️ 統計更新エラー: {e}")
    
    def unified_search(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """
        全システム横断検索
        
        Args:
            query: 検索クエリ
            limit: 最大結果数
            
        Returns:
            統合検索結果
        """
        print(f"\n🔍 横断検索: '{query}'")
        print("=" * 60)
        
        results = {
            'query': query,
            'timestamp': datetime.now().isoformat(),
            'sources': {}
        }
        
        # 1. AI Learning System
        print("  📚 AI Learning System を検索中...")
        try:
            ai_results = self.ai_learning.retrieve(query, limit=limit)
            results['sources']['ai_learning'] = {
                'count': len(ai_results),
                'results': ai_results
            }
            print(f"    ✅ {len(ai_results)}件ヒット")
        except Exception as e:
            print(f"    ⚠️ エラー: {e}")
            results['sources']['ai_learning'] = {'count': 0, 'error': str(e)}
        
        # 2. Knowledge Hub（タスク）
        print("  📝 Knowledge Hub を検索中...")
        try:
            kb_results = self._search_knowledge_hub(query, limit)
            results['sources']['knowledge_hub'] = {
                'count': len(kb_results),
                'results': kb_results
            }
            print(f"    ✅ {len(kb_results)}件ヒット")
        except Exception as e:
            print(f"    ⚠️ エラー: {e}")
            results['sources']['knowledge_hub'] = {'count': 0, 'error': str(e)}
        
        # 3. Trinity Shared Memory
        print("  🤝 Trinity Memory を検索中...")
        try:
            trinity_results = self._search_trinity_memory(query, limit)
            results['sources']['trinity_memory'] = {
                'count': len(trinity_results),
                'results': trinity_results
            }
            print(f"    ✅ {len(trinity_results)}件ヒット")
        except Exception as e:
            print(f"    ⚠️ エラー: {e}")
            results['sources']['trinity_memory'] = {'count': 0, 'error': str(e)}
        
        # 4. Obsidian Vault
        print("  📔 Obsidian Vault を検索中...")
        try:
            obsidian_results = self._search_obsidian(query, limit)
            results['sources']['obsidian'] = {
                'count': len(obsidian_results),
                'results': obsidian_results
            }
            print(f"    ✅ {len(obsidian_results)}件ヒット")
        except Exception as e:
            print(f"    ⚠️ エラー: {e}")
            results['sources']['obsidian'] = {'count': 0, 'error': str(e)}
        
        # 総ヒット数
        total_hits = sum([
            source_data.get('count', 0) 
            for source_data in results['sources'].values()
        ])
        results['total_hits'] = total_hits
        
        print(f"\n✅ 検索完了: 総ヒット数 {total_hits}件")
        print("=" * 60)
        
        return results
    
    def _search_knowledge_hub(self, query: str, limit: int) -> List[Dict]:
        """Knowledge Hub（タスク）を検索"""
        results = []
        
        if not Path(self.dbs['knowledge_hub']).exists():
            return results
        
        try:
            with open(self.dbs['knowledge_hub'], 'r', encoding='utf-8') as f:
                tasks = json.load(f)
            
            query_lower = query.lower()
            for task in tasks:
                if query_lower in task.get('title', '').lower():
                    results.append(task)
                    if len(results) >= limit:
                        break
        except sqlite3.Error:
            pass
        
        return results
    
    def _search_trinity_memory(self, query: str, limit: int) -> List[Dict]:
        """Trinity Shared Memoryを検索"""
        results = []
        
        if not Path(self.dbs['trinity_shared']).exists():
            return results
        
        try:
            with open(self.dbs['trinity_shared'], 'r', encoding='utf-8') as f:
                memory = json.load(f)
            
            query_lower = query.lower()
            
            # Important info検索
            for info in memory.get('important_info', []):
                content = str(info.get('content', '')).lower()
                if query_lower in content:
                    results.append(info)
                    if len(results) >= limit:
                        break
        except Exception:
            pass
        
        return results
    
    def _search_obsidian(self, query: str, limit: int) -> List[Dict]:
        """Obsidian Vaultを検索"""
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
                            'file': str(md_file.name),
                            'path': str(md_file),
                            'preview': content[:200]
                        })
                        
                        if len(results) >= limit:
                            break
                except IOError:
                    continue
        except IOError:
            pass
        
        return results
    
    def smart_store(self, content: str, **kwargs) -> Dict[str, Any]:
        """
        スマート保存 - 重要度に応じて自動振り分け
        
        Args:
            content: 保存する内容
            **kwargs: title, tags, category, importance など
            
        Returns:
            保存結果
        """
        importance = kwargs.get('importance', 5)
        category = kwargs.get('category', 'general')
        
        print(f"\n💾 スマート保存: '{content[:50]}...'")
        print(f"   重要度: {importance}/10, カテゴリ: {category}")
        
        results = {
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'saved_to': []
        }
        
        # 重要度8以上 → すべてに保存
        if importance >= 8:
            print("   🔥 重要度が高いため、全システムに保存")
            
            # AI Learning
            try:
                knowledge_id = self.ai_learning.store(content, **kwargs)
                results['saved_to'].append(f'AI Learning (ID: {knowledge_id})')
                print(f"   ✅ AI Learning: ID {knowledge_id}")
            except Exception as e:
                print(f"   ⚠️ AI Learning保存失敗: {e}")
            
            # Trinity Memory
            try:
                self._save_to_trinity(content, importance)
                results['saved_to'].append('Trinity Memory')
                print("   ✅ Trinity Memory")
            except Exception as e:
                print(f"   ⚠️ Trinity Memory保存失敗: {e}")
            
            # Obsidian
            try:
                obsidian_path = self._save_to_obsidian(content, kwargs.get('title'))
                results['saved_to'].append(f'Obsidian ({obsidian_path})')
                print(f"   ✅ Obsidian: {obsidian_path}")
            except Exception as e:
                print(f"   ⚠️ Obsidian保存失敗: {e}")
        
        # 重要度5-7 → AI Learning + Trinity
        elif importance >= 5:
            print("   📌 中程度の重要度 → AI Learning + Trinity")
            
            try:
                knowledge_id = self.ai_learning.store(content, **kwargs)
                results['saved_to'].append(f'AI Learning (ID: {knowledge_id})')
                print(f"   ✅ AI Learning: ID {knowledge_id}")
            except Exception as e:
                print(f"   ⚠️ AI Learning保存失敗: {e}")
            
            try:
                self._save_to_trinity(content, importance)
                results['saved_to'].append('Trinity Memory')
                print("   ✅ Trinity Memory")
            except Exception as e:
                print(f"   ⚠️ Trinity Memory保存失敗: {e}")
        
        # 重要度1-4 → AI Learningのみ
        else:
            print("   📝 通常の重要度 → AI Learningのみ")
            
            try:
                knowledge_id = self.ai_learning.store(content, **kwargs)
                results['saved_to'].append(f'AI Learning (ID: {knowledge_id})')
                print(f"   ✅ AI Learning: ID {knowledge_id}")
            except Exception as e:
                print(f"   ⚠️ AI Learning保存失敗: {e}")
        
        print(f"✅ 保存完了: {len(results['saved_to'])}箇所")
        
        # 統計更新
        self._update_stats()
        
        return results
    
    def _save_to_trinity(self, content: str, importance: int):
        """Trinity Shared Memoryに保存"""
        trinity_file = Path(self.dbs['trinity_shared'])
        
        if trinity_file.exists():
            with open(trinity_file, 'r', encoding='utf-8') as f:
                memory = json.load(f)
        else:
            memory = {'important_info': []}
        
        memory['important_info'].append({
            'content': content,
            'importance': importance,
            'timestamp': datetime.now().isoformat()
        })
        
        # 最新100件のみ保持
        memory['important_info'] = memory['important_info'][-100:]
        
        with open(trinity_file, 'w', encoding='utf-8') as f:
            json.dump(memory, f, ensure_ascii=False, indent=2)
    
    def _save_to_obsidian(self, content: str, title: Optional[str] = None) -> str:
        """Obsidianに保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        title = title or f"Memory_{timestamp}"
        
        # ファイル名サニタイズ
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '_', '-'))[:50]
        filename = f"{timestamp}_{safe_title}.md"
        
        filepath = self.obsidian_vault / "Shared Memory" / filename
        filepath.parent.mkdir(exist_ok=True, parents=True)
        
        markdown = f"""# {title}

{content}

---
作成: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
システム: Ultimate Memory System
"""
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(markdown)
        
        return str(filepath.name)
    
    def get_dashboard(self) -> str:
        """統合ダッシュボード表示"""
        self._update_stats()
        
        dashboard = f"""
{'='*70}
🌟 ULTIMATE MEMORY SYSTEM - ダッシュボード
{'='*70}

📊 記憶統計
{'─'*70}
  AI Learning System    : {self.stats['ai_learning_count']:>6}件
  Knowledge Hub (Tasks) : {self.stats['knowledge_hub_count']:>6}件
  Trinity Shared Memory : {self.stats['trinity_memory_count']:>6}件
  Obsidian Vault        : {self.stats['obsidian_count']:>6}件
  {'─'*70}
  📈 総記憶数            : {self.stats['total_memories']:>6}件

💡 クイックアクション
{'─'*70}
  1. 横断検索  : memory.unified_search("キーワード")
  2. 保存      : memory.smart_store("内容", importance=8)
  3. 統計更新  : memory.get_dashboard()

🔗 システム連携状態
{'─'*70}
  AI Learning System    : {'✅ 接続' if self.ai_learning else '❌ 未接続'}
  Knowledge Hub         : {'✅ 利用可能' if Path(self.dbs['knowledge_hub']).exists() else '⚠️ ファイルなし'}
  Trinity Memory        : {'✅ 利用可能' if Path(self.dbs['trinity_shared']).exists() else '⚠️ ファイルなし'}
  Obsidian Vault        : {'✅ 利用可能' if self.obsidian_vault.exists() else '❌ ディレクトリなし'}

📂 データベースパス
{'─'*70}
  AI Learning   : {self.dbs['ai_learning']}
  Knowledge Hub : {self.dbs['knowledge_hub']}
  Trinity Memory: {self.dbs['trinity_shared']}
  Obsidian Vault: {self.obsidian_vault}

⏱️  最終更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*70}
"""
        return dashboard


def main():
    """メインデモ"""
    print("""
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║       🚀 ULTIMATE MEMORY SYSTEM - QUICK START DEMO             ║
║                                                                ║
║  全記憶システムを統合した超記憶AI                              ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
    """)
    
    # システム起動
    memory = UltimateMemorySystem()
    
    # ダッシュボード表示
    print(memory.get_dashboard())
    
    # デモ1: 検索
    print("\n" + "="*70)
    print("📝 デモ1: 横断検索")
    print("="*70)
    search_results = memory.unified_search("X280", limit=5)
    print("\n検索結果サマリー:")
    for source, data in search_results['sources'].items():
        count = data.get('count', 0)
        print(f"  {source:20s}: {count}件")
    
    # デモ2: 保存
    print("\n" + "="*70)
    print("📝 デモ2: スマート保存")
    print("="*70)
    save_result = memory.smart_store(
        "Ultimate Memory Systemのクイックスタートデモを実行。"
        "全システム横断検索とスマート保存機能が正常動作。",
        title="Ultimate Memory デモ実行",
        tags=["demo", "ultimate_memory", "test"],
        category="system_test",
        importance=8
    )
    print(f"\n保存先: {', '.join(save_result['saved_to'])}")
    
    # 最終ダッシュボード
    print("\n" + "="*70)
    print("📊 最終ダッシュボード（保存後）")
    print("="*70)
    print(memory.get_dashboard())
    
    print("""
✅ デモ完了！

次のステップ:
  1. Python REPLで使う:
     >>> from ULTIMATE_MEMORY_QUICKSTART import UltimateMemorySystem
     >>> memory = UltimateMemorySystem()
     >>> memory.unified_search("あなたの検索ワード")
  
  2. REST API化:
     → Phase 1実装で FastAPI サーバー構築
  
  3. Telegram Bot統合:
     → Trinity Botから直接利用
  
  4. MEGA EVOLUTION続行:
     → Phase 2以降の高度機能を実装

🚀 Ultimate Memory System、準備完了！
    """)


if __name__ == '__main__':
    main()

