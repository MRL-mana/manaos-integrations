"""
Unit Tests — image_generation_service.batch_generator
======================================================
BatchGenerator / BatchResult のユニットテスト。
service をモックして並行生成ロジックをテスト。
"""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from image_generation_service.batch_generator import BatchGenerator, BatchResult
from image_generation_service.models import (
    ImageGenerateRequest,
    ImageGenerateResponse,
    JobStatus,
    QualityScore,
)


def _make_response(score: float, time_ms: int = 5000, cost: float = 0.5) -> ImageGenerateResponse:
    """テスト用レスポンス生成"""
    return ImageGenerateResponse(  # type: ignore[call-arg]
        status=JobStatus.completed,
        prompt="test prompt",
        seed=42,
        quality_score=QualityScore(
            clip_score=0.3,
            aesthetic_score=score,
            technical_score=score,
            anatomy_score=score,
            commercial_score=score,
            overall=score,
        ),
        generation_time_ms=time_ms,
        cost_estimate_yen=cost,
    )


class TestBatchResult:
    """BatchResult データクラステスト"""

    def test_empty_result(self):
        r = BatchResult()
        assert r.best is None
        assert r.all_results == []
        assert r.best_index == -1
        assert r.total_cost_yen == 0
        assert r.score_spread == 0

    def test_with_data(self):
        resp = _make_response(7.5)
        r = BatchResult(
            best=resp,
            all_results=[resp],
            best_index=0,
            total_cost_yen=1.5,
            total_time_ms=5000,
            score_spread=2.0,
        )
        assert r.best.quality_score.overall == 7.5  # type: ignore[union-attr]
        assert r.total_cost_yen == 1.5


class TestBatchGenerator:
    """BatchGenerator テスト"""

    def _make_generator(self, responses):
        """モックサービス付き BatchGenerator"""
        mock_service = MagicMock()
        mock_service.submit_generation = AsyncMock(side_effect=responses)
        return BatchGenerator(mock_service)

    def test_generate_batch_picks_best(self):
        resps = [_make_response(5.0), _make_response(8.0), _make_response(6.0)]
        bg = self._make_generator(resps)
        req = ImageGenerateRequest(prompt="test batch")  # type: ignore[call-arg]

        result = asyncio.run(bg.generate_batch(req, count=3))
        assert result.best is not None
        assert result.best.quality_score.overall == 8.0  # type: ignore[union-attr]
        assert len(result.all_results) == 3
        assert result.score_spread == 3.0  # 8.0 - 5.0

    def test_generate_batch_speed_strategy(self):
        resps = [
            _make_response(8.0, time_ms=10000),
            _make_response(5.0, time_ms=2000),
            _make_response(7.0, time_ms=5000),
        ]
        bg = self._make_generator(resps)
        req = ImageGenerateRequest(prompt="test speed")  # type: ignore[call-arg]

        result = asyncio.run(bg.generate_batch(req, count=3, strategy="speed"))
        assert result.best.generation_time_ms == 2000  # type: ignore[union-attr]

    def test_generate_batch_count_clamped(self):
        resps = [_make_response(7.0)]
        bg = self._make_generator(resps)
        req = ImageGenerateRequest(prompt="test clamp")  # type: ignore[call-arg]

        result = asyncio.run(bg.generate_batch(req, count=0))  # clamped to 1
        assert len(result.all_results) == 1

    def test_generate_batch_handles_exceptions(self):
        resps = [_make_response(7.0), Exception("GPU OOM"), _make_response(6.0)]
        bg = self._make_generator(resps)
        req = ImageGenerateRequest(prompt="test error")  # type: ignore[call-arg]

        result = asyncio.run(bg.generate_batch(req, count=3))
        assert len(result.all_results) == 2  # 1 exception filtered

    def test_generate_batch_all_fail(self):
        resps = [Exception("fail1"), Exception("fail2")]
        bg = self._make_generator(resps)
        req = ImageGenerateRequest(prompt="test all fail")  # type: ignore[call-arg]

        result = asyncio.run(bg.generate_batch(req, count=2))
        assert result.best is None

    def test_generate_batch_total_cost(self):
        resps = [_make_response(7.0, cost=0.5), _make_response(8.0, cost=0.8)]
        bg = self._make_generator(resps)
        req = ImageGenerateRequest(prompt="test cost")  # type: ignore[call-arg]

        result = asyncio.run(bg.generate_batch(req, count=2))
        assert result.total_cost_yen == 1.3

    def test_ab_compare_a_wins(self):
        mock_service = MagicMock()
        mock_service.submit_generation = AsyncMock(side_effect=[
            _make_response(8.0),
            _make_response(5.0),
        ])
        bg = BatchGenerator(mock_service)

        req_a = ImageGenerateRequest(prompt="prompt A")  # type: ignore[call-arg]
        req_b = ImageGenerateRequest(prompt="prompt B")  # type: ignore[call-arg]

        result = asyncio.run(bg.ab_compare(req_a, req_b))
        assert result["winner"] == "A"
        assert result["score_a"] == 8.0
        assert result["score_b"] == 5.0
        assert result["score_diff"] == 3.0

    def test_ab_compare_b_wins(self):
        mock_service = MagicMock()
        mock_service.submit_generation = AsyncMock(side_effect=[
            _make_response(3.0),
            _make_response(9.0),
        ])
        bg = BatchGenerator(mock_service)

        result = asyncio.run(bg.ab_compare(
            ImageGenerateRequest(prompt="A"),  # type: ignore[call-arg]
            ImageGenerateRequest(prompt="B"),  # type: ignore[call-arg]
        ))
        assert result["winner"] == "B"

    def test_ab_compare_handles_exception(self):
        mock_service = MagicMock()
        mock_service.submit_generation = AsyncMock(side_effect=[
            _make_response(7.0),
            Exception("fail"),
        ])
        bg = BatchGenerator(mock_service)

        result = asyncio.run(bg.ab_compare(
            ImageGenerateRequest(prompt="A"),  # type: ignore[call-arg]
            ImageGenerateRequest(prompt="B"),  # type: ignore[call-arg]
        ))
        assert result["winner"] == "A"
        assert result["b"] is None
