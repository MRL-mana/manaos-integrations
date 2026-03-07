"""
Unit tests for scripts/misc/database_integration.py
"""
import sys
from unittest.mock import MagicMock, patch

import pytest
from scripts.misc.database_integration import (
    DatabaseIntegration,
    MongoDBIntegration,
    PostgreSQLIntegration,
)


# ── helper factories ───────────────────────────────────────────────────────
def _mock_psyco_conn():
    """Return a mock psycopg2 connection with cursor support."""
    mock_cursor = MagicMock()
    mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
    mock_cursor.__exit__ = MagicMock(return_value=False)
    mock_cursor.description = [("col1",)]
    mock_cursor.fetchall.return_value = [{"col1": "val1"}]

    conn = MagicMock()
    conn.cursor.return_value = mock_cursor
    conn.commit.return_value = None
    return conn, mock_cursor


# ── TestPostgreSQLIntegration ──────────────────────────────────────────────
class TestPostgreSQLIntegration:
    def test_is_available_when_connected(self):
        conn, _ = _mock_psyco_conn()
        with patch("psycopg2.connect", return_value=conn):
            pg = PostgreSQLIntegration("postgresql://localhost/test")
        assert pg.is_available() is True

    def test_is_not_available_when_connect_fails(self):
        with patch("psycopg2.connect", side_effect=Exception("conn fail")):
            pg = PostgreSQLIntegration("bad_conn_string")
        assert pg.is_available() is False

    def test_execute_query_returns_rows(self):
        conn, cursor = _mock_psyco_conn()
        cursor.description = [("id",), ("name",)]
        cursor.fetchall.return_value = [{"id": 1, "name": "Alice"}]
        with patch("psycopg2.connect", return_value=conn):
            pg = PostgreSQLIntegration("postgresql://localhost/test")
        result = pg.execute_query("SELECT * FROM users")
        assert isinstance(result, list)

    def test_execute_query_returns_empty_when_not_available(self):
        with patch("psycopg2.connect", side_effect=Exception("err")):
            pg = PostgreSQLIntegration("bad")
        result = pg.execute_query("SELECT 1")
        assert result == []

    def test_insert_data_returns_true_on_success(self):
        conn, cursor = _mock_psyco_conn()
        with patch("psycopg2.connect", return_value=conn):
            pg = PostgreSQLIntegration("postgresql://localhost/test")
        result = pg.insert_data("test_table", {"col1": "val1", "col2": 42})
        assert result is True

    def test_insert_data_returns_false_when_not_available(self):
        with patch("psycopg2.connect", side_effect=Exception("err")):
            pg = PostgreSQLIntegration("bad")
        assert pg.insert_data("t", {"a": 1}) is False


# ── TestMongoDBIntegration ─────────────────────────────────────────────────
class TestMongoDBIntegration:
    def _mock_client(self):
        mock_col = MagicMock()
        mock_col.insert_one.return_value = MagicMock(inserted_id="abc123")
        mock_col.find.return_value = iter([{"_id": "1", "val": "x"}])

        mock_db = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=mock_col)

        mock_client = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        return mock_client, mock_db, mock_col

    def test_is_available_when_connected(self):
        mock_client, mock_db, _ = self._mock_client()
        with patch("scripts.misc.database_integration.MongoClient", return_value=mock_client):
            mg = MongoDBIntegration("mongodb://localhost", "test_db")
        assert mg.is_available() is True

    def test_is_not_available_when_connect_fails(self):
        with patch("scripts.misc.database_integration.MongoClient", side_effect=Exception("conn fail")):
            mg = MongoDBIntegration("bad", "db")
        assert mg.is_available() is False

    def test_insert_document_returns_id(self):
        mock_client, mock_db, mock_col = self._mock_client()
        with patch("scripts.misc.database_integration.MongoClient", return_value=mock_client):
            mg = MongoDBIntegration("mongodb://localhost", "test_db")
        result = mg.insert_document("mycol", {"key": "value"})
        assert result is not None

    def test_insert_document_returns_none_when_unavailable(self):
        with patch("scripts.misc.database_integration.MongoClient", side_effect=Exception("err")):
            mg = MongoDBIntegration("bad", "db")
        assert mg.insert_document("col", {"k": "v"}) is None

    def test_find_documents_returns_empty_when_unavailable(self):
        with patch("scripts.misc.database_integration.MongoClient", side_effect=Exception("err")):
            mg = MongoDBIntegration("bad", "db")
        assert mg.find_documents("col") == []


# ── TestDatabaseIntegration ────────────────────────────────────────────────
class TestDatabaseIntegration:
    def test_init_no_connections(self):
        db = DatabaseIntegration()
        assert db.postgresql is None
        assert db.mongodb is None

    def test_status_both_unavailable(self):
        db = DatabaseIntegration()
        status = db.get_status()
        assert status["postgresql_available"] is False
        assert status["mongodb_available"] is False

    def test_configure_postgresql(self):
        db = DatabaseIntegration()
        conn, _ = _mock_psyco_conn()
        with patch("psycopg2.connect", return_value=conn):
            db.configure_postgresql("postgresql://localhost/test")
        assert db.postgresql is not None
        assert db.postgresql.is_available() is True

    def test_configure_mongodb(self):
        db = DatabaseIntegration()
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_db)
        with patch("scripts.misc.database_integration.MongoClient", return_value=mock_client):
            db.configure_mongodb("mongodb://localhost", "mydb")
        assert db.mongodb is not None

    def test_status_after_configure(self):
        db = DatabaseIntegration()
        conn, _ = _mock_psyco_conn()
        with patch("psycopg2.connect", return_value=conn):
            db.configure_postgresql("postgresql://localhost/test")
        status = db.get_status()
        assert status["postgresql_available"] is True
