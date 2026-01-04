#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改善版統合クラスのテスト
"""

import sys
from pathlib import Path

print("=" * 60)
print("改善版統合クラスのテスト")
print("=" * 60)
print()

results = {}

# 1. ベースクラスのテスト
print("1. ベースクラスのテスト...")
try:
    from base_integration import BaseIntegration
    print("   ✅ ベースクラスのインポート成功")
    results["base_integration"] = True
except Exception as e:
    print(f"   ❌ ベースクラスのインポート失敗: {e}")
    results["base_integration"] = False
    sys.exit(1)

# 2. ComfyUI統合のテスト
print("\n2. ComfyUI統合のテスト...")
try:
    from comfyui_integration_improved import ComfyUIIntegration
    comfyui = ComfyUIIntegration()
    available = comfyui.is_available()
    status = comfyui.get_status()
    print(f"   ✅ ComfyUI統合の初期化成功")
    print(f"   - 利用可能: {available}")
    print(f"   - 状態: {status.get('health', {}).get('status', 'unknown')}")
    results["comfyui"] = True
except Exception as e:
    print(f"   ❌ ComfyUI統合のテスト失敗: {e}")
    results["comfyui"] = False

# 3. Google Drive統合のテスト
print("\n3. Google Drive統合のテスト...")
try:
    from google_drive_integration_improved import GoogleDriveIntegration
    drive = GoogleDriveIntegration()
    available = drive.is_available()
    status = drive.get_status()
    print(f"   ✅ Google Drive統合の初期化成功")
    print(f"   - 利用可能: {available}")
    print(f"   - 状態: {status.get('health', {}).get('status', 'unknown')}")
    results["google_drive"] = True
except Exception as e:
    print(f"   ❌ Google Drive統合のテスト失敗: {e}")
    results["google_drive"] = False

# 4. Obsidian統合のテスト
print("\n4. Obsidian統合のテスト...")
try:
    from obsidian_integration_improved import ObsidianIntegration
    import os
    vault_path = os.getenv("OBSIDIAN_VAULT_PATH", "C:/Users/mana4/Documents/Obsidian Vault")
    obsidian = ObsidianIntegration(vault_path)
    available = obsidian.is_available()
    status = obsidian.get_status()
    print(f"   ✅ Obsidian統合の初期化成功")
    print(f"   - 利用可能: {available}")
    print(f"   - 状態: {status.get('health', {}).get('status', 'unknown')}")
    results["obsidian"] = True
except Exception as e:
    print(f"   ❌ Obsidian統合のテスト失敗: {e}")
    results["obsidian"] = False

# 5. Mem0統合のテスト
print("\n5. Mem0統合のテスト...")
try:
    from mem0_integration_improved import Mem0Integration
    mem0 = Mem0Integration()
    available = mem0.is_available()
    status = mem0.get_status()
    print(f"   ✅ Mem0統合の初期化成功")
    print(f"   - 利用可能: {available}")
    print(f"   - 状態: {status.get('health', {}).get('status', 'unknown')}")
    results["mem0"] = True
except Exception as e:
    print(f"   ❌ Mem0統合のテスト失敗: {e}")
    results["mem0"] = False

# 6. CivitAI統合のテスト
print("\n6. CivitAI統合のテスト...")
try:
    from civitai_integration_improved import CivitAIIntegration
    civitai = CivitAIIntegration()
    available = civitai.is_available()
    status = civitai.get_status()
    print(f"   ✅ CivitAI統合の初期化成功")
    print(f"   - 利用可能: {available}")
    print(f"   - 状態: {status.get('health', {}).get('status', 'unknown')}")
    results["civitai"] = True
except Exception as e:
    print(f"   ❌ CivitAI統合のテスト失敗: {e}")
    results["civitai"] = False

# 7. GitHub統合のテスト
print("\n7. GitHub統合のテスト...")
try:
    from github_integration_improved import GitHubIntegration
    github = GitHubIntegration()
    available = github.is_available()
    status = github.get_status()
    print(f"   ✅ GitHub統合の初期化成功")
    print(f"   - 利用可能: {available}")
    print(f"   - 状態: {status.get('health', {}).get('status', 'unknown')}")
    results["github"] = True
except Exception as e:
    print(f"   ❌ GitHub統合のテスト失敗: {e}")
    results["github"] = False

# 結果サマリー
print("\n" + "=" * 60)
print("テスト結果サマリー")
print("=" * 60)

total = len(results)
passed = sum(1 for v in results.values() if v)
failed = total - passed

for name, result in results.items():
    status = "✅ 成功" if result else "❌ 失敗"
    print(f"{name}: {status}")

print(f"\n合計: {passed}/{total} 成功 ({passed/total*100:.1f}%)")

if failed == 0:
    print("\n🎉 すべてのテストが成功しました！")
    sys.exit(0)
else:
    print(f"\n⚠️ {failed}個のテストが失敗しました")
    sys.exit(1)

