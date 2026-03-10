# -*- coding: utf-8 -*-
"""
日本人清楚ギャルの特徴を強調したキャプションに改善
"""

import os
from pathlib import Path
import sys
import io

# Windowsでの文字エンコーディング問題を回避
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def create_improved_caption(image_name):
    """
    日本人清楚ギャルの特徴を強調したキャプションを作成
    
    特徴:
    - 日本人の顔立ち（目が大きく、肌が白い、顔が小さい）
    - 清楚系ギャル（清潔感、上品、でもギャル要素）
    - 髪型（ロング、ストレート、前髪）
    - メイク（ナチュラルメイク、でもしっかり）
    - 表情（優しい、清楚、笑顔）
    """
    
    # ベース要素（全画像共通）
    base_elements = [
        "manaPerson",  # 固有トークン（最重要）
        "japanese clear gal",
        "japanese woman",
        "clear pure gal style",
        "beautiful japanese face",
        "large eyes",
        "white skin",
        "small face",
        "long straight hair",
        "bangs",
        "natural makeup",
        "gentle expression",
        "clear pure aesthetic",
        "high quality",
        "photorealistic",
        "detailed face"
    ]
    
    return ", ".join(base_elements)


def improve_captions_in_directory(dataset_dir):
    """データセットディレクトリ内の全画像のキャプションを改善"""
    dataset_dir = Path(dataset_dir)
    
    if not dataset_dir.exists():
        print(f"エラー: ディレクトリが見つかりません: {dataset_dir}")
        return
    
    print("=" * 80)
    print("日本人清楚ギャルキャプション改善")
    print("=" * 80)
    print(f"データセット: {dataset_dir}")
    print()
    
    # 画像ファイルを取得
    image_extensions = [".png", ".jpg", ".jpeg", ".webp"]
    image_files = []
    for ext in image_extensions:
        image_files.extend(list(dataset_dir.glob(f"*{ext}")))
        image_files.extend(list(dataset_dir.glob(f"*{ext.upper()}")))
    
    if not image_files:
        print(f"エラー: 画像ファイルが見つかりません: {dataset_dir}")
        return
    
    print(f"見つかった画像: {len(image_files)} 枚")
    print()
    
    # 各画像のキャプションを更新
    updated_count = 0
    created_count = 0
    
    for image_file in image_files:
        # 対応するテキストファイル
        caption_file = image_file.with_suffix('.txt')
        
        # 改善されたキャプションを作成
        improved_caption = create_improved_caption(image_file.name)
        
        # キャプションファイルに書き込み
        try:
            with open(caption_file, 'w', encoding='utf-8') as f:
                f.write(improved_caption)
            
            if caption_file.exists() and caption_file.stat().st_size > 0:
                updated_count += 1
                print(f"✓ 更新: {image_file.name}")
            else:
                created_count += 1
                print(f"✓ 作成: {image_file.name}")
        
        except Exception as e:
            print(f"✗ エラー ({image_file.name}): {e}")
    
    print()
    print("=" * 80)
    print(f"完了: {updated_count} 個更新, {created_count} 個作成")
    print("=" * 80)
    print()
    print("改善されたキャプションのサンプル:")
    print(f"  {improved_caption}")  # type: ignore[possibly-unbound]
    print()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="日本人清楚ギャルキャプション改善")
    parser.add_argument("--dataset_dir", type=str, default="lora_dataset_mana_favorite_20",
                       help="データセットディレクトリ")
    
    args = parser.parse_args()
    
    improve_captions_in_directory(args.dataset_dir)


