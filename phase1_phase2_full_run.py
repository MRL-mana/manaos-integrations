#!/usr/bin/env python3
"""
Phase1/Phase2 一括実行: スナップショット（任意）→ 集計 → 低満足度 → バックフィル → メモ概要 → アーカイブ → 履歴表示。
1コマンドで自己観察パイプラインを全部回す。

例:
  python phase1_phase2_full_run.py
  python phase1_phase2_full_run.py --save
"""

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Phase1/Phase2 一括実行（集計・メモ・アーカイブ・履歴表示）"
    )
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
        default="full",
        help="--save 時のタグ（default: full）",
    )
    parser.add_argument(
        "--history-tail",
        type=int,
        default=10,
        help="履歴表示の直近件数（default: 10）",
    )
    args = parser.parse_args()

    print(f"=== Phase1/Phase2 Full Run {datetime.now().strftime('%Y-%m-%d %H:%M')} ===\n")

    steps = []

    # 1. スナップショット（任意）
    if args.save:
        try:
            from phase1_save_run import snapshot_logs

            conv_path, refl_path = snapshot_logs(args.condition, args.tag)
            print(f"[1] Saved: {conv_path.name}, {refl_path.name}\n")
        except Exception as e:
            print(f"[1] Warn save_run: {e}\n")
        steps.append(1)
    else:
        steps.append(0)

    # 2. 集計
    try:
        from phase1_aggregate import main as aggregate_main

        aggregate_main()
        print()
    except Exception as e:
        print(f"[2] Error aggregate: {e}\n")
        sys.exit(1)
    steps.append(2)

    # 3. 低満足度集約
    try:
        from phase1_low_satisfaction import main as low_sat_main

        low_sat_main()
        print()
    except Exception as e:
        print(f"[3] Error low_satisfaction: {e}\n")
        sys.exit(1)
    steps.append(3)

    # 4. Phase2 バックフィル
    try:
        from phase2_backfill_memos import main as backfill_main

        backfill_main()
        print()
    except Exception as e:
        print(f"[4] Warn backfill: {e}\n")
    steps.append(4)

    # 5. Phase2 メモ自動整理（重複除去→ZIP退避）
    try:
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
    except Exception as e:
        print(f"[5] Warn phase2_auto_cleanup: {e}\n")
    steps.append(5)

    # 6. Phase2 メモ概要
    try:
        from phase2_memo_summary import main as memo_summary_main

        memo_summary_main()
        print()
    except Exception as e:
        print(f"[6] Warn memo_summary: {e}\n")
    steps.append(6)

    # 7. 低満足度アーカイブ
    try:
        from phase1_low_sat_archive import main as archive_main

        archive_main()
        print()
    except Exception as e:
        print(f"[7] Warn archive: {e}\n")
    steps.append(7)

    # 8. 履歴表示
    try:
        view_script = str(ROOT / "phase1_low_sat_history_view.py")
        out = subprocess.run(
            [sys.executable, view_script, "-n", str(args.history_tail)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=15,
        )
        print((out.stdout or "") + (out.stderr or ""))
    except Exception as e:
        print(f"[8] Warn history_view: {e}\n")
    steps.append(8)

    print("=== Full Run done ===")


if __name__ == "__main__":
    main()
