"""Tests for scripts/misc/inspect_workflows.py"""
import sys
import json
from unittest.mock import MagicMock, patch, mock_open
import pytest
from pathlib import Path

_MISC = Path(__file__).parent.parent.parent / "scripts" / "misc"

_FAKE_WF = json.dumps({
    "1": {"class_type": "KSampler", "inputs": {"steps": 20}},
    "2": {"class_type": "CLIPTextEncode", "inputs": {}},
})


def _prep(monkeypatch, workflow_data=None):
    sys.modules.pop("inspect_workflows", None)
    monkeypatch.syspath_prepend(str(_MISC))
    data = workflow_data or _FAKE_WF

    handle = MagicMock()
    handle.__enter__ = MagicMock(return_value=handle)
    handle.__exit__ = MagicMock(return_value=False)
    handle.read.return_value = data

    with patch("builtins.open", MagicMock(return_value=handle)), \
         patch("builtins.print"):
        import inspect_workflows  # noqa


class TestInspectWorkflows:
    def test_imports(self, monkeypatch):
        _prep(monkeypatch)
        assert "inspect_workflows" in sys.modules

    def test_opens_two_workflow_files(self, monkeypatch):
        sys.modules.pop("inspect_workflows", None)
        monkeypatch.syspath_prepend(str(_MISC))

        handle = MagicMock()
        handle.__enter__ = MagicMock(return_value=handle)
        handle.__exit__ = MagicMock(return_value=False)
        handle.read.return_value = _FAKE_WF

        mock_factory = MagicMock(return_value=handle)
        with patch("builtins.open", mock_factory), patch("builtins.print"):
            import inspect_workflows  # noqa
        assert mock_factory.call_count == 2

    def test_prints_each_workflow(self, monkeypatch):
        sys.modules.pop("inspect_workflows", None)
        monkeypatch.syspath_prepend(str(_MISC))

        handle = MagicMock()
        handle.__enter__ = MagicMock(return_value=handle)
        handle.__exit__ = MagicMock(return_value=False)
        handle.read.return_value = _FAKE_WF

        printed = []
        with patch("builtins.open", MagicMock(return_value=handle)), \
             patch("builtins.print", side_effect=lambda *a: printed.append(str(a))):
            import inspect_workflows  # noqa
        # Each workflow name should be printed
        assert any("FLUX1_real2.json" in p for p in printed)
        assert any("05_wQween" in p for p in printed)

    def test_json_data_loaded(self, monkeypatch):
        sys.modules.pop("inspect_workflows", None)
        monkeypatch.syspath_prepend(str(_MISC))

        handle = MagicMock()
        handle.__enter__ = MagicMock(return_value=handle)
        handle.__exit__ = MagicMock(return_value=False)
        handle.read.return_value = _FAKE_WF

        with patch("builtins.open", MagicMock(return_value=handle)), \
             patch("json.load", return_value=json.loads(_FAKE_WF)) as mock_jl, \
             patch("builtins.print"):
            import inspect_workflows  # noqa
        assert mock_jl.call_count == 2
