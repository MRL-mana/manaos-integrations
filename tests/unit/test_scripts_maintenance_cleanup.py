"""
tests/unit/test_scripts_maintenance_cleanup.py
scripts/maintenance/cleanup_temp_files.py の純粋関数テスト

対象関数:
  - should_exclude(path)
  - get_file_age_days(file_path)
"""
import sys
import time
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts" / "maintenance"))

from cleanup_temp_files import should_exclude, get_file_age_days  # type: ignore


# ─── should_exclude ───────────────────────────────────────────────────────────

class TestShouldExclude:
    def test_git_dir_excluded(self):
        assert should_exclude(Path(".git/config")) is True

    def test_venv_excluded(self):
        assert should_exclude(Path("venv/lib/python3.10/site-packages")) is True

    def test_dot_venv_excluded(self):
        assert should_exclude(Path(".venv/Scripts/python.exe")) is True

    def test_env_excluded(self):
        assert should_exclude(Path("env/bin/activate")) is True

    def test_node_modules_excluded(self):
        assert should_exclude(Path("node_modules/lodash/index.js")) is True

    def test_d_drive_excluded(self):
        assert should_exclude(Path("D:/something/data.py")) is True

    def test_normal_src_not_excluded(self):
        assert should_exclude(Path("src/main.py")) is False

    def test_temp_dir_not_excluded(self):
        # "temp" だけでは除外対象外
        assert should_exclude(Path("scripts/temp/somefile.py")) is False

    def test_scripts_checks_not_excluded(self):
        assert should_exclude(Path("scripts/checks/check_foo.py")) is False

    def test_deep_path_not_excluded(self):
        assert should_exclude(Path("tools/trinity_system_optimizer.py")) is False


# ─── get_file_age_days ────────────────────────────────────────────────────────

class TestGetFileAgeDays:
    def test_just_created_file_age_near_zero(self, tmp_path):
        f = tmp_path / "new.txt"
        f.write_text("hello")
        age = get_file_age_days(f)
        assert isinstance(age, float)
        # 作成直後は 1 日未満（Windows タイミング誤差を考慮して -1 まで許容）
        assert -1 < age < 1

    def test_nonexistent_file_returns_zero(self, tmp_path):
        fake = tmp_path / "ghost.txt"
        age = get_file_age_days(fake)
        assert age == 0

    def test_returns_float(self, tmp_path):
        f = tmp_path / "floattest.txt"
        f.write_text("x")
        result = get_file_age_days(f)
        assert isinstance(result, float)

    def test_old_file_has_positive_age(self, tmp_path):
        import os
        f = tmp_path / "old.txt"
        f.write_text("data")
        # mtime を 5 日前に書き換え
        old_time = time.time() - 5 * 86400
        os.utime(str(f), (old_time, old_time))
        age = get_file_age_days(f)
        assert age >= 4.9  # 多少の誤差を許容
