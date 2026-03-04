"""
GPU最適化版ローカルLLMヘルパー
"""

import asyncio
import os
from typing import List, Dict, Optional

try:
    import ollama
    HAS_OLLAMA_LIB = True
except ImportError:
    HAS_OLLAMA_LIB = False
    import httpx

# デフォルト設定
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")


class LocalLLMGPU:
    """GPU最適化版ローカルLLM"""
    
    def __init__(self, url: str = None, default_model: str = None):
        self.url = url or OLLAMA_URL
        self.default_model = default_model or OLLAMA_MODEL
    
    async def chat(
        self,
        messages: List[Dict],
        model: str = None,
        num_gpu: int = -1,  # -1: すべてのGPUを使用
        num_thread: int = None,  # None: 自動
        temperature: float = 0.7,
        top_p: float = 0.9
    ) -> str:
        """
        GPUを使用してチャット
        
        Args:
            messages: メッセージのリスト
            model: 使用するモデル名
            num_gpu: 使用するGPU数（-1: すべて）
            num_thread: CPUスレッド数（None: 自動）
            temperature: 温度パラメータ
            top_p: Top-pサンプリング
        """
        model = model or self.default_model
        
        try:
            if HAS_OLLAMA_LIB:
                # GPU最適化オプション
                options = {
                    "num_gpu": num_gpu,
                    "temperature": temperature,
                    "top_p": top_p
                }
                if num_thread:
                    options["num_thread"] = num_thread
                
                response = ollama.chat(
                    model=model,
                    messages=messages,
                    options=options
                )
                return response['message']['content']
            else:
                # httpxフォールバック
                async with httpx.AsyncClient(timeout=120.0) as client:
                    response = await client.post(
                        f"{self.url}/api/chat",
                        json={
                            "model": model,
                            "messages": messages,
                            "stream": False,
                            "options": {
                                "num_gpu": num_gpu,
                                "temperature": temperature,
                                "top_p": top_p
                            }
                        }
                    )
                    if response.status_code == 200:
                        data = response.json()
                        return data.get("message", {}).get("content", "")
                    else:
                        raise Exception(f"Ollama API error: {response.status_code}")
        except Exception as e:
            raise Exception(f"LLM call error: {e}")
    
    async def chat_stream(
        self,
        messages: List[Dict],
        model: str = None,
        num_gpu: int = -1
    ):
        """GPUを使用してストリーミングチャット"""
        model = model or self.default_model
        
        try:
            if HAS_OLLAMA_LIB:
                stream = ollama.chat(
                    model=model,
                    messages=messages,
                    stream=True,
                    options={"num_gpu": num_gpu}
                )
                for chunk in stream:
                    content = chunk.get('message', {}).get('content', '')
                    if content:
                        yield content
        except Exception as e:
            raise Exception(f"Stream error: {e}")


# 使用例
async def main():
    """使用例"""
    llm = LocalLLMGPU()
    
    messages = [
        {"role": "user", "content": "こんにちは"}
    ]
    
    # GPUを使用してチャット
    reply = await llm.chat(
        messages,
        model="qwen2.5:7b",
        num_gpu=-1  # すべてのGPUを使用
    )
    print(f"レスポンス: {reply}")


if __name__ == "__main__":
    asyncio.run(main())






