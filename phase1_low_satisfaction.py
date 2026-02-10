#!/usr/bin/env python3
"""
Phase1 振り返りログから満足度1〜2の行を抽出し、理由を集約して表示する。
プロンプト改善・低満足度傾向の把握用。
"""

import json
import os
import sys
from collections import Counter
from pathlib import Path

REFLECTION_LOG = os.environ.get("PHASE1_REFLECTION_LOG", "phase1_reflection.log")


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


def get_low_summary(
    refl_path: str | None = None,
    top_n: int = 5,
) -> tuple[int, list[tuple[str, int]]]:
    """
    満足度1〜2の件数と理由の出現回数（上位 top_n）を返す。
    Returns: (low_count, [(reason_short, count), ...])
    """
    path = refl_path or REFLECTION_LOG
    refl = load_jsonl(path)
    low = [
        r
        for r in refl
        if isinstance(r.get("satisfaction"), (int, float)) and 1 <= r["satisfaction"] <= 2
    ]
    if not low:
        return 0, []
    reasons = [r.get("reason") or "" for r in low]
    reason_counts = Counter(r.strip()[:80] for r in reasons if r.strip())
    top_list = [(r, c) for r, c in reason_counts.most_common(top_n)]
    return len(low), top_list


def main() -> None:
    refl = load_jsonl(REFLECTION_LOG)
    low = [
        r
        for r in refl
        if isinstance(r.get("satisfaction"), (int, float)) and 1 <= r["satisfaction"] <= 2
    ]
    if not low:
        print(f"振り返りログ: {REFLECTION_LOG} ({len(refl)} 行)")
        print("満足度1〜2の行はありません。")
        return

    reasons = [r.get("reason") or "" for r in low]
    reason_counts = Counter(r.strip()[:80] for r in reasons if r.strip())

    print("=== Phase1 低満足度（1〜2）集約 ===")
    print(f"振り返りログ: {REFLECTION_LOG} ({len(refl)} 行)")
    print(f"満足度1〜2: {len(low)} 件")
    print()
    print("理由の出現回数（上位15）:")
    for reason_short, count in reason_counts.most_common(15):
        print(f"  [{count}] {reason_short}")
    print()
    print("--- 全件（満足度, 理由先頭80字）---")
    for r in low[:30]:
        sat = r.get("satisfaction", "?")
        reason = (r.get("reason") or "")[:80]
        print(f"  {sat}: {reason}")


if __name__ == "__main__":
    main()
    sys.exit(0)
