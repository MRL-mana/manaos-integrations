#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
このはサーバーから取得した設定の確認
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# .envファイルを読み込む
env_file = Path(".env")
if env_file.exists():
    load_dotenv(env_file)

print("=" * 70)
print("このはサーバーから取得した設定の確認")
print("=" * 70)
print()

important_vars = [
    "OPENAI_API_KEY",
    "N8N_API_KEY",
    "GITHUB_PERSONAL_ACCESS_TOKEN",
    "ANTHROPIC_API_KEY",
    "GEMINI_API_KEY",
    "STRIPE_SECRET_KEY",
    "TELEGRAM_BOT_TOKEN",
    "HUGGINGFACE_HUB_TOKEN",
]

print("重要な環境変数:")
for var in important_vars:
    value = os.getenv(var)
    if value:
        # セキュリティのため、値の一部のみ表示
        if len(value) > 20:
            display_value = value[:10] + "..." + value[-5:]
        else:
            display_value = value
        print(f"  [OK] {var}: {display_value}")
    else:
        print(f"  [WARN] {var}: 未設定")

print()
print("=" * 70)
print("設定状況サマリー")
print("=" * 70)

all_vars = [
    "GITHUB_TOKEN",
    "CIVITAI_API_KEY",
    "OPENAI_API_KEY",
    "SLACK_WEBHOOK_URL",
    "SLACK_VERIFICATION_TOKEN",
    "ROWS_API_KEY",
    "GOOGLE_DRIVE_CREDENTIALS",
    "GOOGLE_DRIVE_TOKEN",
    "OBSIDIAN_VAULT_PATH",
    "OLLAMA_URL",
    "OLLAMA_MODEL",
    "N8N_API_KEY",
    "ANTHROPIC_API_KEY",
    "GEMINI_API_KEY",
    "STRIPE_SECRET_KEY",
]

configured = [var for var in all_vars if os.getenv(var)]
unconfigured = [var for var in all_vars if not os.getenv(var)]

print(f"設定済み: {len(configured)}件")
print(f"未設定: {len(unconfigured)}件")

if configured:
    print()
    print("設定済みの環境変数:")
    for var in configured:
        print(f"  - {var}")

if unconfigured:
    print()
    print("未設定の環境変数:")
    for var in unconfigured:
        print(f"  - {var}")

