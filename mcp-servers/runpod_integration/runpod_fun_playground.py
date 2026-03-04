#!/usr/bin/env python3
"""
RunPodでいろいろ遊んでみる！
画像生成、超解像、動画生成、バッチ処理などを試す
"""

import sys
from pathlib import Path
from datetime import datetime
import time

sys.path.insert(0, '/root/runpod_integration')
sys.path.insert(0, '/root')

def test_image_generation():
    """画像生成テスト"""
    print("🎨 画像生成テスト")
    print("=" * 60)

    try:
        # RunPod Serverless
        sys.path.insert(0, '/root/archive/dummy_systems/20251106')
        from runpod_serverless_client import RunPodServerlessClient

        client = RunPodServerlessClient()

        prompts = [
            "beautiful anime-style character, kawaii, colorful, high quality",
            "gorgeous landscape with mountains and lake, sunset, 4k",
            "cute robot, futuristic design, detailed, vibrant colors",
            "elegant woman in traditional Japanese kimono, cherry blossoms, artistic",
            "fantasy castle in the clouds, magical atmosphere, detailed illustration"
        ]

        results = []
        for i, prompt in enumerate(prompts, 1):
            print(f"\n[{i}/{len(prompts)}] 生成中: {prompt[:50]}...")

            result = client.generate_image(
                prompt=prompt,
                model="stable_diffusion",
                width=1024,
                height=768,
                steps=30,
                negative_prompt="nsfw, low quality, blurry"
            )

            if result.get('status') == 'completed':
                print("  ✅ 成功")
                results.append({
                    "prompt": prompt,
                    "success": True
                })
            else:
                print(f"  ❌ 失敗: {result.get('error')}")
                results.append({
                    "prompt": prompt,
                    "success": False,
                    "error": result.get('error')
                })

            time.sleep(2)  # レート制限対策

        print(f"\n✅ 画像生成完了: {sum(1 for r in results if r['success'])}/{len(results)}枚成功")
        return results

    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return []


def test_batch_processing():
    """バッチ処理テスト"""
    print("\n📦 バッチ処理テスト")
    print("=" * 60)

    try:
        from generate_mufufu_batch import generate_mufufu_batch

        print("バッチ生成を実行中...")
        generate_mufufu_batch(count=5)

        print("✅ バッチ処理完了")

    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()


def test_auto_mode():
    """自動モードテスト"""
    print("\n🤖 自動モードテスト")
    print("=" * 60)

    try:
        from auto_processor import AutoProcessor

        processor = AutoProcessor()

        # 自動画像生成を有効化
        print("自動画像生成を有効化...")
        processor.enable_auto_generate(
            prompts=[
                "beautiful anime character, kawaii style",
                "gorgeous landscape, mountains, sunset",
                "cute robot, futuristic design"
            ],
            interval_minutes=5,  # テスト用に5分間隔
            count_per_run=2
        )

        # 自動超解像を有効化
        print("自動超解像を有効化...")
        processor.enable_auto_upscale(scale=2, method="simple")

        # 開始
        print("自動処理を開始...")
        processor.start()

        print("✅ 自動モード開始")
        print("   5分後に自動画像生成が実行されます")
        print("   停止するには: processor.stop()")

        # 少し待機（テスト用）
        time.sleep(10)

        # ステータス確認
        status = processor.get_status()
        stats = processor.get_stats()

        print("\n📊 ステータス:")
        print(f"   実行中: {status['running']}")
        print(f"   統計: {stats}")

        return processor

    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_gallery_integration():
    """ギャラリー統合テスト"""
    print("\n🖼️  ギャラリー統合テスト")
    print("=" * 60)

    try:
        gallery_dir = Path("/root/trinity_workspace/generated_images")
        gallery_dir.mkdir(parents=True, exist_ok=True)

        # 画像一覧
        all_images = list(gallery_dir.glob("*.png"))
        mufufu_images = [img for img in all_images if 'mufufu' in img.name.lower()]
        runpod_images = [img for img in all_images if 'runpod' in img.name.lower()]
        modal_images = [img for img in all_images if 'modal' in img.name.lower()]

        print("📁 ギャラリー統計:")
        print(f"   総画像数: {len(all_images)}枚")
        print(f"   ムフフ画像: {len(mufufu_images)}枚")
        print(f"   RunPod画像: {len(runpod_images)}枚")
        print(f"   Modal画像: {len(modal_images)}枚")

        # 最新の画像を表示
        if all_images:
            latest_images = sorted(all_images, key=lambda x: x.stat().st_mtime, reverse=True)[:5]
            print("\n📸 最新の5枚:")
            for img in latest_images:
                size = img.stat().st_size / 1024
                mtime = datetime.fromtimestamp(img.stat().st_mtime)
                print(f"   - {img.name}")
                print(f"     サイズ: {size:.1f} KB, 更新: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")

        print("\n✅ ギャラリー統合確認完了")

    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()


def interactive_menu():
    """対話型メニュー"""
    print("\n🎮 RunPod遊び場 - メニュー")
    print("=" * 60)
    print("1. 画像生成テスト")
    print("2. バッチ処理テスト")
    print("3. 自動モードテスト")
    print("4. ギャラリー統合テスト")
    print("5. すべて実行")
    print("0. 終了")
    print()

    choice = input("選択してください (0-5): ").strip()

    if choice == "1":
        test_image_generation()
    elif choice == "2":
        test_batch_processing()
    elif choice == "3":
        processor = test_auto_mode()
        if processor:
            input("\nEnterキーで停止...")
            processor.stop()
    elif choice == "4":
        test_gallery_integration()
    elif choice == "5":
        test_image_generation()
        test_batch_processing()
        test_gallery_integration()
        processor = test_auto_mode()
        if processor:
            input("\nEnterキーで停止...")
            processor.stop()
    elif choice == "0":
        print("終了します")
        return
    else:
        print("無効な選択です")

    print("\n" + "=" * 60)
    print("🎉 完了！")


def main():
    """メイン処理"""
    print("🚀 RunPodでいろいろ遊んでみる！")
    print("=" * 60)
    print()

    import argparse

    parser = argparse.ArgumentParser(description="RunPod遊び場")
    parser.add_argument("--all", action="store_true", help="すべてのテストを実行")
    parser.add_argument("--interactive", action="store_true", help="対話型メニュー")
    parser.add_argument("--generate", action="store_true", help="画像生成のみ")
    parser.add_argument("--batch", action="store_true", help="バッチ処理のみ")
    parser.add_argument("--auto", action="store_true", help="自動モードのみ")
    parser.add_argument("--gallery", action="store_true", help="ギャラリー統合のみ")

    args = parser.parse_args()

    if args.interactive:
        while True:
            interactive_menu()
    elif args.all:
        test_image_generation()
        test_batch_processing()
        test_gallery_integration()
        processor = test_auto_mode()
        if processor:
            print("\n自動モードは起動中です。停止するにはCtrl+C")
            try:
                while True:
                    time.sleep(60)
            except KeyboardInterrupt:
                processor.stop()
    elif args.generate:
        test_image_generation()
    elif args.batch:
        test_batch_processing()
    elif args.auto:
        processor = test_auto_mode()
        if processor:
            print("\n自動モードは起動中です。停止するにはCtrl+C")
            try:
                while True:
                    time.sleep(60)
            except KeyboardInterrupt:
                processor.stop()
    elif args.gallery:
        test_gallery_integration()
    else:
        # デフォルト: すべて実行（非対話型）
        test_image_generation()
        test_batch_processing()
        test_gallery_integration()
        print("\n✅ すべてのテスト完了！")


if __name__ == "__main__":
    main()




