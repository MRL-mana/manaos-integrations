#!/usr/bin/env python3
"""
データセット管理システム
学習用画像データセットの作成・管理
"""

import sys
from pathlib import Path
from datetime import datetime
import json
import shutil
from typing import List, Dict, Any

sys.path.insert(0, '/root/runpod_integration')
sys.path.insert(0, '/root')


class DatasetManager:
    """データセット管理クラス"""

    def __init__(self, base_dir: str = "/root/runpod_integration/datasets"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def create_dataset(
        self,
        dataset_name: str,
        image_paths: List[str],
        trigger_word: str,
        description: str = ""
    ) -> Dict[str, Any]:
        """
        データセットを作成

        Args:
            dataset_name: データセット名
            image_paths: 画像パスのリスト
            trigger_word: トリガーワード
            description: 説明

        Returns:
            結果辞書
        """
        dataset_dir = self.base_dir / dataset_name
        dataset_dir.mkdir(parents=True, exist_ok=True)

        # 画像をコピー
        copied_images = []
        for i, img_path in enumerate(image_paths):
            img_path_obj = Path(img_path)
            if not img_path_obj.exists():
                continue

            # 画像をコピー
            dest_path = dataset_dir / f"{i:04d}.png"
            shutil.copy2(img_path_obj, dest_path)
            copied_images.append(dest_path.name)

        if not copied_images:
            return {
                "success": False,
                "error": "有効な画像が見つかりません"
            }

        # メタデータファイルを作成
        metadata_file = dataset_dir / "metadata.jsonl"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            for img_name in copied_images:
                f.write(f'{{"file_name": "{img_name}", "text": "{trigger_word}"}}\n')

        # データセット情報を保存
        info_file = dataset_dir / "dataset_info.json"
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump({
                "name": dataset_name,
                "trigger_word": trigger_word,
                "description": description,
                "image_count": len(copied_images),
                "created_at": datetime.now().isoformat()
            }, f, indent=2, ensure_ascii=False)

        return {
            "success": True,
            "dataset_path": str(dataset_dir),
            "image_count": len(copied_images),
            "trigger_word": trigger_word
        }

    def list_datasets(self) -> List[Dict[str, Any]]:
        """データセット一覧を取得"""
        datasets = []

        for dataset_dir in self.base_dir.iterdir():
            if not dataset_dir.is_dir():
                continue

            info_file = dataset_dir / "dataset_info.json"
            if info_file.exists():
                with open(info_file, 'r', encoding='utf-8') as f:
                    info = json.load(f)
                    datasets.append({
                        "name": dataset_dir.name,
                        "path": str(dataset_dir),
                        **info
                    })

        return datasets

    def get_dataset_info(self, dataset_name: str) -> Dict[str, Any]:
        """データセット情報を取得"""
        dataset_dir = self.base_dir / dataset_name

        if not dataset_dir.exists():
            return {
                "success": False,
                "error": f"データセットが見つかりません: {dataset_name}"
            }

        info_file = dataset_dir / "dataset_info.json"
        if info_file.exists():
            with open(info_file, 'r', encoding='utf-8') as f:
                info = json.load(f)
                return {
                    "success": True,
                    **info
                }
        else:
            return {
                "success": False,
                "error": "データセット情報ファイルが見つかりません"
            }

    def delete_dataset(self, dataset_name: str) -> Dict[str, Any]:
        """データセットを削除"""
        dataset_dir = self.base_dir / dataset_name

        if not dataset_dir.exists():
            return {
                "success": False,
                "error": f"データセットが見つかりません: {dataset_name}"
            }

        try:
            shutil.rmtree(dataset_dir)
            return {
                "success": True,
                "message": f"データセット '{dataset_name}' を削除しました"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


def main():
    """メイン処理"""
    manager = DatasetManager()

    print("📚 データセット管理システム")
    print("=" * 60)
    print()

    # データセット一覧を表示
    print("📁 データセット一覧:")
    datasets = manager.list_datasets()

    if datasets:
        for dataset in datasets:
            print(f"  - {dataset['name']}")
            print(f"    トリガーワード: {dataset['trigger_word']}")
            print(f"    画像数: {dataset['image_count']}枚")
            print(f"    作成日時: {dataset.get('created_at', '不明')}")
            print()
    else:
        print("  （データセットなし）")
        print()
        print("💡 データセットを作成するには:")
        print("   manager = DatasetManager()")
        print("   manager.create_dataset(")
        print("       dataset_name='my_dataset',")
        print("       image_paths=['/path/to/img1.png', ...],")
        print("       trigger_word='my_trigger'")
        print("   )")


if __name__ == "__main__":
    main()








