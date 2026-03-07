"""
Unit tests for scripts/misc/searxng_integration.py
"""
import sys
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

# ── mocks: base_integration 依存チェーン ──────────────────────────────────
_ml = MagicMock()
_ml.get_logger.return_value = MagicMock()
_ml.get_service_logger.return_value = MagicMock()
sys.modules.setdefault("manaos_logger", _ml)

_eh = MagicMock()
_eh_inst = MagicMock()
_eh_inst.handle_exception = MagicMock(return_value=MagicMock(message="err"))
_eh.ManaOSErrorHandler = MagicMock(return_value=_eh_inst)
_eh.ErrorCategory = MagicMock()
_eh.ErrorSeverity = MagicMock()
sys.modules.setdefault("manaos_error_handler", _eh)

_tc = MagicMock()
_tc.get_timeout_config = MagicMock(return_value={"api_call": 30})
sys.modules.setdefault("manaos_timeout_config", _tc)

_cv = MagicMock()
_cv_inst = MagicMock()
_cv_inst.validate_config = MagicMock(return_value=(True, []))
_cv.ConfigValidator = MagicMock(return_value=_cv_inst)
sys.modules.setdefault("manaos_config_validator", _cv)

_cve = MagicMock()
_cve_inst = MagicMock()
_cve_inst.validate_config_file = MagicMock(return_value=(True, [], {}))
_cve.ConfigValidatorEnhanced = MagicMock(return_value=_cve_inst)
sys.modules.setdefault("config_validator_enhanced", _cve)

_paths = MagicMock()
_paths.SEARXNG_PORT = 8080
sys.modules.setdefault("_paths", _paths)
sys.modules.setdefault("manaos_integrations._paths", _paths)

import pytest
from scripts.misc.searxng_integration import SearXNGIntegration


@pytest.fixture
def sx(tmp_path):
    """キャッシュ専用インスタンス（httpx.Client は作らない）"""
    with patch("scripts.misc.searxng_integration.httpx"):
        inst = SearXNGIntegration(
            base_url="http://127.0.0.1:8080",
            cache_dir=str(tmp_path / "cache"),
            cache_ttl=3600,
            enable_cache=True,
        )
    return inst


# ── TestGetCacheKey ───────────────────────────────────────────────────────
class TestGetCacheKey:
    def test_returns_md5_hex(self, sx):
        key = sx._get_cache_key("テスト")
        assert len(key) == 32
        assert all(c in "0123456789abcdef" for c in key)

    def test_consistent(self, sx):
        assert sx._get_cache_key("hello") == sx._get_cache_key("hello")

    def test_different_queries(self, sx):
        assert sx._get_cache_key("foo") != sx._get_cache_key("bar")

    def test_kwargs_affect_key(self, sx):
        k1 = sx._get_cache_key("q", language="ja")
        k2 = sx._get_cache_key("q", language="en")
        assert k1 != k2

    def test_case_insensitive_query(self, sx):
        assert sx._get_cache_key("HELLO") == sx._get_cache_key("hello")


# ── TestGetCachePath ──────────────────────────────────────────────────────
class TestGetCachePath:
    def test_returns_path_object(self, sx, tmp_path):
        p = sx._get_cache_path("abc123")
        assert isinstance(p, Path)

    def test_filename_ends_with_json(self, sx):
        p = sx._get_cache_path("mykey")
        assert p.name == "mykey.json"

    def test_inside_cache_dir(self, sx, tmp_path):
        p = sx._get_cache_path("xyz")
        assert sx.cache_dir in p.parents


# ── TestLoadCache ─────────────────────────────────────────────────────────
class TestLoadCache:
    def test_returns_none_when_disabled(self, sx):
        sx.enable_cache = False
        assert sx._load_cache("any") is None

    def test_returns_none_when_file_missing(self, sx):
        assert sx._load_cache("nosuchkey") is None

    def test_returns_data_for_valid_cache(self, sx):
        cache_data = {
            "timestamp": datetime.now().isoformat(),
            "results": {"query": "test", "items": []}
        }
        key = "validkey"
        path = sx._get_cache_path(key)
        path.write_text(json.dumps(cache_data), encoding="utf-8")
        result = sx._load_cache(key)
        assert result == {"query": "test", "items": []}

    def test_expired_cache_returns_none(self, sx):
        old_time = (datetime.now() - timedelta(hours=2)).isoformat()
        cache_data = {"timestamp": old_time, "results": {"old": True}}
        key = "expiredkey"
        sx._get_cache_path(key).write_text(
            json.dumps(cache_data), encoding="utf-8"
        )
        assert sx._load_cache(key) is None

    def test_expired_cache_deletes_file(self, sx):
        old_time = (datetime.now() - timedelta(hours=2)).isoformat()
        key = "todeletekey"
        p = sx._get_cache_path(key)
        p.write_text(json.dumps({"timestamp": old_time, "results": {}}))
        sx._load_cache(key)
        assert not p.exists()


# ── TestSaveCache ─────────────────────────────────────────────────────────
class TestSaveCache:
    def test_creates_file(self, sx):
        sx._save_cache("savekey", {"answer": 42})
        p = sx._get_cache_path("savekey")
        assert p.exists()

    def test_file_contents_valid_json(self, sx):
        sx._save_cache("jsonkey", {"x": [1, 2, 3]})
        p = sx._get_cache_path("jsonkey")
        data = json.loads(p.read_text(encoding="utf-8"))
        assert data["results"] == {"x": [1, 2, 3]}
        assert "timestamp" in data

    def test_no_file_when_disabled(self, sx):
        sx.enable_cache = False
        sx._save_cache("noop", {"should": "not save"})
        assert not sx._get_cache_path("noop").exists()


# ── TestIsAvailable ───────────────────────────────────────────────────────
class TestIsAvailable:
    def test_returns_bool(self, sx):
        result = sx.is_available()
        assert isinstance(result, bool)
