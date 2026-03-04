#!/usr/bin/env python3
"""
全Phaseのクイックテスト
実際に使える機能を試す
"""

import sys
from pathlib import Path

def test_phase2():
    """Phase 2のテスト"""
    print("\n" + "=" * 60)
    print("🚀 Phase 2: Pull型ワーカー - 実用テスト")
    print("=" * 60)

    try:
        from manaos_runpod_client import ManaOSRunPodClient
        from job_queue_manager import JobQueueManager

        client = ManaOSRunPodClient()
        manager = JobQueueManager()

        # ヘルスチェック
        print("\n1️⃣ ヘルスチェック...")
        health = client.health_check()
        if health.get("success"):
            print("✅ Phase 2システム正常")
            print("   - Redis: ✅")
            print("   - S3/MinIO: ✅")
            print(f"   - キュー長: {health['redis'].get('queue_length', 0)}")
            print(f"   - S3ファイル数: {health['s3'].get('file_count', 0)}")
        else:
            print("❌ Phase 2システム異常")
            return False

        # ファイルアップロードテスト
        print("\n2️⃣ ファイルアップロードテスト...")
        test_file = Path("/tmp/test_phase2_quick.txt")
        test_file.write_text(f"Phase 2 Quick Test - {sys.version}")

        result = client.upload_file(
            str(test_file),
            "quick_test/phase2_test.txt"
        )

        if result.get("success"):
            print("✅ ファイルアップロード成功")
            print(f"   S3パス: {result.get('s3_path')}")
        else:
            print(f"❌ ファイルアップロード失敗: {result.get('error')}")

        # 画像生成ジョブ投入（非同期）
        print("\n3️⃣ 画像生成ジョブ投入（非同期）...")
        result = client.generate_image(
            prompt="A beautiful Japanese landscape with mountains and cherry blossoms",
            steps=20,
            width=512,
            height=512,
            wait_for_result=False
        )

        if result.get("success"):
            job_id = result.get("job_id")
            print("✅ ジョブ投入成功")
            print(f"   ジョブID: {job_id}")
            print(f"   ステータス: {result.get('status')}")
            print("\n💡 RunPod Workerが起動していれば、このジョブが処理されます")
        else:
            print(f"❌ ジョブ投入失敗: {result.get('error')}")

        # キュー状態確認
        print("\n4️⃣ キュー状態確認...")
        queue_length = manager.get_queue_length()
        print(f"   キュー長: {queue_length}")

        if queue_length > 0:
            print(f"   ⚠️  {queue_length}個のジョブが待機中です")
            print("   💡 RunPod Workerを起動して処理してください")

        return True

    except Exception as e:
        print(f"❌ Phase 2テストエラー: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_phase1():
    """Phase 1のテスト"""
    print("\n" + "=" * 60)
    print("🚀 Phase 1: Modal.com Serverless - 認証確認")
    print("=" * 60)

    try:
        from manaos_modal_client import ManaOSModalClient

        client = ManaOSModalClient()

        print("\n1️⃣ Modal認証確認...")
        auth_ok = client.check_modal_auth()

        if auth_ok:
            print("✅ Modal認証済み")

            print("\n2️⃣ ヘルスチェック...")
            health = client.health_check()
            if health.get("success"):
                print("✅ Modal GPUサービス正常")
                print(f"   GPU利用可能: {health['data'].get('gpu_available', False)}")
                print(f"   GPU数: {health['data'].get('gpu_count', 0)}")
            else:
                print(f"❌ Modal GPUサービス異常: {health.get('error')}")
        else:
            print("❌ Modal認証が必要です")
            print("\n💡 認証方法:")
            print("   modal token set")
            print("   ブラウザで認証URLを開いて認証してください")

        return auth_ok

    except Exception as e:
        print(f"❌ Phase 1テストエラー: {e}")
        return False


def test_phase3():
    """Phase 3のテスト"""
    print("\n" + "=" * 60)
    print("🚀 Phase 3: Tailscale直結 - 接続確認")
    print("=" * 60)

    try:
        from tailscale_runpod_connector import TailscaleRunPodConnector

        connector = TailscaleRunPodConnector()

        print("\n1️⃣ Tailscale接続テスト...")
        result = connector.test_connection()

        if result.get("success"):
            print("✅ Tailscale接続成功")
            print(f"   IP: {result.get('tailscale_ip')}")
            print("   Ping: ✅")
            print("   SSH: ✅")

            print("\n2️⃣ GPU情報取得...")
            gpu_info = connector.get_gpu_info()
            if gpu_info.get("success"):
                print("✅ GPU情報取得成功")
                print(f"   GPU名: {gpu_info.get('gpu_name')}")
                print(f"   メモリ: {gpu_info.get('memory_total_mb')}MB")
            else:
                print(f"❌ GPU情報取得失敗: {gpu_info.get('error')}")

            return True
        else:
            print("❌ Tailscale接続失敗")
            print(f"   Ping: {'✅' if result.get('ping') else '❌'}")
            print(f"   SSH: {'✅' if result.get('ssh') else '❌'}")
            print("\n💡 RunPod側でTailscaleを起動してください:")
            print("   1. RunPod Web Terminalで tailscale up")
            print("   2. 認証URLで認証")
            print("   3. Tailscale IPを確認")
            return False

    except Exception as e:
        print(f"❌ Phase 3テストエラー: {e}")
        return False


def main():
    """メインテスト"""
    print("🧪 RunPod GPU統合 - 全Phase実用テスト")
    print("=" * 60)

    results = {}

    # Phase 2テスト（最も確実）
    results["phase2"] = test_phase2()

    # Phase 1テスト
    results["phase1"] = test_phase1()

    # Phase 3テスト
    results["phase3"] = test_phase3()

    # 結果サマリー
    print("\n" + "=" * 60)
    print("📊 テスト結果サマリー")
    print("=" * 60)

    for phase, result in results.items():
        status = "✅ 動作可能" if result else "⚠️  要設定"
        print(f"  {phase.upper()}: {status}")

    print("\n💡 推奨される次のステップ:")

    if results["phase2"]:
        print("   ✅ Phase 2は使用可能です！")
        print("      - 画像生成ジョブを投入できます")
        print("      - RunPod Workerを起動すれば処理されます")

    if not results["phase1"]:
        print("   📝 Phase 1を使う場合: modal token set")

    if not results["phase3"]:
        print("   📝 Phase 3を使う場合: RunPod側でTailscale起動")

    print("\n🎉 テスト完了！")

    return 0


if __name__ == "__main__":
    sys.exit(main())









