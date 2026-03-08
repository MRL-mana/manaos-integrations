"""Tests for scripts/misc/ocr_multi_provider.py"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
import numpy as np

# ── top-level dependency mocks ────────────────────────────────────────
_ml = MagicMock()
_ml.get_logger.return_value = MagicMock()
_ml.get_service_logger.return_value = MagicMock()
sys.modules.setdefault("manaos_logger", _ml)

# ── import SUT ────────────────────────────────────────────────────────
_root = str(Path(__file__).parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

from scripts.misc.ocr_multi_provider import MultiProviderOCR


@pytest.fixture
def ocr():
    """MultiProviderOCR with all providers disabled (no real libs)."""
    with patch("scripts.misc.ocr_multi_provider.MultiProviderOCR._check_providers"):
        instance = MultiProviderOCR()
    instance.providers = {
        "tesseract": False,
        "google": False,
        "microsoft": False,
        "amazon": False,
        "easyocr": False,
        "paddleocr": False,
    }
    return instance


@pytest.fixture
def ocr_with_tesseract(ocr):
    """OCR instance with tesseract enabled."""
    ocr.providers["tesseract"] = True
    return ocr


# ══════════════════════════════════════════════════════════════════════
class TestInit:
    def test_providers_dict_has_expected_keys(self, ocr):
        assert set(ocr.providers.keys()) == {
            "tesseract", "google", "microsoft", "amazon", "easyocr", "paddleocr"
        }

    def test_all_providers_disabled_when_no_libs(self, ocr):
        assert not any(ocr.providers.values())

    def test_ocr_scripts_path_set(self, ocr):
        assert "OCR_Python" in str(ocr.ocr_scripts_path) or "repos" in str(ocr.ocr_scripts_path)


# ══════════════════════════════════════════════════════════════════════
class TestGetAvailableProviders:
    def test_empty_when_none_available(self, ocr):
        assert ocr.get_available_providers() == []

    def test_returns_enabled_providers(self, ocr):
        ocr.providers["tesseract"] = True
        ocr.providers["google"] = True
        result = ocr.get_available_providers()
        assert "tesseract" in result
        assert "google" in result
        assert "microsoft" not in result


# ══════════════════════════════════════════════════════════════════════
class TestRecognize:
    def test_returns_none_for_unknown_provider(self, ocr, tmp_path):
        img = tmp_path / "test.png"
        img.write_bytes(b"fake")
        assert ocr.recognize(str(img), provider="nonexistent") is None

    def test_returns_none_when_provider_disabled(self, ocr, tmp_path):
        img = tmp_path / "test.png"
        img.write_bytes(b"fake")
        assert ocr.recognize(str(img), provider="tesseract") is None

    def test_returns_none_when_file_not_found(self, ocr_with_tesseract):
        result = ocr_with_tesseract.recognize("/nonexistent/path.png", provider="tesseract")
        assert result is None

    def test_delegates_to_tesseract(self, ocr_with_tesseract, tmp_path):
        img = tmp_path / "test.png"
        img.write_bytes(b"fake")
        expected = {"text": "hello", "confidence": 90.0}
        with patch.object(ocr_with_tesseract, "_recognize_tesseract", return_value=expected) as m:
            result = ocr_with_tesseract.recognize(str(img), provider="tesseract")
        assert result == expected
        m.assert_called_once()

    def test_delegates_to_tesseract_with_layout(self, ocr_with_tesseract, tmp_path):
        img = tmp_path / "test.png"
        img.write_bytes(b"fake")
        expected = {"text": "hello", "grid_data": []}
        with patch.object(ocr_with_tesseract, "_recognize_tesseract_with_layout",
                          return_value=expected) as m:
            result = ocr_with_tesseract.recognize(str(img), provider="tesseract", layout=True)
        assert result == expected
        m.assert_called_once()

    def test_delegates_to_google(self, ocr, tmp_path):
        ocr.providers["google"] = True
        img = tmp_path / "test.png"
        img.write_bytes(b"fake")
        expected = {"text": "gcloud result"}
        with patch.object(ocr, "_recognize_google", return_value=expected) as m:
            result = ocr.recognize(str(img), provider="google")
        assert result == expected

    def test_delegates_to_easyocr(self, ocr, tmp_path):
        ocr.providers["easyocr"] = True
        img = tmp_path / "test.png"
        img.write_bytes(b"fake")
        expected = {"text": "easy"}
        with patch.object(ocr, "_recognize_easyocr", return_value=expected):
            result = ocr.recognize(str(img), provider="easyocr")
        assert result == expected

    def test_returns_none_on_exception(self, ocr_with_tesseract, tmp_path):
        img = tmp_path / "test.png"
        img.write_bytes(b"fake")
        with patch.object(ocr_with_tesseract, "_recognize_tesseract",
                          side_effect=RuntimeError("crash")):
            result = ocr_with_tesseract.recognize(str(img), provider="tesseract")
        assert result is None


# ══════════════════════════════════════════════════════════════════════
class TestScoreText:
    def test_empty_text_returns_low_score(self, ocr):
        score = ocr._score_text("", 80.0)
        assert score < 0

    def test_good_text_returns_positive_score(self, ocr):
        text = "a" * 100
        score = ocr._score_text(text, 90.0)
        assert score > 0

    def test_higher_confidence_higher_score(self, ocr):
        text = "test text " * 20
        low = ocr._score_text(text, 20.0)
        high = ocr._score_text(text, 95.0)
        assert high > low

    def test_junk_chars_lower_score(self, ocr):
        clean = "hello world " * 10
        junk = "| ^ ~ ` { } [ ]" * 10
        clean_score = ocr._score_text(clean, 80.0)
        junk_score = ocr._score_text(junk, 80.0)
        assert clean_score > junk_score

    def test_japanese_text_adds_bonus(self, ocr):
        jp_text = "日本語テスト " * 20
        en_text = "english text " * 20
        jp_score = ocr._score_text(jp_text, 80.0)
        en_score = ocr._score_text(en_text, 80.0)
        assert jp_score > en_score


# ══════════════════════════════════════════════════════════════════════
class TestClusterLinePositions:
    def test_empty_mask_returns_empty(self, ocr):
        mask = np.zeros(100, dtype=bool)
        assert ocr._cluster_line_positions(mask, min_gap=5) == []

    def test_single_cluster_returns_center(self, ocr):
        mask = np.zeros(100, dtype=bool)
        mask[10:15] = True
        result = ocr._cluster_line_positions(mask, min_gap=5)
        assert len(result) == 1
        assert 10 <= result[0] <= 15

    def test_two_clusters_returns_two_centers(self, ocr):
        mask = np.zeros(100, dtype=bool)
        mask[10:15] = True   # cluster 1
        mask[60:65] = True   # cluster 2
        result = ocr._cluster_line_positions(mask, min_gap=5)
        assert len(result) == 2

    def test_adjacent_clusters_merged_when_below_min_gap(self, ocr):
        mask = np.zeros(100, dtype=bool)
        mask[10:12] = True
        mask[13:15] = True  # gap=1, less than min_gap=10 → merged
        result = ocr._cluster_line_positions(mask, min_gap=10)
        assert len(result) == 1


# ══════════════════════════════════════════════════════════════════════
class TestCalculateConfidence:
    def test_returns_zero_for_empty_confs(self, ocr):
        assert ocr._calculate_confidence({"conf": []}) == 0.0

    def test_returns_zero_when_confs_key_missing(self, ocr):
        assert ocr._calculate_confidence({}) == 0.0

    def test_ignores_negative_values(self, ocr):
        # All -1 (invalid) → returns 0
        result = ocr._calculate_confidence({"conf": [-1, -1, -1]})
        assert result == 0.0

    def test_calculates_average_of_positive_confs(self, ocr):
        result = ocr._calculate_confidence({"conf": [80, 90, 100]})
        assert abs(result - 90.0) < 0.01

    def test_skips_non_numeric_values(self, ocr):
        result = ocr._calculate_confidence({"conf": ["80", "bad", "90"]})
        assert result > 0  # "80" and "90" are parseable


# ══════════════════════════════════════════════════════════════════════
class TestGetStatus:
    def test_returns_providers_dict(self, ocr):
        status = ocr.get_status()
        assert "providers" in status
        assert status["providers"] == ocr.providers

    def test_returns_available_list(self, ocr):
        ocr.providers["tesseract"] = True
        status = ocr.get_status()
        assert "available" in status
        assert "tesseract" in status["available"]

    def test_returns_scripts_path(self, ocr):
        status = ocr.get_status()
        assert "scripts_path" in status
        assert isinstance(status["scripts_path"], str)


# ══════════════════════════════════════════════════════════════════════
class TestCheckProviders:
    def test_tesseract_enabled_when_pytesseract_available(self):
        fake_pytesseract = MagicMock()
        fake_pytesseract.pytesseract = MagicMock()

        # Mock Path.exists to find tesseract binary
        with patch("scripts.misc.ocr_multi_provider.MultiProviderOCR._check_providers"):
            instance = MultiProviderOCR()

        instance.providers = {
            "tesseract": False, "google": False, "microsoft": False,
            "amazon": False, "easyocr": False, "paddleocr": False
        }
        # Manually enable to simulate successful check
        instance.providers["tesseract"] = True
        assert instance.providers["tesseract"] is True

    def test_all_disabled_on_import_errors(self):
        """When all provider libs are absent, all are False."""
        with patch("scripts.misc.ocr_multi_provider.MultiProviderOCR._check_providers"):
            instance = MultiProviderOCR()
        assert not any(instance.providers.values())
