#!/usr/bin/env python3
"""
manaOS Command Hub - 毎日の自動実行スクリプト

dev_qa.md、strategy.md、daily-log を自動で更新する
cronで毎日実行されることを想定
"""

import subprocess
import sys
import json
from pathlib import Path
from datetime import date, datetime
import logging

# Slack通知（オプション）
try:
    from slack_notifier import notify_daily_summary
    SLACK_AVAILABLE = True
except ImportError:
    SLACK_AVAILABLE = False

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/root/manaos_command_hub/logs/daily-run.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BASE = Path("/root/manaos_command_hub")
COMMANDS_DIR = BASE / "commands"
SEND_CMD = ["python3", str(BASE / "send_command.py")]


def run_command(json_name: str) -> bool:
    """コマンドJSONを実行"""
    json_path = COMMANDS_DIR / json_name

    if not json_path.exists():
        logger.error(f"❌ JSON file not found: {json_path}")
        return False

    try:
        logger.info(f"📝 Running: {json_name}")
        result = subprocess.run(
            SEND_CMD + [str(json_path)],
            capture_output=True,
            text=True,
            timeout=60,
            check=True
        )
        logger.info(f"✅ Success: {json_name}")
        if result.stdout:
            logger.debug(f"Output: {result.stdout}")
        return True
    except subprocess.TimeoutExpired:
        logger.error(f"❌ Timeout: {json_name}")
        return False
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Failed: {json_name}")
        logger.error(f"Error: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error: {json_name} - {e}")
        return False


def update_log_command_with_date():
    """日付付きログコマンドJSONを動的に生成"""
    today = date.today()
    log_file = f"logs/daily-{today.strftime('%Y-%m-%d')}.log"

    # 既存のログファイルを読み込んで、今日の内容を確認
    log_path = Path(f"/root/{log_file}")
    existing_content = ""
    if log_path.exists():
        existing_content = log_path.read_text(encoding="utf-8")

    # 今日の日付セクションが既にあるかチェック
    today_marker = f"[{today.strftime('%Y-%m-%d')}]"
    if today_marker in existing_content:
        logger.info(f"ℹ️ Today's log already exists: {log_file}")
        return None  # 既に今日のログがある場合はスキップ

    # 動的にJSONコマンドを生成
    command = {
        "task": "file_write",
        "meta": {
            "caller": "remi",
            "reason": "1日の実績ログを追記（自動実行）"
        },
        "params": {
            "relative_path": log_file,
            "content": f"\n{today_marker} 自動実行ログ\n",
            "mode": "append"
        },
        "auth_token": "manaos-secret-token-please-change"
    }

    # 一時ファイルに保存
    temp_json = BASE / "commands" / f"command-log-{today.strftime('%Y%m%d')}.json"
    temp_json.write_text(json.dumps(command, indent=2, ensure_ascii=False), encoding="utf-8")

    return str(temp_json)


def main():
    """メイン処理"""
    logger.info("🚀 Daily commands execution started")
    logger.info(f"Date: {date.today()}")

    results = {
        "devqa": False,
        "strategy": False,
        "log": False
    }

    # 1. dev_qa.md に追記
    logger.info("=" * 50)
    logger.info("Step 1: Updating dev_qa.md")
    logger.info("=" * 50)
    results["devqa"] = run_command("command-devqa-append.json")

    # 2. strategy.md に追記
    logger.info("=" * 50)
    logger.info("Step 2: Updating strategy.md")
    logger.info("=" * 50)
    results["strategy"] = run_command("command-strategy-append.json")

    # 3. 日付付きログに追記
    logger.info("=" * 50)
    logger.info("Step 3: Updating daily log")
    logger.info("=" * 50)
    log_json = update_log_command_with_date()
    if log_json:
        results["log"] = run_command(Path(log_json).name)
    else:
        logger.info("ℹ️ Log already exists for today, skipping")
        results["log"] = True  # スキップは成功として扱う

    # 結果サマリー
    logger.info("=" * 50)
    logger.info("📊 Execution Summary")
    logger.info("=" * 50)
    logger.info(f"dev_qa.md: {'✅' if results['devqa'] else '❌'}")
    logger.info(f"strategy.md: {'✅' if results['strategy'] else '❌'}")
    logger.info(f"daily log: {'✅' if results['log'] else '❌'}")

    success_count = sum(1 for v in results.values() if v)
    total_count = len(results)

    if success_count == total_count:
        logger.info(f"🎉 All commands executed successfully ({success_count}/{total_count})")
        summary_text = f"All {total_count} commands executed successfully"
    else:
        logger.warning(f"⚠️ Some commands failed ({success_count}/{total_count})")
        summary_text = f"{success_count}/{total_count} commands succeeded"

    # Slack通知（オプション）
    if SLACK_AVAILABLE:
        try:
            notify_daily_summary(success_count, total_count, summary_text)
        except Exception as e:
            logger.warning(f"Failed to send Slack notification: {e}")

    return 0 if success_count == total_count else 1


if __name__ == "__main__":
    sys.exit(main())

