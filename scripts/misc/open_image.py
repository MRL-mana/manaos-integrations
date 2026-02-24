"""
画像を開くスクリプト
"""
import os
import sys
from pathlib import Path

# 画像ファイルのパス
image_path = Path(__file__).parent / "generated_images" / "sd_20260113_091619_01_managonomi_cute_anime_girl_m.png"

if image_path.exists():
    print(f"画像ファイルを開きます: {image_path}")
    os.startfile(str(image_path))
    print("画像を開きました！")
else:
    print(f"画像ファイルが見つかりません: {image_path}")
    
    # 代替画像を探す
    generated_dir = Path(__file__).parent / "generated_images"
    if generated_dir.exists():
        images = list(generated_dir.glob("*.png"))
        if images:
            print(f"\n見つかった画像ファイル:")
            for img in images:
                print(f"  - {img.name}")
            # 最新の画像を開く
            latest = max(images, key=lambda p: p.stat().st_mtime)
            print(f"\n最新の画像を開きます: {latest.name}")
            os.startfile(str(latest))
        else:
            print("generated_imagesディレクトリに画像ファイルが見つかりません")
    else:
        print("generated_imagesディレクトリが存在しません")
