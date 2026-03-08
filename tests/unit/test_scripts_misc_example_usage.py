"""tests/unit/test_scripts_misc_example_usage.py

example_usage.py の単体テスト
"""
from unittest.mock import MagicMock
import pytest

import scripts.misc.example_usage as _mod


class TestAnalyzeDifficulty:
    def test_returns_json_response(self, monkeypatch):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "difficulty_score": 0.3,
            "difficulty_level": "LIGHTWEIGHT",
            "recommended_model": "llama3.2:3b",
        }
        monkeypatch.setattr(_mod.requests, "post", lambda *a, **kw: mock_resp)

        result = _mod.analyze_difficulty("タイポを直して", "def hello():\n    print('helo')")
        assert result["difficulty_level"] == "LIGHTWEIGHT"

    def test_without_code_context(self, monkeypatch):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"difficulty_score": 0.5}
        monkeypatch.setattr(_mod.requests, "post", lambda *a, **kw: mock_resp)

        result = _mod.analyze_difficulty("何か教えて")
        assert "difficulty_score" in result

    def test_returns_dict(self, monkeypatch):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {}
        monkeypatch.setattr(_mod.requests, "post", lambda *a, **kw: mock_resp)

        result = _mod.analyze_difficulty("test")
        assert isinstance(result, dict)


class TestRouteLlm:
    def test_returns_routing_result(self, monkeypatch):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "model": "llama3.2:3b",
            "difficulty_score": 0.2,
        }
        monkeypatch.setattr(_mod.requests, "post", lambda *a, **kw: mock_resp)

        result = _mod.route_llm("簡単なタスク")
        assert result["model"] == "llama3.2:3b"

    def test_prefer_quality_flag_passed(self, monkeypatch):
        captured = {}
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"model": "qwen2.5:14b"}

        def capture(url, json=None, **kw):
            captured["data"] = json
            return mock_resp

        monkeypatch.setattr(_mod.requests, "post", capture)

        _mod.route_llm("複雑なタスク", prefer_quality=True)
        assert captured["data"]["preferences"]["prefer_quality"] is True

    def test_with_code_context(self, monkeypatch):
        captured = {}
        mock_resp = MagicMock()
        mock_resp.json.return_value = {}

        def capture(url, json=None, **kw):
            captured["data"] = json
            return mock_resp

        monkeypatch.setattr(_mod.requests, "post", capture)

        _mod.route_llm("test", code_context="def foo(): pass")
        assert captured["data"]["context"].get("code_context") == "def foo(): pass"


class TestGetAvailableModels:
    def test_returns_model_list(self, monkeypatch):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"models": ["llama3.2:3b", "qwen2.5:7b"]}
        monkeypatch.setattr(_mod.requests, "get", lambda *a, **kw: mock_resp)

        result = _mod.get_available_models()
        assert "models" in result
        assert "llama3.2:3b" in result["models"]

    def test_returns_dict(self, monkeypatch):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {}
        monkeypatch.setattr(_mod.requests, "get", lambda *a, **kw: mock_resp)

        result = _mod.get_available_models()
        assert isinstance(result, dict)
