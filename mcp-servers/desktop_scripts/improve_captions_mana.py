# -*- coding: utf-8 -*-
"""
LoRA訓練用キャプション改善スクリプト
固有トークン「manaPerson」を追加し、画像ごとの属性を付与
"""

import os
from pathlib import Path
from PIL import Image
import sys
import io

# Windowsでの文字エンコーディング問題を回避
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def analyze_image_for_caption(image_path):
    """
    画像を分析してキャプションに追加する属性を推測
    （簡易版：実際には画像認識APIを使うか、手動で確認する必要がある）
    """
    # 実際の実装では、画像を開いて分析する
    # ここではプレースホルダーとして基本的な形式を返す
    return {
        "base": "manaPerson, woman",
        "attributes": [
            "portrait",
            "close-up",
            "looking at viewer",
            "beautiful face"
        ]
    }


def create_improved_caption(image_path, base_attributes=None):
    """
    改善されたキャプションを作成
    
    形式: manaPerson, woman, [属性1], [属性2], ...
    
    Args:
        image_path: 画像ファイルのパス
        base_attributes: 基本的な属性リスト（オプション）
    
    Returns:
        改善されたキャプション文字列
    """
    if base_attributes is None:
        base_attributes = [
            "portrait",
            "beautiful face",
            "high quality"
        ]
    
    # 固有トークン + 基本タグ + 属性タグ
    caption_parts = ["manaPerson", "woman"] + base_attributes
    
    return ", ".join(caption_parts)


def improve_all_captions(dataset_dir, dry_run=True):
    """
    データセット内の全キャプションファイルを改善
    
    Args:
        dataset_dir: データセットディレクトリ
        dry_run: Trueの場合、実際には書き込まない（確認のみ）
    """
    dataset_path = Path(dataset_dir)
    
    if not dataset_path.exists():
        print(f"[ERROR] データセットディレクトリが存在しません: {dataset_dir}")
        return
    
    # 画像ファイルを取得
    image_files = sorted(list(dataset_path.glob("*.png")))
    
    if not image_files:
        print(f"[ERROR] 画像ファイルが見つかりません: {dataset_dir}")
        return
    
    print(f"キャプション改善対象: {len(image_files)}枚")
    print("=" * 60)
    
    if dry_run:
        print("[DRY RUN] 実際には書き込みません（確認のみ）")
        print("")
    
    for i, image_path in enumerate(image_files, 1):
        caption_path = image_path.with_suffix('.txt')
        
        # 現在のキャプションを読み込み
        old_caption = ""
        if caption_path.exists():
            old_caption = caption_path.read_text(encoding='utf-8').strip()
        
        # 改善されたキャプションを作成
        # 実際には画像を分析して個別の属性を付与する必要がある
        # ここでは基本形を作成
        new_caption = create_improved_caption(image_path)
        
        print(f"[{i}/{len(image_files)}] {image_path.name}")
        print(f"  旧: {old_caption}")
        print(f"  新: {new_caption}")
        
        if not dry_run:
            caption_path.write_text(new_caption, encoding='utf-8')
            print(f"  ✓ 更新しました")
        else:
            print(f"  [DRY RUN] 更新予定")
        
        print("")
    
    if dry_run:
        print("=" * 60)
        print("[DRY RUN] 確認完了")
        print("実際に更新するには、dry_run=False で実行してください")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="LoRA訓練用キャプション改善")
    parser.add_argument(
        "--dataset_dir",
        type=str,
        default="lora_dataset_mana_favorite_20",
        help="データセットディレクトリ",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="実際にキャプションを更新する（指定しない場合はDRY RUN）",
    )
    
    args = parser.parse_args()
    
    dry_run = not args.apply
    
    if dry_run:
        print("=" * 60)
        print("キャプション改善（DRY RUN）")
        print("=" * 60)
        print("")
        print("実際に更新するには --apply オプションを付けて実行してください")
        print("")
    else:
        print("=" * 60)
        print("キャプション改善（実際に更新します）")
        print("=" * 60)
        print("")
        response = input("本当に更新しますか？ (yes/no): ")
        if response.lower() != "yes":
            print("キャンセルしました")
            return
    
    improve_all_captions(args.dataset_dir, dry_run=dry_run)
    
    if not dry_run:
        print("=" * 60)
        print("キャプション改善が完了しました")
        print("=" * 60)
        print("")
        print("次のステップ:")
        print("1. 生成されたキャプションを確認")
        print("2. 必要に応じて手動で調整（画像ごとの個別属性を追加）")
        print("3. 訓練を再実行")


if __name__ == "__main__":
    main()



