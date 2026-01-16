#!/usr/bin/env python3
"""
Phase 1 (Read-only) 疎通確認
4つのテストを実行
"""

import requests
import os
from pathlib import Path

# .envファイルを読み込み
env_path = Path(".env")
if env_path.exists():
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:5105")
API_KEY = os.getenv("API_KEY", "")

def test_1_no_auth():
    """テスト1: 認証なしで叩く → 401"""
    print("テスト1: 認証なしで叩く → 401")
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/memory/search",
            json={"query": "test"},
            timeout=5
        )
        if response.status_code == 401:
            print("  [PASS] 401が返されました（認証必須が機能しています）")
            return True
        else:
            print(f"  [FAIL] 期待値401、実際{response.status_code}")
            print(f"    レスポンス: {response.text[:100]}")
            return False
    except Exception as e:
        print(f"  [FAIL] エラーが発生しました: {e}")
        return False

def test_2_with_auth():
    """テスト2: 認証ありで叩く → 200"""
    print("テスト2: 認証ありで叩く → 200")
    try:
        headers = {"X-API-Key": API_KEY}
        response = requests.post(
            f"{API_BASE_URL}/api/memory/search",
            json={"query": "test"},
            headers=headers,
            timeout=5
        )
        if response.status_code == 200:
            print("  [PASS] 200が返されました（認証が正常に機能しています）")
            return True
        else:
            print(f"  [FAIL] 期待値200、実際{response.status_code}")
            print(f"    レスポンス: {response.text[:100]}")
            return False
    except Exception as e:
        print(f"  [FAIL] エラーが発生しました: {e}")
        return False

def test_3_max_input_exceeded():
    """テスト3: MAX_INPUT超過で叩く → 413（or 400）"""
    print("テスト3: MAX_INPUT超過で叩く → 413（or 400）")
    try:
        max_input = int(os.getenv("MAX_INPUT_CHARS", "200000"))
        large_text = "a" * (max_input + 1000)  # 制限を超える
        
        headers = {"X-API-Key": API_KEY}
        response = requests.post(
            f"{API_BASE_URL}/api/memory/process",
            json={"text": large_text},
            headers=headers,
            timeout=10
        )
        if response.status_code in [400, 413]:
            print(f"  [PASS] {response.status_code}が返されました（入力サイズ制限が機能しています）")
            return True
        else:
            print(f"  [FAIL] 期待値400/413、実際{response.status_code}")
            print(f"    レスポンス: {response.text[:100]}")
            return False
    except Exception as e:
        print(f"  [FAIL] エラーが発生しました: {e}")
        return False

def test_4_rate_limit():
    """テスト4: レート超過で叩く → 429"""
    print("テスト4: レート超過で叩く → 429")
    try:
        rate_limit = int(os.getenv("RATE_LIMIT_PER_MIN", "60"))
        headers = {"X-API-Key": API_KEY}
        
        # レート制限を超えるリクエストを送信
        success_count = 0
        rate_limited = False
        
        for i in range(rate_limit + 10):  # 制限+10回
            response = requests.post(
                f"{API_BASE_URL}/api/memory/search",
                json={"query": f"test{i}"},
                headers=headers,
                timeout=2
            )
            
            if response.status_code == 200:
                success_count += 1
            elif response.status_code == 429:
                rate_limited = True
                print(f"  [PASS] 429が返されました（レート制限が機能しています）")
                print(f"    成功リクエスト数: {success_count}/{i+1}")
                return True
        
        if not rate_limited:
            print(f"  [WARN] レート制限が発動しませんでした（成功: {success_count}）")
            print(f"    レート制限値: {rate_limit}/分")
            return False
    except Exception as e:
        print(f"  [FAIL] エラーが発生しました: {e}")
        return False

def main():
    """メイン処理"""
    print("=" * 60)
    print("Phase 1 (Read-only) 疎通確認")
    print("=" * 60)
    print()
    print(f"API URL: {API_BASE_URL}")
    print(f"API Key: {'設定済み' if API_KEY else '未設定'}")
    print()
    
    results = []
    
    # テスト1: 認証なし
    results.append(("認証なし → 401", test_1_no_auth()))
    print()
    
    # テスト2: 認証あり
    results.append(("認証あり → 200", test_2_with_auth()))
    print()
    
    # テスト3: MAX_INPUT超過
    results.append(("MAX_INPUT超過 → 413/400", test_3_max_input_exceeded()))
    print()
    
    # テスト4: レート制限
    results.append(("レート超過 → 429", test_4_rate_limit()))
    print()
    
    # 結果サマリー
    print("=" * 60)
    print("結果サマリー")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status}: {name}")
    
    print()
    print(f"合計: {passed}/{total} テストがパスしました")
    
    if passed == total:
        print()
        print("[OK] すべてのテストがパスしました。Phase 1の土台OKです。")
        return True
    else:
        print()
        print("[ERROR] 一部のテストが失敗しました。設定を確認してください。")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
