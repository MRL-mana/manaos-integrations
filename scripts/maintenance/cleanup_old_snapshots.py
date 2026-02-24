#!/usr/bin/env python3
"""
古いスナップショットを整理する（snapshots/YYYY-MM-DD のうち N 日より古いものを削除）
誤削除防止のため --dry-run をデフォルト推奨。本番は --execute を明示。
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

# snapshots/YYYY-MM-DD 形式のディレクトリ名かどうか
_DATE_DIR_PATTERN = __import__("re").compile(r"^\d{4}-\d{2}-\d{2}$")


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean old snapshot directories")
    parser.add_argument(
        "snapshots_dir",
        nargs="?",
        default="snapshots",
        help="Snapshots root directory (default: snapshots)",
    )
    parser.add_argument(
        "--older-than",
        type=int,
        default=30,
        help="Remove directories older than N days (default: 30)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Only list, do not delete (default)")
    parser.add_argument("--execute", action="store_true", help="Actually delete")
    args = parser.parse_args()
    do_delete = args.execute and not args.dry_run

    root = Path(args.snapshots_dir)
    if not root.exists():
        print(f"[WARN] Directory not found: {root}")
        return 0

    cutoff = datetime.now() - timedelta(days=args.older_than)
    to_remove: list[Path] = []
    for child in root.iterdir():
        if not child.is_dir():
            continue
        if not _DATE_DIR_PATTERN.match(child.name):
            continue
        try:
            # ディレクトリ名から日付をパース
            y, m, d = int(child.name[:4]), int(child.name[5:7]), int(child.name[8:10])
            dt = datetime(y, m, d)
            if dt < cutoff:
                to_remove.append(child)
        except (ValueError, IndexError):
            continue

    to_remove.sort(key=lambda p: p.name)

    if not to_remove:
        print("[OK] No old snapshot directories to remove.")
        return 0

    print(f"Directories older than {args.older_than} days ({cutoff.date()}):")
    for p in to_remove:
        print(f"  - {p}")

    if not do_delete:
        print(
            f"\n[DRY-RUN] Would remove {len(to_remove)} directories. Run with --execute to delete."
        )
        return 0

    for p in to_remove:
        try:
            for f in p.iterdir():
                f.unlink()
            p.rmdir()
            print(f"[OK] Removed: {p}")
        except Exception as e:
            print(f"[ERROR] Failed to remove {p}: {e}")
            return 1
    print(f"[OK] Removed {len(to_remove)} directories.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
