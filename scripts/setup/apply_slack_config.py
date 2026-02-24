#!/usr/bin/env python3
"""
既存のSlack設定をNotification Hub Enhancedに適用
"""

import json
import re
from pathlib import Path

# 既存のSlack Webhook URLを取得
slack_webhook_url = None

# 1. SLACK_WEBHOOK_URL.mdから読み込み
slack_url_file = Path("SLACK_WEBHOOK_URL.md")
if slack_url_file.exists():
    content = slack_url_file.read_text(encoding='utf-8')
    match = re.search(r'https://hooks\.slack\.com/services/[^\s`]+', content)
    if match:
        slack_webhook_url = match.group(0)
        print(f"[OK] SLACK_WEBHOOK_URL.mdから取得: {slack_webhook_url[:50]}...")

# 2. notification_system_state.jsonから読み込み
if not slack_webhook_url:
    state_file = Path("notification_system_state.json")
    if state_file.exists():
        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
                slack_webhook_url = state.get("slack_webhook_url")
                if slack_webhook_url:
                    print(f"[OK] notification_system_state.jsonから取得: {slack_webhook_url[:50]}...")
        except Exception as e:
            print(f"[WARNING] notification_system_state.jsonの読み込みエラー: {e}")

# 3. 環境変数から読み込み
import os
if not slack_webhook_url:
    slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if slack_webhook_url:
        print(f"[OK] 環境変数から取得: {slack_webhook_url[:50]}...")

# Notification Hub Enhanced設定を更新
if slack_webhook_url:
    config_file = Path("notification_hub_enhanced_config.json")
    
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
    else:
        # デフォルト設定を作成
        config = {
            "slack_webhook_url": None,
            "telegram_bot_token": None,
            "telegram_chat_id": None,
            "email": {
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "username": None,
                "password": None,
                "from_address": None,
                "to_addresses": []
            },
            "rules": [
                {
                    "name": "Critical Alerts",
                    "priority": "critical",
                    "channels": ["slack", "telegram", "email"],
                    "conditions": {"status": "critical"},
                    "enabled": True
                },
                {
                    "name": "Device Offline",
                    "priority": "important",
                    "channels": ["slack", "telegram"],
                    "conditions": {"status": "offline"},
                    "enabled": True
                },
                {
                    "name": "Warning Alerts",
                    "priority": "normal",
                    "channels": ["slack"],
                    "conditions": {"status": "warning"},
                    "enabled": True
                }
            ],
            "history_file": "notification_history.json",
            "max_history": 1000
        }
    
    # Slack Webhook URLを設定
    config["slack_webhook_url"] = slack_webhook_url
    
    # 設定を保存
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print(f"[OK] Notification Hub Enhanced設定を更新しました")
    print(f"     Slack Webhook URL: {slack_webhook_url[:50]}...")
    
    # テスト通知を送信
    print("\nテスト通知を送信しますか？ (y/n): ", end="")
    test_response = input().strip().lower()
    
    if test_response == 'y':
        import requests
        try:
            payload = {
                "text": "✅ ManaOS通知システムの設定が完了しました！",
                "username": "ManaOS Notification"
            }
            response = requests.post(slack_webhook_url, json=payload, timeout=10)
            if response.status_code == 200:
                print("[OK] テスト通知が送信されました！")
            else:
                print(f"[WARNING] テスト通知の送信に失敗しました（ステータスコード: {response.status_code}）")
        except Exception as e:
            print(f"[ERROR] テスト通知の送信エラー: {e}")
else:
    print("[WARNING] Slack Webhook URLが見つかりませんでした")
    print("手動で設定する場合:")
    print("1. python setup_notifications.ps1 を実行")
    print("2. または notification_hub_enhanced_config.json を直接編集")

