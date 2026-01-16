"""
マナごのみのムフフ動画生成スクリプト（LTX-2使用）
Super LTX-2設定でムフフ動画を生成
"""

import sys
import os
import io
from pathlib import Path
from typing import Optional

# Windows環境での文字エンコーディング設定
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding='utf-8', errors='replace'
    )
    sys.stderr = io.TextIOWrapper(
        sys.stderr.buffer, encoding='utf-8', errors='replace'
    )

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent))

try:
    from ltx2_video_integration import LTX2VideoIntegration
except ImportError:
    print("❌ LTX-2統合モジュールが見つかりません")
    print("ltx2_video_integration.pyが存在するか確認してください")
    sys.exit(1)


def find_mufufu_images():
    """ムフフ画像を探す"""
    # 環境変数から取得、デフォルト値あり
    user_home = Path.home()
    onedrive_desktop = user_home / "OneDrive" / "Desktop"
    desktop = user_home / "Desktop"

    default_path1 = str(onedrive_desktop / "mufufu_cyberrealistic_10")
    default_path2 = str(onedrive_desktop / "output")
    default_path3 = str(
        desktop / "lora_output_mana_favorite_japanese_clear_gal (1)"
    )
    default_path4 = str(onedrive_desktop / "mufufu_combined_10")

    search_paths = [
        Path(os.getenv("MUFUFU_IMAGES_DIR_1", default_path1)),
        Path(os.getenv("MUFUFU_IMAGES_DIR_2", default_path2)),
        Path(os.getenv("MUFUFU_IMAGES_DIR_3", default_path3)),
        Path(os.getenv("MUFUFU_IMAGES_DIR_4", default_path4)),
    ]

    image_extensions = ['.png', '.jpg', '.jpeg']
    found_images = []

    for search_path in search_paths:
        if not search_path.exists():
            continue

        for ext in image_extensions:
            images = list(search_path.glob(f"*{ext}"))
            found_images.extend(images[:5])  # 各フォルダから最大5枚

    return found_images


def generate_mufufu_video(
    start_image_path: str,
    prompt: str = (
        "beautiful character, smooth motion, natural movement, "
        "cinematic, highly detailed"
    ),
    negative_prompt: str = (
        "blurry, low quality, distorted, artifacts, jittery, unnatural"
    ),
    video_length_seconds: int = 5
) -> Optional[str]:
    """
    マナごのみのムフフ動画を生成（Super LTX-2設定）
    
    Args:
        start_image_path: 開始画像のパス
        prompt: プロンプト
        negative_prompt: ネガティブプロンプト
        video_length_seconds: 動画の長さ（秒）
        
    Returns:
        プロンプトID（成功時）、None（失敗時）
    """
    print("🎬 マナごのみのムフフ動画生成を開始（Super LTX-2設定）...")
    print(f"   開始画像: {Path(start_image_path).name}")
    print(f"   プロンプト: {prompt[:60]}...")
    print(f"   動画長: {video_length_seconds}秒")
    setting_msg = "2段階生成 + NAG + res_2sサンプラー（推奨設定）"
    print(f"   設定: {setting_msg}\n")

    try:
        # LTX-2統合を初期化
        ltx2 = LTX2VideoIntegration()

        # ComfyUIに接続できるか確認
        if not ltx2.is_available():
            print("❌ ComfyUIに接続できません")
            comfyui_url = "http://localhost:8188"
            print(f"   ComfyUIが起動しているか確認してください: {comfyui_url}")
            return None

        print("   ✅ ComfyUIに接続できました")
        print()

        # 動画生成
        prompt_id = ltx2.generate_video(
            start_image_path=start_image_path,
            prompt=prompt,
            negative_prompt=negative_prompt,
            video_length_seconds=video_length_seconds,
            width=512,
            height=512,
            use_two_pass=True,  # 推奨設定
            use_nag=True,  # 推奨設定
            use_res2s_sampler=True,  # 推奨設定
            model_name="ltx-2-19b-distilled.safetensors"
        )

        if prompt_id:
            print("✅ 動画生成が開始されました")
            print(f"   プロンプトID: {prompt_id}")
            return prompt_id
        else:
            print("❌ 動画生成に失敗しました")
            return None
    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """メイン関数"""
    print("=" * 60)
    print("マナごのみのムフフ動画生成（LTX-2 Super設定）")
    print("=" * 60)
    print()

    # 画像を探す
    print("[1] ムフフ画像を検索中...")
    images = find_mufufu_images()

    if not images:
        print("   ⚠️ ムフフ画像が見つかりませんでした")
        print("   画像パスを手動で指定してください")
        print()
        msg = "画像パスを入力してください（Enterでスキップ）: "
        image_path = input(msg).strip()
        if not image_path:
            print("   スキップしました")
            return
        image_path = Path(image_path)
    else:
        print(f"   ✅ {len(images)}枚の画像が見つかりました")
        print()
        print("   見つかった画像:")
        for i, img in enumerate(images[:5], 1):
            print(f"   {i}. {img.name}")
        print()

        # 最初の画像を使用
        image_path = images[0]
        print(f"   使用する画像: {image_path.name}")
        print()

    if not Path(image_path).exists():
        print(f"❌ 画像が見つかりません: {image_path}")
        return

    # マナごのみのプロンプト
    # generate_mana_mufufu.pyを参考にしたプロンプト
    quality_tags = (
        "masterpiece, best quality, ultra detailed, 8k, "
        "cinematic lighting, depth of field, soft skin, "
        "beautiful anatomy"
    )
    prompt = (
        f"{quality_tags}, beautiful character, smooth motion, "
        "natural movement, cinematic, highly detailed"
    )
    negative_prompt = (
        "blurry, low quality, distorted, artifacts, jittery, "
        "unnatural, bad anatomy, bad proportions, worst quality, "
        "low quality, bad hands, missing fingers, extra digit, "
        "fewer digits, cropped, jpeg artifacts, signature, "
        "watermark, username"
    )

    print("[2] 動画生成を開始...")
    print(f"   開始画像: {image_path}")
    print(f"   プロンプト: {prompt}")
    print()
    
    # 動画生成
    prompt_id = generate_mufufu_video(
        start_image_path=str(image_path),
        prompt=prompt,
        negative_prompt=negative_prompt,
        video_length_seconds=5
    )
    
    if prompt_id:
        print()
        print("=" * 60)
        print("✅ 動画生成が開始されました！")
        print("=" * 60)
        print()
        print("次のステップ:")
        comfyui_url = "http://localhost:8188"
        print(f"   1. ComfyUIのUIで確認: {comfyui_url}")
        print(f"   2. プロンプトID: {prompt_id}")
        status_url = f"http://localhost:9500/api/ltx2/status/{prompt_id}"
        print(f"   3. 状態確認: curl {status_url}")
        print()
        print("💡 ヒント:")
        print("   - 生成状況はComfyUIのUIで確認できます")
        queue_url = "http://localhost:9500/api/ltx2/queue"
        print(f"   - キュー状態: curl {queue_url}")
        history_url = "http://localhost:9500/api/ltx2/history"
        print(f"   - 履歴: curl {history_url}")
    else:
        print()
        print("❌ 動画生成に失敗しました")
        print("   エラーログを確認してください")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[INFO] 処理が中断されました")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] 予期しないエラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
