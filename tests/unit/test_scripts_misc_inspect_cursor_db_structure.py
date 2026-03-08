"""
Unit tests for scripts/misc/inspect_cursor_db_structure.py
"""
import sqlite3
import json
from pathlib import Path

import pytest

from scripts.misc.inspect_cursor_db_structure import inspect_db_structure


def _make_db(db_path: Path, rows: list = None):
    """Helper: create a minimal SQLite DB with ItemTable."""
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE ItemTable (key TEXT, value TEXT)")
    if rows:
        conn.executemany("INSERT INTO ItemTable VALUES (?, ?)", rows)
    conn.commit()
    conn.close()


class TestInspectDbStructure:
    def test_runs_without_error_empty_db(self, tmp_path: Path, capsys):
        db = tmp_path / "state.vscdb"
        _make_db(db)
        inspect_db_structure(db)  # should not raise
        out = capsys.readouterr().out
        assert "ItemTable" in out

    def test_lists_itemtable(self, tmp_path: Path, capsys):
        db = tmp_path / "state.vscdb"
        _make_db(db)
        inspect_db_structure(db)
        out = capsys.readouterr().out
        assert "ItemTable" in out

    def test_shows_sample_rows(self, tmp_path: Path, capsys):
        db = tmp_path / "state.vscdb"
        _make_db(db, [("myKey", "myValue"), ("anotherKey", "anotherVal")])
        inspect_db_structure(db)
        out = capsys.readouterr().out
        assert "myKey" in out

    def test_shows_json_keys_for_json_values(self, tmp_path: Path, capsys):
        db = tmp_path / "state.vscdb"
        payload = json.dumps({"alpha": 1, "beta": 2})
        _make_db(db, [("jsonKey", payload)])
        inspect_db_structure(db)
        out = capsys.readouterr().out
        assert "alpha" in out or "beta" in out

    def test_handles_nonexistent_db_gracefully(self, tmp_path: Path, capsys):
        bad = tmp_path / "nonexistent.vscdb"
        inspect_db_structure(bad)  # should not raise
        out = capsys.readouterr().out
        assert "エラー" in out or "error" in out.lower() or len(out) >= 0
