#!/usr/bin/env python3
"""
RunPod統合 - 課題解決と実際に使う
"""

import subprocess

def solve_phase1():
    """Phase 1を有効化（Modal認証）"""
    print("\n" + "=" * 60)
    print("🔐 Phase 1: Modal認証を設定")
    print("=" * 60)

    try:
        # Modal認証確認
        result = subprocess.run(
            ["modal", "token", "show"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            print("✅ Modal認証済み")
            return True
        else:
            print("⚠️  Modal認証が必要です")
            print("\n💡 認証方法:")
            print("   1. 以下のコマンドを実行:")
            print("      modal token set")
            print("   2. 表示されたURLをブラウザで開く")
            print("   3. 認証完了後、このスクリプトを再実行")
            return False

    except FileNotFoundError:
        print("❌ modalコマンドが見つかりません")
        print("   pip install modal でインストールしてください")
        return False
    except Exception as e:
        print(f"❌ エラー: {e}")
        return False


def solve_phase2_worker():
    """Phase 2 Worker起動方法を提示"""
    print("\n" + "=" * 60)
    print("⚙️  Phase 2: Worker起動方法")
    print("=" * 60)

    from job_queue_manager import JobQueueManager

    manager = JobQueueManager()
    queue_length = manager.get_queue_length()

    print(f"\n現在のキュー長: {queue_length}")

    if queue_length > 0:
        print(f"⚠️  {queue_length}個のジョブが待機中です")
        print("\n💡 Worker起動方法:")
        print("   1. RunPod Web Terminalを開く")
        print("   2. 以下のコマンドを実行:")
        print("      cd /workspace")
        print("      python3 runpod_trinity_worker.py")
        print("\n   またはバックグラウンドで起動:")
        print("      nohup python3 runpod_trinity_worker.py > worker.log 2>&1 &")
    else:
        print("✅ キューは空です（Worker不要）")


def use_phase2_now():
    """Phase 2を今すぐ使う"""
    print("\n" + "=" * 60)
    print("🚀 Phase 2を今すぐ使う")
    print("=" * 60)

    from manaos_runpod_client import ManaOSRunPodClient

    client = ManaOSRunPodClient()

    print("\n1️⃣ 新しい画像生成ジョブを投入...")

    result = client.generate_image(
        prompt="A futuristic cityscape at sunset with neon lights",
        steps=20,
        width=512,
        height=512,
        wait_for_result=False
    )

    if result.get("success"):
        job_id = result.get("job_id")
        print("✅ ジョブ投入成功!")
        print(f"   ジョブID: {job_id}")
        print("\n💡 Worker起動後、このジョブが処理されます")
        return job_id
    else:
        print(f"❌ ジョブ投入失敗: {result.get('error')}")
        return None


def test_phase1_after_auth():
    """Phase 1認証後のテスト"""
    print("\n" + "=" * 60)
    print("🧪 Phase 1: 認証後のテスト")
    print("=" * 60)

    try:
        from manaos_modal_client import ManaOSModalClient

        client = ManaOSModalClient()

        if not client.check_modal_auth():
            print("❌ まだ認証されていません")
            print("   modal token set を実行してください")
            return False

        print("✅ Modal認証確認")

        print("\nヘルスチェック...")
        health = client.health_check()

        if health.get("success"):
            print("✅ Modal GPUサービス正常")
            gpu_info = health.get("data", {})
            print(f"   GPU利用可能: {gpu_info.get('gpu_available', False)}")
            print(f"   GPU数: {gpu_info.get('gpu_count', 0)}")
            return True
        else:
            print(f"❌ ヘルスチェック失敗: {health.get('error')}")
            return False

    except Exception as e:
        print(f"❌ エラー: {e}")
        return False


def main():
    """メイン実行"""
    print("=" * 60)
    print("🎯 RunPod統合 - 課題解決と実際に使う")
    print("=" * 60)

    # Phase 1認証
    phase1_ok = solve_phase1()

    # Phase 2 Worker起動方法
    solve_phase2_worker()

    # Phase 2を今すぐ使う
    job_id = use_phase2_now()

    # Phase 1認証後のテスト
    if phase1_ok:
        test_phase1_after_auth()

    # まとめ
    print("\n" + "=" * 60)
    print("📊 まとめ")
    print("=" * 60)

    print("\n✅ 今すぐ使える:")
    print("   - Phase 2: ジョブ投入、ファイルアップロード")

    if phase1_ok:
        print("   - Phase 1: Modal.com（認証済み）")
    else:
        print("\n📝 設定すれば使える:")
        print("   - Phase 1: modal token set で認証")

    print("\n💡 次のステップ:")
    print("   1. Phase 1認証: modal token set")
    print("   2. Phase 2 Worker起動: RunPod Web Terminalで起動")
    print("   3. 実際の画像生成: example_usage.py を実行")

    print("\n🎉 準備完了！")


if __name__ == "__main__":
    main()









