"""
GPU Monitor — GPU 使用率モニタリング & 自動スケジュール
========================================================
NVIDIA GPU の使用状況を監視し、ジョブキューの自動制御に活用。

機能:
  - VRAM / GPU Utilization / Temperature のリアルタイム取得
  - GPU 空き判定 → キューワーカーの自動制御
  - 過熱保護 (温度閾値でジョブ一時停止)
  - メトリクス履歴保持 (直近100件)
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

_log = logging.getLogger("manaos.gpu_monitor")

# 閾値設定
GPU_TEMP_WARN = int(os.getenv("GPU_TEMP_WARN", "80"))   # ℃
GPU_TEMP_CRITICAL = int(os.getenv("GPU_TEMP_CRITICAL", "90"))  # ℃
GPU_UTIL_IDLE_THRESHOLD = int(os.getenv("GPU_UTIL_IDLE", "20"))  # %
GPU_VRAM_FREE_MIN_MB = int(os.getenv("GPU_VRAM_FREE_MIN", "2048"))  # MB


@dataclass
class GPUStatus:
    """GPU ステータスのスナップショット"""
    gpu_index: int = 0
    name: str = "Unknown"
    temperature_c: int = 0
    gpu_utilization_pct: int = 0
    memory_used_mb: int = 0
    memory_total_mb: int = 0
    memory_free_mb: int = 0
    fan_speed_pct: int = 0
    power_draw_w: float = 0
    power_limit_w: float = 0
    timestamp: float = field(default_factory=time.time)

    @property
    def memory_utilization_pct(self) -> float:
        if self.memory_total_mb == 0:
            return 0
        return round(self.memory_used_mb / self.memory_total_mb * 100, 1)

    @property
    def is_idle(self) -> bool:
        return self.gpu_utilization_pct < GPU_UTIL_IDLE_THRESHOLD

    @property
    def is_overheating(self) -> bool:
        return self.temperature_c >= GPU_TEMP_CRITICAL

    @property
    def is_warm(self) -> bool:
        return self.temperature_c >= GPU_TEMP_WARN

    @property
    def has_enough_vram(self) -> bool:
        return self.memory_free_mb >= GPU_VRAM_FREE_MIN_MB

    @property
    def can_accept_job(self) -> bool:
        """ジョブ受付可能か判定"""
        return self.has_enough_vram and not self.is_overheating


def _query_nvidia_smi() -> Optional[GPUStatus]:
    """nvidia-smi から GPU ステータスを取得"""
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=index,name,temperature.gpu,utilization.gpu,"
                "memory.used,memory.total,memory.free,"
                "fan.speed,power.draw,power.limit",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            _log.warning("nvidia-smi failed: %s", result.stderr.strip())
            return None

        line = result.stdout.strip().split("\n")[0]
        parts = [p.strip() for p in line.split(",")]

        if len(parts) < 10:
            _log.warning("nvidia-smi unexpected output: %s", line)
            return None

        return GPUStatus(
            gpu_index=int(parts[0]),
            name=parts[1],
            temperature_c=int(parts[2]),
            gpu_utilization_pct=int(parts[3]),
            memory_used_mb=int(parts[4]),
            memory_total_mb=int(parts[5]),
            memory_free_mb=int(parts[6]),
            fan_speed_pct=int(parts[7]) if parts[7] != "[N/A]" else 0,
            power_draw_w=float(parts[8]) if parts[8] != "[N/A]" else 0,
            power_limit_w=float(parts[9]) if parts[9] != "[N/A]" else 0,
        )
    except FileNotFoundError:
        _log.warning("nvidia-smi not found (no NVIDIA GPU?)")
        return None
    except Exception as e:
        _log.warning("GPU query failed: %s", e)
        return None


class GPUMonitor:
    """GPU 使用率モニター"""

    def __init__(self, history_size: int = 100):
        self._history: List[GPUStatus] = []
        self._max_history = history_size
        self._last_status: Optional[GPUStatus] = None

    def poll(self) -> Optional[GPUStatus]:
        """GPU ステータスを取得して履歴に追加"""
        status = _query_nvidia_smi()
        if status:
            self._last_status = status
            self._history.append(status)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]

            # 温度警告
            if status.is_overheating:
                _log.error("🔥 GPU CRITICAL: %d°C — ジョブ停止推奨!", status.temperature_c)
            elif status.is_warm:
                _log.warning("⚠️ GPU WARM: %d°C", status.temperature_c)

        return status

    @property
    def current(self) -> Optional[GPUStatus]:
        """最新のステータス"""
        return self._last_status

    def can_accept_job(self) -> bool:
        """ジョブ受付可能か（最新ステータスで判定）"""
        status = self.poll()
        if status is None:
            return True  # GPU情報取得不可の場合は許可
        return status.can_accept_job

    def get_summary(self) -> Dict:
        """サマリー情報"""
        status = self._last_status
        if not status:
            status = self.poll()
        if not status:
            return {"available": False, "reason": "nvidia-smi unavailable"}

        return {
            "available": True,
            "gpu_name": status.name,
            "temperature_c": status.temperature_c,
            "gpu_utilization_pct": status.gpu_utilization_pct,
            "memory_used_mb": status.memory_used_mb,
            "memory_total_mb": status.memory_total_mb,
            "memory_free_mb": status.memory_free_mb,
            "memory_utilization_pct": status.memory_utilization_pct,
            "power_draw_w": status.power_draw_w,
            "is_idle": status.is_idle,
            "is_overheating": status.is_overheating,
            "can_accept_job": status.can_accept_job,
        }

    def get_history_stats(self) -> Dict:
        """履歴統計"""
        if not self._history:
            return {"data_points": 0}

        temps = [s.temperature_c for s in self._history]
        utils = [s.gpu_utilization_pct for s in self._history]
        vrams = [s.memory_utilization_pct for s in self._history]

        return {
            "data_points": len(self._history),
            "temperature": {
                "avg": round(sum(temps) / len(temps), 1),
                "max": max(temps),
                "min": min(temps),
            },
            "gpu_utilization": {
                "avg": round(sum(utils) / len(utils), 1),
                "max": max(utils),
                "min": min(utils),
            },
            "memory_utilization": {
                "avg": round(sum(vrams) / len(vrams), 1),
                "max": max(vrams),
                "min": min(vrams),
            },
            "overheat_count": sum(1 for s in self._history if s.is_overheating),
            "idle_ratio": round(
                sum(1 for s in self._history if s.is_idle) / len(self._history) * 100, 1
            ),
        }


# シングルトン
_monitor: Optional[GPUMonitor] = None


def get_gpu_monitor() -> GPUMonitor:
    global _monitor
    if _monitor is None:
        _monitor = GPUMonitor()
    return _monitor
