#!/usr/bin/env python3
"""
Adaptive Core System
臨機応変にコア数を変更するシステム
"""

import os
import sys
import time
import json
import random
import threading
from pathlib import Path
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing as mp

# パスを追加
sys.path.append('/root/trinity_workspace/tools')

from advanced_image_generator import AdvancedImageGenerator

class AdaptiveCoreSystem:
    def __init__(self):
        """臨機応変コア数システム初期化"""
        self.max_cpu_cores = os.cpu_count()  # 8コア
        self.current_workers = 4  # 初期値4コア
        self.min_workers = 1
        self.max_workers = self.max_cpu_cores
        
        # パフォーマンス監視設定
        self.performance_history = []
        self.worker_performance = {}
        self.memory_history = []
        
        # 適応的調整設定
        self.performance_threshold = 0.8  # 80%効率で調整
        self.memory_threshold = 0.9  # 90%メモリ使用率で調整
        self.cpu_threshold = 0.95  # 95%CPU使用率で調整
        
        # 出力ディレクトリ
        self.output_dir = Path("/root/trinity_workspace/generated_images/adaptive_core")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 監視スレッド
        self.monitoring_active = False
        self.monitoring_thread = None
        
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
        
        print(f"🚀 臨機応変コア数システム初期化完了")
        print(f"   CPUコア数: {self.max_cpu_cores}")
        print(f"   初期ワーカー数: {self.current_workers}")
        print(f"   適応範囲: {self.min_workers}-{self.max_workers}")
        print(f"   出力ディレクトリ: {self.output_dir}")
    
    def _monitor_system_performance(self):
        """システムパフォーマンス監視"""
        try:
            import psutil
            
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # メモリ使用率
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # スワップ使用率
            swap = psutil.swap_memory()
            swap_percent = swap.percent
            
            # ディスク使用率
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            
            performance_data = {
                "timestamp": time.time(),
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "swap_percent": swap_percent,
                "disk_percent": disk_percent,
                "current_workers": self.current_workers
            }
            
            self.performance_history.append(performance_data)
            
            # 履歴を保持（最新100件）
            if len(self.performance_history) > 100:
                self.performance_history = self.performance_history[-100:]
            
            return performance_data
            
        except ImportError:
            print("⚠️ psutilが利用できません。システム監視をスキップします。")
            return None
        except Exception as e:
            print(f"⚠️ システム監視エラー: {str(e)}")
            return None
    
    def _adjust_worker_count_adaptive(self, performance_data):
        """臨機応変にワーカー数調整"""
        if not performance_data:
            return
        
        cpu_percent = performance_data["cpu_percent"]
        memory_percent = performance_data["memory_percent"]
        swap_percent = performance_data["swap_percent"]
        
        old_workers = self.current_workers
        
        # CPU使用率に基づく調整
        if cpu_percent > self.cpu_threshold * 100:
            # CPU使用率が高い場合はワーカー数を減らす
            new_workers = max(self.min_workers, self.current_workers - 1)
            if new_workers != self.current_workers:
                print(f"🔧 CPU使用率調整: {self.current_workers} → {new_workers} ワーカー (CPU: {cpu_percent:.1f}%)")
                self.current_workers = new_workers
        elif cpu_percent < 70 and self.current_workers < self.max_workers:  # type: ignore
            # CPU使用率が低い場合はワーカー数を増やす
            new_workers = min(self.max_workers, self.current_workers + 1)  # type: ignore
            if new_workers != self.current_workers:
                print(f"🔧 CPU使用率調整: {self.current_workers} → {new_workers} ワーカー (CPU: {cpu_percent:.1f}%)")
                self.current_workers = new_workers
        
        # メモリ使用率に基づく調整
        if memory_percent > self.memory_threshold * 100:
            # メモリ使用率が高い場合はワーカー数を減らす
            new_workers = max(self.min_workers, self.current_workers - 1)
            if new_workers != self.current_workers:
                print(f"🔧 メモリ使用率調整: {self.current_workers} → {new_workers} ワーカー (メモリ: {memory_percent:.1f}%)")
                self.current_workers = new_workers
        
        # スワップ使用率に基づく調整
        if swap_percent > 95:
            # スワップ使用率が高い場合はワーカー数を減らす
            new_workers = max(self.min_workers, self.current_workers - 1)
            if new_workers != self.current_workers:
                print(f"🔧 スワップ使用率調整: {self.current_workers} → {new_workers} ワーカー (スワップ: {swap_percent:.1f}%)")
                self.current_workers = new_workers
        
        if old_workers != self.current_workers:
            print(f"✅ ワーカー数調整完了: {old_workers} → {self.current_workers}")
    
    def _monitoring_thread_worker(self):
        """監視スレッドワーカー"""
        while self.monitoring_active:
            try:
                # システムパフォーマンス監視
                performance_data = self._monitor_system_performance()
                
                # 臨機応変にワーカー数調整
                self._adjust_worker_count_adaptive(performance_data)
                
                # 1秒間隔で監視
                time.sleep(1)
                
            except Exception as e:
                print(f"⚠️ 監視スレッドエラー: {str(e)}")
                time.sleep(1)
    
    def start_monitoring(self):
        """監視開始"""
        if not self.monitoring_active:
            self.monitoring_active = True
            self.monitoring_thread = threading.Thread(target=self._monitoring_thread_worker)
            self.monitoring_thread.daemon = True
            self.monitoring_thread.start()
            print("🔍 臨機応変システム監視開始")
    
    def stop_monitoring(self):
        """監視停止"""
        if self.monitoring_active:
            self.monitoring_active = False
            if self.monitoring_thread:
                self.monitoring_thread.join(timeout=5)
            print("🔍 臨機応変システム監視停止")
    
    def _generate_single_worker(self, task_data):
        """単一ワーカーでの画像生成"""
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
    
    def generate_adaptive_collection(self, count=8):
        """臨機応変画像コレクション生成"""
        print(f"🚀 臨機応変画像生成開始！({count}枚)")
        print(f"   初期ワーカー数: {self.current_workers}")
        print("=" * 60)
        
        # 監視開始
        self.start_monitoring()
        
        start_time = time.time()
        
        try:
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
            
            # 臨機応変ワーカー数で並列実行
            results = []
            with ProcessPoolExecutor(max_workers=self.current_workers) as executor:
                # タスクを並列実行
                futures = [executor.submit(self._generate_single_worker, task) for task in tasks]
                
                # 結果を順次収集
                completed_count = 0
                for future in as_completed(futures):
                    result = future.result()
                    results.append(result)
                    completed_count += 1
                    
                    if result["success"]:
                        print(f"✅ {completed_count}/{count} 完了: {result['style']} ({result['model']}) - ワーカー{result.get('worker_id', 'N/A')}")
                    else:
                        print(f"❌ {completed_count}/{count} 失敗: {result['error']} - ワーカー{result.get('worker_id', 'N/A')}")
            
            total_time = time.time() - start_time
            success_count = sum(1 for r in results if r["success"])
            
            print(f"\n🎉 臨機応変画像生成完了！")
            print(f"   総時間: {total_time:.1f}秒")
            print(f"   成功: {success_count}/{count} 枚")
            print(f"   平均時間: {total_time/count:.1f}秒/枚")
            print(f"   臨機応変効率: {success_count/total_time:.2f}枚/秒")
            print(f"   最終ワーカー数: {self.current_workers}")
            
            return results
            
        finally:
            # 監視停止
            self.stop_monitoring()
    
    def benchmark_adaptive_performance(self, test_counts=[4, 8, 12, 16]):
        """臨機応変パフォーマンスベンチマーク"""
        print(f"📊 臨機応変パフォーマンスベンチマーク")
        print("=" * 60)
        
        results = []
        
        for count in test_counts:
            print(f"\n🧪 臨機応変テスト {count}枚生成")
            
            # 臨機応変処理テスト
            start_time = time.time()
            adaptive_results = self.generate_adaptive_collection(count)
            adaptive_time = time.time() - start_time
            adaptive_success = sum(1 for r in adaptive_results if r["success"])
            
            results.append({
                "count": count,
                "adaptive_time": adaptive_time,
                "adaptive_success": adaptive_success,
                "adaptive_efficiency": adaptive_success/adaptive_time if adaptive_time > 0 else 0,
                "final_workers": self.current_workers
            })
            
            print(f"   臨機応変処理: {adaptive_time:.1f}秒 ({adaptive_success}枚成功)")
            print(f"   効率: {results[-1]['adaptive_efficiency']:.2f}枚/秒")
            print(f"   最終ワーカー数: {results[-1]['final_workers']}")
        
        # 結果サマリー
        print(f"\n📈 臨機応変ベンチマーク結果サマリー")
        print("=" * 60)
        for result in results:
            print(f"   {result['count']}枚: {result['adaptive_efficiency']:.2f}枚/秒, 最終ワーカー数{result['final_workers']}")
        
        return results
    
    def generate_adaptive_report(self):
        """臨機応変レポート生成"""
        print(f"📋 臨機応変レポート生成")
        print("=" * 60)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.output_dir / f"adaptive_core_report_{timestamp}.json"
        
        # パフォーマンス履歴分析
        if self.performance_history:
            avg_cpu = sum(p["cpu_percent"] for p in self.performance_history) / len(self.performance_history)
            avg_memory = sum(p["memory_percent"] for p in self.performance_history) / len(self.performance_history)
            avg_workers = sum(p["current_workers"] for p in self.performance_history) / len(self.performance_history)
        else:
            avg_cpu = avg_memory = avg_workers = 0
        
        report = {
            "timestamp": timestamp,
            "system_info": {
                "max_cpu_cores": self.max_cpu_cores,
                "min_workers": self.min_workers,
                "max_workers": self.max_workers,
                "current_workers": self.current_workers,
                "avg_workers": avg_workers
            },
            "performance_metrics": {
                "avg_cpu_percent": avg_cpu,
                "avg_memory_percent": avg_memory,
                "monitoring_duration": len(self.performance_history)
            },
            "adaptive_features": {
                "dynamic_worker_adjustment": True,
                "cpu_based_adjustment": True,
                "memory_based_adjustment": True,
                "swap_based_adjustment": True,
                "real_time_monitoring": True
            },
            "performance_history": self.performance_history[-50:]  # 最新50件
        }
        
        # レポート保存
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"📊 臨機応変レポート生成完了")
        print(f"   平均CPU使用率: {avg_cpu:.1f}%")
        print(f"   平均メモリ使用率: {avg_memory:.1f}%")
        print(f"   平均ワーカー数: {avg_workers:.1f}")
        print(f"   レポート保存先: {report_path}")
        
        return report
    
    def cleanup(self):
        """リソースクリーンアップ"""
        # 監視停止
        self.stop_monitoring()
        print("🧹 臨機応変コア数システムクリーンアップ完了")


def main():
    """メイン関数"""
    print("🚀 Adaptive Core System")
    print("=" * 60)
    
    # 臨機応変コア数システム初期化
    adaptive_system = AdaptiveCoreSystem()
    
    try:
        # 臨機応変処理テスト
        print("\n🚀 臨機応変処理テスト")
        adaptive_results = adaptive_system.generate_adaptive_collection(count=8)
        
        # パフォーマンスベンチマーク
        print("\n📊 臨機応変パフォーマンスベンチマーク")
        benchmark_results = adaptive_system.benchmark_adaptive_performance([4, 8, 12, 16])
        
        # 臨機応変レポート生成
        print("\n📋 臨機応変レポート生成")
        adaptive_report = adaptive_system.generate_adaptive_report()
        
        print(f"\n🎉 臨機応変コア数システム完了！")
        print(f"   動的ワーカー数調整: 実装完了")
        print(f"   リアルタイム監視: 実装完了")
        print(f"   パフォーマンス: ベンチマーク完了")
        
    finally:
        # クリーンアップ
        adaptive_system.cleanup()


if __name__ == "__main__":
    main()
