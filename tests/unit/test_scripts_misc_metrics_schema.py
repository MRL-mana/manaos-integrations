"""
Unit tests for scripts/misc/metrics_schema.py

Pure-function tests: validate_metrics, normalize_score/todo/system,
read/write JSONL/JSON (using tmp_path).
"""
import sys
import json
import pytest
from pathlib import Path
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts" / "misc"))
from metrics_schema import (
    METRICS_SCHEMA,
    validate_metrics,
    normalize_score_metrics,
    normalize_todo_metrics,
    normalize_system_metrics,
    write_jsonl_metrics,
    read_jsonl_metrics,
    write_json_metrics,
    read_json_metrics,
)


# ---------------------------------------------------------------------------
# validate_metrics
# ---------------------------------------------------------------------------

class TestValidateMetrics:
    def test_valid_score_data(self):
        data = {
            "score_today": 7.5,
            "score_7d_avg": 7.0,
            "score_trend": "↑",
            "score_history": [{"date": "2024-01-01", "score": 7.0}],
        }
        assert validate_metrics(data, "score") is True

    def test_unknown_schema_type_returns_false(self):
        assert validate_metrics({}, "no_such_type") is False

    def test_valid_todo_data(self):
        data = {
            "proposed": 10,
            "approved": 8,
            "executed": 7,
            "expired": 2,
            "approval_rate": 0.8,
            "execution_rate": 0.875,
            "noise_index": 0.2,
        }
        assert validate_metrics(data, "todo") is True

    def test_valid_system_data(self):
        data = {
            "timestamp": "2024-01-01T00:00:00",
            "services_running": 5,
            "services_total": 8,
        }
        assert validate_metrics(data, "system") is True

    def test_wrong_type_for_float_field_returns_false(self):
        data = {"score_today": "not_a_float"}  # should be float
        assert validate_metrics(data, "score") is False

    def test_missing_field_is_ok(self):
        # Fields are optional in the validator
        assert validate_metrics({}, "score") is True

    def test_score_trend_must_be_str(self):
        data = {"score_trend": 123}  # should be str
        assert validate_metrics(data, "score") is False

    def test_history_list_must_be_list(self):
        data = {"score_history": "not_a_list"}
        assert validate_metrics(data, "score") is False

    def test_optional_int_can_be_none(self):
        data = {"uptime_seconds": None}
        assert validate_metrics(data, "system") is True

    def test_optional_int_valid_int(self):
        data = {"uptime_seconds": 3600}
        assert validate_metrics(data, "system") is True

    def test_optional_int_wrong_type_returns_false(self):
        data = {"uptime_seconds": "text"}
        assert validate_metrics(data, "system") is False


# ---------------------------------------------------------------------------
# normalize_score_metrics
# ---------------------------------------------------------------------------

class TestNormalizeScoreMetrics:
    def test_basic_returns_expected_keys(self):
        result = normalize_score_metrics(7.5)
        assert "score_today" in result
        assert "score_7d_avg" in result
        assert "score_trend" in result
        assert "score_history" in result

    def test_score_today_converted_to_float(self):
        result = normalize_score_metrics(8)
        assert result["score_today"] == 8.0
        assert isinstance(result["score_today"], float)

    def test_score_7d_avg_none_by_default(self):
        result = normalize_score_metrics(7.5)
        assert result["score_7d_avg"] is None

    def test_score_7d_avg_provided(self):
        result = normalize_score_metrics(7.5, score_7d_avg=7.0)
        assert result["score_7d_avg"] == 7.0

    def test_default_trend_is_right_arrow(self):
        result = normalize_score_metrics(5.0)
        assert result["score_trend"] == "→"

    def test_custom_trend_stored(self):
        result = normalize_score_metrics(5.0, score_trend="↑")
        assert result["score_trend"] == "↑"

    def test_empty_history_default(self):
        result = normalize_score_metrics(5.0)
        assert result["score_history"] == []

    def test_provided_history_stored(self):
        history = [{"date": "2024-01-01", "score": 7.0}]
        result = normalize_score_metrics(7.5, score_history=history)
        assert result["score_history"] == history


# ---------------------------------------------------------------------------
# normalize_todo_metrics
# ---------------------------------------------------------------------------

class TestNormalizeTodoMetrics:
    def test_all_fields_present(self):
        result = normalize_todo_metrics(10, 8, 7, 2)
        expected_keys = {"proposed", "approved", "executed", "expired",
                         "approval_rate", "execution_rate", "noise_index"}
        assert expected_keys.issubset(result.keys())

    def test_approval_rate_calculated(self):
        result = normalize_todo_metrics(10, 8, 7, 2)
        assert abs(result["approval_rate"] - 0.8) < 1e-9

    def test_execution_rate_calculated(self):
        result = normalize_todo_metrics(10, 8, 8, 2)
        assert result["execution_rate"] == 1.0

    def test_noise_index_calculated(self):
        result = normalize_todo_metrics(10, 8, 7, 2)
        assert abs(result["noise_index"] - 0.2) < 1e-9

    def test_zero_proposed_approval_rate_is_none(self):
        result = normalize_todo_metrics(0, 0, 0, 0)
        assert result["approval_rate"] is None
        assert result["noise_index"] is None

    def test_zero_approved_execution_rate_is_none(self):
        result = normalize_todo_metrics(5, 0, 0, 5)
        assert result["execution_rate"] is None

    def test_counts_are_int(self):
        result = normalize_todo_metrics(10, 8, 7, 2)
        assert isinstance(result["proposed"], int)
        assert isinstance(result["approved"], int)

    def test_100_percent_approval(self):
        result = normalize_todo_metrics(5, 5, 5, 0)
        assert result["approval_rate"] == 1.0
        assert result["noise_index"] == 0.0


# ---------------------------------------------------------------------------
# normalize_system_metrics
# ---------------------------------------------------------------------------

class TestNormalizeSystemMetrics:
    def test_basic_structure(self):
        result = normalize_system_metrics(5, 8)
        assert result["services_running"] == 5
        assert result["services_total"] == 8
        assert "timestamp" in result

    def test_uptime_none_by_default(self):
        result = normalize_system_metrics(5, 8)
        assert result["uptime_seconds"] is None

    def test_uptime_provided(self):
        result = normalize_system_metrics(5, 8, uptime_seconds=3600)
        assert result["uptime_seconds"] == 3600

    def test_services_are_int(self):
        result = normalize_system_metrics(5, 8)
        assert isinstance(result["services_running"], int)
        assert isinstance(result["services_total"], int)


# ---------------------------------------------------------------------------
# write_jsonl_metrics / read_jsonl_metrics
# ---------------------------------------------------------------------------

class TestJsonlMetrics:
    def test_write_and_read_roundtrip(self, tmp_path):
        path = tmp_path / "metrics.jsonl"
        data = {
            "score_today": 8.0,
            "score_7d_avg": 7.5,
            "score_trend": "↑",
            "score_history": [],
        }
        write_jsonl_metrics(path, "score", data)
        results = read_jsonl_metrics(path)
        assert len(results) == 1
        assert results[0]["type"] == "score"
        assert results[0]["data"]["score_today"] == 8.0

    def test_write_invalid_data_raises(self, tmp_path):
        path = tmp_path / "metrics.jsonl"
        bad_data = {"score_today": "not_a_float"}  # wrong type
        with pytest.raises(ValueError):
            write_jsonl_metrics(path, "score", bad_data)

    def test_filter_by_type(self, tmp_path):
        path = tmp_path / "metrics.jsonl"
        score_data = {"score_today": 7.0, "score_7d_avg": 7.0, "score_trend": "→", "score_history": []}
        todo_data = {"proposed": 5, "approved": 4, "executed": 3, "expired": 1,
                     "approval_rate": 0.8, "execution_rate": 0.75, "noise_index": 0.2}
        write_jsonl_metrics(path, "score", score_data)
        write_jsonl_metrics(path, "todo", todo_data)
        score_results = read_jsonl_metrics(path, metrics_type="score")
        todo_results = read_jsonl_metrics(path, metrics_type="todo")
        assert len(score_results) == 1
        assert len(todo_results) == 1

    def test_limit_results(self, tmp_path):
        path = tmp_path / "metrics.jsonl"
        for i in range(5):
            data = {"score_today": float(i), "score_7d_avg": float(i), "score_trend": "→", "score_history": []}
            write_jsonl_metrics(path, "score", data)
        results = read_jsonl_metrics(path, limit=2)
        assert len(results) == 2

    def test_read_nonexistent_returns_empty(self, tmp_path):
        path = tmp_path / "nonexistent.jsonl"
        assert read_jsonl_metrics(path) == []

    def test_each_entry_has_timestamp(self, tmp_path):
        path = tmp_path / "metrics.jsonl"
        data = {"score_today": 7.0, "score_7d_avg": 7.0, "score_trend": "→", "score_history": []}
        write_jsonl_metrics(path, "score", data)
        results = read_jsonl_metrics(path)
        assert "timestamp" in results[0]


# ---------------------------------------------------------------------------
# write_json_metrics / read_json_metrics
# ---------------------------------------------------------------------------

class TestJsonMetrics:
    def test_write_and_read_roundtrip(self, tmp_path):
        path = tmp_path / "metrics.json"
        data = {"score": 8.5, "level": "A"}
        write_json_metrics(path, data)
        result = read_json_metrics(path)
        assert result == data

    def test_nonexistent_returns_none(self, tmp_path):
        path = tmp_path / "no_file.json"
        assert read_json_metrics(path) is None

    def test_overwrite_existing(self, tmp_path):
        path = tmp_path / "metrics.json"
        write_json_metrics(path, {"v": 1})
        write_json_metrics(path, {"v": 2})
        result = read_json_metrics(path)
        assert result["v"] == 2

    def test_creates_parent_dirs(self, tmp_path):
        path = tmp_path / "nested" / "dir" / "metrics.json"
        write_json_metrics(path, {"ok": True})
        assert path.exists()
