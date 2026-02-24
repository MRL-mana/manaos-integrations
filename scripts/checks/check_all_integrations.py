"""
すべての統合の状態を確認
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

print("=" * 60)
print("ManaOS統合システム - 統合状態確認")
print("=" * 60)
print()

integrations_status = {}

# 統一記憶システム
try:
    from memory_unified import UnifiedMemory
    integrations_status["memory_unified"] = "OK"
    print("[OK] 統一記憶システム")
except Exception as e:
    integrations_status["memory_unified"] = f"ERROR: {e}"
    print(f"[ERROR] 統一記憶システム: {e}")

# LLMルーティング
try:
    from llm_routing import LLMRouter
    integrations_status["llm_routing"] = "OK"
    print("[OK] LLMルーティング")
except Exception as e:
    integrations_status["llm_routing"] = f"ERROR: {e}"
    print(f"[ERROR] LLMルーティング: {e}")

# GitHub統合
try:
    from github_integration import GitHubIntegration
    integrations_status["github"] = "OK"
    print("[OK] GitHub統合")
except Exception as e:
    integrations_status["github"] = f"ERROR: {e}"
    print(f"[ERROR] GitHub統合: {e}")

# 通知ハブ
try:
    from notification_hub import NotificationHub
    integrations_status["notification_hub"] = "OK"
    print("[OK] 通知ハブ")
except Exception as e:
    integrations_status["notification_hub"] = f"ERROR: {e}"
    print(f"[ERROR] 通知ハブ: {e}")

# 秘書機能
try:
    from secretary_routines import SecretaryRoutines
    integrations_status["secretary"] = "OK"
    print("[OK] 秘書機能")
except Exception as e:
    integrations_status["secretary"] = f"ERROR: {e}"
    print(f"[ERROR] 秘書機能: {e}")

# 画像ストック
try:
    from image_stock import ImageStock
    integrations_status["image_stock"] = "OK"
    print("[OK] 画像ストック")
except Exception as e:
    integrations_status["image_stock"] = f"ERROR: {e}"
    print(f"[ERROR] 画像ストック: {e}")

print()
print("=" * 60)
print("確認完了")
print("=" * 60)



