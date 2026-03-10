#!/usr/bin/env python3
"""
🌉 ManaOS v3 ⇄ Telegram Bridge
TelegramをManaOS v3に統合し、トリニティ達が使えるように

機能:
- Telegram → ManaOS v3 Orchestratorへの自動転送
- Remi・Luna・Minaの意図検出・ポリシー判定・実行
- ManaOS v3の応答 → Telegramへの自動返信
"""

import asyncio
import logging
from typing import Dict, Any, Optional
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ManaOSTelegramBridge:
    """ManaOS v3とTelegramの橋渡し"""
    
    def __init__(self):
        # ManaOS v3エンドポイント
        self.orchestrator_url = "http://localhost:9200"
        self.intention_url = "http://localhost:9201"
        self.policy_url = "http://localhost:9202"
        self.actuator_url = "http://localhost:9203"
        self.ingestor_url = "http://localhost:9204"
        
        logger.info("🌉 ManaOS-Telegram Bridge initialized")
    
    async def process_with_manaos(
        self, 
        message: str, 
        user_id: str = "telegram",
        actor: str = "remi"
    ) -> Dict[str, Any]:
        """
        メッセージをManaOS v3で処理
        
        Args:
            message: ユーザーメッセージ
            user_id: ユーザーID
            actor: 実行アクター（remi/luna/mina）
        
        Returns:
            処理結果
        """
        logger.info(f"🌉 Processing with ManaOS v3 (actor: {actor})")
        
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                # ManaOS v3 Orchestratorに送信
                response = await client.post(
                    f"{self.orchestrator_url}/run",
                    json={
                        "text": message,
                        "context": {
                            "source": "telegram",
                            "user_id": user_id
                        },
                        "actor": actor,
                        "user": "mana",
                        "priority": 5
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    logger.info(f"  ✅ ManaOS v3 処理完了: {result.get('status')}")
                    
                    return {
                        'success': True,
                        'status': result.get('status'),
                        'message': result.get('message', ''),
                        'intent': result.get('intent', {}),
                        'policy': result.get('policy', {}),
                        'result': result.get('result', {}),
                        'actor': actor
                    }
                else:
                    logger.warning(f"  ⚠️ ManaOS v3 returned {response.status_code}")
                    return {
                        'success': False,
                        'error': f'HTTP {response.status_code}'
                    }
        
        except Exception as e:
            logger.error(f"  ❌ ManaOS v3 error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def ask_trinity(
        self,
        message: str,
        user_id: str = "telegram"
    ) -> Dict[str, Any]:
        """
        トリニティ3人（Remi・Luna・Mina）に質問
        
        全員の意見を聞いて、統合回答を生成
        """
        logger.info("🎯 Asking all Trinity members...")
        
        # 3人に並列で質問
        remi_task = self.process_with_manaos(message, user_id, "remi")
        luna_task = self.process_with_manaos(message, user_id, "luna")
        mina_task = self.process_with_manaos(message, user_id, "mina")
        
        remi_result, luna_result, mina_result = await asyncio.gather(
            remi_task, luna_task, mina_task,
            return_exceptions=True
        )
        
        # 統合回答を生成
        integrated_response = self._integrate_trinity_responses(
            remi_result, luna_result, mina_result  # type: ignore
        )
        
        return integrated_response
    
    def _integrate_trinity_responses(
        self, 
        remi: Dict, 
        luna: Dict, 
        mina: Dict
    ) -> Dict[str, Any]:
        """トリニティ3人の回答を統合"""
        
        responses = []
        
        if isinstance(remi, dict) and remi.get('success'):
            responses.append({
                'actor': 'Remi（司令官）',
                'emoji': '👑',
                'message': remi.get('message', '')
            })
        
        if isinstance(luna, dict) and luna.get('success'):
            responses.append({
                'actor': 'Luna（実務）',
                'emoji': '💼',
                'message': luna.get('message', '')
            })
        
        if isinstance(mina, dict) and mina.get('success'):
            responses.append({
                'actor': 'Mina（分析）',
                'emoji': '📊',
                'message': mina.get('message', '')
            })
        
        # 統合メッセージを作成
        if responses:
            integrated = "**🎯 Trinity会議の結果**\n\n"
            
            for resp in responses:
                integrated += f"{resp['emoji']} **{resp['actor']}**\n"
                integrated += f"{resp['message'][:200]}...\n\n"
            
            return {
                'success': True,
                'integrated_message': integrated,
                'trinity_responses': responses,
                'consensus': self._find_consensus(responses)
            }
        else:
            return {
                'success': False,
                'error': 'No successful responses from Trinity'
            }
    
    def _find_consensus(self, responses: list) -> Optional[str]:
        """3人の合意点を見つける"""
        # 簡易的な実装
        if len(responses) >= 2:
            return "複数のTrinityメンバーが同意しています"
        return None
    
    async def check_manaos_status(self) -> Dict[str, Any]:
        """ManaOS v3の状態を確認"""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.orchestrator_url}/health")
                
                if response.status_code == 200:
                    health = response.json()
                    
                    return {
                        'available': True,
                        'health': health,
                        'orchestrator': health.get('orchestrator'),
                        'services': health.get('services', {})
                    }
        except Exception as e:
            logger.warning(f"ManaOS v3 not available: {e}")
        
        return {
            'available': False,
            'error': 'ManaOS v3 not running'
        }


# テスト用
async def test_bridge():
    """ブリッジのテスト"""
    bridge = ManaOSTelegramBridge()
    
    print("\n" + "="*60)
    print("🌉 ManaOS-Telegram Bridge - Test")
    print("="*60)
    
    # テスト1: ManaOS状態確認
    print("\n📝 Test 1: Check ManaOS status")
    status = await bridge.check_manaos_status()
    
    if status['available']:
        print("  ✅ ManaOS v3 is available")
        print(f"     Orchestrator: {status['orchestrator']}")
        print(f"     Services: {status['services']}")
    else:
        print("  ⚠️ ManaOS v3 not available")
    
    # テスト2: 単一アクター処理
    print("\n📝 Test 2: Process with Remi")
    result = await bridge.process_with_manaos("こんにちは", "test_user", "remi")
    
    if result['success']:
        print("  ✅ Remi responded")
        print(f"     Status: {result['status']}")
        print(f"     Message: {result['message'][:100]}...")
    else:
        print(f"  ⚠️ Remi not available: {result.get('error')}")
    
    # テスト3: Trinity全員に質問
    print("\n📝 Test 3: Ask all Trinity members")
    trinity_result = await bridge.ask_trinity("今日のタスクは？", "test_user")
    
    if trinity_result['success']:
        print("  ✅ Trinity responded")
        print(f"     Responses: {len(trinity_result['trinity_responses'])}")
        print(trinity_result['integrated_message'][:200])
    else:
        print("  ⚠️ Trinity not available")


if __name__ == '__main__':
    asyncio.run(test_bridge())


