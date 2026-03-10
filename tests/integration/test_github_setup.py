#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub設定確認スクリプト
"""

import os
import sys
from pathlib import Path

# 標準出力のエンコーディングを設定
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]

# .envファイルの読み込み
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"[OK] .envファイルを読み込みました: {env_path}")
    else:
        print(f"[WARN] .envファイルが見つかりません: {env_path}")
except ImportError:
    print("[WARN] python-dotenvがインストールされていません")
    print("   インストール: pip install python-dotenv")

# PyGithubの確認
try:
    from github import Github
    print("[OK] PyGithub: インストール済み")
except ImportError:
    print("[ERROR] PyGithub: 未インストール")
    print("   インストール: pip install PyGithub")

# 環境変数の確認
token = os.getenv("GITHUB_TOKEN")
if token:
    print(f"[OK] GITHUB_TOKEN: 設定済み (長さ: {len(token)}文字)")
    print(f"   最初の10文字: {token[:10]}...")
    
    # GitHub接続テスト
    try:
        github = Github(token)  # type: ignore[possibly-unbound]
        user = github.get_user()
        print(f"[OK] GitHub接続成功: {user.login}")
    except Exception as e:
        print(f"[ERROR] GitHub接続エラー: {e}")
else:
    print("[ERROR] GITHUB_TOKEN: 未設定")
    print("\n設定方法:")
    print("1. .envファイルを作成して以下を追加:")
    print("   GITHUB_TOKEN=your_token_here")
    print("\n2. またはPowerShellで:")
    print("   $env:GITHUB_TOKEN = 'your_token_here'")

