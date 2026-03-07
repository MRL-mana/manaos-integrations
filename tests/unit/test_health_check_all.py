"""Unit tests for tools/health_check_all.py."""

from __future__ import annotations

import http.client
import sys
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tools"))
from health_check_all import check_one, load_ledger_services


# ─────────────────────────────────────────────────────────────────────────────
# check_one  —  urllib.request.urlopen をモックして各パスを検証
# ─────────────────────────────────────────────────────────────────────────────

def _make_urlopen_ok(body: str = '{"status":"healthy"}', status: int = 200):
    """urlopen 正常系モック (context manager)。"""
    resp = MagicMock()
    resp.read.return_value = body.encode()
    resp.__enter__ = MagicMock(return_value=resp)
    resp.__exit__ = MagicMock(return_value=False)
    return resp


class TestCheckOne:
    def test_200_json_healthy(self):
        with patch("urllib.request.urlopen", return_value=_make_urlopen_ok()):
            result = check_one("svc", "http://localhost:8000/health", ["core"])
        assert result["healthy"] is True
        assert result["status"] == "healthy"
        assert result["name"] == "svc"
        assert result["error"] is None
        assert "latency_ms" in result

    def test_200_non_json_body_returns_ok(self):
        with patch("urllib.request.urlopen", return_value=_make_urlopen_ok("not-json")):
            result = check_one("svc", "http://localhost", [])
        assert result["healthy"] is True
        assert result["status"] == "ok"

    def test_4xx_treated_as_healthy(self):
        err = urllib.error.HTTPError(url="http://x", code=404, msg="Not Found",
                                     hdrs=None, fp=None)
        with patch("urllib.request.urlopen", side_effect=err):
            result = check_one("svc", "http://localhost", [])
        assert result["healthy"] is True
        assert "http_404" in result["status"]

    def test_5xx_treated_as_error(self):
        err = urllib.error.HTTPError(url="http://x", code=500, msg="Error",
                                     hdrs=None, fp=None)
        with patch("urllib.request.urlopen", side_effect=err):
            result = check_one("svc", "http://localhost", [])
        assert result["healthy"] is False
        assert result["status"] == "error"

    def test_remote_disconnected_returns_alive(self):
        with patch("urllib.request.urlopen",
                   side_effect=http.client.RemoteDisconnected("peer closed")):
            result = check_one("svc", "http://localhost", [])
        assert result["healthy"] is True
        assert result["status"] == "alive"

    def test_connection_error_returns_offline(self):
        with patch("urllib.request.urlopen",
                   side_effect=OSError("connection refused")):
            result = check_one("svc", "http://localhost", [])
        assert result["healthy"] is False
        assert result["status"] == "offline"
        assert result["error"] is not None

    def test_tags_preserved(self):
        with patch("urllib.request.urlopen", return_value=_make_urlopen_ok()):
            result = check_one("svc", "http://x", ["core", "docker"])
        assert result["tags"] == ["core", "docker"]


# ─────────────────────────────────────────────────────────────────────────────
# load_ledger_services  —  YAML ファイルから (name, url, tags) を生成
# ─────────────────────────────────────────────────────────────────────────────

class TestLoadLedgerServices:
    def _write_ledger(self, tmp_path, content: str) -> str:
        p = tmp_path / "services_ledger.yaml"
        p.write_text(content, encoding="utf-8")
        return str(p)

    def test_enabled_service_included(self, tmp_path):
        ledger = self._write_ledger(tmp_path, """
core:
  svc_a:
    enabled: true
    port: 8000
""")
        results = load_ledger_services(ledger)
        names = [r[0] for r in results]
        assert "svc_a" in names

    def test_disabled_service_excluded(self, tmp_path):
        ledger = self._write_ledger(tmp_path, """
core:
  svc_b:
    enabled: false
    port: 8001
""")
        results = load_ledger_services(ledger)
        assert all(r[0] != "svc_b" for r in results)

    def test_url_generated_from_port(self, tmp_path):
        ledger = self._write_ledger(tmp_path, """
core:
  svc_c:
    enabled: true
    port: 9000
""")
        results = load_ledger_services(ledger)
        assert len(results) == 1
        _, url, _ = results[0]
        assert "9000" in url
        assert url.endswith("/health")

    def test_explicit_url_preserved(self, tmp_path):
        ledger = self._write_ledger(tmp_path, """
core:
  svc_d:
    enabled: true
    url: http://127.0.0.1:7777/custom
""")
        results = load_ledger_services(ledger)
        _, url, _ = results[0]
        assert "custom" in url

    def test_optional_section_included(self, tmp_path):
        ledger = self._write_ledger(tmp_path, """
optional:
  svc_opt:
    enabled: true
    port: 6060
""")
        results = load_ledger_services(ledger)
        names = [r[0] for r in results]
        assert "svc_opt" in names

    def test_empty_ledger_returns_empty_list(self, tmp_path):
        ledger = self._write_ledger(tmp_path, "{}\n")
        results = load_ledger_services(ledger)
        assert results == []
