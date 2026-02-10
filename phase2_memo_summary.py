#!/usr/bin/env python3
"""
Phase2 メモの概要: テーマ別件数・満足度平均を一覧表示。
phase2_reflection_memos.jsonl の内容を把握する用。
"""

import json
import os
from collections import defaultdict
from pathlib import Path

MEMO_LOG = os.environ.get("PHASE2_REFLECTION_MEMO_LOG", "phase2_reflection_memos.jsonl")


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
    records = load_jsonl(MEMO_LOG)
    if not records:
        print(f"Phase2 メモ: {MEMO_LOG} (0 件)")
        return

    by_theme: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        tid = r.get("theme_id") or ""
        if tid:
            by_theme[tid].append(r)

    print(f"=== Phase2 メモ概要: {MEMO_LOG} ({len(records)} 件) ===\n")
    print("テーマID | 件数 | 満足度平均")
    print("-" * 50)
    for theme_id in sorted(by_theme.keys(), key=lambda t: -len(by_theme[t])):
        memos = by_theme[theme_id]
        sats = [
            m.get("satisfaction") for m in memos if isinstance(m.get("satisfaction"), (int, float))
        ]
        avg = sum(sats) / len(sats) if sats else 0
        print(f"{theme_id} | {len(memos)} | {avg:.2f}")


if __name__ == "__main__":
    main()
