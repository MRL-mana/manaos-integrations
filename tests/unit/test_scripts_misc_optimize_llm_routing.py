"""
Unit tests for scripts/misc/optimize_llm_routing.py
"""
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

import scripts.misc.optimize_llm_routing as opt


# Helper: create a performance log file
def _write_logs(path: Path, logs: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for log in logs:
            f.write(json.dumps(log) + "\n")


# ─────────────────────────────────────────────
# LLMRoutingOptimizer._load_logs
# ─────────────────────────────────────────────

class TestLoadLogs:
    def test_empty_when_no_file(self, tmp_path):
        with patch.object(opt, "PERFORMANCE_LOG_FILE", tmp_path / "nonexistent.jsonl"):
            o = opt.LLMRoutingOptimizer()
        assert o.performance_logs == []

    def test_loads_valid_jsonl(self, tmp_path):
        log_file = tmp_path / "perf.jsonl"
        _write_logs(log_file, [
            {"model": "qwen2.5", "response_time_ms": 500, "success": True},
            {"model": "llama3", "response_time_ms": 800, "success": False},
        ])
        with patch.object(opt, "PERFORMANCE_LOG_FILE", log_file):
            o = opt.LLMRoutingOptimizer()
        assert len(o.performance_logs) == 2
        assert o.performance_logs[0]["model"] == "qwen2.5"

    def test_skips_invalid_lines(self, tmp_path):
        log_file = tmp_path / "perf.jsonl"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with open(log_file, "w") as f:
            f.write('{"model": "good"}\n')
            f.write("not json\n")
            f.write('{"model": "also good"}\n')
        with patch.object(opt, "PERFORMANCE_LOG_FILE", log_file):
            o = opt.LLMRoutingOptimizer()
        assert len(o.performance_logs) == 2


# ─────────────────────────────────────────────
# analyze_performance
# ─────────────────────────────────────────────

class TestAnalyzePerformance:
    def test_returns_no_data_when_empty(self, tmp_path):
        with patch.object(opt, "PERFORMANCE_LOG_FILE", tmp_path / "x.jsonl"):
            o = opt.LLMRoutingOptimizer()
        result = o.analyze_performance()
        assert result["status"] == "no_data"

    def test_returns_ok_with_logs(self, tmp_path):
        log_file = tmp_path / "perf.jsonl"
        _write_logs(log_file, [
            {"model": "qwen2.5", "response_time_ms": 300, "success": True},
            {"model": "qwen2.5", "response_time_ms": 500, "success": True},
        ])
        with patch.object(opt, "PERFORMANCE_LOG_FILE", log_file):
            o = opt.LLMRoutingOptimizer()
        result = o.analyze_performance()
        assert result["status"] == "ok"
        assert "qwen2.5" in result["model_analysis"]

    def test_computes_mean_response_time(self, tmp_path):
        log_file = tmp_path / "perf.jsonl"
        _write_logs(log_file, [
            {"model": "m1", "response_time_ms": 100, "success": True},
            {"model": "m1", "response_time_ms": 300, "success": True},
        ])
        with patch.object(opt, "PERFORMANCE_LOG_FILE", log_file):
            o = opt.LLMRoutingOptimizer()
        result = o.analyze_performance()
        assert result["model_analysis"]["m1"]["mean_response_time"] == 200.0

    def test_computes_success_rate(self, tmp_path):
        log_file = tmp_path / "perf.jsonl"
        _write_logs(log_file, [
            {"model": "m1", "response_time_ms": 100, "success": True},
            {"model": "m1", "response_time_ms": 100, "success": False},
        ])
        with patch.object(opt, "PERFORMANCE_LOG_FILE", log_file):
            o = opt.LLMRoutingOptimizer()
        result = o.analyze_performance()
        assert result["model_analysis"]["m1"]["success_rate"] == 50.0

    def test_total_logs_count(self, tmp_path):
        log_file = tmp_path / "perf.jsonl"
        _write_logs(log_file, [
            {"model": "a", "response_time_ms": 1, "success": True},
            {"model": "b", "response_time_ms": 2, "success": True},
            {"model": "a", "response_time_ms": 3, "success": False},
        ])
        with patch.object(opt, "PERFORMANCE_LOG_FILE", log_file):
            o = opt.LLMRoutingOptimizer()
        result = o.analyze_performance()
        assert result["total_logs"] == 3


# ─────────────────────────────────────────────
# generate_recommendations
# ─────────────────────────────────────────────

class TestGenerateRecommendations:
    def test_returns_empty_when_no_data(self, tmp_path):
        with patch.object(opt, "PERFORMANCE_LOG_FILE", tmp_path / "x.jsonl"):
            o = opt.LLMRoutingOptimizer()
        recs = o.generate_recommendations()
        assert recs == []

    def test_recommends_fastest_model(self, tmp_path):
        log_file = tmp_path / "perf.jsonl"
        _write_logs(log_file, [
            {"model": "fast", "response_time_ms": 100, "success": True},
            {"model": "slow", "response_time_ms": 1000, "success": True},
        ])
        with patch.object(opt, "PERFORMANCE_LOG_FILE", log_file):
            o = opt.LLMRoutingOptimizer()
        recs = o.generate_recommendations()
        speed_recs = [r for r in recs if r["type"] == "speed_optimization"]
        assert len(speed_recs) == 1
        assert speed_recs[0]["details"]["model"] == "fast"

    def test_warns_on_low_success_rate(self, tmp_path):
        log_file = tmp_path / "perf.jsonl"
        # 10 requests, only 3 success → 30% < 80%
        logs = [{"model": "unreliable", "response_time_ms": 100, "success": i < 3}
                for i in range(10)]
        _write_logs(log_file, logs)
        with patch.object(opt, "PERFORMANCE_LOG_FILE", log_file):
            o = opt.LLMRoutingOptimizer()
        recs = o.generate_recommendations()
        rel_recs = [r for r in recs if r["type"] == "reliability_warning"]
        assert len(rel_recs) == 1
        assert rel_recs[0]["details"]["model"] == "unreliable"

    def test_no_reliability_warning_below_10_requests(self, tmp_path):
        """10件未満なら信頼性警告なし"""
        log_file = tmp_path / "perf.jsonl"
        logs = [{"model": "rare", "response_time_ms": 100, "success": False}
                for _ in range(5)]
        _write_logs(log_file, logs)
        with patch.object(opt, "PERFORMANCE_LOG_FILE", log_file):
            o = opt.LLMRoutingOptimizer()
        recs = o.generate_recommendations()
        rel_recs = [r for r in recs if r["type"] == "reliability_warning"]
        assert len(rel_recs) == 0

    def test_warns_on_slow_response_time(self, tmp_path):
        """平均5000ms超 + 10件以上 → パフォーマンス警告"""
        log_file = tmp_path / "perf.jsonl"
        logs = [{"model": "sluggish", "response_time_ms": 6000, "success": True}
                for _ in range(10)]
        _write_logs(log_file, logs)
        with patch.object(opt, "PERFORMANCE_LOG_FILE", log_file):
            o = opt.LLMRoutingOptimizer()
        recs = o.generate_recommendations()
        perf_recs = [r for r in recs if r["type"] == "performance_warning"]
        assert len(perf_recs) == 1
        assert perf_recs[0]["details"]["model"] == "sluggish"

    def test_recommendation_has_required_fields(self, tmp_path):
        log_file = tmp_path / "perf.jsonl"
        _write_logs(log_file, [{"model": "m", "response_time_ms": 100, "success": True}])
        with patch.object(opt, "PERFORMANCE_LOG_FILE", log_file):
            o = opt.LLMRoutingOptimizer()
        recs = o.generate_recommendations()
        for rec in recs:
            assert "type" in rec
            assert "priority" in rec
            assert "title" in rec
            assert "description" in rec
