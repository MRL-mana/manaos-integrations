"""
Unit tests for scripts/misc/database_connection_pool.py
"""
import sys
import sqlite3
from unittest.mock import MagicMock

# ── external module mocks ──────────────────────────────────────────────────
_ml = MagicMock()
_ml.get_logger.return_value = MagicMock()
_ml.get_service_logger.return_value = MagicMock()
sys.modules.setdefault("manaos_logger", _ml)

_eh_mod = MagicMock()
_eh_class = MagicMock()
_eh_class.return_value = MagicMock()
_eh_mod.ManaOSErrorHandler = _eh_class
_eh_mod.ErrorCategory = MagicMock()
_eh_mod.ErrorSeverity = MagicMock()
sys.modules.setdefault("manaos_error_handler", _eh_mod)

import pytest  # noqa: E402
from scripts.misc.database_connection_pool import (  # noqa: E402
    DatabaseConnectionPool,
    get_pool,
)


# ── fixtures ────────────────────────────────────────────────────────────────
@pytest.fixture
def pool(tmp_path):
    """DatabaseConnectionPool backed by a real temp db file."""
    p = DatabaseConnectionPool(str(tmp_path / "test.db"), max_connections=5, timeout=0.1)
    yield p
    p.close_all()


@pytest.fixture
def mem_pool():
    """In-memory pool for fast tests."""
    # :memory: → parent directory is '.' which always exists
    p = DatabaseConnectionPool(":memory:", max_connections=5, timeout=0.1)
    yield p
    p.close_all()


# ── TestInit ───────────────────────────────────────────────────────────────
class TestInit:
    def test_max_connections_stored(self, pool):
        assert pool.max_connections == 5

    def test_stats_start_at_zero(self, pool):
        for v in pool.stats.values():
            assert v == 0

    def test_active_connections_zero(self, pool):
        assert pool.active_connections == 0


# ── TestCreateConnection ───────────────────────────────────────────────────
class TestCreateConnection:
    def test_returns_sqlite_connection(self, pool):
        conn = pool._create_connection()
        assert isinstance(conn, sqlite3.Connection)
        conn.close()

    def test_increments_created_stat(self, pool):
        initial = pool.stats["connections_created"]
        conn = pool._create_connection()
        assert pool.stats["connections_created"] == initial + 1
        conn.close()

    def test_wal_mode_set(self, pool):
        conn = pool._create_connection()
        result = conn.execute("PRAGMA journal_mode").fetchone()
        assert result[0] == "wal"
        conn.close()


# ── TestGetConnection ──────────────────────────────────────────────────────
class TestGetConnection:
    def test_context_manager_yields_connection(self, mem_pool):
        with mem_pool.get_connection() as conn:
            assert isinstance(conn, sqlite3.Connection)

    def test_connection_is_functional(self, mem_pool):
        with mem_pool.get_connection() as conn:
            result = conn.execute("SELECT 1").fetchone()
            assert result[0] == 1

    def test_connection_returned_to_pool(self, mem_pool):
        with mem_pool.get_connection():
            pass
        assert mem_pool.pool.qsize() == 1

    def test_multiple_contexts(self, mem_pool):
        for _ in range(3):
            with mem_pool.get_connection() as conn:
                conn.execute("SELECT 1")
        # All returned to pool
        assert mem_pool.pool.qsize() >= 1


# ── TestExecuteQuery ───────────────────────────────────────────────────────
class TestExecuteQuery:
    def test_create_table_and_insert(self, mem_pool):
        with mem_pool.get_connection() as conn:
            conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, val TEXT)")
            conn.commit()
        result = mem_pool.execute_query(
            "INSERT INTO t (val) VALUES (?)", ("hello",), fetch_all=False
        )
        assert result is not None  # rowcount

    def test_fetch_all(self, mem_pool):
        with mem_pool.get_connection() as conn:
            conn.execute("CREATE TABLE t2 (id INTEGER, val TEXT)")
            conn.execute("INSERT INTO t2 VALUES (1, 'a')")
            conn.execute("INSERT INTO t2 VALUES (2, 'b')")
            conn.commit()
        rows = mem_pool.execute_query("SELECT * FROM t2")
        assert len(rows) == 2

    def test_fetch_one(self, mem_pool):
        with mem_pool.get_connection() as conn:
            conn.execute("CREATE TABLE t3 (id INTEGER, val TEXT)")
            conn.execute("INSERT INTO t3 VALUES (1, 'x')")
            conn.commit()
        row = mem_pool.execute_query(
            "SELECT val FROM t3 WHERE id = ?", (1,), fetch_one=True
        )
        assert row == ("x",)

    def test_params_applied(self, mem_pool):
        with mem_pool.get_connection() as conn:
            conn.execute("CREATE TABLE t4 (id INTEGER, val TEXT)")
            conn.execute("INSERT INTO t4 VALUES (1, 'target')")
            conn.execute("INSERT INTO t4 VALUES (2, 'other')")
            conn.commit()
        rows = mem_pool.execute_query(
            "SELECT * FROM t4 WHERE id = ?", (1,)
        )
        assert len(rows) == 1
        assert rows[0][1] == "target"


# ── TestExecuteMany ────────────────────────────────────────────────────────
class TestExecuteMany:
    def test_inserts_multiple_rows(self, mem_pool):
        with mem_pool.get_connection() as conn:
            conn.execute("CREATE TABLE mt (id INTEGER, val TEXT)")
            conn.commit()
        mem_pool.execute_many(
            "INSERT INTO mt VALUES (?, ?)",
            [(1, "a"), (2, "b"), (3, "c")]
        )
        rows = mem_pool.execute_query("SELECT * FROM mt")
        assert len(rows) == 3


# ── TestCloseAll ───────────────────────────────────────────────────────────
class TestCloseAll:
    def test_clears_active_connections(self, mem_pool):
        with mem_pool.get_connection():
            pass
        mem_pool.close_all()
        assert mem_pool.active_connections == 0

    def test_pool_empty_after_close(self, mem_pool):
        with mem_pool.get_connection():
            pass
        mem_pool.close_all()
        assert mem_pool.pool.empty()


# ── TestGetStats ───────────────────────────────────────────────────────────
class TestGetStats:
    def test_returns_dict(self, mem_pool):
        assert isinstance(mem_pool.get_stats(), dict)

    def test_required_keys(self, mem_pool):
        stats = mem_pool.get_stats()
        for key in ("connections_created", "connections_reused",
                    "active_connections", "pool_size", "reuse_rate"):
            assert key in stats

    def test_reuse_rate_zero_initially(self, mem_pool):
        assert mem_pool.get_stats()["reuse_rate"] == 0.0

    def test_reuse_rate_updates(self, mem_pool):
        # First use → creates; second use → reuses from pool
        with mem_pool.get_connection():
            pass
        with mem_pool.get_connection():
            pass
        stats = mem_pool.get_stats()
        # pool_hits increments on second use
        assert stats["connections_reused"] >= 1


# ── TestGetPool ────────────────────────────────────────────────────────────
class TestGetPool:
    def test_returns_pool_instance(self, tmp_path):
        p = get_pool(str(tmp_path / "pool.db"))
        assert isinstance(p, DatabaseConnectionPool)
        p.close_all()

    def test_singleton_same_path(self, tmp_path):
        path = str(tmp_path / "singleton.db")
        p1 = get_pool(path)
        p2 = get_pool(path)
        assert p1 is p2
        p1.close_all()
