"""
Unit tests for scripts/misc/intent_execute_router.py
"""
import sys
from unittest.mock import MagicMock, patch

import pytest

# ── モジュールモック（インポート前に設定）──────────────────────────────────────
_ml = MagicMock()
_ml.get_logger = MagicMock(return_value=MagicMock())
_ml.get_service_logger = MagicMock(return_value=MagicMock())
sys.modules.setdefault("manaos_logger", _ml)

_paths_mod = sys.modules.get("_paths") or MagicMock()
_paths_mod.INTENT_ROUTER_PORT = 5118  # type: ignore
_paths_mod.ORCHESTRATOR_PORT = 5119  # type: ignore
_paths_mod.UNIFIED_API_PORT = 9502  # type: ignore
sys.modules["_paths"] = _paths_mod

import scripts.misc.intent_execute_router as ier


# ── TestClassifyIntent ─────────────────────────────────────────────────────
class TestClassifyIntent:
    def test_returns_intent_on_200(self):
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {"intent_type": "device_status", "confidence": 0.9}
        with patch("scripts.misc.intent_execute_router.httpx") as mock_httpx:
            mock_httpx.post.return_value = mock_resp
            result = ier.classify_intent("バッテリーは？")
        assert result["intent_type"] == "device_status"
        assert result["confidence"] == 0.9

    def test_returns_unknown_on_non_200(self):
        mock_resp = MagicMock(status_code=503)
        with patch("scripts.misc.intent_execute_router.httpx") as mock_httpx:
            mock_httpx.post.return_value = mock_resp
            result = ier.classify_intent("test")
        assert result["intent_type"] == "unknown"

    def test_returns_unknown_on_exception(self):
        with patch("scripts.misc.intent_execute_router.httpx") as mock_httpx:
            mock_httpx.post.side_effect = Exception("refused")
            result = ier.classify_intent("test")
        assert result["intent_type"] == "unknown"
        assert result["confidence"] == 0.0


# ── TestExecuteByIntent ────────────────────────────────────────────────────
class TestExecuteByIntent:
    def _setup_classify(self, mock_httpx, intent_type, confidence=0.9):
        classify_resp = MagicMock(status_code=200)
        classify_resp.json.return_value = {
            "intent_type": intent_type,
            "confidence": confidence
        }
        return classify_resp

    def test_device_status_pixel_shortcut(self):
        mock_classify = MagicMock(status_code=200)
        mock_classify.json.return_value = {"intent_type": "device_status", "confidence": 0.9}
        mock_pixel = MagicMock(status_code=200)
        mock_pixel.json.return_value = {"battery": "80%"}

        with patch("scripts.misc.intent_execute_router.httpx") as mock_httpx:
            mock_httpx.post.return_value = mock_classify
            mock_httpx.get.return_value = mock_pixel
            result = ier.execute_by_intent("pixel バッテリー残量は？")

        assert result["intent_type"] == "device_status"
        assert result.get("shortcut") is True
        assert result["result"]["battery"] == "80%"

    def test_device_status_non_pixel(self):
        mock_classify = MagicMock(status_code=200)
        mock_classify.json.return_value = {"intent_type": "device_status", "confidence": 0.9}
        mock_devices = MagicMock(status_code=200)
        mock_devices.json.return_value = {"devices": []}

        with patch("scripts.misc.intent_execute_router.httpx") as mock_httpx:
            mock_httpx.post.return_value = mock_classify
            mock_httpx.get.return_value = mock_devices
            result = ier.execute_by_intent("デバイスの状態を確認")

        assert result["intent_type"] == "device_status"
        assert result.get("shortcut") is True

    def test_file_status_shortcut(self):
        mock_classify = MagicMock(status_code=200)
        mock_classify.json.return_value = {"intent_type": "file_status", "confidence": 0.9}
        mock_inbox = MagicMock(status_code=200)
        mock_inbox.json.return_value = {"count": 5}

        with patch("scripts.misc.intent_execute_router.httpx") as mock_httpx:
            mock_httpx.post.return_value = mock_classify
            mock_httpx.get.return_value = mock_inbox
            result = ier.execute_by_intent("inbox状況を確認")

        assert result["intent_type"] == "file_status"
        assert result.get("shortcut") is True

    def test_low_confidence_falls_back_to_orchestrator(self):
        mock_classify = MagicMock(status_code=200)
        mock_classify.json.return_value = {"intent_type": "device_status", "confidence": 0.3}
        mock_orch = MagicMock(status_code=200)
        mock_orch.json.return_value = {"response": "ok"}

        with patch("scripts.misc.intent_execute_router.httpx") as mock_httpx:
            mock_httpx.post.side_effect = [mock_classify, mock_orch]
            result = ier.execute_by_intent("なんかよくわからない")

        assert result.get("shortcut") is False

    def test_unknown_intent_falls_back_to_orchestrator(self):
        mock_classify = MagicMock(status_code=200)
        mock_classify.json.return_value = {"intent_type": "unknown", "confidence": 0.95}
        mock_orch = MagicMock(status_code=200)
        mock_orch.json.return_value = {"response": "done"}

        with patch("scripts.misc.intent_execute_router.httpx") as mock_httpx:
            mock_httpx.post.side_effect = [mock_classify, mock_orch]
            result = ier.execute_by_intent("any text")

        assert result["intent_type"] == "unknown"
        assert result.get("shortcut") is False

    def test_orchestrator_failure_returns_error_dict(self):
        mock_classify = MagicMock(status_code=200)
        mock_classify.json.return_value = {"intent_type": "unknown", "confidence": 0.0}

        with patch("scripts.misc.intent_execute_router.httpx") as mock_httpx:
            mock_httpx.post.side_effect = [mock_classify, Exception("orch down")]
            result = ier.execute_by_intent("test")

        assert "error" in result

    def test_file_management_organize_shortcut(self):
        mock_classify = MagicMock(status_code=200)
        mock_classify.json.return_value = {"intent_type": "file_management", "confidence": 0.9}
        mock_organize = MagicMock(status_code=200)
        mock_organize.json.return_value = {"files": []}

        with patch("scripts.misc.intent_execute_router.httpx") as mock_httpx:
            mock_httpx.post.side_effect = [mock_classify, mock_organize]
            result = ier.execute_by_intent("ファイルを整理して")

        assert result["intent_type"] == "file_management"
        assert result.get("shortcut") is True
