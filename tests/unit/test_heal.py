"""Unit tests for tools/heal.py."""

from __future__ import annotations

import socket
import sys
import textwrap
import urllib.error
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# tools/ を直接 import できるよう sys.path を通す
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tools"))
import heal as heal_mod


# ─────────────────────────────────────────────────────────────────────────────
# topo_sort
# ─────────────────────────────────────────────────────────────────────────────

class TestTopoSort:
    def test_empty_targets(self):
        assert heal_mod.topo_sort([], {}) == []

    def test_no_deps_preserves_order(self):
        services = {
            "a": {"depends_on": []},
            "b": {"depends_on": []},
        }
        result = heal_mod.topo_sort(["a", "b"], services)
        assert result == ["a", "b"]

    def test_dep_comes_first(self):
        # b depends on a → a must precede b
        services = {
            "a": {"depends_on": []},
            "b": {"depends_on": ["a"]},
        }
        result = heal_mod.topo_sort(["b", "a"], services)
        assert result.index("a") < result.index("b")

    def test_chain_of_three(self):
        # c → b → a
        services = {
            "a": {"depends_on": []},
            "b": {"depends_on": ["a"]},
            "c": {"depends_on": ["b"]},
        }
        result = heal_mod.topo_sort(["c", "b", "a"], services)
        assert result.index("a") < result.index("b")
        assert result.index("b") < result.index("c")

    def test_dep_not_in_targets_is_ignored(self):
        # b depends on "x", but "x" is not in targets
        services = {
            "b": {"depends_on": ["x"]},
            "x": {"depends_on": []},
        }
        result = heal_mod.topo_sort(["b"], services)
        assert result == ["b"]

    def test_unknown_service_handled_gracefully(self):
        # target not in services dict
        result = heal_mod.topo_sort(["unknown"], {})
        assert result == ["unknown"]

    def test_diamond_dep_no_duplicates(self):
        # a and b both depend on "base"; c depends on a and b
        services = {
            "base": {"depends_on": []},
            "a": {"depends_on": ["base"]},
            "b": {"depends_on": ["base"]},
            "c": {"depends_on": ["a", "b"]},
        }
        result = heal_mod.topo_sort(["c", "a", "b", "base"], services)
        # base appears exactly once
        assert result.count("base") == 1
        # base before a and b
        assert result.index("base") < result.index("a")
        assert result.index("base") < result.index("b")


# ─────────────────────────────────────────────────────────────────────────────
# is_alive
# ─────────────────────────────────────────────────────────────────────────────

class TestIsAlive:
    def test_health_url_200_returns_true(self):
        svc = {"health_url": "http://127.0.0.1:9999/health"}
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.status = 200
        with patch("urllib.request.urlopen", return_value=mock_resp):
            assert heal_mod.is_alive(svc, timeout=1.0) is True

    def test_health_url_500_returns_false(self):
        svc = {"health_url": "http://127.0.0.1:9999/health"}
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.status = 503
        with patch("urllib.request.urlopen", return_value=mock_resp):
            assert heal_mod.is_alive(svc, timeout=1.0) is False

    def test_health_url_exception_falls_back_to_port_ok(self):
        svc = {"health_url": "http://127.0.0.1:9999/health", "port": 9999}
        mock_sock = MagicMock()
        mock_sock.__enter__ = lambda s: s
        mock_sock.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", side_effect=Exception("connection refused")):
            with patch("socket.create_connection", return_value=mock_sock):
                assert heal_mod.is_alive(svc, timeout=1.0) is True

    def test_no_health_url_port_ok_returns_true(self):
        svc = {"port": 9999}
        mock_sock = MagicMock()
        mock_sock.__enter__ = lambda s: s
        mock_sock.__exit__ = MagicMock(return_value=False)
        with patch("socket.create_connection", return_value=mock_sock):
            assert heal_mod.is_alive(svc, timeout=1.0) is True

    def test_no_health_url_port_fail_returns_false(self):
        svc = {"port": 9999}
        with patch("socket.create_connection", side_effect=OSError("refused")):
            assert heal_mod.is_alive(svc, timeout=1.0) is False

    def test_no_url_no_port_returns_false(self):
        svc: dict[str, Any] = {}
        assert heal_mod.is_alive(svc, timeout=1.0) is False


# ─────────────────────────────────────────────────────────────────────────────
# start_service  (dry_run path)
# ─────────────────────────────────────────────────────────────────────────────

class TestStartServiceDryRun:
    def test_no_start_cmd_returns_false(self, tmp_path):
        svc = {"name": "svc_a"}
        with patch.object(heal_mod, "LOG_DIR", tmp_path), \
             patch.object(heal_mod, "HEAL_LOG", tmp_path / "heal.log"):
            result = heal_mod.start_service(svc, dry_run=True)
        assert result is False

    def test_dry_run_returns_true_without_popen(self, tmp_path):
        svc = {"name": "svc_a", "start_cmd": "python server.py"}
        with patch("subprocess.Popen") as mock_popen, \
             patch.object(heal_mod, "LOG_DIR", tmp_path), \
             patch.object(heal_mod, "HEAL_LOG", tmp_path / "heal.log"):
            result = heal_mod.start_service(svc, dry_run=True)
        assert result is True
        mock_popen.assert_not_called()

    def test_dry_run_with_recovery_hint_in_log(self, tmp_path):
        svc = {
            "name": "svc_a",
            "start_cmd": "python server.py",
            "recovery_hint": "check config.yaml",
        }
        log_file = tmp_path / "heal.log"
        with patch.object(heal_mod, "LOG_DIR", tmp_path), \
             patch.object(heal_mod, "HEAL_LOG", log_file):
            heal_mod.start_service(svc, dry_run=True)
        content = log_file.read_text(encoding="utf-8")
        assert "check config.yaml" in content

    def test_dry_run_python_prefix_replaced(self, tmp_path):
        svc = {"name": "svc_a", "start_cmd": "python my_server.py --port 8080"}
        log_file = tmp_path / "heal.log"
        with patch.object(heal_mod, "LOG_DIR", tmp_path), \
             patch.object(heal_mod, "HEAL_LOG", log_file):
            result = heal_mod.start_service(svc, dry_run=True)
        assert result is True
        content = log_file.read_text(encoding="utf-8")
        # "python " のプレフィックスが sys.executable に置換されているはず
        assert "my_server.py" in content


# ─────────────────────────────────────────────────────────────────────────────
# load_ledger
# ─────────────────────────────────────────────────────────────────────────────

class TestLoadLedger:
    def test_basic_load(self, tmp_path):
        ledger = textwrap.dedent("""\
            core:
              memory:
                port: 5100
                enabled: true
                health_url: http://127.0.0.1:5100/health
                start_cmd: python memory_server.py
            optional:
              analytics:
                port: 5200
                enabled: true
        """)
        ledger_file = tmp_path / "services_ledger.yaml"
        ledger_file.write_text(ledger, encoding="utf-8")

        with patch.object(heal_mod, "LEDGER_PATH", ledger_file):
            services = heal_mod.load_ledger()

        assert "memory" in services
        assert "analytics" in services
        assert services["memory"]["group"] == "core"
        assert services["analytics"]["group"] == "optional"

    def test_name_injected_from_key(self, tmp_path):
        ledger = textwrap.dedent("""\
            core:
              llm_router:
                port: 9502
                enabled: true
        """)
        ledger_file = tmp_path / "services_ledger.yaml"
        ledger_file.write_text(ledger, encoding="utf-8")

        with patch.object(heal_mod, "LEDGER_PATH", ledger_file):
            services = heal_mod.load_ledger()

        assert services["llm_router"]["name"] == "llm_router"

    def test_empty_ledger_returns_empty_dict(self, tmp_path):
        ledger_file = tmp_path / "services_ledger.yaml"
        ledger_file.write_text("", encoding="utf-8")

        with patch.object(heal_mod, "LEDGER_PATH", ledger_file):
            services = heal_mod.load_ledger()

        assert services == {}

    def test_missing_ledger_exits_2(self, tmp_path):
        ledger_file = tmp_path / "nonexistent.yaml"
        with patch.object(heal_mod, "LEDGER_PATH", ledger_file):
            with pytest.raises(SystemExit) as exc:
                heal_mod.load_ledger()
        assert exc.value.code == 2
