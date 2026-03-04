"""
Prometheus メトリクスエクスポーター
====================================
Prometheus / Grafana 用の /metrics エンドポイント互換テキスト出力。
外部依存なし — prometheus_client 不要で動作。

使い方:
  exporter = PrometheusExporter()
  exporter.inc("rl_cycles_total", labels={"outcome": "success"})
  exporter.set("rl_current_difficulty", 2.0)
  exporter.observe("rl_score", 0.85)
  text = exporter.render()  # Prometheus text format
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple


class PrometheusExporter:
    """
    軽量 Prometheus エクスポーター。外部依存ゼロ。
    - Counter: inc()
    - Gauge: set(), inc(), dec()
    - Histogram: observe() (bucket + sum + count)
    """

    # デフォルトの histogram buckets
    DEFAULT_BUCKETS = (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, float("inf"))

    def __init__(self):
        self._lock = threading.Lock()
        # Counters: {(name, frozen_labels): value}
        self._counters: Dict[Tuple, float] = defaultdict(float)
        # Gauges: {(name, frozen_labels): value}
        self._gauges: Dict[Tuple, float] = {}
        # Histograms: {name: {frozen_labels: {"buckets": {le: count}, "sum": v, "count": n}}}
        self._histograms: Dict[str, Dict[Tuple, Dict[str, Any]]] = defaultdict(dict)
        # Metadata: {name: (type, help)}
        self._meta: Dict[str, Tuple[str, str]] = {}

    def register(self, name: str, metric_type: str, help_text: str = "") -> None:
        """メトリクス定義を登録（HELP / TYPE 行用）"""
        self._meta[name] = (metric_type, help_text)

    # ─── Counter ──────────────────────────────────
    def inc(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """Counter をインクリメント"""
        key = (name, self._freeze_labels(labels))
        with self._lock:
            self._counters[key] += value
        if name not in self._meta:
            self._meta[name] = ("counter", "")

    # ─── Gauge ────────────────────────────────────
    def set(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Gauge を設定"""
        key = (name, self._freeze_labels(labels))
        with self._lock:
            self._gauges[key] = value
        if name not in self._meta:
            self._meta[name] = ("gauge", "")

    def gauge_inc(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """Gauge をインクリメント"""
        key = (name, self._freeze_labels(labels))
        with self._lock:
            self._gauges[key] = self._gauges.get(key, 0.0) + value
        if name not in self._meta:
            self._meta[name] = ("gauge", "")

    # ─── Histogram ────────────────────────────────
    def observe(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
        buckets: Optional[Tuple[float, ...]] = None,
    ) -> None:
        """Histogram に値を記録"""
        fl = self._freeze_labels(labels)
        bkts = buckets or self.DEFAULT_BUCKETS
        with self._lock:
            if fl not in self._histograms[name]:
                self._histograms[name][fl] = {
                    "buckets": {le: 0 for le in bkts},
                    "sum": 0.0,
                    "count": 0,
                }
            h = self._histograms[name][fl]
            h["sum"] += value
            h["count"] += 1
            for le in h["buckets"]:
                if value <= le:
                    h["buckets"][le] += 1
        if name not in self._meta:
            self._meta[name] = ("histogram", "")

    # ─── レンダリング ──────────────────────────────
    def render(self) -> str:
        """
        Prometheus text exposition format を出力。
        /metrics エンドポイントでそのまま返せる。
        """
        lines: List[str] = []
        rendered_names: set = set()

        with self._lock:
            # Counters
            for (name, fl), val in sorted(self._counters.items()):
                if name not in rendered_names:
                    self._render_meta(lines, name)
                    rendered_names.add(name)
                lines.append(f"{name}{self._labels_str(fl)} {val}")

            # Gauges
            for (name, fl), val in sorted(self._gauges.items()):
                if name not in rendered_names:
                    self._render_meta(lines, name)
                    rendered_names.add(name)
                lines.append(f"{name}{self._labels_str(fl)} {val}")

            # Histograms
            for name in sorted(self._histograms.keys()):
                if name not in rendered_names:
                    self._render_meta(lines, name)
                    rendered_names.add(name)
                for fl, h in self._histograms[name].items():
                    for le, cnt in sorted(h["buckets"].items()):
                        le_str = "+Inf" if le == float("inf") else str(le)
                        lbl = self._merge_labels(fl, ("le", le_str))
                        lines.append(f"{name}_bucket{{{lbl}}} {cnt}")
                    lines.append(f"{name}_sum{self._labels_str(fl)} {h['sum']}")
                    lines.append(f"{name}_count{self._labels_str(fl)} {h['count']}")

        lines.append("")
        return "\n".join(lines)

    def get_snapshot(self) -> Dict[str, Any]:
        """JSON-friendly スナップショット（デバッグ / API 用）"""
        with self._lock:
            return {
                "counters": {
                    f"{n}{self._labels_str(fl)}": v
                    for (n, fl), v in self._counters.items()
                },
                "gauges": {
                    f"{n}{self._labels_str(fl)}": v
                    for (n, fl), v in self._gauges.items()
                },
                "histograms": {
                    name: {
                        self._labels_str(fl): {
                            "count": h["count"],
                            "sum": round(h["sum"], 4),
                        }
                        for fl, h in entries.items()
                    }
                    for name, entries in self._histograms.items()
                },
            }

    # ─── ヘルパー ──────────────────────────────────
    @staticmethod
    def _freeze_labels(labels: Optional[Dict[str, str]]) -> Tuple[Tuple[str, str], ...]:
        if not labels:
            return ()
        return tuple(sorted(labels.items()))

    @staticmethod
    def _labels_str(fl: Tuple[Tuple[str, str], ...]) -> str:
        if not fl:
            return ""
        parts = [f'{k}="{v}"' for k, v in fl]
        return "{" + ",".join(parts) + "}"

    @staticmethod
    def _merge_labels(fl: Tuple[Tuple[str, str], ...], extra: Tuple[str, str]) -> str:
        all_labels = list(fl) + [extra]
        return ",".join(f'{k}="{v}"' for k, v in all_labels)

    def _render_meta(self, lines: List[str], name: str) -> None:
        if name in self._meta:
            mtype, help_text = self._meta[name]
            if help_text:
                lines.append(f"# HELP {name} {help_text}")
            lines.append(f"# TYPE {name} {mtype}")
