"""
Unit tests for scripts/misc/vscode_cursor_integration.py
"""
import json
import sys
from pathlib import Path

import pytest
from scripts.misc.vscode_cursor_integration import VSCodeManaOSIntegration


# ── helpers ───────────────────────────────────────────────────────────────

def _make_vi(tmp_path: Path) -> VSCodeManaOSIntegration:
    vi = VSCodeManaOSIntegration.__new__(VSCodeManaOSIntegration)
    vi.home_dir = tmp_path
    vi.vscode_dir = tmp_path / ".vscode"
    vi.cursor_dir = tmp_path / ".cursor"
    vi.manaos_path = Path(__file__).resolve().parent
    vi._appdata_dir = tmp_path / "AppData"
    return vi


@pytest.fixture
def vi(tmp_path):
    return _make_vi(tmp_path)


# ── TestInit ──────────────────────────────────────────────────────────────
class TestInit:
    def test_paths_set(self):
        vi = VSCodeManaOSIntegration()
        assert vi.home_dir is not None
        assert vi.vscode_dir == vi.home_dir / ".vscode"
        assert vi.cursor_dir == vi.home_dir / ".cursor"


# ── TestGetPaths ──────────────────────────────────────────────────────────
class TestGetPaths:
    def test_vscode_settings_path(self, vi, tmp_path):
        path = vi.get_vscode_settings_path()
        assert path == tmp_path / ".vscode" / "settings.json"

    def test_cursor_settings_path(self, vi, tmp_path):
        path = vi.get_cursor_settings_path()
        assert path == tmp_path / ".cursor" / "settings.json"

    def test_vscode_mcp_config_path(self, vi, tmp_path):
        path = vi.get_vscode_mcp_config_path()
        assert path == tmp_path / ".vscode" / "mcp.json"

    def test_cursor_mcp_config_path(self, vi, tmp_path):
        path = vi.get_cursor_mcp_config_path()
        assert path == tmp_path / ".cursor" / "mcp.json"


# ── TestGetClineMcpSettingsPath ───────────────────────────────────────────
class TestGetClineMcpSettingsPath:
    def test_non_windows_or_no_appdata_returns_none(self, vi):
        vi._appdata_dir = None
        path = vi.get_cline_mcp_settings_path()
        assert path is None

    def test_returns_path_on_windows(self, vi, tmp_path):
        if sys.platform != "win32":
            pytest.skip("Windows-only test")
        vi._appdata_dir = tmp_path
        path = vi.get_cline_mcp_settings_path()
        assert path is not None
        assert "cline_mcp_settings.json" in str(path)


# ── TestCreateVscodeManaosSettings ────────────────────────────────────────
class TestCreateVscodeManaosSettings:
    def test_returns_dict(self, vi):
        settings = vi.create_vscode_manaos_settings()
        assert isinstance(settings, dict)

    def test_has_manaos_key(self, vi):
        settings = vi.create_vscode_manaos_settings()
        assert "manaos" in settings

    def test_manaos_enabled(self, vi):
        settings = vi.create_vscode_manaos_settings()
        assert settings["manaos"]["enabled"] is True

    def test_has_memory_config(self, vi):
        settings = vi.create_vscode_manaos_settings()
        memory = settings["manaos"]["memory"]
        assert memory["enabled"] is True
        assert "apiUrl" in memory


# ── TestCreateVscodeMcpServers ────────────────────────────────────────────
class TestCreateVscodeMcpServers:
    def test_returns_dict(self, vi):
        servers = vi.create_vscode_mcp_servers()
        assert isinstance(servers, dict)

    def test_has_required_servers(self, vi):
        servers = vi.create_vscode_mcp_servers()
        assert "manaos-unified-api" in servers
        assert "manaos-video-pipeline" in servers
        assert "manaos-pico-hid" in servers
        assert "manaos-gallery-api" in servers

    def test_server_has_command(self, vi):
        servers = vi.create_vscode_mcp_servers()
        for name, server in servers.items():
            assert "command" in server, f"{name} missing 'command'"
            assert "args" in server, f"{name} missing 'args'"
            assert "env" in server, f"{name} missing 'env'"


# ── TestCreateClineMcpServers ─────────────────────────────────────────────
class TestCreateClineMcpServers:
    def test_returns_dict(self, vi):
        servers = vi.create_cline_mcp_servers()
        assert isinstance(servers, dict)

    def test_has_required_servers(self, vi):
        servers = vi.create_cline_mcp_servers()
        assert "manaos-unified-api" in servers
        assert "manaos-gallery-api" in servers

    def test_server_structure(self, vi):
        servers = vi.create_cline_mcp_servers()
        for name, server in servers.items():
            assert "command" in server
            assert "args" in server


# ── TestSetupVscodeMcp ────────────────────────────────────────────────────
class TestSetupVscodeMcp:
    def test_creates_mcp_json(self, vi, tmp_path):
        result = vi.setup_vscode_mcp()
        assert result is True
        mcp_path = vi.get_vscode_mcp_config_path()
        assert mcp_path.exists()

    def test_mcp_json_has_mcp_servers(self, vi, tmp_path):
        vi.setup_vscode_mcp()
        with open(vi.get_vscode_mcp_config_path(), encoding="utf-8") as f:
            config = json.load(f)
        assert "mcpServers" in config
        assert len(config["mcpServers"]) > 0

    def test_merges_existing_config(self, vi, tmp_path):
        mcp_path = vi.get_vscode_mcp_config_path()
        mcp_path.parent.mkdir(parents=True, exist_ok=True)
        existing = {"mcpServers": {"custom-server": {"command": "python"}}, "otherKey": "value"}
        mcp_path.write_text(json.dumps(existing), encoding="utf-8")
        vi.setup_vscode_mcp()
        with open(mcp_path, encoding="utf-8") as f:
            config = json.load(f)
        assert "custom-server" in config["mcpServers"]
        assert "manaos-unified-api" in config["mcpServers"]
        assert config["otherKey"] == "value"

    def test_invalid_existing_config_resets(self, vi, tmp_path):
        mcp_path = vi.get_vscode_mcp_config_path()
        mcp_path.parent.mkdir(parents=True, exist_ok=True)
        mcp_path.write_text("not valid json!!!", encoding="utf-8")
        result = vi.setup_vscode_mcp()
        assert result is True


# ── TestSetupVscode ───────────────────────────────────────────────────────
class TestSetupVscode:
    def test_creates_settings_json(self, vi, tmp_path):
        result = vi.setup_vscode()
        assert result is True
        settings_path = vi.get_vscode_settings_path()
        assert settings_path.exists()

    def test_settings_has_manaos(self, vi, tmp_path):
        vi.setup_vscode()
        with open(vi.get_vscode_settings_path(), encoding="utf-8") as f:
            settings = json.load(f)
        assert "manaos" in settings

    def test_merges_existing_settings(self, vi, tmp_path):
        settings_path = vi.get_vscode_settings_path()
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(json.dumps({"editor.fontSize": 14}), encoding="utf-8")
        vi.setup_vscode()
        with open(settings_path, encoding="utf-8") as f:
            settings = json.load(f)
        assert settings["editor.fontSize"] == 14
        assert "manaos" in settings


# ── TestSetupCursor ───────────────────────────────────────────────────────
class TestSetupCursor:
    def test_returns_false_when_no_mcp_file(self, vi, tmp_path):
        result = vi.setup_cursor()
        assert result is False

    def test_returns_true_when_file_exists(self, vi, tmp_path):
        mcp_path = vi.get_cursor_mcp_config_path()
        mcp_path.parent.mkdir(parents=True, exist_ok=True)
        mcp_path.write_text(json.dumps({"mcpServers": {}}), encoding="utf-8")
        result = vi.setup_cursor()
        assert result is True

    def test_localhost_replaced_with_127(self, vi, tmp_path):
        mcp_path = vi.get_cursor_mcp_config_path()
        mcp_path.parent.mkdir(parents=True, exist_ok=True)
        config = {
            "mcpServers": {
                "srv": {
                    "command": "python",
                    "env": {"MANAOS_INTEGRATION_API_URL": "http://localhost:9502"}
                }
            }
        }
        mcp_path.write_text(json.dumps(config), encoding="utf-8")
        vi.setup_cursor()
        with open(mcp_path, encoding="utf-8") as f:
            updated = json.load(f)
        api_url = updated["mcpServers"]["srv"]["env"]["MANAOS_INTEGRATION_API_URL"]
        assert "127.0.0.1" in api_url
        assert "localhost" not in api_url
