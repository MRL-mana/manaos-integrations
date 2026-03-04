#!/usr/bin/env python3
"""
RunPod統合 - 実用例
すぐに使えるサンプルコード
"""

import json
from pathlib import Path

# ============================================
# Phase 2: Pull型ワーカー（現在使用可能）
# ============================================

def example_phase2_image_generation():
    """Phase 2で画像生成ジョブを投入"""
    print("🎨 Phase 2: 画像生成ジョブ投入例")
    print("-" * 50)

    from manaos_runpod_client import ManaOSRunPodClient

    client = ManaOSRunPodClient()

    # 画像生成ジョブ投入（非同期）
    result = client.generate_image(
        prompt="A beautiful Japanese landscape with mountains, cherry blossoms, and a traditional temple",
        negative_prompt="ugly, blurry, low quality",
        steps=30,
        width=512,
        height=512,
        wait_for_result=False  # 非同期実行
    )

    if result.get("success"):
        job_id = result.get("job_id")
        print("✅ ジョブ投入成功!")
        print(f"   ジョブID: {job_id}")
        print("\n💡 ジョブ状態確認:")
        print(f"   python3 -c \"from manaos_runpod_client import ManaOSRunPodClient; client = ManaOSRunPodClient(); print(client.get_job_status('{job_id}'))\"")
        return job_id
    else:
        print(f"❌ ジョブ投入失敗: {result.get('error')}")
        return None


def example_phase2_file_upload():
    """Phase 2でファイルをアップロード"""
    print("\n📤 Phase 2: ファイルアップロード例")
    print("-" * 50)

    from manaos_runpod_client import ManaOSRunPodClient

    client = ManaOSRunPodClient()

    # テストファイル作成
    test_file = Path("/tmp/example_upload.txt")
    test_file.write_text("This is a test file for RunPod Phase 2 integration.\n日本語も使えます！")

    # アップロード
    result = client.upload_file(
        str(test_file),
        "examples/upload_test.txt"
    )

    if result.get("success"):
        print("✅ アップロード成功!")
        print(f"   S3パス: {result.get('s3_path')}")
        return True
    else:
        print(f"❌ アップロード失敗: {result.get('error')}")
        return False


def example_phase2_check_status():
    """Phase 2でジョブ状態を確認"""
    print("\n📊 Phase 2: ジョブ状態確認例")
    print("-" * 50)

    from manaos_runpod_client import ManaOSRunPodClient
    from job_queue_manager import JobQueueManager

    client = ManaOSRunPodClient()
    manager = JobQueueManager()

    # キュー状態確認
    queue_length = manager.get_queue_length()
    pending_jobs = manager.get_pending_jobs()

    print(f"キュー長: {queue_length}")
    print(f"待機中ジョブ数: {len(pending_jobs)}")

    if pending_jobs:
        # 最新のジョブを確認
        latest_job = pending_jobs[-1]
        status = client.get_job_status(latest_job)

        print(f"\n最新ジョブ: {latest_job}")
        print(f"ステータス: {status.get('status', '不明')}")

        if status.get('result'):
            print("✅ 結果が利用可能です!")
            print(json.dumps(status.get('result'), indent=2, ensure_ascii=False)[:200] + "...")


def example_phase2_list_files():
    """Phase 2でS3ファイル一覧を取得"""
    print("\n📋 Phase 2: S3ファイル一覧例")
    print("-" * 50)

    from manaos_runpod_client import ManaOSRunPodClient

    client = ManaOSRunPodClient()

    # ファイル一覧取得
    files = client.list_s3_files()

    print(f"ファイル数: {files.get('count', 0)}")

    if files.get('files'):
        print("\nファイル一覧:")
        for f in files.get('files', [])[:10]:  # 最新10件
            print(f"  📄 {f.get('key')} - {f.get('size')} bytes")


# ============================================
# Phase 1: Modal.com（認証後使用可能）
# ============================================

def example_phase1_image_generation():
    """Phase 1で画像生成（認証が必要）"""
    print("\n🎨 Phase 1: Modal.com画像生成例")
    print("-" * 50)

    try:
        from manaos_modal_client import ManaOSModalClient

        client = ManaOSModalClient()

        # 認証確認
        if not client.check_modal_auth():
            print("❌ Modal認証が必要です")
            print("   実行: modal token set")
            return False

        # 画像生成
        result = client.generate_image(
            prompt="A beautiful sunset over mountains",
            steps=20
        )

        if result.get("success"):
            print("✅ 画像生成成功!")
            print(f"   パス: {result.get('path')}")
            return True
        else:
            print(f"❌ 画像生成失敗: {result.get('error')}")
            return False

    except Exception as e:
        print(f"❌ エラー: {e}")
        return False


# ============================================
# Phase 3: Tailscale（接続後使用可能）
# ============================================

def example_phase3_direct_execution():
    """Phase 3で直接実行（Tailscale接続が必要）"""
    print("\n⚡ Phase 3: Tailscale直接実行例")
    print("-" * 50)

    try:
        from manaos_tailscale_client import ManaOSTailscaleClient

        client = ManaOSTailscaleClient()

        # ヘルスチェック
        health = client.health_check()

        if not health.get("success"):
            print("❌ Tailscale接続が必要です")
            print("   RunPod側でTailscaleを起動してください")
            return False

        # GPU情報取得
        gpu_info = client.get_gpu_info()

        if gpu_info.get("success"):
            print("✅ GPU情報取得成功")
            print(f"   GPU名: {gpu_info.get('gpu_name')}")
            print(f"   メモリ: {gpu_info.get('memory_total_mb')}MB")
            return True
        else:
            print(f"❌ GPU情報取得失敗: {gpu_info.get('error')}")
            return False

    except Exception as e:
        print(f"❌ エラー: {e}")
        return False


# ============================================
# メイン実行
# ============================================

def main():
    """メイン実行関数"""
    print("=" * 60)
    print("🚀 RunPod統合 - 実用例")
    print("=" * 60)

    print("\n現在使用可能: Phase 2 (Pull型ワーカー)")
    print("\n" + "=" * 60)

    # Phase 2の例を実行
    example_phase2_image_generation()
    example_phase2_file_upload()
    example_phase2_list_files()
    example_phase2_check_status()

    # Phase 1の例（認証が必要）
    print("\n" + "=" * 60)
    print("認証後使用可能: Phase 1 (Modal.com)")
    print("=" * 60)
    example_phase1_image_generation()

    # Phase 3の例（接続が必要）
    print("\n" + "=" * 60)
    print("接続後使用可能: Phase 3 (Tailscale)")
    print("=" * 60)
    example_phase3_direct_execution()

    print("\n" + "=" * 60)
    print("✅ 実用例完了！")
    print("=" * 60)
    print("\n💡 使い方:")
    print("   python3 example_usage.py")
    print("\n💡 個別に実行:")
    print("   from example_usage import example_phase2_image_generation")
    print("   example_phase2_image_generation()")


if __name__ == "__main__":
    main()









