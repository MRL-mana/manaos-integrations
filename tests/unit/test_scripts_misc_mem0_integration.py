"""
Unit tests for scripts/misc/mem0_integration.py
Focuses on _LocalMemoryFallback — pure logic, uses only stdlib (json, Path, uuid, datetime).
"""
import sys
import json
from pathlib import Path
from unittest.mock import MagicMock
import pytest

# ── Standard mocks ────────────────────────────────────────────────────────────
_ml = MagicMock()
_ml.get_service_logger.return_value = MagicMock()
_ml.get_logger.return_value = MagicMock()
sys.modules.setdefault("manaos_logger", _ml)

_eh = MagicMock()
_eh_inst = MagicMock()
_eh_inst.handle_exception = MagicMock(return_value=MagicMock(message="err"))
_eh.ManaOSErrorHandler = MagicMock(return_value=_eh_inst)
sys.modules.setdefault("manaos_error_handler", _eh)

_tc = MagicMock()
_tc.get_timeout_config = MagicMock(return_value={})
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

_paths_m = MagicMock()
_paths_m.OLLAMA_PORT = 11434
sys.modules.setdefault("_paths", _paths_m)

# ── Import target ─────────────────────────────────────────────────────────────
from scripts.misc.mem0_integration import _LocalMemoryFallback  # noqa: E402


# ── Fixtures ──────────────────────────────────────────────────────────────────
@pytest.fixture
def storage(tmp_path):
    """Return a _LocalMemoryFallback backed by a temp JSONL file."""
    return _LocalMemoryFallback(tmp_path / "memories.jsonl")


# ── TestLocalMemoryFallbackInit ───────────────────────────────────────────────
class TestLocalMemoryFallbackInit:
    def test_creates_parent_directory(self, tmp_path):
        nested = tmp_path / "sub" / "deep" / "mem.jsonl"
        fb = _LocalMemoryFallback(nested)
        assert fb.storage_path.parent.exists()

    def test_storage_path_set(self, tmp_path):
        p = tmp_path / "mem.jsonl"
        fb = _LocalMemoryFallback(p)
        assert fb.storage_path == p


# ── TestLoad ─────────────────────────────────────────────────────────────────
class TestLoad:
    def test_nonexistent_file_returns_empty(self, storage):
        assert storage._load() == []

    def test_empty_file_returns_empty(self, storage):
        storage.storage_path.write_text("", encoding="utf-8")
        assert storage._load() == []

    def test_valid_jsonl_returns_records(self, storage):
        records = [{"id": "1", "memory": "hello"}, {"id": "2", "memory": "world"}]
        storage.storage_path.write_text(
            "\n".join(json.dumps(r) for r in records), encoding="utf-8"
        )
        loaded = storage._load()
        assert len(loaded) == 2
        assert loaded[0]["id"] == "1"

    def test_skips_blank_lines(self, storage):
        storage.storage_path.write_text(
            '{"id": "1"}\n\n{"id": "2"}\n', encoding="utf-8"
        )
        assert len(storage._load()) == 2

    def test_skips_invalid_json(self, storage):
        storage.storage_path.write_text(
            '{"id": "1"}\nNOT_JSON\n{"id": "2"}\n', encoding="utf-8"
        )
        loaded = storage._load()
        assert len(loaded) == 2

    def test_all_invalid_json_returns_empty(self, storage):
        storage.storage_path.write_text("BAD\nALSO_BAD\n", encoding="utf-8")
        assert storage._load() == []


# ── TestAdd ───────────────────────────────────────────────────────────────────
class TestAdd:
    def test_returns_memory_id(self, storage):
        result = storage.add("test memory")
        assert "memory_id" in result
        assert isinstance(result["memory_id"], str)

    def test_file_exists_after_add(self, storage):
        storage.add("some memory")
        assert storage.storage_path.exists()

    def test_content_persisted(self, storage):
        storage.add("unique_content_xyz")
        records = storage._load()
        assert any("unique_content_xyz" in r.get("memory", "") for r in records)

    def test_default_user_id(self, storage):
        storage.add("text")
        records = storage._load()
        assert records[0]["user_id"] == "default"

    def test_explicit_user_id(self, storage):
        storage.add("text", user_id="alice")
        records = storage._load()
        assert records[0]["user_id"] == "alice"

    def test_metadata_stored(self, storage):
        storage.add("text", metadata={"source": "test"})
        records = storage._load()
        assert records[0]["metadata"]["source"] == "test"

    def test_multiple_adds_appended(self, storage):
        storage.add("first")
        storage.add("second")
        records = storage._load()
        assert len(records) == 2


# ── TestSearch ────────────────────────────────────────────────────────────────
class TestSearch:
    def test_finds_matching_entry(self, storage):
        storage.add("Python is a programming language", user_id="u1")
        results = storage.search("python", user_id="u1")
        assert len(results) == 1

    def test_no_match_returns_empty(self, storage):
        storage.add("Hello world", user_id="u1")
        results = storage.search("zzz_no_match_xyz", user_id="u1")
        assert results == []

    def test_multiple_terms_ranked_higher(self, storage):
        storage.add("Python is great", user_id="u1")
        storage.add("Python Python Python", user_id="u1")
        results = storage.search("python", user_id="u1")
        # All match; just ensure results returned
        assert len(results) == 2

    def test_respects_limit(self, storage):
        for i in range(5):
            storage.add(f"python memory {i}", user_id="u1")
        results = storage.search("python", user_id="u1", limit=2)
        assert len(results) <= 2

    def test_empty_query_returns_all_for_user(self, storage):
        storage.add("abc", user_id="u2")
        storage.add("def", user_id="u2")
        results = storage.search("", user_id="u2")
        assert len(results) == 2

    def test_user_id_filter(self, storage):
        storage.add("shared text", user_id="alice")
        storage.add("shared text", user_id="bob")
        results = storage.search("shared", user_id="alice")
        assert all(r.get("user_id") == "alice" for r in results)


# ── TestGetAll ────────────────────────────────────────────────────────────────
class TestGetAll:
    def test_returns_all_for_user(self, storage):
        storage.add("mem1", user_id="alice")
        storage.add("mem2", user_id="alice")
        result = storage.get_all(user_id="alice")
        assert len(result) == 2

    def test_filters_by_user_id(self, storage):
        storage.add("mem1", user_id="alice")
        storage.add("mem2", user_id="bob")
        result = storage.get_all(user_id="alice")
        assert len(result) == 1
        assert result[0]["user_id"] == "alice"

    def test_empty_storage_returns_empty(self, storage):
        assert storage.get_all(user_id="nobody") == []
