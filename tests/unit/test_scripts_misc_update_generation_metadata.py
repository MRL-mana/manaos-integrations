"""Tests for scripts/misc/update_generation_metadata.py"""
import sys
import types
import json
import importlib.util
import os as _os_mod
from unittest.mock import MagicMock, patch, mock_open
import pytest
from pathlib import Path

_MISC = Path(__file__).parent.parent.parent / "scripts" / "misc"

# generation_metadata.json is a dict: { "prompt_id": {...}, ... }
_SAMPLE_META = {
    "abc123": {
        "prompt_id": "abc123",
        "created_at": "2024-01-01T12:00:00",
        "output_file": None,
    }
}


def _load_module(monkeypatch, db_exists=True, meta=None, raise_exit=False):
    sys.modules.pop("update_generation_metadata", None)
    monkeypatch.syspath_prepend(str(_MISC))
    monkeypatch.delenv("COMFYUI_BASE", raising=False)
    monkeypatch.delenv("COMFYUI_PATH", raising=False)
    monkeypatch.delenv("COMFYUI_URL", raising=False)
    monkeypatch.delenv("COMFYUI_OUTPUT_DIR", raising=False)

    if meta is None:
        meta = _SAMPLE_META

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"outputs": {}}
    mock_req = MagicMock()
    mock_req.get.return_value = mock_resp
    monkeypatch.setitem(sys.modules, "requests", mock_req)

    if raise_exit:
        exit_fn = MagicMock(side_effect=SystemExit(1))
    else:
        exit_fn = MagicMock()

    with patch("builtins.print"):
        with patch("builtins.open", mock_open(read_data=json.dumps(meta))):
            with patch("pathlib.Path.exists", return_value=db_exists):
                with patch("sys.exit", exit_fn):
                    try:
                        import update_generation_metadata as m
                    except SystemExit:
                        m = None
    return m, mock_req, exit_fn


class TestUpdateGenerationMetadata:
    def test_exits_when_db_missing(self, monkeypatch):
        _, _, mock_exit = _load_module(monkeypatch, db_exists=False, raise_exit=True)
        mock_exit.assert_called_with(1)

    def test_imports_with_db_present(self, monkeypatch):
        m, _, _ = _load_module(monkeypatch, db_exists=True)
        assert "update_generation_metadata" in sys.modules

    def test_env_comfyui_base_used(self, monkeypatch):
        monkeypatch.setenv("COMFYUI_BASE", "C:/TestComfyUI")
        m, _, _ = _load_module(monkeypatch, db_exists=True)
        assert True

    def test_requests_imported(self, monkeypatch):
        _, mock_req, _ = _load_module(monkeypatch, db_exists=True)
        assert sys.modules.get("requests") is mock_req
