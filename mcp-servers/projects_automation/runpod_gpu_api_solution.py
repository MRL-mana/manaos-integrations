#!/usr/bin/env python3
"""
RunPod GPU API解決策
SSH接続でのCUDA初期化問題を回避するためのAPIサーバー
"""

import subprocess
import os
from flask import Flask, request, jsonify

app = Flask(__name__)

class RunPodGPUManager:
    def __init__(self):
        self.runpod_host = "213.181.111.2"
        self.runpod_port = "26156"
        self.ssh_key = "/root/.ssh/id_ed25519_runpod_latest"
        
    def execute_ssh_command(self, command):
        """SSH経由でコマンドを実行"""
        try:
            cmd = [
                'ssh', '-i', self.ssh_key,
                f'root@{self.runpod_host}', '-p', self.runpod_port,
                command
            ]
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=60
            )
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr,
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": "",
                "error": "Command timeout",
                "returncode": -1
            }
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": str(e),
                "returncode": -1
            }
    
    def check_gpu_status(self):
        """GPU状態確認"""
        result = self.execute_ssh_command("nvidia-smi --query-gpu=name,memory.total,memory.used,temperature.gpu,utilization.gpu --format=csv,noheader")
        return result
    
    def run_gpu_task(self, task_type="image_generation"):
        """GPUタスクを実行"""
        if task_type == "image_generation":
            # Web Terminalで実行されるGPUタスクをSSH経由で実行
            command = '''
            cd /workspace && python3 -c "
            import torch
            import torch.nn as nn
            import matplotlib.pyplot as plt
            import numpy as np
            
            print('🚀 GPU画像生成開始')
            device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            print(f'デバイス: {device}')
            
            if torch.cuda.is_available():
                # 簡単な画像生成テスト
                x = torch.randn(1, 3, 64, 64).to(device)
                y = torch.nn.functional.relu(x)
                print(f'GPU処理成功: {y.shape}')
                
                # 画像保存
                img = y[0].cpu().permute(1, 2, 0).numpy()
                img = (img - img.min()) / (img.max() - img.min())
                plt.imsave('/workspace/ssh_gpu_test.png', img)
                print('✅ 画像保存完了: /workspace/ssh_gpu_test.png')
            else:
                print('❌ CUDA利用不可')
            "
            '''
        else:
            command = "echo 'Unknown task type'"
        
        return self.execute_ssh_command(command)

# グローバルインスタンス
gpu_manager = RunPodGPUManager()

@app.route('/')
def index():
    return jsonify({
        "status": "running",
        "message": "RunPod GPU API Server",
        "version": "1.0",
        "endpoints": {
            "/gpu/status": "GET - GPU状態確認",
            "/gpu/task": "POST - GPUタスク実行",
            "/ssh/test": "GET - SSH接続テスト"
        }
    })

@app.route('/gpu/status')
def gpu_status():
    """GPU状態確認"""
    result = gpu_manager.check_gpu_status()
    return jsonify(result)

@app.route('/gpu/task', methods=['POST'])
def run_gpu_task():
    """GPUタスク実行"""
    data = request.get_json() or {}
    task_type = data.get('task_type', 'image_generation')
    
    result = gpu_manager.run_gpu_task(task_type)
    return jsonify(result)

@app.route('/ssh/test')
def ssh_test():
    """SSH接続テスト"""
    result = gpu_manager.execute_ssh_command("echo 'SSH接続成功' && hostname")
    return jsonify(result)

@app.route('/gpu/web-terminal-command', methods=['POST'])
def web_terminal_command():
    """Web Terminalで実行すべきコマンドを提供"""
    data = request.get_json() or {}
    command_type = data.get('type', 'gpu_test')
    
    commands = {
        'gpu_test': '''
# GPU動作テスト
cd /workspace
python3 -c "
import torch
print('PyTorch:', torch.__version__)
print('CUDA:', torch.cuda.is_available())
if torch.cuda.is_available():
    print('GPU:', torch.cuda.get_device_name(0))
    x = torch.randn(1000, 1000).cuda()
    y = torch.mm(x, x.t())
    print('GPU計算成功:', y.shape)
"
        ''',
        'image_generation': '''
# 画像生成テスト
cd /workspace
python3 -c "
import torch
import torch.nn as nn
import matplotlib.pyplot as plt
import numpy as np

device = torch.device('cuda')
print('デバイス:', device)

# 簡単な画像生成
generator = nn.Sequential(
    nn.ConvTranspose2d(100, 64, 4, 1, 0),
    nn.ReLU(),
    nn.ConvTranspose2d(64, 3, 4, 2, 1),
    nn.Tanh()
).to(device)

noise = torch.randn(1, 100, 1, 1).to(device)
img = generator(noise)[0].cpu().permute(1, 2, 0).numpy()
img = (img + 1) / 2

plt.imsave('/workspace/web_terminal_gpu_test.png', img)
print('画像保存完了: /workspace/web_terminal_gpu_test.png')
"
        '''
    }
    
    return jsonify({
        "success": True,
        "command": commands.get(command_type, "echo 'Unknown command type'"),
        "message": "Web Terminalで実行してください"
    })

if __name__ == '__main__':
    print("🚀 RunPod GPU API Server起動中...")
    print("📡 エンドポイント:")
    print("  - http://localhost:5000/gpu/status")
    print("  - http://localhost:5000/gpu/task")
    print("  - http://localhost:5000/ssh/test")
    print("  - http://localhost:5000/gpu/web-terminal-command")
    
    app.run(host="0.0.0.0", port=port, debug=os.getenv("DEBUG", "False").lower() == "true")
