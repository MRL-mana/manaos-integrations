"""
拡張フェーズ APIエンドポイントのテスト
統合APIサーバーが起動している必要があります
"""

import sys
import io

# Windows環境でのエンコーディング問題を回避
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import requests
import json
from typing import Dict, Any

BASE_URL = "http://localhost:9500"


def test_llm_routing():
    """LLMルーティングのテスト"""
    print("=" * 60)
    print("LLMルーティング API テスト")
    print("=" * 60)
    
    # 会話タスク
    print("\n[1] 会話タスク")
    print("-" * 60)
    try:
        response = requests.post(
            f"{BASE_URL}/api/llm/route",
            json={
                "task_type": "conversation",
                "prompt": "こんにちは、テストです。"
            },
            timeout=30
        )
        if response.status_code == 200:
            result = response.json()
            print(f"[OK] 成功")
            print(f"   モデル: {result.get('model', 'N/A')}")
            print(f"   ソース: {result.get('source', 'N/A')}")
            print(f"   レイテンシ: {result.get('latency_ms', 0)}ms")
        else:
            print(f"[FAIL] エラー: {response.status_code}")
            print(f"   {response.text}")
    except Exception as e:
        print(f"[FAIL] エラー: {e}")


def test_memory():
    """記憶システムのテスト"""
    print("\n" + "=" * 60)
    print("記憶システム API テスト")
    print("=" * 60)
    
    # 記憶への保存
    print("\n[1] 記憶への保存")
    print("-" * 60)
    try:
        response = requests.post(
            f"{BASE_URL}/api/memory/store",
            json={
                "content": {
                    "type": "conversation",
                    "content": "API経由のテストメモです。"
                },
                "format_type": "conversation"
            },
            timeout=10
        )
        if response.status_code == 200:
            result = response.json()
            print(f"[OK] 成功")
            print(f"   メモリID: {result.get('memory_id', 'N/A')}")
        else:
            print(f"[FAIL] エラー: {response.status_code}")
            print(f"   {response.text}")
    except Exception as e:
        print(f"[FAIL] エラー: {e}")
    
    # 記憶からの検索
    print("\n[2] 記憶からの検索")
    print("-" * 60)
    try:
        response = requests.get(
            f"{BASE_URL}/api/memory/recall",
            params={
                "query": "テスト",
                "scope": "all",
                "limit": 10
            },
            timeout=10
        )
        if response.status_code == 200:
            result = response.json()
            print(f"[OK] 成功")
            print(f"   検索結果: {result.get('count', 0)}件")
        else:
            print(f"[FAIL] エラー: {response.status_code}")
            print(f"   {response.text}")
    except Exception as e:
        print(f"[FAIL] エラー: {e}")


def test_notification():
    """通知ハブのテスト"""
    print("\n" + "=" * 60)
    print("通知ハブ API テスト")
    print("=" * 60)
    
    print("\n[1] 通知送信")
    print("-" * 60)
    try:
        response = requests.post(
            f"{BASE_URL}/api/notification/send",
            json={
                "message": "API経由のテスト通知です",
                "priority": "normal"
            },
            timeout=10
        )
        if response.status_code == 200:
            result = response.json()
            print(f"[OK] 成功")
            print(f"   結果: {result.get('results', {})}")
        else:
            print(f"[FAIL] エラー: {response.status_code}")
            print(f"   {response.text}")
    except Exception as e:
        print(f"[FAIL] エラー: {e}")


def test_secretary():
    """秘書機能のテスト"""
    print("\n" + "=" * 60)
    print("秘書機能 API テスト")
    print("=" * 60)
    
    routines = ["morning", "noon", "evening"]
    
    for routine in routines:
        print(f"\n[{routine}] ルーチン")
        print("-" * 60)
        try:
            # 夜のルーチンは重いモデルを使うのでタイムアウトを延長
            timeout = 90 if routine == "evening" else 30
            response = requests.post(
                f"{BASE_URL}/api/secretary/{routine}",
                timeout=timeout
            )
            if response.status_code == 200:
                result = response.json()
                print(f"[OK] 成功")
                print(f"   レポート: {len(result.get('report', ''))}文字")
            else:
                print(f"[FAIL] エラー: {response.status_code}")
                print(f"   {response.text}")
        except Exception as e:
            print(f"[FAIL] エラー: {e}")


def test_image_stock():
    """画像ストックのテスト"""
    print("\n" + "=" * 60)
    print("画像ストック API テスト")
    print("=" * 60)
    
    # 統計情報
    print("\n[1] 統計情報")
    print("-" * 60)
    try:
        response = requests.get(
            f"{BASE_URL}/api/image/statistics",
            timeout=10
        )
        if response.status_code == 200:
            result = response.json()
            print(f"[OK] 成功")
            print(f"   総数: {result.get('total', 0)}件")
        else:
            print(f"[FAIL] エラー: {response.status_code}")
            print(f"   {response.text}")
    except Exception as e:
        print(f"[FAIL] エラー: {e}")
    
    # 検索
    print("\n[2] 画像検索")
    print("-" * 60)
    try:
        response = requests.get(
            f"{BASE_URL}/api/image/search",
            params={
                "query": "test",
                "limit": 10
            },
            timeout=10
        )
        if response.status_code == 200:
            result = response.json()
            print(f"[OK] 成功")
            print(f"   検索結果: {result.get('count', 0)}件")
        else:
            print(f"[FAIL] エラー: {response.status_code}")
            print(f"   {response.text}")
    except Exception as e:
        print(f"[FAIL] エラー: {e}")


def test_health():
    """ヘルスチェック"""
    print("=" * 60)
    print("ヘルスチェック")
    print("=" * 60)
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            result = response.json()
            print(f"[OK] サーバー起動中")
            print(f"   統合システム: {len(result.get('integrations', {}))}個")
        else:
            print(f"[FAIL] エラー: {response.status_code}")
            return False
    except Exception as e:
        print(f"[FAIL] サーバーに接続できません: {e}")
        print(f"   統合APIサーバーが起動しているか確認してください")
        return False
    
    return True


def main():
    """メイン関数"""
    print("=" * 60)
    print("拡張フェーズ APIエンドポイント テスト")
    print("=" * 60)
    
    # ヘルスチェック
    if not test_health():
        print("\n[WARN] サーバーが起動していません。先にサーバーを起動してください。")
        print("   python start_extension_phase.py")
        return
    
    # 各APIのテスト
    test_llm_routing()
    test_memory()
    test_notification()
    test_secretary()
    test_image_stock()
    
    print("\n" + "=" * 60)
    print("テスト完了")
    print("=" * 60)


if __name__ == "__main__":
    main()

