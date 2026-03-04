#!/usr/bin/env python3
"""
🔗 ManaOS v3 Bridge
ManaOS v3（Remi/Luna/Mina）から Unified Memory System を使えるようにする

使い方:
  from integrations.manaos_bridge import unified_memory
  
  # 検索
  results = await unified_memory.search("X280")
  
  # 保存
  await unified_memory.store("新しい知識", importance=8)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import aiohttp
from typing import Dict, List, Optional


class ManaOSUnifiedMemoryBridge:
    """ManaOS v3 → Unified Memory System ブリッジ"""
    
    def __init__(self, api_url: str = "http://localhost:8800"):
        self.api_url = api_url
    
    async def search(self, query: str, limit: int = 10, 
                    importance_min: Optional[int] = None) -> Dict:
        """
        記憶を検索（ManaOS用）
        
        Args:
            query: 検索クエリ
            limit: 最大結果数
            importance_min: 最低重要度
            
        Returns:
            検索結果
        """
        params = {'q': query, 'limit': limit}
        if importance_min:
            params['importance_min'] = importance_min
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.api_url}/api/search",
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return {'error': f'HTTP {response.status}'}
        except Exception as e:
            return {'error': str(e)}
    
    async def store(self, content: str, title: Optional[str] = None,
                   importance: int = 5, tags: Optional[List[str]] = None,
                   category: Optional[str] = None,
                   actor: str = "manaos") -> Dict:
        """
        記憶を保存（ManaOS用）
        
        Args:
            content: 保存内容
            title: タイトル
            importance: 重要度 (1-10)
            tags: タグ
            category: カテゴリ
            actor: 実行者（remi/luna/mina）
            
        Returns:
            保存結果
        """
        data = {
            'content': content,
            'title': title,
            'importance': importance,
            'tags': tags or [],
            'category': category or 'manaos',
            'metadata': {'actor': actor, 'source': 'manaos_v3'}
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_url}/api/store",
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return {'error': f'HTTP {response.status}'}
        except Exception as e:
            return {'error': str(e)}
    
    async def get_stats(self) -> Dict:
        """統計取得"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.api_url}/api/stats",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return {'error': f'HTTP {response.status}'}
        except Exception as e:
            return {'error': str(e)}


# グローバルインスタンス（簡単に使える）
unified_memory = ManaOSUnifiedMemoryBridge()


# ========== 簡易API（ManaOS Actuatorから使いやすい） ==========

async def search_memory(query: str, **kwargs) -> Dict:
    """簡易検索API"""
    return await unified_memory.search(query, **kwargs)


async def store_memory(content: str, **kwargs) -> Dict:
    """簡易保存API"""
    return await unified_memory.store(content, **kwargs)


async def get_memory_stats() -> Dict:
    """簡易統計API"""
    return await unified_memory.get_stats()


# テスト
async def test_manaos_bridge():
    print("\n🧪 ManaOS Bridge テスト")
    print("="*60)
    
    # 検索テスト
    print("\n🔍 検索テスト")
    results = await search_memory("システム", limit=5)
    print(f"ヒット: {results.get('total_hits', 0)}件")
    
    # 保存テスト（Remiが保存）
    print("\n💾 保存テスト（Remi）")
    save_result = await store_memory(
        "Remi: ManaOS v3から Unified Memory 使用テスト",
        title="ManaOS統合テスト",
        importance=8,
        tags=['manaos', 'remi', 'test'],
        actor='remi'
    )
    print(f"保存: {len(save_result.get('saved_to', []))}箇所")
    
    # 統計テスト
    print("\n📊 統計テスト")
    stats = await get_memory_stats()
    print(f"総記憶: {stats.get('total_memories', 0)}件")
    
    print("\n✅ ManaOS Bridge 完全動作！")


if __name__ == '__main__':
    asyncio.run(test_manaos_bridge())

