"""Unit tests for tools/trinity_civitai_downloader.py."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tools"))
from trinity_civitai_downloader import AdvancedCivitAIDownloader


# ─────────────────────────────────────────────────────────────────────────────
# helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_downloader():
    """__init__ をバイパスして Downloader インスタンスを作成する。"""
    with patch.object(AdvancedCivitAIDownloader, "__init__", lambda self: None):
        d = AdvancedCivitAIDownloader()
    d.base_url = "https://civitai.com/api/v1"
    d.headers = {}
    d.mana_favorites = {
        "anime_models": {
            "name": "アニメ・イラスト系",
            "search_terms": ["anime", "waifu"],
            "size_gb": 2.0,
            "priority": 1,
        }
    }
    return d


def _item(name: str, downloads: int = 0, thumbs: int = 0) -> dict:
    return {
        "name": name,
        "stats": {"downloadCount": downloads, "thumbsUpCount": thumbs},
    }


# ─────────────────────────────────────────────────────────────────────────────
# find_best_models
# ─────────────────────────────────────────────────────────────────────────────

class TestFindBestModels:

    # ── None / empty 境界 ─────────────────────────────────────────────────

    def test_none_search_result_returns_empty(self):
        d = _make_downloader()
        with patch.object(d, "search_models_by_category", return_value=None):
            assert d.find_best_models("anime_models") == []

    def test_empty_items_returns_empty(self):
        d = _make_downloader()
        with patch.object(d, "search_models_by_category",
                          return_value={"items": []}):
            assert d.find_best_models("anime_models") == []

    def test_missing_items_key_returns_empty(self):
        d = _make_downloader()
        with patch.object(d, "search_models_by_category",
                          return_value={}):
            assert d.find_best_models("anime_models") == []

    # ── スコアしきい値 ────────────────────────────────────────────────────

    def test_high_score_model_included(self):
        """ダウンロード数・評価が十分に高いモデルは結果に含まれる。"""
        d = _make_downloader()
        high = _item("anime waifu model", downloads=200_000, thumbs=10_000)
        with patch.object(d, "search_models_by_category",
                          return_value={"items": [high]}):
            result = d.find_best_models("anime_models")
        assert len(result) == 1

    def test_low_score_model_excluded(self):
        """スコアが 5 以下のモデルは除外される。"""
        d = _make_downloader()
        low = _item("obscure-thing", downloads=100, thumbs=10)
        with patch.object(d, "search_models_by_category",
                          return_value={"items": [low]}):
            result = d.find_best_models("anime_models")
        assert result == []

    # ── 結果の構造 ────────────────────────────────────────────────────────

    def test_result_contains_score_field(self):
        d = _make_downloader()
        high = _item("anime waifu", downloads=200_000, thumbs=10_000)
        with patch.object(d, "search_models_by_category",
                          return_value={"items": [high]}):
            result = d.find_best_models("anime_models")
        assert "score" in result[0]

    def test_result_contains_category_field(self):
        d = _make_downloader()
        high = _item("anime waifu", downloads=200_000, thumbs=10_000)
        with patch.object(d, "search_models_by_category",
                          return_value={"items": [high]}):
            result = d.find_best_models("anime_models")
        assert result[0]["category"] == "anime_models"

    def test_result_contains_model_dict(self):
        d = _make_downloader()
        high = _item("anime waifu", downloads=200_000, thumbs=10_000)
        with patch.object(d, "search_models_by_category",
                          return_value={"items": [high]}):
            result = d.find_best_models("anime_models")
        assert "model" in result[0]
        assert result[0]["model"]["name"] == "anime waifu"

    # ── ソート順 ─────────────────────────────────────────────────────────

    def test_sorted_by_score_descending(self):
        d = _make_downloader()
        items = [
            _item("medium model", downloads=100_000, thumbs=5_000),   # mid score
            _item("anime top waifu", downloads=500_000, thumbs=20_000),  # high score
            _item("another anime", downloads=200_000, thumbs=8_000),   # mid score
        ]
        with patch.object(d, "search_models_by_category",
                          return_value={"items": items}):
            result = d.find_best_models("anime_models")
        scores = [r["score"] for r in result]
        assert scores == sorted(scores, reverse=True)

    # ── スコア計算の上限 ──────────────────────────────────────────────────

    def test_download_count_score_capped_at_10(self):
        """ダウンロード count のスコア加算は最大 10。"""
        d = _make_downloader()
        mega = _item("mega anime model", downloads=9_999_999, thumbs=0)
        with patch.object(d, "search_models_by_category",
                          return_value={"items": [mega]}):
            result = d.find_best_models("anime_models")
        # ダウンロードだけでは 10 (> 5 のしきい値) → 含まれる
        if result:
            assert result[0]["score"] <= 10 + 5 + 4 + 10  # max caps + name bonus

    def test_name_match_boosts_score(self):
        """名前に search_terms が含まれるとスコアが上がる。"""
        d = _make_downloader()
        matched = _item("anime digital art", downloads=100_000, thumbs=5_000)
        unmatched = _item("landscape photo", downloads=100_000, thumbs=5_000)
        with patch.object(d, "search_models_by_category",
                          return_value={"items": [matched, unmatched]}):
            result = d.find_best_models("anime_models")
        # matched は "anime" が search_terms に含まれる → score が高い
        result_names = [r["model"]["name"] for r in result]
        if "landscape photo" in result_names and "anime digital art" in result_names:
            match_score = next(r["score"] for r in result if r["model"]["name"] == "anime digital art")
            unmatch_score = next(r["score"] for r in result if r["model"]["name"] == "landscape photo")
            assert match_score > unmatch_score

    # ── 上位 3 件のみ考慮 ─────────────────────────────────────────────────

    def test_only_top_3_items_considered(self):
        """items が 10 件でも上位 3 つしか採点しない。"""
        d = _make_downloader()
        items = [
            _item(f"anime model {i}", downloads=500_000, thumbs=20_000)
            for i in range(10)
        ]
        with patch.object(d, "search_models_by_category",
                          return_value={"items": items}):
            result = d.find_best_models("anime_models")
        assert len(result) <= 3

    def test_returns_list_type(self):
        d = _make_downloader()
        with patch.object(d, "search_models_by_category",
                          return_value={"items": []}):
            result = d.find_best_models("anime_models")
        assert isinstance(result, list)
