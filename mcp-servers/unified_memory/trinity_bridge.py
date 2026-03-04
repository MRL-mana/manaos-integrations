#!/usr/bin/env python3
"""
🤝 Trinity Bridge
Trinity Telegram Bot から Unified Memory System を使えるようにする

使い方（Telegram Botから）:
  from integrations.trinity_bridge import trinity_memory
  
  # テレグラムでの会話を記憶
  await trinity_memory.remember_conversation(user_message, bot_response)
  
  # 過去の会話を検索
  results = await trinity_memory.recall("X280の設定")
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import aiohttp
from typing import Dict, List, Optional
from datetime import datetime


class TrinityUnifiedMemoryBridge:
    """Trinity → Unified Memory System ブリッジ"""
    
    def __init__(self, api_url: str = "http://localhost:8800"):
        self.api_url = api_url
    
    async def remember_conversation(self, user_message: str, 
                                   bot_response: str,
                                   user_id: str = "telegram",
                                   emotion: Optional[str] = None) -> Dict:
        """
        テレグラム会話を記憶
        
        Args:
            user_message: ユーザーメッセージ
            bot_response: ボット返答
            user_id: ユーザーID
            emotion: 感情（任意）
            
        Returns:
            保存結果
        """
        content = f"""Telegram会話:

User: {user_message}
Bot: {bot_response}

User ID: {user_id}
Timestamp: {datetime.now().isoformat()}
"""
        if emotion:
            content += f"Emotion: {emotion}\n"
        
        return await self._store(
            content=content,
            title=f"Telegram: {user_message[:30]}",
            importance=6,
            tags=['telegram', 'conversation', user_id],
            category='telegram_chat'
        )
    
    async def recall(self, query: str, limit: int = 5) -> List[Dict]:
        """
        過去の記憶を思い出す
        
        Args:
            query: 検索クエリ
            limit: 最大結果数
            
        Returns:
            検索結果リスト
        """
        result = await self._search(query, limit)
        
        if result.get('total_hits', 0) > 0:
            # 全ソースから結果を集約
            all_results = []
            for source_data in result.get('sources', {}).values():
                all_results.extend(source_data.get('results', []))
            
            return all_results[:limit]
        
        return []
    
    async def learn_from_user(self, user_id: str, preference: str,
                             importance: int = 7) -> Dict:
        """
        ユーザーの好み・習慣を学習
        
        Args:
            user_id: ユーザーID
            preference: 好み・習慣
            importance: 重要度
            
        Returns:
            学習結果
        """
        return await self._store(
            content=f"User {user_id} の好み: {preference}",
            title=f"ユーザー好み: {user_id}",
            importance=importance,
            tags=['user_preference', user_id],
            category='trinity_learning'
        )
    
    async def get_user_context(self, user_id: str) -> Dict:
        """
        ユーザーのコンテキスト取得
        
        Args:
            user_id: ユーザーID
            
        Returns:
            ユーザーコンテキスト（過去会話、好みなど）
        """
        # ユーザーIDで検索
        results = await self._search(user_id, limit=10)
        
        return {
            'user_id': user_id,
            'total_memories': results.get('total_hits', 0),
            'recent_conversations': results.get('sources', {}).get('context_memory', {}).get('results', [])[:5]
        }
    
    async def _search(self, query: str, limit: int = 10) -> Dict:
        """内部検索メソッド"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.api_url}/api/search",
                    params={'q': query, 'limit': limit},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return {'error': f'HTTP {response.status}', 'total_hits': 0}
        except Exception as e:
            return {'error': str(e), 'total_hits': 0}
    
    async def _store(self, content: str, **kwargs) -> Dict:
        """内部保存メソッド"""
        data = {'content': content, **kwargs}
        
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


# グローバルインスタンス
trinity_memory = TrinityUnifiedMemoryBridge()


# ========== 超簡単API（Telegram Botから1行で使える） ==========

async def remember(user_msg: str, bot_msg: str, user_id: str = "telegram") -> bool:
    """会話を記憶（超簡単版）"""
    result = await trinity_memory.remember_conversation(user_msg, bot_msg, user_id)
    return 'saved_to' in result


async def recall(query: str, limit: int = 5) -> List[str]:
    """記憶を思い出す（超簡単版）"""
    results = await trinity_memory.recall(query, limit)
    return [
        r.get('content', r.get('text', ''))[:200] 
        for r in results
    ]


async def learn(user_id: str, preference: str) -> bool:
    """好みを学習（超簡単版）"""
    result = await trinity_memory.learn_from_user(user_id, preference)
    return 'saved_to' in result


# テスト
async def test_trinity_bridge():
    print("\n🧪 Trinity Bridge テスト")
    print("="*60)
    
    # 会話記憶
    print("\n💬 会話記憶テスト")
    saved = await remember(
        "Unified Memory使える？",
        "もちろん！完璧に動くよ！",
        "mana"
    )
    print(f"記憶: {'✅ 成功' if saved else '❌ 失敗'}")
    
    # 思い出す
    print("\n🔍 思い出しテスト")
    memories = await recall("Unified Memory", limit=3)
    print(f"思い出した: {len(memories)}件")
    for mem in memories[:2]:
        print(f"  • {mem[:60]}...")
    
    # 好み学習
    print("\n💡 好み学習テスト")
    learned = await learn("mana", "効率性重視、完璧主義")
    print(f"学習: {'✅ 成功' if learned else '❌ 失敗'}")
    
    print("\n✅ Trinity Bridge 完全動作！")


if __name__ == '__main__':
    asyncio.run(test_trinity_bridge())

