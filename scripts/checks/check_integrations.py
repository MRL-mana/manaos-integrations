"""
統合システムの状態をチェックするスクリプト
"""

import os
import sys
from pathlib import Path

# パスを追加
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 60)
print("ManaOS統合システム - 状態チェック")
print("=" * 60)
print()

# 環境変数の読み込み
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print("[OK] 環境変数ファイルを読み込みました")
except ImportError:
    pass

print("\n[統合システムの状態]")
print("-" * 60)

# ComfyUI
try:
    from comfyui_integration import ComfyUIIntegration
    comfyui = ComfyUIIntegration()
    status = "[OK] 利用可能" if comfyui.is_available() else "[NG] 利用不可"
    print(f"ComfyUI: {status}")
except Exception as e:
    print(f"ComfyUI: [ERROR] エラー - {e}")

# Google Drive
try:
    from google_drive_integration import GoogleDriveIntegration
    drive = GoogleDriveIntegration()
    status = "[OK] 利用可能" if drive.is_available() else "[NG] 利用不可"
    print(f"Google Drive: {status}")
except Exception as e:
    print(f"Google Drive: [ERROR] エラー - {e}")

# CivitAI
try:
    from civitai_integration import CivitAIIntegration
    civitai = CivitAIIntegration(api_key=os.getenv("CIVITAI_API_KEY"))
    status = "[OK] 利用可能" if civitai.is_available() else "[NG] 利用不可"
    print(f"CivitAI: {status}")
except Exception as e:
    print(f"CivitAI: [ERROR] エラー - {e}")

# LangChain
try:
    from langchain_integration import LangChainIntegration
    langchain = LangChainIntegration()
    status = "[OK] 利用可能" if langchain.is_available() else "[NG] 利用不可"
    print(f"LangChain: {status}")
except Exception as e:
    print(f"LangChain: [ERROR] エラー - {e}")

# LangGraph
try:
    from langchain_integration import LangGraphIntegration
    langgraph = LangGraphIntegration()
    status = "[OK] 利用可能" if langgraph.is_available() else "[NG] 利用不可"
    print(f"LangGraph: {status}")
except Exception as e:
    print(f"LangGraph: [ERROR] エラー - {e}")

# Mem0
try:
    from mem0_integration import Mem0Integration
    mem0 = Mem0Integration()
    status = "[OK] 利用可能" if mem0.is_available() else "[NG] 利用不可"
    print(f"Mem0: {status}")
except Exception as e:
    print(f"Mem0: [ERROR] エラー - {e}")

# Obsidian
try:
    from obsidian_integration import ObsidianIntegration
    vault_path = os.getenv("OBSIDIAN_VAULT_PATH", "C:/Users/mana4/Documents/Obsidian Vault")
    obsidian = ObsidianIntegration(vault_path=vault_path)
    status = "[OK] 利用可能" if obsidian.is_available() else "[NG] 利用不可"
    print(f"Obsidian: {status}")
    if not obsidian.is_available():
        print(f"  Vaultパス: {vault_path}")
except Exception as e:
    print(f"Obsidian: [ERROR] エラー - {e}")

print("\n" + "=" * 60)

