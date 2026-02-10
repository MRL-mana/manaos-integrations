#!/usr/bin/env python3
"""
Phase2: phase2_reflection_memos.jsonl の .bak を圧縮退避して整理する。

- 既定: `phase2_reflection_memos.jsonl.bak` を
  `backups/phase2_memos/<timestamp>_phase2_reflection_memos.jsonl.bak.zip` に保存
- オプションで .bak を削除

例:
  python phase2_archive_memo_backup.py
  python phase2_archive_memo_backup.py --delete-bak
"""

from __future__ import annotations

import argparse
import os
import zipfile
from datetime import datetime
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase2 メモ .bak の圧縮退避")
    parser.add_argument(
        "--bak",
        default=os.environ.get("PHASE2_MEMO_BAK", "phase2_reflection_memos.jsonl.bak"),
        help="対象 .bak（default: PHASE2_MEMO_BAK or phase2_reflection_memos.jsonl.bak）",
    )
    parser.add_argument(
        "--out-dir",
        default=str(Path("backups") / "phase2_memos"),
        help="出力先ディレクトリ（default: backups/phase2_memos）",
    )
    parser.add_argument(
        "--delete-bak",
        action="store_true",
        help="圧縮後に .bak を削除する",
    )
    args = parser.parse_args()

    bak_path = Path(args.bak)
    if not bak_path.exists():
        print(f"No bak found: {bak_path}")
        return

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_path = out_dir / f"{ts}_{bak_path.name}.zip"

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.write(bak_path, arcname=bak_path.name)

    print(f"Archived: {bak_path} -> {zip_path}")

    if args.delete_bak:
        try:
            bak_path.unlink()
            print(f"Deleted: {bak_path}")
        except Exception as e:
            print(f"Warn: failed to delete bak: {e}")


if __name__ == "__main__":
    main()
