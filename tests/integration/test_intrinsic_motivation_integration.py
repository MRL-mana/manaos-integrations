#!/usr/bin/env python3
"""
Intrinsic Motivation System 統合テスト
"""

import httpx
import time
import os

try:
    from manaos_integrations._paths import INTRINSIC_MOTIVATION_PORT
except Exception:  # pragma: no cover
    try:
        from _paths import INTRINSIC_MOTIVATION_PORT  # type: ignore
    except Exception:  # pragma: no cover
        INTRINSIC_MOTIVATION_PORT = int(os.getenv("INTRINSIC_MOTIVATION_PORT", "5130"))

def test_intrinsic_motivation():
    """Intrinsic Motivation Systemのテスト"""

    base_url = os.getenv(
        "INTRINSIC_MOTIVATION_URL",
        f"http://127.0.0.1:{INTRINSIC_MOTIVATION_PORT}",
    )

    print("Intrinsic Motivation System Integration Test")
    print("=" * 60)

    # 1. ヘルスチェック
    print("\n1. ヘルスチェック...")
    try:
        response = httpx.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print("   [OK] Health check success")
            print(f"   {response.json()}")
        else:
            print(f"   [FAIL] Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   [ERROR] Connection error: {e}")
        print("   💡 サービスが起動していない可能性があります")
        print("   💡 起動コマンド: python intrinsic_motivation.py 5130")
        return False

    # 2. 状態取得
    print("\n2. 状態取得...")
    try:
        response = httpx.get(f"{base_url}/api/status", timeout=5)
        if response.status_code == 200:
            status = response.json()
            print("   [OK] Status retrieved")
            print(f"   Idle: {status.get('is_idle', 'N/A')}")
            print(f"   Idle threshold: {status.get('idle_threshold_minutes', 'N/A')} minutes")
            print(f"   Enabled: {status.get('enabled', 'N/A')}")
            print(f"   Long-term goal: {status.get('long_term_goal', 'N/A')}")
        else:
            print(f"   [FAIL] Status retrieval failed: {response.status_code}")
    except Exception as e:
        print(f"   [ERROR] {e}")

    # 3. 外部タスク記録
    print("\n3. 外部タスク記録...")
    try:
        response = httpx.post(f"{base_url}/api/record-external-task", timeout=5)
        if response.status_code == 200:
            print("   [OK] External task recorded")
        else:
            print(f"   [FAIL] External task recording failed: {response.status_code}")
    except Exception as e:
        print(f"   [ERROR] {e}")

    # 4. 内発的タスク生成
    print("\n4. 内発的タスク生成...")
    try:
        response = httpx.post(f"{base_url}/api/generate-tasks", timeout=10)
        if response.status_code == 200:
            data = response.json()
            tasks = data.get("tasks", [])
            print(f"   [OK] Intrinsic tasks generated: {len(tasks)} tasks")
            for i, task in enumerate(tasks[:3], 1):  # 最初の3件のみ表示
                print(f"   {i}. {task.get('title', 'N/A')} (Priority: {task.get('priority', 'N/A')})")
        else:
            print(f"   [FAIL] Intrinsic task generation failed: {response.status_code}")
    except Exception as e:
        print(f"   [ERROR] {e}")

    print("\n" + "=" * 60)
    print("[OK] Test completed")

    return True


