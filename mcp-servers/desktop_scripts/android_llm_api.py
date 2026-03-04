"""
Android端末からローカルLLMにアクセスするためのAPIサーバー
ManaOS統合・記憶機能対応
"""

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import httpx
import os
import uvicorn

app = FastAPI(
    title="Android LLM API",
    description="Android端末からローカルLLMにアクセスするAPI",
    version="1.0.0"
)

# CORS設定（Androidアプリからのアクセスを許可）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では特定のオリジンのみ許可
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 設定
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
MANAOS_API_URL = os.getenv("MANAOS_API_URL", "http://127.0.0.1:9405")
API_KEY = os.getenv("ANDROID_LLM_API_KEY", "")  # オプション


class ChatRequest(BaseModel):
    """チャットリクエスト"""
    messages: List[Dict[str, str]]
    model: str = "qwen2.5:7b"
    stream: bool = False
    use_memory: bool = False
    persona: Optional[str] = None


class ChatResponse(BaseModel):
    """チャットレスポンス"""
    response: str
    model: str
    used_memory: bool = False


@app.get("/api/health")
async def health():
    """ヘルスチェック"""
    return {"status": "ok", "ollama_url": OLLAMA_URL}


@app.get("/api/models")
async def list_models():
    """利用可能なモデル一覧を取得"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{OLLAMA_URL}/api/tags")
            if response.status_code == 200:
                data = response.json()
                models = [m["name"] for m in data.get("models", [])]
                return {"models": models, "count": len(models)}
            return {"models": [], "count": 0}
    except Exception as e:
        return {"models": [], "count": 0, "error": str(e)}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """
    チャットAPI（ManaOS統合・記憶機能対応）
    """
    # APIキー認証（設定されている場合）
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            # 1. ManaOSから記憶を取得（オプション）
            memories = []
            if request.use_memory:
                try:
                    mem_response = await client.get(
                        f"{MANAOS_API_URL}/api/memory/search",
                        params={
                            "query": request.messages[-1].get("content", ""),
                            "limit": 3
                        },
                        timeout=5.0
                    )
                    if mem_response.status_code == 200:
                        memories = mem_response.json().get("memories", [])
                except:
                    pass  # ManaOS未接続時は無視
            
            # 2. メッセージを構築
            messages = request.messages.copy()
            
            # システムプロンプトを構築
            system_parts = []
            
            # 人格設定
            persona = request.persona or "あなたは親切なアシスタントです。"
            system_parts.append(persona)
            
            # 記憶を追加
            if memories:
                memory_context = "\n".join([
                    f"- {m.get('content', '')}" for m in memories[:3]
                ])
                system_parts.append(f"\n関連する過去の情報:\n{memory_context}\n\nこの情報を参考にして、ユーザーの質問に答えてください。")
            
            if system_parts:
                system_prompt = "\n".join(system_parts)
                messages.insert(0, {"role": "system", "content": system_prompt})
            
            # 3. Ollamaにリクエスト
            ollama_response = await client.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": request.model,
                    "messages": messages,
                    "stream": request.stream
                }
            )
            
            if ollama_response.status_code != 200:
                raise HTTPException(
                    status_code=ollama_response.status_code,
                    detail=f"Ollama API error: {ollama_response.text}"
                )
            
            data = ollama_response.json()
            reply = data.get("message", {}).get("content", "")
            
            # 4. 記憶に保存（オプション）
            if request.use_memory and len(reply) > 50:
                try:
                    await client.post(
                        f"{MANAOS_API_URL}/api/memory/store",
                        json={
                            "content": f"Q: {request.messages[-1].get('content', '')}\nA: {reply[:200]}...",
                            "tags": ["llm", "chat", "android"]
                        },
                        timeout=5.0
                    )
                except:
                    pass  # ManaOS未接続時は無視
            
            return ChatResponse(
                response=reply,
                model=request.model,
                used_memory=len(memories) > 0
            )
    
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Request timeout")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/status")
async def status():
    """システムステータス"""
    status_info = {
        "ollama_connected": False,
        "manaos_connected": False,
        "models_count": 0
    }
    
    # Ollama接続確認
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{OLLAMA_URL}/api/tags")
            if response.status_code == 200:
                status_info["ollama_connected"] = True
                data = response.json()
                status_info["models_count"] = len(data.get("models", []))
    except:
        pass
    
    # ManaOS接続確認
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{MANAOS_API_URL}/api/health")
            if response.status_code == 200:
                status_info["manaos_connected"] = True
    except:
        pass
    
    return status_info


if __name__ == "__main__":
    # 0.0.0.0でリッスンして外部アクセスを許可
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=11435,
        log_level="info"
    )



