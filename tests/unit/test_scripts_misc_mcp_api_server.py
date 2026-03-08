"""Tests for scripts/misc/mcp_api_server.py"""
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

# ── top-level dependency mocks ────────────────────────────────────────
_ml = MagicMock()
_ml.get_logger.return_value = MagicMock()
_ml.get_service_logger.return_value = MagicMock()
sys.modules.setdefault("manaos_logger", _ml)

_paths_mod = MagicMock()
_paths_mod.COMFYUI_PORT = 8188
_paths_mod.UNIFIED_API_PORT = 8000
sys.modules["_paths"] = _paths_mod

# manaos_unified_mcp_server is optional (try/except in module)
# leave it absent so MCP_SERVER_AVAILABLE stays False

# ── import SUT ────────────────────────────────────────────────────────
_root = str(Path(__file__).parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

import scripts.misc.mcp_api_server as _sut
from scripts.misc.mcp_api_server import app

app.config["TESTING"] = True


@pytest.fixture
def client():
    with app.test_client() as c:
        yield c


@pytest.fixture(autouse=True)
def _clean_state():
    """Clear global job/plan dicts between tests."""
    _sut._OPS_PLANS.clear()
    _sut._OPS_JOBS.clear()
    yield
    _sut._OPS_PLANS.clear()
    _sut._OPS_JOBS.clear()


# ══════════════════════════════════════════════════════════════════════
class TestPureFunctions:
    def test_utc_now_iso_returns_string(self):
        result = _sut._utc_now_iso()
        assert isinstance(result, str)
        assert "T" in result  # ISO format

    def test_is_dangerous_command_blocks_rm_rf(self):
        assert _sut._is_dangerous_command("rm -rf /") is True

    def test_is_dangerous_command_blocks_shutdown(self):
        assert _sut._is_dangerous_command("shutdown /r /f") is True

    def test_is_dangerous_command_allows_safe(self):
        assert _sut._is_dangerous_command("echo hello") is False
        assert _sut._is_dangerous_command("dir C:\\") is False

    def test_create_job_returns_queued_job(self):
        job = _sut._create_job("test_type", {"key": "val"})
        assert job["status"] == "queued"
        assert job["type"] == "test_type"
        assert "job_id" in job
        assert job["payload"] == {"key": "val"}

    def test_create_job_stored_in_jobs_dict(self):
        job = _sut._create_job("x")
        assert job["job_id"] in _sut._OPS_JOBS

    def test_update_job_changes_status(self):
        job = _sut._create_job("upd_test")
        _sut._update_job(job["job_id"], status="completed", result={"ok": True})
        assert _sut._OPS_JOBS[job["job_id"]]["status"] == "completed"

    def test_update_job_noop_for_unknown_id(self):
        _sut._update_job("nonexistent-id", status="fail")  # should not raise

    def test_score_memory_entry_exact_match(self):
        entry = {"content": "hello world", "metadata": {}}
        score = _sut._score_memory_entry("hello", entry)
        assert score == 1.0

    def test_score_memory_entry_no_match(self):
        entry = {"content": "goodbye", "metadata": {}}
        score = _sut._score_memory_entry("hello", entry)
        assert score == 0.0

    def test_score_memory_entry_empty_query_returns_one(self):
        entry = {"content": "anything", "metadata": {}}
        score = _sut._score_memory_entry("", entry)
        assert score == 1.0


# ══════════════════════════════════════════════════════════════════════
class TestHealthEndpoint:
    def test_returns_200(self, client):
        r = client.get("/health")
        assert r.status_code == 200

    def test_returns_healthy_status(self, client):
        data = r = client.get("/health")
        body = json.loads(r.data)
        assert body["status"] == "healthy"

    def test_includes_mcp_available_flag(self, client):
        body = json.loads(client.get("/health").data)
        assert "mcp_available" in body


# ══════════════════════════════════════════════════════════════════════
class TestReadyEndpoint:
    def test_503_when_mcp_unavailable(self, client):
        with patch.object(_sut, "MCP_SERVER_AVAILABLE", new=False):
            r = client.get("/ready")
        body = json.loads(r.data)
        assert body["status"] == "starting"
        assert r.status_code == 503

    def test_200_when_mcp_available(self, client):
        orig = _sut.MCP_SERVER_AVAILABLE
        try:
            _sut.MCP_SERVER_AVAILABLE = True
            r = client.get("/ready")
            assert r.status_code == 200
            assert json.loads(r.data)["status"] == "ready"
        finally:
            _sut.MCP_SERVER_AVAILABLE = orig


# ══════════════════════════════════════════════════════════════════════
class TestMemoryWrite:
    def test_success(self, client, tmp_path):
        with patch.object(_sut, "_memory_log_path", return_value=tmp_path / "mem.jsonl"), \
             patch.object(_sut, "_append_memory_entry") as mock_append:
            r = client.post("/memory/write", json={"content": "test memory"})
        assert r.status_code == 200
        body = json.loads(r.data)
        assert body["success"] is True
        assert body["entry"]["content"] == "test memory"

    def test_400_when_content_missing(self, client):
        r = client.post("/memory/write", json={})
        assert r.status_code == 400

    def test_400_when_metadata_not_dict(self, client):
        r = client.post("/api/memory/write", json={"content": "x", "metadata": "bad"})
        assert r.status_code == 400

    def test_api_prefix_route_works(self, client):
        with patch.object(_sut, "_append_memory_entry"):
            r = client.post("/api/memory/write", json={"content": "ok"})
        assert r.status_code == 200


# ══════════════════════════════════════════════════════════════════════
class TestMemorySearch:
    def _seed_entries(self, entries):
        with patch.object(_sut, "_load_memory_entries", return_value=entries):
            return entries

    def test_returns_matching_entries(self, client):
        entries = [
            {"content": "hello world", "metadata": {}, "timestamp": "2025-01-01T00:00:00"},
            {"content": "goodbye", "metadata": {}, "timestamp": "2025-01-01T00:00:01"},
        ]
        with patch.object(_sut, "_load_memory_entries", return_value=entries):
            r = client.post("/memory/search", json={"query": "hello"})
        body = json.loads(r.data)
        assert body["success"] is True
        assert body["count"] == 1
        assert body["results"][0]["content"] == "hello world"

    def test_empty_query_returns_all(self, client):
        entries = [
            {"content": "a", "metadata": {}, "timestamp": "2025-01-01"},
            {"content": "b", "metadata": {}, "timestamp": "2025-01-02"},
        ]
        with patch.object(_sut, "_load_memory_entries", return_value=entries):
            r = client.post("/api/memory/search", json={"query": ""})
        body = json.loads(r.data)
        assert body["success"] is True

    def test_limit_applied(self, client):
        entries = [{"content": "item", "metadata": {}, "timestamp": "2025-01-01"}] * 20
        with patch.object(_sut, "_load_memory_entries", return_value=entries):
            r = client.post("/memory/search", json={"query": "", "limit": 5})
        body = json.loads(r.data)
        assert len(body["results"]) <= 5


# ══════════════════════════════════════════════════════════════════════
class TestOpsPlan:
    def test_creates_plan(self, client):
        r = client.post("/ops/plan", json={"goal": "Deploy service"})
        assert r.status_code == 200
        body = json.loads(r.data)
        assert body["success"] is True
        assert "plan_id" in body["plan"]

    def test_400_when_goal_missing(self, client):
        r = client.post("/ops/plan", json={})
        assert r.status_code == 400

    def test_custom_steps_accepted(self, client):
        r = client.post("/ops/plan", json={"goal": "Test", "steps": ["step1", "step2"]})
        body = json.loads(r.data)
        assert body["plan"]["steps"] == ["step1", "step2"]

    def test_default_steps_generated(self, client):
        r = client.post("/ops/plan", json={"goal": "DoSomething"})
        body = json.loads(r.data)
        assert len(body["plan"]["steps"]) > 0

    def test_plan_stored_in_state(self, client):
        r = client.post("/ops/plan", json={"goal": "Store me"})
        plan_id = json.loads(r.data)["plan"]["plan_id"]
        assert plan_id in _sut._OPS_PLANS


# ══════════════════════════════════════════════════════════════════════
class TestOpsExec:
    def test_401_without_token_when_token_required(self, client):
        with patch.dict(os.environ, {"OPS_EXEC_BEARER_TOKEN": "secret"}):
            r = client.post("/ops/exec", json={"command": "echo hi", "approved": True})
        assert r.status_code == 401

    def test_403_wrong_token(self, client):
        with patch.dict(os.environ, {"OPS_EXEC_BEARER_TOKEN": "secret"}):
            r = client.post(
                "/ops/exec",
                json={"command": "echo hi", "approved": True},
                headers={"Authorization": "Bearer wrong"},
            )
        assert r.status_code == 403

    def test_dry_run_does_not_execute(self, client):
        with patch.dict(os.environ, {"OPS_EXEC_BEARER_TOKEN": "", "OPS_APPROVAL_MODE": "none"}):
            r = client.post("/ops/exec", json={"command": "echo hi", "dry_run": True, "approved": True})
        body = json.loads(r.data)
        assert body["success"] is True
        assert "dry-run" in body["stdout"]

    def test_dangerous_command_blocked(self, client):
        with patch.dict(os.environ, {"OPS_EXEC_BEARER_TOKEN": "", "OPS_APPROVAL_MODE": "none"}):
            r = client.post("/ops/exec", json={"command": "rm -rf /", "approved": True})
        assert r.status_code == 400

    def test_400_when_no_command(self, client):
        with patch.dict(os.environ, {"OPS_EXEC_BEARER_TOKEN": "", "OPS_APPROVAL_MODE": "none"}):
            r = client.post("/ops/exec", json={"approved": True})
        assert r.status_code == 400

    def test_approval_required_blocks_unapproved(self, client):
        with patch.dict(os.environ, {"OPS_EXEC_BEARER_TOKEN": "", "OPS_APPROVAL_MODE": "required"}):
            r = client.post("/ops/exec", json={"command": "echo hi", "approved": False})
        assert r.status_code == 403

    def test_real_exec_runs_subprocess(self, client):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "hello"
        mock_result.stderr = ""
        with patch.dict(os.environ, {"OPS_EXEC_BEARER_TOKEN": "", "OPS_APPROVAL_MODE": "none"}), \
             patch("scripts.misc.mcp_api_server.subprocess.run", return_value=mock_result):
            r = client.post("/ops/exec", json={"command": "echo hello", "dry_run": False, "approved": True})
        body = json.loads(r.data)
        assert body["success"] is True


# ══════════════════════════════════════════════════════════════════════
class TestOpsJob:
    def test_404_for_unknown_job(self, client):
        r = client.get("/ops/job/nonexistent-id")
        assert r.status_code == 404

    def test_returns_job_by_id(self, client):
        job = _sut._create_job("test_job")
        r = client.get(f"/ops/job/{job['job_id']}")
        assert r.status_code == 200
        body = json.loads(r.data)
        assert body["success"] is True
        assert body["job"]["job_id"] == job["job_id"]

    def test_api_prefix_route(self, client):
        job = _sut._create_job("api_test")
        r = client.get(f"/api/ops/job/{job['job_id']}")
        assert r.status_code == 200


# ══════════════════════════════════════════════════════════════════════
class TestOpsNotify:
    def test_returns_success(self, client):
        r = client.post("/ops/notify", json={"message": "hello"})
        assert r.status_code == 200
        body = json.loads(r.data)
        assert body["success"] is True

    def test_400_when_message_missing(self, client):
        r = client.post("/ops/notify", json={"channel": "slack"})
        assert r.status_code == 400

    def test_channel_and_level_in_response(self, client):
        r = client.post("/ops/notify", json={"message": "hi", "channel": "ops", "level": "warning"})
        body = json.loads(r.data)
        assert body["notification"]["channel"] == "ops"
        assert body["notification"]["level"] == "warning"


# ══════════════════════════════════════════════════════════════════════
class TestDevEndpoints:
    def test_dev_patch_queues_job(self, client):
        r = client.post("/dev/patch", json={"file": "x.py"})
        assert r.status_code == 200
        body = json.loads(r.data)
        assert body["success"] is True
        assert body["action"] == "patch"

    def test_dev_test_queues_job(self, client):
        r = client.post("/api/dev/test", json={"suite": "unit"})
        assert r.status_code == 200
        body = json.loads(r.data)
        assert body["action"] == "test"

    def test_dev_deploy_requires_auth(self, client):
        with patch.dict(os.environ, {"OPS_EXEC_BEARER_TOKEN": "tok"}):
            r = client.post("/dev/deploy", json={})
        assert r.status_code == 401

    def test_dev_deploy_succeeds_with_token(self, client):
        with patch.dict(os.environ, {"OPS_EXEC_BEARER_TOKEN": "tok"}):
            r = client.post(
                "/api/dev/deploy", json={},
                headers={"Authorization": "Bearer tok"}
            )
        assert r.status_code == 200
        body = json.loads(r.data)
        assert body["action"] == "deploy"


# ══════════════════════════════════════════════════════════════════════
class TestListMcpTools:
    def test_503_when_mcp_unavailable(self, client):
        with patch.object(_sut, "MCP_SERVER_AVAILABLE", new=False), \
             patch.object(_sut, "server", new=None):
            r = client.get("/api/mcp/tools")
        assert r.status_code == 503

    def test_200_when_mcp_available(self, client):
        orig = _sut.MCP_SERVER_AVAILABLE
        orig_server = _sut.server
        try:
            _sut.MCP_SERVER_AVAILABLE = True
            _sut.server = MagicMock()
            r = client.get("/api/mcp/tools")
            assert r.status_code == 200
            body = json.loads(r.data)
            assert "tools" in body
        finally:
            _sut.MCP_SERVER_AVAILABLE = orig
            _sut.server = orig_server


# ══════════════════════════════════════════════════════════════════════
class TestOpenApiSpec:
    def test_returns_openapi_json(self, client):
        r = client.get("/openapi.json")
        assert r.status_code == 200
        body = json.loads(r.data)
        assert "paths" in body

    def test_contains_memory_write_path(self, client):
        r = client.get("/openapi.json")
        body = json.loads(r.data)
        assert "/memory/write" in body["paths"]


# ══════════════════════════════════════════════════════════════════════
class TestRequireOpsToken:
    def test_returns_none_when_no_token_configured(self):
        with patch.dict(os.environ, {"OPS_EXEC_BEARER_TOKEN": ""}):
            with app.test_request_context("/"):
                result = _sut._require_ops_token()
        assert result is None

    def test_returns_401_when_missing_header(self):
        with patch.dict(os.environ, {"OPS_EXEC_BEARER_TOKEN": "mysecret"}):
            with app.test_request_context("/"):
                result = _sut._require_ops_token()
        assert result is not None
        resp, code = result
        assert code == 401
