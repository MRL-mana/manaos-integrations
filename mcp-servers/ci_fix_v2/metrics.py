"""
Metrics — Prometheus-style メトリクス収集
===========================================
自前実装。prometheus_client ライブラリなしで動作。

収集メトリクス:
  - image_generations_total      — 生成リクエスト総数 (status別)
  - image_generation_duration    — 生成時間ヒストグラム (秒)
  - image_quality_score          — 品質スコアヒストグラム
  - api_requests_total           — API リクエスト総数 (endpoint別)
  - queue_depth                  — キュー深度 (ゲージ)
  - billing_usage_total          — 課金使用量 (ゲージ)
  - gpu_cost_yen_total           — GPU コスト累計 (カウンター)

出力:
  GET /metrics → Prometheus text format
"""

from __future__ import annotations

import logging
import time
import threading
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple

_log = logging.getLogger("manaos.metrics")


class _Counter:
    """スレッドセーフなカウンター"""
    def __init__(self):
        self._values: Dict[Tuple[str, ...], float] = defaultdict(float)
        self._lock = threading.Lock()

    def inc(self, *labels: str, value: float = 1.0):
        with self._lock:
            self._values[labels] += value

    def get(self, *labels: str) -> float:
        return self._values.get(labels, 0.0)

    def items(self):
        with self._lock:
            return list(self._values.items())


class _Gauge:
    """スレッドセーフなゲージ"""
    def __init__(self):
        self._values: Dict[Tuple[str, ...], float] = defaultdict(float)
        self._lock = threading.Lock()

    def set(self, *labels: str, value: float):
        with self._lock:
            self._values[labels] = value

    def inc(self, *labels: str, value: float = 1.0):
        with self._lock:
            self._values[labels] += value

    def get(self, *labels: str) -> float:
        return self._values.get(labels, 0.0)

    def items(self):
        with self._lock:
            return list(self._values.items())


class _Histogram:
    """簡易ヒストグラム（バケット）"""
    def __init__(self, buckets: List[float]):
        self._buckets = sorted(buckets) + [float("inf")]
        self._counts: Dict[Tuple[str, ...], List[int]] = defaultdict(
            lambda: [0] * len(self._buckets)
        )
        self._sums: Dict[Tuple[str, ...], float] = defaultdict(float)
        self._totals: Dict[Tuple[str, ...], int] = defaultdict(int)
        self._lock = threading.Lock()

    def observe(self, value: float, *labels: str):
        with self._lock:
            self._sums[labels] += value
            self._totals[labels] += 1
            for i, b in enumerate(self._buckets):
                if value <= b:
                    self._counts[labels][i] += 1

    def items(self):
        with self._lock:
            result = {}
            for labels in set(list(self._counts.keys()) + list(self._sums.keys())):
                result[labels] = {
                    "buckets": list(zip(self._buckets, self._counts[labels])),
                    "sum": self._sums[labels],
                    "count": self._totals[labels],
                }
            return list(result.items())


# ─── Global Metrics ───────────────────────────────────

# Counters
generations_total = _Counter()      # labels: (status,)
api_requests_total = _Counter()     # labels: (method, endpoint, status_code)
gpu_cost_yen_total = _Counter()     # labels: ()

# Gauges
queue_depth = _Gauge()              # labels: ()
active_generations = _Gauge()       # labels: ()
billing_remaining = _Gauge()        # labels: (api_key,)

# Histograms
generation_duration = _Histogram(
    buckets=[1, 2, 5, 10, 20, 30, 60, 120, 300]  # 秒
)
quality_score = _Histogram(
    buckets=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
)

# 起動時刻
_start_time = time.monotonic()


# ─── Record Helpers ───────────────────────────────────

def record_generation(
    status: str,
    duration_seconds: float,
    quality_overall: Optional[float] = None,
    cost_yen: float = 0,
):
    """画像生成完了時に呼ぶ"""
    generations_total.inc(status)
    generation_duration.observe(duration_seconds, status)
    if quality_overall is not None:
        quality_score.observe(quality_overall, status)
    if cost_yen > 0:
        gpu_cost_yen_total.inc(value=cost_yen)


def record_api_request(method: str, endpoint: str, status_code: int):
    """API リクエスト完了時に呼ぶ"""
    api_requests_total.inc(method, endpoint, str(status_code))


def update_queue_depth(depth: int):
    """キュー深度を更新"""
    queue_depth.set(value=float(depth))


# ─── Prometheus Text Format Export ────────────────────

def export_prometheus() -> str:
    """Prometheus テキストフォーマットで全メトリクスをエクスポート"""
    lines: List[str] = []
    now_ms = int(time.time() * 1000)

    # uptime
    uptime = time.monotonic() - _start_time
    lines.append("# HELP manaos_uptime_seconds Service uptime in seconds")
    lines.append("# TYPE manaos_uptime_seconds gauge")
    lines.append(f"manaos_uptime_seconds {uptime:.1f}")
    lines.append("")

    # generations_total
    lines.append("# HELP manaos_image_generations_total Total image generation requests")
    lines.append("# TYPE manaos_image_generations_total counter")
    for labels, value in generations_total.items():
        status = labels[0] if labels else "unknown"
        lines.append(f'manaos_image_generations_total{{status="{status}"}} {value}')
    lines.append("")

    # api_requests_total
    lines.append("# HELP manaos_api_requests_total Total API requests")
    lines.append("# TYPE manaos_api_requests_total counter")
    for labels, value in api_requests_total.items():
        method, endpoint, code = labels if len(labels) == 3 else ("?", "?", "?")
        lines.append(
            f'manaos_api_requests_total{{method="{method}",endpoint="{endpoint}",'
            f'status="{code}"}} {value}'
        )
    lines.append("")

    # gpu_cost_yen_total
    lines.append("# HELP manaos_gpu_cost_yen_total Total GPU cost in JPY")
    lines.append("# TYPE manaos_gpu_cost_yen_total counter")
    total_cost = sum(v for _, v in gpu_cost_yen_total.items()) or 0
    lines.append(f"manaos_gpu_cost_yen_total {total_cost:.4f}")
    lines.append("")

    # queue_depth
    lines.append("# HELP manaos_queue_depth Current queue depth")
    lines.append("# TYPE manaos_queue_depth gauge")
    depth = sum(v for _, v in queue_depth.items()) or 0
    lines.append(f"manaos_queue_depth {depth}")
    lines.append("")

    # generation_duration histogram
    lines.append("# HELP manaos_generation_duration_seconds Image generation duration in seconds")
    lines.append("# TYPE manaos_generation_duration_seconds histogram")
    for labels, data in generation_duration.items():
        status = labels[0] if labels else "unknown"
        cumulative = 0
        for bound, count in data["buckets"]:
            cumulative += count
            le = "+Inf" if bound == float("inf") else f"{bound}"
            lines.append(
                f'manaos_generation_duration_seconds_bucket{{status="{status}",le="{le}"}} {cumulative}'
            )
        lines.append(f'manaos_generation_duration_seconds_sum{{status="{status}"}} {data["sum"]:.3f}')
        lines.append(f'manaos_generation_duration_seconds_count{{status="{status}"}} {data["count"]}')
    lines.append("")

    # quality_score histogram
    lines.append("# HELP manaos_quality_score Image quality score distribution")
    lines.append("# TYPE manaos_quality_score histogram")
    for labels, data in quality_score.items():
        status = labels[0] if labels else "unknown"
        cumulative = 0
        for bound, count in data["buckets"]:
            cumulative += count
            le = "+Inf" if bound == float("inf") else f"{bound}"
            lines.append(
                f'manaos_quality_score_bucket{{status="{status}",le="{le}"}} {cumulative}'
            )
        lines.append(f'manaos_quality_score_sum{{status="{status}"}} {data["sum"]:.2f}')
        lines.append(f'manaos_quality_score_count{{status="{status}"}} {data["count"]}')
    lines.append("")

    return "\n".join(lines) + "\n"


def export_json() -> Dict:
    """JSON 形式でメトリクスサマリを返す"""
    gen_items = generations_total.items()
    gen_total = sum(v for _, v in gen_items) or 0
    gen_success = generations_total.get("success")
    gen_failed = generations_total.get("failed")

    api_total = sum(v for _, v in api_requests_total.items()) or 0

    return {
        "uptime_seconds": round(time.monotonic() - _start_time, 1),
        "generations": {
            "total": int(gen_total),
            "success": int(gen_success),
            "failed": int(gen_failed),
            "success_rate": round(gen_success / gen_total * 100, 1) if gen_total > 0 else 0,
        },
        "api_requests_total": int(api_total),
        "gpu_cost_yen_total": round(
            sum(v for _, v in gpu_cost_yen_total.items()) or 0, 4
        ),
        "queue_depth": int(sum(v for _, v in queue_depth.items()) or 0),
        "timestamp": datetime.now().isoformat(),
    }
