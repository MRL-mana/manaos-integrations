"""
LLMルーティングシステムのテスト
"""

import sys
from pathlib import Path

# パスを追加
sys.path.insert(0, str(Path(__file__).parent))

from llm_routing import LLMRouter, ModelUnavailableError, AllModelsUnavailableError
import manaos_core_api as manaos


def test_llm_routing():
    """LLMルーティングのテスト"""
    print("=" * 60)
    print("LLMルーティングシステム テスト")
    print("=" * 60)
    
    router = LLMRouter()
    
    # 1. 会話タスク
    print("\n[1] 会話タスク（conversation）")
    print("-" * 60)
    try:
        result = router.route(
            task_type="conversation",
            prompt="こんにちは、今日はいい天気ですね。"
        )
        print(f"✅ 成功")
        print(f"   モデル: {result['model']} ({result['source']})")
        print(f"   レイテンシ: {result['latency_ms']}ms")
        print(f"   応答: {result['response'][:100]}...")
    except AllModelsUnavailableError as e:
        print(f"❌ エラー: {e}")
        print("   → Ollamaが起動しているか確認してください")
    except Exception as e:
        print(f"❌ エラー: {e}")
    
    # 2. 推論タスク
    print("\n[2] 推論タスク（reasoning）")
    print("-" * 60)
    try:
        result = router.route(
            task_type="reasoning",
            prompt="プロジェクトの優先順位を決定する方法を分析してください。"
        )
        print(f"✅ 成功")
        print(f"   モデル: {result['model']} ({result['source']})")
        print(f"   レイテンシ: {result['latency_ms']}ms")
        print(f"   応答: {result['response'][:100]}...")
    except AllModelsUnavailableError as e:
        print(f"❌ エラー: {e}")
    except Exception as e:
        print(f"❌ エラー: {e}")
    
    # 3. 自動処理タスク
    print("\n[3] 自動処理タスク（automation）")
    print("-" * 60)
    try:
        result = router.route(
            task_type="automation",
            prompt="Pythonでファイルを読み込むコードを生成してください。"
        )
        print(f"✅ 成功")
        print(f"   モデル: {result['model']} ({result['source']})")
        print(f"   レイテンシ: {result['latency_ms']}ms")
        print(f"   応答: {result['response'][:100]}...")
    except AllModelsUnavailableError as e:
        print(f"❌ エラー: {e}")
    except Exception as e:
        print(f"❌ エラー: {e}")
    
    # 4. 監査ログ
    print("\n[4] 監査ログ")
    print("-" * 60)
    logs = router.get_audit_logs(limit=10)
    if logs:
        print(f"✅ {len(logs)}件のログを取得")
        for log in logs[-3:]:  # 最後の3件を表示
            print(f"   {log['timestamp']} | {log['task_type']} -> {log['routed_model']} ({'fallback' if log['fallback_used'] else 'primary'}) | {log['latency_ms']}ms")
    else:
        print("⚠️  ログがありません")


def test_manaos_core_api():
    """manaOS標準APIのテスト"""
    print("\n" + "=" * 60)
    print("manaOS標準API テスト")
    print("=" * 60)
    
    # 1. イベント発行
    print("\n[1] イベント発行（emit）")
    print("-" * 60)
    event = manaos.emit("test_event", {"message": "テストイベント"}, "normal")
    print(f"✅ イベント発行: {event['event_id']}")
    
    # 2. 記憶への保存
    print("\n[2] 記憶への保存（remember）")
    print("-" * 60)
    memory = manaos.remember({"type": "conversation", "content": "テストメモ"}, "conversation")
    print(f"✅ 記憶保存: {memory['memory_id']}")
    
    # 3. 記憶からの検索
    print("\n[3] 記憶からの検索（recall）")
    print("-" * 60)
    results = manaos.recall("テスト", scope="all", limit=5)
    print(f"✅ 検索結果: {len(results)}件")
    
    # 4. LLM呼び出し（アクション実行）
    print("\n[4] LLM呼び出し（act）")
    print("-" * 60)
    try:
        result = manaos.act("llm_call", {
            "task_type": "conversation",
            "prompt": "こんにちは、テストです。"
        })
        if "error" in result:
            print(f"❌ エラー: {result['error']}")
        else:
            print(f"✅ LLM呼び出し成功")
            print(f"   モデル: {result.get('model', 'N/A')}")
            print(f"   応答: {result.get('response', '')[:100]}...")
    except Exception as e:
        print(f"❌ エラー: {e}")


if __name__ == "__main__":
    # LLMルーティングのテスト
    test_llm_routing()
    
    # manaOS標準APIのテスト
    test_manaos_core_api()
    
    print("\n" + "=" * 60)
    print("テスト完了")
    print("=" * 60)


















