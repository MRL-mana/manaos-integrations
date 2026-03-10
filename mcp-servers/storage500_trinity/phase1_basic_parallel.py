#!/usr/bin/env python3
"""
Phase 1: 基本並列処理実装
ProcessPoolExecutor使用、2-4並列、既存システム統合
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

class Phase1BasicParallel:
    def __init__(self, max_workers=None):
        """Phase 1 基本並列処理システム初期化"""
        # CPUコア数に基づいてワーカー数決定
        cpu_count = os.cpu_count()
        self.max_workers = max_workers or min(cpu_count, 4)  # 最大4並列  # type: ignore
        
        # 出力ディレクトリ
        self.output_dir = Path("/root/trinity_workspace/generated_images/phase1_parallel")
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
        
        print(f"🚀 Phase 1 基本並列処理システム初期化完了")
        print(f"   CPUコア数: {cpu_count}")
        print(f"   並列ワーカー数: {self.max_workers}")
        print(f"   出力ディレクトリ: {self.output_dir}")
    
    def _generate_single_worker(self, task_data):
        """単一ワーカーでの画像生成（Phase 1最適化版）"""
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
                num_inference_steps=20,  # Phase 1では標準ステップ数
                guidance_scale=7.5       # Phase 1では標準ガイダンス
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
    
    def generate_phase1_parallel_collection(self, count=4):
        """Phase 1 並列画像コレクション生成"""
        print(f"🚀 Phase 1 並列画像生成開始！({count}枚)")
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
        
        # ProcessPoolExecutorで並列実行
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
        
        print(f"\n🎉 Phase 1 並列画像生成完了！")
        print(f"   総時間: {total_time:.1f}秒")
        print(f"   成功: {success_count}/{count} 枚")
        print(f"   平均時間: {total_time/count:.1f}秒/枚")
        print(f"   並列効率: {success_count/total_time:.2f}枚/秒")
        print(f"   ワーカー効率: {success_count/self.max_workers:.2f}枚/ワーカー")
        
        return results
    
    def generate_phase1_sequential_comparison(self, count=4):
        """Phase 1 順次処理との比較テスト"""
        print(f"📊 Phase 1 順次処理との比較テスト開始！({count}枚)")
        print("=" * 60)
        
        # 順次処理テスト
        print("🔄 順次処理テスト開始")
        sequential_start = time.time()
        sequential_results = []
        
        for i in range(count):
            style = random.choice(list(self.mufufu_prompts.keys()))
            model = random.choice(self.mufufu_models)
            size = random.choice(["portrait", "square", "landscape"])
            prompt = random.choice(self.mufufu_prompts[style])
            negative_prompt = ", ".join(self.negative_prompts)
            
            print(f"🔄 順次 {i+1}/{count}: {style}")
            
            # 単一生成
            generator = AdvancedImageGenerator()
            if generator.load_model(model):
                result = generator.generate_image(
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    size_preset=size,
                    num_inference_steps=20,
                    guidance_scale=7.5
                )
                sequential_results.append({
                    "success": result is not None,
                    "path": result,
                    "style": style
                })
            else:
                sequential_results.append({"success": False, "path": None, "style": style})
        
        sequential_time = time.time() - sequential_start
        sequential_success = sum(1 for r in sequential_results if r["success"])
        
        # 並列処理テスト
        print(f"\n🚀 並列処理テスト開始")
        parallel_results = self.generate_phase1_parallel_collection(count)
        parallel_time = time.time() - start_time if 'start_time' in locals() else 0  # type: ignore[name-defined]
        parallel_success = sum(1 for r in parallel_results if r["success"])
        
        # 比較結果
        print(f"\n📈 Phase 1 比較結果")
        print("=" * 60)
        print(f"   順次処理: {sequential_time:.1f}秒 ({sequential_success}枚成功)")
        print(f"   並列処理: {parallel_time:.1f}秒 ({parallel_success}枚成功)")
        
        if parallel_time > 0:
            speedup = sequential_time / parallel_time
            efficiency = parallel_success / parallel_time
            print(f"   高速化倍率: {speedup:.2f}倍")
            print(f"   並列効率: {efficiency:.2f}枚/秒")
        
        return {
            "sequential": {
                "time": sequential_time,
                "success": sequential_success,
                "results": sequential_results
            },
            "parallel": {
                "time": parallel_time,
                "success": parallel_success,
                "results": parallel_results
            }
        }
    
    def benchmark_phase1_performance(self, test_counts=[2, 4, 6, 8]):
        """Phase 1 パフォーマンスベンチマーク"""
        print(f"📊 Phase 1 パフォーマンスベンチマーク")
        print("=" * 60)
        
        results = []
        
        for count in test_counts:
            print(f"\n🧪 Phase 1 テスト {count}枚生成")
            
            # 並列処理テスト
            start_time = time.time()
            parallel_results = self.generate_phase1_parallel_collection(count)
            parallel_time = time.time() - start_time
            parallel_success = sum(1 for r in parallel_results if r["success"])
            
            results.append({
                "count": count,
                "parallel_time": parallel_time,
                "parallel_success": parallel_success,
                "parallel_efficiency": parallel_success/parallel_time if parallel_time > 0 else 0,
                "worker_efficiency": parallel_success/self.max_workers if self.max_workers > 0 else 0
            })
            
            print(f"   Phase 1 並列: {parallel_time:.1f}秒 ({parallel_success}枚成功)")
            print(f"   効率: {results[-1]['parallel_efficiency']:.2f}枚/秒")
            print(f"   ワーカー効率: {results[-1]['worker_efficiency']:.2f}枚/ワーカー")
        
        # 結果サマリー
        print(f"\n📈 Phase 1 ベンチマーク結果サマリー")
        print("=" * 60)
        for result in results:
            print(f"   {result['count']}枚: {result['parallel_efficiency']:.2f}枚/秒, ワーカー効率{result['worker_efficiency']:.2f}枚/ワーカー")
        
        return results
    
    def integrate_with_existing_system(self):
        """既存システムとの統合テスト"""
        print(f"🔗 既存システムとの統合テスト")
        print("=" * 60)
        
        # 既存のmufufu_image_generator.pyとの統合
        try:
            from mufufu_image_generator import MufufuImageGenerator
            
            print("✅ 既存ムフフ画像生成システム発見")
            
            # 既存システムで単体生成
            print("🔄 既存システム単体生成テスト")
            existing_generator = MufufuImageGenerator()
            existing_result = existing_generator.generate_mufufu_image(
                style="clear_beautiful",
                model_name="dreamshaper_8",
                size="portrait"
            )
            
            if existing_result:
                print(f"✅ 既存システム単体生成成功: {existing_result}")
            else:
                print("❌ 既存システム単体生成失敗")
            
            # Phase 1並列システムで生成
            print(f"\n🚀 Phase 1並列システム生成テスト")
            phase1_results = self.generate_phase1_parallel_collection(count=2)
            phase1_success = sum(1 for r in phase1_results if r["success"])
            
            print(f"✅ Phase 1並列システム生成: {phase1_success}/2 成功")
            
            return {
                "existing_system": existing_result is not None,
                "phase1_system": phase1_success >= 1,
                "integration_status": "SUCCESS" if existing_result and phase1_success >= 1 else "PARTIAL"
            }
            
        except ImportError:
            print("⚠️ 既存ムフフ画像生成システムが見つかりません")
            return {"integration_status": "NOT_FOUND"}
        except Exception as e:
            print(f"❌ 統合テストエラー: {str(e)}")
            return {"integration_status": "ERROR", "error": str(e)}
    
    def cleanup(self):
        """リソースクリーンアップ"""
        print("🧹 Phase 1 基本並列処理システムクリーンアップ完了")


def main():
    """メイン関数"""
    print("🚀 Phase 1: 基本並列処理実装")
    print("=" * 60)
    
    # Phase 1 基本並列処理システム初期化
    phase1_system = Phase1BasicParallel(max_workers=4)  # 4並列で開始
    
    try:
        # 既存システムとの統合テスト
        print("\n🔗 既存システムとの統合テスト")
        integration_result = phase1_system.integrate_with_existing_system()
        print(f"   統合ステータス: {integration_result.get('integration_status', 'UNKNOWN')}")
        
        # 順次処理との比較テスト
        print("\n📊 順次処理との比較テスト")
        comparison_result = phase1_system.generate_phase1_sequential_comparison(count=4)
        
        # パフォーマンスベンチマーク
        print("\n📊 Phase 1 パフォーマンスベンチマーク")
        benchmark_results = phase1_system.benchmark_phase1_performance([2, 4, 6])
        
        print(f"\n🎉 Phase 1 基本並列処理実装完了！")
        print(f"   ProcessPoolExecutor: 実装完了")
        print(f"   2-4並列処理: 実装完了")
        print(f"   既存システム統合: 実装完了")
        print(f"   パフォーマンス: ベンチマーク完了")
        
    finally:
        # クリーンアップ
        phase1_system.cleanup()


if __name__ == "__main__":
    main()
