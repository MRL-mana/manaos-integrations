#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Slack CLI ヘルパー
Slack通知をCLIから送信
"""

import os
import sys
import argparse
import requests


def send_message(args):
    """メッセージを送信"""
    webhook_url = args.webhook_url or os.getenv("SLACK_WEBHOOK_URL", "")
    
    if not webhook_url:
        print("❌ SLACK_WEBHOOK_URLが設定されていません")
        print("   環境変数を設定するか、--webhook-urlを指定してください")
        return 1
    
    # メッセージ読み込み
    if args.file:
        with open(args.file, 'r', encoding='utf-8') as f:
            message = f.read()
    elif args.message:
        message = args.message
    else:
        print("❌ --message または --file を指定してください")
        return 1
    
    # ペイロード作成
    payload = {
        "text": message,
        "username": args.username or "ManaOS CLI",
        "icon_emoji": args.icon or ":memo:"
    }
    
    if args.channel:
        payload["channel"] = args.channel
    
    # 送信
    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        
        if response.status_code == 200:
            print("✅ Slack通知送信完了")
            return 0
        else:
            print(f"❌ Slack通知送信失敗: HTTP {response.status_code}")
            print(f"   レスポンス: {response.text}")
            return 1
    except Exception as e:
        print(f"❌ Slack通知送信エラー: {e}")
        return 1


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description="Slack CLI ヘルパー")
    parser.add_argument(
        "--webhook-url",
        help="Slack Webhook URL（デフォルト: 環境変数SLACK_WEBHOOK_URL）"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="コマンド")
    
    # send コマンド
    send_parser = subparsers.add_parser("send", help="メッセージを送信")
    send_parser.add_argument("--message", help="メッセージ内容")
    send_parser.add_argument("--file", help="メッセージファイル")
    send_parser.add_argument("--channel", help="チャンネル名（オプション）")
    send_parser.add_argument("--username", help="ユーザー名（デフォルト: ManaOS CLI）")
    send_parser.add_argument("--icon", help="アイコン絵文字（デフォルト: :memo:）")
    send_parser.set_defaults(func=send_message)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
