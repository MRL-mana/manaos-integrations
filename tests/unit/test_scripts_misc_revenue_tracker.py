"""
Unit tests for scripts/misc/revenue_tracker.py
"""
import sys
import json
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock

# ── mocks ─────────────────────────────────────────────────────────────────
_ml = MagicMock()
_ml.get_service_logger.return_value = MagicMock()
_ml.get_logger.return_value = MagicMock()
sys.modules.setdefault("manaos_logger", _ml)

_eh = MagicMock()
_eh_inst = MagicMock()
_eh_inst.handle_exception = MagicMock(return_value=MagicMock(message="err"))
_eh.ManaOSErrorHandler = MagicMock(return_value=_eh_inst)
_eh.ErrorCategory = MagicMock()
_eh.ErrorSeverity = MagicMock()
sys.modules.setdefault("manaos_error_handler", _eh)

_tc = MagicMock()
_tc.get_timeout_config = MagicMock(return_value={})
sys.modules.setdefault("manaos_timeout_config", _tc)

sys.modules.setdefault("flask_cors", MagicMock())

import pytest
import scripts.misc.revenue_tracker as rt


@pytest.fixture
def db(tmp_path, monkeypatch):
    """tmp_path の新鮮な SQLite DB に向け直す"""
    db_path = tmp_path / "rt_test.db"
    monkeypatch.setattr(rt, "DB_PATH", db_path)
    rt.init_db()
    return db_path


# ── TestInitDb ────────────────────────────────────────────────────────────
class TestInitDb:
    def test_creates_tables(self, db):
        conn = sqlite3.connect(db)
        tables = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        conn.close()
        assert "costs" in tables
        assert "revenue" in tables
        assert "products" in tables

    def test_idempotent(self, db, monkeypatch, tmp_path):
        # 2 回呼んでも壊れない
        monkeypatch.setattr(rt, "DB_PATH", db)
        rt.init_db()
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT count(*) FROM sqlite_master WHERE type='table'"
        ).fetchone()
        conn.close()
        assert row[0] >= 3


# ── TestAddCost ───────────────────────────────────────────────────────────
class TestAddCost:
    def test_inserts_record(self, db, monkeypatch):
        monkeypatch.setattr(rt, "DB_PATH", db)
        rt.add_cost("openai", "api", 100.0)
        conn = sqlite3.connect(db)
        rows = conn.execute("SELECT service_name, amount FROM costs").fetchall()
        conn.close()
        assert len(rows) == 1
        assert rows[0] == ("openai", 100.0)

    def test_default_currency_jpy(self, db, monkeypatch):
        monkeypatch.setattr(rt, "DB_PATH", db)
        rt.add_cost("aws", "storage", 50.0)
        conn = sqlite3.connect(db)
        row = conn.execute("SELECT currency FROM costs").fetchone()
        conn.close()
        assert row[0] == "JPY"

    def test_metadata_stored_as_json(self, db, monkeypatch):
        monkeypatch.setattr(rt, "DB_PATH", db)
        rt.add_cost("svc", "type", 1.0, metadata={"note": "test"})
        conn = sqlite3.connect(db)
        row = conn.execute("SELECT metadata FROM costs").fetchone()
        conn.close()
        meta = json.loads(row[0])
        assert meta["note"] == "test"

    def test_multiple_inserts(self, db, monkeypatch):
        monkeypatch.setattr(rt, "DB_PATH", db)
        rt.add_cost("s1", "t", 10.0)
        rt.add_cost("s2", "t", 20.0)
        conn = sqlite3.connect(db)
        count = conn.execute("SELECT count(*) FROM costs").fetchone()[0]
        conn.close()
        assert count == 2


# ── TestAddRevenue ────────────────────────────────────────────────────────
class TestAddRevenue:
    def test_inserts_record(self, db, monkeypatch):
        monkeypatch.setattr(rt, "DB_PATH", db)
        rt.add_revenue("p001", "image", 500.0)
        conn = sqlite3.connect(db)
        row = conn.execute("SELECT product_id, amount FROM revenue").fetchone()
        conn.close()
        assert row == ("p001", 500.0)

    def test_default_source(self, db, monkeypatch):
        monkeypatch.setattr(rt, "DB_PATH", db)
        rt.add_revenue(None, "video", 999.0)
        conn = sqlite3.connect(db)
        row = conn.execute("SELECT source FROM revenue").fetchone()
        conn.close()
        assert row[0] == "unknown"


# ── TestCreateProduct ─────────────────────────────────────────────────────
class TestCreateProduct:
    def test_inserts_product(self, db, monkeypatch):
        monkeypatch.setattr(rt, "DB_PATH", db)
        rt.create_product("prod1", "image", "Test Image")
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT product_id, product_type, title FROM products"
        ).fetchone()
        conn.close()
        assert row == ("prod1", "image", "Test Image")

    def test_status_defaults_to_draft(self, db, monkeypatch):
        monkeypatch.setattr(rt, "DB_PATH", db)
        rt.create_product("p2", "video", "Vid")
        conn = sqlite3.connect(db)
        row = conn.execute("SELECT status FROM products").fetchone()
        conn.close()
        assert row[0] == "draft"

    def test_upsert_replaces(self, db, monkeypatch):
        monkeypatch.setattr(rt, "DB_PATH", db)
        rt.create_product("dup", "a", "Title A")
        rt.create_product("dup", "a", "Title B")
        conn = sqlite3.connect(db)
        rows = conn.execute("SELECT title FROM products WHERE product_id='dup'").fetchall()
        conn.close()
        assert len(rows) == 1
        assert rows[0][0] == "Title B"


# ── TestGetStatistics ─────────────────────────────────────────────────────
class TestGetStatistics:
    def test_empty_db_returns_zeros(self, db, monkeypatch):
        monkeypatch.setattr(rt, "DB_PATH", db)
        stats = rt.get_statistics(days=30)
        assert stats["total_costs"] == 0.0
        assert stats["total_revenue"] == 0.0

    def test_costs_summed(self, db, monkeypatch):
        monkeypatch.setattr(rt, "DB_PATH", db)
        rt.add_cost("s", "t", 100.0)
        rt.add_cost("s", "t", 50.0)
        stats = rt.get_statistics()
        assert stats["total_costs"] == 150.0

    def test_revenue_summed(self, db, monkeypatch):
        monkeypatch.setattr(rt, "DB_PATH", db)
        rt.add_revenue(None, "x", 300.0)
        stats = rt.get_statistics()
        assert stats["total_revenue"] == 300.0

    def test_profit_calculated(self, db, monkeypatch):
        monkeypatch.setattr(rt, "DB_PATH", db)
        rt.add_cost("s", "t", 100.0)
        rt.add_revenue(None, "r", 400.0)
        stats = rt.get_statistics()
        assert stats["profit"] == 300.0
