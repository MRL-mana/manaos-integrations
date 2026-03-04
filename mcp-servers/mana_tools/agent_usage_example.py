#!/usr/bin/env python3
"""
Trinityエージェントが実際に使う統合例
各エージェントが実際のタスクで使う際のサンプルコード
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tools.policy.agent_integration import get_agent_policy

def example_remi_design_change():
    """Remiが設計変更を提案する例"""
    print("=" * 60)
    print("🎯 Remi: 設計変更を提案")
    print("=" * 60)

    remi = get_agent_policy("remi")

    # 設計変更を提案
    result = remi.propose_change(
        resource="architecture/microservices",
        intent="design_microservices_architecture",
        files=["docs/architecture.md", "config/services.yaml"],
        description="マイクロサービス化の設計を追加"
    )

    if result["success"]:
        print(f"✅ 提案成功: {result['action_id']}")

        # PR作成前のチェック
        check = remi.check_before_pr(
            pr_title="remi/architecture/design_microservices_architecture",
            pr_files=["docs/architecture.md", "config/services.yaml"]
        )

        if check["can_proceed"]:
            print("✅ PR作成可能")
            print(f"💡 推奨事項: {check.get('recommendations', [])}")
        else:
            print("❌ ポリシー違反あり")
    else:
        print(f"❌ エラー: {result.get('error')}")

def example_luna_implementation():
    """Lunaがコード実装を提案する例"""
    print("\n" + "=" * 60)
    print("⚙️  Luna: コード実装を提案")
    print("=" * 60)

    luna = get_agent_policy("luna")

    # コード実装を提案
    result = luna.propose_change(
        resource="adapters/model_v1",
        intent="implement_learning_rate_scheduler",
        files=["adapters/model_v1.py", "tests/test_model.py"],
        description="学習率スケジューラを実装",
        data={"feature": "learning_rate_scheduler", "priority": "high"}
    )

    if result["success"]:
        print(f"✅ 提案成功: {result['action_id']}")
        print(f"📊 ロック取得: {result.get('lock_acquired')}")

        if result.get("conflicts"):
            print(f"⚠️  競合検出: {len(result['conflicts'])}件")
            for conflict in result["conflicts"]:
                print(f"   - PR #{conflict.get('pr_number')}: {conflict.get('conflict_type')}")
    else:
        print(f"❌ エラー: {result.get('error')}")

def example_machi_config_optimization():
    """Machiが設定最適化を提案する例"""
    print("\n" + "=" * 60)
    print("🔧 Machi: 設定最適化を提案")
    print("=" * 60)

    machi = get_agent_policy("machi")

    # 設定最適化を提案（Machiは設定変更が許可されている）
    result = machi.propose_change(
        resource="config/learning",
        intent="optimize_learning_parameters",
        files=["config/learning.yaml"],
        description="学習パラメータを最適化",
        data={
            "learning_rate": 0.001,
            "batch_size": 32,
            "epochs": 100
        }
    )

    if result["success"]:
        print(f"✅ 提案成功: {result['action_id']}")

        # キュー状態を確認
        status = machi.get_queue_status()
        print(f"📊 キュー状態: {status['pending']}件待機中")
    else:
        print(f"❌ エラー: {result.get('error')}")

def example_mina_code_review():
    """Minaがコードレビューでポリシーチェックする例"""
    print("\n" + "=" * 60)
    print("🔍 Mina: コードレビューでポリシーチェック")
    print("=" * 60)

    mina = get_agent_policy("mina")

    # レビュー対象のPRをチェック
    check = mina.check_before_pr(
        pr_title="luna/adapters/implement_learning_rate_scheduler",
        pr_files=["adapters/model_v1.py", "tests/test_model.py"],
        pr_number=123
    )

    if check["can_proceed"]:
        print("✅ ポリシーチェック通過")
        print("✅ レビューを続行できます")
    else:
        print("❌ ポリシー違反あり")
        print("\n違反内容:")
        for violation in check["violations"]:
            print(f"  - {violation.get('message')}")

        print("\n推奨事項:")
        for rec in check.get("recommendations", []):
            print(f"  {rec}")

def example_aria_documentation():
    """Ariaがドキュメント更新でポリシーチェックする例"""
    print("\n" + "=" * 60)
    print("📖 Aria: ドキュメント更新")
    print("=" * 60)

    aria = get_agent_policy("aria")

    # 重要なドキュメント変更がある場合はチェック
    check = aria.check_before_pr(
        pr_title="aria/knowledge/update_architecture_docs",
        pr_files=["docs/knowledge.md", "docs/architecture.md"]
    )

    if check["can_proceed"]:
        print("✅ ポリシーチェック通過")
        print("✅ ドキュメント更新を続行できます")
    else:
        print("⚠️  注意事項あり")
        for warning in check.get("warnings", []):
            print(f"  - {warning.get('message')}")

def main():
    """すべての例を実行"""
    print("\n🚀 Trinityエージェント統合例 - 実用例\n")

    try:
        example_remi_design_change()
        example_luna_implementation()
        example_machi_config_optimization()
        example_mina_code_review()
        example_aria_documentation()

        print("\n" + "=" * 60)
        print("🎉 すべての例実行完了")
        print("=" * 60)
        print("\n💡 ヒント:")
        print("   - 各エージェントは get_agent_policy(agent_name) でヘルパーを取得")
        print("   - propose_change() で変更を提案")
        print("   - check_before_pr() でPR前チェック")
        print("   - 詳細は /root/infra/policies/AGENT_INTEGRATION.md を参照")

    except Exception as e:
        print(f"\n❌ エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()



