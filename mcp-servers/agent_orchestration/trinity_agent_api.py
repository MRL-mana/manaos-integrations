#!/usr/bin/env python3
"""
Trinity Agent Orchestration API
LangGraph + CrewAI統合APIサーバー
"""
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ログ設定
log_dir = Path("/root/logs/agent_orchestration")
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "trinity_agent_api.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Trinity Agent Orchestration API",
    version="1.0.0",
    description="LangGraph + CrewAI統合API"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== データモデル =====


class TaskRequest(BaseModel):
    """タスクリクエスト"""
    description: str
    max_iterations: int = 10
    use_langgraph: bool = True  # True: LangGraph, False: CrewAI


class TaskResponse(BaseModel):
    """タスクレスポンス"""
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None
    timestamp: str


class PlanRequest(BaseModel):
    """プランリクエスト"""
    goal: Optional[str] = None  # ユーザーの目標（オプション）
    use_intent_predictor: bool = True  # Intent Predictorを使用するか


class PlanResponse(BaseModel):
    """プランレスポンス"""
    suggested_actions: list
    predicted_intent: Optional[dict] = None
    plan: dict
    timestamp: str


# ===== APIエンドポイント =====
@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {
        "name": "Trinity Agent Orchestration API",
        "version": "1.0.0",
        "description": "LangGraph + CrewAI統合API",
        "endpoints": {
            "/health": "ヘルスチェック",
            "/task": "タスク実行（LangGraph/CrewAI）",
            "/plan": "プラン生成（Intent Predictor統合）"
        }
    }


@app.get("/health")
async def health_check():
    """ヘルスチェック"""
    # パッケージの可用性をチェック
    langgraph_available = False
    crewai_available = False

    try:
        import langgraph
        langgraph_available = True
    except ImportError:
        pass

    try:
        import crewai
        crewai_available = True
    except ImportError:
        pass

    return {
        "status": "healthy",
        "version": "1.0.0",
        "packages": {
            "langgraph": langgraph_available,
            "crewai": crewai_available
        },
        "timestamp": datetime.now().isoformat()
    }


@app.post("/task", response_model=TaskResponse)
async def execute_task(request: TaskRequest):
    """タスクを実行"""
    try:
        if request.use_langgraph:
            # LangGraphを使用
            try:
                from langgraph_system.langgraph_trinity import run_trinity_workflow
                result = await run_trinity_workflow(
                    request.description,
                    request.max_iterations
                )
            except ImportError:
                raise HTTPException(
                    status_code=500,
                    detail="LangGraphパッケージがインストールされていません。pip install langgraph を実行してください。"
                )
        else:
            # CrewAIを使用
            try:
                from crewai_system.crewai_trinity import run_trinity_crew
                result = run_trinity_crew(request.description)
            except ImportError:
                raise HTTPException(
                    status_code=500,
                    detail="CrewAIパッケージがインストールされていません。pip install crewai を実行してください。"
                )

        return TaskResponse(
            success=result.get("success", False),
            result=result,
            timestamp=datetime.now().isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"タスク実行エラー: {e}", exc_info=True)
        return TaskResponse(
            success=False,
            error=str(e),
            timestamp=datetime.now().isoformat()
        )


@app.post("/plan", response_model=PlanResponse)
async def create_plan(request: PlanRequest):
    """プラン生成（Intent Predictor統合）"""
    try:
        intent_predictor_url = "http://localhost:5031"
        http_client = httpx.AsyncClient(timeout=10.0)

        predicted_intent = None
        suggested_actions = []

        # Intent Predictorを使用する場合
        if request.use_intent_predictor:
            try:
                predict_response = await http_client.post(
                    f"{intent_predictor_url}/predict",
                    json={
                        "now": datetime.now().isoformat(),
                        "limits": {"max_actions": 5}
                    }
                )
                predict_response.raise_for_status()
                predicted_intent = predict_response.json()
                suggested_actions = predicted_intent.get("actions", [])
                logger.info(
                    f"✅ Intent Predictor予測: {len(suggested_actions)}件のアクション")
            except Exception as e:
                logger.warning(f"⚠️ Intent Predictorエラー: {e}（続行）")

        # ユーザーの目標がある場合、それも含めてプラン生成
        if request.goal:
            # Trinity Agentでプラン生成
            task_result = await execute_task(TaskRequest(
                description=f"目標: {request.goal}\n推奨アクション: {', '.join([a.get('action', '') for a in suggested_actions])}",
                use_langgraph=False
            ))
            plan = task_result.result or {}
        else:
            # 推奨アクションのみ
            plan = {
                "suggested_actions": suggested_actions,
                "message": "ユーザーが何も言ってなくても、サジェストだけ出す"
            }

        return PlanResponse(
            suggested_actions=suggested_actions,
            predicted_intent=predicted_intent,
            plan=plan,
            timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        logger.error(f"❌ プラン生成エラー: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.on_event("startup")
async def startup():
    """起動時の初期化"""
    logger.info("🚀 Trinity Agent Orchestration API 起動中...")
    logger.info("✅ サーバー準備完了")


@app.on_event("shutdown")
async def shutdown():
    """シャットダウン時のクリーンアップ"""
    logger.info("🛑 Trinity Agent Orchestration API シャットダウン中...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=5017,
        log_level="info"
    )
