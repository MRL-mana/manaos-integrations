"""
tests/unit/test_scripts_misc_load_test.py
Load Test Tool のユニットテスト
"""

import sys
import json
import asyncio
import time
import statistics
from unittest.mock import MagicMock, patch, AsyncMock
from dataclasses import asdict
import pytest

# ── optional/external imports のモック ──────────────────────────
sys.modules.setdefault("aiohttp", MagicMock())
sys.modules.setdefault("matplotlib", MagicMock())
sys.modules.setdefault("matplotlib.pyplot", MagicMock())
sys.modules.setdefault("_paths", MagicMock(
    UNIFIED_API_URL="http://127.0.0.1:9502",
    MRL_MEMORY_URL="http://127.0.0.1:9507",
    LEARNING_SYSTEM_URL="http://127.0.0.1:9508",
))

# ── モジュールをインポート ──────────────────────────────────────────
import scripts.misc.load_test as _sut
from scripts.misc.load_test import (
    LoadTestResult,
    LoadTestStats,
    LoadTester,
    LoadTestRunner,
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  TestLoadTestResult
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestLoadTestResult:
    def test_init_fields(self):
        r = LoadTestResult(
            timestamp=1.0, response_time=0.123,
            status_code=200, success=True
        )
        assert r.timestamp == 1.0
        assert r.response_time == 0.123
        assert r.status_code == 200
        assert r.success is True
        assert r.error is None

    def test_with_error(self):
        r = LoadTestResult(
            timestamp=1.0, response_time=10.0,
            status_code=0, success=False, error="Timeout"
        )
        assert r.error == "Timeout"
        assert r.success is False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  TestLoadTestStats
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestLoadTestStats:
    def test_init_with_defaults(self):
        s = LoadTestStats(
            total_requests=100,
            successful_requests=95,
            failed_requests=5,
            success_rate=95.0,
            avg_response_time=0.1,
            min_response_time=0.05,
            max_response_time=0.5,
            p50_response_time=0.1,
            p95_response_time=0.3,
            p99_response_time=0.45,
            requests_per_second=50.0,
            total_duration=2.0,
        )
        assert s.total_requests == 100
        assert s.success_rate == 95.0
        assert s.errors == {}

    def test_asdict_works(self):
        s = LoadTestStats(
            total_requests=1, successful_requests=1, failed_requests=0,
            success_rate=100.0, avg_response_time=0.1,
            min_response_time=0.1, max_response_time=0.1,
            p50_response_time=0.1, p95_response_time=0.1,
            p99_response_time=0.1, requests_per_second=1.0,
            total_duration=1.0,
        )
        d = asdict(s)
        assert isinstance(d, dict)
        assert d["total_requests"] == 1


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  TestLoadTesterCalculateStatistics
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestLoadTesterCalculateStatistics:
    def _make_results(self, n_success: int, n_fail: int, base_time: float = 1.0) -> list:
        results = []
        t = base_time
        for i in range(n_success):
            results.append(LoadTestResult(timestamp=t + i * 0.01, response_time=0.1 + i * 0.001, status_code=200, success=True))
        for i in range(n_fail):
            results.append(LoadTestResult(timestamp=t + (n_success + i) * 0.01, response_time=10.0, status_code=0, success=False, error="Timeout"))
        return results

    def test_empty_results_returns_zero_stats(self):
        tester = LoadTester("http://localhost", "/health")
        stats = tester.calculate_statistics([])
        assert stats.total_requests == 0
        assert stats.success_rate == 0

    def test_all_success_stats(self):
        tester = LoadTester("http://localhost", "/health")
        results = self._make_results(10, 0)
        stats = tester.calculate_statistics(results)
        assert stats.total_requests == 10
        assert stats.successful_requests == 10
        assert stats.failed_requests == 0
        assert stats.success_rate == 100.0

    def test_mixed_results(self):
        tester = LoadTester("http://localhost", "/health")
        results = self._make_results(8, 2)
        stats = tester.calculate_statistics(results)
        assert stats.total_requests == 10
        assert stats.successful_requests == 8
        assert stats.failed_requests == 2
        assert stats.success_rate == 80.0
        assert "Timeout" in stats.errors

    def test_percentile_calculation(self):
        tester = LoadTester("http://localhost", "/health")
        # 100件のresults（0.01〜1.00の応答時間）
        results = [
            LoadTestResult(timestamp=float(i), response_time=float(i + 1) / 100.0, status_code=200, success=True)
            for i in range(100)
        ]
        stats = tester.calculate_statistics(results)
        assert stats.p50_response_time <= stats.p95_response_time
        assert stats.p95_response_time <= stats.p99_response_time
        assert stats.p99_response_time <= stats.max_response_time

    def test_rps_calculation(self):
        tester = LoadTester("http://localhost", "/health")
        # 10件、0〜0.9秒に分布（duration ≈ 0.9s → RPS ≈ 11.1）
        results = [
            LoadTestResult(timestamp=float(i) * 0.1, response_time=0.01, status_code=200, success=True)
            for i in range(10)
        ]
        stats = tester.calculate_statistics(results)
        assert stats.requests_per_second > 0
        assert stats.total_duration > 0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  TestLoadTesterInit
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestLoadTesterInit:
    def test_default_endpoint(self):
        tester = LoadTester("http://localhost:9502")
        assert tester.base_url == "http://localhost:9502"
        assert tester.endpoint == "/health"
        assert tester.results == []

    def test_custom_endpoint(self):
        tester = LoadTester("http://localhost:9502", "/api/status")
        assert tester.endpoint == "/api/status"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  TestLoadTestRunnerInit
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestLoadTestRunnerInit:
    def test_services_initialized(self):
        runner = LoadTestRunner()
        assert "Unified API" in runner.services
        assert "MRL Memory" in runner.services
        assert "Learning System" in runner.services

    def test_all_results_empty_initially(self):
        runner = LoadTestRunner()
        assert runner.all_results == {}

    def test_service_urls_set(self):
        with patch.object(_sut, "UNIFIED_API_URL", "http://127.0.0.1:9502"), \
             patch.object(_sut, "MRL_MEMORY_URL", "http://127.0.0.1:9507"):
            runner = LoadTestRunner()
        assert "http" in runner.services["Unified API"]
        assert "http" in runner.services["MRL Memory"]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  TestLoadTestRunnerReport
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TestLoadTestRunnerReport:
    def _make_runner_with_results(self):
        runner = LoadTestRunner()
        runner.all_results["Unified API - Burst"] = LoadTestStats(
            total_requests=100, successful_requests=95, failed_requests=5,
            success_rate=95.0, avg_response_time=0.1,
            min_response_time=0.05, max_response_time=0.5,
            p50_response_time=0.1, p95_response_time=0.3,
            p99_response_time=0.45, requests_per_second=50.0,
            total_duration=2.0, errors={"Timeout": 3, "HTTP 500": 2},
        )
        return runner

    def test_generate_report_runs_without_error(self, capsys):
        runner = self._make_runner_with_results()
        runner.generate_report()
        captured = capsys.readouterr()
        assert "Unified API" in captured.out

    def test_save_report_creates_json_file(self, tmp_path):
        runner = self._make_runner_with_results()
        output_file = str(tmp_path / "report.json")
        runner.save_report(filename=output_file)
        import os
        assert os.path.exists(output_file)
        with open(output_file, "r") as f:
            data = json.load(f)
        assert "timestamp" in data
        assert "results" in data
        assert "Unified API - Burst" in data["results"]

    def test_save_report_auto_filename(self, tmp_path):
        """ファイル名省略時のテスト（カレントディレクトリに作成される可能性があるため一時変更）"""
        import os
        original_dir = os.getcwd()
        os.chdir(str(tmp_path))
        try:
            runner = self._make_runner_with_results()
            runner.save_report()
            # tmpパスにJSONファイルが作成されていることを確認
            json_files = list(tmp_path.glob("load_test_report_*.json"))
            assert len(json_files) > 0
        finally:
            os.chdir(original_dir)
