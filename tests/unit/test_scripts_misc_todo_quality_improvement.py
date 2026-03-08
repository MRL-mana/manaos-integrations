"""
Unit tests for scripts/misc/todo_quality_improvement.py
"""
import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

import scripts.misc.todo_quality_improvement as _mod


class TestLoadQualityConfig:
    def test_returns_default_when_missing(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(_mod, "QUALITY_CONFIG", tmp_path / "no_config.json")
        result = _mod.load_quality_config()
        assert "banned_tags" in result
        assert "min_granularity" in result

    def test_returns_saved_config(self, tmp_path: Path, monkeypatch):
        cfg_path = tmp_path / "cfg.json"
        cfg_data = {"banned_tags": ["tag1"], "min_granularity": "high"}
        cfg_path.write_text(json.dumps(cfg_data), encoding="utf-8")
        monkeypatch.setattr(_mod, "QUALITY_CONFIG", cfg_path)
        result = _mod.load_quality_config()
        assert result["banned_tags"] == ["tag1"]


class TestSaveQualityConfig:
    def test_creates_file_and_directories(self, tmp_path: Path, monkeypatch):
        deep_path = tmp_path / "deep" / "nested" / "config.json"
        monkeypatch.setattr(_mod, "QUALITY_CONFIG", deep_path)
        _mod.save_quality_config({"min_granularity": "low"})
        assert deep_path.exists()
        data = json.loads(deep_path.read_text(encoding="utf-8"))
        assert data["min_granularity"] == "low"

    def test_overwrites_existing_config(self, tmp_path: Path, monkeypatch):
        cfg_path = tmp_path / "cfg.json"
        cfg_path.write_text('{"old": true}', encoding="utf-8")
        monkeypatch.setattr(_mod, "QUALITY_CONFIG", cfg_path)
        _mod.save_quality_config({"new": True})
        data = json.loads(cfg_path.read_text(encoding="utf-8"))
        assert "new" in data and "old" not in data


class TestRecordRejection:
    def test_writes_jsonl_entry(self, tmp_path: Path, monkeypatch):
        log_path = tmp_path / "rejections.jsonl"
        monkeypatch.setattr(_mod, "REJECTION_LOG", log_path)
        _mod.record_rejection("todo-1", "too vague", "maintenance", ["tag1"], "low")
        lines = log_path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["todo_id"] == "todo-1"
        assert entry["reason"] == "too vague"
        assert entry["category"] == "maintenance"

    def test_uses_provided_datetime(self, tmp_path: Path, monkeypatch):
        log_path = tmp_path / "r.jsonl"
        monkeypatch.setattr(_mod, "REJECTION_LOG", log_path)
        dt = datetime(2026, 1, 1, 12, 0, 0)
        _mod.record_rejection("t1", "reason", "cat", [], "medium", rejected_at=dt)
        entry = json.loads(log_path.read_text(encoding="utf-8").strip())
        assert "2026-01-01" in entry["rejected_at"]

    def test_appends_multiple_entries(self, tmp_path: Path, monkeypatch):
        log_path = tmp_path / "r.jsonl"
        monkeypatch.setattr(_mod, "REJECTION_LOG", log_path)
        for i in range(3):
            _mod.record_rejection(f"t{i}", "reason", "cat", [], "medium")
        lines = log_path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 3


class TestLoadRejections:
    def test_returns_empty_when_file_missing(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(_mod, "REJECTION_LOG", tmp_path / "no_file.jsonl")
        assert _mod.load_rejections() == []

    def test_returns_recent_rejections(self, tmp_path: Path, monkeypatch):
        log_path = tmp_path / "r.jsonl"
        monkeypatch.setattr(_mod, "REJECTION_LOG", log_path)
        recent = datetime.now() - timedelta(days=1)
        entry = {"todo_id": "x", "reason": "r", "category": "c",
                 "tags": [], "granularity": "medium",
                 "rejected_at": recent.isoformat()}
        log_path.write_text(json.dumps(entry) + "\n", encoding="utf-8")
        result = _mod.load_rejections(days=7)
        assert len(result) == 1

    def test_filters_old_rejections(self, tmp_path: Path, monkeypatch):
        log_path = tmp_path / "r.jsonl"
        monkeypatch.setattr(_mod, "REJECTION_LOG", log_path)
        old = datetime.now() - timedelta(days=60)
        entry = {"todo_id": "old", "reason": "r", "category": "c",
                 "tags": [], "granularity": "medium",
                 "rejected_at": old.isoformat()}
        log_path.write_text(json.dumps(entry) + "\n", encoding="utf-8")
        result = _mod.load_rejections(days=30)
        assert result == []
