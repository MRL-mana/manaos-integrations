"""
記憶機能のテストスクリプト
"""

import requests
import json
from datetime import datetime

API_BASE = "http://127.0.0.1:9510"

def test_memory_store():
    """記憶への保存をテスト"""
    print("=" * 60)
    print("記憶への保存テスト")
    print("=" * 60)
    
    test_data = [
        {
            "content": "今日はManaOSの統合システムをセットアップしました。GitHub統合、統一記憶システム、LLMルーティングなどが有効化されました。",
            "metadata": {
                "source": "test",
                "timestamp": datetime.now().isoformat(),
                "category": "setup"
            }
        },
        {
            "content": "ユーザーは統合システムのセットアップを完了し、すべての統合が正常に動作していることを確認しました。",
            "metadata": {
                "source": "test",
                "category": "system_status"
            }
        },
        {
            "content": "記憶機能をテストしています。保存と検索が正常に動作することを確認します。",
            "metadata": {
                "source": "test",
                "category": "testing"
            }
        }
    ]
    
    stored_ids = []
    for i, data in enumerate(test_data, 1):
        try:
            response = requests.post(
                f"{API_BASE}/api/memory/store",
                json=data,
                timeout=5
            )
            if response.status_code == 200:
                result = response.json()
                memory_id = result.get("memory_id")
                stored_ids.append(memory_id)
                print(f"[{i}] 保存成功: {memory_id}")
                print(f"     内容: {data['content'][:50]}...")
            else:
                print(f"[{i}] 保存失敗: HTTP {response.status_code}")
                print(f"     エラー: {response.text}")
        except Exception as e:
            print(f"[{i}] エラー: {e}")
    
    print(f"\n保存したメモリ数: {len(stored_ids)}")
    return stored_ids


def test_memory_recall():
    """記憶からの検索をテスト"""
    print("\n" + "=" * 60)
    print("記憶からの検索テスト")
    print("=" * 60)
    
    queries = [
        "ManaOS統合",
        "セットアップ",
        "記憶機能",
        "テスト"
    ]
    
    for query in queries:
        print(f"\n検索クエリ: '{query}'")
        try:
            response = requests.get(
                f"{API_BASE}/api/memory/recall",
                params={"query": query, "limit": 5},
                timeout=5
            )
            if response.status_code == 200:
                result = response.json()
                results = result.get("results", [])
                count = result.get("count", 0)
                print(f"  検索結果: {count}件")
                for i, res in enumerate(results[:3], 1):
                    content = str(res.get("content", res.get("input_data", {})))[:80]
                    print(f"    {i}. {content}...")
            else:
                print(f"  検索失敗: HTTP {response.status_code}")
        except Exception as e:
            print(f"  エラー: {e}")


def test_memory_status():
    """記憶システムの状態を確認"""
    print("\n" + "=" * 60)
    print("記憶システムの状態確認")
    print("=" * 60)
    
    try:
        response = requests.get(f"{API_BASE}/ready", timeout=5)
        if response.status_code == 200:
            result = response.json()
            checks = result.get("readiness_checks", {})
            memory_db = checks.get("memory_db", {})
            obsidian = checks.get("obsidian_path", {})
            
            print(f"記憶DB: {memory_db.get('status', 'unknown')} - {memory_db.get('message', '')}")
            print(f"Obsidian: {obsidian.get('status', 'unknown')} - {obsidian.get('message', '')}")
        else:
            print(f"状態確認失敗: HTTP {response.status_code}")
    except Exception as e:
        print(f"エラー: {e}")


if __name__ == "__main__":
    # 状態確認
    test_memory_status()
    
    # 保存テスト
    stored_ids = test_memory_store()
    
    # 検索テスト
    test_memory_recall()
    
    print("\n" + "=" * 60)
    print("テスト完了")
    print("=" * 60)



