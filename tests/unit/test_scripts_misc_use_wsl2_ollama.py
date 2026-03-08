"""tests/unit/test_scripts_misc_use_wsl2_ollama.py

use_wsl2_ollama.py の単体テスト
"""
import json
from unittest.mock import MagicMock
import pytest

import scripts.misc.use_wsl2_ollama as _mod


class TestCallWsl2OllamaApi:
    def test_get_returns_parsed_json(self, monkeypatch):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({"models": ["llama3", "mistral"]})
        monkeypatch.setattr(_mod.subprocess, "run", lambda *a, **kw: mock_result)

        result = _mod.call_wsl2_ollama_api("/api/tags")
        assert isinstance(result, dict)
        assert "models" in result

    def test_returns_none_on_nonzero_returncode(self, monkeypatch):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        monkeypatch.setattr(_mod.subprocess, "run", lambda *a, **kw: mock_result)

        result = _mod.call_wsl2_ollama_api("/api/tags")
        assert result is None

    def test_returns_raw_string_if_not_json(self, monkeypatch):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "plain text response"
        monkeypatch.setattr(_mod.subprocess, "run", lambda *a, **kw: mock_result)

        result = _mod.call_wsl2_ollama_api("/api/tags")
        assert result == "plain text response"

    def test_post_method_passes_json_data(self, monkeypatch):
        captured = {}
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"ok": true}'

        def capture_run(cmd, **kw):
            captured["cmd"] = cmd
            return mock_result

        monkeypatch.setattr(_mod.subprocess, "run", capture_run)
        result = _mod.call_wsl2_ollama_api("/api/generate", method="POST", json_data={"model": "llama3"})
        # POST コマンドが組み立てられていることを確認
        cmd_str = " ".join(str(c) for c in captured["cmd"])
        assert "POST" in cmd_str
