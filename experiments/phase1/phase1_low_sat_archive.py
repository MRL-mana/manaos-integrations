#!/usr/bin/env python3
"""
Phase1 低満足度の履歴を1行追記する。
get_low_summary の結果を phase1_low_sat_history.jsonl にタイムスタンプ付きで保存し、
週次で傾向を追えるようにする。
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HISTORY_LOG = os.environ.get("PHASE1_LOW_SAT_HISTORY_LOG", "phase1_low_sat_history.jsonl")


def main() -> None:
    from phase1_low_satisfaction import get_low_summary

    low_count, reasons_top = get_low_summary(top_n=5)
    record = {
        "ts": datetime.now(tz=timezone.utc).isoformat(),
        "low_count": low_count,
        "reasons_top": [{"reason": r[:120], "count": c} for r, c in reasons_top],
    }
    path = ROOT / HISTORY_LOG
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"Archived: low_count={low_count} -> {path.name}")


if __name__ == "__main__":
    main()
