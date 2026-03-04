#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MRL Memory System 使用例とテストスクリプト
実際に使えるようにするためのサンプルコード
"""

import sys
import os
from pathlib import Path

try:
    from manaos_integrations._paths import MRL_MEMORY_PORT
except Exception:  # pragma: no cover
    try:
        from _paths import MRL_MEMORY_PORT  # type: ignore
    except Exception:  # pragma: no cover
        MRL_MEMORY_PORT = int(os.getenv("MRL_MEMORY_PORT", "5105"))

# WindowsのコンソールエンコーディングをUTF-8に設定
if sys.platform == 'win32':
    import io
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

def test_mrl_memory_api():
    """MRL Memory APIの直接使用例"""
    print("=" * 60)
    print("MRL Memory API 直接使用例")
    print("=" * 60)

    import requests
    import json

    # APIキーを読み込む
    api_key = None
    env_path = Path(".env")
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("MRL_MEMORY_API_KEY=") and "=" in line:
                api_key = line.split("=", 1)[1].strip()
                break

    base_url = os.getenv("MRL_MEMORY_API_URL", f"http://127.0.0.1:{MRL_MEMORY_PORT}")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key

    # 1. テキストを処理してメモリに保存
    print("\n[1] テキストを処理してメモリに保存")
    test_text = "プロジェクトXの開始日は2024年2月1日です。メンバーは3人で、予算は100万円です。"
    try:
        response = requests.post(
            f"{base_url}/api/memory/process",
            json={
                "text": test_text,
                "source": "test",
                "enable_rehearsal": True,
                "enable_promotion": False
            },
            headers=headers,
            timeout=5
        )
        if response.status_code == 200:
            result = response.json()
            print(f"  [OK] 処理成功")
            print(f"  - 抽出された情報: {result.get('extracted', {}).get('count', 0)}件")
        else:
            print(f"  [ERROR] HTTP {response.status_code}: {response.text}")
    except Exception as e:
        print(f"  [ERROR] {e}")

    # 2. メモリから検索
    print("\n[2] メモリから検索")
    try:
        response = requests.post(
            f"{base_url}/api/memory/search",
            json={
                "query": "プロジェクトX",
                "limit": 5
            },
            headers=headers,
            timeout=5
        )
        if response.status_code == 200:
            result = response.json()
            print(f"  [OK] 検索成功: {result.get('count', 0)}件の結果")
            for i, item in enumerate(result.get('results', [])[:3], 1):
                print(f"  - 結果{i}: {item.get('value', '')[:50]}...")
        else:
            print(f"  [ERROR] HTTP {response.status_code}: {response.text}")
    except Exception as e:
        print(f"  [ERROR] {e}")

    # 3. LLMコンテキストを取得
    print("\n[3] LLMコンテキストを取得")
    try:
        response = requests.post(
            f"{base_url}/api/memory/context",
            json={
                "query": "プロジェクトXについて",
                "limit": 3
            },
            headers=headers,
            timeout=5
        )
        if response.status_code == 200:
            result = response.json()
            context = result.get('context', '')
            print(f"  [OK] コンテキスト取得成功 ({len(context)}文字)")
            print(f"  - コンテキスト: {context[:200]}...")
        else:
            print(f"  [ERROR] HTTP {response.status_code}: {response.text}")
    except Exception as e:
        print(f"  [ERROR] {e}")


def test_mrl_memory_with_llm_routing():
    """MRL Memory + LLMルーティング統合の使用例"""
    print("\n" + "=" * 60)
    print("MRL Memory + LLMルーティング統合の使用例")
    print("=" * 60)

    try:
        from mrl_memory_integration import MRLMemoryLLMIntegration
        from llm_routing import LLMRouter

        print("\n[1] 統合システムを初期化")
        llm_router = LLMRouter()
        mrl_integration = MRLMemoryLLMIntegration(llm_router=llm_router)
        print("  [OK] 初期化完了")

        print("\n[2] メモリを活用したLLMルーティング")
        result = mrl_integration.route_with_memory(
            task_type="conversation",
            prompt="プロジェクトXの予算はいくらでしたか？",
            source="test",
            enable_memory=True
        )

        print(f"  [OK] ルーティング成功")
        print(f"  - 使用モデル: {result.get('model', 'unknown')}")
        print(f"  - メモリ使用: {result.get('memory_used', False)}")
        print(f"  - コンテキスト長: {result.get('memory_context_length', 0)}文字")
        if result.get('response'):
            print(f"  - レスポンス: {result['response'][:100]}...")

    except ImportError as e:
        print(f"  [WARN] インポートエラー: {e}")
        print("  MRL Memory統合またはLLMルーティングが利用できません")
    except Exception as e:
        print(f"  [ERROR] {e}")


def test_manaos_core_api_integration():
    """ManaOS Core API経由での使用例"""
    print("\n" + "=" * 60)
    print("ManaOS Core API経由での使用例")
    print("=" * 60)

    try:
        from manaos_core_api import ManaOSCoreAPI

        print("\n[1] ManaOS Core APIを初期化")
        api = ManaOSCoreAPI()
        print("  [OK] 初期化完了")

        print("\n[2] 記憶を保存")
        memory_entry = api.remember(
            input_data={
                "content": "今日の会議で、来週のリリース日を3月15日に決定しました。",
                "metadata": {"type": "meeting_note"}
            },
            format_type="mrl_memory"
        )
        print(f"  [OK] 記憶を保存しました")

        print("\n[3] 記憶を検索")
        results = api.recall(
            query="リリース日",
            scope="all",
            limit=5
        )
        print(f"  [OK] 検索成功: {len(results)}件の結果")
        for i, result in enumerate(results[:3], 1):
            content = result.get('input_data', {}).get('content', str(result))
            print(f"  - 結果{i}: {content[:50]}...")

    except ImportError as e:
        print(f"  [WARN] インポートエラー: {e}")
    except Exception as e:
        print(f"  [ERROR] {e}")



