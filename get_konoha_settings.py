#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
このはサーバーから設定を取得するスクリプト
"""

import subprocess
import os
from pathlib import Path

def get_konoha_env_vars():
    """このはサーバーから環境変数を取得"""
    print("=" * 70)
    print("このはサーバーから環境変数を取得")
    print("=" * 70)
    print()
    print("以下のコマンドをこのはサーバーで実行してください:")
    print()
    print("ssh konoha")
    print("cat /root/.env")
    print("env | grep -E '(API|TOKEN|KEY|SECRET)'")
    print()
    print("または、以下のコマンドで.envファイルをコピー:")
    print()
    print("scp konoha:/root/.env C:\\Users\\mana4\\Desktop\\manaos_integrations\\.env.konoha")
    print()

def get_konoha_n8n_api_key():
    """このはサーバーのn8nからAPIキーを取得"""
    print("=" * 70)
    print("このはサーバーのn8nからAPIキーを取得")
    print("=" * 70)
    print()
    print("方法1: Web UIから取得（推奨）")
    print("1. ブラウザで http://100.93.120.33:5678 にアクセス")
    print("2. Settings → API → Create API Key")
    print("3. APIキーをコピー")
    print()
    print("方法2: SSH経由で確認")
    print("ssh konoha")
    print("docker exec trinity-n8n env | grep -i api")
    print()

def check_local_settings():
    """ローカルの設定を確認"""
    print("=" * 70)
    print("ローカルの設定確認")
    print("=" * 70)
    print()
    
    # .envファイルから環境変数を読み込む
    try:
        from dotenv import load_dotenv
        env_file = Path(".env")
        if env_file.exists():
            load_dotenv(env_file)
            print(f"[OK] .envファイルが存在します: {env_file.absolute()}")
        else:
            print(f"[WARN] .envファイルが存在しません: {env_file.absolute()}")
    except ImportError:
        print("[WARN] python-dotenvがインストールされていません")
    
    print()
    print("現在の環境変数設定:")
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
    
    for var in env_vars:
        value = os.getenv(var)
        if value:
            print(f"  [OK] {var}: 設定済み")
        else:
            print(f"  [WARN] {var}: 未設定")

def main():
    """メイン処理"""
    print()
    get_konoha_env_vars()
    print()
    get_konoha_n8n_api_key()
    print()
    check_local_settings()
    print()
    print("=" * 70)
    print("次のステップ")
    print("=" * 70)
    print()
    print("1. このはサーバーから環境変数を取得")
    print("2. .envファイルに追加")
    print("3. n8n APIキーを設定（必要に応じて）")
    print("4. 動作確認")
    print()

if __name__ == "__main__":
    main()

