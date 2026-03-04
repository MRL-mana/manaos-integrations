#!/usr/bin/env python3
"""
Slackに毎日自動ポスト - レミの外部モニタ
"""

import os
import json
import sys
import requests
from pathlib import Path
from datetime import date
from dotenv import load_dotenv

load_dotenv()

BASE = Path("/root/manaos_command_hub/dashboard")
WEBHOOK = os.getenv("SLACK_WEBHOOK_URL") or os.getenv("MANAOS_SLACK_WEBHOOK")


def read_file(name: str) -> str:
    """ダッシュボードファイルを読み込む"""
    p = BASE / name
    if p.exists():
        try:
            return p.read_text(encoding="utf-8")
        except Exception:
            return f"(読み込みエラー: {name})"
    return f"(まだ {name} が生成されていません)"


def main():
    if not WEBHOOK:
        print("Error: SLACK_WEBHOOK_URL or MANAOS_SLACK_WEBHOOK is not set in .env", file=sys.stderr)
        return

    today_str = date.today().isoformat()
    today = read_file("today.md")
    status = read_file("status.md")
    money = read_file("money.md")

    # Slackメッセージを構築
    text = f"*manaOS Daily Summary - {today_str}*\n\n"

    # 今日のミッション
    text += "*📋 今日のミッション*\n"
    text += "```\n" + today[:1800] + "\n```\n\n"

    # システム状態（簡潔版）
    status_lines = status.split("\n")[:30]  # 最初の30行だけ
    text += "*💻 システム状態*\n"
    text += "```\n" + "\n".join(status_lines)[:1800] + "\n```\n\n"

    # 今月の金脈候補
    text += "*💰 今月の金脈候補*\n"
    text += "```\n" + money[:1800] + "\n```"

    payload = {
        "text": text,
        "username": "manaOS",
        "icon_emoji": ":rocket:"
    }

    try:
        response = requests.post(WEBHOOK, json=payload, timeout=10)
        response.raise_for_status()
        print(f"✅ Posted to Slack successfully. Status: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Error posting to Slack: {e}", file=sys.stderr)
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()








