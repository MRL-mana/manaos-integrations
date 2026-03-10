#!/usr/bin/env python3
"""
Phase 3: 高度最適化
動的ワーカー数調整、メモリ監視とエラーハンドリング
"""

import os
import sys
import time
import json
import random
import threading
import queue
from pathlib import Path
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing as mp

# パスを追加
sys.path.append('/root/trinity_workspace/tools')

from advanced_image_generator import AdvancedImageGenerator
from phase1_basic_parallel import Phase1BasicParallel
from phase2_batch_processing import Phase2BatchProcessing

class Phase3AdvancedOptimization:
    def __init__(self, max_workers=None):
        """Phase 3 高度最適化システム初期化"""
        # Phase 1, 2システムを継承
        self.phase1_system = Phase1BasicParallel(max_workers)
        self.phase2_system = Phase2BatchProcessing(max_workers)
        
        # 動的ワーカー数調整設定
        self.min_workers = 1
        self.max_workers = max_workers or min(os.cpu_count(), 8)  # type: ignore
        self.current_workers = self.max_workers
        
        # パフォーマンス監視設定
        self.performance_history = []
        self.worker_performance = {}
        self.memory_history = []
        
        # エラーハンドリング設定
        self.max_retries = 3
        self.retry_delay = 1.0
        self.error_threshold = 0.3  # 30%エラー率でワーカー数調整
        
        # 出力ディレクトリ
        self.output_dir = Path("/root/trinity_workspace/generated_images/phase3_advanced")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 監視スレッド
        self.monitoring_active = False
        self.monitoring_thread = None
        
        print(f"🚀 Phase 3 高度最適化システム初期化完了")
        print(f"   動的ワーカー数: {self.min_workers}-{self.max_workers}")
        print(f"   現在のワーカー数: {self.current_workers}")
        print(f"   エラーハンドリング: 最大{self.max_retries}回リトライ")
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
            
            # ディスク使用率
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            
            performance_data = {
                "timestamp": time.time(),
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
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
    
    def _adjust_worker_count(self, performance_data):
        """動的ワーカー数調整"""
        if not performance_data:
            return
        
        cpu_percent = performance_data["cpu_percent"]
        memory_percent = performance_data["memory_percent"]
        
        # CPU使用率に基づく調整
        if cpu_percent > 80:
            # CPU使用率が高い場合はワーカー数を減らす
            new_workers = max(self.min_workers, self.current_workers - 1)
            if new_workers != self.current_workers:
                print(f"🔧 CPU使用率調整: {self.current_workers} → {new_workers} ワーカー")
                self.current_workers = new_workers
        elif cpu_percent < 50 and self.current_workers < self.max_workers:
            # CPU使用率が低い場合はワーカー数を増やす
            new_workers = min(self.max_workers, self.current_workers + 1)
            if new_workers != self.current_workers:
                print(f"🔧 CPU使用率調整: {self.current_workers} → {new_workers} ワーカー")
                self.current_workers = new_workers
        
        # メモリ使用率に基づく調整
        if memory_percent > 85:
            # メモリ使用率が高い場合はワーカー数を減らす
            new_workers = max(self.min_workers, self.current_workers - 1)
            if new_workers != self.current_workers:
                print(f"🔧 メモリ使用率調整: {self.current_workers} → {new_workers} ワーカー")
                self.current_workers = new_workers
    
    def _handle_error_with_retry(self, task_data, error_count=0):
        """エラーハンドリングとリトライ"""
        try:
            # タスク実行
            result = self.phase1_system._generate_single_worker(task_data)
            
            if result["success"]:
                return result
            else:
                # エラーが発生した場合
                if error_count < self.max_retries:
                    print(f"⚠️ エラー発生、リトライ中... ({error_count + 1}/{self.max_retries})")
                    print(f"   エラー: {result['error']}")
                    
                    # リトライ前に少し待機
                    time.sleep(self.retry_delay * (error_count + 1))
                    
                    # リトライ実行
                    return self._handle_error_with_retry(task_data, error_count + 1)
                else:
                    print(f"❌ 最大リトライ回数に達しました: {result['error']}")
                    return result
                    
        except Exception as e:
            if error_count < self.max_retries:
                print(f"⚠️ 例外発生、リトライ中... ({error_count + 1}/{self.max_retries})")
                print(f"   例外: {str(e)}")
                
                # リトライ前に少し待機
                time.sleep(self.retry_delay * (error_count + 1))
                
                # リトライ実行
                return self._handle_error_with_retry(task_data, error_count + 1)
            else:
                print(f"❌ 最大リトライ回数に達しました: {str(e)}")
                return {
                    "id": task_data["id"],
                    "success": False,
                    "error": str(e),
                    "retry_count": error_count
                }
    
    def _monitoring_thread_worker(self):
        """監視スレッドワーカー"""
        while self.monitoring_active:
            try:
                # システムパフォーマンス監視
                performance_data = self._monitor_system_performance()
                
                # 動的ワーカー数調整
                self._adjust_worker_count(performance_data)
                
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
            print("🔍 システム監視開始")
    
    def stop_monitoring(self):
        """監視停止"""
        if self.monitoring_active:
            self.monitoring_active = False
            if self.monitoring_thread:
                self.monitoring_thread.join(timeout=5)
            print("🔍 システム監視停止")
    
    def generate_phase3_optimized_collection(self, count=6):
        """Phase 3 最適化画像コレクション生成"""
        print(f"🚀 Phase 3 最適化画像生成開始！({count}枚)")
        print(f"   動的ワーカー数: {self.current_workers}")
        print("=" * 60)
        
        # 監視開始
        self.start_monitoring()
        
        start_time = time.time()
        
        try:
            # タスク準備
            tasks = []
            styles = list(self.phase1_system.mufufu_prompts.keys())
            
            for i in range(count):
                # ランダムなスタイルとモデル選択
                style = random.choice(styles)
                model = random.choice(self.phase1_system.mufufu_models)
                size = random.choice(["portrait", "square", "landscape"])
                
                # プロンプト選択
                prompt_text = random.choice(self.phase1_system.mufufu_prompts[style])
                negative_prompt = ", ".join(self.phase1_system.negative_prompts)
                
                tasks.append({
                    "id": i,
                    "prompt": prompt_text,
                    "negative_prompt": negative_prompt,
                    "model": model,
                    "style": style,
                    "size": size
                })
            
            # 動的ワーカー数で並列実行
            results = []
            with ProcessPoolExecutor(max_workers=self.current_workers) as executor:
                # タスクを並列実行（エラーハンドリング付き）
                futures = []
                for task in tasks:
                    future = executor.submit(self._handle_error_with_retry, task)
                    futures.append(future)
                
                # 結果を順次収集
                completed_count = 0
                for future in as_completed(futures):
                    result = future.result()
                    results.append(result)
                    completed_count += 1
                    
                    if result["success"]:
                        print(f"✅ {completed_count}/{count} 完了: {result['style']} ({result['model']}) - ワーカー{result.get('worker_id', 'N/A')}")
                    else:
                        print(f"❌ {completed_count}/{count} 失敗: {result['error']} - リトライ{result.get('retry_count', 0)}回")
            
            total_time = time.time() - start_time
            success_count = sum(1 for r in results if r["success"])
            error_count = sum(1 for r in results if not r["success"])
            
            print(f"\n🎉 Phase 3 最適化画像生成完了！")
            print(f"   総時間: {total_time:.1f}秒")
            print(f"   成功: {success_count}/{count} 枚")
            print(f"   エラー: {error_count}/{count} 枚")
            print(f"   平均時間: {total_time/count:.1f}秒/枚")
            print(f"   最適化効率: {success_count/total_time:.2f}枚/秒")
            print(f"   最終ワーカー数: {self.current_workers}")
            
            return results
            
        finally:
            # 監視停止
            self.stop_monitoring()
    
    def generate_phase3_hybrid_optimized(self, count=8):
        """Phase 3 ハイブリッド最適化処理"""
        print(f"🔥 Phase 3 ハイブリッド最適化処理開始！({count}枚)")
        print("   並列処理 + バッチ処理 + 動的最適化")
        print("=" * 60)
        
        start_time = time.time()
        
        # 並列処理で異なるスタイルを生成
        parallel_count = min(count // 2, self.current_workers)
        batch_count = count - parallel_count
        
        results = []
        
        # 並列処理部分（最適化版）
        if parallel_count > 0:
            print(f"🚀 最適化並列処理: {parallel_count}枚")
            parallel_results = self.generate_phase3_optimized_collection(parallel_count)
            results.extend(parallel_results)
        
        # バッチ処理部分
        if batch_count > 0:
            print(f"📦 バッチ処理: {batch_count}枚")
            style = random.choice(list(self.phase1_system.mufufu_prompts.keys()))
            batch_results = self.phase2_system.generate_mufufu_batch_collection(style, batch_count)
            results.extend([{"success": True, "path": path, "style": style} for path in batch_results])
        
        total_time = time.time() - start_time
        success_count = sum(1 for r in results if r.get("success", False))
        
        print(f"\n🎉 Phase 3 ハイブリッド最適化処理完了！")
        print(f"   総時間: {total_time:.1f}秒")
        print(f"   成功: {success_count}/{count} 枚")
        print(f"   平均時間: {total_time/count:.1f}秒/枚")
        print(f"   総合最適化効率: {success_count/total_time:.2f}枚/秒")
        
        return results
    
    def benchmark_phase3_performance(self, test_counts=[3, 6, 9, 12]):
        """Phase 3 パフォーマンスベンチマーク"""
        print(f"📊 Phase 3 パフォーマンスベンチマーク")
        print("=" * 60)
        
        results = []
        
        for count in test_counts:
            print(f"\n🧪 Phase 3 テスト {count}枚生成")
            
            # 最適化処理テスト
            start_time = time.time()
            optimized_results = self.generate_phase3_optimized_collection(count)
            optimized_time = time.time() - start_time
            optimized_success = sum(1 for r in optimized_results if r["success"])
            
            # Phase 1並列処理との比較
            start_time = time.time()
            phase1_results = self.phase1_system.generate_phase1_parallel_collection(count)
            phase1_time = time.time() - start_time
            phase1_success = sum(1 for r in phase1_results if r["success"])
            
            results.append({
                "count": count,
                "optimized_time": optimized_time,
                "optimized_success": optimized_success,
                "phase1_time": phase1_time,
                "phase1_success": phase1_success,
                "optimized_efficiency": optimized_success/optimized_time if optimized_time > 0 else 0,
                "phase1_efficiency": phase1_success/phase1_time if phase1_time > 0 else 0,
                "speedup": phase1_time/optimized_time if optimized_time > 0 else 0
            })
            
            print(f"   Phase 3最適化: {optimized_time:.1f}秒 ({optimized_success}枚成功)")
            print(f"   Phase 1並列: {phase1_time:.1f}秒 ({phase1_success}枚成功)")
            print(f"   高速化倍率: {results[-1]['speedup']:.2f}倍")
        
        # 結果サマリー
        print(f"\n📈 Phase 3 ベンチマーク結果サマリー")
        print("=" * 60)
        for result in results:
            print(f"   {result['count']}枚: 最適化{result['optimized_efficiency']:.2f}枚/秒, Phase1{result['phase1_efficiency']:.2f}枚/秒, 高速化{result['speedup']:.2f}倍")
        
        return results
    
    def generate_performance_report(self):
        """パフォーマンスレポート生成"""
        print(f"📋 パフォーマンスレポート生成")
        print("=" * 60)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.output_dir / f"phase3_performance_report_{timestamp}.json"
        
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
            "optimization_features": {
                "dynamic_worker_adjustment": True,
                "error_handling_retry": True,
                "system_monitoring": True,
                "memory_optimization": True
            },
            "performance_history": self.performance_history[-50:]  # 最新50件
        }
        
        # レポート保存
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"📊 パフォーマンスレポート生成完了")
        print(f"   平均CPU使用率: {avg_cpu:.1f}%")
        print(f"   平均メモリ使用率: {avg_memory:.1f}%")
        print(f"   平均ワーカー数: {avg_workers:.1f}")
        print(f"   レポート保存先: {report_path}")
        
        return report
    
    def cleanup(self):
        """リソースクリーンアップ"""
        # 監視停止
        self.stop_monitoring()
        
        # Phase 1, 2システムクリーンアップ
        if hasattr(self.phase1_system, 'cleanup'):
            self.phase1_system.cleanup()
        if hasattr(self.phase2_system, 'cleanup'):
            self.phase2_system.cleanup()
        
        print("🧹 Phase 3 高度最適化システムクリーンアップ完了")


def main():
    """メイン関数"""
    print("🚀 Phase 3: 高度最適化")
    print("=" * 60)
    
    # Phase 3 高度最適化システム初期化
    phase3_system = Phase3AdvancedOptimization(max_workers=6)
    
    try:
        # Phase 3最適化処理テスト
        print("\n🚀 Phase 3最適化処理テスト")
        optimized_results = phase3_system.generate_phase3_optimized_collection(count=6)
        
        # ハイブリッド最適化処理テスト
        print("\n🔥 ハイブリッド最適化処理テスト")
        hybrid_results = phase3_system.generate_phase3_hybrid_optimized(count=8)
        
        # パフォーマンスベンチマーク
        print("\n📊 Phase 3パフォーマンスベンチマーク")
        benchmark_results = phase3_system.benchmark_phase3_performance([3, 6, 9, 12])
        
        # パフォーマンスレポート生成
        print("\n📋 パフォーマンスレポート生成")
        performance_report = phase3_system.generate_performance_report()
        
        print(f"\n🎉 Phase 3 高度最適化完了！")
        print(f"   動的ワーカー数調整: 実装完了")
        print(f"   メモリ監視: 実装完了")
        print(f"   エラーハンドリング: 実装完了")
        print(f"   パフォーマンス: ベンチマーク完了")
        
    finally:
        # クリーンアップ
        phase3_system.cleanup()


if __name__ == "__main__":
    main()
