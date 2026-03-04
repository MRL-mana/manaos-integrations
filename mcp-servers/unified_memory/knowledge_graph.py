#!/usr/bin/env python3
"""
🕸️ Knowledge Graph Engine
Phase 4+5: グラフベース記憶ネットワーク

機能:
1. 記憶同士の関連性を自動抽出
2. グラフ検索（芋づる式）
3. パスファインディング
4. 関連記憶の可視化
"""

import asyncio
import logging
from typing import Dict, List, Set
from pathlib import Path
import json
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("KnowledgeGraph")


class KnowledgeGraph:
    """知識グラフエンジン"""
    
    def __init__(self, unified_memory_api):
        logger.info("🕸️ Knowledge Graph 初期化中...")
        
        self.memory_api = unified_memory_api
        
        # グラフデータ
        self.graph_db = Path('/root/unified_memory_system/data/knowledge_graph.json')
        self.graph_db.parent.mkdir(exist_ok=True, parents=True)
        self.graph = self._load_graph()
        
        logger.info("✅ Knowledge Graph 準備完了")
    
    def _load_graph(self) -> Dict:
        """グラフ読み込み"""
        if self.graph_db.exists():
            try:
                with open(self.graph_db, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        return {
            'nodes': {},  # {node_id: {data}}
            'edges': {},  # {node_id: [connected_node_ids]}
            'keywords': defaultdict(set)  # {keyword: {node_ids}}
        }
    
    def _save_graph(self):
        """グラフ保存"""
        try:
            # defaultdictをdictに変換
            save_data = {
                'nodes': self.graph['nodes'],
                'edges': self.graph['edges'],
                'keywords': {k: list(v) for k, v in self.graph['keywords'].items()}
            }
            
            with open(self.graph_db, 'w') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"グラフ保存エラー: {e}")
    
    async def build_graph_from_memories(self, limit: int = 100) -> Dict:
        """
        記憶からグラフを構築
        
        Args:
            limit: 処理する記憶数
            
        Returns:
            構築結果
        """
        logger.info(f"🕸️ グラフ構築開始（{limit}件）...")
        
        # 全記憶を取得
        stats = await self.memory_api.get_stats()
        
        result = {
            'nodes_created': 0,
            'edges_created': 0
        }
        
        # AI Learningから記憶を取得
        import sqlite3
        conn = sqlite3.connect('/root/ai_learning.db')
        cursor = conn.cursor()
        
        cursor.execute(f"""
            SELECT id, content, title, tags, importance 
            FROM knowledge 
            ORDER BY importance DESC, id DESC 
            LIMIT {limit}
        """)
        
        memories = cursor.fetchall()
        conn.close()
        
        for memory in memories:
            mem_id, content, title, tags_json, importance = memory
            
            # ノード作成
            node_id = f"mem_{mem_id}"
            self.graph['nodes'][node_id] = {
                'id': mem_id,
                'title': title,
                'content': content[:200],
                'importance': importance
            }
            result['nodes_created'] += 1
            
            # キーワード抽出
            keywords = self._extract_keywords(content, title)
            
            # キーワードでノードをリンク
            for keyword in keywords:
                if keyword not in self.graph['keywords']:
                    self.graph['keywords'][keyword] = set()
                self.graph['keywords'][keyword].add(node_id)
            
            # エッジ作成（同じキーワードを持つノード同士を接続）
            if node_id not in self.graph['edges']:
                self.graph['edges'][node_id] = []
            
            for keyword in keywords:
                related_nodes = self.graph['keywords'].get(keyword, set())
                for related_id in related_nodes:
                    if related_id != node_id and related_id not in self.graph['edges'][node_id]:
                        self.graph['edges'][node_id].append(related_id)
                        result['edges_created'] += 1
        
        self._save_graph()
        
        logger.info(f"✅ グラフ構築完了: {result['nodes_created']}ノード、{result['edges_created']}エッジ")
        
        return result
    
    def _extract_keywords(self, content: str, title: str) -> Set[str]:
        """キーワード抽出"""
        text = f"{title or ''} {content or ''}"
        
        # 重要キーワードリスト
        important_keywords = [
            'X280', 'RunPod', 'Trinity', 'ManaOS', 'Remi', 'Luna', 'Mina',
            'GPU', 'SSH', 'Tailscale', 'Docker', 'API', 'システム',
            '設定', '実行', '成功', '完了', 'バックアップ', '最適化'
        ]
        
        keywords = set()
        text_lower = text.lower()
        
        for keyword in important_keywords:
            if keyword.lower() in text_lower:
                keywords.add(keyword)
        
        return keywords
    
    async def find_related(self, node_id: str, depth: int = 2) -> List[Dict]:
        """
        関連記憶を芋づる式検索
        
        Args:
            node_id: 起点ノードID
            depth: 探索深度
            
        Returns:
            関連ノードリスト
        """
        logger.info(f"🔍 関連検索: {node_id}, 深度{depth}")
        
        visited = set()
        queue = [(node_id, 0)]
        related = []
        
        while queue:
            current_id, current_depth = queue.pop(0)
            
            if current_id in visited or current_depth > depth:
                continue
            
            visited.add(current_id)
            
            # ノード情報取得
            node_data = self.graph['nodes'].get(current_id)
            if node_data and current_id != node_id:
                related.append({
                    'node_id': current_id,
                    'title': node_data.get('title'),
                    'importance': node_data.get('importance'),
                    'depth': current_depth
                })
            
            # 接続ノードをキューに追加
            connected = self.graph['edges'].get(current_id, [])
            for connected_id in connected:
                if connected_id not in visited:
                    queue.append((connected_id, current_depth + 1))
        
        logger.info(f"  ✅ 関連記憶: {len(related)}件発見")
        
        return related
    
    async def get_graph_stats(self) -> Dict:
        """グラフ統計"""
        total_nodes = len(self.graph['nodes'])
        total_edges = sum(len(edges) for edges in self.graph['edges'].values())
        total_keywords = len(self.graph['keywords'])
        
        # 最も接続の多いノード
        if self.graph['edges']:
            max_connections = max(len(edges) for edges in self.graph['edges'].values())
            most_connected = [
                node_id for node_id, edges in self.graph['edges'].items()
                if len(edges) == max_connections
            ]
        else:
            max_connections = 0
            most_connected = []
        
        return {
            'total_nodes': total_nodes,
            'total_edges': total_edges,
            'total_keywords': total_keywords,
            'max_connections': max_connections,
            'most_connected_nodes': most_connected[:5]
        }


# テスト
async def test_graph():
    print("\n" + "="*70)
    print("🧪 Knowledge Graph - テスト")
    print("="*70)
    
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.unified_memory_api import UnifiedMemoryAPI
    
    memory = UnifiedMemoryAPI()
    graph = KnowledgeGraph(memory)
    
    # グラフ構築
    print("\n🕸️ グラフ構築")
    result = await graph.build_graph_from_memories(limit=50)
    print(f"ノード: {result['nodes_created']}個")
    print(f"エッジ: {result['edges_created']}個")
    
    # 統計
    print("\n📊 グラフ統計")
    stats = await graph.get_graph_stats()
    print(f"総ノード数: {stats['total_nodes']}")
    print(f"総エッジ数: {stats['total_edges']}")
    print(f"キーワード数: {stats['total_keywords']}")
    
    print("\n✅ テスト完了")


if __name__ == '__main__':
    asyncio.run(test_graph())

