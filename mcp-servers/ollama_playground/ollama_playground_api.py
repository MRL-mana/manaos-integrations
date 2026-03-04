#!/usr/bin/env python3
"""
Local LLM Playground: Ollama統合API
ローカルLLMの管理と実行
"""
import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ログ設定
log_dir = Path("/root/logs/ollama_playground")
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "ollama_playground.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Ollama Playground API",
    version="1.0.0",
    description="Local LLM Playground with Ollama"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== 設定 =====
class Config:
    """設定"""
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11435")
    PORT = int(os.getenv("OLLAMA_PLAYGROUND_PORT", "5016"))


# ===== データモデル =====
class ChatRequest(BaseModel):
    """チャットリクエスト"""
    model: str
    messages: List[Dict[str, str]]
    stream: bool = False
    temperature: float = 0.7
    max_tokens: Optional[int] = None


class ModelPullRequest(BaseModel):
    """モデルプルリクエスト"""
    model: str


class ModelInfo(BaseModel):
    """モデル情報"""
    name: str
    size: Optional[int] = None
    modified_at: Optional[str] = None


# ===== Ollamaクライアント =====
class OllamaClient:
    """Ollama APIクライアント"""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=300.0)  # 5分タイムアウト

    async def list_models(self) -> List[Dict[str, Any]]:
        """利用可能なモデル一覧を取得"""
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            data = response.json()
            return data.get("models", [])
        except Exception as e:
            logger.error(f"モデル一覧取得エラー: {e}")
            raise HTTPException(status_code=500, detail=f"モデル一覧取得に失敗: {e}")

    async def pull_model(self, model: str) -> Dict[str, Any]:
        """モデルをダウンロード"""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/pull",
                json={"name": model},
                timeout=600.0  # 10分タイムアウト（大きなモデル用）
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"モデルプルエラー: {e}")
            raise HTTPException(status_code=500, detail=f"モデルダウンロードに失敗: {e}")

    async def chat(self, request: ChatRequest) -> Dict[str, Any]:
        """チャット実行"""
        try:
            payload = {
                "model": request.model,
                "messages": request.messages,
                "stream": request.stream,
                "options": {
                    "temperature": request.temperature
                }
            }

            if request.max_tokens:
                payload["options"]["num_predict"] = request.max_tokens

            response = await self.client.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=300.0
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"チャットエラー: {e}")
            raise HTTPException(status_code=500, detail=f"チャット実行に失敗: {e}")

    async def generate(self, model: str, prompt: str, stream: bool = False) -> Dict[str, Any]:
        """テキスト生成"""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": stream
                },
                timeout=300.0
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"生成エラー: {e}")
            raise HTTPException(status_code=500, detail=f"テキスト生成に失敗: {e}")

    async def get_model_info(self, model: str) -> Dict[str, Any]:
        """モデル情報を取得"""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/show",
                json={"name": model},
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"モデル情報取得エラー: {e}")
            raise HTTPException(status_code=500, detail=f"モデル情報取得に失敗: {e}")


# グローバルクライアント
ollama_client = OllamaClient(Config.OLLAMA_BASE_URL)


# ===== APIエンドポイント =====
@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {
        "name": "Ollama Playground API",
        "version": "1.0.0",
        "description": "Local LLM Playground with Ollama",
        "ollama_url": Config.OLLAMA_BASE_URL,
        "endpoints": {
            "/health": "ヘルスチェック",
            "/models": "利用可能なモデル一覧",
            "/models/{model}": "モデル情報",
            "/chat": "チャット実行",
            "/generate": "テキスト生成",
            "/pull": "モデルダウンロード"
        }
    }


@app.get("/health")
async def health_check():
    """ヘルスチェック"""
    try:
        # Ollama接続確認
        response = await ollama_client.client.get(f"{Config.OLLAMA_BASE_URL}/api/tags")
        ollama_available = response.status_code == 200

        return {
            "status": "healthy" if ollama_available else "degraded",
            "version": "1.0.0",
            "ollama_available": ollama_available,
            "ollama_url": Config.OLLAMA_BASE_URL,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "version": "1.0.0",
            "ollama_available": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@app.get("/models")
async def list_models():
    """利用可能なモデル一覧"""
    models = await ollama_client.list_models()
    return {
        "models": models,
        "count": len(models),
        "timestamp": datetime.now().isoformat()
    }


@app.get("/models/{model}")
async def get_model_info(model: str):
    """モデル情報を取得"""
    info = await ollama_client.get_model_info(model)
    return {
        "model": model,
        "info": info,
        "timestamp": datetime.now().isoformat()
    }


@app.post("/chat")
async def chat(request: ChatRequest):
    """チャット実行"""
    result = await ollama_client.chat(request)
    return {
        "success": True,
        "result": result,
        "timestamp": datetime.now().isoformat()
    }


@app.post("/generate")
async def generate(model: str, prompt: str, stream: bool = False):
    """テキスト生成"""
    result = await ollama_client.generate(model, prompt, stream)
    return {
        "success": True,
        "result": result,
        "timestamp": datetime.now().isoformat()
    }


@app.post("/pull")
async def pull_model(request: ModelPullRequest):
    """モデルをダウンロード"""
    logger.info(f"📥 モデルダウンロード開始: {request.model}")
    result = await ollama_client.pull_model(request.model)
    logger.info(f"✅ モデルダウンロード完了: {request.model}")
    return {
        "success": True,
        "model": request.model,
        "result": result,
        "timestamp": datetime.now().isoformat()
    }


@app.on_event("startup")
async def startup():
    """起動時の初期化"""
    logger.info("🚀 Ollama Playground API 起動中...")
    logger.info(f"📊 Ollama URL: {Config.OLLAMA_BASE_URL}")
    logger.info(f"✅ サーバー準備完了")


@app.on_event("shutdown")
async def shutdown():
    """シャットダウン時のクリーンアップ"""
    logger.info("🛑 Ollama Playground API シャットダウン中...")
    await ollama_client.client.aclose()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=Config.PORT,
        log_level="info"
    )

