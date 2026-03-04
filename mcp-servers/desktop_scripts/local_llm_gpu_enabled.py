"""
GPU有効化版ローカルLLMヘルパー
RTX 5080を活用
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
    """GPU有効化版ローカルLLM（RTX 5080対応）"""
    
    def __init__(self, url: str = None, default_model: str = None):
        self.url = url or OLLAMA_URL
        self.default_model = default_model or OLLAMA_MODEL
        # GPU使用を明示的に有効化
        os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")
        os.environ.setdefault("OLLAMA_NUM_GPU", "1")
    
    async def chat(
        self,
        messages: List[Dict],
        model: str = None,
        use_gpu: bool = True,
        num_gpu: int = 1,  # RTX 5080を1つ使用
        temperature: float = 0.7,
        top_p: float = 0.9,
        num_ctx: int = 4096  # コンテキスト長
    ) -> str:
        """
        GPUを使用してチャット（RTX 5080最適化）
        
        Args:
            messages: メッセージのリスト
            model: 使用するモデル名
            use_gpu: GPUを使用するか
            num_gpu: 使用するGPU数
            temperature: 温度パラメータ
            top_p: Top-pサンプリング
            num_ctx: コンテキスト長
        """
        model = model or self.default_model
        
        try:
            if HAS_OLLAMA_LIB:
                # GPU最適化オプション（RTX 5080用）
                options = {
                    "temperature": temperature,
                    "top_p": top_p,
                    "num_ctx": num_ctx
                }
                
                if use_gpu:
                    options["num_gpu"] = num_gpu
                    # RTX 5080の16GB VRAMを最大限活用
                    options["num_gpu_layers"] = 99  # 可能な限りGPUレイヤーを使用
                
                response = ollama.chat(
                    model=model,
                    messages=messages,
                    options=options
                )
                return response['message']['content']
            else:
                # httpxフォールバック
                async with httpx.AsyncClient(timeout=120.0) as client:
                    payload = {
                        "model": model,
                        "messages": messages,
                        "stream": False,
                        "options": {
                            "temperature": temperature,
                            "top_p": top_p,
                            "num_ctx": num_ctx
                        }
                    }
                    
                    if use_gpu:
                        payload["options"]["num_gpu"] = num_gpu
                        payload["options"]["num_gpu_layers"] = 99
                    
                    response = await client.post(
                        f"{self.url}/api/chat",
                        json=payload
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
        use_gpu: bool = True
    ):
        """GPUを使用してストリーミングチャット"""
        model = model or self.default_model
        
        try:
            if HAS_OLLAMA_LIB:
                options = {}
                if use_gpu:
                    options["num_gpu"] = 1
                    options["num_gpu_layers"] = 99
                
                stream = ollama.chat(
                    model=model,
                    messages=messages,
                    stream=True,
                    options=options
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
        {"role": "user", "content": "RTX 5080を使ってこんにちはと返事して"}
    ]
    
    # GPUを使用してチャット
    reply = await llm.chat(
        messages,
        model="qwen2.5:7b",
        use_gpu=True
    )
    print(f"レスポンス: {reply}")


if __name__ == "__main__":
    asyncio.run(main())






