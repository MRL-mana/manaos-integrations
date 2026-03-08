"""Tests for scripts/misc/production_first_run.py"""
import importlib
import sys
from unittest.mock import MagicMock

import pytest


@pytest.fixture(scope="module")
def _mod():
    sys.path.insert(0, "scripts/misc")
    if "production_first_run" in sys.modules:
        return sys.modules["production_first_run"]
    return importlib.import_module("production_first_run")


class TestMain:
    def test_main_runs_without_error(self, _mod, monkeypatch):
        """run_list_files_only をモックして main() が例外なく完走すること"""
        mock_result = {
            "plan_id": "test-001",
            "status": "success",
            "executor": "test",
            "list_files_result": {"files": ["file1.txt", "file2.txt"]},
        }
        monkeypatch.setattr(_mod, "run_list_files_only", lambda: mock_result)
        _mod.main()  # raises がなければ OK

    def test_main_handles_empty_result(self, _mod, monkeypatch):
        """run_list_files_only が空 dict を返しても main() が例外なく完走すること"""
        monkeypatch.setattr(_mod, "run_list_files_only", lambda: {})
        _mod.main()  # raises がなければ OK
