#!/usr/bin/env python3
"""
Distributed Image Generator
X280との分散並列画像生成システム
"""

import os
import sys
import time
import json
import random
import subprocess
from pathlib import Path
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed, ThreadPoolExecutor
import threading
import queue

# パスを追加
sys.path.append('/root/trinity_workspace/tools')

from parallel_image_generator import ParallelImageGenerator
from parallel_mufufu_generator import ParallelMufufuGenerator

class DistributedImageGenerator:
    def __init__(self, use_x280=True, max_local_workers=4):
        """分散画像生成システム初期化"""
        self.use_x280 = use_x280
        self.max_local_workers = max_local_workers
        
        # X280接続設定
        self.x280_host = "x280"
        self.x280_user = "mana"
        self.x280_workspace = "/home/mana/trinity_workspace"
        
        # 出力ディレクトリ
        self.output_dir = Path("/root/trinity_workspace/generated_images/distributed")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # タスクキュー
        self.task_queue = queue.Queue()
        self.result_queue = queue.Queue()
        
        # X280接続テスト
        self.x280_available = False
        if self.use_x280:
            self.x280_available = self._test_x280_connection()
        
        print(f"🌐 分散画像生成システム初期化完了")
        print(f"   ローカルワーカー数: {self.max_local_workers}")
        print(f"   X280利用: {'✅' if self.x280_available else '❌'}")
        print(f"   出力ディレクトリ: {self.output_dir}")
    
    def _test_x280_connection(self):
        """X280接続テスト"""
        try:
            print("🔍 X280接続テスト中...")
            
            # SSH接続テスト
            result = subprocess.run([
                "ssh", f"{self.x280_user}@{self.x280_host}",
                "echo 'X280接続成功'"
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                print("✅ X280接続成功")
                
                # ワークスペース確認
                workspace_check = subprocess.run([
                    "ssh", f"{self.x280_user}@{self.x280_host}",
                    f"test -d {self.x280_workspace} && echo 'ワークスペース存在'"
                ], capture_output=True, text=True, timeout=10)
                
                if workspace_check.returncode == 0:
                    print("✅ X280ワークスペース確認完了")
                    return True
                else:
                    print("⚠️ X280ワークスペースが見つかりません")
                    return False
            else:
                print("❌ X280接続失敗")
                return False
                
        except Exception as e:
            print(f"❌ X280接続テストエラー: {str(e)}")
            return False
    
    def _setup_x280_environment(self):
        """X280環境セットアップ"""
        if not self.x280_available:
            return False
        
        try:
            print("🔧 X280環境セットアップ中...")
            
            # 必要なディレクトリ作成
            subprocess.run([
                "ssh", f"{self.x280_user}@{self.x280_host}",
                f"mkdir -p {self.x280_workspace}/generated_images"
            ], timeout=10)
            
            # 画像生成スクリプトをX280にコピー
            subprocess.run([
                "scp", "/root/trinity_workspace/tools/parallel_image_generator.py",
                f"{self.x280_user}@{self.x280_host}:{self.x280_workspace}/"
            ], timeout=30)
            
            subprocess.run([
                "scp", "/root/trinity_workspace/tools/parallel_mufufu_generator.py",
                f"{self.x280_user}@{self.x280_host}:{self.x280_workspace}/"
            ], timeout=30)
            
            print("✅ X280環境セットアップ完了")
            return True
            
        except Exception as e:
            print(f"❌ X280環境セットアップエラー: {str(e)}")
            return False
    
    def _generate_on_x280(self, task_data):
        """X280で画像生成実行"""
        try:
            task_id = task_data["id"]
            prompt = task_data["prompt"]
            negative_prompt = task_data["negative_prompt"]
            model = task_data["model"]
            style = task_data["style"]
            size = task_data["size"]
            
            print(f"🚀 X280で画像生成開始: {task_id}")
            
            # X280で画像生成実行
            cmd = [
                "ssh", f"{self.x280_user}@{self.x280_host}",
                f"cd {self.x280_workspace} && python3 -c \""
                f"import sys; sys.path.append('.'); "
                f"from parallel_mufufu_generator import ParallelMufufuGenerator; "
                f"gen = ParallelMufufuGenerator(max_workers=2); "
                f"result = gen.generate_mufufu_parallel_collection(1, ['{style}']); "
                f"print('X280_RESULT:', result[0]['path'] if result and result[0]['success'] else 'FAILED')"
                f"\""
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0 and "X280_RESULT:" in result.stdout:
                output_path = result.stdout.split("X280_RESULT:")[-1].strip()
                if output_path != "FAILED":
                    # 生成された画像をローカルにコピー
                    local_filename = f"x280_{task_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    local_path = self.output_dir / local_filename
                    
                    subprocess.run([
                        "scp", f"{self.x280_user}@{self.x280_host}:{output_path}",
                        str(local_path)
                    ], timeout=30)
                    
                    return {
                        "id": task_id,
                        "success": True,
                        "path": str(local_path),
                        "worker": "X280",
                        "style": style,
                        "model": model,
                        "size": size
                    }
            
            return {
                "id": task_id,
                "success": False,
                "error": "X280生成失敗",
                "worker": "X280"
            }
            
        except Exception as e:
            return {
                "id": task_data["id"],
                "success": False,
                "error": f"X280生成エラー: {str(e)}",
                "worker": "X280"
            }
    
    def _generate_on_local(self, task_data):
        """ローカルで画像生成実行"""
        try:
            task_id = task_data["id"]
            prompt = task_data["prompt"]
            negative_prompt = task_data["negative_prompt"]
            model = task_data["model"]
            style = task_data["style"]
            size = task_data["size"]
            
            print(f"🏠 ローカルで画像生成開始: {task_id}")
            
            # ローカルで画像生成
            generator = ParallelMufufuGenerator(max_workers=1)
            results = generator.generate_mufufu_parallel_collection(1, [style])
            
            if results and results[0]["success"]:
                return {
                    "id": task_id,
                    "success": True,
                    "path": results[0]["path"],
                    "worker": "LOCAL",
                    "style": style,
                    "model": model,
                    "size": size
                }
            else:
                return {
                    "id": task_id,
                    "success": False,
                    "error": "ローカル生成失敗",
                    "worker": "LOCAL"
                }
                
        except Exception as e:
            return {
                "id": task_data["id"],
                "success": False,
                "error": f"ローカル生成エラー: {str(e)}",
                "worker": "LOCAL"
            }
        finally:
            if 'generator' in locals():
                generator.cleanup()  # type: ignore[possibly-unbound]
    
    def generate_distributed_collection(self, count=6, use_both=True):
        """分散画像コレクション生成"""
        print(f"🌐 分散画像生成開始！({count}枚)")
        print(f"   ローカル + X280分散処理")
        print("=" * 60)
        
        # X280環境セットアップ
        if self.x280_available and use_both:
            self._setup_x280_environment()
        
        # タスク準備
        tasks = []
        styles = ["clear_beautiful", "elegant_style", "cute_kawaii", "innocent_pure"]
        models = ["dreamshaper_8", "majicmixLux_v3", "majicmixRealistic_v7"]
        sizes = ["portrait", "square", "landscape"]
        
        for i in range(count):
            style = random.choice(styles)
            model = random.choice(models)
            size = random.choice(sizes)
            
            # ムフフプロンプト選択
            mufufu_prompts = {
                "clear_beautiful": [
                    "a beautiful clear girl, innocent expression, soft smile, high quality, detailed, anime style",
                    "cute girl with pure eyes, gentle smile, clear skin, beautiful hair, high quality, anime art"
                ],
                "elegant_style": [
                    "elegant beautiful woman, sophisticated style, graceful pose, high quality, detailed",
                    "refined beautiful girl, classy outfit, gentle expression, high quality, anime style"
                ],
                "cute_kawaii": [
                    "super cute kawaii girl, big eyes, adorable expression, soft colors, high quality",
                    "lovely cute girl, sweet smile, fluffy hair, pastel colors, high quality, anime style"
                ],
                "innocent_pure": [
                    "innocent pure girl, gentle expression, soft features, high quality, anime style",
                    "pure beautiful girl, innocent eyes, gentle smile, high quality, detailed art"
                ]
            }
            
            prompt = random.choice(mufufu_prompts[style])
            negative_prompt = "nsfw, nude, explicit, sexual, inappropriate, violence, blood, gore, scary, horror, bad quality, low resolution, blurry, distorted, ugly, deformed, bad anatomy"
            
            tasks.append({
                "id": i,
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "model": model,
                "style": style,
                "size": size
            })
        
        # 分散実行
        start_time = time.time()
        results = []
        
        if self.x280_available and use_both:
            # ローカル + X280分散処理
            print(f"🌐 ローカル + X280分散処理実行中...")
            
            # タスクを分散
            local_tasks = tasks[:count//2] if count > 2 else tasks[:1]
            x280_tasks = tasks[count//2:] if count > 2 else tasks[1:]
            
            # ローカル処理
            if local_tasks:
                print(f"🏠 ローカル処理: {len(local_tasks)}枚")
                with ThreadPoolExecutor(max_workers=self.max_local_workers) as executor:
                    local_futures = [executor.submit(self._generate_on_local, task) for task in local_tasks]
                    for future in as_completed(local_futures):
                        result = future.result()
                        results.append(result)
                        if result["success"]:
                            print(f"✅ ローカル完了: {result['id']} ({result['style']})")
                        else:
                            print(f"❌ ローカル失敗: {result['id']} ({result['error']})")
            
            # X280処理
            if x280_tasks:
                print(f"🚀 X280処理: {len(x280_tasks)}枚")
                with ThreadPoolExecutor(max_workers=2) as executor:  # X280は性能低いので2並列
                    x280_futures = [executor.submit(self._generate_on_x280, task) for task in x280_tasks]
                    for future in as_completed(x280_futures):
                        result = future.result()
                        results.append(result)
                        if result["success"]:
                            print(f"✅ X280完了: {result['id']} ({result['style']})")
                        else:
                            print(f"❌ X280失敗: {result['id']} ({result['error']})")
        else:
            # ローカルのみ処理
            print(f"🏠 ローカルのみ処理: {count}枚")
            with ThreadPoolExecutor(max_workers=self.max_local_workers) as executor:
                futures = [executor.submit(self._generate_on_local, task) for task in tasks]
                for future in as_completed(futures):
                    result = future.result()
                    results.append(result)
                    if result["success"]:
                        print(f"✅ ローカル完了: {result['id']} ({result['style']})")
                    else:
                        print(f"❌ ローカル失敗: {result['id']} ({result['error']})")
        
        total_time = time.time() - start_time
        success_count = sum(1 for r in results if r["success"])
        
        # ワーカー別統計
        local_success = sum(1 for r in results if r.get("worker") == "LOCAL" and r["success"])
        x280_success = sum(1 for r in results if r.get("worker") == "X280" and r["success"])
        
        print(f"\n🎉 分散画像生成完了！")
        print(f"   総時間: {total_time:.1f}秒")
        print(f"   成功: {success_count}/{count} 枚")
        print(f"   平均時間: {total_time/count:.1f}秒/枚")
        print(f"   分散効率: {success_count/total_time:.2f}枚/秒")
        print(f"   ローカル成功: {local_success}枚")
        print(f"   X280成功: {x280_success}枚")
        
        return results
    
    def benchmark_distributed_performance(self, test_counts=[3, 6, 9]):
        """分散処理パフォーマンスベンチマーク"""
        print(f"📊 分散画像生成パフォーマンスベンチマーク")
        print("=" * 60)
        
        results = []
        
        for count in test_counts:
            print(f"\n🧪 分散テスト {count}枚生成")
            
            # 分散処理テスト
            start_time = time.time()
            distributed_results = self.generate_distributed_collection(count, use_both=True)
            distributed_time = time.time() - start_time
            distributed_success = sum(1 for r in distributed_results if r["success"])
            
            # ローカルのみテスト
            start_time = time.time()
            local_results = self.generate_distributed_collection(count, use_both=False)
            local_time = time.time() - start_time
            local_success = sum(1 for r in local_results if r["success"])
            
            results.append({
                "count": count,
                "distributed_time": distributed_time,
                "distributed_success": distributed_success,
                "local_time": local_time,
                "local_success": local_success,
                "distributed_efficiency": distributed_success/distributed_time if distributed_time > 0 else 0,
                "local_efficiency": local_success/local_time if local_time > 0 else 0,
                "speedup": local_time/distributed_time if distributed_time > 0 else 0
            })
            
            print(f"   分散処理: {distributed_time:.1f}秒 ({distributed_success}枚成功)")
            print(f"   ローカルのみ: {local_time:.1f}秒 ({local_success}枚成功)")
            print(f"   高速化倍率: {results[-1]['speedup']:.2f}倍")
        
        # 結果サマリー
        print(f"\n📈 分散ベンチマーク結果サマリー")
        print("=" * 60)
        for result in results:
            print(f"   {result['count']}枚: 分散{result['distributed_efficiency']:.2f}枚/秒, ローカル{result['local_efficiency']:.2f}枚/秒, 高速化{result['speedup']:.2f}倍")
        
        return results
    
    def cleanup(self):
        """リソースクリーンアップ"""
        print("🧹 分散画像生成システムクリーンアップ完了")


def main():
    """メイン関数"""
    print("🌐 Distributed Image Generator")
    print("=" * 60)
    
    # 分散画像生成システム初期化
    generator = DistributedImageGenerator(use_x280=True, max_local_workers=4)
    
    try:
        # 分散処理テスト
        print("\n🌐 分散処理テスト")
        distributed_results = generator.generate_distributed_collection(count=6, use_both=True)
        
        # パフォーマンスベンチマーク
        print("\n📊 分散パフォーマンスベンチマーク")
        benchmark_results = generator.benchmark_distributed_performance([3, 6, 9])
        
        print(f"\n🎉 分散画像生成システム完了！")
        print(f"   ローカル + X280分散処理: 準備完了")
        print(f"   パフォーマンス: ベンチマーク完了")
        
    finally:
        # クリーンアップ
        generator.cleanup()


if __name__ == "__main__":
    main()
