#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
提供された情報を使って自動設定するスクリプト
"""

import os
from pathlib import Path


def check_current_settings():
    """現在の設定を確認"""
    print("=" * 70)
    print("現在の設定確認")
    print("=" * 70)
    print()

    # .envファイルから環境変数を読み込む
    try:
        from dotenv import load_dotenv
        env_file = Path(".env")
        if env_file.exists():
            load_dotenv(env_file)
    except ImportError:
        pass

    env_vars = [
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
        "OLLAMA_MODEL"
    ]

    configured = []
    unconfigured = []

    for var in env_vars:
        value = os.getenv(var)
        if value:
            configured.append(var)
            print(f"  [OK] {var}: 設定済み")
        else:
            unconfigured.append(var)
            print(f"  [WARN] {var}: 未設定")

    print()
    print(f"設定済み: {len(configured)}件")
    print(f"未設定: {len(unconfigured)}件")

    return configured, unconfigured


def main():
    """メイン処理"""
    print("=" * 70)
    print("設定状況チェック（Secretsは自動抽出しません）")
    print("=" * 70)
    print()

    # 現在の設定を確認
    print("[1] 現在の設定を確認中...")
    print("-" * 70)
    _, unconfigured = check_current_settings()

    if unconfigured:
        print()
        print("-" * 70)
        print("不足しているものは、次のどちらかで設定してください:")
        print("  - OS環境変数（CI/本番向け）")
        print("  - ローカルの `.env`（コミット禁止）")

    print()
    print("=" * 70)
    print("完了")
    print("=" * 70)


if __name__ == "__main__":
    main()