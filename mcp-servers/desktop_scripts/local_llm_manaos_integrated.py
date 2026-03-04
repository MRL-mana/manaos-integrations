"""
ManaOS統合版ローカルLLMヘルパー
記憶機能と統合されたローカルLLMを使用
"""

import asyncio
import os
import httpx
from typing import List, Dict, Optional, AsyncGenerator

try:
    import ollama
    HAS_OLLAMA_LIB = True
except ImportError:
    HAS_OLLAMA_LIB = False

# デフォルト設定
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
MANAOS_API_URL = os.getenv("MANAOS_API_URL", "http://127.0.0.1:9405")


class LocalLLMWithMemory:
    """ManaOS統合版ローカルLLM（記憶機能付き）"""
    
    def __init__(
        self,
        ollama_url: str = None,
        manaos_api_url: str = None,
        default_model: str = None
    ):
        self.ollama_url = ollama_url or OLLAMA_URL
        self.manaos_api_url = manaos_api_url or MANAOS_API_URL
        self.default_model = default_model or OLLAMA_MODEL
    
    async def _get_memories(self, query: str, limit: int = 3) -> List[Dict]:
        """ManaOSから関連する記憶を取得"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # ManaOS Unified API経由で記憶を検索
                response = await client.get(
                    f"{self.manaos_api_url}/api/memory/search",
                    params={"query": query, "limit": limit}
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get("memories", [])
        except Exception as e:
            pass  # 記憶取得エラーは無視（オプション機能）
        return []
    
    async def _store_memory(self, content: str, tags: List[str] = None):
        """ManaOSに記憶を保存"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{self.manaos_api_url}/api/memory/store",
                    json={
                        "content": content,
                        "tags": tags or ["llm", "chat"]
                    }
                )
                return response.status_code == 200
        except Exception as e:
            pass  # 記憶保存エラーは無視（オプション機能）
        return False
    
    async def chat_with_memory(
        self,
        user_message: str,
        model: str = None,
        use_memory: bool = True,
        save_memory: bool = True,
        stream: bool = False
    ) -> str:
        """
        記憶機能を使用してチャット
        
        Args:
            user_message: ユーザーのメッセージ
            model: 使用するモデル名
            use_memory: 記憶機能を使用するか
            save_memory: 会話を記憶に保存するか
            stream: ストリーミングするか
        
        Returns:
            レスポンステキスト
        """
        model = model or self.default_model
        
        # 1. 関連する記憶を取得
        context_memories = []
        if use_memory:
            memories = await self._get_memories(user_message)
            context_memories = [m.get("content", "") for m in memories]
        
        # 2. メッセージを構築
        messages = []
        
        # システムプロンプトに記憶を追加
        if context_memories:
            memory_context = "\n".join([
                f"- {mem}" for mem in context_memories[:3]
            ])
            system_prompt = f"""あなたは親切なアシスタントです。
関連する過去の情報:
{memory_context}

この情報を参考にして、ユーザーの質問に答えてください。"""
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": user_message})
        
        # 3. LLMでチャット
        if stream:
            return self.chat_stream(messages, model)
        
        try:
            if HAS_OLLAMA_LIB:
                # GPU最適化オプション（RTX 5080用）
                response = ollama.chat(
                    model=model,
                    messages=messages,
                    options={
                        "num_gpu": 1,  # RTX 5080を使用
                        "num_gpu_layers": 99,  # すべてのレイヤーをGPUに
                        "num_ctx": 4096,
                        "temperature": 0.7
                    }
                )
                reply = response['message']['content']
            else:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    response = await client.post(
                        f"{self.ollama_url}/api/chat",
                        json={
                            "model": model,
                            "messages": messages,
                            "stream": False
                        }
                    )
                    if response.status_code == 200:
                        data = response.json()
                        reply = data.get("message", {}).get("content", "")
                    else:
                        raise Exception(f"Ollama API error: {response.status_code}")
            
            # 4. 重要な情報を記憶に保存
            if save_memory and len(reply) > 50:
                memory_content = f"Q: {user_message}\nA: {reply[:200]}..."
                await self._store_memory(memory_content, ["llm", "chat", "qwen"])
            
            return reply
        except Exception as e:
            raise Exception(f"LLM call error: {e}")
    
    async def chat_stream(
        self,
        messages: List[Dict],
        model: str = None
    ) -> AsyncGenerator[str, None]:
        """ストリーミング形式でチャット"""
        model = model or self.default_model
        
        try:
            if HAS_OLLAMA_LIB:
                stream = ollama.chat(
                    model=model,
                    messages=messages,
                    stream=True
                )
                for chunk in stream:
                    content = chunk.get('message', {}).get('content', '')
                    if content:
                        yield content
            else:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    async with client.stream(
                        "POST",
                        f"{self.ollama_url}/api/chat",
                        json={
                            "model": model,
                            "messages": messages,
                            "stream": True
                        }
                    ) as response:
                        async for line in response.aiter_lines():
                            if line:
                                try:
                                    import json
                                    data = json.loads(line)
                                    content = data.get("message", {}).get("content", "")
                                    if content:
                                        yield content
                                except:
                                    pass
        except Exception as e:
            raise Exception(f"Stream error: {e}")
    
    async def check_manaos_connection(self) -> bool:
        """ManaOSへの接続を確認"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # 複数のエンドポイントを試す
                endpoints = [
                    f"{self.manaos_api_url}/api/health",
                    f"{self.manaos_api_url}/health",
                    f"{self.manaos_api_url}/api/status"
                ]
                for endpoint in endpoints:
                    try:
                        response = await client.get(endpoint)
                        if response.status_code == 200:
                            return True
                    except:
                        continue
        except:
            pass
        return False


# 便利関数
async def quick_chat_with_memory(
    user_message: str,
    model: str = None,
    use_memory: bool = True
) -> str:
    """記憶機能を使用して簡単にチャット"""
    llm = LocalLLMWithMemory()
    return await llm.chat_with_memory(user_message, model=model, use_memory=use_memory)


# 使用例
async def main():
    """使用例"""
    llm = LocalLLMWithMemory()
    
    # ManaOS接続確認
    if await llm.check_manaos_connection():
        print("✅ ManaOS接続成功")
    else:
        print("⚠️ ManaOS接続失敗（記憶機能なしで動作）")
    
    # 記憶機能を使用してチャット
    reply = await llm.chat_with_memory(
        "秋田県の観光地を3つ教えて",
        model="qwen2.5:7b",
        use_memory=True,
        save_memory=True
    )
    print(f"レスポンス: {reply}")


if __name__ == "__main__":
    asyncio.run(main())

