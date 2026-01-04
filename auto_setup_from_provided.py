#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
提供された情報を使って自動設定するスクリプト
"""

import os
from pathlib import Path
from typing import Dict, List

def get_provided_credentials() -> Dict[str, str]:
    """提供された認証情報を取得"""
    credentials = {}
    
    # test_comfyui_civitai.pyからCivitAI APIキーを取得
    civitai_file = Path("test_comfyui_civitai.py")
    if civitai_file.exists():
        try:
            with open(civitai_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # CivitAI APIキーを検索
                if "9d0afbe6cb2ad5d2c75080f2800dab3b" in content:
                    credentials["CIVITAI_API_KEY"] = "9d0afbe6cb2ad5d2c75080f2800dab3b"
                    print("[OK] CivitAI APIキーを発見: test_comfyui_civitai.py")
        except Exception as e:
            print(f"[WARN] test_comfyui_civitai.pyの読み込みに失敗: {e}")
    
    # GitHubトークン（既に設定済み）
    if os.getenv("GITHUB_TOKEN"):
        credentials["GITHUB_TOKEN"] = os.getenv("GITHUB_TOKEN")
        print("[OK] GitHubトークンは既に設定済み")
    
    return credentials

def update_env_file(credentials: Dict[str, str]) -> bool:
    """.envファイルを更新"""
    env_file = Path(".env")
    
    # .envファイルを読み込む
    env_vars = {}
    if env_file.exists():
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
        except Exception as e:
            print(f"[WARN] .envファイルの読み込みに失敗: {e}")
            return False
    
    # 提供された認証情報を追加/更新
    updated = False
    for key, value in credentials.items():
        if key not in env_vars or env_vars[key] != value:
            env_vars[key] = value
            updated = True
            print(f"[OK] {key}を設定しました")
    
    # .envファイルに書き込む
    if updated:
        try:
            with open(env_file, 'w', encoding='utf-8') as f:
                # 既存の設定を書き込む
                for key, value in env_vars.items():
                    f.write(f"{key}={value}\n")
            print(f"[OK] .envファイルを更新しました: {env_file.absolute()}")
            return True
        except Exception as e:
            print(f"[ERROR] .envファイルの書き込みに失敗: {e}")
            return False
    
    return False

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
    print("提供された情報から自動設定")
    print("=" * 70)
    print()
    
    # 提供された認証情報を取得
    print("[1] 提供された認証情報を検索中...")
    print("-" * 70)
    credentials = get_provided_credentials()
    
    if not credentials:
        print("[INFO] 提供された認証情報が見つかりませんでした")
    else:
        print(f"[OK] {len(credentials)}件の認証情報を発見しました")
    
    print()
    
    # 現在の設定を確認
    print("[2] 現在の設定を確認中...")
    print("-" * 70)
    configured, unconfigured = check_current_settings()
    
    print()
    
    # .envファイルを更新
    if credentials:
        print("[3] .envファイルを更新中...")
        print("-" * 70)
        updated = update_env_file(credentials)
        
        if updated:
            print()
            print("[4] 更新後の設定を確認中...")
            print("-" * 70)
            check_current_settings()
        else:
            print("[INFO] 更新する項目がありませんでした")
    else:
        print("[INFO] 設定する認証情報がありませんでした")
    
    print()
    print("=" * 70)
    print("完了")
    print("=" * 70)

if __name__ == "__main__":
    main()

