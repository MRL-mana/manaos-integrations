"""
Unit tests for scripts/misc/http_session_pool.py
"""
import sys
from datetime import datetime, timedelta
from unittest.mock import MagicMock

# ── external module mocks ──────────────────────────────────────────────────
_ml = MagicMock()
_ml.get_logger.return_value = MagicMock()
_ml.get_service_logger.return_value = MagicMock()
sys.modules.setdefault("manaos_logger", _ml)

_eh_mod = MagicMock()
_eh_mod.ManaOSErrorHandler = MagicMock(return_value=MagicMock())
_eh_mod.ErrorCategory = MagicMock()
_eh_mod.ErrorSeverity = MagicMock()
sys.modules.setdefault("manaos_error_handler", _eh_mod)

_tc_mod = MagicMock()
_tc_mod.get_timeout_config = MagicMock(return_value={"api_call": 10.0})
sys.modules.setdefault("manaos_timeout_config", _tc_mod)

import pytest  # noqa: E402
import requests  # noqa: E402
from scripts.misc.http_session_pool import (  # noqa: E402
    HTTPSessionPool,
    get_http_session_pool,
)


# ── fixtures ────────────────────────────────────────────────────────────────
@pytest.fixture
def pool():
    """Fresh HTTPSessionPool."""
    p = HTTPSessionPool(max_sessions=5)
    yield p
    p.close_all()


# ── TestInit ───────────────────────────────────────────────────────────────
class TestInit:
    def test_max_sessions_stored(self, pool):
        assert pool.max_sessions == 5

    def test_sessions_empty(self, pool):
        assert pool.sessions == {}

    def test_stats_start_at_zero(self, pool):
        for v in pool.stats.values():
            assert v == 0


# ── TestGenerateSessionKey ─────────────────────────────────────────────────
class TestGenerateSessionKey:
    def test_basic_key(self, pool):
        key = pool._generate_session_key("http://example.com")
        assert "http://example.com" in key

    def test_same_url_same_key(self, pool):
        k1 = pool._generate_session_key("http://example.com")
        k2 = pool._generate_session_key("http://example.com")
        assert k1 == k2

    def test_different_url_different_key(self, pool):
        k1 = pool._generate_session_key("http://a.com")
        k2 = pool._generate_session_key("http://b.com")
        assert k1 != k2

    def test_headers_affect_key(self, pool):
        k1 = pool._generate_session_key("http://a.com")
        k2 = pool._generate_session_key("http://a.com", headers={"X-Key": "val"})
        assert k1 != k2

    def test_auth_affects_key(self, pool):
        k1 = pool._generate_session_key("http://a.com")
        k2 = pool._generate_session_key("http://a.com", auth=("user", "pass"))
        assert k1 != k2


# ── TestGetSession ─────────────────────────────────────────────────────────
class TestGetSession:
    def test_returns_requests_session(self, pool):
        session = pool.get_session("http://example.com")
        assert isinstance(session, requests.Session)
        session.close()

    def test_creates_session_first_time(self, pool):
        pool.get_session("http://example.com")
        assert pool.stats["sessions_created"] == 1

    def test_reuses_existing_session(self, pool):
        pool.get_session("http://example.com")
        pool.get_session("http://example.com")
        assert pool.stats["sessions_created"] == 1
        assert pool.stats["sessions_reused"] == 1

    def test_different_urls_different_sessions(self, pool):
        pool.get_session("http://a.com")
        pool.get_session("http://b.com")
        assert pool.stats["sessions_created"] == 2

    def test_default_headers_set(self, pool):
        session = pool.get_session("http://example.com")
        assert "User-Agent" in session.headers

    def test_custom_headers_applied(self, pool):
        session = pool.get_session(
            "http://example.com",
            headers={"X-Custom": "value"}
        )
        assert session.headers.get("X-Custom") == "value"

    def test_auth_applied(self, pool):
        session = pool.get_session(
            "http://example.com",
            auth=("user", "pass")
        )
        assert session.auth == ("user", "pass")

    def test_session_stored_in_pool(self, pool):
        pool.get_session("http://example.com")
        assert len(pool.sessions) == 1

    def test_expires_old_session(self, pool):
        pool.get_session("http://example.com")
        key = list(pool.session_metadata.keys())[0]
        # Manually set last_used to 31 minutes ago
        old_time = (datetime.now() - timedelta(minutes=31)).isoformat()
        pool.session_metadata[key]["last_used"] = old_time

        # Should create a new session
        pool.get_session("http://example.com")
        assert pool.stats["sessions_created"] == 2

    def test_max_sessions_evicts_oldest(self, pool):
        # Fill up all 5 slots
        for i in range(5):
            pool.get_session(f"http://host{i}.com")
        assert len(pool.sessions) == 5
        # One more should evict oldest
        pool.get_session("http://new.com")
        assert len(pool.sessions) == 5


# ── TestCloseAll ───────────────────────────────────────────────────────────
class TestCloseAll:
    def test_clears_sessions(self, pool):
        pool.get_session("http://a.com")
        pool.close_all()
        assert pool.sessions == {}

    def test_clears_metadata(self, pool):
        pool.get_session("http://a.com")
        pool.close_all()
        assert pool.session_metadata == {}


# ── TestGetStats ───────────────────────────────────────────────────────────
class TestGetStats:
    def test_returns_dict(self, pool):
        assert isinstance(pool.get_stats(), dict)

    def test_required_keys(self, pool):
        stats = pool.get_stats()
        for key in ("sessions_created", "sessions_reused",
                    "requests_made", "active_sessions", "reuse_rate"):
            assert key in stats

    def test_reuse_rate_zero_initially(self, pool):
        stats = pool.get_stats()
        assert stats["reuse_rate"] == 0.0

    def test_reuse_rate_calculated(self, pool):
        pool.get_session("http://example.com")  # create
        pool.get_session("http://example.com")  # reuse
        stats = pool.get_stats()
        assert stats["reuse_rate"] > 0

    def test_active_sessions_count(self, pool):
        pool.get_session("http://a.com")
        pool.get_session("http://b.com")
        stats = pool.get_stats()
        assert stats["active_sessions"] == 2


# ── TestGetHttpSessionPool ─────────────────────────────────────────────────
class TestGetHttpSessionPool:
    def test_returns_instance(self):
        p = get_http_session_pool()
        assert isinstance(p, HTTPSessionPool)

    def test_singleton_behavior(self):
        p1 = get_http_session_pool()
        p2 = get_http_session_pool()
        assert p1 is p2
