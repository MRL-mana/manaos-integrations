"""
ManaOS API自動ドキュメント生成

このモジュールは、FastAPIを使用してManaOS統合APIの
OpenAPI/Swagger自動ドキュメントを生成します。
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uvicorn
import os

# ===========================
# Pydanticモデル定義
# ===========================

class HealthResponse(BaseModel):
    """ヘルスチェックレスポンス"""
    status: str = Field(..., description="サービスの状態（healthy/unhealthy）")
    timestamp: datetime = Field(..., description="チェック時刻")
    version: str = Field(..., description="APIバージョン")
    services: Dict[str, str] = Field(..., description="各サービスの状態")
    
    class Config:
        schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2026-02-16T10:30:00Z",
                "version": "2.6.0",
                "services": {
                    "unified_api": "healthy",
                    "mrl_memory": "healthy",
                    "learning_system": "healthy"
                }
            }
        }


class MemoryStoreRequest(BaseModel):
    """メモリ保存リクエスト"""
    key: str = Field(..., description="メモリキー", min_length=1, max_length=255)
    value: Any = Field(..., description="保存する値（任意のJSON形式）")
    ttl: Optional[int] = Field(None, description="有効期限（秒）", ge=1)
    tags: Optional[List[str]] = Field(None, description="検索用タグ")
    
    class Config:
        schema_extra = {
            "example": {
                "key": "user_preferences_12345",
                "value": {"theme": "dark", "language": "ja"},
                "ttl": 3600,
                "tags": ["user", "preferences"]
            }
        }


class MemoryStoreResponse(BaseModel):
    """メモリ保存レスポンス"""
    success: bool = Field(..., description="保存の成否")
    key: str = Field(..., description="保存されたキー")
    timestamp: datetime = Field(..., description="保存時刻")
    expires_at: Optional[datetime] = Field(None, description="有効期限")


class MemoryRetrieveResponse(BaseModel):
    """メモリ取得レスポンス"""
    found: bool = Field(..., description="キーが見つかったか")
    key: str = Field(..., description="リクエストされたキー")
    value: Optional[Any] = Field(None, description="保存された値")
    created_at: Optional[datetime] = Field(None, description="作成時刻")
    expires_at: Optional[datetime] = Field(None, description="有効期限")


class LearningEventRequest(BaseModel):
    """学習イベント記録リクエスト"""
    event_type: str = Field(..., description="イベントタイプ", regex="^(success|failure|optimization)$")
    context: Dict[str, Any] = Field(..., description="イベントコンテキスト")
    metadata: Optional[Dict[str, Any]] = Field(None, description="追加メタデータ")
    
    class Config:
        schema_extra = {
            "example": {
                "event_type": "success",
                "context": {
                    "task": "image_generation",
                    "model": "stable-diffusion-xl",
                    "duration_ms": 3500
                },
                "metadata": {
                    "user_id": "12345",
                    "quality_score": 0.95
                }
            }
        }


class LearningEventResponse(BaseModel):
    """学習イベント記録レスポンス"""
    success: bool = Field(..., description="記録の成否")
    event_id: str = Field(..., description="イベントID")
    recommendations: Optional[List[str]] = Field(None, description="最適化推奨事項")


class LLMRoutingRequest(BaseModel):
    """LLMルーティングリクエスト"""
    prompt: str = Field(..., description="プロンプトテキスト", min_length=1)
    max_tokens: Optional[int] = Field(None, description="最大トークン数", ge=1, le=4096)
    temperature: Optional[float] = Field(0.7, description="温度パラメータ", ge=0.0, le=2.0)
    preferred_model: Optional[str] = Field(None, description="優先モデル名")
    
    class Config:
        schema_extra = {
            "example": {
                "prompt": "日本の首都はどこですか？",
                "max_tokens": 100,
                "temperature": 0.7,
                "preferred_model": "gpt-4"
            }
        }


class LLMRoutingResponse(BaseModel):
    """LLMルーティングレスポンス"""
    model_used: str = Field(..., description="使用されたモデル")
    response: str = Field(..., description="生成されたレスポンス")
    tokens_used: int = Field(..., description="使用トークン数")
    cost_estimate: float = Field(..., description="推定コスト（USD）")
    reasoning: Optional[str] = Field(None, description="モデル選択の理由")


class ErrorResponse(BaseModel):
    """エラーレスポンス"""
    error: str = Field(..., description="エラータイプ")
    message: str = Field(..., description="エラーメッセージ")
    timestamp: datetime = Field(..., description="エラー発生時刻")
    request_id: Optional[str] = Field(None, description="リクエストID")


# ===========================
# FastAPIアプリケーション
# ===========================

app = FastAPI(
    title="ManaOS Unified API",
    description="""
    # ManaOS統合API
    
    ManaOS統合API（Unified API）は、複数のAI/MLサービスを統合し、
    統一されたインターフェースを提供します。
    
    ## 主な機能
    
    ### 🧠 メモリ管理（MRL Memory）
    - キー・バリュー形式でのデータ保存
    - TTL（Time To Live）によるデータ有効期限管理
    - タグベースの検索機能
    - キャッシュ最適化
    
    ### 📚 学習システム（Learning System）
    - イベントベースの学習データ収集
    - パフォーマンス最適化の提案
    - ユーザー行動分析
    - A/Bテスト結果の統合
    
    ### 🤖 LLMルーティング（LLM Router）
    - プロンプトの複雑度分析
    - 最適なLLMモデルの自動選択
    - コスト最適化
    - レート制限管理
    
    ### 🎨 ギャラリーAPI
    - 画像生成リクエストの管理
    - 画像メタデータの保存
    - 画像検索とフィルタリング
    
    ## 認証
    
    現在はオープンアクセスですが、本番環境では以下の認証方式をサポート予定：
    - API Key認証
    - OAuth 2.0
    - JWT Bearer Token
    
    ## レート制限
    
    - 無認証: 100リクエスト/分
    - 認証済み: 1000リクエスト/分
    - エンタープライズ: カスタマイズ可能
    
    ## サポート
    
    - GitHub: [MRL-mana/manaos-integrations](https://github.com/MRL-mana/manaos-integrations)
    - ドキュメント: [README.md](https://github.com/MRL-mana/manaos-integrations/blob/master/README.md)
    """,
    version="2.6.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={
        "name": "ManaOS Development Team",
        "url": "https://github.com/MRL-mana",
        "email": "support@manaos.io"
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    }
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===========================
# エンドポイント定義
# ===========================

@app.get(
    "/",
    summary="ルートエンドポイント",
    description="APIの基本情報を返します",
    response_model=Dict[str, str],
    tags=["General"]
)
async def root():
    """ルートエンドポイント"""
    return {
        "name": "ManaOS Unified API",
        "version": "2.6.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get(
    "/health",
    summary="ヘルスチェック",
    description="全サービスのヘルス状態をチェックします",
    response_model=HealthResponse,
    tags=["Health"],
    responses={
        200: {"description": "全サービスが正常"},
        503: {"description": "一部またはすべてのサービスに問題あり", "model": ErrorResponse}
    }
)
async def health_check():
    """ヘルスチェックエンドポイント"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "version": "2.6.0",
        "services": {
            "unified_api": "healthy",
            "mrl_memory": "healthy",
            "learning_system": "healthy",
            "llm_routing": "healthy",
            "gallery_api": "healthy"
        }
    }


@app.post(
    "/memory/store",
    summary="メモリに保存",
    description="キー・バリュー形式でデータを保存します。TTLを指定することで自動削除も可能です。",
    response_model=MemoryStoreResponse,
    tags=["Memory Management"],
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "正常に保存されました"},
        400: {"description": "リクエストが不正です", "model": ErrorResponse},
        500: {"description": "サーバーエラー", "model": ErrorResponse}
    }
)
async def store_memory(request: MemoryStoreRequest):
    """メモリ保存エンドポイント"""
    # 実装例（実際のサービスに接続）
    return {
        "success": True,
        "key": request.key,
        "timestamp": datetime.utcnow(),
        "expires_at": datetime.utcnow() if request.ttl else None
    }


@app.get(
    "/memory/retrieve/{key}",
    summary="メモリから取得",
    description="指定されたキーから保存されたデータを取得します",
    response_model=MemoryRetrieveResponse,
    tags=["Memory Management"],
    responses={
        200: {"description": "データが見つかりました"},
        404: {"description": "キーが見つかりません", "model": ErrorResponse}
    }
)
async def retrieve_memory(key: str):
    """メモリ取得エンドポイント"""
    # 実装例
    return {
        "found": True,
        "key": key,
        "value": {"example": "data"},
        "created_at": datetime.utcnow(),
        "expires_at": None
    }


@app.post(
    "/learning/event",
    summary="学習イベントを記録",
    description="システムの学習・最適化のためのイベントを記録します",
    response_model=LearningEventResponse,
    tags=["Learning System"],
    status_code=status.HTTP_201_CREATED
)
async def record_learning_event(request: LearningEventRequest):
    """学習イベント記録エンドポイント"""
    return {
        "success": True,
        "event_id": "evt_" + datetime.utcnow().strftime("%Y%m%d%H%M%S"),
        "recommendations": [
            "モデルパラメータの調整を検討してください",
            "キャッシュサイズを増やすことで性能向上が期待できます"
        ]
    }


@app.post(
    "/llm/route",
    summary="LLMルーティング",
    description="プロンプトに最適なLLMモデルを自動選択し、レスポンスを生成します",
    response_model=LLMRoutingResponse,
    tags=["LLM Routing"],
    responses={
        200: {"description": "正常にレスポンスが生成されました"},
        429: {"description": "レート制限に達しました", "model": ErrorResponse}
    }
)
async def route_llm_request(request: LLMRoutingRequest):
    """LLMルーティングエンドポイント"""
    return {
        "model_used": request.preferred_model or "gpt-3.5-turbo",
        "response": "これはサンプルレスポンスです。",
        "tokens_used": 25,
        "cost_estimate": 0.00005,
        "reasoning": "プロンプトの複雑度が低いため、コスト効率の良いモデルを選択しました"
    }


@app.get(
    "/metrics",
    summary="メトリクス取得",
    description="Prometheus形式のメトリクスを取得します",
    tags=["Monitoring"],
    response_class=JSONResponse
)
async def get_metrics():
    """メトリクスエンドポイント（Prometheus形式）"""
    # 実際にはprometheus_clientを使用
    return {
        "http_requests_total": 12345,
        "http_request_duration_seconds": 0.25,
        "active_connections": 42
    }


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 9502))
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
