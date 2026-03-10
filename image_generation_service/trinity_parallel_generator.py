#!/usr/bin/env python3
"""
Parallel Image Generator
並列処理による高速画像生成システム
"""

import os
import sys
import time
import json
import random
from pathlib import Path
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing as mp

# パスを追加
sys.path.append('/root/trinity_workspace/tools')

from advanced_image_generator import AdvancedImageGenerator

class ParallelImageGenerator:
    def __init__(self, max_workers=None):
        """並列画像生成システム初期化"""
        self.max_workers = max_workers or min(os.cpu_count(), 8)  # type: ignore
        self.executor = ProcessPoolExecutor(max_workers=self.max_workers)
        
        # 出力ディレクトリ
        self.output_dir = Path("/root/trinity_workspace/generated_images/parallel")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # ムフフ画像用のプロンプトテンプレート
        self.mufufu_prompts = {
            "clear_beautiful": [
                "a beautiful clear girl, innocent expression, soft smile, high quality, detailed, anime style",
                "cute girl with pure eyes, gentle smile, clear skin, beautiful hair, high quality, anime art",
                "innocent beautiful girl, shy expression, soft lighting, high quality, detailed illustration"
            ],
            "elegant_style": [
                "elegant beautiful woman, sophisticated style, graceful pose, high quality, detailed",
                "refined beautiful girl, classy outfit, gentle expression, high quality, anime style",
                "stylish beautiful woman, fashionable clothes, confident smile, high quality, detailed art"
            ],
            "cute_kawaii": [
                "super cute kawaii girl, big eyes, adorable expression, soft colors, high quality",
                "lovely cute girl, sweet smile, fluffy hair, pastel colors, high quality, anime style",
                "adorable kawaii character, innocent face, cute outfit, high quality, detailed illustration"
            ]
        }
        
        # ネガティブプロンプト
        self.negative_prompts = [
            "nsfw, nude, explicit, sexual, inappropriate, violence, blood, gore, scary, horror",
            "bad quality, low resolution, blurry, distorted, ugly, deformed, bad anatomy"
        ]
        
        # ムフフ画像に適したモデル
        self.mufufu_models = [
            "dreamshaper_8",
            "majicmixLux_v3", 
            "majicmixRealistic_v7"
        ]
        
        print(f"🚀 並列画像生成システム初期化完了")
        print(f"   CPUコア数: {os.cpu_count()}")
        print(f"   並列ワーカー数: {self.max_workers}")
        print(f"   出力ディレクトリ: {self.output_dir}")
    
    def _prepare_parallel_prompts(self, count):
        """並列処理用プロンプト準備"""
        prompts = []
        styles = list(self.mufufu_prompts.keys())
        
        for i in range(count):
            # ランダムなスタイルとモデル選択
            style = random.choice(styles)
            model = random.choice(self.mufufu_models)
            size = random.choice(["portrait", "square", "landscape"])
            
            # プロンプト選択
            prompt_text = random.choice(self.mufufu_prompts[style])
            negative_prompt = ", ".join(self.negative_prompts)
            
            prompts.append({
                "id": i,
                "prompt": prompt_text,
                "negative_prompt": negative_prompt,
                "model": model,
                "style": style,
                "size": size,
                "num_inference_steps": 25,
                "guidance_scale": 8.0
            })
        
        return prompts
    
    def _generate_single_worker(self, prompt_data):
        """単一ワーカーでの画像生成"""
        try:
            # 各ワーカーで独立したジェネレーターを作成
            generator = AdvancedImageGenerator()
            
            # モデル読み込み
            if not generator.load_model(prompt_data["model"]):
                return {
                    "id": prompt_data["id"],
                    "success": False,
                    "error": "モデル読み込み失敗",
                    "path": None
                }
            
            # 画像生成
            result = generator.generate_image(
                prompt=prompt_data["prompt"],
                negative_prompt=prompt_data["negative_prompt"],
                size_preset=prompt_data["size"],
                num_inference_steps=prompt_data["num_inference_steps"],
                guidance_scale=prompt_data["guidance_scale"]
            )
            
            if result:
                return {
                    "id": prompt_data["id"],
                    "success": True,
                    "error": None,
                    "path": result,
                    "style": prompt_data["style"],
                    "model": prompt_data["model"],
                    "size": prompt_data["size"]
                }
            else:
                return {
                    "id": prompt_data["id"],
                    "success": False,
                    "error": "画像生成失敗",
                    "path": None
                }
                
        except Exception as e:
            return {
                "id": prompt_data["id"],
                "success": False,
                "error": str(e),
                "path": None
            }
    
    def generate_parallel_collection(self, count=3):
        """並列画像コレクション生成"""
        print(f"🚀 並列画像生成開始！({count}枚)")
        print(f"   並列ワーカー数: {self.max_workers}")
        print("=" * 60)
        
        start_time = time.time()
        
        # 並列処理用プロンプト準備
        prompts = self._prepare_parallel_prompts(count)
        
        # 並列実行
        futures = []
        for prompt_data in prompts:
            future = self.executor.submit(self._generate_single_worker, prompt_data)
            futures.append(future)
        
        # 結果収集
        results = []
        completed_count = 0
        
        print(f"⏳ 並列処理実行中...")
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            completed_count += 1
            
            if result["success"]:
                print(f"✅ {completed_count}/{count} 完了: {result['style']} ({result['model']})")
            else:
                print(f"❌ {completed_count}/{count} 失敗: {result['error']}")
        
        total_time = time.time() - start_time
        success_count = sum(1 for r in results if r["success"])
        
        print(f"\n🎉 並列画像生成完了！")
        print(f"   総時間: {total_time:.1f}秒")
        print(f"   成功: {success_count}/{count} 枚")
        print(f"   平均時間: {total_time/count:.1f}秒/枚")
        print(f"   並列効率: {success_count/total_time:.2f}枚/秒")
        
        return results
    
    def generate_batch_collection(self, prompt, batch_size=4):
        """バッチ処理による画像生成"""
        print(f"📦 バッチ画像生成開始！({batch_size}枚)")
        print(f"   プロンプト: {prompt}")
        print("=" * 60)
        
        start_time = time.time()
        
        try:
            # ジェネレーター作成
            generator = AdvancedImageGenerator()
            
            # デフォルトモデル読み込み
            model_name = self.mufufu_models[0]
            if not generator.load_model(model_name):
                print("❌ モデル読み込み失敗")
                return []
            
            # バッチ生成
            negative_prompt = ", ".join(self.negative_prompts)
            
            # 複数画像を一度に生成
            images = generator.current_pipeline(
                prompt=prompt,
                negative_prompt=negative_prompt,
                num_images_per_prompt=batch_size,
                num_inference_steps=25,
                guidance_scale=8.0
            ).images
            
            # ファイル保存
            results = []
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            for i, image in enumerate(images):
                filename = f"batch_{model_name}_{timestamp}_{i+1}.png"
                output_path = self.output_dir / filename
                image.save(output_path)
                results.append(str(output_path))
                print(f"✅ バッチ {i+1}/{batch_size} 保存: {output_path}")
            
            total_time = time.time() - start_time
            print(f"\n🎉 バッチ画像生成完了！")
            print(f"   総時間: {total_time:.1f}秒")
            print(f"   平均時間: {total_time/batch_size:.1f}秒/枚")
            print(f"   バッチ効率: {batch_size/total_time:.2f}枚/秒")
            
            return results
            
        except Exception as e:
            print(f"❌ バッチ生成エラー: {str(e)}")
            return []
    
    def generate_hybrid_collection(self, count=6):
        """ハイブリッド並列+バッチ処理"""
        print(f"🔥 ハイブリッド画像生成開始！({count}枚)")
        print("   並列処理 + バッチ処理の組み合わせ")
        print("=" * 60)
        
        start_time = time.time()
        
        # 並列処理で異なるプロンプトを生成
        parallel_count = min(count // 2, self.max_workers)
        batch_count = count - parallel_count
        
        results = []
        
        # 並列処理部分
        if parallel_count > 0:
            print(f"🚀 並列処理: {parallel_count}枚")
            parallel_results = self.generate_parallel_collection(parallel_count)
            results.extend(parallel_results)
        
        # バッチ処理部分
        if batch_count > 0:
            print(f"📦 バッチ処理: {batch_count}枚")
            # ランダムなプロンプト選択
            style = random.choice(list(self.mufufu_prompts.keys()))
            prompt = random.choice(self.mufufu_prompts[style])
            batch_results = self.generate_batch_collection(prompt, batch_count)
            results.extend([{"success": True, "path": path} for path in batch_results])
        
        total_time = time.time() - start_time
        success_count = sum(1 for r in results if r.get("success", False))
        
        print(f"\n🎉 ハイブリッド画像生成完了！")
        print(f"   総時間: {total_time:.1f}秒")
        print(f"   成功: {success_count}/{count} 枚")
        print(f"   平均時間: {total_time/count:.1f}秒/枚")
        print(f"   総合効率: {success_count/total_time:.2f}枚/秒")
        
        return results
    
    def benchmark_performance(self, test_counts=[1, 3, 6, 9]):
        """パフォーマンスベンチマーク"""
        print(f"📊 並列画像生成パフォーマンスベンチマーク")
        print("=" * 60)
        
        results = []
        
        for count in test_counts:
            print(f"\n🧪 テスト {count}枚生成")
            
            # 並列処理テスト
            start_time = time.time()
            parallel_results = self.generate_parallel_collection(count)
            parallel_time = time.time() - start_time
            parallel_success = sum(1 for r in parallel_results if r["success"])
            
            # バッチ処理テスト（同じプロンプトで）
            if count <= 4:  # バッチ処理は4枚まで
                start_time = time.time()
                prompt = random.choice(self.mufufu_prompts["clear_beautiful"])
                batch_results = self.generate_batch_collection(prompt, count)
                batch_time = time.time() - start_time
                batch_success = len(batch_results)
            else:
                batch_time = 0
                batch_success = 0
            
            results.append({
                "count": count,
                "parallel_time": parallel_time,
                "parallel_success": parallel_success,
                "batch_time": batch_time,
                "batch_success": batch_success,
                "parallel_efficiency": parallel_success/parallel_time if parallel_time > 0 else 0,
                "batch_efficiency": batch_success/batch_time if batch_time > 0 else 0
            })
            
            print(f"   並列処理: {parallel_time:.1f}秒 ({parallel_success}枚成功)")
            print(f"   バッチ処理: {batch_time:.1f}秒 ({batch_success}枚成功)")
        
        # 結果サマリー
        print(f"\n📈 ベンチマーク結果サマリー")
        print("=" * 60)
        for result in results:
            print(f"   {result['count']}枚: 並列{result['parallel_efficiency']:.2f}枚/秒, バッチ{result['batch_efficiency']:.2f}枚/秒")
        
        return results
    
    def cleanup(self):
        """リソースクリーンアップ"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=True)
        print("🧹 並列画像生成システムクリーンアップ完了")


def main():
    """メイン関数"""
    print("🚀 Parallel Image Generator")
    print("=" * 60)
    
    # 並列画像生成システム初期化
    generator = ParallelImageGenerator(max_workers=4)  # 4並列で開始
    
    try:
        # パフォーマンスベンチマーク
        print("\n📊 パフォーマンスベンチマーク開始")
        benchmark_results = generator.benchmark_performance([1, 3, 6])
        
        # ハイブリッド生成テスト
        print("\n🔥 ハイブリッド生成テスト")
        hybrid_results = generator.generate_hybrid_collection(count=6)
        
        print(f"\n🎉 全テスト完了！")
        print(f"   並列処理システム: 準備完了")
        print(f"   バッチ処理システム: 準備完了")
        print(f"   ハイブリッドシステム: 準備完了")
        
    finally:
        # クリーンアップ
        generator.cleanup()


if __name__ == "__main__":
    main()
