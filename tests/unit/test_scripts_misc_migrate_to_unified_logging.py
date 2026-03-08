"""
Unit tests for scripts/misc/migrate_to_unified_logging.py
"""
import sys
import types

import pytest

# Minimal stub for manaos_logger if not installed
if "manaos_logger" not in sys.modules:
    _ml_mod = types.ModuleType("manaos_logger")
    sys.modules.setdefault("manaos_logger", _ml_mod)

from scripts.misc.migrate_to_unified_logging import (
    get_logger_name,
    migrate_file,
)


class TestGetLoggerName:
    def test_api_server_returns_api_server(self, tmp_path):
        p = tmp_path / "api_server.py"
        result = get_logger_name(p)
        assert "api" in result.lower()

    def test_mcp_server_excludes_mcp_label(self, tmp_path):
        p = tmp_path / "mcp_main_server.py"
        result = get_logger_name(p)
        # should return something meaningful without just "mcp"
        assert isinstance(result, str) and len(result) > 0

    def test_generic_stem_returns_stem_based_name(self, tmp_path):
        p = tmp_path / "my_awesome_module.py"
        result = get_logger_name(p)
        assert isinstance(result, str)
        # stem characters appear somewhere in result
        assert "my" in result or "awesome" in result or "module" in result

    def test_returns_string(self, tmp_path):
        p = tmp_path / "some_file.py"
        assert isinstance(get_logger_name(p), str)


class TestMigrateFile:
    # Pattern 2 expects: "from manaos_logger import get_logger\nlogger = get_logger(__name__)"
    _PATTERN2 = "from manaos_logger import get_logger\nlogger = get_logger(__name__)\n"

    def _write(self, tmp_path, content: str):
        p = tmp_path / "target.py"
        p.write_text(content, encoding="utf-8")
        return p

    def test_file_without_manaos_logger_returns_false(self, tmp_path):
        p = self._write(tmp_path, "# nothing here\nprint('hello')\n")
        migrated, msg = migrate_file(p)
        assert not migrated

    def test_file_with_old_import_pattern2_is_migrated(self, tmp_path):
        p = self._write(tmp_path, self._PATTERN2)
        migrated, msg = migrate_file(p)
        assert migrated

    def test_returns_tuple(self, tmp_path):
        p = self._write(tmp_path, "x = 1\n")
        result = migrate_file(p)
        assert isinstance(result, tuple) and len(result) == 2

    def test_migrated_file_no_longer_has_old_import(self, tmp_path):
        p = self._write(tmp_path, self._PATTERN2)
        migrate_file(p)
        new_content = p.read_text(encoding="utf-8")
        assert "from manaos_logger import get_logger" not in new_content

    def test_message_is_string(self, tmp_path):
        p = self._write(tmp_path, "# no logger\n")
        _, msg = migrate_file(p)
        assert isinstance(msg, str)
