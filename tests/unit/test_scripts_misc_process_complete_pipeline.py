"""tests/unit/test_scripts_misc_process_complete_pipeline.py

process_complete_pipeline.py の単体テスト
"""
import pytest

import scripts.misc.process_complete_pipeline as _mod


class TestWaitForFile:
    def test_returns_true_when_file_ready(self, tmp_path, monkeypatch):
        f = tmp_path / "output.xlsx"
        f.write_bytes(b"data content")
        monkeypatch.setattr(_mod.time, "sleep", lambda s: None)
        result = _mod.wait_for_file(str(f), timeout=10, check_interval=1)
        assert result is True

    def test_returns_false_on_timeout_no_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(_mod.time, "sleep", lambda s: None)
        result = _mod.wait_for_file(str(tmp_path / "missing.xlsx"), timeout=0, check_interval=1)
        assert result is False

    def test_returns_false_for_empty_file_on_timeout(self, tmp_path, monkeypatch):
        f = tmp_path / "empty.xlsx"
        f.write_bytes(b"")
        monkeypatch.setattr(_mod.time, "sleep", lambda s: None)
        result = _mod.wait_for_file(str(f), timeout=0, check_interval=1)
        assert result is False

    def test_accepts_string_path(self, tmp_path, monkeypatch):
        f = tmp_path / "result.png"
        f.write_bytes(b"\x89PNG")
        monkeypatch.setattr(_mod.time, "sleep", lambda s: None)
        result = _mod.wait_for_file(str(f), timeout=5, check_interval=1)
        assert isinstance(result, bool)
        assert result is True

    def test_default_timeout_signature(self):
        import inspect
        sig = inspect.signature(_mod.wait_for_file)
        params = sig.parameters
        assert params["timeout"].default == 3600
        assert params["check_interval"].default == 10
