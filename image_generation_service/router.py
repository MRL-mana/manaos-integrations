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

import json
import logging
import os
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
from .api_auth import AuthContext, require_auth
from .billing import BillingManager, Plan
from .queue import JobQueue
from .feedback import FeedbackManager
from .batch_generator import BatchGenerator
from .gpu_monitor import get_gpu_monitor
from .revenue_tracker import RevenueWriter

_log = logging.getLogger("manaos.image_api")

router = APIRouter(prefix="/api/v1/images", tags=["Image Generation"])

# シングルトン (DI で差し替え可能)
_service: Optional[ImageGenerationService] = None
_enhancer: Optional[PromptEnhancer] = None
_billing: Optional[BillingManager] = None
_queue: Optional[JobQueue] = None


def get_service() -> ImageGenerationService:
    global _service  # pylint: disable=global-statement
    if _service is None:
        _service = ImageGenerationService()
    return _service


def get_enhancer() -> PromptEnhancer:
    global _enhancer  # pylint: disable=global-statement
    if _enhancer is None:
        _enhancer = PromptEnhancer()
    return _enhancer


def get_billing() -> BillingManager:
    global _billing  # pylint: disable=global-statement
    if _billing is None:
        _billing = BillingManager()
    return _billing


def get_queue() -> JobQueue:
    global _queue  # pylint: disable=global-statement
    if _queue is None:
        _queue = JobQueue()
    return _queue


_feedback: Optional[FeedbackManager] = None
_batch: Optional[BatchGenerator] = None
_revenue: Optional[RevenueWriter] = None


def get_feedback() -> FeedbackManager:
    global _feedback  # pylint: disable=global-statement
    if _feedback is None:
        _feedback = FeedbackManager()
    return _feedback


def get_batch_generator() -> BatchGenerator:
    global _batch  # pylint: disable=global-statement
    if _batch is None:
        _batch = BatchGenerator(get_service())
    return _batch


def get_revenue() -> RevenueWriter:
    global _revenue  # pylint: disable=global-statement
    if _revenue is None:
        _revenue = RevenueWriter()
    return _revenue


class SignupRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    plan: str = Field("free", description="free/pro/enterprise")
    label: str = Field("", max_length=120)


# ─── Payment & Signup Endpoints ─────────────────────

@router.post("/payment/stripe", summary="Stripe決済セッション作成", response_model=dict)
def payment_stripe(plan: str, user_id: str):
    billing = get_billing()
    return billing.create_stripe_payment(user_id=user_id, plan=plan)


@router.post("/payment/komoju", summary="KOMOJU決済セッション作成", response_model=dict)
def payment_komoju(plan: str, user_id: str):
    billing = get_billing()
    return billing.create_komoju_payment(user_id=user_id, plan=plan)


@router.get(
    "/payment/callback",
    summary="決済完了コールバック",
    description="Stripe/KOMOJU の success_url から呼ばれるエンドポイント",
)
async def payment_callback(
    session_id: str = Query(""),
    plan: str = Query("pro"),
    user_id: str = Query(""),
    billing: BillingManager = Depends(get_billing),
):
    """決済完了後にプランをアクティベート"""
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    result = await billing.activate_subscription(
        user_id=user_id, plan=plan, session_id=session_id,
    )
    if not result.get("ok"):
        raise HTTPException(
            status_code=400,
            detail=result.get("detail", "activation failed"),
        )
    return {"status": "ok", "message": "Subscription activated", **result}


@router.post(
    "/webhook/stripe",
    summary="Stripe Webhook 受信",
    description="Stripe から checkout.session.completed イベントを受信しプランをアクティベート",
)
async def webhook_stripe():
    """
    Stripe Webhook: checkout.session.completed を処理。
    本番では署名検証 (STRIPE_WEBHOOK_SECRET) を追加する。
    署名検証は将来 middleware で実装予定。今は payload だけ処理。
    """
    # NOTE: FastAPI の Depends で Request を注入するのではなく
    # この関数自体は billing のみ依存。body は手動で取得。
    # → 将来の署名検証移行を容易にするため
    return {
        "status": "ok",
        "message": (
            "Stripe webhook endpoint ready"
            " (signature verification pending)"
        ),
        "hint": "Set STRIPE_WEBHOOK_SECRET for production",
    }


@router.post("/signup", summary="ユーザー登録とAPIキー発行", response_model=dict)
async def signup(
    req: SignupRequest,
    billing: BillingManager = Depends(get_billing),
):
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", req.email):
        raise HTTPException(status_code=400, detail="Invalid email format")

    try:
        plan = Plan(req.plan)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid plan (free/pro/enterprise)",
        ) from exc

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
        429: {"model": ErrorResponse,
              "description": "Rate limit / quota exceeded"},
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
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ConnectionError as exc:
        raise HTTPException(
            status_code=503, detail="ComfyUI is not available"
        ) from exc


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
    _auth: AuthContext = Depends(require_auth),
    bg: BatchGenerator = Depends(get_batch_generator),
):
    result = await bg.generate_batch(req, count=count, strategy=strategy)
    return {
        "best_job_id": result.best.job_id if result.best else None,
        "best_score": (
            result.best.quality_score.overall
            if result.best and result.best.quality_score
            else None
        ),
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
    _auth: AuthContext = Depends(require_auth),
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
        quality_overall = (
            job.quality_score.overall if job.quality_score else None
        )
        prompt = job.prompt or ""
    tag_list = (
        [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    )
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


# ─── Revenue KPI (for RPG dashboard) ─────────────────

@router.get(
    "/revenue/kpi",
    summary="収益 KPI サマリ（RPGダッシュボード向け）",
    description="MRR, 日次売上, アクティブユーザー, 品質スコア, RL成功率を統合",
)
async def revenue_kpi(
    auth: AuthContext = Depends(require_auth),
    billing: BillingManager = Depends(get_billing),
    fb: FeedbackManager = Depends(get_feedback),
):
    """image_gen + billing + RL + feedback を横断する統合 KPI"""
    from . import rl_bridge

    # 1) Billing KPI
    bill_data = await billing.get_billing_dashboard(auth.api_key)

    # 2) Feedback stats (過去7日)
    fb_stats = await fb.get_aggregate_stats(7)

    # 3) RL dashboard (品質→収益ループの指標)
    rl_data = rl_bridge.get_rl_dashboard() or {}

    # 4) 統合KPI
    return {
        "status": "ok",
        "billing": {
            "mrr_yen": bill_data.get("mrr_yen", 0),
            "daily_sales_yen": bill_data.get("daily_sales_yen", 0),
            "active_users_30d": bill_data.get("active_users_30d", 0),
            "active_keys": bill_data.get("active_keys", 0),
            "plan": bill_data.get("plan", "unknown"),
        },
        "quality": {
            "avg_rating": (
                fb_stats.get("avg_rating")
                if isinstance(fb_stats, dict) else None
            ),
            "total_feedback": (
                fb_stats.get("total_feedback", 0)
                if isinstance(fb_stats, dict) else 0
            ),
        },
        "rl": {
            "enabled": rl_data.get("enabled", False),
            "total_cycles": rl_data.get("total_cycles", 0),
            "success_rate": rl_data.get("success_rate"),
            "avg_score": rl_data.get("avg_score"),
            "skills_count": (
                len(rl_data.get("skills", []))
                if "skills" in rl_data else 0
            ),
        },
        "loop_health": _compute_loop_health(bill_data, fb_stats, rl_data),
    }


def _compute_loop_health(bill: dict, fb, rl: dict) -> dict:
    """品質→収益ループの健全性を0-100でスコアリング"""
    scores = []

    # 有料ユーザー存在 → 20点
    mrr = bill.get("mrr_yen", 0)
    scores.append(min(20, mrr / 500))  # 10,000円で20点満点

    # アクティブユーザー → 20点
    active = bill.get("active_users_30d", 0)
    scores.append(min(20, active * 4))  # 5人で20点

    # フィードバック量 → 20点
    fb_count = fb.get("total_feedback", 0) if isinstance(fb, dict) else 0
    scores.append(min(20, fb_count * 2))  # 10件で20点

    # RL成功率 → 20点
    sr = rl.get("success_rate")
    if sr is not None:
        scores.append(sr * 20)  # 100%で20点
    else:
        scores.append(0)

    # RL学習サイクル → 20点
    cycles = rl.get("total_cycles", 0)
    scores.append(min(20, cycles * 0.2))  # 100サイクルで20点

    total = sum(scores)
    if total < 20:
        level = "critical"
    elif total < 50:
        level = "building"
    elif total < 80:
        level = "growing"
    else:
        level = "thriving"

    return {
        "score": round(total, 1),
        "level": level,
        "breakdown": {
            "revenue": round(scores[0], 1),
            "users": round(scores[1], 1),
            "feedback": round(scores[2], 1),
            "rl_success": round(scores[3], 1),
            "rl_learning": round(scores[4], 1),
        },
    }


@router.get(
    "/revenue/history",
    summary="日次収益推移",
    description="過去N日間の日次収益・コスト・利益・生成数を返す",
)
async def revenue_history(
    days: int = 30,
    _auth: AuthContext = Depends(require_auth),
):
    """Revenue Tracker DB から日次推移を取得"""
    writer = RevenueWriter()
    history = writer.get_daily_history(days)
    summary = writer.get_summary(days)
    return {**history, "summary": summary}


@router.get(
    "/revenue/alert-check",
    summary="ループヘルス アラートチェック",
    description="loop_health が閾値を下回った場合に警告レベルを返す",
)
async def revenue_alert_check(
    auth: AuthContext = Depends(require_auth),
    billing: BillingManager = Depends(get_billing),
    fb: FeedbackManager = Depends(get_feedback),
):
    """ループヘルスの閾値チェック + 自動アラート発火"""
    from . import rl_bridge

    bill_data = await billing.get_billing_dashboard(auth.api_key)
    fb_stats = await fb.get_aggregate_stats(7)
    rl_data = rl_bridge.get_rl_dashboard() or {}
    health = _compute_loop_health(bill_data, fb_stats, rl_data)

    alerts = []
    bd = health["breakdown"]

    # 全次元の閾値チェック (各20点中)
    thresholds = {
        "revenue": (5, "収益が低下しています — MRR < ¥2,500"),
        "users": (5, "アクティブユーザー不足 — 30日間 < 2人"),
        "feedback": (5, "フィードバック不足 — 直近7日 < 3件"),
        "rl_success": (5, "RL成功率低下 — < 25%"),
        "rl_learning": (5, "RL学習停滞 — サイクル < 25 or スキル不足"),
    }
    for dim, (thr, msg) in thresholds.items():
        if bd.get(dim, 0) < thr:
            alerts.append({
                "dimension": dim,
                "value": bd.get(dim, 0),
                "threshold": thr,
                "severity": "critical" if bd.get(dim, 0) == 0 else "warning",
                "message": msg,
            })

    # Slack 通知 (critical アラートがある場合)
    critical_alerts = [a for a in alerts if a["severity"] == "critical"]
    slack_sent = False
    if critical_alerts:
        slack_sent = _send_loop_health_slack(health, critical_alerts)

    return {
        "status": "ok",
        "health": health,
        "alerts": alerts,
        "alert_count": len(alerts),
        "slack_notified": slack_sent,
    }


def _send_loop_health_slack(health: dict, alerts: list) -> bool:
    """ループヘルス低下時に Slack 通知を送信"""
    try:
        import urllib.request
        webhook_url = os.environ.get("SLACK_WEBHOOK_URL", "")
        if not webhook_url:
            _log.debug("SLACK_WEBHOOK_URL not set — skipping alert")
            return False

        lines = [
            f"🚨 *Loop Health Alert* — スコア: "
            f"{health['score']}/100 ({health['level']})",
            "",
        ]
        for a in alerts:
            emoji = "🔴" if a["severity"] == "critical" else "🟡"
            lines.append(f"{emoji} {a['dimension']}: {a['message']}")
        lines.append("\n_自動検知 by ManaOS revenue-loop_")

        payload = json.dumps({"text": "\n".join(lines)}).encode("utf-8")
        req = urllib.request.Request(
            webhook_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10):
            pass
        _log.info("Slack loop health alert sent")
        return True
    except Exception as e:  # noqa: BLE001  # pylint: disable=W0703
        _log.warning("Slack alert failed: %s", e)
        return False


# ─── Revenue Anomaly Detection ───────────────────────

@router.get(
    "/revenue/anomaly",
    summary="収益異常検知",
    description="日次収益データをAnomalyDetectorで分析し、急落・停滞・異常を検出",
)
async def revenue_anomaly(
    days: int = 30,
    _auth: AuthContext = Depends(require_auth),
):
    """RLAnything AnomalyDetector × 収益データ"""
    from .revenue_anomaly import analyze_revenue_anomalies

    writer = RevenueWriter()
    history = writer.get_daily_history(days)
    daily_data = history.get("days", [])

    result = analyze_revenue_anomalies(daily_data)
    result["period_days"] = days
    result["data_source"] = "revenue_tracker.db"
    return result


# ─── Revenue Auto-Tuning ────────────────────────────

def _get_current_rl_params() -> dict:
    """RLAnything Orchestrator から現在のパラメータスナップショットを取得"""
    try:
        from .rl_bridge import _get_orchestrator
        rl = _get_orchestrator()
        if rl is None:
            return {}
        params = {}
        if hasattr(rl, "policy_gradient"):
            pg = rl.policy_gradient
            params["learning_rate"] = getattr(pg, "lr", 0.01)
            params["temperature"] = getattr(pg, "temperature", 1.0)
        if hasattr(rl, "curriculum"):
            cur = rl.curriculum
            params["curriculum_up_threshold"] = getattr(
                cur, "up_threshold", 0.75
            )
            params["curriculum_down_threshold"] = getattr(
                cur, "down_threshold", 0.30
            )
        if hasattr(rl, "anomaly_detector"):
            ad = rl.anomaly_detector
            params["anomaly_z_threshold"] = getattr(ad, "z_threshold", 2.0)
        return params
    except Exception:  # noqa: BLE001  # pylint: disable=W0703
        return {}


@router.post(
    "/revenue/auto-tune",
    summary="収益駆動自動チューニング",
    description="収益トレンド×異常検知→RL最適パラメータを提案(apply=trueで即時適用)",
)
async def revenue_auto_tune(
    days: int = 30,
    apply: bool = False,
    auth: AuthContext = Depends(require_auth),
    billing: BillingManager = Depends(get_billing),
    fb: FeedbackManager = Depends(get_feedback),
):
    """
    収益データ → AnomalyDetector → AutoTuner → (optional) MetaController 適用
    """
    from .revenue_anomaly import analyze_revenue_anomalies
    from .revenue_autotuner import auto_tune, apply_tune_to_orchestrator
    from . import rl_bridge

    # 1) 収益データ取得
    writer = RevenueWriter()
    history = writer.get_daily_history(days)
    daily_data = history.get("days", [])

    # 2) 異常検知
    anomaly_result = analyze_revenue_anomalies(daily_data)
    alerts = anomaly_result.get("alerts", [])
    trend = anomaly_result.get(
        "trend", {"direction": "unknown", "change_pct": 0}
    )

    # 3) ループ健全度 (既存の _compute_loop_health を再利用)
    bill_data = await billing.get_billing_dashboard(auth.api_key)
    fb_stats = await fb.get_aggregate_stats(7)
    rl_data = rl_bridge.get_rl_dashboard() or {}
    health_dict = _compute_loop_health(bill_data, fb_stats, rl_data)
    loop_health = float(health_dict.get("score", 0))

    # 4) 現在のRLパラメータ
    current_params = _get_current_rl_params()

    # 5) Auto-Tune 実行
    report = auto_tune(
        revenue_trend=trend,
        anomaly_alerts=alerts,
        loop_health_score=loop_health,
        current_rl_params=current_params,
    )

    # 6) 適用 (オプション)
    apply_result = None
    if apply and report.actions:
        apply_result = apply_tune_to_orchestrator(report)

    return {
        "strategy": report.strategy,
        "actions": [a.to_dict() for a in report.actions],
        "action_count": len(report.actions),
        "applied": apply_result is not None,
        "apply_result": apply_result,
        "loop_health": {
            "before": round(loop_health, 2),
            "estimated_after": report.health_score,
        },
        "anomaly_summary": {
            "alert_count": len(alerts),
            "trend_direction": trend.get("direction", "unknown"),
            "change_pct": trend.get("change_pct", 0),
        },
        "rl_params": current_params,
        "revenue_signal": report.revenue_signal,
        "timestamp": report.timestamp,
    }


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
) -> ImageGenerateResponse | JSONResponse:
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
            "stats": svc._stats,  # pylint: disable=protected-access
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
        return HTMLResponse(
            "<h1>ManaOS Image Generation API</h1>"
            "<p><a href='/docs'>API Docs</a></p>"
        )

    return app


# uvicorn 直接起動用
router_app = create_app()
