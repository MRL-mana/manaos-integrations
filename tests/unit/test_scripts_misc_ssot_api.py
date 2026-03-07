"""
Unit tests for scripts/misc/ssot_api.py
"""
import sys
import json
import types
from unittest.mock import MagicMock

import pytest

# ── モジュールモック（インポート前に設定）─────────────────────────────────────
sys.modules.setdefault("manaos_logger", MagicMock(
    get_logger=MagicMock(return_value=MagicMock()),
    get_service_logger=MagicMock(return_value=MagicMock()),
))
sys.modules.setdefault("manaos_error_handler", MagicMock(
    ManaOSErrorHandler=MagicMock(return_value=MagicMock(
        handle_exception=MagicMock(return_value=MagicMock(
            message="err",
            user_message="user err",
            to_json_response=MagicMock(return_value={"error": "err"}),
        ))
    )),
    ErrorCategory=MagicMock(),
    ErrorSeverity=MagicMock(),
))

# flask & flask_cors must be real or importable
import scripts.misc.ssot_api as api

# Flask test client
@pytest.fixture
def client():
    api.app.config["TESTING"] = True
    with api.app.test_client() as c:
        yield c


# ─────────────────────────────────────────────
# /health
# ─────────────────────────────────────────────

class TestHealth:
    def test_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_returns_healthy_status(self, client):
        data = resp = client.get("/health").get_json()
        assert data["status"] == "healthy"


# ─────────────────────────────────────────────
# /api/ssot  (SSOT file not found)
# ─────────────────────────────────────────────

class TestGetSsot:
    def test_returns_404_when_file_missing(self, tmp_path, client):
        import scripts.misc.ssot_api as api
        original = api.SSOT_FILE
        api.SSOT_FILE = tmp_path / "nonexistent.json"
        try:
            resp = client.get("/api/ssot")
            assert resp.status_code == 404
        finally:
            api.SSOT_FILE = original

    def test_returns_ssot_content_when_file_exists(self, tmp_path, client):
        import scripts.misc.ssot_api as api
        content = {"timestamp": "2026-01-01", "services": []}
        ssot_file = tmp_path / "ssot.json"
        ssot_file.write_text(json.dumps(content), encoding="utf-8")

        original = api.SSOT_FILE
        api.SSOT_FILE = ssot_file
        try:
            resp = client.get("/api/ssot")
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["timestamp"] == "2026-01-01"
        finally:
            api.SSOT_FILE = original


# ─────────────────────────────────────────────
# /api/ssot/summary
# ─────────────────────────────────────────────

class TestGetSsotSummary:
    def test_returns_404_when_file_missing(self, tmp_path, client):
        import scripts.misc.ssot_api as api
        original = api.SSOT_FILE
        api.SSOT_FILE = tmp_path / "nonexistent.json"
        try:
            resp = client.get("/api/ssot/summary")
            assert resp.status_code == 404
        finally:
            api.SSOT_FILE = original

    def test_returns_summary_fields(self, tmp_path, client):
        import scripts.misc.ssot_api as api
        content = {
            "timestamp": "2026-01-01",
            "summary": {"total": 3},
            "system": {"cpu": {"percent": 10}, "ram": {"percent": 50}, "disk": {"percent": 30}},
            "active_tasks": ["t1"],
            "last_error": None,
        }
        ssot_file = tmp_path / "ssot.json"
        ssot_file.write_text(json.dumps(content), encoding="utf-8")

        original = api.SSOT_FILE
        api.SSOT_FILE = ssot_file
        try:
            resp = client.get("/api/ssot/summary")
            assert resp.status_code == 200
            data = resp.get_json()
            assert "timestamp" in data
            assert "summary" in data
            assert "system" in data
        finally:
            api.SSOT_FILE = original


# ─────────────────────────────────────────────
# /api/ssot/services
# ─────────────────────────────────────────────

class TestGetServicesStatus:
    def test_returns_services_list(self, tmp_path, client):
        import scripts.misc.ssot_api as api
        content = {"services": [{"name": "svc1"}], "summary": {"total": 1}}
        ssot_file = tmp_path / "ssot.json"
        ssot_file.write_text(json.dumps(content), encoding="utf-8")

        original = api.SSOT_FILE
        api.SSOT_FILE = ssot_file
        try:
            resp = client.get("/api/ssot/services")
            assert resp.status_code == 200
            data = resp.get_json()
            assert "services" in data
        finally:
            api.SSOT_FILE = original


# ─────────────────────────────────────────────
# /api/ssot/recent
# ─────────────────────────────────────────────

class TestGetRecentInputs:
    def test_returns_recent_inputs(self, tmp_path, client):
        import scripts.misc.ssot_api as api
        content = {"recent_inputs": ["cmd1", "cmd2"]}
        ssot_file = tmp_path / "ssot.json"
        ssot_file.write_text(json.dumps(content), encoding="utf-8")

        original = api.SSOT_FILE
        api.SSOT_FILE = ssot_file
        try:
            resp = client.get("/api/ssot/recent")
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["recent_inputs"] == ["cmd1", "cmd2"]
        finally:
            api.SSOT_FILE = original


# ─────────────────────────────────────────────
# /api/ssot/error
# ─────────────────────────────────────────────

class TestGetLastError:
    def test_returns_last_error(self, tmp_path, client):
        import scripts.misc.ssot_api as api
        content = {"last_error": "OutOfMemory"}
        ssot_file = tmp_path / "ssot.json"
        ssot_file.write_text(json.dumps(content), encoding="utf-8")

        original = api.SSOT_FILE
        api.SSOT_FILE = ssot_file
        try:
            resp = client.get("/api/ssot/error")
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["last_error"] == "OutOfMemory"
        finally:
            api.SSOT_FILE = original

    def test_returns_none_when_no_error(self, tmp_path, client):
        import scripts.misc.ssot_api as api
        content = {}
        ssot_file = tmp_path / "ssot.json"
        ssot_file.write_text(json.dumps(content), encoding="utf-8")

        original = api.SSOT_FILE
        api.SSOT_FILE = ssot_file
        try:
            resp = client.get("/api/ssot/error")
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["last_error"] is None
        finally:
            api.SSOT_FILE = original
