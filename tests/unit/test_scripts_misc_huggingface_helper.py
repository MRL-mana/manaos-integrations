"""
Unit tests for scripts/misc/huggingface_helper.py
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ─── mocks ────────────────────────────────────────────────────────────────────
_ml = MagicMock()
_ml.get_service_logger.return_value = MagicMock()
sys.modules.setdefault("manaos_logger", _ml)

_hf_hub_mod = MagicMock()
_hf_api_cls = MagicMock()
_hf_hub_mod.HfApi = _hf_api_cls
_hf_hub_mod.snapshot_download = MagicMock(return_value="/cache/model")
_hf_hub_mod.utils = MagicMock()
_hf_hub_mod.utils.HfHubHTTPError = Exception  # use base Exception for easy raising
sys.modules["huggingface_hub"] = _hf_hub_mod
# utils sub-module
sys.modules["huggingface_hub.utils"] = MagicMock()

# Remove cached module
sys.modules.pop("scripts.misc.huggingface_helper", None)

from scripts.misc.huggingface_helper import HuggingFaceHelper  # noqa: E402


def _make_helper(token=None):
    obj = HuggingFaceHelper.__new__(HuggingFaceHelper)
    obj.api = MagicMock()
    obj.token = token
    return obj


# ─── Init ─────────────────────────────────────────────────────────────────────
class TestHuggingFaceHelperInit:
    def test_init_creates_api(self):
        """HfApi が呼ばれてインスタンスが生成される"""
        _hf_api_cls.reset_mock()
        helper = HuggingFaceHelper(token="hf_test")
        _hf_api_cls.assert_called_once_with(token="hf_test")

    def test_init_raises_when_unavailable(self, monkeypatch):
        """huggingface_hub が利用不可の場合は ImportError"""
        monkeypatch.setattr("scripts.misc.huggingface_helper.HF_HUB_AVAILABLE", False)
        with pytest.raises(ImportError):
            HuggingFaceHelper()


# ─── search_models ────────────────────────────────────────────────────────────
class TestSearchModels:
    def test_returns_model_list(self):
        helper = _make_helper()
        fake_model = MagicMock()
        fake_model.id = "org/model"
        fake_model.author = "org"
        fake_model.downloads = 100
        fake_model.likes = 10
        fake_model.tags = ["text-to-image"]
        fake_model.pipeline_tag = "text-to-image"
        helper.api.list_models.return_value = [fake_model]

        result = helper.search_models("stable-diffusion", task="text-to-image", limit=5)

        assert len(result) == 1
        assert result[0]["id"] == "org/model"
        assert result[0]["downloads"] == 100

    def test_returns_empty_list_on_error(self):
        helper = _make_helper()
        helper.api.list_models.side_effect = RuntimeError("API error")
        result = helper.search_models("query")
        assert result == []

    def test_passes_query_and_task_to_api(self):
        helper = _make_helper()
        helper.api.list_models.return_value = []
        helper.search_models("diffusion", task="text-to-image", limit=3)
        helper.api.list_models.assert_called_once_with(
            search="diffusion", task="text-to-image", limit=3
        )


# ─── download_model ───────────────────────────────────────────────────────────
class TestDownloadModel:
    def test_returns_path_on_success(self):
        helper = _make_helper()
        with patch(
            "scripts.misc.huggingface_helper.snapshot_download",
            return_value="/tmp/model",
        ):
            result = helper.download_model("org/model")
        assert result == Path("/tmp/model")

    def test_returns_none_on_error(self):
        helper = _make_helper()
        with patch(
            "scripts.misc.huggingface_helper.snapshot_download",
            side_effect=RuntimeError("download failed"),
        ):
            result = helper.download_model("org/model")
        assert result is None

    def test_passes_cache_dir(self):
        helper = _make_helper(token="tok")
        with patch(
            "scripts.misc.huggingface_helper.snapshot_download",
            return_value="/cache",
        ) as mock_dl:
            helper.download_model("org/model", cache_dir="/my/cache")
        mock_dl.assert_called_once_with(
            repo_id="org/model", cache_dir="/my/cache", token="tok"
        )


# ─── get_model_info ───────────────────────────────────────────────────────────
class TestGetModelInfo:
    def test_returns_info_dict(self):
        helper = _make_helper()
        fake_info = MagicMock()
        fake_info.id = "org/model"
        fake_info.author = "org"
        fake_info.downloads = 500
        fake_info.likes = 50
        fake_info.tags = ["nlp"]
        fake_info.pipeline_tag = "text-generation"
        sib = MagicMock(); sib.rfilename = "model.safetensors"
        fake_info.siblings = [sib]
        helper.api.model_info.return_value = fake_info

        result = helper.get_model_info("org/model")

        assert result["id"] == "org/model"
        assert result["downloads"] == 500
        assert "model.safetensors" in result["siblings"]

    def test_returns_none_on_error(self):
        helper = _make_helper()
        helper.api.model_info.side_effect = RuntimeError("not found")
        result = helper.get_model_info("nonexistent/model")
        assert result is None
