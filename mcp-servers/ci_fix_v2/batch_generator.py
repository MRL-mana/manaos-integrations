"""
Batch Generator — 1プロンプト→N枚生成→ベスト選択
==================================================
batch_size > 1 の場合に複数バリエーションを生成し、
品質スコアが最高の1枚を返す。

用途:
  - 商用品質保証（3枚生成→ベスト納品）
  - A/Bテスト用比較画像生成
  - スタイル探索（同プロンプト×異スタイル）
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .models import (
    ImageGenerateRequest,
    ImageGenerateResponse,
    JobStatus,
    QualityScore,
)

_log = logging.getLogger("manaos.batch_generator")


@dataclass
class BatchResult:
    """バッチ生成結果"""
    best: Optional[ImageGenerateResponse] = None
    all_results: List[ImageGenerateResponse] = field(default_factory=list)
    best_index: int = -1
    total_cost_yen: float = 0.0
    total_time_ms: int = 0
    score_spread: float = 0.0  # max - min スコア差


class BatchGenerator:
    """
    N枚並行生成してベスト選択するジェネレータ。
    
    使い方:
        bg = BatchGenerator(service)
        result = await bg.generate_batch(request, count=3)
        best_image = result.best
    """

    def __init__(self, service):
        """
        Args:
            service: ImageGenerationService instance
        """
        self._service = service

    async def generate_batch(
        self,
        req: ImageGenerateRequest,
        count: int = 3,
        strategy: str = "quality",  # "quality" | "diversity" | "speed"
    ) -> BatchResult:
        """
        同一プロンプトでN枚を生成し、strategy に応じたベストを返す。
        
        strategy:
          quality  — 品質スコア最高の1枚
          diversity — 品質スコア分散が大きい上位を返す
          speed    — 最も早く完了した1枚
        """
        if count < 1:
            count = 1
        if count > 8:
            count = 8

        # 各バリエーション用にシードを変える
        requests = []
        for i in range(count):
            variant = req.model_copy(deep=True)
            variant.seed = -1  # ランダムシード
            variant.batch_size = 1  # 個別生成
            requests.append(variant)

        # 全バリエーションを並行生成
        _log.info("Batch generating %d variants for prompt='%s...'", count, req.prompt[:50])
        tasks = [self._service.submit_generation(r) for r in requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # エラーを除外して成功結果を収集
        successful: List[ImageGenerateResponse] = []
        for r in results:
            if isinstance(r, Exception):
                _log.warning("Batch variant failed: %s", r)
                continue
            if isinstance(r, ImageGenerateResponse) and r.status == JobStatus.completed:
                successful.append(r)

        if not successful:
            return BatchResult(all_results=[r for r in results if isinstance(r, ImageGenerateResponse)])

        # ベスト選択
        batch_result = BatchResult(all_results=successful)
        batch_result.total_cost_yen = sum(r.cost_estimate_yen or 0 for r in successful)
        batch_result.total_time_ms = max(r.generation_time_ms or 0 for r in successful)

        if strategy == "speed":
            # 最短生成時間
            batch_result.best = min(successful, key=lambda r: r.generation_time_ms or float("inf"))
        else:
            # 品質スコアでソート
            scored = [
                (i, r, r.quality_score.overall if r.quality_score and r.quality_score.overall else 0)
                for i, r in enumerate(successful)
            ]
            scored.sort(key=lambda x: x[2], reverse=True)

            batch_result.best = scored[0][1]
            batch_result.best_index = scored[0][0]

            if len(scored) >= 2:
                batch_result.score_spread = scored[0][2] - scored[-1][2]

        _log.info(
            "Batch complete: %d/%d succeeded, best_score=%.1f, spread=%.1f",
            len(successful), count,
            batch_result.best.quality_score.overall if batch_result.best and batch_result.best.quality_score else 0,
            batch_result.score_spread,
        )

        return batch_result

    async def ab_compare(
        self,
        req_a: ImageGenerateRequest,
        req_b: ImageGenerateRequest,
    ) -> Dict:
        """
        A/B比較: 2つのリクエストを並行実行してスコア比較。
        
        Returns:
            {
                "winner": "A" or "B",
                "a": ImageGenerateResponse,
                "b": ImageGenerateResponse,
                "score_diff": float,
                "details": {...}
            }
        """
        _log.info("A/B compare: A='%s...' vs B='%s...'", req_a.prompt[:30], req_b.prompt[:30])

        result_a, result_b = await asyncio.gather(
            self._service.submit_generation(req_a),
            self._service.submit_generation(req_b),
            return_exceptions=True,
        )

        def _score(r) -> float:
            if isinstance(r, Exception):
                return -1
            if r.quality_score and r.quality_score.overall:
                return r.quality_score.overall
            return 0

        score_a = _score(result_a)
        score_b = _score(result_b)

        winner = "A" if score_a >= score_b else "B"

        return {
            "winner": winner,
            "a": result_a if not isinstance(result_a, Exception) else None,
            "b": result_b if not isinstance(result_b, Exception) else None,
            "score_a": score_a,
            "score_b": score_b,
            "score_diff": abs(score_a - score_b),
            "details": {
                "a_time_ms": getattr(result_a, "generation_time_ms", None),
                "b_time_ms": getattr(result_b, "generation_time_ms", None),
                "a_cost": getattr(result_a, "cost_estimate_yen", None),
                "b_cost": getattr(result_b, "cost_estimate_yen", None),
            },
        }

    async def style_exploration(
        self,
        prompt: str,
        styles: Optional[List[str]] = None,
    ) -> List[Dict]:
        """
        同一プロンプトを複数スタイルで生成して比較。
        
        Returns:
            [{"style": "anime", "score": 7.5, "response": ...}, ...]
        """
        from .models import StylePreset

        if styles is None:
            styles = ["anime", "photorealistic", "illustration", "cyberpunk", "fantasy"]

        results = []
        tasks = []
        for style_name in styles:
            try:
                style = StylePreset(style_name)
            except ValueError:
                continue
            req = ImageGenerateRequest(prompt=prompt, style=style)  # type: ignore[call-arg]
            tasks.append((style_name, self._service.submit_generation(req)))

        for style_name, task in tasks:
            try:
                resp = await task
                score = resp.quality_score.overall if resp.quality_score else None
                results.append({
                    "style": style_name,
                    "score": score,
                    "status": resp.status.value,
                    "job_id": resp.job_id,
                    "time_ms": resp.generation_time_ms,
                    "response": resp,
                })
            except Exception as e:
                results.append({
                    "style": style_name,
                    "score": None,
                    "status": "failed",
                    "error": str(e),
                })

        # スコア順にソート
        results.sort(key=lambda r: r.get("score") or 0, reverse=True)
        return results
