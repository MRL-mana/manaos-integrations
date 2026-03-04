#!/usr/bin/env python3
"""
Obsidian自動同期スケジューラー
定期的にホットメモリからObsidianへ同期

実行タイミング:
- 重要度9以上: リアルタイム（即座に実行）
- 重要度7-8: 毎時間バッチ処理
- 日次ノート: 毎日0時
"""

import time
import subprocess
import logging
from datetime import datetime
from pathlib import Path

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/root/.mana_memory/auto_sync_scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

SYNC_SCRIPT = Path("/root/.mana_memory/obsidian_sync.py")
STATE_FILE = Path("/root/.mana_memory/sync_scheduler_state.json")


def run_sync(mode: str = "normal"):
    """同期を実行"""
    try:
        if mode == "realtime":
            cmd = ["python3", str(SYNC_SCRIPT), "--realtime"]
        elif mode == "daily":
            cmd = ["python3", str(SYNC_SCRIPT), "--daily-only"]
        else:
            cmd = ["python3", str(SYNC_SCRIPT)]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode == 0:
            logger.info(f"✅ 同期成功 ({mode})")
            return True
        else:
            logger.error(f"❌ 同期失敗 ({mode}): {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"❌ 同期実行エラー ({mode}): {e}")
        return False


def check_realtime_sync():
    """リアルタイム同期チェック（重要度9以上）"""
    # この関数は、新しい記憶が追加されたときに呼ばれる想定
    # 実際の実装では、データベースの変更を監視する必要がある
    pass


def main():
    """メインループ（デーモンモード）"""
    import argparse

    parser = argparse.ArgumentParser(description='Obsidian自動同期スケジューラー')
    parser.add_argument('--daemon', action='store_true', help='デーモンモードで実行')
    parser.add_argument('--once', action='store_true', help='1回だけ実行')
    parser.add_argument('--realtime', action='store_true', help='リアルタイムモード')
    parser.add_argument('--daily', action='store_true', help='日次ノートのみ')
    args = parser.parse_args()

    if args.once:
        # 1回だけ実行
        mode = "realtime" if args.realtime else ("daily" if args.daily else "normal")
        run_sync(mode)
        return

    if args.daemon:
        # デーモンモード
        logger.info("🔄 デーモンモードで開始")

        last_hourly_sync = None
        last_daily_sync = None

        while True:
            now = datetime.now()

            # 毎時間: 重要度7-8のバッチ処理
            if last_hourly_sync is None or (now - last_hourly_sync).seconds >= 3600:
                logger.info("⏰ 毎時間同期実行")
                run_sync("normal")
                last_hourly_sync = now

            # 毎日0時: 日次ノート生成
            if now.hour == 0 and (last_daily_sync is None or last_daily_sync.date() != now.date()):
                logger.info("📅 日次ノート生成")
                run_sync("daily")
                last_daily_sync = now

            # リアルタイム同期（重要度9以上）
            # 実際の実装では、データベースの変更を監視する必要がある
            # ここでは簡易的に5分ごとにチェック
            if now.minute % 5 == 0:
                run_sync("realtime")

            time.sleep(60)  # 1分ごとにチェック
    else:
        # 通常モード（1回実行）
        mode = "realtime" if args.realtime else ("daily" if args.daily else "normal")
        run_sync(mode)


if __name__ == '__main__':
    main()









