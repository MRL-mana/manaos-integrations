"""Tests for scripts/misc/complete_integration_test.py"""
import importlib
import sys
from unittest.mock import MagicMock

import pytest


@pytest.fixture(scope="module")
def _mod():
    sys.path.insert(0, "scripts/misc")
    if "complete_integration_test" in sys.modules:
        return sys.modules["complete_integration_test"]
    return importlib.import_module("complete_integration_test")


class TestTestAllIntegrations:
    def test_returns_false_when_server_unavailable(self, _mod, monkeypatch):
        """サーバーが起動していないとき False を返す"""
        import requests

        def _raise(*args, **kwargs):
            raise requests.exceptions.ConnectionError("refused")

        monkeypatch.setattr(requests, "get", _raise)
        result = _mod.test_all_integrations()
        assert result is False

    def test_returns_false_when_health_check_not_200(self, _mod, monkeypatch):
        """ヘルスチェックが 200 以外のとき False を返す"""
        import requests

        mock_resp = MagicMock()
        mock_resp.status_code = 503
        monkeypatch.setattr(requests, "get", lambda *a, **kw: mock_resp)
        result = _mod.test_all_integrations()
        assert result is False
