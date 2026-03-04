#!/usr/bin/env python3
"""
⚡ ManaOS TURBO Enhancer
Phase 1強化を一気に適用

強化内容:
1. CPU負荷分散最適化
2. プロセスプール最適化
3. 非同期処理高速化
4. メモリ効率化
"""

import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor
import psutil
import os
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

CPU_CORES = mp.cpu_count()

# =============================================================================
# CPU負荷分散最適化
# =============================================================================

def optimize_cpu_affinity():
    """プロセスCPUアフィニティ最適化"""
    current_process = psutil.Process()
    
    # 全CPUコアを使用可能に設定
    try:
        current_process.cpu_affinity(list(range(CPU_CORES)))
        return {
            "success": True,
            "cpu_cores": CPU_CORES,
            "affinity": list(range(CPU_CORES)),
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }

def set_process_priority(priority="normal"):
    """プロセス優先度設定"""
    current_process = psutil.Process()
    
    priority_map = {
        "low": psutil.BELOW_NORMAL_PRIORITY_CLASS if os.name == 'nt' else 10,
        "normal": psutil.NORMAL_PRIORITY_CLASS if os.name == 'nt' else 0,
        "high": psutil.ABOVE_NORMAL_PRIORITY_CLASS if os.name == 'nt' else -10,
    }
    
    try:
        if os.name == 'nt':
            current_process.nice(priority_map.get(priority, priority_map["normal"]))
        else:
            current_process.nice(priority_map.get(priority, priority_map["normal"]))
        
        return {
            "success": True,
            "priority": priority,
            "nice_value": current_process.nice(),
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }

# =============================================================================
# プロセスプール最適化
# =============================================================================

class OptimizedProcessPool:
    """最適化されたプロセスプール"""
    
    def __init__(self, max_workers=None):
        self.max_workers = max_workers or CPU_CORES
        self.executor = ProcessPoolExecutor(max_workers=self.max_workers)
    
    def submit(self, func, *args, **kwargs):
        """タスク投入"""
        return self.executor.submit(func, *args, **kwargs)
    
    def map(self, func, *iterables):
        """マップ実行"""
        return self.executor.map(func, *iterables)
    
    def shutdown(self):
        """シャットダウン"""
        self.executor.shutdown(wait=True)

# グローバルプロセスプール
_process_pool = None

def get_process_pool():
    """プロセスプール取得"""
    global _process_pool
    if _process_pool is None:
        _process_pool = OptimizedProcessPool(max_workers=CPU_CORES)
    return _process_pool

# =============================================================================
# メモリ効率化
# =============================================================================

def optimize_memory():
    """メモリ最適化"""
    import gc
    
    # ガベージコレクション実行
    gc.collect()
    
    memory_info = psutil.virtual_memory()
    
    return {
        "success": True,
        "total_gb": round(memory_info.total / (1024**3), 2),
        "available_gb": round(memory_info.available / (1024**3), 2),
        "percent": memory_info.percent,
        "gc_collected": True,
    }

# =============================================================================
# 負荷分散計算デモ
# =============================================================================

def heavy_task(x):
    """CPUヘビーなタスク"""
    import os
    
    # プロセスID取得
    pid = os.getpid()
    
    # CPU割り当て確認
    cpu_affinity = psutil.Process(pid).cpu_affinity() if hasattr(psutil.Process(pid), 'cpu_affinity') else None
    
    # 計算実行
    result = sum(i * i for i in range(x))
    
    return {
        "pid": pid,
        "cpu_affinity": cpu_affinity,
        "input": x,
        "result": result % 1000000,  # 結果を小さく
    }

async def run_balanced_computation(num_tasks=8, task_size=5000000):
    """負荷分散計算実行"""
    import time
    
    pool = get_process_pool()
    
    start_time = time.time()
    
    # 全CPUコアに均等にタスク分散
    tasks = [task_size] * num_tasks
    
    # 並列実行
    results = list(pool.map(heavy_task, tasks))
    
    elapsed_time = time.time() - start_time
    
    # PIDごとの実行回数をカウント
    pid_counts = {}
    for r in results:
        pid = r["pid"]
        pid_counts[pid] = pid_counts.get(pid, 0) + 1
    
    return {
        "success": True,
        "num_tasks": num_tasks,
        "elapsed_seconds": round(elapsed_time, 4),
        "tasks_per_second": round(num_tasks / elapsed_time, 2),
        "results": results,
        "pid_distribution": pid_counts,
        "num_processes_used": len(pid_counts),
    }

# =============================================================================
# システム最適化
# =============================================================================

def apply_all_optimizations():
    """全最適化を適用"""
    results = {
        "cpu_affinity": optimize_cpu_affinity(),
        "process_priority": set_process_priority("normal"),
        "memory": optimize_memory(),
    }
    
    return results

# =============================================================================
# REST API
# =============================================================================

@app.route('/')
def index():
    """システム情報"""
    return jsonify({
        "system": "ManaOS TURBO Enhancer",
        "version": "1.0.0",
        "cpu_cores": CPU_CORES,
        "optimizations": [
            "CPU負荷分散",
            "プロセスプール最適化",
            "メモリ効率化",
        ],
    })

@app.route('/optimize', methods=['POST'])
def optimize():
    """全最適化適用"""
    results = apply_all_optimizations()
    return jsonify({
        "success": True,
        "optimizations": results,
    })

@app.route('/test/balanced-computation', methods=['POST'])
async def test_balanced_computation():
    """負荷分散計算テスト"""
    result = await run_balanced_computation()
    return jsonify(result)

@app.route('/status')
def status():
    """システムステータス"""
    cpu_percent = psutil.cpu_percent(interval=0.1, percpu=True)
    memory = psutil.virtual_memory()
    
    return jsonify({
        "cpu": {
            "cores": CPU_CORES,
            "usage_per_core": cpu_percent,
            "average": round(sum(cpu_percent) / len(cpu_percent), 2),
            "max": round(max(cpu_percent), 2),
        },
        "memory": {
            "total_gb": round(memory.total / (1024**3), 2),
            "used_gb": round(memory.used / (1024**3), 2),
            "available_gb": round(memory.available / (1024**3), 2),
            "percent": memory.percent,
        },
    })

@app.route('/health')
def health():
    """ヘルスチェック"""
    return jsonify({
        "status": "healthy",
    })

# =============================================================================
# メイン
# =============================================================================

if __name__ == '__main__':
    print("=" * 80)
    print("⚡ ManaOS TURBO Enhancer 起動中...")
    print("=" * 80)
    print(f"💪 CPU Cores: {CPU_CORES}")
    print("=" * 80)
    print("\n📍 エンドポイント:")
    print("  - http://localhost:5025/              - システム情報")
    print("  - http://localhost:5025/optimize      - 全最適化適用")
    print("  - http://localhost:5025/test/balanced-computation - 負荷分散テスト")
    print("  - http://localhost:5025/status        - システムステータス")
    print("=" * 80)
    print()
    
    # 起動時に最適化適用
    print("🚀 起動時最適化を適用中...")
    opt_results = apply_all_optimizations()
    print(f"✅ CPU Affinity: {opt_results['cpu_affinity']['success']}")
    print(f"✅ Process Priority: {opt_results['process_priority']['success']}")
    print(f"✅ Memory Optimization: {opt_results['memory']['success']}")
    print()
    
    app.run(
        host='0.0.0.0',
        port=5025,
        debug=os.getenv("DEBUG", "False").lower() == "true",
    )

