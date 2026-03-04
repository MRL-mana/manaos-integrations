#!/usr/bin/env python3
"""
バッチ画像処理システム
大量の画像を効率的に処理（生成、超解像、GIF生成など）
"""

import sys
from pathlib import Path
from datetime import datetime
import json
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any

sys.path.insert(0, '/root/runpod_integration')
sys.path.insert(0, '/root')

BASE_URL = "http://localhost:5556"


class BatchProcessor:
    """バッチ処理クラス"""

    def __init__(self, max_workers: int = 3):
        self.max_workers = max_workers
        self.results = []

    def upscale_batch(
        self,
        filenames: List[str],
        scale: int = 2,
        method: str = "simple"
    ) -> List[Dict[str, Any]]:
        """
        複数画像を一括超解像

        Args:
            filenames: 画像ファイル名のリスト
            scale: 拡大倍率
            method: 使用手法

        Returns:
            処理結果のリスト
        """
        print(f"🎨 バッチ超解像開始: {len(filenames)}枚")
        print("=" * 60)

        results = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 各画像の超解像を並列実行
            future_to_filename = {
                executor.submit(self._upscale_single, filename, scale, method): filename
                for filename in filenames
            }

            for i, future in enumerate(as_completed(future_to_filename), 1):
                filename = future_to_filename[future]
                try:
                    result = future.result()
                    results.append(result)

                    if result.get('success'):
                        print(f"[{i}/{len(filenames)}] ✅ {filename}")
                    else:
                        print(f"[{i}/{len(filenames)}] ❌ {filename}: {result.get('error')}")
                except Exception as e:
                    print(f"[{i}/{len(filenames)}] ❌ {filename}: {e}")
                    results.append({
                        'filename': filename,
                        'success': False,
                        'error': str(e)
                    })

        # サマリー
        success_count = sum(1 for r in results if r.get('success'))
        print()
        print("=" * 60)
        print(f"📊 処理完了: {success_count}/{len(filenames)}枚成功")

        return results

    def _upscale_single(self, filename: str, scale: int, method: str) -> Dict[str, Any]:
        """単一画像の超解像"""
        try:
            response = requests.post(
                f"{BASE_URL}/api/upscale",
                json={
                    "filename": filename,
                    "scale": scale,
                    "method": method
                },
                timeout=60
            )

            if response.status_code == 200:
                result = response.json()
                return {
                    'filename': filename,
                    'success': True,
                    **result
                }
            else:
                return {
                    'filename': filename,
                    'success': False,
                    'error': response.text
                }
        except Exception as e:
            return {
                'filename': filename,
                'success': False,
                'error': str(e)
            }

    def generate_gif_batch(
        self,
        image_groups: List[List[str]],
        duration: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        複数のGIFを一括生成

        Args:
            image_groups: 画像グループのリスト（各グループが1つのGIFになる）
            duration: 各フレームの表示時間

        Returns:
            処理結果のリスト
        """
        print(f"🎬 バッチGIF生成開始: {len(image_groups)}個")
        print("=" * 60)

        results = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_group = {
                executor.submit(self._generate_gif_single, group, duration): group
                for group in image_groups
            }

            for i, future in enumerate(as_completed(future_to_group), 1):
                group = future_to_group[future]
                try:
                    result = future.result()
                    results.append(result)

                    if result.get('success'):
                        print(f"[{i}/{len(image_groups)}] ✅ GIF生成完了 ({len(group)}枚)")
                    else:
                        print(f"[{i}/{len(image_groups)}] ❌ 失敗: {result.get('error')}")
                except Exception as e:
                    print(f"[{i}/{len(image_groups)}] ❌ エラー: {e}")
                    results.append({
                        'success': False,
                        'error': str(e),
                        'group': group
                    })

        # サマリー
        success_count = sum(1 for r in results if r.get('success'))
        print()
        print("=" * 60)
        print(f"📊 処理完了: {success_count}/{len(image_groups)}個成功")

        return results

    def _generate_gif_single(self, filenames: List[str], duration: float) -> Dict[str, Any]:
        """単一GIFの生成"""
        try:
            response = requests.post(
                f"{BASE_URL}/api/generate_gif",
                json={
                    "filenames": filenames,
                    "duration": duration,
                    "loop": 0
                },
                timeout=300
            )

            if response.status_code == 200:
                result = response.json()
                return {
                    'success': True,
                    'filenames': filenames,
                    **result
                }
            else:
                return {
                    'success': False,
                    'error': response.text
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def process_gallery_images(
        self,
        filter_pattern: str = "mufufu",
        max_images: int = 10
    ) -> List[str]:
        """
        ギャラリーから画像を取得

        Args:
            filter_pattern: フィルターパターン
            max_images: 最大取得数

        Returns:
            画像ファイル名のリスト
        """
        try:
            response = requests.get(f"{BASE_URL}/api/sd_images", timeout=10)
            if response.status_code == 200:
                images = response.json()
                filtered = [
                    img['filename'] for img in images
                    if filter_pattern.lower() in img.get('filename', '').lower()
                ][:max_images]

                print(f"📁 ギャラリーから {len(filtered)}枚の画像を取得")
                return filtered
            else:
                print(f"❌ ギャラリー取得失敗: {response.status_code}")
                return []
        except Exception as e:
            print(f"❌ エラー: {e}")
            return []


def main():
    """メイン処理"""
    processor = BatchProcessor(max_workers=3)

    print("🚀 バッチ処理システム")
    print("=" * 60)
    print()

    # 1. ギャラリーから画像を取得
    print("1️⃣ ギャラリーから画像を取得")
    print("-" * 60)
    images = processor.process_gallery_images(filter_pattern="mufufu", max_images=10)

    if not images:
        print("⚠️  画像が見つかりません")
        return

    print(f"   取得画像: {len(images)}枚")
    print()

    # 2. バッチ超解像
    print("2️⃣ バッチ超解像実行")
    print("-" * 60)
    upscale_results = processor.upscale_batch(
        filenames=images[:5],  # 最初の5枚だけテスト
        scale=2,
        method="simple"
    )

    print()

    # 3. バッチGIF生成
    print("3️⃣ バッチGIF生成実行")
    print("-" * 60)

    # 画像を3枚ずつのグループに分ける
    image_groups = [images[i:i+3] for i in range(0, min(9, len(images)), 3)]

    gif_results = processor.generate_gif_batch(
        image_groups=image_groups[:3],  # 最初の3グループだけテスト
        duration=0.5
    )

    print()
    print("=" * 60)
    print("🎉 バッチ処理完了！")
    print()
    print("📊 結果サマリー:")
    print(f"   超解像: {sum(1 for r in upscale_results if r.get('success'))}/{len(upscale_results)}枚成功")
    print(f"   GIF生成: {sum(1 for r in gif_results if r.get('success'))}/{len(gif_results)}個成功")

    # 結果をJSONで保存
    result_file = Path("/root/runpod_integration/batch_results.json")
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'upscale_results': upscale_results,
            'gif_results': gif_results
        }, f, indent=2, ensure_ascii=False)

    print(f"💾 結果を保存: {result_file}")


if __name__ == "__main__":
    main()








