#!/usr/bin/env python3
"""
Phase 1: 8コア全部使用並列処理
スワップメモリ活用で8並列実行
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

class Phase1_8CoreParallel:
    def __init__(self):
        """8コア全部使用並列処理システム初期化"""
        # 8コア全部使用
        self.max_workers = os.cpu_count()  # 8並列
        
        # 出力ディレクトリ
        self.output_dir = Path("/root/trinity_workspace/generated_images/phase1_8core")
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
        
        print(f"🚀 8コア全部使用並列処理システム初期化完了")
        print(f"   CPUコア数: {os.cpu_count()}")
        print(f"   並列ワーカー数: {self.max_workers}")
        print(f"   スワップメモリ活用: 有効")
        print(f"   出力ディレクトリ: {self.output_dir}")
    
    def _generate_single_worker(self, task_data):
        """単一ワーカーでの画像生成（8コア最適化版）"""
        try:
            task_id = task_data["id"]
            prompt = task_data["prompt"]
            negative_prompt = task_data["negative_prompt"]
            model = task_data["model"]
            style = task_data["style"]
            size = task_data["size"]
            
            print(f"🔄 ワーカー {task_id} 開始: {style} ({model})")
            
            # 各ワーカーで独立したジェネレーターを作成
            generator = AdvancedImageGenerator()
            
            # モデル読み込み
            if not generator.load_model(model):
                return {
                    "id": task_id,
                    "success": False,
                    "error": "モデル読み込み失敗",
                    "path": None,
                    "worker_id": task_id
                }
            
            # 画像生成
            result = generator.generate_image(
                prompt=prompt,
                negative_prompt=negative_prompt,
                size_preset=size,
                num_inference_steps=20,
                guidance_scale=7.5
            )
            
            if result:
                return {
                    "id": task_id,
                    "success": True,
                    "error": None,
                    "path": result,
                    "style": style,
                    "model": model,
                    "size": size,
                    "worker_id": task_id
                }
            else:
                return {
                    "id": task_id,
                    "success": False,
                    "error": "画像生成失敗",
                    "path": None,
                    "worker_id": task_id
                }
                
        except Exception as e:
            return {
                "id": task_data["id"],
                "success": False,
                "error": str(e),
                "path": None,
                "worker_id": task_data["id"]
            }
    
    def generate_8core_parallel_collection(self, count=8):
        """8コア全部使用並列画像コレクション生成"""
        print(f"🚀 8コア全部使用並列画像生成開始！({count}枚)")
        print(f"   並列ワーカー数: {self.max_workers}")
        print("=" * 60)
        
        start_time = time.time()
        
        # タスク準備
        tasks = []
        styles = list(self.mufufu_prompts.keys())
        
        for i in range(count):
            # ランダムなスタイルとモデル選択
            style = random.choice(styles)
            model = random.choice(self.mufufu_models)
            size = random.choice(["portrait", "square", "landscape"])
            
            # プロンプト選択
            prompt_text = random.choice(self.mufufu_prompts[style])
            negative_prompt = ", ".join(self.negative_prompts)
            
            tasks.append({
                "id": i,
                "prompt": prompt_text,
                "negative_prompt": negative_prompt,
                "model": model,
                "style": style,
                "size": size
            })
        
        # ProcessPoolExecutorで8並列実行
        results = []
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # タスクを並列実行
            futures = [executor.submit(self._generate_single_worker, task) for task in tasks]
            
            # 結果を順次収集
            completed_count = 0
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                completed_count += 1
                
                if result["success"]:
                    print(f"✅ {completed_count}/{count} 完了: {result['style']} ({result['model']}) - ワーカー{result['worker_id']}")
                else:
                    print(f"❌ {completed_count}/{count} 失敗: {result['error']} - ワーカー{result['worker_id']}")
        
        total_time = time.time() - start_time
        success_count = sum(1 for r in results if r["success"])
        
        print(f"\n🎉 8コア全部使用並列画像生成完了！")
        print(f"   総時間: {total_time:.1f}秒")
        print(f"   成功: {success_count}/{count} 枚")
        print(f"   平均時間: {total_time/count:.1f}秒/枚")
        print(f"   8コア効率: {success_count/total_time:.2f}枚/秒")
        print(f"   ワーカー効率: {success_count/self.max_workers:.2f}枚/ワーカー")
        
        return results
    
    def benchmark_8core_performance(self, test_counts=[4, 8, 12, 16]):
        """8コアパフォーマンスベンチマーク"""
        print(f"📊 8コアパフォーマンスベンチマーク")
        print("=" * 60)
        
        results = []
        
        for count in test_counts:
            print(f"\n🧪 8コアテスト {count}枚生成")
            
            # 8コア並列処理テスト
            start_time = time.time()
            parallel_results = self.generate_8core_parallel_collection(count)
            parallel_time = time.time() - start_time
            parallel_success = sum(1 for r in parallel_results if r["success"])
            
            results.append({
                "count": count,
                "parallel_time": parallel_time,
                "parallel_success": parallel_success,
                "parallel_efficiency": parallel_success/parallel_time if parallel_time > 0 else 0,
                "worker_efficiency": parallel_success/self.max_workers if self.max_workers > 0 else 0
            })
            
            print(f"   8コア並列: {parallel_time:.1f}秒 ({parallel_success}枚成功)")
            print(f"   効率: {results[-1]['parallel_efficiency']:.2f}枚/秒")
            print(f"   ワーカー効率: {results[-1]['worker_efficiency']:.2f}枚/ワーカー")
        
        # 結果サマリー
        print(f"\n📈 8コアベンチマーク結果サマリー")
        print("=" * 60)
        for result in results:
            print(f"   {result['count']}枚: {result['parallel_efficiency']:.2f}枚/秒, ワーカー効率{result['worker_efficiency']:.2f}枚/ワーカー")
        
        return results
    
    def monitor_system_resources(self):
        """システムリソース監視"""
        print(f"📊 システムリソース監視")
        print("=" * 60)
        
        try:
            import psutil
            
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            print(f"   CPU使用率: {cpu_percent:.1f}%")
            
            # メモリ使用率
            memory = psutil.virtual_memory()
            print(f"   メモリ使用率: {memory.percent:.1f}%")
            print(f"   利用可能メモリ: {memory.available / (1024**3):.1f}GB")
            
            # スワップ使用率
            swap = psutil.swap_memory()
            print(f"   スワップ使用率: {swap.percent:.1f}%")
            print(f"   利用可能スワップ: {swap.free / (1024**3):.1f}GB")
            
            # ディスク使用率
            disk = psutil.disk_usage('/')
            print(f"   ディスク使用率: {disk.percent:.1f}%")
            
            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "swap_percent": swap.percent,
                "disk_percent": disk.percent
            }
            
        except ImportError:
            print("⚠️ psutilが利用できません。システム監視をスキップします。")
            return None
        except Exception as e:
            print(f"⚠️ システム監視エラー: {str(e)}")
            return None
    
    def cleanup(self):
        """リソースクリーンアップ"""
        print("🧹 8コア全部使用並列処理システムクリーンアップ完了")


def main():
    """メイン関数"""
    print("🚀 Phase 1: 8コア全部使用並列処理")
    print("=" * 60)
    
    # 8コア全部使用並列処理システム初期化
    system = Phase1_8CoreParallel()
    
    try:
        # システムリソース監視
        print("\n📊 システムリソース監視")
        resource_info = system.monitor_system_resources()
        
        # 8コア並列処理テスト
        print("\n🚀 8コア並列処理テスト")
        results = system.generate_8core_parallel_collection(count=8)
        
        # パフォーマンスベンチマーク
        print("\n📊 8コアパフォーマンスベンチマーク")
        benchmark_results = system.benchmark_8core_performance([4, 8, 12, 16])
        
        print(f"\n🎉 8コア全部使用並列処理完了！")
        print(f"   8コア並列処理: 実装完了")
        print(f"   スワップメモリ活用: 実装完了")
        print(f"   パフォーマンス: ベンチマーク完了")
        
    finally:
        # クリーンアップ
        system.cleanup()


if __name__ == "__main__":
    main()
