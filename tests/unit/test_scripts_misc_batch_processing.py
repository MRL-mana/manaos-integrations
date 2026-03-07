"""
Unit tests for scripts/misc/batch_processing.py
"""
import sys
import json
from pathlib import Path
from collections import defaultdict
import pytest

sys.path.insert(0, "scripts/misc")
from batch_processing import BatchProcessor


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_bp(tmp_path: Path) -> BatchProcessor:
    """Create a BatchProcessor bypassing __init__ disk I/O."""
    bp = BatchProcessor.__new__(BatchProcessor)
    bp.max_workers = 2
    bp.batch_history = []
    bp.storage_path = tmp_path / "batch_state.json"
    return bp


# ── BatchProcessor.process_batch ─────────────────────────────────────────────

class TestProcessBatch:
    def test_processes_all_items(self, tmp_path):
        bp = make_bp(tmp_path)
        data = [1, 2, 3, 4, 5]
        result = bp.process_batch(data, lambda x: x * 2)
        assert sorted(result["results"]) == [2, 4, 6, 8, 10]

    def test_returns_results_and_summary(self, tmp_path):
        bp = make_bp(tmp_path)
        result = bp.process_batch([1], lambda x: x)
        assert "results" in result
        assert "summary" in result

    def test_summary_has_required_keys(self, tmp_path):
        bp = make_bp(tmp_path)
        result = bp.process_batch(["a"], lambda x: x)
        summary = result["summary"]
        for key in ("batch_id", "total_items", "processed_items", "failed_items",
                    "duration_seconds", "start_time", "end_time"):
            assert key in summary

    def test_total_items_in_summary(self, tmp_path):
        bp = make_bp(tmp_path)
        data = list(range(7))
        result = bp.process_batch(data, lambda x: x)
        assert result["summary"]["total_items"] == 7

    def test_processed_items_in_summary(self, tmp_path):
        bp = make_bp(tmp_path)
        data = list(range(4))
        result = bp.process_batch(data, lambda x: x)
        assert result["summary"]["processed_items"] == 4

    def test_with_batch_size(self, tmp_path):
        bp = make_bp(tmp_path)
        data = list(range(6))
        result = bp.process_batch(data, lambda x: x * 3, batch_size=2)
        assert len(result["results"]) == 6

    def test_records_history_entry(self, tmp_path):
        bp = make_bp(tmp_path)
        bp.process_batch([1, 2], lambda x: x)
        assert len(bp.batch_history) == 1

    def test_empty_data(self, tmp_path):
        bp = make_bp(tmp_path)
        result = bp.process_batch([], lambda x: x)
        assert result["results"] == []
        assert result["summary"]["total_items"] == 0

    def test_failing_processor_captured_in_result(self, tmp_path):
        bp = make_bp(tmp_path)

        def bad_processor(x):
            raise ValueError("boom")

        result = bp.process_batch([1, 2], bad_processor)
        # Items that fail are still returned with error keys
        for r in result["results"]:
            assert "error" in r

    def test_saves_state_file(self, tmp_path):
        bp = make_bp(tmp_path)
        bp.process_batch([1], lambda x: x)
        assert bp.storage_path.exists()

    def test_state_file_is_valid_json(self, tmp_path):
        bp = make_bp(tmp_path)
        bp.process_batch([1], lambda x: x)
        with open(bp.storage_path, encoding="utf-8") as f:
            state = json.load(f)
        assert "history" in state


# ── BatchProcessor._process_batch_thread ────────────────────────────────────

class TestProcessBatchThread:
    def test_processes_items_sequentially(self, tmp_path):
        bp = make_bp(tmp_path)
        results = bp._process_batch_thread([1, 2, 3], lambda x: x + 10)
        assert results == [11, 12, 13]

    def test_exception_captured_as_dict(self, tmp_path):
        bp = make_bp(tmp_path)

        def boom(x):
            raise RuntimeError("fail")

        results = bp._process_batch_thread([1], boom)
        assert len(results) == 1
        assert "error" in results[0]

    def test_mixed_success_and_failure(self, tmp_path):
        bp = make_bp(tmp_path)

        def maybe_fail(x):
            if x == 2:
                raise ValueError("nope")
            return x * 10

        results = bp._process_batch_thread([1, 2, 3], maybe_fail)
        assert results[0] == 10
        assert "error" in results[1]
        assert results[2] == 30


# ── BatchProcessor._process_batch_multiprocess ──────────────────────────────

class TestProcessBatchMultiprocess:
    def test_processes_items(self, tmp_path):
        bp = make_bp(tmp_path)
        results = bp._process_batch_multiprocess([5, 6], lambda x: x * 2)
        assert results == [10, 12]

    def test_exception_captured(self, tmp_path):
        bp = make_bp(tmp_path)

        def err(x):
            raise TypeError("oops")

        results = bp._process_batch_multiprocess([1], err)
        assert "error" in results[0]


# ── BatchProcessor.process_image_batch ───────────────────────────────────────

class TestProcessImageBatch:
    def test_delegates_to_process_batch(self, tmp_path):
        bp = make_bp(tmp_path)
        paths = ["img1.png", "img2.png"]
        result = bp.process_image_batch(paths, lambda p, **kw: p.upper())
        assert sorted(result["results"]) == ["IMG1.PNG", "IMG2.PNG"]


# ── BatchProcessor.process_text_batch ────────────────────────────────────────

class TestProcessTextBatch:
    def test_processes_texts(self, tmp_path):
        bp = make_bp(tmp_path)
        texts = ["hello", "world"]
        result = bp.process_text_batch(texts, lambda t, **kw: t.upper())
        assert sorted(result["results"]) == ["HELLO", "WORLD"]

    def test_extra_kwargs_forwarded(self, tmp_path):
        bp = make_bp(tmp_path)

        def repeat(text, times=1):
            return text * times

        result = bp.process_text_batch(["x"], repeat, times=3)
        assert result["results"] == ["xxx"]


# ── BatchProcessor.get_batch_history ─────────────────────────────────────────

class TestGetBatchHistory:
    def test_empty_history(self, tmp_path):
        bp = make_bp(tmp_path)
        assert bp.get_batch_history() == []

    def test_returns_limited_entries(self, tmp_path):
        bp = make_bp(tmp_path)
        bp.batch_history = [{"id": i} for i in range(20)]
        result = bp.get_batch_history(limit=5)
        assert len(result) == 5

    def test_returns_most_recent_entries(self, tmp_path):
        bp = make_bp(tmp_path)
        bp.batch_history = [{"id": i} for i in range(10)]
        result = bp.get_batch_history(limit=3)
        assert result[-1] == {"id": 9}

    def test_default_limit_ten(self, tmp_path):
        bp = make_bp(tmp_path)
        bp.batch_history = [{"id": i} for i in range(15)]
        result = bp.get_batch_history()
        assert len(result) == 10


# ── BatchProcessor._load_state / _save_state ─────────────────────────────────

class TestLoadSaveState:
    def test_save_then_load_preserves_history(self, tmp_path):
        bp = make_bp(tmp_path)
        bp.batch_history = [{"batch_id": "b1", "total_items": 5}]
        bp._save_state()

        bp2 = make_bp(tmp_path)
        bp2._load_state()
        assert len(bp2.batch_history) == 1
        assert bp2.batch_history[0]["batch_id"] == "b1"

    def test_load_state_missing_file_is_empty(self, tmp_path):
        bp = make_bp(tmp_path)
        bp._load_state()  # file does not exist
        assert bp.batch_history == []

    def test_load_state_corrupt_file_is_empty(self, tmp_path):
        bp = make_bp(tmp_path)
        bp.storage_path.write_text("not json")
        bp._load_state()
        assert bp.batch_history == []
