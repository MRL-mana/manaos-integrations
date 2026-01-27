#!/usr/bin/env python3
"""
Phase 1 24h summary (fixed).
Use this instead of phase1_24h_summary.py if it was reverted.
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional


def load_snapshot(p: Path) -> dict:
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def collect_snapshots(snapshot_dir: Path, hours: int) -> List[Path]:
    cutoff = datetime.now().timestamp() - (hours * 3600)

    files: List[Path] = []
    files.extend(snapshot_dir.glob("phase1_metrics_snapshot_*.json"))

    for d in snapshot_dir.iterdir():
        if d.is_dir() and re.match(r"\d{4}-\d{2}-\d{2}", d.name):
            files.extend(d.glob("*.json"))

    files = sorted(files, key=lambda p: p.stat().st_mtime)
    return [p for p in files if p.stat().st_mtime >= cutoff]


def calculate_summary(snapshots: List[Path], baseline: Optional[Path], hours: int) -> dict:
    if not snapshots:
        return {"error": "スナップショットがありません", "snapshot_count": 0, "time_range_hours": hours}

    baseline_data = load_snapshot(baseline) if baseline and baseline.exists() else None

    p95 = []
    writes = []
    http5xx = []

    for p in snapshots:
        try:
            s = load_snapshot(p)
            m = s.get("metrics", {})
            e = s.get("errors", {})
            p95.append(m.get("e2e_p95_sec", 0))
            writes.append(m.get("writes_per_min", 0))
            http5xx.append(e.get("http_5xx_last_60min", 0))
        except Exception:
            continue

    return {
        "snapshot_count": len(snapshots),
        "time_range_hours": hours,
        "metrics": {
            "p95_max": max(p95) if p95 else 0,
            "writes_per_min_max": max(writes) if writes else 0,
            "http_5xx_total": sum(http5xx),
        },
        "baseline": {
            "p95": baseline_data.get("metrics", {}).get("e2e_p95_sec", 0) if baseline_data else 0,
        } if baseline_data else None,
    }


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/phase1_24h_summary_fixed.py <snapshot_dir> [baseline] [hours]")
        raise SystemExit(2)

    snapshot_dir = Path(sys.argv[1])
    baseline = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("phase1_metrics_snapshot_baseline.json")
    hours = int(sys.argv[3]) if len(sys.argv) > 3 else 24

    snaps = collect_snapshots(snapshot_dir, hours)
    summary = calculate_summary(snaps, baseline, hours)

    out = snapshot_dir / f"phase1_24h_summary_fixed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\nSaved: {out}")


if __name__ == "__main__":
    main()

