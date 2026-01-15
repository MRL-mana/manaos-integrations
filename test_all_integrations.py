#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全統合システムの動作確認スクリプト
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# .envファイルを読み込む
env_file = Path(".env")
if env_file.exists():
    load_dotenv(env_file)

print("=" * 70)
print("全統合システムの動作確認")
print("=" * 70)
print()

# 有料APIの警告
print("[!] 有料APIの警告")
print("-" * 70)
paid_apis = []
if os.getenv("OPENAI_API_KEY"):
    paid_apis.append("OpenAI API (Mem0統合)")
if os.getenv("ANTHROPIC_API_KEY"):
    paid_apis.append("Anthropic API")
if os.getenv("STRIPE_SECRET_KEY"):
    paid_apis.append("Stripe決済")

if paid_apis:
    print("以下のAPIは有料です。使用時に料金が発生する可能性があります:")
    for api in paid_apis:
        print(f"  - {api}")
else:
    print("有料APIは設定されていません")

print()

# 統合システムのテスト
integrations_to_test = []

# 1. GitHub統合
print("[1] GitHub統合")
print("-" * 70)
try:
    from github_integration import GitHubIntegration
    gh = GitHubIntegration()
    if gh.is_available():
        print("  [OK] GitHub統合: 利用可能")
        integrations_to_test.append(("GitHub", gh))
    else:
        print("  [WARN] GitHub統合: 利用不可（トークン未設定）")
except Exception as e:
    print(f"  [ERROR] GitHub統合: {e}")

print()

# 2. CivitAI統合
print("[2] CivitAI統合")
print("-" * 70)
try:
    from civitai_integration import CivitAIIntegration
    civitai = CivitAIIntegration()
    if civitai.is_available():
        print("  [OK] CivitAI統合: 利用可能")
        integrations_to_test.append(("CivitAI", civitai))
    else:
        print("  [WARN] CivitAI統合: 利用不可（APIキー未設定）")
except Exception as e:
    print(f"  [ERROR] CivitAI統合: {e}")

print()

# 3. Mem0統合（有料API）
print("[3] Mem0統合（OpenAI API使用 - 有料）")
print("-" * 70)
try:
    from mem0_integration import Mem0Integration
    mem0 = Mem0Integration()
    if mem0.is_available():
        print("  [OK] Mem0統合: 利用可能")
        print("  [!] 注意: OpenAI APIは有料です")
        integrations_to_test.append(("Mem0", mem0))
    else:
        print("  [WARN] Mem0統合: 利用不可（OpenAI APIキー未設定）")
except Exception as e:
    print(f"  [ERROR] Mem0統合: {e}")

print()

# 4. Google Drive統合
print("[4] Google Drive統合")
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

# 5. Obsidian統合
print("[5] Obsidian統合")
print("-" * 70)
try:
    from obsidian_integration import ObsidianIntegration
    vault_path = os.getenv("OBSIDIAN_VAULT_PATH", "C:/Users/mana4/Documents/Obsidian Vault")
    obsidian = ObsidianIntegration(vault_path=vault_path)
    if obsidian.is_available():
        print("  [OK] Obsidian統合: 利用可能")
        integrations_to_test.append(("Obsidian", obsidian))
    else:
        print("  [WARN] Obsidian統合: 利用不可（Vaultパス未設定）")
except Exception as e:
    print(f"  [ERROR] Obsidian統合: {e}")

print()

# 6. ComfyUI統合
print("[6] ComfyUI統合")
print("-" * 70)
try:
    from comfyui_integration import ComfyUIIntegration
    comfyui_url = os.getenv("COMFYUI_URL", "http://localhost:8188")
    comfyui = ComfyUIIntegration(base_url=comfyui_url)
    if comfyui.is_available():
        print(f"  [OK] ComfyUI統合: 利用可能 ({comfyui_url})")
        integrations_to_test.append(("ComfyUI", comfyui))
    else:
        print(f"  [WARN] ComfyUI統合: 利用不可（サーバー未起動: {comfyui_url}）")
except Exception as e:
    print(f"  [ERROR] ComfyUI統合: {e}")

print()

# 7. ManaOS Complete Integration
print("[7] ManaOS Complete Integration")
print("-" * 70)
try:
    from manaos_complete_integration import ManaOSCompleteIntegration
    integration = ManaOSCompleteIntegration()
    status = integration.get_complete_status()
    
    print("  [OK] ManaOS Complete Integration: 初期化完了")
    
    # 各システムの状態を表示
    if "rag_memory" in status:
        print(f"    - RAG Memory: {'利用可能' if status['rag_memory'].get('available') else '利用不可'}")
    if "learning_system" in status:
        print(f"    - Learning System: {'利用可能' if status['learning_system'].get('available') else '利用不可'}")
    if "personality_system" in status:
        print(f"    - Personality System: {'利用可能' if status['personality_system'].get('available') else '利用不可'}")
    if "autonomy_system" in status:
        print(f"    - Autonomy System: {'利用可能' if status['autonomy_system'].get('available') else '利用不可'}")
    if "secretary_system" in status:
        print(f"    - Secretary System: {'利用可能' if status['secretary_system'].get('available') else '利用不可'}")
    if "github_integration" in status:
        gh_status = status.get("github", {}).get("github_integration", {})
        print(f"    - GitHub Integration: {'利用可能' if gh_status.get('available') else '利用不可'}")
    
    integrations_to_test.append(("ManaOS Complete Integration", integration))
except Exception as e:
    print(f"  [ERROR] ManaOS Complete Integration: {e}")

print()

# まとめ
print("=" * 70)
print("動作確認結果")
print("=" * 70)
print(f"利用可能な統合: {len(integrations_to_test)}件")

if integrations_to_test:
    print()
    print("利用可能な統合システム:")
    for name, _ in integrations_to_test:
        print(f"  - {name}")

print()
print("=" * 70)
print("完了")
print("=" * 70)






















