#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通知システムテストスクリプト
"""

import json
import sys
import io

# 標準出力のエンコーディングを設定
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from notification_hub_enhanced import NotificationHubEnhanced

print("=== 通知システムテスト ===")
print("")

# Notification Hub Enhancedを初期化
hub = NotificationHubEnhanced()

# 設定を確認
print("設定確認:")
print(f"  Slack Webhook URL: {'設定済み' if hub.slack_webhook_url else '未設定'}")
print(f"  Telegram Bot Token: {'設定済み' if hub.telegram_bot_token else '未設定'}")
print(f"  メール設定: {'設定済み' if hub.email_config.get('username') else '未設定'}")
print("")

# テスト通知を送信
if hub.slack_webhook_url:
    print("Slackテスト通知を送信中...")
    result = hub.send_notification(
        "ManaOS通知システムのテスト通知です",
        priority="normal",
        context={"test": True}
    )
    
    if result:
        print("[OK] テスト通知が送信されました！")
    else:
        print("[ERROR] テスト通知の送信に失敗しました")
else:
    print("[WARNING] Slack Webhook URLが設定されていません")
    print("   python apply_slack_config.py を実行してください")

# 統計を表示
print("")
print("通知統計:")
stats = hub.get_stats()
print(json.dumps(stats, indent=2, ensure_ascii=False))

