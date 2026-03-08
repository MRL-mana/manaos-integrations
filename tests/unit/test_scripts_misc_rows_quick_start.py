"""Tests for scripts/misc/rows_quick_start.py"""
import importlib
import sys

import pytest


@pytest.fixture(scope="module")
def _mod():
    sys.path.insert(0, "scripts/misc")
    if "rows_quick_start" in sys.modules:
        return sys.modules["rows_quick_start"]
    return importlib.import_module("rows_quick_start")


class TestQuickTest:
    def test_returns_none_when_server_unavailable(self, _mod, monkeypatch):
        """APIサーバーが起動していないとき early return (None)"""
        import requests

        def _raise(*args, **kwargs):
            raise requests.exceptions.ConnectionError("refused")

        monkeypatch.setattr(requests, "get", _raise)
        result = _mod.quick_test()
        # 接続失敗時は return だけ (None) で終了する
        assert result is None

    def test_returns_none_when_health_not_200(self, _mod, monkeypatch):
        """ヘルスチェックが 200 以外のとき early return"""
        from unittest.mock import MagicMock
        import requests

        mock_resp = MagicMock()
        mock_resp.status_code = 503
        monkeypatch.setattr(requests, "get", lambda *a, **kw: mock_resp)
        result = _mod.quick_test()
        assert result is None
