"""
Unit Tests — image_generation_service.models
=============================================
Pydantic スキーマのバリデーションテスト。外部依存ゼロ。
"""

import pytest
from datetime import datetime
from uuid import UUID

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from image_generation_service.models import (
    ImageGenerateRequest,
    ImageGenerateResponse,
    QualityScore,
    JobStatus,
    JobStatusResponse,
    ErrorResponse,
    QualityMode,
    StylePreset,
)


# ─── ImageGenerateRequest ────────────────────────────

class TestImageGenerateRequest:

    def test_minimal_request(self):
        """最小限のリクエスト（prompt のみ）"""
        req = ImageGenerateRequest(prompt="a cat")
        assert req.prompt == "a cat"
        assert req.width == 512
        assert req.height == 512
        assert req.steps == 20
        assert req.cfg_scale == 7.0
        assert req.seed == -1
        assert req.quality_mode == QualityMode.standard
        assert req.batch_size == 1
        assert req.auto_improve is False
        assert req.mufufu_mode is False
        assert req.lab_mode is False

    def test_full_request(self):
        """全フィールド指定"""
        req = ImageGenerateRequest(
            prompt="cyberpunk city",
            negative_prompt="blurry, low quality",
            width=1024,
            height=768,
            steps=50,
            cfg_scale=12.0,
            sampler="dpmpp_2m",
            scheduler="normal",
            seed=42,
            model="sd_xl_base_1.0",
            loras=[{"name": "detail_enhancer", "weight": 0.8}],
            style=StylePreset.cyberpunk,
            quality_mode=QualityMode.best,
            batch_size=4,
            auto_improve=True,
            mufufu_mode=True,
            lab_mode=True,
        )
        assert req.width == 1024
        assert req.height == 768
        assert req.steps == 50
        assert req.style == StylePreset.cyberpunk
        assert req.quality_mode == QualityMode.best
        assert len(req.loras) == 1

    def test_prompt_too_short(self):
        """空プロンプトはバリデーションエラー"""
        with pytest.raises(Exception):
            ImageGenerateRequest(prompt="")

    def test_width_bounds(self):
        """解像度の上限・下限チェック"""
        with pytest.raises(Exception):
            ImageGenerateRequest(prompt="test", width=100)
        with pytest.raises(Exception):
            ImageGenerateRequest(prompt="test", width=4096)

    def test_steps_bounds(self):
        """ステップ数の上限・下限チェック"""
        with pytest.raises(Exception):
            ImageGenerateRequest(prompt="test", steps=0)
        with pytest.raises(Exception):
            ImageGenerateRequest(prompt="test", steps=200)

    def test_cfg_bounds(self):
        """CFG の上限・下限チェック"""
        with pytest.raises(Exception):
            ImageGenerateRequest(prompt="test", cfg_scale=0.5)
        with pytest.raises(Exception):
            ImageGenerateRequest(prompt="test", cfg_scale=35.0)

    def test_batch_size_bounds(self):
        """バッチサイズの上限"""
        with pytest.raises(Exception):
            ImageGenerateRequest(prompt="test", batch_size=0)
        with pytest.raises(Exception):
            ImageGenerateRequest(prompt="test", batch_size=10)


# ─── QualityScore ────────────────────────────────────

class TestQualityScore:

    def test_all_none(self):
        """全フィールド None (初期状態)"""
        qs = QualityScore()
        assert qs.clip_score is None
        assert qs.overall is None

    def test_valid_scores(self):
        """正常値"""
        qs = QualityScore(
            clip_score=0.85,
            aesthetic_score=7.5,
            technical_score=8.0,
            anatomy_score=6.0,
            commercial_score=7.0,
            overall=7.2,
        )
        assert qs.clip_score == 0.85
        assert qs.overall == 7.2

    def test_clip_score_bounds(self):
        """CLIP スコアは 0-1"""
        with pytest.raises(Exception):
            QualityScore(clip_score=1.5)
        with pytest.raises(Exception):
            QualityScore(clip_score=-0.1)

    def test_aesthetic_score_bounds(self):
        """美的スコアは 0-10"""
        with pytest.raises(Exception):
            QualityScore(aesthetic_score=11.0)


# ─── ImageGenerateResponse ───────────────────────────

class TestImageGenerateResponse:

    def test_default_response(self):
        """デフォルトレスポンス"""
        resp = ImageGenerateResponse()
        # uuid4 形式
        UUID(resp.job_id)
        assert resp.status == JobStatus.queued
        assert resp.message == ""
        assert resp.image_url is None
        assert resp.quality_score is None
        assert isinstance(resp.created_at, datetime)

    def test_completed_response(self):
        """完了レスポンス"""
        resp = ImageGenerateResponse(
            status=JobStatus.completed,
            prompt="a cat",
            seed=42,
            image_url="/images/cat.png",
            quality_score=QualityScore(overall=8.5),
            generation_time_ms=5000,
            cost_estimate_yen=0.012,
            message="Done",
        )
        assert resp.status == JobStatus.completed
        assert resp.generation_time_ms == 5000
        assert resp.quality_score.overall == 8.5


# ─── JobStatus Enum ──────────────────────────────────

class TestJobStatus:

    def test_all_statuses(self):
        """全ステータスの存在確認"""
        statuses = [s.value for s in JobStatus]
        assert "queued" in statuses
        assert "processing" in statuses
        assert "scoring" in statuses
        assert "improving" in statuses
        assert "completed" in statuses
        assert "failed" in statuses


# ─── StylePreset Enum ────────────────────────────────

class TestStylePreset:

    def test_all_presets(self):
        """12 プリセットの存在確認"""
        assert len(StylePreset) == 12
        assert StylePreset.anime.value == "anime"
        assert StylePreset.mufufu.value == "mufufu"
        assert StylePreset.lab.value == "lab"


# ─── ErrorResponse ───────────────────────────────────

class TestErrorResponse:

    def test_basic_error(self):
        err = ErrorResponse(error="NOT_FOUND", message="Job not found")
        assert err.error == "NOT_FOUND"
        assert err.detail is None

    def test_error_with_detail(self):
        err = ErrorResponse(
            error="VALIDATION",
            message="Invalid parameter",
            detail={"field": "width", "max": 2048},
        )
        assert err.detail["field"] == "width"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
