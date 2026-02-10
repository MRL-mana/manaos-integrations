#!/usr/bin/env python3
"""
Phase 2 Auto Monitor (hourly)

- Create a snapshot file at: snapshots/YYYY-MM-DD/HH.json
- Uses existing snapshot generator: phase1_metrics_snapshot.py

Note:
This script is intentionally ASCII-only in prints to avoid Windows console encoding issues.
"""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path


def _log(base_dir: Path, message: str, is_error: bool = False) -> None:
    """監視ログを logs/phase2_auto_YYYYMMDD.log に追記する。"""
    log_dir = base_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"phase2_auto_{datetime.now().strftime('%Y-%m-%d')}.log"
    try:
        with open(log_file, "a", encoding="utf-8", errors="replace") as f:
            prefix = "ERROR" if is_error else "INFO"
            f.write(f"{datetime.now().isoformat()} [{prefix}] {message}\n")
    except Exception:
        pass


def _snapshot_path(base_dir: Path) -> Path:
    now = datetime.now()
    date_dir = base_dir / "snapshots" / now.strftime("%Y-%m-%d")
    date_dir.mkdir(parents=True, exist_ok=True)
    return date_dir / f"{now.strftime('%H')}.json"


def main() -> int:
    base_dir = Path(__file__).resolve().parent
    out_path = _snapshot_path(base_dir)
    baseline_path = base_dir / "phase1_metrics_snapshot_baseline.json"
    snapshot_script = base_dir / "phase1_metrics_snapshot.py"

    if not snapshot_script.exists():
        print("[ERROR] Missing required file: phase1_metrics_snapshot.py")
        _log(base_dir, "Missing phase1_metrics_snapshot.py", is_error=True)
        return 2

    # Generate snapshot
    cmd = [sys.executable, str(snapshot_script), str(out_path), str(baseline_path)]
    try:
        p = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=60,
        )
    except Exception as e:
        print(f"[ERROR] Snapshot generation failed: {e}")
        _log(base_dir, f"Snapshot generation failed: {e}", is_error=True)
        return 2

    if p.returncode != 0:
        print("[ERROR] Snapshot generator returned non-zero.")
        if p.stdout.strip():
            print("--- stdout ---")
            print(p.stdout.strip()[:4000])
        if p.stderr.strip():
            print("--- stderr ---")
            print(p.stderr.strip()[:4000])
        _log(base_dir, f"Snapshot generator exit code {p.returncode}", is_error=True)
        return int(p.returncode) if int(p.returncode) != 0 else 2

    print(f"[OK] Snapshot saved: {out_path}")
    _log(base_dir, f"Snapshot saved: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
