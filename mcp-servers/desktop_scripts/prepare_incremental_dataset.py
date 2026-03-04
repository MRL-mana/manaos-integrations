# -*- coding: utf-8 -*-
"""段階的訓練用データセット準備（30枚ずつ分割）"""

import shutil
from pathlib import Path
import random

def prepare_incremental_datasets(source_dir, output_base_dir, batch_size=30):
    """
    データセットを30枚ずつに分割して、段階的訓練用のディレクトリを作成
    
    Args:
        source_dir: 元のデータセットディレクトリ
        output_base_dir: 出力ベースディレクトリ
        batch_size: 1グループあたりの画像数（デフォルト: 30）
    """
    source_path = Path(source_dir)
    output_base = Path(output_base_dir)
    
    # 画像ファイルとキャプションファイルを取得
    image_files = sorted(source_path.glob("*.png"))
    caption_files = sorted(source_path.glob("*.txt"))
    
    print(f"元のデータセット: {len(image_files)}枚")
    print(f"グループサイズ: {batch_size}枚")
    
    # 画像とキャプションをペアにする
    pairs = []
    for img_file in image_files:
        caption_file = source_path / f"{img_file.stem}.txt"
        if caption_file.exists():
            pairs.append((img_file, caption_file))
        else:
            print(f"警告: {img_file.name}に対応するキャプションファイルが見つかりません")
    
    # シャッフル（オプション）
    random.seed(42)
    random.shuffle(pairs)
    
    # グループに分割
    num_groups = (len(pairs) + batch_size - 1) // batch_size
    print(f"グループ数: {num_groups}")
    
    # 各グループのディレクトリを作成
    for group_idx in range(num_groups):
        start_idx = group_idx * batch_size
        end_idx = min(start_idx + batch_size, len(pairs))
        group_pairs = pairs[start_idx:end_idx]
        
        # グループディレクトリを作成
        group_dir = output_base / f"group_{group_idx + 1:02d}"
        group_dir.mkdir(parents=True, exist_ok=True)
        
        # 画像とキャプションをコピー
        for img_file, caption_file in group_pairs:
            shutil.copy2(img_file, group_dir / img_file.name)
            shutil.copy2(caption_file, group_dir / caption_file.name)
        
        print(f"グループ {group_idx + 1}: {len(group_pairs)}枚 → {group_dir}")
    
    # 累積データセットも作成（1グループ目、1-2グループ目、1-3グループ目...）
    print("\n累積データセットを作成中...")
    for cumulative_idx in range(1, num_groups + 1):
        cumulative_dir = output_base / f"cumulative_{cumulative_idx:02d}"
        cumulative_dir.mkdir(parents=True, exist_ok=True)
        
        # 1グループ目から現在のグループまでをコピー
        for group_idx in range(cumulative_idx):
            group_dir = output_base / f"group_{group_idx + 1:02d}"
            for img_file in group_dir.glob("*.png"):
                caption_file = group_dir / f"{img_file.stem}.txt"
                shutil.copy2(img_file, cumulative_dir / img_file.name)
                if caption_file.exists():
                    shutil.copy2(caption_file, cumulative_dir / caption_file.name)
        
        num_images = len(list(cumulative_dir.glob("*.png")))
        print(f"累積 {cumulative_idx}: {num_images}枚 → {cumulative_dir}")
    
    print(f"\n完了！")
    print(f"出力先: {output_base}")
    print(f"\n使用方法:")
    print(f"  1. グループ1で訓練開始")
    print(f"  2. チェックポイントから続けて、累積2で訓練")
    print(f"  3. チェックポイントから続けて、累積3で訓練")
    print(f"  ... これを繰り返す")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="段階的訓練用データセット準備")
    parser.add_argument("--source_dir", type=str, default="lora_dataset_mana_favorite",
                       help="元のデータセットディレクトリ")
    parser.add_argument("--output_dir", type=str, default="lora_dataset_mana_favorite_incremental",
                       help="出力ディレクトリ")
    parser.add_argument("--batch_size", type=int, default=30,
                       help="1グループあたりの画像数")
    
    args = parser.parse_args()
    
    prepare_incremental_datasets(
        source_dir=args.source_dir,
        output_base_dir=args.output_dir,
        batch_size=args.batch_size
    )

