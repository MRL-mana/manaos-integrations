#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
サーバー起動待機＆テストスクリプト
"""

import time
import requests
import sys

BASE_URL = "http://127.0.0.1:9510"
MAX_WAIT = 60  # 最大60秒待機
CHECK_INTERVAL = 2  # 2秒ごとにチェック

def wait_for_server():
    """サーバーが起動するまで待機"""
    print("=" * 60)
    print("統合APIサーバーの起動を待機中...")
    print("=" * 60)
    print()
    
    elapsed = 0
    while elapsed < MAX_WAIT:
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=2)
            if response.status_code == 200:
                print(f"[OK] サーバーが起動しました！（{elapsed}秒後）")
                return True
        except Exception:
            pass
        
        if elapsed % 10 == 0:
            print(f"  待機中... ({elapsed}秒経過)")
        
        time.sleep(CHECK_INTERVAL)
        elapsed += CHECK_INTERVAL
    
    print(f"[NG] サーバーが{MAX_WAIT}秒以内に起動しませんでした")
    return False

def test_oh_my_opencode():
    """OH MY OPENCODE統合テスト"""
    print()
    print("=" * 60)
    print("OH MY OPENCODE統合テスト")
    print("=" * 60)
    print()
    
    # 統合状態確認
    print("1. 統合状態確認...")
    try:
        response = requests.get(f"{BASE_URL}/api/integrations/status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            oh_my_opencode = data.get('integrations', {}).get('oh_my_opencode', {})
            if oh_my_opencode.get('available'):
                print("[OK] OH MY OPENCODE統合が利用可能です")
                print(f"   状態: {oh_my_opencode.get('status', 'unknown')}")
            else:
                print("[WARN] OH MY OPENCODE統合が利用できません")
                return False
        else:
            print(f"[NG] 統合状態取得失敗: {response.status_code}")
            return False
    except Exception as e:
        print(f"[NG] エラー: {e}")
        return False
    
    print()
    
    # 簡単なタスク実行テスト
    print("2. 簡単なタスク実行テスト...")
    test_task = {
        "task_description": "PythonでHello Worldを出力するコードを生成してください",
        "mode": "normal",
        "task_type": "code_generation"
    }
    
    print(f"   タスク: {test_task['task_description']}")
    print("   実行中...")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/oh_my_opencode/execute",
            json=test_task,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print("[OK] タスク実行成功！")
            print(f"   タスクID: {result.get('result', {}).get('task_id', 'N/A')}")
            print(f"   ステータス: {result.get('result', {}).get('status', 'N/A')}")
            return True
        else:
            print(f"[NG] タスク実行失敗: {response.status_code}")
            print(f"   エラー: {response.text[:200]}")
            return False
    except requests.exceptions.Timeout:
        print("[WARN] タイムアウト（30秒）")
        print("   タスクは実行中かもしれません")
        return False
    except Exception as e:
        print(f"[NG] エラー: {e}")
        return False

def main():
    """メイン処理"""
    # サーバー起動待機
    if not wait_for_server():
        print()
        print("=" * 60)
        print("サーバーが起動していません")
        print("手動でサーバーを起動してください:")
        print("  python unified_api_server.py")
        print("=" * 60)
        sys.exit(1)
    
    # 少し待機（初期化完了まで）
    print()
    print("初期化完了を待機中（5秒）...")
    time.sleep(5)
    
    # OH MY OPENCODEテスト
    success = test_oh_my_opencode()
    
    print()
    print("=" * 60)
    if success:
        print("[OK] すべてのテストが成功しました！")
        print("=" * 60)
        print()
        print("🎉 OH MY OPENCODE統合が正常に動作しています！")
        print()
        print("次のステップ:")
        print("  - 実際のタスクを実行してみてください")
        print("  - ブラウザで http://127.0.0.1:9510/health にアクセス")
    else:
        print("[WARN] 一部のテストが失敗しました")
        print("=" * 60)
        print()
        print("トラブルシューティング:")
        print("  - サーバーのログを確認してください")
        print("  - APIキーが正しく設定されているか確認してください")
    print("=" * 60)

if __name__ == "__main__":
    main()
