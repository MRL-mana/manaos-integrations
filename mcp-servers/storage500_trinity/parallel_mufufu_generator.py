#!/usr/bin/env python3
"""
Parallel Mufufu Image Generator
並列処理による高速ムフフ画像生成システム
"""

import os
import sys
import time
import json
import random
from pathlib import Path
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed

# パスを追加
sys.path.append('/root/trinity_workspace/tools')

from parallel_image_generator import ParallelImageGenerator

class ParallelMufufuGenerator:
    def __init__(self, max_workers=None):
        """並列ムフフ画像生成システム初期化"""
        self.parallel_generator = ParallelImageGenerator(max_workers)
        
        # ムフフ専用プロンプトテンプレート
        self.mufufu_prompts = {
            "clear_beautiful": [
                "a beautiful clear girl, innocent expression, soft smile, high quality, detailed, anime style",
                "cute girl with pure eyes, gentle smile, clear skin, beautiful hair, high quality, anime art",
                "innocent beautiful girl, shy expression, soft lighting, high quality, detailed illustration",
                "pure beautiful girl, gentle expression, soft features, high quality, anime style",
                "lovely clear girl, sweet smile, innocent eyes, high quality, detailed art"
            ],
            "elegant_style": [
                "elegant beautiful woman, sophisticated style, graceful pose, high quality, detailed",
                "refined beautiful girl, classy outfit, gentle expression, high quality, anime style",
                "stylish beautiful woman, fashionable clothes, confident smile, high quality, detailed art",
                "graceful beautiful girl, elegant dress, gentle pose, high quality, anime illustration",
                "sophisticated beautiful woman, refined features, elegant style, high quality, detailed"
            ],
            "cute_kawaii": [
                "super cute kawaii girl, big eyes, adorable expression, soft colors, high quality",
                "lovely cute girl, sweet smile, fluffy hair, pastel colors, high quality, anime style",
                "adorable kawaii character, innocent face, cute outfit, high quality, detailed illustration",
                "charming cute girl, big sparkling eyes, sweet expression, high quality, anime art",
                "precious kawaii girl, innocent smile, cute features, high quality, detailed illustration"
            ],
            "innocent_pure": [
                "innocent pure girl, gentle expression, soft features, high quality, anime style",
                "pure beautiful girl, innocent eyes, gentle smile, high quality, detailed art",
                "angelic pure girl, innocent expression, soft lighting, high quality, anime illustration",
                "virgin pure girl, innocent face, gentle features, high quality, detailed art",
                "chaste pure girl, innocent smile, gentle expression, high quality, anime style"
            ]
        }
        
        print(f"🎨 並列ムフフ画像生成システム初期化完了")
        print(f"   並列ワーカー数: {self.parallel_generator.max_workers}")
        print(f"   ムフフスタイル数: {len(self.mufufu_prompts)}")
    
    def generate_mufufu_parallel_collection(self, count=6, styles=None):
        """並列ムフフ画像コレクション生成"""
        print(f"🎨 並列ムフフ画像生成開始！({count}枚)")
        print("=" * 60)
        
        if styles is None:
            styles = list(self.mufufu_prompts.keys())
        
        # ムフフ専用プロンプト準備
        prompts = []
        for i in range(count):
            style = random.choice(styles)
            model = random.choice(self.parallel_generator.mufufu_models)
            size = random.choice(["portrait", "square", "landscape"])
            
            # ムフフプロンプト選択
            prompt_text = random.choice(self.mufufu_prompts[style])
            negative_prompt = ", ".join(self.parallel_generator.negative_prompts)
            
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
        
        # 並列実行
        start_time = time.time()
        futures = []
        
        for prompt_data in prompts:
            future = self.parallel_generator.executor.submit(
                self.parallel_generator._generate_single_worker, prompt_data
            )
            futures.append(future)
        
        # 結果収集
        results = []
        completed_count = 0
        
        print(f"⏳ 並列ムフフ画像生成中...")
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            completed_count += 1
            
            if result["success"]:
                print(f"✅ {completed_count}/{count} ムフフ完了: {result['style']} ({result['model']})")
            else:
                print(f"❌ {completed_count}/{count} ムフフ失敗: {result['error']}")
        
        total_time = time.time() - start_time
        success_count = sum(1 for r in results if r["success"])
        
        print(f"\n🎉 並列ムフフ画像生成完了！")
        print(f"   総時間: {total_time:.1f}秒")
        print(f"   成功: {success_count}/{count} 枚")
        print(f"   平均時間: {total_time/count:.1f}秒/枚")
        print(f"   ムフフ効率: {success_count/total_time:.2f}枚/秒")
        
        return results
    
    def generate_mufufu_batch_collection(self, style="clear_beautiful", batch_size=4):
        """バッチムフフ画像生成"""
        print(f"📦 バッチムフフ画像生成開始！({batch_size}枚)")
        print(f"   スタイル: {style}")
        print("=" * 60)
        
        if style not in self.mufufu_prompts:
            style = "clear_beautiful"
        
        # ムフフプロンプト選択
        prompt = random.choice(self.mufufu_prompts[style])
        negative_prompt = ", ".join(self.parallel_generator.negative_prompts)
        
        start_time = time.time()
        
        try:
            # ジェネレーター作成
            from advanced_image_generator import AdvancedImageGenerator
            generator = AdvancedImageGenerator()
            
            # デフォルトモデル読み込み
            model_name = self.parallel_generator.mufufu_models[0]
            if not generator.load_model(model_name):
                print("❌ モデル読み込み失敗")
                return []
            
            # バッチ生成
            images = generator.current_pipeline(  # type: ignore[operator]
                prompt=prompt,
                negative_prompt=negative_prompt,
                num_images_per_prompt=batch_size,
                num_inference_steps=25,
                guidance_scale=8.0
            ).images
            
            # ファイル保存
            results = []
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = Path("/root/trinity_workspace/generated_images/parallel/mufufu")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            for i, image in enumerate(images):
                filename = f"mufufu_batch_{style}_{timestamp}_{i+1}.png"
                output_path = output_dir / filename
                image.save(output_path)
                results.append(str(output_path))
                print(f"✅ ムフフバッチ {i+1}/{batch_size} 保存: {output_path}")
            
            total_time = time.time() - start_time
            print(f"\n🎉 バッチムフフ画像生成完了！")
            print(f"   総時間: {total_time:.1f}秒")
            print(f"   平均時間: {total_time/batch_size:.1f}秒/枚")
            print(f"   ムフフバッチ効率: {batch_size/total_time:.2f}枚/秒")
            
            return results
            
        except Exception as e:
            print(f"❌ バッチムフフ生成エラー: {str(e)}")
            return []
    
    def generate_mufufu_hybrid_collection(self, count=8):
        """ハイブリッドムフフ画像生成"""
        print(f"🔥 ハイブリッドムフフ画像生成開始！({count}枚)")
        print("   並列処理 + バッチ処理のムフフ組み合わせ")
        print("=" * 60)
        
        start_time = time.time()
        
        # 並列処理で異なるスタイルを生成
        parallel_count = min(count // 2, self.parallel_generator.max_workers)
        batch_count = count - parallel_count
        
        results = []
        
        # 並列処理部分
        if parallel_count > 0:
            print(f"🚀 並列ムフフ処理: {parallel_count}枚")
            parallel_results = self.generate_mufufu_parallel_collection(parallel_count)
            results.extend(parallel_results)
        
        # バッチ処理部分
        if batch_count > 0:
            print(f"📦 バッチムフフ処理: {batch_count}枚")
            style = random.choice(list(self.mufufu_prompts.keys()))
            batch_results = self.generate_mufufu_batch_collection(style, batch_count)
            results.extend([{"success": True, "path": path, "style": style} for path in batch_results])
        
        total_time = time.time() - start_time
        success_count = sum(1 for r in results if r.get("success", False))
        
        print(f"\n🎉 ハイブリッドムフフ画像生成完了！")
        print(f"   総時間: {total_time:.1f}秒")
        print(f"   成功: {success_count}/{count} 枚")
        print(f"   平均時間: {total_time/count:.1f}秒/枚")
        print(f"   ムフフ総合効率: {success_count/total_time:.2f}枚/秒")
        
        return results
    
    def generate_mufufu_style_collection(self, style="clear_beautiful", count=4):
        """特定スタイルのムフフ画像生成"""
        print(f"🎭 {style}スタイルムフフ画像生成開始！({count}枚)")
        print("=" * 60)
        
        if style not in self.mufufu_prompts:
            print(f"❌ 不明なスタイル: {style}")
            return []
        
        # 並列処理で同じスタイルを生成
        results = self.generate_mufufu_parallel_collection(count, [style])
        
        print(f"\n🎉 {style}スタイルムフフ画像生成完了！")
        return results
    
    def list_mufufu_styles(self):
        """ムフフスタイル一覧表示"""
        print("🎭 ムフフ画像スタイル一覧")
        print("=" * 60)
        
        for style, prompts in self.mufufu_prompts.items():
            print(f"\n📁 {style}:")
            for i, prompt in enumerate(prompts, 1):
                print(f"   {i}. {prompt}")
    
    def benchmark_mufufu_performance(self, test_counts=[2, 4, 6, 8]):
        """ムフフ画像生成パフォーマンスベンチマーク"""
        print(f"📊 ムフフ画像生成パフォーマンスベンチマーク")
        print("=" * 60)
        
        results = []
        
        for count in test_counts:
            print(f"\n🧪 ムフフテスト {count}枚生成")
            
            # 並列処理テスト
            start_time = time.time()
            parallel_results = self.generate_mufufu_parallel_collection(count)
            parallel_time = time.time() - start_time
            parallel_success = sum(1 for r in parallel_results if r["success"])
            
            # バッチ処理テスト
            if count <= 4:
                start_time = time.time()
                style = random.choice(list(self.mufufu_prompts.keys()))
                batch_results = self.generate_mufufu_batch_collection(style, count)
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
            
            print(f"   並列ムフフ: {parallel_time:.1f}秒 ({parallel_success}枚成功)")
            print(f"   バッチムフフ: {batch_time:.1f}秒 ({batch_success}枚成功)")
        
        # 結果サマリー
        print(f"\n📈 ムフフベンチマーク結果サマリー")
        print("=" * 60)
        for result in results:
            print(f"   {result['count']}枚: 並列{result['parallel_efficiency']:.2f}枚/秒, バッチ{result['batch_efficiency']:.2f}枚/秒")
        
        return results
    
    def cleanup(self):
        """リソースクリーンアップ"""
        if hasattr(self.parallel_generator, 'executor'):
            self.parallel_generator.executor.shutdown(wait=True)
        print("🧹 並列ムフフ画像生成システムクリーンアップ完了")


def main():
    """メイン関数"""
    print("🎨 Parallel Mufufu Image Generator")
    print("=" * 60)
    
    # 並列ムフフ画像生成システム初期化
    generator = ParallelMufufuGenerator(max_workers=4)  # 4並列で開始
    
    try:
        # ムフフスタイル一覧
        generator.list_mufufu_styles()
        
        # パフォーマンスベンチマーク
        print("\n📊 ムフフパフォーマンスベンチマーク開始")
        benchmark_results = generator.benchmark_mufufu_performance([2, 4, 6])
        
        # ハイブリッドムフフ生成テスト
        print("\n🔥 ハイブリッドムフフ生成テスト")
        hybrid_results = generator.generate_mufufu_hybrid_collection(count=8)
        
        # スタイル別生成テスト
        print("\n🎭 スタイル別ムフフ生成テスト")
        style_results = generator.generate_mufufu_style_collection("cute_kawaii", count=4)
        
        print(f"\n🎉 全ムフフテスト完了！")
        print(f"   並列ムフフシステム: 準備完了")
        print(f"   バッチムフフシステム: 準備完了")
        print(f"   ハイブリッドムフフシステム: 準備完了")
        
    finally:
        # クリーンアップ
        generator.cleanup()


if __name__ == "__main__":
    main()
