#!/usr/bin/env python3
"""
エージェント使用例のデモ
実際のエージェントがどう使うかを示す
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tools.policy.agent_integration import get_agent_policy

def demo_remi():
    """Remi（戦略指令AI）の使用例"""
    print("=" * 60)
    print("🎯 Remi（戦略指令AI）の使用例")
    print("=" * 60)

    remi = get_agent_policy("remi")

    # 1. 変更を提案
    print("\n1. 設計変更を提案...")
    result = remi.propose_change(
        resource="architecture/design",
        intent="update_system_architecture",
        files=["docs/architecture.md", "config/system.yaml"],
        description="新しいアーキテクチャパターンを導入"
    )

    if result["success"]:
        print(f"   ✅ 提案成功: {result['action_id']}")
        if result.get("conflicts"):
            print(f"   ⚠️  競合: {len(result['conflicts'])}件")
        else:
            print("   ✅ 競合なし")
    else:
        print(f"   ❌ 提案失敗: {result.get('error')}")

    # 2. PR前チェック
    print("\n2. PR作成前のポリシーチェック...")
    check = remi.check_before_pr(
        pr_title="remi/architecture/update_system_architecture",
        pr_files=["docs/architecture.md", "config/system.yaml"]
    )

    if check["can_proceed"]:
        print("   ✅ ポリシーチェック通過")
    else:
        print("   ❌ ポリシー違反あり")
        for violation in check["violations"]:
            print(f"      - {violation.get('message')}")

    if check["recommendations"]:
        print("   💡 推奨事項:")
        for rec in check["recommendations"]:
            print(f"      {rec}")

def demo_luna():
    """Luna（実務遂行AI）の使用例"""
    print("\n" + "=" * 60)
    print("⚙️  Luna（実務遂行AI）の使用例")
    print("=" * 60)

    luna = get_agent_policy("luna")

    # 1. コード実装の提案
    print("\n1. コード実装を提案...")
    result = luna.propose_change(
        resource="adapters/model_v1",
        intent="implement_new_feature",
        files=["adapters/model_v1.py", "tests/test_model.py"],
        description="新しい機能を実装",
        data={"feature": "learning_rate_scheduler"}
    )

    if result["success"]:
        print(f"   ✅ 提案成功: {result['action_id']}")
        print(f"   📊 ロック取得: {result.get('lock_acquired')}")
    else:
        print(f"   ❌ 提案失敗: {result.get('error')}")

    # 2. キュー状態を確認
    print("\n2. キュー状態を確認...")
    status = luna.get_queue_status()
    print(f"   📊 待機中: {status['pending']}, 処理中: {status['processing']}, 失敗: {status['failed']}")

def demo_machi():
    """Machi（設定最適化AI）の使用例"""
    print("\n" + "=" * 60)
    print("🔧 Machi（設定最適化AI）の使用例")
    print("=" * 60)

    machi = get_agent_policy("machi")

    # 1. 設定変更の提案（Machiは設定変更が許可されている）
    print("\n1. 設定最適化を提案...")
    result = machi.propose_change(
        resource="config/learning",
        intent="optimize_learning_params",
        files=["config/learning.yaml"],
        description="学習パラメータを最適化",
        data={"learning_rate": 0.001, "batch_size": 32}
    )

    if result["success"]:
        print(f"   ✅ 提案成功: {result['action_id']}")
    else:
        print(f"   ❌ 提案失敗: {result.get('error')}")

    # 2. PAUSE_AUTOフラグチェック
    print("\n2. システム状態を確認...")
    if machi.is_paused():
        print("   ⚠️  PAUSE_AUTOフラグが有効（自動アクション停止中）")
    else:
        print("   ✅ システムは正常に動作中")

def main():
    """全デモを実行"""
    print("\n🚀 ManaOS ポリシーシステム - エージェント使用例デモ\n")

    try:
        demo_remi()
        demo_luna()
        demo_machi()

        print("\n" + "=" * 60)
        print("🎉 デモ完了")
        print("=" * 60)
        print("\n💡 ヒント:")
        print("   - 各エージェントは get_agent_policy(agent_name) でヘルパーを取得")
        print("   - propose_change() で変更を提案")
        print("   - check_before_pr() でPR前チェック")
        print("   - 詳細は /root/infra/policies/USAGE_EXAMPLES.md を参照")

    except Exception as e:
        print(f"\n❌ エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()



