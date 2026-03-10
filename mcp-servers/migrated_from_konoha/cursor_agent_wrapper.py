"""
Cursor Agent Wrapper
既存のエージェントにCursor API統合を追加するラッパー

使用方法:
    agent = CursorAgentWrapper(original_agent)
    response = await agent.call_ai(prompt)
    # → Cursor内ならCursor Pro使用、そうでなければ標準API
"""

import logging
import asyncio
from typing import Dict, Any, Optional
import sys
from pathlib import Path

# Trinity core modules
sys.path.insert(0, str(Path(__file__).parent.parent / 'core'))
from cursor_runtime import cursor_runtime
from cursor_api_proxy import cursor_api

logger = logging.getLogger(__name__)


class CursorAgentWrapper:
    """
    Cursorエージェントラッパー
    
    既存のエージェントクラスをラップして、Cursor API統合を追加する。
    Cursor内実行時は自動的にCursor Pro APIを使用し、追加料金なしで動作。
    """
    
    def __init__(self, agent_instance):
        """
        Args:
            agent_instance: 既存のエージェントインスタンス（Remi, Luna, Mina, Aria）
        """
        self.agent = agent_instance
        self.name = getattr(agent_instance, 'name', 'Unknown')
        self.is_cursor = cursor_runtime.is_cursor
        self.use_cursor_api = cursor_runtime.should_use_cursor_api()
        
        logger.info(f"🎯 {self.name} Agent wrapped for Cursor integration")
        if self.use_cursor_api:
            logger.info(f"   ✅ Using Cursor Pro credits - No additional costs!")
        else:
            logger.info(f"   ⚠️ Using standard API")
    
    async def call_ai(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        **kwargs
    ) -> Dict[str, Any]:
        """
        AI呼び出し（Cursor統合）
        
        Cursor内実行時: Cursor Pro API使用
        標準実行時: 元のエージェントのAPI使用
        """
        
        # モデル決定（エージェント固有のモデル優先）
        if model is None:
            model = getattr(self.agent, 'model', 'gpt-4')
        
        logger.info(f"🤖 {self.name}: Calling AI with {model}")
        
        if self.use_cursor_api:
            # Cursor API使用
            return await self._call_via_cursor_api(prompt, model, max_tokens, temperature, **kwargs)  # type: ignore
        else:
            # 標準API使用（元のエージェントの実装）
            return await self._call_via_standard_api(prompt, model, max_tokens, temperature, **kwargs)  # type: ignore
    
    async def _call_via_cursor_api(
        self,
        prompt: str,
        model: str,
        max_tokens: int,
        temperature: float,
        **kwargs
    ) -> Dict[str, Any]:
        """Cursor API経由で呼び出し"""
        
        logger.debug(f"Using Cursor Pro API for {model}")
        
        try:
            response = await cursor_api.complete(
                prompt=prompt,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )
            
            return {
                'success': True,
                'response': response['response'],
                'model': response['model'],
                'api_type': 'cursor',
                'cost': 0.0,  # Cursor Pro使用
                'tokens': response.get('tokens', 0),
            }
        
        except Exception as e:
            logger.error(f"Cursor API call failed: {e}")
            # フォールバック: 標準API
            logger.info("Falling back to standard API")
            return await self._call_via_standard_api(prompt, model, max_tokens, temperature, **kwargs)
    
    async def _call_via_standard_api(
        self,
        prompt: str,
        model: str,
        max_tokens: int,
        temperature: float,
        **kwargs
    ) -> Dict[str, Any]:
        """標準API経由で呼び出し（元のエージェント実装使用）"""
        
        logger.debug(f"Using standard API for {model}")
        
        # 元のエージェントにクライアントがあればそれを使用
        if hasattr(self.agent, 'client') and self.agent.client:
            try:
                # OpenAI/Anthropic クライアントを使用
                if 'gpt' in model:
                    return await self._call_openai_client(prompt, model, max_tokens, temperature)
                elif 'claude' in model:
                    return await self._call_anthropic_client(prompt, model, max_tokens, temperature)
            except Exception as e:
                logger.error(f"Standard API call failed: {e}")
        
        # APIクライアントなし or エラー → モックモード
        logger.warning(f"No API client available, using mock response")
        return self._generate_mock_response(prompt, model)
    
    async def _call_openai_client(self, prompt: str, model: str, max_tokens: int, temperature: float) -> Dict[str, Any]:
        """OpenAI クライアント経由"""
        
        # 同期API → 非同期変換
        loop = asyncio.get_event_loop()
        
        response = await loop.run_in_executor(
            None,
            lambda: self.agent.client.chat.completions.create(
                model=model,
                messages=[
                    {'role': 'system', 'content': getattr(self.agent, 'system_prompt', '')},
                    {'role': 'user', 'content': prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature
            )
        )
        
        return {
            'success': True,
            'response': response.choices[0].message.content,
            'model': model,
            'api_type': 'openai',
            'cost': response.usage.total_tokens * 0.00003,  # 概算
            'tokens': response.usage.total_tokens,
        }
    
    async def _call_anthropic_client(self, prompt: str, model: str, max_tokens: int, temperature: float) -> Dict[str, Any]:
        """Anthropic クライアント経由"""
        
        loop = asyncio.get_event_loop()
        
        response = await loop.run_in_executor(
            None,
            lambda: self.agent.client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=getattr(self.agent, 'system_prompt', ''),
                messages=[
                    {'role': 'user', 'content': prompt}
                ]
            )
        )
        
        return {
            'success': True,
            'response': response.content[0].text,
            'model': model,
            'api_type': 'anthropic',
            'cost': (response.usage.input_tokens + response.usage.output_tokens) * 0.000003,
            'tokens': response.usage.input_tokens + response.usage.output_tokens,
        }
    
    def _generate_mock_response(self, prompt: str, model: str) -> Dict[str, Any]:
        """モックレスポンス生成"""
        
        mock_response = f"""# {self.name} Mock Response

## Task Analysis
{prompt[:200]}...

## Implementation (Mock)
```python
# Mock implementation by {self.name}
def mock_implementation():
    '''
    This is a mock response generated because:
    - No API key available
    - Or API call failed
    
    To use real AI:
    1. Set API keys (OpenAI/Anthropic)
    2. Or run in Cursor with Cursor Pro
    '''
    pass
```

## Notes
- This is a mock response from {self.name}
- Model: {model}
- For real implementation, configure API keys or use Cursor Pro
"""
        
        return {
            'success': True,
            'response': mock_response,
            'model': model,
            'api_type': 'mock',
            'cost': 0.0,
            'tokens': 0,
            'is_mock': True,
        }
    
    def __getattr__(self, name):
        """その他のメソッド/属性は元のエージェントに委譲"""
        return getattr(self.agent, name)


def wrap_agent_for_cursor(agent_instance):
    """
    エージェントをCursor対応にラップ
    
    使用例:
        remi = RemiAgent(db, api_key)
        remi_cursor = wrap_agent_for_cursor(remi)
        # Cursor内実行時は自動的にCursor Pro使用
    """
    return CursorAgentWrapper(agent_instance)


# テスト
async def test_wrapper():
    """Cursor Agent Wrapperテスト"""
    
    print("\n🧪 Testing Cursor Agent Wrapper\n")
    
    # ダミーエージェント
    class DummyAgent:
        def __init__(self):
            self.name = "TestAgent"
            self.model = "gpt-4"
            self.client = None
    
    dummy = DummyAgent()
    wrapped = CursorAgentWrapper(dummy)
    
    # テスト呼び出し
    test_prompt = "Calculate fibonacci(10)"
    
    print(f"Testing with prompt: {test_prompt}\n")
    
    response = await wrapped.call_ai(test_prompt, max_tokens=200)
    
    print(f"Success: {response['success']}")
    print(f"Model: {response['model']}")
    print(f"API Type: {response['api_type']}")
    print(f"Cost: ${response.get('cost', 0):.4f}")
    print(f"\nResponse Preview:")
    print(response['response'][:300])


if __name__ == '__main__':
    asyncio.run(test_wrapper())











