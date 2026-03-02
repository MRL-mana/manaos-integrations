"""
Image Generation Service — ビジネスロジック
=============================================
パイプライン全体を統括し、以下を接続する:
  pipeline.py        → ComfyUI での実際の生成
  scorer.py          → 品質評価
  rl_bridge.py       → RLAnything 評価ループ
  revenue_tracker.py → 収益 DB 書き込み
  billing.py         → 課金チェック

全接続済み — generate 1 回で以下が自動実行:
  1. billing.check_quota → 枠確認
  2. rl_bridge.begin_image_task → RL タスク開始
  3. pipeline.generate → ComfyUI 実行
  4. scorer.score → 品質評価 (5指標)
  5. rl_bridge.score_image_quality → RL 中間スコア
  6. billing.estimate_cost → コスト算出
  7. revenue_tracker → DB 書き込み (costs + products)
  8. rl_bridge.end_image_task → RL タスク終了 (20+サブシステム起動)
"""

from __future__ import annotations

import logging
import time
from collections import OrderedDict
from typing import Dict, List, Optional

from . import metrics
from .models import (
    ImageGenerateRequest,
    ImageGenerateResponse,
    JobStatus,
    JobStatusResponse,
)
from .pipeline import ComfyUIPipeline
from .scorer import ImageScorer
from .billing import BillingManager
from .prompt_enhancer import PromptEnhancer
from . import rl_bridge
from .revenue_tracker import RevenueWriter

_log = logging.getLogger("manaos.image_service")

# インメモリジョブストア（MVP用。Week 3 で SQLite に置き換え）
_MAX_JOBS = 1000
_AUTO_IMPROVE_THRESHOLD = 5.0  # overall がこれ未満なら自動リプロンプト
_MAX_IMPROVE_ATTEMPTS = 3      # 最大リトライ回数


class ImageGenerationService:
    """画像生成の全フローを統括 — 全サブシステム接続済み + 自動改善ループ"""

    def __init__(self):
        self._pipeline = ComfyUIPipeline()
        self._scorer = ImageScorer()
        self._billing = BillingManager()
        self._enhancer = PromptEnhancer()
        self._revenue = RevenueWriter()
        self._jobs: OrderedDict[str, ImageGenerateResponse] = OrderedDict()
        self._stats = {"total": 0, "success": 0, "failed": 0, "improved": 0}

    # ─── Public API ───────────────────────────────────

    async def submit_generation(
        self, req: ImageGenerateRequest
    ) -> ImageGenerateResponse:
        """
        生成ジョブを作成し、全パイプラインを実行:
          enhance → billing → RL begin → ComfyUI → scorer → auto-improve → revenue → RL end
        """
        self._stats["total"] += 1

        # 0) プロンプト強化
        enhanced_req = await self._enhancer.enhance(req)

        # 1) 課金チェック
        api_key = "default"  # TODO: リクエストヘッダーから取得
        if not await self._billing.check_quota(api_key):
            response = ImageGenerateResponse(
                status=JobStatus.failed,
                prompt=req.prompt,
                seed=req.seed,
                message="Daily quota exceeded (429)",
            )
            self._store_job(response)
            self._stats["failed"] += 1
            return response

        response = ImageGenerateResponse(
            status=JobStatus.queued,
            prompt=enhanced_req.prompt,
            seed=enhanced_req.seed,
            message="Queued for generation",
        )

        # ジョブ登録
        self._store_job(response)

        # 2) RLAnything タスク開始
        rl_bridge.begin_image_task(response.job_id, enhanced_req.prompt)

        # パイプライン実行
        attempt = 0
        try:
            response.status = JobStatus.processing
            start = time.monotonic()

            while attempt < _MAX_IMPROVE_ATTEMPTS:
                attempt += 1

                # 3) ComfyUI 実行
                prompt_id = await self._pipeline.generate(enhanced_req)
                response.comfyui_prompt_id = prompt_id

                # RL にツール使用を記録
                rl_bridge.log_tool_usage(
                    "comfyui_generate",
                    params={"prompt": enhanced_req.prompt[:100], "steps": enhanced_req.steps, "attempt": attempt},
                    result=prompt_id,
                    job_id=response.job_id,
                )

                elapsed_ms = int((time.monotonic() - start) * 1000)
                response.generation_time_ms = elapsed_ms

                # 4) 品質評価 (scorer)
                response.status = JobStatus.scoring
                try:
                    images = await self._pipeline.get_result_images(prompt_id)
                    if images:
                        from pathlib import Path
                        quality = await self._scorer.score(
                            image_path=Path(images[0]),
                            prompt=enhanced_req.prompt,
                        )
                        response.quality_score = quality
                        response.image_url = images[0]

                        # 5) RL 中間スコア
                        if quality.overall is not None:
                            rl_bridge.score_image_quality(
                                response.job_id,
                                quality.overall,
                                reason=f"attempt={attempt} 5-metric quality",
                            )

                            # 自動改善ループ: スコアが低ければリプロンプト
                            if (
                                enhanced_req.auto_improve
                                and quality.overall < _AUTO_IMPROVE_THRESHOLD
                                and attempt < _MAX_IMPROVE_ATTEMPTS
                            ):
                                response.status = JobStatus.improving
                                _log.info(
                                    "Job %s attempt %d score=%.1f < %.1f, retrying",
                                    response.job_id, attempt,
                                    quality.overall, _AUTO_IMPROVE_THRESHOLD,
                                )
                                # CFG 強化 + ステップ追加でリトライ
                                enhanced_req = enhanced_req.model_copy(deep=True)
                                enhanced_req.cfg_scale = min(30, enhanced_req.cfg_scale + 1.0)
                                enhanced_req.steps = min(100, enhanced_req.steps + 5)
                                enhanced_req.seed = -1  # 新しいシードで再試行
                                self._stats["improved"] += 1
                                continue  # → 再生成
                except Exception as e:
                    _log.warning("Scoring skipped: %s", e)

                break  # スコアOK or スコアリング失敗 → ループ終了

            # 6) コスト算出 & 収益記録
            cost_yen = await self._billing.estimate_cost(
                enhanced_req.width, enhanced_req.height,
                enhanced_req.steps, enhanced_req.batch_size,
            )
            response.cost_estimate_yen = cost_yen * attempt  # リトライ分も加算

            # 7) Revenue DB 書き込み
            self._revenue.record_generation_cost(
                job_id=response.job_id,
                cost_yen=response.cost_estimate_yen,
                width=enhanced_req.width,
                height=enhanced_req.height,
                steps=enhanced_req.steps,
            )
            self._revenue.record_product(
                job_id=response.job_id,
                prompt=enhanced_req.prompt,
                price_yen=response.cost_estimate_yen * 10,
                file_path=response.image_url,
                status="generated",
            )

            # 課金記録 (有料プランの場合)
            plan = await self._billing.get_plan(api_key)
            if plan.value != "free":
                self._revenue.record_revenue(
                    job_id=response.job_id,
                    amount_yen=response.cost_estimate_yen * 10,
                    source=f"plan_{plan.value}",
                )

            response.status = JobStatus.completed
            msg = f"Generated in {elapsed_ms}ms"
            if attempt > 1:
                msg += f" ({attempt} attempts, auto-improved)"
            response.message = msg
            self._stats["success"] += 1

            # メトリクス記録
            metrics.record_generation(
                status="success",
                duration_seconds=elapsed_ms / 1000,
                quality_overall=(
                    response.quality_score.overall
                    if response.quality_score else None
                ),
                cost_yen=response.cost_estimate_yen or 0,
            )

            _log.info("Job %s completed in %dms (%d attempts)", response.job_id, elapsed_ms, attempt)

        except ConnectionError as e:
            response.status = JobStatus.failed
            response.message = f"ComfyUI connection error: {e}"
            _log.error("Job %s failed: %s", response.job_id, e)
            self._stats["failed"] += 1
            metrics.record_generation(status="failed", duration_seconds=0)
            raise

        except Exception as e:
            response.status = JobStatus.failed
            response.message = f"Generation error: {e}"
            _log.error("Job %s failed: %s", response.job_id, e)
            self._stats["failed"] += 1
            metrics.record_generation(status="failed", duration_seconds=0)

        finally:
            # 8) RLAnything タスク終了 — 自動で20+サブシステム起動
            outcome = "success" if response.status == JobStatus.completed else "failed"
            quality_score = (
                response.quality_score.overall
                if response.quality_score and response.quality_score.overall
                else None
            )
            rl_bridge.end_image_task(
                job_id=response.job_id,
                outcome=outcome,
                quality_overall=quality_score,
                generation_time_ms=response.generation_time_ms,
                cost_yen=response.cost_estimate_yen,
            )

        return response

    async def get_status(self, job_id: str) -> Optional[JobStatusResponse]:
        """ジョブの現在のステータスを取得"""
        job = self._jobs.get(job_id)
        if job is None:
            return None
        progress = 100.0 if job.status == JobStatus.completed else None
        return JobStatusResponse(
            job_id=job_id,
            status=job.status,
            progress=progress,
            result=job if job.status == JobStatus.completed else None,
        )

    async def get_result(self, job_id: str) -> Optional[ImageGenerateResponse]:
        """完了済みジョブの結果取得"""
        return self._jobs.get(job_id)

    async def list_recent(self, limit: int = 10) -> List[Dict]:
        """最近の N 件のジョブサマリ"""
        items = list(self._jobs.values())[-limit:]
        return [
            {
                "job_id": j.job_id,
                "status": j.status.value,
                "prompt": j.prompt[:80],
                "created_at": j.created_at.isoformat(),
                "generation_time_ms": j.generation_time_ms,
                "quality_score": j.quality_score.overall if j.quality_score else None,
                "cost_yen": j.cost_estimate_yen,
            }
            for j in reversed(items)
        ]

    async def get_dashboard(self) -> Dict:
        """ダッシュボード統計を返す"""
        recent = list(self._jobs.values())[-100:]
        completed = [j for j in recent if j.status == JobStatus.completed]
        scores = [
            j.quality_score.overall
            for j in completed
            if j.quality_score and j.quality_score.overall is not None
        ]
        times = [j.generation_time_ms for j in completed if j.generation_time_ms]
        costs = [j.cost_estimate_yen for j in completed if j.cost_estimate_yen]

        return {
            "stats": self._stats.copy(),
            "recent_jobs_count": len(recent),
            "avg_quality": round(sum(scores) / len(scores), 2) if scores else None,
            "avg_generation_time_ms": round(sum(times) / len(times)) if times else None,
            "total_cost_yen": round(sum(costs), 4) if costs else 0,
            "quality_distribution": {
                "excellent": sum(1 for s in scores if s >= 8),
                "good": sum(1 for s in scores if 6 <= s < 8),
                "fair": sum(1 for s in scores if 4 <= s < 6),
                "poor": sum(1 for s in scores if s < 4),
            },
            "rl_dashboard": rl_bridge.get_rl_dashboard(),
        }

    # ─── Internal ─────────────────────────────────────

    def _store_job(self, job: ImageGenerateResponse):
        """ジョブをストアに保存（LRU で古いものを削除）"""
        self._jobs[job.job_id] = job
        while len(self._jobs) > _MAX_JOBS:
            self._jobs.popitem(last=False)
