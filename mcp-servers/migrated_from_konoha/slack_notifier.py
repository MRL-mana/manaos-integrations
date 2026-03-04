#!/usr/bin/env python3
"""
manaOS Command Hub - Slack通知機能

コマンド実行結果やエラーをSlackに通知する
"""

import json
import requests
import os
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv
import logging

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")


def send_slack_message(
    text: str,
    title: Optional[str] = None,
    color: str = "good",  # good, warning, danger
    fields: Optional[list] = None
) -> bool:
    """Slackにメッセージを送信"""
    if not SLACK_WEBHOOK_URL:
        logger.warning("SLACK_WEBHOOK_URL is not set, skipping Slack notification")
        return False

    try:
        attachments = [{
            "color": color,
            "text": text
        }]

        if title:
            attachments[0]["title"] = title

        if fields:
            attachments[0]["fields"] = fields

        payload = {
            "attachments": attachments
        }

        response = requests.post(
            SLACK_WEBHOOK_URL,
            json=payload,
            timeout=10
        )
        response.raise_for_status()

        logger.info("✅ Slack notification sent")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to send Slack notification: {e}")
        return False


def notify_command_success(command_name: str, result: Dict[str, Any]):
    """コマンド成功を通知"""
    text = f"✅ Command executed successfully: `{command_name}`"

    fields = []
    if "action" in result:
        fields.append({
            "title": "Action",
            "value": result["action"],
            "short": True
        })

    if "path" in result:
        fields.append({
            "title": "Path",
            "value": result["path"],
            "short": True
        })

    if "commit_sha" in result:
        fields.append({
            "title": "Commit SHA",
            "value": result["commit_sha"][:8],
            "short": True
        })

    send_slack_message(
        text=text,
        title="manaOS Command Hub",
        color="good",
        fields=fields
    )


def notify_command_error(command_name: str, error: str):
    """コマンドエラーを通知"""
    send_slack_message(
        text=f"❌ Command failed: `{command_name}`\n```{error}```",
        title="manaOS Command Hub - Error",
        color="danger"
    )


def notify_daily_summary(success_count: int, total_count: int, summary: str):
    """毎日の自動実行サマリーを通知"""
    color = "good" if success_count == total_count else "warning"

    fields = [
        {
            "title": "Success",
            "value": f"{success_count}/{total_count}",
            "short": True
        }
    ]

    send_slack_message(
        text=f"📊 Daily commands execution completed\n\n{summary}",
        title="manaOS Command Hub - Daily Summary",
        color=color,
        fields=fields
    )


def notify_weekly_summary(summary_path: str):
    """週次まとめ生成完了を通知"""
    send_slack_message(
        text=f"📅 Weekly summary generated\n`{summary_path}`",
        title="manaOS Command Hub - Weekly Summary",
        color="good"
    )


def notify_monthly_summary(summary_path: str):
    """月次まとめ生成完了を通知"""
    send_slack_message(
        text=f"📅 Monthly summary generated\n`{summary_path}`",
        title="manaOS Command Hub - Monthly Summary",
        color="good"
    )


if __name__ == "__main__":
    # テスト実行
    if SLACK_WEBHOOK_URL:
        send_slack_message(
            text="🧪 Test notification from manaOS Command Hub",
            title="Test",
            color="good"
        )
        print("✅ Test notification sent")
    else:
        print("⚠️ SLACK_WEBHOOK_URL is not set")








