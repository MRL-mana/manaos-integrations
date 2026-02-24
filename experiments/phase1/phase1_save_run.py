#!/usr/bin/env python3
"""
フェーズ1 実験ログをスナップショット保存するユーティリティ。

既定の `phase1_conversation.log` / `phase1_reflection.log` を
`phase1_runs/<timestamp>_<condition>[_tag]_conversation.log` として保存する。

例:
    python phase1_save_run.py --condition on
    python phase1_save_run.py --condition off --tag round3
"""

from __future__ import annotations

import argparse
import os
import shutil
from datetime import datetime
from pathlib import Path

DEFAULT_CONV = os.environ.get("PHASE1_CONVERSATION_LOG", "phase1_conversation.log")
DEFAULT_REFL = os.environ.get("PHASE1_REFLECTION_LOG", "phase1_reflection.log")
RUN_DIR = Path(__file__).resolve().parent / "phase1_runs"


def snapshot_logs(condition: str, tag: str | None = None) -> tuple[Path, Path]:
    """
    会話ログ・振り返りログを condition/tag 付きで保存する。
    Returns 保存先パス tuple (conversation_path, reflection_path)。
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = f"_{tag}" if tag else ""
    base = f"{timestamp}_{condition}{suffix}"

    RUN_DIR.mkdir(parents=True, exist_ok=True)

    src_conv = Path(DEFAULT_CONV)
    src_refl = Path(DEFAULT_REFL)

    if not src_conv.exists():
        raise FileNotFoundError(f"Conversation log not found: {src_conv}")
    if not src_refl.exists():
        raise FileNotFoundError(f"Reflection log not found: {src_refl}")

    dest_conv = RUN_DIR / f"{base}_conversation.log"
    dest_refl = RUN_DIR / f"{base}_reflection.log"

    shutil.copy2(src_conv, dest_conv)
    shutil.copy2(src_refl, dest_refl)

    return dest_conv, dest_refl


def main() -> None:
    parser = argparse.ArgumentParser(description="フェーズ1ログのスナップショット保存")
    parser.add_argument(
        "--condition",
        required=True,
        choices=["on", "off"],
        help="ログの条件ラベル（on/off）",
    )
    parser.add_argument(
        "--tag",
        help="任意のタグ（例: run3, baseline 等）",
    )
    args = parser.parse_args()

    conv_path, refl_path = snapshot_logs(args.condition, args.tag)
    print("フェーズ1ログを保存しました:")
    print(f"  conversation -> {conv_path}")
    print(f"  reflection   -> {refl_path}")


if __name__ == "__main__":
    main()
