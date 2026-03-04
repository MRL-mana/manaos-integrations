#!/usr/bin/env python3
"""
🚀 GPU並行ブーストモード - 複数タスク同時実行テスト
"""
import requests
import concurrent.futures
import time
from datetime import datetime

TRINITY_API = "http://localhost:5009"

def gpu_task(task_name, endpoint, method='GET'):
    """GPU タスク実行"""
    start = time.time()
    try:
        if method == 'POST':
            response = requests.post(f"{TRINITY_API}{endpoint}", timeout=60)
        else:
            response = requests.get(f"{TRINITY_API}{endpoint}", timeout=60)
        
        elapsed = time.time() - start
        result = response.json()
        return {
            'task': task_name,
            'success': True,
            'elapsed': f'{elapsed:.2f}秒',
            'result': result
        }
    except Exception as e:
        elapsed = time.time() - start
        return {
            'task': task_name,
            'success': False,
            'elapsed': f'{elapsed:.2f}秒',
            'error': str(e)
        }

def parallel_boost_test():
    """並行ブーストテスト"""
    print("🚀 GPU並行ブーストモード開始...")
    print(f"⏰ 開始時刻: {datetime.now().strftime('%H:%M:%S')}\n")
    
    # 並行実行するタスク
    tasks = [
        ("GPU状態取得-1", "/trinity/gpu/status", "GET"),
        ("画像生成-1", "/trinity/gpu/generate", "POST"),
        ("深層学習-1", "/trinity/gpu/learn", "POST"),
        ("GPU状態取得-2", "/trinity/gpu/status", "GET"),
        ("画像生成-2", "/trinity/gpu/generate", "POST"),
        ("深層学習-2", "/trinity/gpu/learn", "POST"),
    ]
    
    # 並行実行
    start_time = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(gpu_task, task[0], task[1], task[2]) for task in tasks]
        results = [future.result() for future in concurrent.futures.as_completed(futures)]
    
    total_time = time.time() - start_time
    
    # 結果表示
    print("=" * 70)
    print("📊 GPU並行ブーストモード 実行結果")
    print("=" * 70)
    
    for i, result in enumerate(results, 1):
        status = "✅" if result['success'] else "❌"
        print(f"\n{status} タスク{i}: {result['task']}")
        print(f"   ⏱️  実行時間: {result['elapsed']}")
        if result['success'] and 'result' in result:
            if 'result' in result['result']:
                r = result['result']['result']
                if 'images_generated' in r:
                    print(f"   🎨 画像生成: {r['images_generated']}枚")
                elif 'training_time' in r:
                    print(f"   🧠 学習時間: {r['training_time']}")
            elif 'gpu_info' in result['result']:
                print(f"   🎮 GPU: {result['result']['gpu_info']['name']}")
    
    print("\n" + "=" * 70)
    print(f"🎯 総実行時間: {total_time:.2f}秒")
    print(f"⚡ 並行効率: {len(tasks)}タスク同時実行")
    print("=" * 70)

if __name__ == "__main__":
    parallel_boost_test()
