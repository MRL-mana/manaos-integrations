"""
Unit Tests — image_generation_service.feedback
================================================
FeedbackManager のユニットテスト。一時 SQLite DB で実行。
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from image_generation_service.feedback import FeedbackManager


@pytest.fixture
def fb_manager(tmp_path):
    """一時DB付き FeedbackManager"""
    db_path = tmp_path / "test_feedback.db"
    return FeedbackManager(db_path=db_path)


class TestFeedbackSubmit:
    """フィードバック投稿テスト"""

    def test_submit_basic(self, fb_manager):
        result = asyncio.run(fb_manager.submit_feedback(
            job_id="job-001",
            rating=5,
        ))
        assert result["status"] == "recorded"
        assert result["rating"] == 5
        assert result["job_id"] == "job-001"
        assert "feedback_id" in result

    def test_submit_with_all_fields(self, fb_manager):
        result = asyncio.run(fb_manager.submit_feedback(
            job_id="job-002",
            rating=3,
            user_id="user-a",
            api_key="key-1",
            tags=["good_color", "bad_anatomy"],
            comment="色はいいけど形が変",
            prompt="beautiful sunset",
            quality_score_overall=6.5,
        ))
        assert result["feedback_id"] is not None
        assert result["rating"] == 3

    def test_invalid_rating_too_low(self, fb_manager):
        with pytest.raises(ValueError, match="Rating must be 1-5"):
            asyncio.run(fb_manager.submit_feedback(job_id="x", rating=0))

    def test_invalid_rating_too_high(self, fb_manager):
        with pytest.raises(ValueError, match="Rating must be 1-5"):
            asyncio.run(fb_manager.submit_feedback(job_id="x", rating=6))


class TestFeedbackQuery:
    """フィードバック照会テスト"""

    def _seed(self, fb_manager):
        """テストデータ投入"""
        for i in range(5):
            asyncio.run(fb_manager.submit_feedback(
                job_id=f"job-{i:03d}",
                rating=i + 1,
                user_id="tester",
                tags=["tag_a"] if i % 2 == 0 else ["tag_b"],
                quality_score_overall=float(i + 4),
            ))

    def test_get_feedback_for_job(self, fb_manager):
        asyncio.run(fb_manager.submit_feedback(job_id="job-X", rating=4))
        asyncio.run(fb_manager.submit_feedback(job_id="job-X", rating=2))
        asyncio.run(fb_manager.submit_feedback(job_id="job-Y", rating=5))

        fb = asyncio.run(fb_manager.get_feedback_for_job("job-X"))
        assert len(fb) == 2
        assert all(f["job_id"] == "job-X" for f in fb)

    def test_get_aggregate_stats(self, fb_manager):
        self._seed(fb_manager)
        stats = asyncio.run(fb_manager.get_aggregate_stats(days=7))

        assert stats["total_feedback"] == 5
        assert stats["avg_rating"] == 3.0  # (1+2+3+4+5)/5
        assert stats["min_rating"] == 1
        assert stats["max_rating"] == 5
        assert stats["positive_count"] == 2  # rating 4,5
        assert stats["negative_count"] == 2  # rating 1,2

    def test_get_low_rated_jobs(self, fb_manager):
        self._seed(fb_manager)
        low = asyncio.run(fb_manager.get_low_rated_jobs(threshold=2))
        assert len(low) == 2  # rating 1, 2

    def test_get_popular_tags(self, fb_manager):
        self._seed(fb_manager)
        tags = asyncio.run(fb_manager.get_popular_tags())
        tag_names = [t["tag"] for t in tags]
        assert "tag_a" in tag_names
        assert "tag_b" in tag_names


class TestFeedbackCorrelation:
    """品質スコア相関テスト"""

    def test_correlation_with_data(self, fb_manager):
        # スコアとレーティングが正相関するデータ
        for r, s in [(1, 2.0), (2, 4.0), (3, 5.0), (4, 7.0), (5, 9.0)]:
            asyncio.run(fb_manager.submit_feedback(
                job_id=f"corr-{r}", rating=r, quality_score_overall=s,
            ))
        result = asyncio.run(fb_manager.get_quality_correlation())
        assert result["data_points"] == 5
        assert result["correlation"] > 0.9  # 強い正相関
        assert 1 in result["avg_quality_by_rating"]

    def test_correlation_empty(self, fb_manager):
        result = asyncio.run(fb_manager.get_quality_correlation())
        assert result["data_points"] == 0
        assert result["correlation"] is None

    def test_aggregate_stats_empty(self, fb_manager):
        stats = asyncio.run(fb_manager.get_aggregate_stats())
        assert stats["total_feedback"] == 0
        assert stats["avg_rating"] is None
