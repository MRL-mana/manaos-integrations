#!/usr/bin/env python3
"""
直近 N 時間分のスナップショットからメトリクスの中央値等を計算し、
phase1_metrics_snapshot_baseline.json を更新する（週次運用向け）。
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from datetime import datetime

_DATE_DIR_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_HOUR_JSON_RE = re.compile(r"^\d{2}\.json$")


def _list_snapshot_files(snapshot_dir: Path, max_count: int = 24 * 7):
    if not snapshot_dir.exists():
        return []
    out = []
    for p in snapshot_dir.rglob("*.json"):
        if not p.is_file():
            continue
        if not _DATE_DIR_RE.match(p.parent.name) or not _HOUR_JSON_RE.match(p.name):
            continue
        out.append(p)
    out = sorted(out, key=lambda p: (p.parent.name, p.name), reverse=True)
    return out[:max_count]


def main() -> int:
    base = Path(__file__).resolve().parent
    snapshots_dir = base / "snapshots"
    baseline_path = base / "phase1_metrics_snapshot_baseline.json"

    # 直近 24*7 件（最大7日分）を取得
    paths = _list_snapshot_files(snapshots_dir, max_count=24 * 7)
    if not paths:
        print("[WARN] No snapshot files found.")
        return 1

    values = {
        "e2e_p95_sec": [],
        "writes_per_min": [],
        "contradiction_rate": [],
        "gate_block_rate": [],
    }
    for p in paths:
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
        m = data.get("metrics", {})
        values["e2e_p95_sec"].append(m.get("e2e_p95_sec", 0))
        values["writes_per_min"].append(m.get("writes_per_min", 0))
        values["contradiction_rate"].append(m.get("contradiction_rate", 0))
        values["gate_block_rate"].append(m.get("gate_block_rate", 0))

    def median(lst):
        if not lst:
            return 0
        s = sorted(lst)
        n = len(s)
        return (s[(n - 1) // 2] + s[n // 2]) / 2 if n else 0

    metrics = {
        "e2e_p95_sec": median(values["e2e_p95_sec"]),
        "writes_per_min": int(median(values["writes_per_min"])),
        "contradiction_rate": median(values["contradiction_rate"]),
        "gate_block_rate": median(values["gate_block_rate"]),
        "slot_usage_variance": 0,
    }

    # 既存ベースラインを読んで config/security 等を維持
    existing = {}
    if baseline_path.exists():
        try:
            with open(baseline_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            pass

    baseline = {
        "timestamp": datetime.now().isoformat(),
        "phase": existing.get("phase", "Phase 1: Read-only"),
        "config": existing.get("config", {}),
        "security": existing.get("security", {}),
        "metrics": metrics,
        "storage": existing.get("storage", {}),
        "errors": existing.get("errors", {}),
        "api_status": existing.get("api_status", {}),
    }

    with open(baseline_path, "w", encoding="utf-8") as f:
        json.dump(baseline, f, ensure_ascii=False, indent=2)
    print(f"[OK] Updated baseline from {len(paths)} snapshots: {baseline_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
