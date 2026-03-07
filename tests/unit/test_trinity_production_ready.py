"""Unit tests for tools/trinity_production_ready.py."""

from __future__ import annotations

import builtins
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tools"))
from trinity_production_ready import ProductionReadinessCheck


# ─────────────────────────────────────────────────────────────────────────────
# __init__
# ─────────────────────────────────────────────────────────────────────────────

class TestInit:
    def test_checks_passed_starts_at_zero(self):
        checker = ProductionReadinessCheck()
        assert checker.checks_passed == 0

    def test_checks_failed_starts_at_zero(self):
        checker = ProductionReadinessCheck()
        assert checker.checks_failed == 0

    def test_root_is_path_object(self):
        checker = ProductionReadinessCheck()
        assert isinstance(checker.root, Path)


# ─────────────────────────────────────────────────────────────────────────────
# check_directory_structure
# ─────────────────────────────────────────────────────────────────────────────

class TestCheckDirectoryStructure:
    _REQUIRED = [
        "core", "agents", "dashboard", "integrations",
        "shared", "logs", "tests", "scripts",
    ]

    def test_all_dirs_exist_no_exception(self, tmp_path):
        checker = ProductionReadinessCheck()
        checker.root = tmp_path
        for name in self._REQUIRED:
            (tmp_path / name).mkdir()
        checker.check_directory_structure()  # must not raise

    def test_missing_dir_raises(self, tmp_path):
        checker = ProductionReadinessCheck()
        checker.root = tmp_path
        # 一部しか作らない
        for name in self._REQUIRED[:-1]:
            (tmp_path / name).mkdir()
        with pytest.raises(Exception):
            checker.check_directory_structure()

    def test_empty_root_raises(self, tmp_path):
        checker = ProductionReadinessCheck()
        checker.root = tmp_path
        with pytest.raises(Exception):
            checker.check_directory_structure()


# ─────────────────────────────────────────────────────────────────────────────
# check_log_directories
# ─────────────────────────────────────────────────────────────────────────────

class TestCheckLogDirectories:
    def test_creates_missing_logs_dir(self, tmp_path):
        checker = ProductionReadinessCheck()
        checker.root = tmp_path
        checker.check_log_directories()
        assert (tmp_path / "logs").is_dir()

    def test_existing_logs_dir_no_exception(self, tmp_path):
        checker = ProductionReadinessCheck()
        checker.root = tmp_path
        (tmp_path / "logs").mkdir()
        checker.check_log_directories()  # must not raise

    def test_no_write_test_file_leftover(self, tmp_path):
        checker = ProductionReadinessCheck()
        checker.root = tmp_path
        checker.check_log_directories()
        assert not (tmp_path / "logs" / ".write_test").exists()


# ─────────────────────────────────────────────────────────────────────────────
# check_ports
# ─────────────────────────────────────────────────────────────────────────────

class TestCheckPorts:
    def test_port_in_use_no_exception(self):
        checker = ProductionReadinessCheck()
        with patch("subprocess.run", return_value=MagicMock(returncode=0)):
            checker.check_ports()  # must not raise

    def test_port_not_in_use_raises(self):
        checker = ProductionReadinessCheck()
        with patch("subprocess.run", return_value=MagicMock(returncode=1)):
            with pytest.raises(Exception, match="ダッシュボード"):
                checker.check_ports()


# ─────────────────────────────────────────────────────────────────────────────
# check_python_dependencies
# ─────────────────────────────────────────────────────────────────────────────

class TestCheckPythonDependencies:
    def test_missing_package_raises(self):
        """builtins.__import__ を差し替えて flask を見つからなくする。"""
        checker = ProductionReadinessCheck()
        original_import = builtins.__import__

        def block_flask(name, *args, **kwargs):
            if name in ("flask", "flask_socketio", "flask_cors"):
                raise ImportError(f"blocked: {name}")
            return original_import(name, *args, **kwargs)

        with patch.object(builtins, "__import__", side_effect=block_flask):
            with pytest.raises(Exception, match="不足"):
                checker.check_python_dependencies()

    def test_no_missing_packages_no_exception(self):
        """実際にインストール済みのパッケージを全部モックして通過させる。"""
        checker = ProductionReadinessCheck()
        original_import = builtins.__import__
        checked = {"flask", "flask_socketio", "flask_cors", "click", "tabulate", "watchdog"}

        def allow_all(name, *args, **kwargs):
            if name.replace("-", "_") in checked:
                return MagicMock()
            return original_import(name, *args, **kwargs)

        with patch.object(builtins, "__import__", side_effect=allow_all):
            checker.check_python_dependencies()  # must not raise


# ─────────────────────────────────────────────────────────────────────────────
# run_all_checks  —  各 check メソッドをモックしてカウンタを検証
# ─────────────────────────────────────────────────────────────────────────────

class TestRunAllChecks:
    def test_all_pass_increments_passed_counter(self):
        checker = ProductionReadinessCheck()
        with patch.multiple(
            checker,
            check_directory_structure=MagicMock(),
            check_python_dependencies=MagicMock(),
            check_database_integrity=MagicMock(),
            check_log_directories=MagicMock(),
            check_permissions=MagicMock(),
            check_ports=MagicMock(),
            print_recommendations=MagicMock(),
        ):
            checker.run_all_checks()
        assert checker.checks_passed == 6
        assert checker.checks_failed == 0

    def test_one_failure_increments_failed_counter(self):
        checker = ProductionReadinessCheck()
        with patch.multiple(
            checker,
            check_directory_structure=MagicMock(side_effect=Exception("FAIL")),
            check_python_dependencies=MagicMock(),
            check_database_integrity=MagicMock(),
            check_log_directories=MagicMock(),
            check_permissions=MagicMock(),
            check_ports=MagicMock(),
            print_recommendations=MagicMock(),
        ):
            checker.run_all_checks()
        assert checker.checks_failed == 1
        assert checker.checks_passed == 5
