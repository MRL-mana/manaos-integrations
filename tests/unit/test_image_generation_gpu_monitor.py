"""
Unit Tests — image_generation_service.gpu_monitor
===================================================
GPUStatus + GPUMonitor のユニットテスト。nvidia-smi 不要のモック。
"""

import os
import sys
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from image_generation_service.gpu_monitor import GPUStatus, GPUMonitor


class TestGPUStatus:
    """GPUStatus プロパティテスト"""

    def test_memory_utilization(self):
        s = GPUStatus(memory_used_mb=4000, memory_total_mb=16000, memory_free_mb=12000)
        assert s.memory_utilization_pct == 25.0

    def test_memory_utilization_zero_total(self):
        s = GPUStatus(memory_total_mb=0)
        assert s.memory_utilization_pct == 0

    def test_is_idle(self):
        s = GPUStatus(gpu_utilization_pct=5)
        assert s.is_idle is True
        s2 = GPUStatus(gpu_utilization_pct=50)
        assert s2.is_idle is False

    def test_is_overheating(self):
        s = GPUStatus(temperature_c=95)
        assert s.is_overheating is True
        s2 = GPUStatus(temperature_c=70)
        assert s2.is_overheating is False

    def test_is_warm(self):
        s = GPUStatus(temperature_c=85)
        assert s.is_warm is True
        s2 = GPUStatus(temperature_c=60)
        assert s2.is_warm is False

    def test_has_enough_vram(self):
        s = GPUStatus(memory_free_mb=4096)
        assert s.has_enough_vram is True
        s2 = GPUStatus(memory_free_mb=512)
        assert s2.has_enough_vram is False

    def test_can_accept_job_normal(self):
        s = GPUStatus(memory_free_mb=4096, temperature_c=60)
        assert s.can_accept_job is True

    def test_can_accept_job_overheating(self):
        s = GPUStatus(memory_free_mb=4096, temperature_c=95)
        assert s.can_accept_job is False

    def test_can_accept_job_low_vram(self):
        s = GPUStatus(memory_free_mb=512, temperature_c=60)
        assert s.can_accept_job is False


class TestGPUMonitor:
    """GPUMonitor テスト（nvidia-smi をモック）"""

    def _mock_status(self, **kwargs):
        defaults = dict(
            gpu_index=0, name="RTX 5080", temperature_c=65,
            gpu_utilization_pct=30, memory_used_mb=4000,
            memory_total_mb=16000, memory_free_mb=12000,
            fan_speed_pct=40, power_draw_w=200, power_limit_w=350,
        )
        defaults.update(kwargs)
        return GPUStatus(**defaults)  # type: ignore

    @patch("image_generation_service.gpu_monitor._query_nvidia_smi")
    def test_poll_stores_history(self, mock_smi):
        mock_smi.return_value = self._mock_status()
        m = GPUMonitor(history_size=10)
        m.poll()
        m.poll()
        assert len(m._history) == 2

    @patch("image_generation_service.gpu_monitor._query_nvidia_smi")
    def test_history_size_limit(self, mock_smi):
        mock_smi.return_value = self._mock_status()
        m = GPUMonitor(history_size=3)
        for _ in range(5):
            m.poll()
        assert len(m._history) == 3

    @patch("image_generation_service.gpu_monitor._query_nvidia_smi")
    def test_current_returns_latest(self, mock_smi):
        mock_smi.return_value = self._mock_status(temperature_c=70)
        m = GPUMonitor()
        m.poll()
        assert m.current.temperature_c == 70  # type: ignore[union-attr]

    @patch("image_generation_service.gpu_monitor._query_nvidia_smi")
    def test_can_accept_job_delegates(self, mock_smi):
        mock_smi.return_value = self._mock_status(temperature_c=60, memory_free_mb=8000)
        m = GPUMonitor()
        assert m.can_accept_job() is True

    @patch("image_generation_service.gpu_monitor._query_nvidia_smi")
    def test_get_summary(self, mock_smi):
        mock_smi.return_value = self._mock_status(name="RTX 5080")
        m = GPUMonitor()
        m.poll()
        summary = m.get_summary()
        assert summary["available"] is True
        assert summary["gpu_name"] == "RTX 5080"
        assert "temperature_c" in summary
        assert "can_accept_job" in summary

    @patch("image_generation_service.gpu_monitor._query_nvidia_smi")
    def test_get_summary_no_gpu(self, mock_smi):
        mock_smi.return_value = None
        m = GPUMonitor()
        summary = m.get_summary()
        assert summary["available"] is False

    @patch("image_generation_service.gpu_monitor._query_nvidia_smi")
    def test_history_stats(self, mock_smi):
        m = GPUMonitor()
        for temp in [60, 70, 80]:
            mock_smi.return_value = self._mock_status(temperature_c=temp, gpu_utilization_pct=temp)
            m.poll()
        stats = m.get_history_stats()
        assert stats["data_points"] == 3
        assert stats["temperature"]["avg"] == 70.0
        assert stats["temperature"]["max"] == 80
        assert stats["temperature"]["min"] == 60

    @patch("image_generation_service.gpu_monitor._query_nvidia_smi")
    def test_history_stats_empty(self, mock_smi):
        m = GPUMonitor()
        stats = m.get_history_stats()
        assert stats["data_points"] == 0
