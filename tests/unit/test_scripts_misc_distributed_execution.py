"""
Unit tests for scripts/misc/distributed_execution.py
"""
import json
import sys
from unittest.mock import MagicMock, patch

# ── module-level mocks ─────────────────────────────────────────────────────
_ml = MagicMock()
_ml.get_service_logger.return_value = MagicMock()
_ml.get_logger.return_value = MagicMock()
sys.modules.setdefault("manaos_logger", _ml)

_paths_mod = sys.modules.get("_paths") or MagicMock()
_paths_mod.UNIFIED_API_PORT = 9999
sys.modules["_paths"] = _paths_mod

import pytest
from scripts.misc.distributed_execution import DistributedExecution, NodeStatus


# ── fixtures ────────────────────────────────────────────────────────────────
@pytest.fixture
def de(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    obj = DistributedExecution()
    return obj


# ── TestNodeStatus ─────────────────────────────────────────────────────────
class TestNodeStatus:
    def test_values(self):
        assert NodeStatus.ONLINE.value == "online"
        assert NodeStatus.OFFLINE.value == "offline"
        assert NodeStatus.BUSY.value == "busy"
        assert NodeStatus.IDLE.value == "idle"


# ── TestInit ───────────────────────────────────────────────────────────────
class TestInit:
    def test_nodes_empty_initially(self, de):
        assert de.nodes == {}

    def test_tasks_empty_initially(self, de):
        assert de.tasks == []


# ── TestRegisterNode ───────────────────────────────────────────────────────
class TestRegisterNode:
    def test_node_registered(self, de):
        de.register_node("n1", "http://localhost:9000", ["img_gen"])
        assert "n1" in de.nodes

    def test_node_fields(self, de):
        de.register_node("n2", "http://localhost:9001", ["text_gen"], {"max_concurrent_tasks": 2})
        node = de.nodes["n2"]
        assert node["url"] == "http://localhost:9001"
        assert "text_gen" in node["capabilities"]
        assert node["status"] == NodeStatus.OFFLINE.value

    def test_metadata_default_empty(self, de):
        de.register_node("n3", "http://localhost:9002", [])
        assert de.nodes["n3"]["metadata"] == {}


# ── TestCheckNodeStatus ────────────────────────────────────────────────────
class TestCheckNodeStatus:
    def test_unknown_node_returns_false(self, de):
        assert de.check_node_status("nonexistent") is False

    def test_online_200_returns_true(self, de):
        de.register_node("n4", "http://localhost:9003", ["cap1"])
        mock_resp = MagicMock(status_code=200)
        with patch("requests.get", return_value=mock_resp):
            assert de.check_node_status("n4") is True

    def test_offline_500_returns_false(self, de):
        de.register_node("n5", "http://localhost:9004", ["cap2"])
        mock_resp = MagicMock(status_code=500)
        with patch("requests.get", return_value=mock_resp):
            assert de.check_node_status("n5") is False

    def test_connection_error_returns_false(self, de):
        de.register_node("n6", "http://localhost:9005", ["cap3"])
        with patch("requests.get", side_effect=Exception("connection error")):
            assert de.check_node_status("n6") is False


# ── TestGetTaskStatus ──────────────────────────────────────────────────────
class TestGetTaskStatus:
    def test_nonexistent_task_returns_none(self, de):
        assert de.get_task_status("no_such_task") is None

    def test_returns_task_dict(self, de):
        de.register_node("nA", "http://localhost:9006", ["type_x"])
        # inject a task directly
        de.tasks.append({
            "id": "task_direct_1",
            "type": "type_x",
            "data": {},
            "node_id": "nA",
            "status": "pending",
        })
        with patch("requests.get", side_effect=Exception("no server")):
            result = de.get_task_status("task_direct_1")
        assert result is not None
        assert result["id"] == "task_direct_1"


# ── TestGetStatus ──────────────────────────────────────────────────────────
class TestGetStatus:
    def test_empty_status(self, de):
        # no nodes → all counts zero
        s = de.get_status()
        assert s["total_nodes"] == 0
        assert s["online_nodes"] == 0
        assert s["total_tasks"] == 0

    def test_counts_pending_tasks(self, de):
        de.tasks = [
            {"status": "pending"},
            {"status": "running"},
            {"status": "completed"},
        ]
        s = de.get_status()
        assert s["total_tasks"] == 3
        assert s["pending_tasks"] == 1
        assert s["running_tasks"] == 1
        assert s["completed_tasks"] == 1
