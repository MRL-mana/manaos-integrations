#!/usr/bin/env python3
"""
Phase1 低満足度履歴の簡易表示。
phase1_low_sat_history.jsonl を読み、直近 N 件の ts / low_count / reasons_top を一覧表示。
"""

import json
import os
from pathlib import Path

HISTORY_LOG = os.environ.get("PHASE1_LOW_SAT_HISTORY_LOG", "phase1_low_sat_history.jsonl")
DEFAULT_TAIL = 10

ROOT = Path(__file__).resolve().parent


def load_jsonl(path: str) -> list[dict]:
    out = []
    p = Path(path)
    if not p.exists():
        return out
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Phase1 低満足度履歴の簡易表示")
    parser.add_argument("-n", "--tail", type=int, default=DEFAULT_TAIL, help="表示する直近件数")
    args = parser.parse_args()

    path = ROOT / HISTORY_LOG
    records = load_jsonl(str(path))
    if not records:
        print(f"履歴: {path.name} (0 件)")
        return

    tail = records[-args.tail :]
    print(f"=== Phase1 低満足度履歴（直近 {len(tail)} 件）: {path.name} ===\n")
    print("ts | low_count | reasons_top")
    print("-" * 60)
    for r in tail:
        ts = (r.get("ts") or "")[:19]
        low = r.get("low_count", 0)
        reasons = r.get("reasons_top") or []
        parts = [f"{x.get('reason', '')[:30]}...({x.get('count', 0)})" for x in reasons[:3]]
        top_str = "; ".join(parts)
        if not top_str:
            top_str = "-"
        print(f"{ts} | {low} | {top_str}")


if __name__ == "__main__":
    main()
