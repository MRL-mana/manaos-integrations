"""tests/unit/test_scripts_misc_set_openrouter_api_key.py

set_openrouter_api_key.py の単体テスト
"""
from pathlib import Path
import pytest

import scripts.misc.set_openrouter_api_key as _mod


class TestUpdateEnvFile:
    def test_creates_new_env_file(self, tmp_path, monkeypatch):
        real_Path = Path

        def mock_path_ctor(arg):
            if arg == _mod.__file__:
                return tmp_path / "dummy_script.py"
            return real_Path(arg)

        monkeypatch.setattr(_mod, "Path", mock_path_ctor)
        result = _mod.update_env_file()
        assert result is True
        env_file = tmp_path / ".env"
        assert env_file.exists()
        assert "OPENROUTER_API_KEY" in env_file.read_text(encoding="utf-8")

    def test_updates_existing_env_file(self, tmp_path, monkeypatch):
        real_Path = Path

        def mock_path_ctor(arg):
            if arg == _mod.__file__:
                return tmp_path / "dummy_script.py"
            return real_Path(arg)

        env_file = tmp_path / ".env"
        env_file.write_text("OPENROUTER_API_KEY=old_key\nOTHER_VAR=abc\n", encoding="utf-8")
        monkeypatch.setattr(_mod, "Path", mock_path_ctor)
        result = _mod.update_env_file()
        assert result is True
        content = env_file.read_text(encoding="utf-8")
        # old key should be replaced
        assert "old_key" not in content

    def test_appends_to_existing_file_without_key(self, tmp_path, monkeypatch):
        real_Path = Path

        def mock_path_ctor(arg):
            if arg == _mod.__file__:
                return tmp_path / "dummy_script.py"
            return real_Path(arg)

        env_file = tmp_path / ".env"
        env_file.write_text("OTHER_VAR=abc\n", encoding="utf-8")
        monkeypatch.setattr(_mod, "Path", mock_path_ctor)
        result = _mod.update_env_file()
        assert result is True
        content = env_file.read_text(encoding="utf-8")
        assert "OPENROUTER_API_KEY" in content


class TestSetEnvironmentVariable:
    def test_returns_true_on_success(self, monkeypatch):
        import winreg

        mock_key = object()
        monkeypatch.setattr(winreg, "OpenKey", lambda *a, **kw: mock_key)
        monkeypatch.setattr(winreg, "SetValueEx", lambda *a, **kw: None)
        monkeypatch.setattr(winreg, "CloseKey", lambda k: None)

        result = _mod.set_environment_variable()
        assert result is True

    def test_returns_false_on_exception(self, monkeypatch):
        import winreg

        def _raise(*a, **kw):
            raise OSError("registry access denied")

        monkeypatch.setattr(winreg, "OpenKey", _raise)
        result = _mod.set_environment_variable()
        assert result is False
