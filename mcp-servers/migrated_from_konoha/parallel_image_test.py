#!/usr/bin/env python3
"""
Parallel Image Generation Test
並列画像生成システムのテストとベンチマーク
"""

import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime

# パスを追加
sys.path.append('/root/trinity_workspace/tools')

from parallel_image_generator import ParallelImageGenerator
from parallel_mufufu_generator import ParallelMufufuGenerator

class ParallelImageTest:
    def __init__(self):
        """並列画像生成テスト初期化"""
        self.test_results = []
        self.output_dir = Path("/root/trinity_workspace/generated_images/test_results")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        print("🧪 並列画像生成テストシステム初期化完了")
    
    def test_basic_parallel(self):
        """基本並列処理テスト"""
        print("\n🧪 基本並列処理テスト開始")
        print("=" * 50)
        
        generator = ParallelImageGenerator(max_workers=2)  # 2並列でテスト
        
        try:
            start_time = time.time()
            results = generator.generate_parallel_collection(count=3)
            test_time = time.time() - start_time
            
            success_count = sum(1 for r in results if r["success"])
            
            test_result = {
                "test_name": "basic_parallel",
                "count": 3,
                "time": test_time,
                "success_count": success_count,
                "efficiency": success_count/test_time if test_time > 0 else 0,
                "status": "PASS" if success_count >= 2 else "FAIL"
            }
            
            self.test_results.append(test_result)
            
            print(f"✅ 基本並列処理テスト完了")
            print(f"   時間: {test_time:.1f}秒")
            print(f"   成功: {success_count}/3 枚")
            print(f"   効率: {test_result['efficiency']:.2f}枚/秒")
            print(f"   ステータス: {test_result['status']}")
            
        except Exception as e:
            test_result = {
                "test_name": "basic_parallel",
                "error": str(e),
                "status": "ERROR"
            }
            self.test_results.append(test_result)
            print(f"❌ 基本並列処理テストエラー: {str(e)}")
        
        finally:
            generator.cleanup()
    
    def test_batch_processing(self):
        """バッチ処理テスト"""
        print("\n🧪 バッチ処理テスト開始")
        print("=" * 50)
        
        generator = ParallelImageGenerator(max_workers=2)
        
        try:
            start_time = time.time()
            results = generator.generate_batch_collection(
                prompt="a beautiful anime girl, high quality, detailed",
                batch_size=3
            )
            test_time = time.time() - start_time
            
            success_count = len(results)
            
            test_result = {
                "test_name": "batch_processing",
                "count": 3,
                "time": test_time,
                "success_count": success_count,
                "efficiency": success_count/test_time if test_time > 0 else 0,
                "status": "PASS" if success_count >= 2 else "FAIL"
            }
            
            self.test_results.append(test_result)
            
            print(f"✅ バッチ処理テスト完了")
            print(f"   時間: {test_time:.1f}秒")
            print(f"   成功: {success_count}/3 枚")
            print(f"   効率: {test_result['efficiency']:.2f}枚/秒")
            print(f"   ステータス: {test_result['status']}")
            
        except Exception as e:
            test_result = {
                "test_name": "batch_processing",
                "error": str(e),
                "status": "ERROR"
            }
            self.test_results.append(test_result)
            print(f"❌ バッチ処理テストエラー: {str(e)}")
        
        finally:
            generator.cleanup()
    
    def test_mufufu_parallel(self):
        """ムフフ並列処理テスト"""
        print("\n🧪 ムフフ並列処理テスト開始")
        print("=" * 50)
        
        generator = ParallelMufufuGenerator(max_workers=2)
        
        try:
            start_time = time.time()
            results = generator.generate_mufufu_parallel_collection(count=4)
            test_time = time.time() - start_time
            
            success_count = sum(1 for r in results if r["success"])
            
            test_result = {
                "test_name": "mufufu_parallel",
                "count": 4,
                "time": test_time,
                "success_count": success_count,
                "efficiency": success_count/test_time if test_time > 0 else 0,
                "status": "PASS" if success_count >= 3 else "FAIL"
            }
            
            self.test_results.append(test_result)
            
            print(f"✅ ムフフ並列処理テスト完了")
            print(f"   時間: {test_time:.1f}秒")
            print(f"   成功: {success_count}/4 枚")
            print(f"   効率: {test_result['efficiency']:.2f}枚/秒")
            print(f"   ステータス: {test_result['status']}")
            
        except Exception as e:
            test_result = {
                "test_name": "mufufu_parallel",
                "error": str(e),
                "status": "ERROR"
            }
            self.test_results.append(test_result)
            print(f"❌ ムフフ並列処理テストエラー: {str(e)}")
        
        finally:
            generator.cleanup()
    
    def test_mufufu_batch(self):
        """ムフフバッチ処理テスト"""
        print("\n🧪 ムフフバッチ処理テスト開始")
        print("=" * 50)
        
        generator = ParallelMufufuGenerator(max_workers=2)
        
        try:
            start_time = time.time()
            results = generator.generate_mufufu_batch_collection(
                style="cute_kawaii",
                batch_size=3
            )
            test_time = time.time() - start_time
            
            success_count = len(results)
            
            test_result = {
                "test_name": "mufufu_batch",
                "count": 3,
                "time": test_time,
                "success_count": success_count,
                "efficiency": success_count/test_time if test_time > 0 else 0,
                "status": "PASS" if success_count >= 2 else "FAIL"
            }
            
            self.test_results.append(test_result)
            
            print(f"✅ ムフフバッチ処理テスト完了")
            print(f"   時間: {test_time:.1f}秒")
            print(f"   成功: {success_count}/3 枚")
            print(f"   効率: {test_result['efficiency']:.2f}枚/秒")
            print(f"   ステータス: {test_result['status']}")
            
        except Exception as e:
            test_result = {
                "test_name": "mufufu_batch",
                "error": str(e),
                "status": "ERROR"
            }
            self.test_results.append(test_result)
            print(f"❌ ムフフバッチ処理テストエラー: {str(e)}")
        
        finally:
            generator.cleanup()
    
    def test_hybrid_processing(self):
        """ハイブリッド処理テスト"""
        print("\n🧪 ハイブリッド処理テスト開始")
        print("=" * 50)
        
        generator = ParallelImageGenerator(max_workers=2)
        
        try:
            start_time = time.time()
            results = generator.generate_hybrid_collection(count=5)
            test_time = time.time() - start_time
            
            success_count = sum(1 for r in results if r.get("success", False))
            
            test_result = {
                "test_name": "hybrid_processing",
                "count": 5,
                "time": test_time,
                "success_count": success_count,
                "efficiency": success_count/test_time if test_time > 0 else 0,
                "status": "PASS" if success_count >= 4 else "FAIL"
            }
            
            self.test_results.append(test_result)
            
            print(f"✅ ハイブリッド処理テスト完了")
            print(f"   時間: {test_time:.1f}秒")
            print(f"   成功: {success_count}/5 枚")
            print(f"   効率: {test_result['efficiency']:.2f}枚/秒")
            print(f"   ステータス: {test_result['status']}")
            
        except Exception as e:
            test_result = {
                "test_name": "hybrid_processing",
                "error": str(e),
                "status": "ERROR"
            }
            self.test_results.append(test_result)
            print(f"❌ ハイブリッド処理テストエラー: {str(e)}")
        
        finally:
            generator.cleanup()
    
    def run_performance_benchmark(self):
        """パフォーマンスベンチマーク実行"""
        print("\n📊 パフォーマンスベンチマーク実行")
        print("=" * 60)
        
        # 並列処理ベンチマーク
        generator = ParallelImageGenerator(max_workers=4)
        try:
            benchmark_results = generator.benchmark_performance([1, 3, 6])
            self.test_results.append({
                "test_name": "performance_benchmark",
                "results": benchmark_results,
                "status": "PASS"
            })
        except Exception as e:
            self.test_results.append({
                "test_name": "performance_benchmark",
                "error": str(e),
                "status": "ERROR"
            })
        finally:
            generator.cleanup()
        
        # ムフフベンチマーク
        mufufu_generator = ParallelMufufuGenerator(max_workers=4)
        try:
            mufufu_benchmark_results = mufufu_generator.benchmark_mufufu_performance([2, 4, 6])
            self.test_results.append({
                "test_name": "mufufu_performance_benchmark",
                "results": mufufu_benchmark_results,
                "status": "PASS"
            })
        except Exception as e:
            self.test_results.append({
                "test_name": "mufufu_performance_benchmark",
                "error": str(e),
                "status": "ERROR"
            })
        finally:
            mufufu_generator.cleanup()
    
    def generate_test_report(self):
        """テストレポート生成"""
        print("\n📋 テストレポート生成")
        print("=" * 60)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.output_dir / f"parallel_image_test_report_{timestamp}.json"
        
        # テスト結果サマリー
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r.get("status") == "PASS")
        failed_tests = sum(1 for r in self.test_results if r.get("status") == "FAIL")
        error_tests = sum(1 for r in self.test_results if r.get("status") == "ERROR")
        
        report = {
            "timestamp": timestamp,
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "error_tests": error_tests,
                "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0
            },
            "test_results": self.test_results
        }
        
        # レポート保存
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"📊 テストレポート生成完了")
        print(f"   総テスト数: {total_tests}")
        print(f"   成功: {passed_tests}")
        print(f"   失敗: {failed_tests}")
        print(f"   エラー: {error_tests}")
        print(f"   成功率: {report['summary']['success_rate']:.1f}%")
        print(f"   レポート保存先: {report_path}")
        
        return report
    
    def run_all_tests(self):
        """全テスト実行"""
        print("🧪 並列画像生成システム全テスト開始")
        print("=" * 60)
        
        # 基本テスト
        self.test_basic_parallel()
        self.test_batch_processing()
        self.test_mufufu_parallel()
        self.test_mufufu_batch()
        self.test_hybrid_processing()
        
        # パフォーマンスベンチマーク
        self.run_performance_benchmark()
        
        # テストレポート生成
        report = self.generate_test_report()
        
        print(f"\n🎉 全テスト完了！")
        print(f"   テストレポート: 生成完了")
        print(f"   成功率: {report['summary']['success_rate']:.1f}%")
        
        return report


def main():
    """メイン関数"""
    print("🧪 Parallel Image Generation Test")
    print("=" * 60)
    
    # テストシステム初期化
    test_system = ParallelImageTest()
    
    # 全テスト実行
    report = test_system.run_all_tests()
    
    print(f"\n🎉 並列画像生成システムテスト完了！")
    print(f"   システム準備完了: 並列処理、バッチ処理、ハイブリッド処理")
    print(f"   ムフフ画像生成: 並列処理、バッチ処理対応")
    print(f"   パフォーマンス: ベンチマーク完了")


if __name__ == "__main__":
    main()
