"""
Windows側のOllama用ManaOS統合版ローカルLLMヘルパー
記憶機能・GPUモード・ManaOS統合対応
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


class WindowsLocalLLMWithManaOS:
    """Windows側のOllama用ManaOS統合版ローカルLLM"""
    
    def __init__(
        self,
        ollama_url: str = None,  # type: ignore
        manaos_api_url: str = None,  # type: ignore
        default_model: str = None,  # type: ignore
        use_gpu: bool = True,
        persona: str = None  # type: ignore
    ):
        self.ollama_url = ollama_url or OLLAMA_URL
        self.manaos_api_url = manaos_api_url or MANAOS_API_URL
        self.default_model = default_model or OLLAMA_MODEL
        self.use_gpu = use_gpu
        self.persona = persona or "あなたは親切なアシスタントです。"
    
    async def _get_memories(self, query: str, limit: int = 3) -> List[Dict]:
        """ManaOSから関連する記憶を取得"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
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
    
    async def _store_memory(self, content: str, tags: List[str] = None):  # type: ignore
        """ManaOSに記憶を保存"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{self.manaos_api_url}/api/memory/store",
                    json={
                        "content": content,
                        "tags": tags or ["llm", "chat", "windows"]
                    }
                )
                return response.status_code == 200
        except Exception as e:
            pass  # 記憶保存エラーは無視（オプション機能）
        return False
    
    def _get_gpu_options(self) -> Dict:
        """GPUオプションを取得"""
        if not self.use_gpu:
            return {}
        
        # Windows側のOllama用GPUオプション
        # RTX 5080などの高性能GPUを想定
        return {
            "num_gpu": 1,  # GPUを使用
            "num_gpu_layers": 99,  # すべてのレイヤーをGPUに
            "num_ctx": 4096,  # コンテキストサイズ
            "temperature": 0.7,
            "top_p": 0.9,
            "top_k": 40
        }
    
    async def chat_with_memory(
        self,
        user_message: str,
        model: str = None,  # type: ignore
        use_memory: bool = True,
        save_memory: bool = True,
        persona: str = None  # type: ignore
    ) -> str:
        """
        記憶機能を使用してチャット（GPU対応）
        
        Args:
            user_message: ユーザーのメッセージ
            model: 使用するモデル名
            use_memory: 記憶機能を使用するか
            save_memory: 会話を記憶に保存するか
        
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
        system_persona = persona or self.persona
        
        if context_memories:
            memory_context = "\n".join([
                f"- {mem}" for mem in context_memories[:3]
            ])
            system_prompt = f"""{system_persona}

関連する過去の情報:
{memory_context}

この情報を参考にして、ユーザーの質問に答えてください。"""
            messages.append({"role": "system", "content": system_prompt})
        else:
            # 記憶がない場合でも人格設定を使用
            messages.append({"role": "system", "content": system_persona})
        
        messages.append({"role": "user", "content": user_message})
        
        # 3. LLMでチャット（GPUオプション付き）
        
        try:
            if HAS_OLLAMA_LIB:
                # Ollama公式クライアントを使用（GPUオプション付き）
                gpu_options = self._get_gpu_options()
                response = ollama.chat(  # type: ignore[possibly-unbound]
                    model=model,
                    messages=messages,
                    options=gpu_options if gpu_options else None
                )
                reply = response['message']['content']
            else:
                # httpxを使用（フォールバック）
                async with httpx.AsyncClient(timeout=300.0) as client:
                    json_data = {
                        "model": model,
                        "messages": messages,
                        "stream": False
                    }
                    # GPUオプションを追加
                    gpu_options = self._get_gpu_options()
                    if gpu_options:
                        json_data["options"] = gpu_options
                    
                    response = await client.post(
                        f"{self.ollama_url}/api/chat",
                        json=json_data
                    )
                    if response.status_code == 200:
                        data = response.json()
                        reply = data.get("message", {}).get("content", "")
                    else:
                        raise Exception(f"Ollama API error: {response.status_code}")
            
            # 4. 重要な情報を記憶に保存
            if save_memory and len(reply) > 50:
                memory_content = f"Q: {user_message}\nA: {reply[:200]}..."
                await self._store_memory(memory_content, ["llm", "chat", "windows"])
            
            return reply
        except Exception as e:
            raise Exception(f"LLM call error: {e}")
    
    async def chat_with_memory_stream(
        self,
        user_message: str,
        model: str = None,  # type: ignore
        use_memory: bool = True,
        persona: str = None  # type: ignore
    ) -> AsyncGenerator[str, None]:
        """記憶機能を使用してストリーミングチャット"""
        model = model or self.default_model
        
        # 1. 関連する記憶を取得
        context_memories = []
        if use_memory:
            memories = await self._get_memories(user_message)
            context_memories = [m.get("content", "") for m in memories]
        
        # 2. メッセージを構築
        messages = []
        system_persona = persona or self.persona
        
        if context_memories:
            memory_context = "\n".join([
                f"- {mem}" for mem in context_memories[:3]
            ])
            system_prompt = f"""{system_persona}

関連する過去の情報:
{memory_context}

この情報を参考にして、ユーザーの質問に答えてください。"""
            messages.append({"role": "system", "content": system_prompt})
        else:
            messages.append({"role": "system", "content": system_persona})
        
        messages.append({"role": "user", "content": user_message})
        
        # 3. ストリーミングチャット
        async for chunk in self.chat_stream(messages, model):
            yield chunk
    
    async def chat_stream(
        self,
        messages: List[Dict],
        model: str = None  # type: ignore
    ) -> AsyncGenerator[str, None]:
        """ストリーミング形式でチャット（GPU対応）"""
        model = model or self.default_model
        
        try:
            if HAS_OLLAMA_LIB:
                gpu_options = self._get_gpu_options()
                stream = ollama.chat(  # type: ignore[possibly-unbound]
                    model=model,
                    messages=messages,
                    stream=True,
                    options=gpu_options if gpu_options else None
                )
                for chunk in stream:
                    content = chunk.get('message', {}).get('content', '')
                    if content:
                        yield content
            else:
                async with httpx.AsyncClient(timeout=300.0) as client:
                    json_data = {
                        "model": model,
                        "messages": messages,
                        "stream": True
                    }
                    gpu_options = self._get_gpu_options()
                    if gpu_options:
                        json_data["options"] = gpu_options
                    
                    async with client.stream(
                        "POST",
                        f"{self.ollama_url}/api/chat",
                        json=json_data
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
    
    async def check_gpu_status(self) -> Dict:
        """GPU使用状況を確認"""
        try:
            # Ollamaのプロセス情報を取得
            import subprocess
            result = subprocess.run(
                ["ollama", "ps"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                output = result.stdout
                if "GPU" in output or "CUDA" in output:
                    return {"gpu_enabled": True, "status": output}
                else:
                    return {"gpu_enabled": False, "status": output}
        except:
            pass
        return {"gpu_enabled": False, "status": "確認不可"}


# 便利関数
async def quick_chat_with_manaos(
    user_message: str,
    model: str = None,  # type: ignore
    use_memory: bool = True,
    use_gpu: bool = True
) -> str:
    """ManaOS統合・記憶機能・GPU対応で簡単にチャット"""
    llm = WindowsLocalLLMWithManaOS(use_gpu=use_gpu)
    return await llm.chat_with_memory(
        user_message,
        model=model,
        use_memory=use_memory,
        save_memory=True
    )


# 使用例
async def main():
    """使用例"""
    llm = WindowsLocalLLMWithManaOS(use_gpu=True)
    
    # ManaOS接続確認
    print("ManaOS接続確認中...")
    if await llm.check_manaos_connection():
        print("[OK] ManaOS接続成功")
    else:
        print("[警告] ManaOS接続失敗（記憶機能なしで動作）")
    
    # GPU状態確認
    print("\nGPU状態確認中...")
    gpu_status = await llm.check_gpu_status()
    print(f"GPU有効: {gpu_status.get('gpu_enabled', False)}")
    
    # 記憶機能を使用してチャット
    print("\nチャットテスト...")
    reply = await llm.chat_with_memory(
        "こんにちは！簡単に自己紹介してください。",
        model="qwen2.5:7b",
        use_memory=True,
        save_memory=True
    )
    print(f"レスポンス: {reply}")


if __name__ == "__main__":
    asyncio.run(main())

