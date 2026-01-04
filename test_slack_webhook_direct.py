#!/usr/bin/env python3
"""Slack Webhook直接送信テスト"""

import json
import requests

# 設定ファイルからWebhook URLを読み込み
with open("notification_hub_enhanced_config.json", "r", encoding="utf-8") as f:
    config = json.load(f)
    webhook_url = config.get("slack_webhook_url", "")

if not webhook_url:
    print("❌ Slack Webhook URLが設定されていません")
    exit(1)

print("=" * 60)
print("Slack Webhook直接送信テスト")
print("=" * 60)
print(f"Webhook URL: {webhook_url[:50]}...")
print()

# テストメッセージ
test_message = "🤖 Slack Integrationテスト: こんにちは！会話機能が動作しています。"

try:
    payload = {"text": test_message}
    response = requests.post(webhook_url, json=payload, timeout=10)
    
    print(f"ステータスコード: {response.status_code}")
    print(f"レスポンス: {response.text}")
    
    if response.status_code == 200:
        print("\n✅ Slack Webhook送信成功！")
        print("Slackチャンネルを確認してください。")
    else:
        print(f"\n❌ Slack Webhook送信失敗: {response.status_code}")
        print(f"エラー: {response.text}")
        
except Exception as e:
    print(f"\n❌ エラー: {e}")

print("\n" + "=" * 60)

