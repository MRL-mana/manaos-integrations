#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
無料統合システムの動作確認スクリプト
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# .envファイルを読み込む
env_file = Path(".env")
if env_file.exists():
    load_dotenv(env_file)

print("=" * 70)
print("無料統合システムの動作確認")
print("=" * 70)
print()

# 無料統合システムのテスト
integrations_to_test = []

# 1. GitHub統合（無料）
print("[1] GitHub統合（無料）")
print("-" * 70)
try:
    from github_integration import GitHubIntegration
    gh = GitHubIntegration()
    if gh.is_available():
        print("  [OK] GitHub統合: 利用可能")
        integrations_to_test.append(("GitHub", gh))
    else:
        print("  [WARN] GitHub統合: 利用不可")
except Exception as e:
    print(f"  [ERROR] GitHub統合: {e}")

print()

# 2. CivitAI統合（無料）
print("[2] CivitAI統合（無料）")
print("-" * 70)
try:
    from civitai_integration import CivitAIIntegration
    civitai = CivitAIIntegration()
    if civitai.is_available():
        print("  [OK] CivitAI統合: 利用可能")
        integrations_to_test.append(("CivitAI", civitai))
    else:
        print("  [WARN] CivitAI統合: 利用不可")
except Exception as e:
    print(f"  [ERROR] CivitAI統合: {e}")

print()

# 3. Google Drive統合（無料）
print("[3] Google Drive統合（無料）")
print("-" * 70)
try:
    from google_drive_integration import GoogleDriveIntegration
    drive = GoogleDriveIntegration()
    if drive.is_available():
        print("  [OK] Google Drive統合: 利用可能")
        integrations_to_test.append(("Google Drive", drive))
    else:
        print("  [WARN] Google Drive統合: 利用不可")
except Exception as e:
    print(f"  [ERROR] Google Drive統合: {e}")

print()

# 4. Obsidian統合（無料、ローカル）
print("[4] Obsidian統合（無料、ローカル）")
print("-" * 70)
try:
    from obsidian_integration import ObsidianIntegration
    vault_path = os.getenv("OBSIDIAN_VAULT_PATH", "C:/Users/mana4/Documents/Obsidian Vault")
    obsidian = ObsidianIntegration(vault_path=vault_path)
    if obsidian.is_available():
        print("  [OK] Obsidian統合: 利用可能")
        integrations_to_test.append(("Obsidian", obsidian))
    else:
        print("  [WARN] Obsidian統合: 利用不可")
except Exception as e:
    print(f"  [ERROR] Obsidian統合: {e}")

print()

# 5. n8n統合（無料、ローカル）
print("[5] n8n統合（無料、ローカル）")
print("-" * 70)
try:
    from n8n_integration import N8NIntegration
    n8n = N8NIntegration()
    if n8n.is_available():
        print("  [OK] n8n統合: 利用可能")
        workflows = n8n.list_workflows()
        print(f"    ワークフロー数: {len(workflows)}件")
        integrations_to_test.append(("n8n", n8n))
    else:
        print("  [WARN] n8n統合: 利用不可（サーバー未起動またはAPIキー未設定）")
except Exception as e:
    print(f"  [ERROR] n8n統合: {e}")

print()

# 6. LangChain統合（無料、Ollama）
print("[6] LangChain統合（無料、Ollama）")
print("-" * 70)
try:
    from langchain_integration import LangChainIntegration
    langchain = LangChainIntegration()
    if langchain.is_available():
        print("  [OK] LangChain統合: 利用可能")
        integrations_to_test.append(("LangChain", langchain))
    else:
        print("  [WARN] LangChain統合: 利用不可（Ollama未起動）")
except Exception as e:
    print(f"  [ERROR] LangChain統合: {e}")

print()

# まとめ
print("=" * 70)
print("動作確認結果")
print("=" * 70)
print(f"利用可能な無料統合: {len(integrations_to_test)}件")

if integrations_to_test:
    print()
    print("利用可能な無料統合システム:")
    for name, _ in integrations_to_test:
        print(f"  - {name}")

print()
print("=" * 70)
print("完了")
print("=" * 70)
print()
print("注意: OpenAI APIは保留中のため、Mem0統合は無効化されています")






















