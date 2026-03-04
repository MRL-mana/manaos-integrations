#!/usr/bin/env python3
"""
Phase 2: バッチ処理統合
Stable Diffusionバッチ機能活用、メモリ効率向上
"""

import os
import sys
import time
import json
import random
from pathlib import Path
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
import torch

# パスを追加
sys.path.append('/root/trinity_workspace/tools')

from advanced_image_generator import AdvancedImageGenerator
from phase1_basic_parallel import Phase1BasicParallel

class Phase2BatchProcessing:
    def __init__(self, max_workers=None):
        """Phase 2 バッチ処理システム初期化"""
        # Phase 1システムを継承
        self.phase1_system = Phase1BasicParallel(max_workers)
        self.max_workers = max_workers or min(os.cpu_count(), 4)
        
        # バッチ処理用設定
        self.batch_sizes = [2, 4, 6, 8]  # テスト用バッチサイズ
        self.max_batch_size = 8  # 最大バッチサイズ
        
        # 出力ディレクトリ
        self.output_dir = Path("/root/trinity_workspace/generated_images/phase2_batch")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # メモリ監視設定
        self.memory_threshold = 0.8  # メモリ使用率80%で警告
        self.memory_optimization = True
        
        print(f"🚀 Phase 2 バッチ処理システム初期化完了")
        print(f"   最大バッチサイズ: {self.max_batch_size}")
        print(f"   メモリ最適化: {'有効' if self.memory_optimization else '無効'}")
        print(f"   出力ディレクトリ: {self.output_dir}")
    
    def _check_memory_usage(self):
        """メモリ使用率チェック"""
        try:
            import psutil
            memory = psutil.virtual_memory()
            usage_percent = memory.percent / 100
            
            if usage_percent > self.memory_threshold:
                print(f"⚠️ メモリ使用率警告: {memory.percent:.1f}%")
                return False
            else:
                print(f"✅ メモリ使用率正常: {memory.percent:.1f}%")
                return True
        except ImportError:
            print("⚠️ psutilが利用できません。メモリ監視をスキップします。")
            return True
        except Exception as e:
            print(f"⚠️ メモリ監視エラー: {str(e)}")
            return True
    
    def _optimize_memory(self):
        """メモリ最適化"""
        if not self.memory_optimization:
            return
        
        try:
            # PyTorchキャッシュクリア
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                print("🧹 CUDAキャッシュクリア完了")
            
            # ガベージコレクション
            import gc
            gc.collect()
            print("🧹 ガベージコレクション完了")
            
        except Exception as e:
            print(f"⚠️ メモリ最適化エラー: {str(e)}")
    
    def generate_batch_images(self, prompt, negative_prompt="", batch_size=4, model_name=None):
        """バッチ画像生成（Stable Diffusionバッチ機能活用）"""
        print(f"📦 バッチ画像生成開始！({batch_size}枚)")
        print(f"   プロンプト: {prompt}")
        print(f"   バッチサイズ: {batch_size}")
        print("=" * 60)
        
        # メモリチェック
        if not self._check_memory_usage():
            print("⚠️ メモリ使用率が高いため、バッチサイズを調整します")
            batch_size = min(batch_size, 2)
        
        start_time = time.time()
        
        try:
            # ジェネレーター作成
            generator = AdvancedImageGenerator()
            
            # モデル読み込み
            if not model_name:
                model_name = self.phase1_system.mufufu_models[0]
            
            if not generator.load_model(model_name):
                print("❌ モデル読み込み失敗")
                return []
            
            # バッチ生成実行
            print(f"🔄 バッチ生成実行中...")
            images = generator.current_pipeline(
                prompt=prompt,
                negative_prompt=negative_prompt,
                num_images_per_prompt=batch_size,
                num_inference_steps=20,
                guidance_scale=7.5
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
            
            # メモリ最適化
            self._optimize_memory()
            
            return results
            
        except Exception as e:
            print(f"❌ バッチ生成エラー: {str(e)}")
            return []
    
    def generate_mufufu_batch_collection(self, style="clear_beautiful", batch_size=4):
        """ムフフバッチ画像コレクション生成"""
        print(f"🎨 ムフフバッチ画像生成開始！({batch_size}枚)")
        print(f"   スタイル: {style}")
        print("=" * 60)
        
        if style not in self.phase1_system.mufufu_prompts:
            style = "clear_beautiful"
        
        # ムフフプロンプト選択
        prompt = random.choice(self.phase1_system.mufufu_prompts[style])
        negative_prompt = ", ".join(self.phase1_system.negative_prompts)
        
        # バッチ生成実行
        results = self.generate_batch_images(
            prompt=prompt,
            negative_prompt=negative_prompt,
            batch_size=batch_size
        )
        
        return results
    
    def generate_hybrid_parallel_batch(self, count=8):
        """ハイブリッド並列+バッチ処理"""
        print(f"🔥 ハイブリッド並列+バッチ処理開始！({count}枚)")
        print("   並列処理 + バッチ処理の組み合わせ")
        print("=" * 60)
        
        start_time = time.time()
        
        # 並列処理で異なるスタイルを生成
        parallel_count = min(count // 2, self.max_workers)
        batch_count = count - parallel_count
        
        results = []
        
        # 並列処理部分
        if parallel_count > 0:
            print(f"🚀 並列処理: {parallel_count}枚")
            parallel_results = self.phase1_system.generate_phase1_parallel_collection(parallel_count)
            results.extend(parallel_results)
        
        # バッチ処理部分
        if batch_count > 0:
            print(f"📦 バッチ処理: {batch_count}枚")
            style = random.choice(list(self.phase1_system.mufufu_prompts.keys()))
            batch_results = self.generate_mufufu_batch_collection(style, batch_count)
            results.extend([{"success": True, "path": path, "style": style} for path in batch_results])
        
        total_time = time.time() - start_time
        success_count = sum(1 for r in results if r.get("success", False))
        
        print(f"\n🎉 ハイブリッド並列+バッチ処理完了！")
        print(f"   総時間: {total_time:.1f}秒")
        print(f"   成功: {success_count}/{count} 枚")
        print(f"   平均時間: {total_time/count:.1f}秒/枚")
        print(f"   総合効率: {success_count/total_time:.2f}枚/秒")
        
        return results
    
    def benchmark_batch_performance(self, test_batch_sizes=[2, 4, 6, 8]):
        """バッチ処理パフォーマンスベンチマーク"""
        print(f"📊 バッチ処理パフォーマンスベンチマーク")
        print("=" * 60)
        
        results = []
        
        for batch_size in test_batch_sizes:
            print(f"\n🧪 バッチサイズ {batch_size} テスト")
            
            # バッチ処理テスト
            start_time = time.time()
            batch_results = self.generate_mufufu_batch_collection(
                style="clear_beautiful",
                batch_size=batch_size
            )
            batch_time = time.time() - start_time
            batch_success = len(batch_results)
            
            # 並列処理との比較
            start_time = time.time()
            parallel_results = self.phase1_system.generate_phase1_parallel_collection(batch_size)
            parallel_time = time.time() - start_time
            parallel_success = sum(1 for r in parallel_results if r["success"])
            
            results.append({
                "batch_size": batch_size,
                "batch_time": batch_time,
                "batch_success": batch_success,
                "parallel_time": parallel_time,
                "parallel_success": parallel_success,
                "batch_efficiency": batch_success/batch_time if batch_time > 0 else 0,
                "parallel_efficiency": parallel_success/parallel_time if parallel_time > 0 else 0,
                "speedup": parallel_time/batch_time if batch_time > 0 else 0
            })
            
            print(f"   バッチ処理: {batch_time:.1f}秒 ({batch_success}枚成功)")
            print(f"   並列処理: {parallel_time:.1f}秒 ({parallel_success}枚成功)")
            print(f"   高速化倍率: {results[-1]['speedup']:.2f}倍")
        
        # 結果サマリー
        print(f"\n📈 バッチ処理ベンチマーク結果サマリー")
        print("=" * 60)
        for result in results:
            print(f"   バッチサイズ{result['batch_size']}: バッチ{result['batch_efficiency']:.2f}枚/秒, 並列{result['parallel_efficiency']:.2f}枚/秒, 高速化{result['speedup']:.2f}倍")
        
        return results
    
    def optimize_memory_usage(self):
        """メモリ使用量最適化"""
        print(f"🧠 メモリ使用量最適化")
        print("=" * 60)
        
        # 現在のメモリ使用量
        if not self._check_memory_usage():
            print("⚠️ メモリ使用率が高いため、最適化を実行します")
            self._optimize_memory()
        
        # 最適化後のメモリ使用量
        print("✅ メモリ最適化完了")
        self._check_memory_usage()
    
    def test_memory_efficiency(self, test_sizes=[2, 4, 6, 8]):
        """メモリ効率テスト"""
        print(f"🧠 メモリ効率テスト")
        print("=" * 60)
        
        results = []
        
        for size in test_sizes:
            print(f"\n🧪 メモリ効率テスト {size}枚")
            
            # メモリ使用量測定前
            print("📊 最適化前メモリ使用量")
            self._check_memory_usage()
            
            # バッチ処理実行
            start_time = time.time()
            batch_results = self.generate_mufufu_batch_collection(
                style="clear_beautiful",
                batch_size=size
            )
            batch_time = time.time() - start_time
            
            # メモリ最適化
            self._optimize_memory()
            
            # メモリ使用量測定後
            print("📊 最適化後メモリ使用量")
            self._check_memory_usage()
            
            results.append({
                "size": size,
                "time": batch_time,
                "success": len(batch_results),
                "efficiency": len(batch_results)/batch_time if batch_time > 0 else 0
            })
            
            print(f"   バッチ処理: {batch_time:.1f}秒 ({len(batch_results)}枚成功)")
            print(f"   効率: {results[-1]['efficiency']:.2f}枚/秒")
        
        return results
    
    def cleanup(self):
        """リソースクリーンアップ"""
        # メモリ最適化
        self._optimize_memory()
        
        # Phase 1システムクリーンアップ
        if hasattr(self.phase1_system, 'cleanup'):
            self.phase1_system.cleanup()
        
        print("🧹 Phase 2 バッチ処理システムクリーンアップ完了")


def main():
    """メイン関数"""
    print("🚀 Phase 2: バッチ処理統合")
    print("=" * 60)
    
    # Phase 2 バッチ処理システム初期化
    phase2_system = Phase2BatchProcessing(max_workers=4)
    
    try:
        # バッチ処理テスト
        print("\n📦 バッチ処理テスト")
        batch_results = phase2_system.generate_mufufu_batch_collection(
            style="cute_kawaii",
            batch_size=4
        )
        
        # ハイブリッド処理テスト
        print("\n🔥 ハイブリッド処理テスト")
        hybrid_results = phase2_system.generate_hybrid_parallel_batch(count=8)
        
        # バッチ処理パフォーマンスベンチマーク
        print("\n📊 バッチ処理パフォーマンスベンチマーク")
        benchmark_results = phase2_system.benchmark_batch_performance([2, 4, 6, 8])
        
        # メモリ効率テスト
        print("\n🧠 メモリ効率テスト")
        memory_results = phase2_system.test_memory_efficiency([2, 4, 6])
        
        print(f"\n🎉 Phase 2 バッチ処理統合完了！")
        print(f"   Stable Diffusionバッチ機能: 実装完了")
        print(f"   メモリ効率向上: 実装完了")
        print(f"   ハイブリッド処理: 実装完了")
        print(f"   パフォーマンス: ベンチマーク完了")
        
    finally:
        # クリーンアップ
        phase2_system.cleanup()


if __name__ == "__main__":
    main()
