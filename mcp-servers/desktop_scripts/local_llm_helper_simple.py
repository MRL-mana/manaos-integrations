"""
母艦でローカルLLM（Ollama）を使うためのシンプルなヘルパー
"""

import asyncio
import os
from typing import List, Dict, Optional, AsyncGenerator

try:
    import ollama
    HAS_OLLAMA_LIB = True
except ImportError:
    HAS_OLLAMA_LIB = False
    import httpx
    import json

# デフォルト設定
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")


class LocalLLM:
    """ローカルLLM（Ollama）のシンプルなラッパー"""
    
    def __init__(self, url: str = None, default_model: str = None):  # type: ignore
        self.url = url or OLLAMA_URL
        self.default_model = default_model or OLLAMA_MODEL
    
    async def chat(self, messages: List[Dict], model: str = None, stream: bool = False) -> str:  # type: ignore
        """
        チャット形式でLLMを呼び出す
        
        Args:
            messages: メッセージのリスト [{"role": "user", "content": "..."}]
            model: 使用するモデル名（省略時はデフォルト）
            stream: ストリーミングするか
        
        Returns:
            レスポンステキスト（stream=Falseの場合）
        """
        model = model or self.default_model
        
        if stream:
            async for chunk in self.chat_stream(messages, model):
                pass  # ストリーミングは別メソッドで処理
            return ""
        
        try:
            if HAS_OLLAMA_LIB:
                # Ollama公式クライアントを使用
                response = ollama.chat(model=model, messages=messages)  # type: ignore[possibly-unbound]
                return response['message']['content']
            else:
                # httpxを使用（フォールバック）
                async with httpx.AsyncClient(  # type: ignore[possibly-unbound]
                    timeout=httpx.Timeout(120.0, connect=10.0),  # type: ignore[possibly-unbound]
                    limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)  # type: ignore[possibly-unbound]
                ) as client:
                    response = await client.post(
                        f"{self.url}/api/chat",
                        json={
                            "model": model,
                            "messages": messages,
                            "stream": False
                        },
                        headers={"Content-Type": "application/json"}
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        return data.get("message", {}).get("content", "")
                    else:
                        raise Exception(f"Ollama API error: {response.status_code}")
        except Exception as e:
            raise Exception(f"Ollama call error: {e}")
    
    async def chat_stream(self, messages: List[Dict], model: str = None) -> AsyncGenerator[str, None]:  # type: ignore
        """
        ストリーミング形式でチャット
        
        Yields:
            テキストチャンク
        """
        model = model or self.default_model
        
        try:
            if HAS_OLLAMA_LIB:
                # Ollama公式クライアントのストリーミング
                stream = ollama.chat(  # type: ignore[possibly-unbound]
                    model=model,
                    messages=messages,
                    stream=True
                )
                for chunk in stream:
                    content = chunk.get('message', {}).get('content', '')
                    if content:
                        yield content
            else:
                # httpxを使用（フォールバック）
                async with httpx.AsyncClient(timeout=60.0) as client:  # type: ignore[possibly-unbound]
                    async with client.stream(
                        "POST",
                        f"{self.url}/api/chat",
                        json={
                            "model": model,
                            "messages": messages,
                            "stream": True
                        }
                    ) as response:
                        async for line in response.aiter_lines():
                            if line:
                                try:
                                    data = json.loads(line)  # type: ignore[possibly-unbound]
                                    content = data.get("message", {}).get("content", "")
                                    if content:
                                        yield content
                                except:
                                    pass
        except Exception as e:
            raise Exception(f"Ollama stream error: {e}")
    
    async def generate(self, prompt: str, model: str = None) -> str:  # type: ignore
        """
        プロンプトから直接生成
        
        Args:
            prompt: プロンプトテキスト
            model: 使用するモデル名
        
        Returns:
            生成されたテキスト
        """
        model = model or self.default_model
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:  # type: ignore[possibly-unbound]
                response = await client.post(
                    f"{self.url}/api/generate",
                    json={
                        "model": model,
                        "prompt": prompt,
                        "stream": False
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("response", "")
                else:
                    raise Exception(f"Ollama API error: {response.status_code}")
        except Exception as e:
            raise Exception(f"Ollama generate error: {e}")
    
    async def list_models(self) -> List[str]:
        """利用可能なモデル一覧を取得"""
        try:
            if HAS_OLLAMA_LIB:
                response = ollama.list()  # type: ignore[possibly-unbound]
                models = response.get('models', [])
                return [m.get('name', '') for m in models]
            else:
                async with httpx.AsyncClient(timeout=5.0) as client:  # type: ignore[possibly-unbound]
                    response = await client.get(f"{self.url}/api/tags")
                    if response.status_code == 200:
                        data = response.json()
                        return [model["name"] for model in data.get("models", [])]
                    return []
        except Exception as e:
            raise Exception(f"Failed to list models: {e}")
    
    async def check_connection(self) -> bool:
        """Ollamaへの接続を確認"""
        try:
            if HAS_OLLAMA_LIB:
                ollama.list()  # 接続テスト  # type: ignore[possibly-unbound]
                return True
            else:
                async with httpx.AsyncClient(  # type: ignore[possibly-unbound]
                    timeout=httpx.Timeout(10.0, connect=5.0),  # type: ignore[possibly-unbound]
                    limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)  # type: ignore[possibly-unbound]
                ) as client:
                    response = await client.get(f"{self.url}/api/tags")
                    return response.status_code == 200
        except Exception as e:
            print(f"接続確認エラー: {e}")
            return False


# 便利関数
async def quick_chat(user_message: str, system_message: str = None, model: str = None) -> str:  # type: ignore
    """
    簡単にチャットする
    
    Args:
        user_message: ユーザーのメッセージ
        system_message: システムメッセージ（省略可）
        model: モデル名（省略可）
    
    Returns:
        レスポンステキスト
    """
    llm = LocalLLM()
    messages = []
    
    if system_message:
        messages.append({"role": "system", "content": system_message})
    
    messages.append({"role": "user", "content": user_message})
    
    return await llm.chat(messages, model=model)


async def quick_generate(prompt: str, model: str = None) -> str:  # type: ignore
    """
    簡単にテキスト生成する
    
    Args:
        prompt: プロンプト
        model: モデル名（省略可）
    
    Returns:
        生成されたテキスト
    """
    llm = LocalLLM()
    return await llm.generate(prompt, model=model)


# 使用例
async def main():
    """使用例"""
    llm = LocalLLM()
    
    # 接続確認
    if await llm.check_connection():
        print("✅ Ollama接続成功")
    else:
        print("❌ Ollama接続失敗")
        return
    
    # モデル一覧
    models = await llm.list_models()
    print(f"利用可能なモデル: {len(models)}個")
    
    # チャット
    messages = [
        {"role": "system", "content": "あなたはレミ。マナの隣にいる相棒の女の子。"},
        {"role": "user", "content": "こんにちは"}
    ]
    reply = await llm.chat(messages)
    print(f"レスポンス: {reply}")
    
    # 簡単なチャット
    reply2 = await quick_chat("秋田県の観光地を3つ教えて", system_message="あなたは親切なアシスタントです。")
    print(f"簡単チャット: {reply2}")
    
    # ストリーミング
    print("\nストリーミング:")
    async for chunk in llm.chat_stream([{"role": "user", "content": "Pythonでクイックソートを実装して"}]):
        print(chunk, end="", flush=True)
    print()


if __name__ == "__main__":
    asyncio.run(main())

