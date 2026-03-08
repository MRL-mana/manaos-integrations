"""
Unit tests for scripts/misc/local_oss_absorption.py
（純粋な Python クラス - 外部依存なし）
"""
import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

import pytest

from scripts.misc.local_oss_absorption import LocalOSSAbsorption


# ─── helpers ──────────────────────────────────────────────────────────────────
def _make_instance(tmp_path: Path, profile: dict | None = None) -> LocalOSSAbsorption:
    """一時ディレクトリにプロファイルを配置してインスタンス生成"""
    if profile is not None:
        cfg_dir = tmp_path / "config"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        (cfg_dir / "local_oss_profile.json").write_text(
            json.dumps(profile), encoding="utf-8"
        )
    return LocalOSSAbsorption(base_dir=str(tmp_path))


# ─── Init & profile loading ───────────────────────────────────────────────────
class TestLocalOSSAbsorptionInit:
    def test_no_profile_available_false(self, tmp_path: Path):
        obj = LocalOSSAbsorption(base_dir=str(tmp_path))
        assert obj.get_status()["available"] is False

    def test_with_profile_available_true(self, tmp_path: Path):
        profile = {"profile_name": "test-profile", "notes": {}, "oh_my_opencode": {}}
        obj = _make_instance(tmp_path, profile=profile)
        assert obj.get_status()["available"] is True
        assert obj.get_status()["profile_name"] == "test-profile"

    def test_invalid_json_profile_handled(self, tmp_path: Path):
        cfg_dir = tmp_path / "config"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        (cfg_dir / "local_oss_profile.json").write_text("NOT JSON", encoding="utf-8")
        obj = LocalOSSAbsorption(base_dir=str(tmp_path))
        assert obj.get_status()["available"] is False


# ─── get_status ───────────────────────────────────────────────────────────────
class TestGetStatus:
    def test_returns_notes_files_count(self, tmp_path: Path):
        profile = {"profile_name": "p", "notes": {"directory": "notes", "glob": "**/*.md"}}
        obj = _make_instance(tmp_path, profile=profile)
        notes_dir = tmp_path / "notes"
        notes_dir.mkdir()
        (notes_dir / "a.md").write_text("hello", encoding="utf-8")
        (notes_dir / "b.md").write_text("world", encoding="utf-8")
        status = obj.get_status()
        assert status["notes_files"] == 2

    def test_zero_notes_when_dir_missing(self, tmp_path: Path):
        profile = {"profile_name": "p", "notes": {"directory": "nodir"}}
        obj = _make_instance(tmp_path, profile=profile)
        assert obj.get_status()["notes_files"] == 0


# ─── _list_notes ──────────────────────────────────────────────────────────────
class TestListNotes:
    def test_returns_empty_without_dir(self, tmp_path: Path):
        obj = LocalOSSAbsorption(base_dir=str(tmp_path))
        assert obj._list_notes() == []

    def test_returns_md_files(self, tmp_path: Path):
        notes = tmp_path / "notes"
        notes.mkdir()
        (notes / "x.md").write_text("x", encoding="utf-8")
        (notes / "y.txt").write_text("y", encoding="utf-8")
        obj = LocalOSSAbsorption(base_dir=str(tmp_path))
        result = obj._list_notes()
        names = [f.name for f in result]
        assert "x.md" in names
        assert "y.txt" not in names


# ─── _build_context ───────────────────────────────────────────────────────────
class TestBuildContext:
    def test_empty_when_no_notes(self, tmp_path: Path):
        obj = LocalOSSAbsorption(base_dir=str(tmp_path))
        ctx = obj._build_context()
        assert ctx == ""

    def test_includes_note_content(self, tmp_path: Path):
        notes = tmp_path / "notes"
        notes.mkdir()
        (notes / "memo.md").write_text("important information", encoding="utf-8")
        obj = LocalOSSAbsorption(base_dir=str(tmp_path))
        ctx = obj._build_context()
        assert "important information" in ctx

    def test_query_matching_notes_prioritized(self, tmp_path: Path):
        notes = tmp_path / "notes"
        notes.mkdir()
        (notes / "alpha.md").write_text("python programming", encoding="utf-8")
        (notes / "beta.md").write_text("java programming", encoding="utf-8")
        obj = LocalOSSAbsorption(base_dir=str(tmp_path))
        ctx = obj._build_context(query="python")
        # alpha.md (contains "python") should appear before beta.md
        assert ctx.index("alpha.md") < ctx.index("beta.md")

    def test_truncates_by_max_files(self, tmp_path: Path):
        profile = {"notes": {"directory": "notes", "max_context_files": 2}}
        obj = _make_instance(tmp_path, profile=profile)
        notes = tmp_path / "notes"
        notes.mkdir()
        for i in range(5):
            (notes / f"note{i}.md").write_text(f"content {i}", encoding="utf-8")
        ctx = obj._build_context()
        # Should only include 2 files
        file_count = ctx.count("## note")
        assert file_count == 2


# ─── _write_note ──────────────────────────────────────────────────────────────
class TestWriteNote:
    def test_creates_note_file(self, tmp_path: Path):
        obj = LocalOSSAbsorption(base_dir=str(tmp_path))
        p = obj._write_note("test-title", "some content")
        assert p.exists()
        assert "test-title" in p.name
        assert p.read_text(encoding="utf-8") == "some content"


# ─── execute ──────────────────────────────────────────────────────────────────
class TestExecute:
    def test_unavailable_when_no_oh_my_opencode(self, tmp_path: Path):
        obj = LocalOSSAbsorption(base_dir=str(tmp_path))
        result = asyncio.run(obj.execute("do something", integrations={}))
        assert result["status"] == "unavailable"

    def test_delegates_to_oh_my_opencode(self, tmp_path: Path):
        obj = LocalOSSAbsorption(base_dir=str(tmp_path))
        fake_result = MagicMock()
        fake_result.status = "success"
        fake_result.task_id = "task-123"
        fake_result.cost = 0.05
        fake_result.execution_time = 3.0
        fake_result.iterations = 1
        fake_result.error = None
        fake_result.result = "done"
        oh_mock = MagicMock()
        oh_mock.execute_task = AsyncMock(return_value=fake_result)
        result = asyncio.run(
            obj.execute("task description", integrations={"oh_my_opencode": oh_mock})
        )
        assert result["status"] == "success"
        assert result["task_id"] == "task-123"

    def test_error_when_execute_task_raises(self, tmp_path: Path):
        obj = LocalOSSAbsorption(base_dir=str(tmp_path))
        oh_mock = MagicMock()
        oh_mock.execute_task = AsyncMock(side_effect=RuntimeError("agent error"))
        result = asyncio.run(
            obj.execute("broken task", integrations={"oh_my_opencode": oh_mock})
        )
        assert result["status"] == "error"
        assert "agent error" in result["error"]

    def test_writes_note_when_requested(self, tmp_path: Path):
        obj = LocalOSSAbsorption(base_dir=str(tmp_path))
        fake_result = MagicMock()
        fake_result.status = "success"
        fake_result.task_id = "t1"
        fake_result.cost = None
        fake_result.execution_time = None
        fake_result.iterations = None
        fake_result.error = None
        fake_result.result = None
        oh_mock = MagicMock()
        oh_mock.execute_task = AsyncMock(return_value=fake_result)
        result = asyncio.run(
            obj.execute(
                "task",
                integrations={"oh_my_opencode": oh_mock},
                write_note=True,
                note_title="my-note"
            )
        )
        assert "note_path" in result
        assert Path(result["note_path"]).exists()

    def test_context_injected_with_notes(self, tmp_path: Path):
        notes_dir = tmp_path / "notes"
        notes_dir.mkdir()
        (notes_dir / "info.md").write_text("context data", encoding="utf-8")
        obj = LocalOSSAbsorption(base_dir=str(tmp_path))
        captured_prompt = {}
        async def fake_execute_task(task_description, mode=None, task_type=None, use_trinity=None):
            captured_prompt["val"] = task_description
            r = MagicMock()
            r.status = "success"; r.task_id = None; r.cost = None
            r.execution_time = None; r.iterations = None; r.error = None; r.result = None
            return r
        oh_mock = MagicMock()
        oh_mock.execute_task = fake_execute_task
        asyncio.run(obj.execute("do work", integrations={"oh_my_opencode": oh_mock}))
        assert "context data" in captured_prompt.get("val", "")
