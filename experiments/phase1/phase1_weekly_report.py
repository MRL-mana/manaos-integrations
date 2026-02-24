#!/usr/bin/env python3
"""
Phase1 週次レポート: 集計＋低満足度集約を一括実行。
オプションで現在ログをスナップショット保存してから集計する。

例:
  python phase1_weekly_report.py
  python phase1_weekly_report.py --save --condition on --tag weekly
"""

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase1 週次レポート（集計＋低満足度）")
    parser.add_argument(
        "--save",
        action="store_true",
        help="先に phase1_save_run でログをスナップショット保存する",
    )
    parser.add_argument(
        "--condition",
        default="on",
        choices=["on", "off"],
        help="--save 時の条件ラベル（default: on）",
    )
    parser.add_argument(
        "--tag",
        default="weekly",
        help="--save 時のタグ（default: weekly）",
    )
    parser.add_argument(
        "--phase2",
        action="store_true",
        help="Phase2 メモ概要（テーマ別件数・満足度）を末尾に追加",
    )
    args = parser.parse_args()

    print(f"=== Phase1 Weekly Report {datetime.now().strftime('%Y-%m-%d %H:%M')} ===\n")

    if args.save:
        try:
            from phase1_save_run import snapshot_logs

            conv_path, refl_path = snapshot_logs(args.condition, args.tag)
            print(f"[Saved] {conv_path.name}, {refl_path.name}\n")
        except Exception as e:
            print(f"[Warn] save_run failed: {e}\n")

    # 集計
    try:
        from phase1_aggregate import main as aggregate_main

        aggregate_main()
    except Exception as e:
        print(f"[Error] aggregate: {e}\n")
        sys.exit(1)

    print()

    # 低満足度集約
    try:
        from phase1_low_satisfaction import main as low_sat_main

        low_sat_main()
    except Exception as e:
        print(f"[Error] low_satisfaction: {e}\n")
        sys.exit(1)

    # Phase2 メモ概要（オプション）
    if args.phase2:
        print()
        try:
            # Phase2: 自動整理（重複除去→ZIP退避）してから概要表示
            cleanup = subprocess.run(
                [sys.executable, str(ROOT / "phase2_auto_cleanup.py")],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                timeout=60,
            )
            if cleanup.stdout:
                print(cleanup.stdout.rstrip())
            if cleanup.stderr:
                print(cleanup.stderr.rstrip())

            from phase2_memo_summary import main as phase2_summary_main

            phase2_summary_main()
        except Exception as e:
            print(f"[Warn] phase2_memo_summary: {e}\n")


if __name__ == "__main__":
    main()
