"""
ManaOS統合システムの全機能テスト
Windows側で動作していることを確認
"""

import requests
import json
from datetime import datetime

API_BASE = "http://localhost:9500"

def print_section(title):
    """セクションタイトルを表示"""
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)

def test_memory():
    """記憶機能のテスト"""
    print_section("記憶機能テスト")
    
    # 保存
    data = {
        "content": f"Windows側でのテスト実行: {datetime.now().isoformat()}",
        "metadata": {"source": "test", "platform": "windows"}
    }
    
    try:
        response = requests.post(f"{API_BASE}/api/memory/store", json=data, timeout=5)
        if response.status_code == 200:
            result = response.json()
            print(f"[OK] 記憶を保存: {result.get('memory_id', 'unknown')}")
        else:
            print(f"[ERROR] 保存失敗: HTTP {response.status_code}")
    except Exception as e:
        print(f"[ERROR] {e}")
    
    # 検索
    try:
        response = requests.get(f"{API_BASE}/api/memory/recall", params={"query": "Windows", "limit": 3}, timeout=5)
        if response.status_code == 200:
            result = response.json()
            print(f"[OK] 検索結果: {result.get('count', 0)}件")
        else:
            print(f"[ERROR] 検索失敗: HTTP {response.status_code}")
    except Exception as e:
        print(f"[ERROR] {e}")

def test_llm_chat():
    """LLMチャット（人格設定付き）のテスト"""
    print_section("LLMチャットテスト（人格設定確認）")
    
    data = {
        "messages": [
            {"role": "user", "content": "あなたは誰ですか？簡単に自己紹介してください。"}
        ],
        "task_type": "conversation"
    }
    
    try:
        response = requests.post(f"{API_BASE}/api/llm/chat", json=data, timeout=60)
        if response.status_code == 200:
            result = response.json()
            print(f"[OK] チャット応答:")
            print(f"  応答: {result.get('response', '')[:150]}...")
            print(f"  モデル: {result.get('model', 'unknown')}")
            print(f"  レイテンシ: {result.get('latency_ms', 0)}ms")
            
            # 人格設定が適用されているか確認
            response_text = result.get('response', '').lower()
            if 'manaos' in response_text or 'アシスタント' in response_text:
                print(f"  [OK] 人格設定が適用されています")
            else:
                print(f"  [WARN] 人格設定が確認できませんでした")
        else:
            print(f"[ERROR] チャット失敗: HTTP {response.status_code}")
            print(f"  エラー: {response.text}")
    except Exception as e:
        print(f"[ERROR] {e}")

def test_github():
    """GitHub統合のテスト"""
    print_section("GitHub統合テスト")
    
    try:
        response = requests.get(
            f"{API_BASE}/api/github/repository",
            params={"owner": "comfyanonymous", "repo": "ComfyUI"},
            timeout=10
        )
        if response.status_code == 200:
            result = response.json()
            repo = result.get('repository', {})
            print(f"[OK] リポジトリ情報取得:")
            print(f"  名前: {repo.get('name', 'unknown')}")
            print(f"  スター数: {repo.get('stars', 0)}")
            print(f"  言語: {repo.get('language', 'unknown')}")
        elif response.status_code == 503:
            print(f"[INFO] GitHub統合が利用できません（トークン未設定の可能性）")
        else:
            print(f"[ERROR] HTTP {response.status_code}")
    except Exception as e:
        print(f"[ERROR] {e}")

def test_system_status():
    """システム状態の確認"""
    print_section("システム状態確認")
    
    try:
        response = requests.get(f"{API_BASE}/ready", timeout=5)
        if response.status_code == 200:
            result = response.json()
            status = result.get('status', 'unknown')
            print(f"[OK] システム状態: {status}")
            
            integrations = result.get('integrations', {})
            print(f"\n統合状態:")
            for key, value in integrations.items():
                status_icon = "✓" if value else "✗"
                print(f"  {status_icon} {key}: {value}")
        else:
            print(f"[ERROR] HTTP {response.status_code}")
    except Exception as e:
        print(f"[ERROR] {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("ManaOS統合システム - 全機能テスト")
    print(f"実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # システム状態確認
    test_system_status()
    
    # 記憶機能テスト
    test_memory()
    
    # LLMチャットテスト
    test_llm_chat()
    
    # GitHub統合テスト
    test_github()
    
    print("\n" + "=" * 60)
    print("テスト完了")
    print("=" * 60)



