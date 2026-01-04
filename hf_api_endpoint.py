"""
Hugging Face統合APIエンドポイント（ManaOS統合版）
FastAPIベースのREST API
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ManaOS統合APIをインポート
from manaos_core_api import get_manaos_api

app = FastAPI(
    title="Hugging Face統合API（ManaOS統合版）",
    description="Hugging Faceモデル検索・ダウンロード・画像生成API",
    version="1.0.0"
)


# リクエストモデル
class GenerateImageRequest(BaseModel):
    prompt: str
    negative_prompt: Optional[str] = ""
    model_id: Optional[str] = "runwayml/stable-diffusion-v1-5"
    width: Optional[int] = 512
    height: Optional[int] = 512
    num_inference_steps: Optional[int] = 50
    guidance_scale: Optional[float] = 7.5
    seed: Optional[int] = None
    auto_stock: Optional[bool] = True


class SearchModelsRequest(BaseModel):
    query: str
    task: Optional[str] = None
    limit: Optional[int] = 10


class ModelInfoRequest(BaseModel):
    model_id: str


@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {
        "service": "Hugging Face統合API（ManaOS統合版）",
        "version": "1.0.0",
        "endpoints": {
            "POST /api/hf/generate": "画像生成",
            "POST /api/hf/search": "モデル検索",
            "GET /api/hf/model/{model_id}": "モデル情報取得",
            "GET /api/hf/popular": "人気モデル一覧",
            "GET /api/hf/recommended": "推奨モデル一覧"
        }
    }


@app.post("/api/hf/generate")
async def generate_image(request: GenerateImageRequest):
    """
    画像生成
    
    Args:
        request: 生成リクエスト
        
    Returns:
        生成結果
    """
    try:
        api = get_manaos_api()
        result = api.act("generate_image", {
            "prompt": request.prompt,
            "negative_prompt": request.negative_prompt,
            "model_id": request.model_id,
            "width": request.width,
            "height": request.height,
            "num_inference_steps": request.num_inference_steps,
            "guidance_scale": request.guidance_scale,
            "seed": request.seed,
            "auto_stock": request.auto_stock
        })
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
        
    except Exception as e:
        logger.error(f"画像生成エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/hf/search")
async def search_models(request: SearchModelsRequest):
    """
    モデル検索
    
    Args:
        request: 検索リクエスト
        
    Returns:
        検索結果
    """
    try:
        api = get_manaos_api()
        result = api.act("search_models", {
            "query": request.query,
            "task": request.task,
            "limit": request.limit
        })
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
        
    except Exception as e:
        logger.error(f"モデル検索エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/hf/model/{model_id}")
async def get_model_info(model_id: str):
    """
    モデル情報取得
    
    Args:
        model_id: モデルID
        
    Returns:
        モデル情報
    """
    try:
        api = get_manaos_api()
        result = api.act("get_model_info", {
            "model_id": model_id
        })
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
        
    except Exception as e:
        logger.error(f"モデル情報取得エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/hf/popular")
async def get_popular_models(task: Optional[str] = None, limit: int = 20):
    """
    人気モデル一覧取得
    
    Args:
        task: タスクタイプ（オプション）
        limit: 結果数
        
    Returns:
        人気モデル一覧
    """
    try:
        from huggingface_integration import HuggingFaceManaOSIntegration
        hf = HuggingFaceManaOSIntegration()
        results = hf.list_popular_models(task=task, limit=limit)
        return {"models": results, "count": len(results)}
        
    except Exception as e:
        logger.error(f"人気モデル取得エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/hf/recommended")
async def get_recommended_models():
    """
    推奨モデル一覧取得
    
    Returns:
        推奨モデル一覧
    """
    try:
        from huggingface_integration import HuggingFaceManaOSIntegration
        hf = HuggingFaceManaOSIntegration()
        recommendations = hf.get_recommended_models()
        return recommendations
        
    except Exception as e:
        logger.error(f"推奨モデル取得エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """ヘルスチェック"""
    return {"status": "ok", "service": "hf-api"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9510)



