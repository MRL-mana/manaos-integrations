#!/usr/bin/env python3
"""
Phase2 自動整理:
- 既存 .bak があれば先にZIP退避して削除
- メモログを重複除去（in-place + .bak 作成）
- 生成された .bak をZIP退避して削除

これにより、`phase2_reflection_memos.jsonl` は常に整形され、
`.bak` は残さず `backups/phase2_memos/` にZIPとして蓄積される。
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def _run(cmd: list[str], cwd: Path) -> None:
    p = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=30,
    )
    if p.stdout:
        print(p.stdout.rstrip())
    if p.stderr:
        print(p.stderr.rstrip())
    if p.returncode != 0:
        raise RuntimeError(f"command failed (exit={p.returncode}): {' '.join(cmd)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase2 自動整理（dedup + backup archive）")
    parser.add_argument(
        "--memo",
        default=os.environ.get("PHASE2_REFLECTION_MEMO_LOG", "phase2_reflection_memos.jsonl"),
        help="対象メモログ（default: PHASE2_REFLECTION_MEMO_LOG or phase2_reflection_memos.jsonl）",
    )
    parser.add_argument(
        "--backup-dir",
        default=str(Path("backups") / "phase2_memos"),
        help="ZIP退避先（default: backups/phase2_memos）",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    memo = Path(args.memo)
    bak = memo.with_suffix(memo.suffix + ".bak")

    # 1) 既存 .bak が残っていたら先に退避
    if (root / bak).exists() or bak.exists():
        _run(
            [
                sys.executable,
                str(root / "phase2_archive_memo_backup.py"),
                "--bak",
                str(bak),
                "--out-dir",
                str(args.backup_dir),
                "--delete-bak",
            ],
            cwd=root,
        )

    # 2) dedup in-place + .bak 作成
    _run(
        [
            sys.executable,
            str(root / "phase2_dedup_memos.py"),
            "--path",
            str(memo),
            "--in-place",
            "--backup",
        ],
        cwd=root,
    )

    # 3) 生成された .bak を退避して削除
    if (root / bak).exists() or bak.exists():
        _run(
            [
                sys.executable,
                str(root / "phase2_archive_memo_backup.py"),
                "--bak",
                str(bak),
                "--out-dir",
                str(args.backup_dir),
                "--delete-bak",
            ],
            cwd=root,
        )

    print("Phase2 auto cleanup: done")


if __name__ == "__main__":
    main()
