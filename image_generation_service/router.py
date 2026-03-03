"""
FastAPI Router — /api/v1/images/*
==================================
画像生成 API の全エンドポイント:
  POST /generate         — 画像生成 (認証必須)
  POST /enhance-preview  — プロンプト強化プレビュー (認証必須)
  GET  /{job_id}         — ジョブステータス (認証必須)
  GET  /{job_id}/result  — 生成結果取得 (認証必須)
  GET  /                 — 最近の生成履歴
  GET  /dashboard        — ダッシュボード統計
  GET  /billing          — 課金情報
  GET  /queue/stats      — キュー統計
  GET  /health           — ヘルスチェック

認証方式:
  X-API-Key ヘッダー / ?api_key= クエリ / Bearer トークン

起動例:
  uvicorn image_generation_service.router:router_app --port 5560
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .models import (
    ErrorResponse,
    ImageGenerateRequest,
    ImageGenerateResponse,
    JobStatus,
    JobStatusResponse,
)
from .prompt_enhancer import PromptEnhancer
from .service import ImageGenerationService
from .api_auth import AuthContext, require_auth, optional_auth
from .billing import BillingManager, Plan
from .queue import JobQueue
from .feedback import FeedbackManager
from .batch_generator import BatchGenerator
from .gpu_monitor import get_gpu_monitor

_log = logging.getLogger("manaos.image_api")

router = APIRouter(prefix="/api/v1/images", tags=["Image Generation"])

# シングルトン (DI で差し替え可能)
_service: Optional[ImageGenerationService] = None
_enhancer: Optional[PromptEnhancer] = None
_billing: Optional[BillingManager] = None
_queue: Optional[JobQueue] = None


def get_service() -> ImageGenerationService:
    global _service
    if _service is None:
        _service = ImageGenerationService()
    return _service


def get_enhancer() -> PromptEnhancer:
    global _enhancer
    if _enhancer is None:
        _enhancer = PromptEnhancer()
    return _enhancer


def get_billing() -> BillingManager:
    global _billing
    if _billing is None:
        _billing = BillingManager()
    return _billing


def get_queue() -> JobQueue:
    global _queue
    if _queue is None:
        _queue = JobQueue()
    return _queue


_feedback: Optional[FeedbackManager] = None
_batch: Optional[BatchGenerator] = None


def get_feedback() -> FeedbackManager:
    global _feedback
    if _feedback is None:
        _feedback = FeedbackManager()
    return _feedback


def get_batch_generator() -> BatchGenerator:
    global _batch
    if _batch is None:
        _batch = BatchGenerator(get_service())
    return _batch


class SignupRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    plan: str = Field("free", description="free/pro/enterprise")
    label: str = Field("", max_length=120)


# ─── Payment & Signup Endpoints ─────────────────────

@router.post("/payment/stripe", summary="Stripe決済スタブ", response_model=dict)
def payment_stripe(plan: str, user_id: str):
    billing = get_billing()
    return billing.create_stripe_payment(user_id=user_id, plan=plan)


@router.post("/payment/komoju", summary="KOMOJU決済スタブ", response_model=dict)
def payment_komoju(plan: str, user_id: str):
    billing = get_billing()
    return billing.create_komoju_payment(user_id=user_id, plan=plan)


@router.post("/signup", summary="ユーザー登録とAPIキー発行", response_model=dict)
async def signup(
    req: SignupRequest,
    billing: BillingManager = Depends(get_billing),
):
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", req.email):
        raise HTTPException(status_code=400, detail="Invalid email format")

    try:
        plan = Plan(req.plan)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid plan (free/pro/enterprise)")

    result = await billing.register_user(
        email=req.email.strip().lower(),
        plan=plan,
        label=req.label.strip(),
    )
    return {
        "status": "ok",
        "message": "signup completed",
        **result,
    }


# ─── Endpoints ────────────────────────────────────────

@router.post(
    "/generate",
    response_model=ImageGenerateResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse, "description": "Invalid API key"},
        429: {"model": ErrorResponse, "description": "Rate limit / quota exceeded"},
        503: {"model": ErrorResponse, "description": "ComfyUI unavailable"},
    },
    summary="画像生成リクエスト",
    description="プロンプトから画像を非同期生成。job_id を返すので /images/{job_id} でポーリング。",
)
async def generate_image(
    req: ImageGenerateRequest,
    auth: AuthContext = Depends(require_auth),
    svc: ImageGenerationService = Depends(get_service),
) -> ImageGenerateResponse:
    """画像生成ジョブを投入（認証必須）"""
    # 解像度チェック
    if max(req.width, req.height) > auth.limits.max_resolution:
        raise HTTPException(
            status_code=400,
            detail=f"Resolution exceeds {auth.plan.value} plan limit "
                   f"(max {auth.limits.max_resolution}px)",
        )
    # auto_improve はProプラン以上
    if req.auto_improve and not auth.can_auto_improve:
        req = req.model_copy(update={"auto_improve": False})
    try:
        return await svc.submit_generation(req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ConnectionError:
        raise HTTPException(status_code=503, detail="ComfyUI is not available")


@router.get(
    "",
    summary="最近の生成履歴",
    description="指定件数の最近のジョブ一覧を返す",
)
async def list_recent_jobs(
    limit: int = Query(10, ge=1, le=50),
    svc: ImageGenerationService = Depends(get_service),
):
    """最近のジョブ一覧"""
    return await svc.list_recent(limit)


@router.post(
    "/enhance-preview",
    summary="プロンプト強化プレビュー",
    description="生成は実行せず、強化後のプロンプトとパラメータを返す",
)
async def enhance_preview(
    req: ImageGenerateRequest,
    enhancer: PromptEnhancer = Depends(get_enhancer),
):
    """プロンプトがどう強化されるかプレビュー"""
    enhanced = await enhancer.enhance(req)
    return {
        "original_prompt": req.prompt,
        "enhanced_prompt": enhanced.prompt,
        "original_negative": req.negative_prompt,
        "enhanced_negative": enhanced.negative_prompt,
        "original_steps": req.steps,
        "enhanced_steps": enhanced.steps,
        "original_cfg": req.cfg_scale,
        "enhanced_cfg": enhanced.cfg_scale,
        "cost_multiplier": enhancer.estimate_enhanced_cost_multiplier(req),
    }


@router.get(
    "/dashboard",
    summary="ダッシュボード統計",
    description="収益・使用量・MRR・日次売上・アクティブユーザー数を含むダッシュボード情報",
)
async def dashboard(
    auth: AuthContext = Depends(require_auth),
    billing: BillingManager = Depends(get_billing),
):
    """収益ダッシュボード（MRR等含む）"""
    return await billing.get_billing_dashboard(auth.api_key)


@router.get(
    "/billing",
    summary="課金情報",
    description="現在のプラン、使用量、残りクォータを確認",
)
async def billing_info(
    auth: AuthContext = Depends(require_auth),
    billing: BillingManager = Depends(get_billing),
):
    """課金ダッシュボード"""
    return await billing.get_billing_dashboard(auth.api_key)


@router.get(
    "/queue/stats",
    summary="キュー統計",
    description="ジョブキューの現在の状態",
)
async def queue_stats(
    queue: JobQueue = Depends(get_queue),
):
    """キュー統計情報"""
    return await queue.get_stats()


# ─── Batch Endpoints ─────────────────────────────────

@router.post(
    "/batch/generate",
    summary="バッチ画像生成",
    description="同一プロンプトでN枚生成し、品質ベストを選択",
)
async def batch_generate(
    req: ImageGenerateRequest,
    count: int = Query(3, ge=1, le=8, description="生成枚数"),
    strategy: str = Query("quality", description="選択戦略: quality/speed"),
    auth: AuthContext = Depends(require_auth),
    bg: BatchGenerator = Depends(get_batch_generator),
):
    result = await bg.generate_batch(req, count=count, strategy=strategy)
    return {
        "best_job_id": result.best.job_id if result.best else None,
        "best_score": result.best.quality_score.overall if result.best and result.best.quality_score else None,
        "total_generated": len(result.all_results),
        "total_cost_yen": result.total_cost_yen,
        "total_time_ms": result.total_time_ms,
        "score_spread": result.score_spread,
    }


@router.post(
    "/ab-compare",
    summary="A/B 比較生成",
    description="2つのリクエストを比較して勝者を返す",
)
async def ab_compare(
    req_a: ImageGenerateRequest,
    req_b: ImageGenerateRequest,
    auth: AuthContext = Depends(require_auth),
    bg: BatchGenerator = Depends(get_batch_generator),
):
    return await bg.ab_compare(req_a, req_b)


# ─── Feedback Endpoints ──────────────────────────────

@router.post(
    "/{job_id}/feedback",
    summary="ユーザーフィードバック送信",
    description="画像に対する1-5の評価とコメント",
)
async def submit_feedback(
    job_id: str,
    rating: int = Query(..., ge=1, le=5),
    comment: str = Query(""),
    tags: str = Query("", description="カンマ区切りタグ"),
    auth: AuthContext = Depends(require_auth),
    fb: FeedbackManager = Depends(get_feedback),
    svc: ImageGenerationService = Depends(get_service),
):
    job = await svc.get_result(job_id)
    quality_overall = None
    prompt = ""
    if job:
        quality_overall = job.quality_score.overall if job.quality_score else None
        prompt = job.prompt or ""
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    return await fb.submit_feedback(
        job_id=job_id,
        rating=rating,
        user_id=auth.api_key,
        api_key=auth.api_key,
        tags=tag_list,
        comment=comment,
        prompt=prompt,
        quality_score_overall=quality_overall,
    )


@router.get(
    "/feedback/stats",
    summary="フィードバック統計",
)
async def feedback_stats(
    days: int = Query(7, ge=1, le=90),
    fb: FeedbackManager = Depends(get_feedback),
):
    return await fb.get_aggregate_stats(days)


@router.get(
    "/feedback/correlation",
    summary="品質スコアとユーザー評価の相関",
)
async def feedback_correlation(
    fb: FeedbackManager = Depends(get_feedback),
):
    return await fb.get_quality_correlation()


# ─── GPU Monitoring ──────────────────────────────────

@router.get(
    "/gpu/status",
    summary="GPU ステータス",
)
async def gpu_status():
    monitor = get_gpu_monitor()
    return monitor.get_summary()


@router.get(
    "/gpu/history",
    summary="GPU 履歴統計",
)
async def gpu_history():
    monitor = get_gpu_monitor()
    return monitor.get_history_stats()


# ─── Job Endpoints (dynamic pathは末尾に配置) ───────────

@router.get(
    "/{job_id}",
    response_model=JobStatusResponse,
    responses={404: {"model": ErrorResponse}},
    summary="ジョブステータス確認",
)
async def get_job_status(
    job_id: str,
    svc: ImageGenerationService = Depends(get_service),
) -> JobStatusResponse:
    """ジョブの進捗と結果を取得"""
    result = await svc.get_status(job_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return result


@router.get(
    "/{job_id}/result",
    response_model=ImageGenerateResponse,
    responses={
        404: {"model": ErrorResponse},
        202: {"description": "Still processing"},
    },
    summary="生成結果取得",
)
async def get_job_result(
    job_id: str,
    svc: ImageGenerationService = Depends(get_service),
) -> ImageGenerateResponse:
    """完了済みジョブの結果を取得。未完了なら 202。"""
    result = await svc.get_result(job_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    if result.status != JobStatus.completed:
        return JSONResponse(
            status_code=202,
            content={"job_id": job_id, "status": result.status.value,
                     "message": "Still processing"},
        )
    return result


# ─── App Factory ─────────────────────────────────────

def create_app() -> FastAPI:
    """FastAPI アプリケーション生成"""
    from . import metrics
    from fastapi.responses import PlainTextResponse

    app = FastAPI(
        title="ManaOS Image Generation API",
        version="0.4.0",
        description="AI画像生成サービス — 品質評価・自動改善・バッチ生成・フィードバック・GPU監視・課金・キュー統合",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)

    @app.get("/health")
    async def health():
        svc = get_service()
        queue = get_queue()
        return {
            "status": "healthy",
            "service": "image_generation",
            "version": "0.4.0",
            "stats": svc._stats,
            "queue": await queue.get_stats(),
            "timestamp": datetime.now().isoformat(),
        }

    @app.get("/metrics", response_class=PlainTextResponse)
    async def prometheus_metrics():
        """Prometheus テキストフォーマットでメトリクスを公開"""
        return metrics.export_prometheus()

    @app.get("/metrics/json")
    async def json_metrics():
        """JSON 形式でメトリクスサマリを返す"""
        return metrics.export_json()

    # ランディングページ
    from fastapi.responses import HTMLResponse
    from pathlib import Path

    _LANDING_HTML = Path(__file__).resolve().parent / "landing_page.html"

    @app.get("/", response_class=HTMLResponse)
    async def landing_page():
        """ランディングページを表示"""
        if _LANDING_HTML.exists():
            return HTMLResponse(_LANDING_HTML.read_text(encoding="utf-8"))
        return HTMLResponse("<h1>ManaOS Image Generation API</h1><p><a href='/docs'>API Docs</a></p>")

    return app


# uvicorn 直接起動用
router_app = create_app()
