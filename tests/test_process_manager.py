#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
テスト: manaos_process_manager モジュール
ProcessManager の各メソッドを検証
"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from manaos_process_manager import ProcessManager, get_process_manager


class TestProcessManagerInit:
    """初期化"""

    def test_creates_instance(self):
        pm = ProcessManager("test")
        assert pm.service_name == "test"

    def test_singleton(self):
        pm1 = get_process_manager("A")
        pm2 = get_process_manager("B")
        # 最初に作成されたインスタンスが返される
        assert pm1 is pm2


class TestCheckPortInUse:
    """ポートチェック"""

    def test_unused_port_returns_false(self):
        pm = ProcessManager("test")
        # 極端に使われないポート
        assert pm.check_port_in_use(59999) is False


class TestGetProcessesByPort:
    """ポート指定プロセス取得"""

    def test_unused_port_returns_empty(self):
        pm = ProcessManager("test")
        result = pm.get_processes_by_port(59999)
        assert result == []


class TestKillByPid:
    """PID 指定終了"""

    def test_nonexistent_pid(self):
        pm = ProcessManager("test")
        # 存在しない PID は NoSuchProcess で True を返す
        result = pm.kill_by_pid(999999999)
        assert result is True


class TestKillProcessesByKeywords:
    """キーワード指定終了"""

    def test_no_match_returns_zero(self):
        pm = ProcessManager("test")
        result = pm.kill_processes_by_keywords(
            ["__nonexistent_keyword_xyzzy__"]
        )
        assert result == 0


class TestListTopProcesses:
    """トッププロセス一覧"""

    def test_returns_list(self):
        pm = ProcessManager("test")
        result = pm.list_top_processes(sort_by="cpu", limit=5)
        assert isinstance(result, list)
        assert len(result) <= 5

    def test_each_has_required_keys(self):
        pm = ProcessManager("test")
        result = pm.list_top_processes(limit=3)
        for p in result:
            assert "pid" in p
            assert "name" in p
            assert "cpu_percent" in p
            assert "memory_mb" in p

    def test_sort_by_memory(self):
        pm = ProcessManager("test")
        result = pm.list_top_processes(sort_by="memory", limit=5)
        if len(result) >= 2:
            assert result[0]["memory_mb"] >= result[1]["memory_mb"]


class TestGetProcessInfo:
    """スクリプト名でプロセス情報取得"""

    def test_nonexistent_script(self):
        pm = ProcessManager("test")
        result = pm.get_process_info("__definitely_not_running_script.py")
        assert result is None


class TestSaveAndCleanup:
    """プロセス情報の保存とクリーンアップ"""

    def test_save_creates_file(self, tmp_path):
        pm = ProcessManager("test")
        pm.process_info_file = tmp_path / "process_info.json"
        pm.save_process_info("test_script.py", 12345)
        assert pm.process_info_file.exists()
        data = json.loads(pm.process_info_file.read_text())
        assert "test_script.py" in data
        assert data["test_script.py"]["pid"] == 12345

    def test_cleanup_removes_entry(self, tmp_path):
        pm = ProcessManager("test")
        pm.process_info_file = tmp_path / "process_info.json"
        pm.save_process_info("test_script.py", 999999999)
        result = pm.cleanup_process("test_script.py")
        assert result is True
        data = json.loads(pm.process_info_file.read_text())
        assert "test_script.py" not in data
