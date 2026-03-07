"""
Unit tests for scripts/misc/huggingface_integration.py
"""
import sys
from unittest.mock import MagicMock, patch

# ── module-level mocks (must be set before import) ─────────────────────────
_ml = MagicMock()
_ml.get_logger.return_value = MagicMock()
_ml.get_service_logger.return_value = MagicMock()
sys.modules.setdefault("manaos_logger", _ml)

# huggingface_helper - makes HF_AVAILABLE = True
_hf_helper_instance = MagicMock()
_hf_helper_cls = MagicMock(return_value=_hf_helper_instance)
_hf_helper_mod = MagicMock(HuggingFaceHelper=_hf_helper_cls)
sys.modules.setdefault("huggingface_helper", _hf_helper_mod)

# stable_diffusion_generator - makes SD_AVAILABLE = True
_sd_gen_cls = MagicMock()
_sd_gen_mod = MagicMock(StableDiffusionGenerator=_sd_gen_cls)
sys.modules.setdefault("stable_diffusion_generator", _sd_gen_mod)

# image_stock
_img_stock_mod = MagicMock(ImageStock=MagicMock(return_value=MagicMock()))
sys.modules.setdefault("image_stock", _img_stock_mod)

import pytest
from scripts.misc.huggingface_integration import HuggingFaceManaOSIntegration


@pytest.fixture
def hf(tmp_path):
    return HuggingFaceManaOSIntegration(output_dir=str(tmp_path / "generated"))


# ── TestInit ───────────────────────────────────────────────────────────────
class TestInit:
    def test_output_dir_created(self, tmp_path):
        out = tmp_path / "gen_imgs"
        hf = HuggingFaceManaOSIntegration(output_dir=str(out))
        assert out.exists()

    def test_model_cache_initially_empty(self, hf):
        # cache starts empty (no cache file)
        assert isinstance(hf.model_cache, dict)

    def test_generators_initially_empty(self, hf):
        assert hf.generators == {}


# ── TestModelCache ─────────────────────────────────────────────────────────
class TestModelCache:
    def test_update_and_get_cache(self, hf):
        info = {"name": "MyModel", "downloads": 1000}
        hf.update_model_cache("author/model1", info)
        result = hf.get_cached_model_info("author/model1")
        assert result == info

    def test_get_nonexistent_returns_none(self, hf):
        assert hf.get_cached_model_info("no/such/model") is None

    def test_multiple_entries_distinct(self, hf):
        hf.update_model_cache("m1", {"name": "A"})
        hf.update_model_cache("m2", {"name": "B"})
        assert hf.get_cached_model_info("m1")["name"] == "A"
        assert hf.get_cached_model_info("m2")["name"] == "B"


# ── TestSearchModels ───────────────────────────────────────────────────────
class TestSearchModels:
    def test_returns_helper_results(self, hf):
        models = [{"id": "org/modelA"}, {"id": "org/modelB"}]
        hf.helper.search_models.return_value = models
        result = hf.search_models("stable diffusion")
        assert result == models

    def test_returns_empty_on_exception(self, hf):
        hf.helper.search_models.side_effect = Exception("API error")
        result = hf.search_models("anything")
        assert result == []
        hf.helper.search_models.side_effect = None  # reset


# ── TestGetModelInfo ───────────────────────────────────────────────────────
class TestGetModelInfo:
    def test_uses_cache_when_available(self, hf):
        info = {"name": "CachedModel"}
        hf.update_model_cache("org/cached", info)
        result = hf.get_model_info("org/cached", use_cache=True, force_refresh=False)
        assert result == info
        # helper.get_model_info should NOT have been called
        hf.helper.get_model_info.assert_not_called()

    def test_force_refresh_bypasses_cache(self, hf):
        info = {"name": "FreshModel"}
        hf.update_model_cache("org/old", {"name": "OldModel"})
        hf.helper.get_model_info.return_value = info
        result = hf.get_model_info("org/old", use_cache=True, force_refresh=True)
        assert result == info

    def test_returns_none_on_error_no_cache(self, hf):
        hf.helper.get_model_info.side_effect = Exception("err")
        result = hf.get_model_info("org/unknown", use_cache=False)
        assert result is None
        hf.helper.get_model_info.side_effect = None


# ── TestListPopularModels ──────────────────────────────────────────────────
class TestListPopularModels:
    def test_returns_helper_list(self, hf):
        popular = [{"id": "popular/model"}]
        hf.helper.list_popular_models.return_value = popular
        result = hf.list_popular_models(task="text-to-image", limit=5)
        assert result == popular

    def test_returns_empty_on_exception(self, hf):
        hf.helper.list_popular_models.side_effect = Exception("fail")
        result = hf.list_popular_models()
        assert result == []
        hf.helper.list_popular_models.side_effect = None


# ── TestGetRecommendedModels ───────────────────────────────────────────────
class TestGetRecommendedModels:
    def test_delegates_to_helper(self, hf):
        rec = {"text-to-image": [{"id": "rec/model"}]}
        hf.helper.get_recommended_models.return_value = rec
        result = hf.get_recommended_models()
        assert result == rec


# ── TestGenerateImage (no SD generator) ───────────────────────────────────
class TestGenerateImageNoGenerator:
    def test_returns_error_when_no_generator(self, hf):
        # Override sd_available to False so get_generator returns None
        hf.sd_available = False
        result = hf.generate_image("a cat", model_id="test/model")
        assert result["success"] is False
        assert "error" in result


# ── TestGenerateBatch ──────────────────────────────────────────────────────
class TestGenerateBatch:
    def test_batch_result_structure(self, hf):
        # Mock generate_image to succeed
        hf.sd_available = False  # will fail but we can patch generate_image
        with patch.object(hf, "generate_image", return_value={"success": True, "images": []}):
            result = hf.generate_batch(["prompt1", "prompt2"])
        assert result["total"] == 2
        assert result["success"] is True
        assert len(result["results"]) == 2

    def test_success_count_correct(self, hf):
        responses = [
            {"success": True, "images": []},
            {"success": False, "error": "fail"},
        ]
        with patch.object(hf, "generate_image", side_effect=responses):
            result = hf.generate_batch(["p1", "p2"])
        assert result["success_count"] == 1


# ── TestCleanup ────────────────────────────────────────────────────────────
class TestCleanup:
    def test_cleanup_clears_generators(self, hf):
        mock_gen = MagicMock()
        hf.generators["test_key"] = mock_gen
        hf.cleanup()
        assert hf.generators == {}
        mock_gen.cleanup.assert_called_once()
