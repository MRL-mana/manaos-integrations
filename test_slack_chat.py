#!/usr/bin/env python3
"""Slack会話機能のテスト"""

import requests
import json

# テスト用のWebhookエンドポイント
url = "http://127.0.0.1:5114/api/slack/webhook"

# テストデータ
test_cases = [
    {
        "text": "こんにちは",
        "user": "test_user",
        "channel": "test_channel"
    },
    {
        "text": "元気？",
        "user": "test_user",
        "channel": "test_channel"
    }
]

print("=" * 60)
print("Slack会話機能テスト")
print("=" * 60)

for i, test in enumerate(test_cases, 1):
    print(f"\n[{i}] テスト: {test['text']}")
    try:
        response = requests.post(url, json=test, timeout=30)
        print(f"  ステータスコード: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"  結果: {json.dumps(result, indent=2, ensure_ascii=False)}")
        else:
            print(f"  エラー: {response.text[:200]}")
    except Exception as e:
        print(f"  エラー: {e}")

print("\n" + "=" * 60)
print("テスト完了")
print("=" * 60)
