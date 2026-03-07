"""
Unit tests for scripts/misc/cost_optimization.py
"""
import sys
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from pathlib import Path

# ── external module mocks ──────────────────────────────────────────────────
_ul = MagicMock()
_ul.get_service_logger.return_value = MagicMock()
sys.modules.setdefault("unified_logging", _ul)

import pytest
from scripts.misc.cost_optimization import CostOptimization


# ── Helpers ───────────────────────────────────────────────────────────────
def make_co(tmp_path):
    co = CostOptimization.__new__(CostOptimization)
    co.resource_costs = {
        "cpu_per_hour": 0.01,
        "memory_per_gb_hour": 0.005,
        "disk_per_gb_hour": 0.001,
        "network_per_gb": 0.01,
    }
    co.usage_history = []
    co.cost_history = []
    co.optimization_suggestions = []
    co.storage_path = tmp_path / "state.json"
    return co


def _make_cost_record(days_ago=0, cpu=0.1, memory=0.05, disk=0.02, network=0.01):
    ts = (datetime.now() - timedelta(days=days_ago)).isoformat()
    return {
        "timestamp": ts,
        "cpu_percent": 50.0,
        "memory_gb": 8.0,
        "disk_gb": 100.0,
        "network_gb": 10.0,
        "duration_hours": 1.0,
        "costs": {
            "cpu": cpu,
            "memory": memory,
            "disk": disk,
            "network": network,
            "total": cpu + memory + disk + network,
        },
    }


# ── calculate_resource_cost ───────────────────────────────────────────────
class TestCalculateResourceCost:
    def test_returns_dict(self, tmp_path):
        co = make_co(tmp_path)
        result = co.calculate_resource_cost(50.0, 4.0, 100.0, 1.0)
        assert isinstance(result, dict)

    def test_keys(self, tmp_path):
        co = make_co(tmp_path)
        result = co.calculate_resource_cost(50.0, 4.0, 100.0, 1.0)
        for key in ("cpu", "memory", "disk", "network", "total"):
            assert key in result

    def test_cpu_cost_proportional(self, tmp_path):
        co = make_co(tmp_path)
        r1 = co.calculate_resource_cost(50.0, 0.0, 0.0, 0.0)
        r2 = co.calculate_resource_cost(100.0, 0.0, 0.0, 0.0)
        assert r2["cpu"] == pytest.approx(r1["cpu"] * 2, rel=1e-6)

    def test_total_is_sum(self, tmp_path):
        co = make_co(tmp_path)
        result = co.calculate_resource_cost(50.0, 4.0, 100.0, 1.0)
        expected = result["cpu"] + result["memory"] + result["disk"] + result["network"]
        assert result["total"] == pytest.approx(expected, rel=1e-6)

    def test_hours_multiplier(self, tmp_path):
        co = make_co(tmp_path)
        r1 = co.calculate_resource_cost(50.0, 4.0, 100.0, 1.0, hours=1.0)
        r2 = co.calculate_resource_cost(50.0, 4.0, 100.0, 1.0, hours=2.0)
        assert r2["cpu"] == pytest.approx(r1["cpu"] * 2, rel=1e-6)

    def test_zero_inputs(self, tmp_path):
        co = make_co(tmp_path)
        result = co.calculate_resource_cost(0.0, 0.0, 0.0, 0.0)
        assert result["total"] == 0.0


# ── analyze_costs ─────────────────────────────────────────────────────────
class TestAnalyzeCosts:
    def test_returns_empty_if_no_history(self, tmp_path):
        co = make_co(tmp_path)
        assert co.analyze_costs(days=7) == {}

    def test_returns_dict_with_data(self, tmp_path):
        co = make_co(tmp_path)
        co.cost_history = [_make_cost_record(days_ago=0)]
        result = co.analyze_costs(days=7)
        assert isinstance(result, dict)

    def test_result_keys(self, tmp_path):
        co = make_co(tmp_path)
        co.cost_history = [_make_cost_record(days_ago=0)]
        result = co.analyze_costs(days=7)
        for key in ("period_days", "total_costs", "average_daily",
                    "max_cost_resource", "projected_monthly"):
            assert key in result

    def test_excludes_old_data(self, tmp_path):
        co = make_co(tmp_path)
        co.cost_history = [_make_cost_record(days_ago=30)]  # older than 7 days
        result = co.analyze_costs(days=7)
        assert result == {}

    def test_includes_recent_data(self, tmp_path):
        co = make_co(tmp_path)
        co.cost_history = [
            _make_cost_record(days_ago=0),
            _make_cost_record(days_ago=3),
        ]
        result = co.analyze_costs(days=7)
        assert result["total_costs"]["cpu"] > 0

    def test_max_cost_resource_cpu(self, tmp_path):
        co = make_co(tmp_path)
        # Make CPU cost dominant
        co.cost_history = [_make_cost_record(days_ago=0, cpu=1.0, memory=0.001,
                                             disk=0.001, network=0.001)]
        result = co.analyze_costs(days=7)
        assert result["max_cost_resource"] == "cpu"

    def test_projected_monthly(self, tmp_path):
        co = make_co(tmp_path)
        co.cost_history = [_make_cost_record(days_ago=0)]
        result = co.analyze_costs(days=7)
        assert result["projected_monthly"]["total"] == pytest.approx(
            result["average_daily"]["total"] * 30, rel=1e-6)


# ── record_usage ──────────────────────────────────────────────────────────
class TestRecordUsage:
    def test_returns_dict(self, tmp_path):
        co = make_co(tmp_path)
        with patch("scripts.misc.cost_optimization.psutil") as p:
            p.cpu_percent.return_value = 50.0
            p.virtual_memory.return_value = MagicMock(total=8 * 1024**3)
            p.disk_usage.return_value = MagicMock(used=100 * 1024**3)
            p.net_io_counters.return_value = MagicMock(bytes_sent=1024**3,
                                                        bytes_recv=1024**3)
            result = co.record_usage(duration_hours=1.0)
        assert isinstance(result, dict)

    def test_appends_to_history(self, tmp_path):
        co = make_co(tmp_path)
        with patch("scripts.misc.cost_optimization.psutil") as p:
            p.cpu_percent.return_value = 50.0
            p.virtual_memory.return_value = MagicMock(total=8 * 1024**3)
            p.disk_usage.return_value = MagicMock(used=100 * 1024**3)
            p.net_io_counters.return_value = MagicMock(bytes_sent=1024**3,
                                                        bytes_recv=1024**3)
            co.record_usage(duration_hours=1.0)
        assert len(co.usage_history) == 1
        assert len(co.cost_history) == 1

    def test_result_contains_costs(self, tmp_path):
        co = make_co(tmp_path)
        with patch("scripts.misc.cost_optimization.psutil") as p:
            p.cpu_percent.return_value = 50.0
            p.virtual_memory.return_value = MagicMock(total=8 * 1024**3)
            p.disk_usage.return_value = MagicMock(used=100 * 1024**3)
            p.net_io_counters.return_value = MagicMock(bytes_sent=1024**3,
                                                        bytes_recv=1024**3)
            result = co.record_usage(duration_hours=1.0)
        assert "costs" in result


# ── suggest_optimizations ─────────────────────────────────────────────────
class TestSuggestOptimizations:
    def test_empty_if_no_history(self, tmp_path):
        co = make_co(tmp_path)
        suggestions = co.suggest_optimizations()
        assert suggestions == []

    def test_returns_list_with_cpu_dominant(self, tmp_path):
        co = make_co(tmp_path)
        # Make CPU cost dominant: cpu=1.0, rest near 0
        co.cost_history = [_make_cost_record(
            days_ago=0, cpu=1.0, memory=0.001, disk=0.001, network=0.001)]
        suggestions = co.suggest_optimizations()
        types = [s["type"] for s in suggestions]
        assert "reduce_cpu" in types

    def test_suggestion_has_required_keys(self, tmp_path):
        co = make_co(tmp_path)
        co.cost_history = [_make_cost_record(
            days_ago=0, cpu=1.0, memory=0.001, disk=0.001, network=0.001)]
        suggestions = co.suggest_optimizations()
        if suggestions:
            s = suggestions[0]
            for key in ("type", "priority", "current_cost", "suggestion", "potential_savings"):
                assert key in s


# ── get_cost_summary ──────────────────────────────────────────────────────
class TestGetCostSummary:
    def test_returns_dict(self, tmp_path):
        co = make_co(tmp_path)
        result = co.get_cost_summary()
        assert isinstance(result, dict)

    def test_summary_keys(self, tmp_path):
        co = make_co(tmp_path)
        result = co.get_cost_summary()
        for key in ("current_analysis", "optimization_suggestions",
                    "total_suggested_savings", "timestamp"):
            assert key in result

    def test_savings_is_numeric(self, tmp_path):
        co = make_co(tmp_path)
        result = co.get_cost_summary()
        assert isinstance(result["total_suggested_savings"], (int, float))
