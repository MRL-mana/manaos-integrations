"""
Unit tests for scripts/misc/nectarstt_integration.py
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ── モジュールモック（インポート前に設定）─────────────────────────────────────
sys.modules.setdefault("manaos_logger", MagicMock(
    get_logger=MagicMock(return_value=MagicMock()),
    get_service_logger=MagicMock(return_value=MagicMock()),
))

import scripts.misc.nectarstt_integration as ns


# ─────────────────────────────────────────────
# NectarSTTIntegration.__init__
# ─────────────────────────────────────────────

class TestInit:
    def test_disabled_skips_availability_check(self):
        with patch.object(ns.NectarSTTIntegration, "_check_availability") as mock_check:
            obj = ns.NectarSTTIntegration(enabled=False)
        mock_check.assert_not_called()
        assert obj.enabled is False

    def test_enabled_calls_availability_check(self):
        with patch.object(ns.NectarSTTIntegration, "_check_availability",
                          return_value=False) as mock_check:
            obj = ns.NectarSTTIntegration(enabled=True)
        mock_check.assert_called_once()

    def test_available_defaults_to_false(self):
        with patch.object(ns.NectarSTTIntegration, "_check_availability",
                          return_value=False):
            obj = ns.NectarSTTIntegration()
        assert obj.available is False


# ─────────────────────────────────────────────
# _check_availability
# ─────────────────────────────────────────────

class TestCheckAvailability:
    def test_returns_false_when_engine_not_found(self):
        obj = ns.NectarSTTIntegration(enabled=False)
        with patch("pathlib.Path.exists", return_value=False):
            result = obj._check_availability()
        assert result is False
        assert obj.available is False

    def test_returns_false_when_nectarstt_import_fails(self):
        obj = ns.NectarSTTIntegration(enabled=False)
        with patch("pathlib.Path.exists", return_value=True), \
             patch.dict("sys.modules", {"nectarstt": None}):
            result = obj._check_availability()
        assert result is False

    def test_returns_true_when_nectarstt_importable(self):
        obj = ns.NectarSTTIntegration(enabled=False)
        mock_nectarstt = MagicMock()
        with patch("pathlib.Path.exists", return_value=True), \
             patch.dict("sys.modules", {"nectarstt": mock_nectarstt}):
            result = obj._check_availability()
        assert result is True
        assert obj.available is True


# ─────────────────────────────────────────────
# is_available
# ─────────────────────────────────────────────

class TestIsAvailable:
    def test_false_when_disabled(self):
        obj = ns.NectarSTTIntegration(enabled=False)
        assert obj.is_available() is False

    def test_false_when_available_false(self):
        obj = ns.NectarSTTIntegration(enabled=False)
        obj.available = False
        assert obj.is_available() is False

    def test_true_when_enabled_and_available(self):
        obj = ns.NectarSTTIntegration(enabled=False)
        obj.enabled = True
        obj.available = True
        assert obj.is_available() is True


# ─────────────────────────────────────────────
# record_until_silence
# ─────────────────────────────────────────────

class TestRecordUntilSilence:
    def test_returns_none_when_unavailable(self):
        obj = ns.NectarSTTIntegration(enabled=False)
        result = obj.record_until_silence()
        assert result is None

    def test_returns_text_when_available(self):
        obj = ns.NectarSTTIntegration(enabled=False)
        obj.enabled = True
        obj.available = True

        mock_ns = MagicMock()
        mock_ns.record_until_silence.return_value = "こんにちは"
        with patch.dict("sys.modules", {"nectarstt": mock_ns}):
            result = obj.record_until_silence()

        assert result == "こんにちは"

    def test_returns_none_on_exception(self):
        obj = ns.NectarSTTIntegration(enabled=False)
        obj.enabled = True
        obj.available = True

        mock_ns = MagicMock()
        mock_ns.record_until_silence.side_effect = RuntimeError("mic error")
        with patch.dict("sys.modules", {"nectarstt": mock_ns}):
            result = obj.record_until_silence()

        assert result is None


# ─────────────────────────────────────────────
# transcribe_file
# ─────────────────────────────────────────────

class TestTranscribeFile:
    def test_returns_none_when_unavailable(self):
        obj = ns.NectarSTTIntegration(enabled=False)
        result = obj.transcribe_file("audio.wav")
        assert result is None


# ─────────────────────────────────────────────
# get_status
# ─────────────────────────────────────────────

class TestGetStatus:
    def test_contains_expected_keys(self):
        obj = ns.NectarSTTIntegration(enabled=False)
        status = obj.get_status()
        assert "enabled" in status
        assert "available" in status
        assert "path" in status
        assert "main_engine_exists" in status

    def test_enabled_false_in_status(self):
        obj = ns.NectarSTTIntegration(enabled=False)
        status = obj.get_status()
        assert status["enabled"] is False

    def test_available_false_in_status(self):
        obj = ns.NectarSTTIntegration(enabled=False)
        status = obj.get_status()
        assert status["available"] is False
