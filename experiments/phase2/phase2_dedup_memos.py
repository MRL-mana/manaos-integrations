#!/usr/bin/env python3
"""
Phase2 メモログ（JSONL）の重複除去・整形。

重複キー: (thread_id, turn_id) を基本とし、同キーが複数ある場合は ts が新しい方を残す。
バックアップを作って in-place で置換する運用を想定。

例:
  python phase2_dedup_memos.py --in-place --backup
  python phase2_dedup_memos.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not path.exists():
        return out
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                v = json.loads(line)
                if isinstance(v, dict):
                    out.append(v)
            except json.JSONDecodeError:
                continue
    return out


def _key(rec: dict[str, Any]) -> tuple[str, int] | None:
    tid = rec.get("thread_id")
    turn = rec.get("turn_id")
    if tid is None or turn is None:
        return None
    try:
        return (str(tid), int(turn))
    except Exception:
        return None


def dedup(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    """
    Returns: (deduped_records, duplicate_count_removed)
    """
    kept: dict[tuple[str, int], dict[str, Any]] = {}
    order: list[tuple[str, int]] = []
    removed = 0

    for r in records:
        k = _key(r)
        if k is None:
            # キー不明は落とさず、そのままユニーク扱い（末尾に保持）
            # ただし安定のため、thread_id/turn_id が無い行はそのまま残す
            k_fallback = (f"__no_key__:{len(order)}", 0)
            kept[k_fallback] = r
            order.append(k_fallback)
            continue

        if k not in kept:
            kept[k] = r
            order.append(k)
            continue

        # 同キーの重複: ts が新しい方を残す（ISO8601 文字列比較で概ねOK）
        prev = kept[k]
        prev_ts = str(prev.get("ts") or "")
        cur_ts = str(r.get("ts") or "")
        if cur_ts and (not prev_ts or cur_ts > prev_ts):
            kept[k] = r
        removed += 1

    deduped = [kept[k] for k in order]
    return deduped, removed


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase2 メモログの重複除去")
    parser.add_argument(
        "--path",
        default=os.environ.get("PHASE2_REFLECTION_MEMO_LOG", "phase2_reflection_memos.jsonl"),
        help="対象JSONL（default: PHASE2_REFLECTION_MEMO_LOG or phase2_reflection_memos.jsonl）",
    )
    parser.add_argument("--dry-run", action="store_true", help="書き換えずに件数だけ表示")
    parser.add_argument("--in-place", action="store_true", help="同じファイルに上書き")
    parser.add_argument("--backup", action="store_true", help="in-place 時に .bak を作る")
    args = parser.parse_args()

    path = Path(args.path)
    records = load_jsonl(path)
    deduped, removed = dedup(records)

    print(f"Input: {path} ({len(records)} lines)")
    print(f"Output: {len(deduped)} lines (removed {removed} duplicates)")

    if args.dry_run:
        return

    if args.in_place:
        tmp = path.with_suffix(path.suffix + ".tmp")
        write_jsonl(tmp, deduped)
        if args.backup and path.exists():
            bak = path.with_suffix(path.suffix + ".bak")
            try:
                if bak.exists():
                    bak.unlink()
            except Exception:
                pass
            path.replace(bak)
        tmp.replace(path)
        print("Done: in-place updated")
        return

    out_path = path.with_suffix(path.suffix + ".dedup.jsonl")
    write_jsonl(out_path, deduped)
    print(f"Done: wrote {out_path}")


if __name__ == "__main__":
    main()
