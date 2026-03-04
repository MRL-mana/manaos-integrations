#!/usr/bin/env python3
"""
RAG記憶検索システム - AIが忘れないシステム
"""

import json
import time
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import hashlib
import re

@dataclass
class MemoryFragment:
    """記憶断片"""
    fragment_id: str
    content: str
    category: str
    tags: List[str]
    created_at: float
    last_accessed: float
    access_count: int
    importance: float
    embedding_hash: str  # 簡易的な類似度計算用

class RAGMemorySystem:
    """RAG記憶検索システム"""
    
    def __init__(self):
        self.memory_dir = Path("/root/god_mode/rag_memory")
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        self.memories_db = self.memory_dir / "memories.jsonl"
        self.index_cache = self.memory_dir / "index.json"
        
        self._load_index()
    
    def _load_index(self):
        """インデックス読み込み"""
        if self.index_cache.exists():
            with open(self.index_cache, 'r') as f:
                self.index = json.load(f)
        else:
            self.index = {
                "tag_index": {},
                "category_index": {},
                "total_memories": 0
            }
    
    def _save_index(self):
        """インデックス保存"""
        with open(self.index_cache, 'w') as f:
            json.dump(self.index, f, indent=2, ensure_ascii=False)
    
    def _compute_embedding_hash(self, text: str) -> str:
        """簡易埋め込みハッシュ（単語ベース）"""
        # 本格実装ならSentence Transformers使うけど、今は軽量版
        words = set(re.findall(r'\w+', text.lower()))
        sorted_words = sorted(list(words)[:50])  # 上位50単語
        return hashlib.md5(''.join(sorted_words).encode()).hexdigest()
    
    def store_memory(
        self,
        content: str,
        category: str,
        tags: List[str],
        importance: float = 0.5
    ) -> str:
        """記憶を保存"""
        fragment_id = hashlib.md5(
            f"{content}_{time.time()}".encode()
        ).hexdigest()[:12]
        
        embedding_hash = self._compute_embedding_hash(content)
        
        fragment = MemoryFragment(
            fragment_id=fragment_id,
            content=content,
            category=category,
            tags=tags,
            created_at=time.time(),
            last_accessed=time.time(),
            access_count=0,
            importance=importance,
            embedding_hash=embedding_hash
        )
        
        # データベースに追加
        with open(self.memories_db, 'a') as f:
            f.write(json.dumps(asdict(fragment), ensure_ascii=False) + '\n')
        
        # インデックス更新
        for tag in tags:
            if tag not in self.index['tag_index']:
                self.index['tag_index'][tag] = []
            self.index['tag_index'][tag].append(fragment_id)
        
        if category not in self.index['category_index']:
            self.index['category_index'][category] = []
        self.index['category_index'][category].append(fragment_id)
        
        self.index['total_memories'] += 1
        self._save_index()
        
        return fragment_id
    
    def search(
        self,
        query: str,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 5
    ) -> List[Dict]:
        """記憶を検索"""
        if not self.memories_db.exists():
            return []
        
        query_embedding = self._compute_embedding_hash(query)
        query_words = set(re.findall(r'\w+', query.lower()))
        
        # 全記憶を読み込み
        memories = []
        with open(self.memories_db, 'r') as f:
            for line in f:
                try:
                    memory = json.loads(line)
                    memories.append(memory)
                except sqlite3.Error:
                    continue
        
        # フィルタリング
        if category:
            memories = [m for m in memories if m.get('category') == category]
        
        if tags:
            memories = [
                m for m in memories
                if any(tag in m.get('tags', []) for tag in tags)
            ]
        
        # スコアリング
        scored_memories = []
        for memory in memories:
            score = self._calculate_relevance_score(
                memory,
                query_words,
                query_embedding
            )
            scored_memories.append((memory, score))
        
        # ソートして上位を返す
        scored_memories.sort(key=lambda x: x[1], reverse=True)
        
        results = []
        for memory, score in scored_memories[:limit]:
            # アクセス記録更新
            self._update_access(memory['fragment_id'])
            
            results.append({
                **memory,
                'relevance_score': score
            })
        
        return results
    
    def _calculate_relevance_score(
        self,
        memory: Dict,
        query_words: set,
        query_embedding: str
    ) -> float:
        """関連度スコア計算"""
        score = 0.0
        
        # 1. 単語マッチング（基本スコア）
        content_words = set(re.findall(r'\w+', memory['content'].lower()))
        word_overlap = len(query_words & content_words)
        word_score = word_overlap / max(len(query_words), 1)
        score += word_score * 0.4
        
        # 2. 埋め込みハッシュ類似度（簡易）
        if memory['embedding_hash'] == query_embedding:
            score += 0.3
        
        # 3. 重要度
        score += memory.get('importance', 0.5) * 0.2
        
        # 4. アクセス頻度（人気度）
        access_boost = min(memory.get('access_count', 0) / 10, 1.0)
        score += access_boost * 0.1
        
        return score
    
    def _update_access(self, fragment_id: str):
        """アクセス記録更新（簡易版）"""
        # 本格実装なら全メモリをロードして更新・保存
        # 今は次回検索で反映される形で実装
        pass
    
    def get_related_memories(self, fragment_id: str, limit: int = 3) -> List[Dict]:
        """関連記憶を取得"""
        # 指定されたメモリを取得
        target_memory = None
        if self.memories_db.exists():
            with open(self.memories_db, 'r') as f:
                for line in f:
                    try:
                        memory = json.loads(line)
                        if memory['fragment_id'] == fragment_id:
                            target_memory = memory
                            break
                    except sqlite3.Error:
                        continue
        
        if not target_memory:
            return []
        
        # 同じカテゴリ・タグの記憶を検索
        related = self.search(
            query=target_memory['content'],
            category=target_memory.get('category'),
            tags=target_memory.get('tags'),
            limit=limit + 1  # 自分自身を除く
        )
        
        # 自分自身を除外
        related = [m for m in related if m['fragment_id'] != fragment_id]
        
        return related[:limit]
    
    def get_statistics(self) -> Dict:
        """統計情報"""
        if not self.memories_db.exists():
            return {
                "total_memories": 0,
                "categories": {},
                "tags": {},
                "avg_importance": 0.0
            }
        
        memories = []
        with open(self.memories_db, 'r') as f:
            for line in f:
                try:
                    memories.append(json.loads(line))
                except sqlite3.Error:
                    continue
        
        # カテゴリ分布
        category_dist = {}
        for m in memories:
            cat = m.get('category', 'unknown')
            category_dist[cat] = category_dist.get(cat, 0) + 1
        
        # タグ分布
        tag_dist = {}
        for m in memories:
            for tag in m.get('tags', []):
                tag_dist[tag] = tag_dist.get(tag, 0) + 1
        
        # 平均重要度
        avg_importance = sum(m.get('importance', 0.5) for m in memories) / len(memories) if memories else 0.0
        
        return {
            "total_memories": len(memories),
            "categories": category_dist,
            "tags": dict(sorted(tag_dist.items(), key=lambda x: x[1], reverse=True)[:10]),
            "avg_importance": avg_importance
        }
    
    def vacuum_old_memories(self, days: int = 30, min_importance: float = 0.3):
        """古い低重要度メモリを削除"""
        if not self.memories_db.exists():
            return 0
        
        cutoff = time.time() - (days * 86400)
        
        # 保持するメモリ
        kept_memories = []
        removed_count = 0
        
        with open(self.memories_db, 'r') as f:
            for line in f:
                try:
                    memory = json.loads(line)
                    created = memory.get('created_at', 0)
                    importance = memory.get('importance', 0.5)
                    
                    # 新しいか、重要度が高いものは保持
                    if created >= cutoff or importance >= min_importance:
                        kept_memories.append(memory)
                    else:
                        removed_count += 1
                except Exception:
                    continue
        
        # 再構築
        if removed_count > 0:
            with open(self.memories_db, 'w') as f:
                for memory in kept_memories:
                    f.write(json.dumps(memory, ensure_ascii=False) + '\n')
            
            # インデックス再構築
            self._rebuild_index(kept_memories)
        
        return removed_count
    
    def _rebuild_index(self, memories: List[Dict]):
        """インデックス再構築"""
        self.index = {
            "tag_index": {},
            "category_index": {},
            "total_memories": len(memories)
        }
        
        for memory in memories:
            fragment_id = memory['fragment_id']
            
            for tag in memory.get('tags', []):
                if tag not in self.index['tag_index']:
                    self.index['tag_index'][tag] = []
                self.index['tag_index'][tag].append(fragment_id)
            
            category = memory.get('category', 'unknown')
            if category not in self.index['category_index']:
                self.index['category_index'][category] = []
            self.index['category_index'][category].append(fragment_id)
        
        self._save_index()

# グローバルインスタンス
_rag_system = None

def get_rag_system() -> RAGMemorySystem:
    """グローバルRAGシステム取得"""
    global _rag_system
    if _rag_system is None:
        _rag_system = RAGMemorySystem()
    return _rag_system

# テスト実行
if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🧪 RAG記憶検索システム - デモ実行")
    print("=" * 70)
    
    system = RAGMemorySystem()
    
    # サンプル記憶を保存
    print("\n[記憶登録]")
    
    memories_data = [
        {
            "content": "GitHub PRの自動レビューでは、まずdiffを取得し、次にコード品質チェック、最後にコメント生成の順で実行する。",
            "category": "implementation_pattern",
            "tags": ["github", "pr", "review", "workflow"],
            "importance": 0.8
        },
        {
            "content": "Level 3の自律判断エンジンは信頼度0.95以上でのみ自動実装を許可する。それ以下は承認待ちキューに入れる。",
            "category": "safety_rule",
            "tags": ["level3", "autonomous", "safety", "decision"],
            "importance": 0.95
        },
        {
            "content": "Slackの通知は /root/.mana_vault/slack_webhook.json にwebhook URLを設定することで有効化できる。",
            "category": "configuration",
            "tags": ["slack", "notification", "setup"],
            "importance": 0.7
        },
        {
            "content": "バックアップは毎日自動実行され、7日以上古いものは自動削除される。復元は tar -xzf で可能。",
            "category": "operations",
            "tags": ["backup", "restore", "maintenance"],
            "importance": 0.75
        }
    ]
    
    for data in memories_data:
        fragment_id = system.store_memory(**data)
        print(f"  ✅ {fragment_id[:8]}: {data['content'][:50]}...")
    
    # 検索テスト
    print("\n[検索テスト 1] クエリ: 'GitHub PR レビュー'")
    results = system.search("GitHub PR レビュー", limit=3)
    for i, result in enumerate(results, 1):
        print(f"  {i}. [スコア: {result['relevance_score']:.2f}] {result['content'][:60]}...")
    
    print("\n[検索テスト 2] クエリ: 'Level 3 自律'")
    results = system.search("Level 3 自律", limit=3)
    for i, result in enumerate(results, 1):
        print(f"  {i}. [スコア: {result['relevance_score']:.2f}] {result['content'][:60]}...")
    
    print("\n[検索テスト 3] カテゴリ: 'safety_rule'")
    results = system.search("", category="safety_rule", limit=5)
    for i, result in enumerate(results, 1):
        print(f"  {i}. {result['content'][:60]}...")
    
    # 統計
    print("\n[統計情報]")
    stats = system.get_statistics()
    print(f"  総記憶数: {stats['total_memories']}")
    print(f"  カテゴリ: {list(stats['categories'].keys())}")
    print(f"  人気タグ TOP5: {list(stats['tags'].keys())[:5]}")
    print(f"  平均重要度: {stats['avg_importance']:.2f}")
    
    print("\n" + "=" * 70)
    print("✅ デモ完了")
    print(f"   記憶保存先: {system.memory_dir}")
    print("=" * 70)

