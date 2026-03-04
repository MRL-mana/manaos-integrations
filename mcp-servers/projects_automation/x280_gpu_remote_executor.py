#!/usr/bin/env python3
"""
🎮 X280 GPU Remote Executor
X280のGPUをリモートから完全活用

機能:
- X280のGPU状態リアルタイム監視
- GPU計算タスクのリモート実行
- PyTorch/TensorFlow対応
- 画像生成・機械学習タスク実行
"""

import os
import subprocess
import time
from datetime import datetime
from typing import Dict, Any, List
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

X280_HOST = "100.127.121.20"  # X280 Tailscale IP

# =============================================================================
# SSH経由コマンド実行
# =============================================================================

def run_ssh_command(command: str, timeout: int = 30) -> Dict[str, Any]:
    """X280でSSH経由コマンド実行"""
    try:
        result = subprocess.run(
            ["ssh", X280_HOST, command],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr,
            "return_code": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": f"Timeout after {timeout} seconds",
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }

# =============================================================================
# GPU情報取得
# =============================================================================

def get_gpu_info() -> Dict[str, Any]:
    """X280のGPU詳細情報取得"""
    # nvidia-smiで詳細情報取得
    result = run_ssh_command(
        "nvidia-smi --query-gpu=name,memory.total,memory.used,memory.free,"
        "utilization.gpu,utilization.memory,temperature.gpu,power.draw "
        "--format=csv,noheader,nounits"
    )
    
    if not result["success"]:
        return {"available": False, "error": result.get("error")}
    
    try:
        parts = result["output"].strip().split(',')
        return {
            "available": True,
            "name": parts[0].strip(),
            "memory": {
                "total_mb": int(parts[1].strip()),
                "used_mb": int(parts[2].strip()),
                "free_mb": int(parts[3].strip()),
                "usage_percent": round(int(parts[2].strip()) / int(parts[1].strip()) * 100, 1),
            },
            "utilization": {
                "gpu_percent": int(parts[4].strip()),
                "memory_percent": int(parts[5].strip()),
            },
            "temperature_celsius": int(parts[6].strip()),
            "power_draw_watts": float(parts[7].strip()),
        }
    except Exception as e:
        return {"available": False, "error": f"Parse error: {str(e)}", "raw": result["output"]}

def get_gpu_processes() -> List[Dict[str, Any]]:
    """X280のGPU使用プロセス一覧"""
    result = run_ssh_command(
        "nvidia-smi --query-compute-apps=pid,process_name,used_memory "
        "--format=csv,noheader,nounits"
    )
    
    if not result["success"] or not result["output"].strip():
        return []
    
    processes = []
    for line in result["output"].strip().split('\n'):
        parts = line.split(',')
        if len(parts) >= 3:
            processes.append({
                "pid": parts[0].strip(),
                "name": parts[1].strip(),
                "memory_mb": int(parts[2].strip()),
            })
    
    return processes

# =============================================================================
# GPU計算タスク実行
# =============================================================================

def execute_python_on_gpu(code: str, timeout: int = 300) -> Dict[str, Any]:
    """X280のGPUでPythonコード実行"""
    # 一時ファイル作成＆実行
    timestamp = int(time.time())
    temp_file = f"C:/Users/mana/temp_gpu_task_{timestamp}.py"
    
    # ファイル作成
    create_cmd = f'echo {code} > {temp_file}'
    result = run_ssh_command(create_cmd)
    
    if not result["success"]:
        return {"success": False, "error": "Failed to create temp file"}
    
    # Python実行
    exec_cmd = f"python {temp_file}"
    exec_result = run_ssh_command(exec_cmd, timeout=timeout)
    
    # クリーンアップ
    run_ssh_command(f"del {temp_file}")
    
    return {
        "success": exec_result["success"],
        "output": exec_result["output"],
        "error": exec_result["error"],
    }

def run_pytorch_test() -> Dict[str, Any]:
    """PyTorchGPUテスト実行"""
    code = """
import torch
print('PyTorch Version:', torch.__version__)
print('CUDA Available:', torch.cuda.is_available())
if torch.cuda.is_available():
    print('CUDA Device:', torch.cuda.get_device_name(0))
    print('CUDA Memory:', torch.cuda.get_device_properties(0).total_memory / 1e9, 'GB')
    x = torch.rand(5, 5).cuda()
    print('Test Tensor:', x)
"""
    return execute_python_on_gpu(code.replace('\n', ' && '))

# =============================================================================
# REST API
# =============================================================================

@app.route('/')
def index():
    """API情報"""
    return jsonify({
        "service": "X280 GPU Remote Executor",
        "version": "1.0.0",
        "x280_host": X280_HOST,
        "timestamp": datetime.now().isoformat(),
    })

@app.route('/gpu/info')
def gpu_info():
    """GPU情報取得"""
    info = get_gpu_info()
    return jsonify({
        "timestamp": datetime.now().isoformat(),
        "gpu": info,
    })

@app.route('/gpu/processes')
def gpu_processes():
    """GPU使用プロセス一覧"""
    processes = get_gpu_processes()
    return jsonify({
        "timestamp": datetime.now().isoformat(),
        "processes": processes,
        "count": len(processes),
    })

@app.route('/gpu/status')
def gpu_status():
    """GPU総合ステータス"""
    info = get_gpu_info()
    processes = get_gpu_processes()
    
    return jsonify({
        "timestamp": datetime.now().isoformat(),
        "gpu": info,
        "processes": processes,
        "summary": {
            "available": info.get("available", False),
            "memory_free_mb": info.get("memory", {}).get("free_mb", 0),
            "gpu_usage_percent": info.get("utilization", {}).get("gpu_percent", 0),
            "active_processes": len(processes),
        }
    })

@app.route('/gpu/execute', methods=['POST'])
def gpu_execute():
    """GPUでコマンド実行"""
    data = request.get_json()
    command = data.get('command', '')
    timeout = data.get('timeout', 30)
    
    if not command:
        return jsonify({"success": False, "error": "No command provided"}), 400
    
    result = run_ssh_command(command, timeout=timeout)
    
    return jsonify({
        "timestamp": datetime.now().isoformat(),
        "command": command,
        "result": result,
    })

@app.route('/gpu/python', methods=['POST'])
def gpu_python():
    """GPUでPythonコード実行"""
    data = request.get_json()
    code = data.get('code', '')
    timeout = data.get('timeout', 300)
    
    if not code:
        return jsonify({"success": False, "error": "No code provided"}), 400
    
    result = execute_python_on_gpu(code, timeout=timeout)
    
    return jsonify({
        "timestamp": datetime.now().isoformat(),
        "result": result,
    })

@app.route('/gpu/pytorch-test')
def pytorch_test():
    """PyTorch GPU テスト"""
    result = run_pytorch_test()
    
    return jsonify({
        "timestamp": datetime.now().isoformat(),
        "test": "PyTorch GPU",
        "result": result,
    })

@app.route('/health')
def health():
    """ヘルスチェック"""
    gpu_available = get_gpu_info().get("available", False)
    
    return jsonify({
        "status": "healthy" if gpu_available else "degraded",
        "x280_reachable": True,
        "gpu_available": gpu_available,
        "timestamp": datetime.now().isoformat(),
    })

# =============================================================================
# メイン
# =============================================================================

if __name__ == '__main__':
    print("=" * 80)
    print("🎮 X280 GPU Remote Executor 起動中...")
    print("=" * 80)
    print(f"🖥️  X280 Host: {X280_HOST}")
    print("🌐 API Port: 5022")
    print("=" * 80)
    print("\n📍 エンドポイント:")
    print("  - http://localhost:5022/              - API情報")
    print("  - http://localhost:5022/gpu/info      - GPU詳細情報")
    print("  - http://localhost:5022/gpu/status    - GPU総合ステータス")
    print("  - http://localhost:5022/gpu/processes - GPU使用プロセス")
    print("  - http://localhost:5022/gpu/pytorch-test - PyTorchテスト")
    print("=" * 80)
    print()
    
    app.run(
        host='0.0.0.0',
        port=5022,
        debug=os.getenv("DEBUG", "False").lower() == "true",
    )

