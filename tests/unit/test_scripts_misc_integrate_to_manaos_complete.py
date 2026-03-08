"""tests/unit/test_scripts_misc_integrate_to_manaos_complete.py

integrate_to_manaos_complete.py の単体テスト
"""
import json
from pathlib import Path
import pytest

import scripts.misc.integrate_to_manaos_complete as _mod


class TestCheckMcpIntegration:
    def test_returns_true_when_no_config_file(self, tmp_path, monkeypatch):
        # ~/.cursor/mcp.json が存在しない場合
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        result = _mod.check_mcp_integration()
        assert result is True

    def test_returns_true_when_config_exists(self, tmp_path, monkeypatch):
        cursor_dir = tmp_path / ".cursor"
        cursor_dir.mkdir()
        config = {
            "mcpServers": {
                "manaos": {
                    "env": {
                        "BRAVE_API_KEY": "test_key",
                    }
                }
            }
        }
        (cursor_dir / "mcp.json").write_text(json.dumps(config), encoding="utf-8")
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        result = _mod.check_mcp_integration()
        assert result is True

    def test_returns_false_on_exception(self, monkeypatch):
        def _raise(*a, **kw):
            raise RuntimeError("unexpected error")
        # Cause an exception by making Path.home raise
        monkeypatch.setattr(Path, "home", _raise)
        result = _mod.check_mcp_integration()
        assert result is False


class TestCheckUnifiedApiIntegration:
    def test_returns_bool(self, monkeypatch):
        # unified_api_server が importable かどうかに関係なく bool を返す
        result = _mod.check_unified_api_integration()
        assert isinstance(result, bool)
