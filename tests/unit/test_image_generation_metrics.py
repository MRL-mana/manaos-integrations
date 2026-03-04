"""
Unit Tests — image_generation_service.metrics
===============================================
Counter/Gauge/Histogram の単体テスト。外部依存ゼロ。
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from image_generation_service.metrics import (
    _Counter,
    _Gauge,
    _Histogram,
    record_generation,
    record_api_request,
    update_queue_depth,
    export_prometheus,
    export_json,
    generations_total,
    api_requests_total,
    gpu_cost_yen_total,
    queue_depth,
    generation_duration,
    quality_score,
)


# ─── _Counter ────────────────────────────────────────

class TestCounter:

    def test_inc_default(self):
        c = _Counter()
        c.inc("ok")
        assert c.get("ok") == 1

    def test_inc_by_value(self):
        c = _Counter()
        c.inc("ok", value=5)
        assert c.get("ok") == 5

    def test_inc_multiple_labels(self):
        c = _Counter()
        c.inc("GET", "/health", "200")
        c.inc("POST", "/generate", "201")
        c.inc("GET", "/health", "200")
        assert c.get("GET", "/health", "200") == 2
        assert c.get("POST", "/generate", "201") == 1

    def test_get_missing_label(self):
        c = _Counter()
        assert c.get("nonexistent") == 0

    def test_items(self):
        c = _Counter()
        c.inc("a")
        c.inc("b", value=3)
        items = c.items()
        assert isinstance(items, list)
        assert len(items) == 2


# ─── _Gauge ──────────────────────────────────────────

class TestGauge:

    def test_set_and_get(self):
        g = _Gauge()
        g.set("queue", value=5.0)
        assert g.get("queue") == 5.0

    def test_inc(self):
        g = _Gauge()
        g.set("active", value=0)
        g.inc("active", value=1)
        assert g.get("active") == 1.0
        g.inc("active", value=-1)
        assert g.get("active") == 0.0

    def test_items(self):
        g = _Gauge()
        g.set("a", value=1)
        g.set("b", value=2)
        items = g.items()
        assert len(items) == 2


# ─── _Histogram ──────────────────────────────────────

class TestHistogram:

    def test_observe(self):
        h = _Histogram(buckets=[1, 5, 10])
        h.observe(0.5, "test")
        h.observe(3, "test")
        h.observe(7, "test")
        h.observe(15, "test")

        items = h.items()
        assert len(items) == 1

        labels, data = items[0]
        assert labels == ("test",)
        assert data["count"] == 4
        assert data["sum"] == pytest.approx(25.5)

        # バケット検証: [1, 5, 10, inf]
        # observe は cumulative: value <= bucket なら全バケットをインクリメント
        buckets = data["buckets"]
        assert len(buckets) == 4  # 3 + inf
        # 0.5 <= 1: count=1
        assert buckets[0] == (1, 1)
        # 0.5 + 3 <= 5: count=2
        assert buckets[1] == (5, 2)
        # 0.5 + 3 + 7 <= 10: count=3
        assert buckets[2] == (10, 3)
        # all <= inf: count=4
        assert buckets[3] == (float("inf"), 4)

    def test_multiple_labels(self):
        h = _Histogram(buckets=[5, 10])
        h.observe(3, "success")
        h.observe(7, "failure")

        items = h.items()
        assert len(items) == 2

    def test_empty_histogram(self):
        h = _Histogram(buckets=[1, 5, 10])
        items = h.items()
        assert items == []


# ─── Record Helpers ──────────────────────────────────

class TestRecordHelpers:

    def test_record_generation(self):
        """record_generation が例外なく動く"""
        record_generation(
            status="test_success",
            duration_seconds=5.0,
            quality_overall=7.5,
            cost_yen=0.05,
        )
        assert generations_total.get("test_success") >= 1

    def test_record_api_request(self):
        record_api_request("GET", "/test", 200)
        assert api_requests_total.get("GET", "/test", "200") >= 1

    def test_update_queue_depth(self):
        update_queue_depth(42)
        assert queue_depth.get() == 42.0


# ─── Export ──────────────────────────────────────────

class TestExport:

    def test_prometheus_format(self):
        """Prometheus テキストフォーマットが出力される"""
        text = export_prometheus()
        assert isinstance(text, str)
        assert "manaos_uptime_seconds" in text
        assert "# HELP" in text
        assert "# TYPE" in text
        assert "manaos_image_generations_total" in text
        assert "manaos_queue_depth" in text

    def test_json_format(self):
        """JSON エクスポートが正しい構造"""
        data = export_json()
        assert isinstance(data, dict)
        assert "uptime_seconds" in data
        assert "generations" in data
        assert "api_requests_total" in data
        assert "gpu_cost_yen_total" in data
        assert "queue_depth" in data
        assert "timestamp" in data

        # generations の構造
        gen = data["generations"]
        assert "total" in gen
        assert "success" in gen
        assert "failed" in gen
        assert "success_rate" in gen


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
