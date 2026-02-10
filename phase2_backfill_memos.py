#!/usr/bin/env python3
"""
Phase2: 既存の phase1_conversation.log / phase1_reflection.log から
振り返りメモを phase2_reflection_memos.jsonl に投入する。
"""

import os
import sys
from pathlib import Path

from phase2_reflection_memo import (
    load_jsonl,
    theme_id_from_conv,
    append_memo,
    MEMO_LOG,
)

ROOT = Path(__file__).resolve().parent
CONV_LOG = os.environ.get("PHASE1_CONVERSATION_LOG", "phase1_conversation.log")
REFL_LOG = os.environ.get("PHASE1_REFLECTION_LOG", "phase1_reflection.log")


def main() -> None:
    conv_path = ROOT / CONV_LOG
    refl_path = ROOT / REFL_LOG
    if not conv_path.exists():
        print(f"Conversation log not found: {conv_path}")
        sys.exit(1)
    if not refl_path.exists():
        print(f"Reflection log not found: {refl_path}")
        sys.exit(1)

    conv = load_jsonl(str(conv_path))
    refl = load_jsonl(str(refl_path))
    theme_by_thread = theme_id_from_conv(conv)

    # 既にメモに存在する (thread_id, turn_id) はスキップ（重複追記を防ぐ）
    memo_path = ROOT / MEMO_LOG
    existing = set()
    if memo_path.exists():
        for rec in load_jsonl(str(memo_path)):
            tid = rec.get("thread_id")
            turn = rec.get("turn_id")
            if tid is not None and turn is not None:
                existing.add((str(tid), int(turn)))

    appended = 0
    for r in refl:
        thread_id = r.get("thread_id", "")
        turn_id = r.get("turn_id", 0)
        if (thread_id, turn_id) in existing:
            continue
        theme_id = theme_by_thread.get(thread_id)
        if not theme_id:
            continue
        satisfaction = r.get("satisfaction")
        reason = r.get("reason") or ""
        append_memo(theme_id, thread_id, turn_id, satisfaction, reason)
        existing.add((thread_id, turn_id))
        appended += 1

    print(f"Backfill: {appended} memos appended to {MEMO_LOG}")


if __name__ == "__main__":
    main()
