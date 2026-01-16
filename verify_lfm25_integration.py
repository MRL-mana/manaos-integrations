#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LFM 2.5統合効果確認スクリプト
"""

import requests
import json
import sys
import time

# Windowsコンソールのエンコーディング設定
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def check_service(port, name):
    """サービスが動作しているか確認"""
    try:
        response = requests.get(f"http://localhost:{port}/health", timeout=2)
        if response.status_code == 200:
            return True
    except:
        pass
    return False

def test_intent_router():
    """Intent Routerのテスト"""
    print("[1] Intent Router動作確認...")
    try:
        test_data = {"text": "こんにちは"}
        start_time = time.time()
        response = requests.post(
            "http://localhost:5100/api/classify",
            json=test_data,
            timeout=10
        )
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            print(f"  [OK] 動作確認成功")
            print(f"  レイテンシ: {elapsed:.2f}秒")
            print(f"  意図タイプ: {result.get('intent_type', 'N/A')}")
            print(f"  信頼度: {result.get('confidence', 'N/A')}")
            return True, elapsed
        else:
            print(f"  [FAIL] HTTP {response.status_code}")
            return False, None
    except Exception as e:
        print(f"  [FAIL] エラー: {e}")
        return False, None

def test_unified_api():
    """Unified API Serverのテスト"""
    print("[2] Unified API Server動作確認...")
    try:
        response = requests.get("http://localhost:9500/health", timeout=2)
        if response.status_code == 200:
            print("  [OK] 動作確認成功")
            return True
        else:
            print(f"  [FAIL] HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"  [FAIL] エラー: {e}")
        return False

def main():
    print("=" * 50)
    print("LFM 2.5統合効果確認")
    print("=" * 50)
    print()
    
    # サービス状態確認
    print("[0] サービス状態確認...")
    print()
    
    services = [
        ("Intent Router", 5100),
        ("Task Planner", 5101),
        ("Content Generation", 5109),
        ("Unified API Server", 9500)
    ]
    
    all_running = True
    for name, port in services:
        if check_service(port, name):
            print(f"  [OK] {name}: 動作中")
        else:
            print(f"  [FAIL] {name}: 停止中")
            all_running = False
    
    print()
    
    if not all_running:
        print("[WARN] 一部のサービスが停止しています")
        print()
    
    # Intent Routerのテスト
    success, latency = test_intent_router()
    print()
    
    # Unified API Serverのテスト
    unified_ok = test_unified_api()
    print()
    
    print("=" * 50)
    print("確認完了")
    print("=" * 50)
    print()
    print("期待される効果:")
    print("  - Intent Router: レイテンシ70-90%削減（10秒 → 1-3秒）")
    if latency:
        if latency < 3:
            print(f"  [OK] 実際のレイテンシ: {latency:.2f}秒（期待値内）")
        else:
            print(f"  [WARN] 実際のレイテンシ: {latency:.2f}秒（期待値より高い）")
    print("  - Secretary Routines: レイテンシ80-85%削減（30-60秒 → 5-10秒）")
    print("  - Task Planner: 簡単な計画で80-85%削減")
    print("  - Content Generation: 下書き生成で80-85%削減")
    print()
    
    if success and unified_ok:
        print("[OK] 基本的な動作確認は成功しました")
        return 0
    else:
        print("[WARN] 一部の確認に失敗しました")
        return 1

if __name__ == "__main__":
    sys.exit(main())
