"""
Unit tests for scripts/misc/automated_deployment_pipeline.py
"""
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

# ── module-level mocks ─────────────────────────────────────────────────────
_ml = MagicMock()
_ml.get_service_logger.return_value = MagicMock()
_ml.get_logger.return_value = MagicMock()
sys.modules.setdefault("manaos_logger", _ml)

import pytest
from scripts.misc.automated_deployment_pipeline import (
    AutomatedDeploymentPipeline,
    Deployment,
    DeploymentStage,
)


# ── fixtures ────────────────────────────────────────────────────────────────
@pytest.fixture
def adp(tmp_path):
    cfg_path = tmp_path / "adp_cfg.json"
    p = AutomatedDeploymentPipeline(config_path=str(cfg_path))
    # redirect history to tmp dir so tests are isolated
    p.history_file = tmp_path / "adp_history.json"
    p.deployment_history = []
    return p


# ── TestDeploymentStage ────────────────────────────────────────────────────
class TestDeploymentStage:
    def test_fields(self):
        stage = DeploymentStage(
            stage_id="s1",
            name="Build",
            commands=["make build"],
            rollback_commands=["make clean"],
            timeout=120,
            required=True,
        )
        assert stage.stage_id == "s1"
        assert stage.name == "Build"
        assert stage.timeout == 120
        assert stage.required is True


# ── TestDeployment ─────────────────────────────────────────────────────────
class TestDeployment:
    def test_fields(self):
        d = Deployment(
            deployment_id="d1",
            branch="main",
            commit_hash="abc1234",
            target_devices=["dev1"],
            stages=[],
            status="pending",
            started_at=datetime.now().isoformat(),
            completed_at=None,
        )
        assert d.deployment_id == "d1"
        assert d.branch == "main"
        assert d.status == "pending"


# ── TestInit ───────────────────────────────────────────────────────────────
class TestInit:
    def test_config_file_created(self, tmp_path):
        cfg = tmp_path / "cfg2.json"
        adp = AutomatedDeploymentPipeline(config_path=str(cfg))
        assert cfg.exists()

    def test_default_config_has_required_keys(self, tmp_path):
        cfg = tmp_path / "cfg3.json"
        adp = AutomatedDeploymentPipeline(config_path=str(cfg))
        with open(cfg, encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, dict)
        assert "git_branch" in data or "stages" in data


# ── TestRunCommand ─────────────────────────────────────────────────────────
class TestRunCommand:
    def test_success(self, adp):
        mock_result = MagicMock(returncode=0, stdout="ok", stderr="")
        with patch("subprocess.run", return_value=mock_result):
            result = adp._run_command("echo hello", timeout=10)
        assert result["success"] is True

    def test_nonzero_returncode_fails(self, adp):
        mock_result = MagicMock(returncode=1, stdout="", stderr="error msg")
        with patch("subprocess.run", return_value=mock_result):
            result = adp._run_command("exit 1", timeout=10)
        assert result["success"] is False

    def test_timeout_returns_failure(self, adp):
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="cmd", timeout=1)):
            result = adp._run_command("sleep 999", timeout=1)
        assert result["success"] is False
        assert "error" in result


# ── TestGetStats ───────────────────────────────────────────────────────────
class TestGetStats:
    def test_empty_history_stats(self, adp):
        stats = adp.get_stats()
        assert stats["total_deployments"] == 0

    def _make_dep(self, dep_id, status):
        return Deployment(
            deployment_id=dep_id, branch="main", commit_hash="abc",
            target_devices=[], stages=[], status=status,
        )

    def test_counts_completed(self, adp):
        adp.deployment_history = [
            self._make_dep("a", "completed"),
            self._make_dep("b", "failed"),
            self._make_dep("c", "completed"),
        ]
        stats = adp.get_stats()
        assert stats["total_deployments"] == 3
        assert stats["successful_deployments"] == 2
        assert stats["failed_deployments"] == 1

    def test_success_rate_full_success(self, adp):
        adp.deployment_history = [
            self._make_dep("x", "completed"),
            self._make_dep("y", "completed"),
        ]
        stats = adp.get_stats()
        assert stats["success_rate"] == 1.0


# ── TestGetDeploymentStatus ────────────────────────────────────────────────
class TestGetDeploymentStatus:
    def test_nonexistent_id_returns_none(self, adp):
        result = adp.get_deployment_status("no_such_id")
        assert result is None

    def test_existing_id_returns_deployment(self, adp):
        d_id = "dep_abc"
        dep = Deployment(
            deployment_id=d_id, branch="main", commit_hash="abc",
            target_devices=[], stages=[], status="completed",
        )
        adp.deployment_history = [dep]
        result = adp.get_deployment_status(d_id)
        assert result is not None
        assert result.deployment_id == d_id
