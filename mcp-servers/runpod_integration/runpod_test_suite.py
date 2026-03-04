#!/usr/bin/env python3
"""
RunPod統合テストスイート
実際にRunPodでいろいろやってみる！
"""

import sys
from pathlib import Path
from datetime import datetime
import json

sys.path.insert(0, '/root/runpod_integration')
sys.path.insert(0, '/root')

def test_runpod_services():
    """RunPod関連サービスのテスト"""
    print("🚀 RunPod統合テストスイート")
    print("=" * 60)
    print()

    results = {
        "timestamp": datetime.now().isoformat(),
        "tests": []
    }

    # 1. Modal.com（Phase 1）テスト
    print("1️⃣ Modal.com テスト...")
    try:
        from manaos_modal_client import ManaOSModalClient
        client = ManaOSModalClient()

        # ヘルスチェック
        if client.check_modal_auth():
            print("  ✅ Modal.com認証: OK")
            results["tests"].append({
                "name": "Modal.com認証",
                "status": "success"
            })

            # 簡単な画像生成テスト
            print("  🎨 画像生成テスト...")
            result = client.generate_image(
                prompt="A beautiful landscape with mountains",
                steps=20
            )

            if result.get('success'):
                print(f"  ✅ 画像生成成功: {result.get('path')}")
                results["tests"].append({
                    "name": "Modal.com画像生成",
                    "status": "success",
                    "path": result.get('path')
                })
            else:
                print(f"  ❌ 画像生成失敗: {result.get('error')}")
                results["tests"].append({
                    "name": "Modal.com画像生成",
                    "status": "failed",
                    "error": result.get('error')
                })
        else:
            print("  ❌ Modal.com認証: NG")
            results["tests"].append({
                "name": "Modal.com認証",
                "status": "failed",
                "error": "認証失敗"
            })
    except Exception as e:
        print(f"  ❌ Modal.comテストエラー: {e}")
        results["tests"].append({
            "name": "Modal.comテスト",
            "status": "error",
            "error": str(e)
        })

    print()

    # 2. RunPod Serverlessテスト
    print("2️⃣ RunPod Serverless テスト...")
    try:
        # RunPod Serverless Clientを探す
        runpod_serverless_available = False

        # パス1: manaos_unified_system
        try:
            from manaos_unified_system.services.runpod_serverless_client import RunPodServerlessClient
            runpod_client_class = RunPodServerlessClient
            runpod_serverless_available = True
            print("  ✅ RunPod Serverless Client: 見つかりました")
        except ImportError:
            # パス2: archive
            try:
                sys.path.insert(0, '/root/archive/dummy_systems/20251106')
                from runpod_serverless_client import RunPodServerlessClient
                runpod_client_class = RunPodServerlessClient
                runpod_serverless_available = True
                print("  ✅ RunPod Serverless Client (archive): 見つかりました")
            except ImportError:
                print("  ⚠️  RunPod Serverless Client: 見つかりません")

        if runpod_serverless_available:
            client = runpod_client_class()

            # 画像生成テスト
            print("  🎨 画像生成テスト...")
            result = client.generate_image(
                prompt="A cute anime character",
                model="stable_diffusion",
                width=1024,
                height=768,
                steps=25
            )

            if result.get('status') == 'completed':
                print("  ✅ RunPod Serverless画像生成成功")
                results["tests"].append({
                    "name": "RunPod Serverless画像生成",
                    "status": "success"
                })
            else:
                print(f"  ❌ RunPod Serverless画像生成失敗: {result.get('error')}")
                results["tests"].append({
                    "name": "RunPod Serverless画像生成",
                    "status": "failed",
                    "error": result.get('error')
                })
        else:
            results["tests"].append({
                "name": "RunPod Serverless",
                "status": "skipped",
                "error": "Client not found"
            })
    except Exception as e:
        print(f"  ❌ RunPod Serverlessテストエラー: {e}")
        results["tests"].append({
            "name": "RunPod Serverlessテスト",
            "status": "error",
            "error": str(e)
        })

    print()

    # 3. ギャラリー統合テスト
    print("3️⃣ ギャラリー統合テスト...")
    try:
        gallery_dir = Path("/root/trinity_workspace/generated_images")
        gallery_dir.mkdir(parents=True, exist_ok=True)

        # ギャラリーファイル数を確認
        image_files = list(gallery_dir.glob("*.png"))
        print(f"  📁 ギャラリー画像数: {len(image_files)}枚")

        # 最新の画像を確認
        if image_files:
            latest_image = max(image_files, key=lambda x: x.stat().st_mtime)
            print(f"  📸 最新画像: {latest_image.name}")

        results["tests"].append({
            "name": "ギャラリー統合",
            "status": "success",
            "image_count": len(image_files)
        })
    except Exception as e:
        print(f"  ❌ ギャラリー統合テストエラー: {e}")
        results["tests"].append({
            "name": "ギャラリー統合テスト",
            "status": "error",
            "error": str(e)
        })

    print()

    # 4. 自動処理システムテスト
    print("4️⃣ 自動処理システムテスト...")
    try:
        from auto_processor import AutoProcessor
        processor = AutoProcessor()

        # ステータス取得
        status = processor.get_status()
        stats = processor.get_stats()

        print(f"  🔄 実行中: {'はい' if status['running'] else 'いいえ'}")
        print("  📊 統計:")
        print(f"     生成画像: {stats.get('total_generated', 0)}枚")
        print(f"     超解像: {stats.get('total_upscaled', 0)}枚")
        print(f"     GIF生成: {stats.get('total_gifs', 0)}個")
        print(f"     LoRA学習: {stats.get('total_trainings', 0)}回")

        results["tests"].append({
            "name": "自動処理システム",
            "status": "success",
            "running": status['running'],
            "stats": stats
        })
    except Exception as e:
        print(f"  ❌ 自動処理システムテストエラー: {e}")
        results["tests"].append({
            "name": "自動処理システムテスト",
            "status": "error",
            "error": str(e)
        })

    print()

    # 結果サマリー
    print("=" * 60)
    print("📊 テスト結果サマリー")
    print("=" * 60)

    success_count = sum(1 for t in results["tests"] if t.get("status") == "success")
    failed_count = sum(1 for t in results["tests"] if t.get("status") == "failed")
    error_count = sum(1 for t in results["tests"] if t.get("status") == "error")
    skipped_count = sum(1 for t in results["tests"] if t.get("status") == "skipped")

    print(f"✅ 成功: {success_count}")
    print(f"❌ 失敗: {failed_count}")
    print(f"💥 エラー: {error_count}")
    print(f"⏭️  スキップ: {skipped_count}")
    print()

    # 結果を保存
    result_file = Path("/root/runpod_integration/test_results.json")
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"💾 結果を保存: {result_file}")
    print()

    # 次のステップ提案
    print("💡 次のステップ:")
    if success_count > 0:
        print("  ✅ テスト成功！実際に使ってみましょう！")
        print("     python3 /root/runpod_integration/generate_mufufu_with_runpod.py")
        print("     または")
        print("     python3 /root/runpod_integration/generate_mufufu_batch.py")
    else:
        print("  ⚠️  設定を確認してください")
        print("     - Modal.com認証: modal token set")
        print("     - RunPod APIキー: 環境変数または設定ファイル")

    print()
    print("🎉 テスト完了！")


def test_batch_generation():
    """バッチ生成テスト"""
    print("\n🎨 バッチ画像生成テスト")
    print("=" * 60)

    try:
        from generate_mufufu_batch import generate_mufufu_batch
        generate_mufufu_batch(count=3)
    except Exception as e:
        print(f"❌ バッチ生成エラー: {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="RunPod統合テストスイート")
    parser.add_argument("--batch", action="store_true", help="バッチ生成も実行")
    args = parser.parse_args()

    test_runpod_services()

    if args.batch:
        test_batch_generation()




