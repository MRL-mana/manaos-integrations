#!/usr/bin/env python3
"""
RunPod ハイブリッド解決策
SSH接続とWeb Terminalを組み合わせた最適化されたGPU操作システム
"""

import subprocess

class RunPodHybridManager:
    def __init__(self):
        self.runpod_host = "213.181.111.2"
        self.runpod_port = "26156"
        self.ssh_key = "/root/.ssh/id_ed25519_runpod_latest"
        self.web_terminal_url = "https://213.181.111.2:3000"  # Web Terminal URL
        
    def ssh_command(self, command, timeout=60):
        """SSH経由でコマンド実行（ファイル操作、設定確認用）"""
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
                timeout=timeout
            )
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr,
                "method": "SSH"
            }
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": str(e),
                "method": "SSH"
            }
    
    def check_gpu_status(self):
        """GPU状態確認（SSH経由）"""
        return self.ssh_command("nvidia-smi --query-gpu=name,memory.total,memory.used,temperature.gpu,utilization.gpu --format=csv,noheader")
    
    def create_gpu_script(self, script_content, filename):
        """GPU処理スクリプトを作成（SSH経由）"""
        # スクリプトをエスケープしてSSH経由で作成
        escaped_content = script_content.replace('"', '\\"').replace('\n', '\\n')
        command = f'echo "{escaped_content}" > /workspace/{filename}'
        return self.ssh_command(command)
    
    def execute_gpu_script(self, filename):
        """GPU処理スクリプトを実行（Web Terminal用）"""
        # Web Terminalで実行すべきコマンドを提供
        return {
            "success": True,
            "method": "Web Terminal",
            "command": f"cd /workspace && python3 {filename}",
            "message": "Web Terminalで実行してください"
        }
    
    def get_web_terminal_commands(self):
        """Web Terminalで実行すべきコマンド一覧"""
        return {
            "gpu_test": {
                "description": "GPU動作テスト",
                "command": """cd /workspace && python3 -c "
import torch
print('PyTorch:', torch.__version__)
print('CUDA:', torch.cuda.is_available())
if torch.cuda.is_available():
    print('GPU:', torch.cuda.get_device_name(0))
    x = torch.randn(1000, 1000).cuda()
    y = torch.mm(x, x.t())
    print('GPU計算成功:', y.shape)
" """
            },
            "image_generation": {
                "description": "画像生成テスト",
                "command": """cd /workspace && python3 -c "
import torch
import torch.nn as nn
import matplotlib.pyplot as plt
import numpy as np

device = torch.device('cuda')
print('デバイス:', device)

generator = nn.Sequential(
    nn.ConvTranspose2d(100, 64, 4, 1, 0),
    nn.ReLU(),
    nn.ConvTranspose2d(64, 3, 4, 2, 1),
    nn.Tanh()
).to(device)

noise = torch.randn(1, 100, 1, 1).to(device)
with torch.no_grad():
    img = generator(noise)[0].cpu().permute(1, 2, 0).numpy()

img = (img + 1) / 2
plt.imsave('/workspace/hybrid_gpu_test.png', img)
print('画像保存完了: /workspace/hybrid_gpu_test.png')
" """
            },
            "deep_learning": {
                "description": "深層学習テスト",
                "command": """cd /workspace && python3 -c "
import torch
import torch.nn as nn
import time

device = torch.device('cuda')
print('デバイス:', device)

model = nn.Sequential(
    nn.Linear(784, 2048),
    nn.ReLU(),
    nn.Linear(2048, 1024),
    nn.ReLU(),
    nn.Linear(1024, 512),
    nn.ReLU(),
    nn.Linear(512, 10)
).to(device)

print('パラメータ数:', sum(p.numel() for p in model.parameters()))

batch_size = 1000
x = torch.randn(batch_size, 784).to(device)
y = torch.randint(0, 10, (batch_size,)).to(device)

criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

print('学習開始...')
start_time = time.time()
for epoch in range(100):
    optimizer.zero_grad()
    outputs = model(x)
    loss = criterion(outputs, y)
    loss.backward()
    optimizer.step()
    
    if epoch % 20 == 0:
        print(f'Epoch {epoch}, Loss: {loss.item():.4f}')

torch.cuda.synchronize()
end_time = time.time()
print(f'学習時間: {end_time - start_time:.4f}秒')
print('✅ 深層学習完了！')
" """
            }
        }
    
    def list_files(self):
        """ワークスペースのファイル一覧（SSH経由）"""
        return self.ssh_command("ls -la /workspace/")
    
    def download_file(self, remote_path, local_path):
        """ファイルダウンロード（SSH経由）"""
        try:
            cmd = [
                'scp', '-i', self.ssh_key,
                f'root@{self.runpod_host}:{remote_path}',
                local_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr,
                "method": "SCP"
            }
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": str(e),
                "method": "SCP"
            }

def main():
    """メイン実行関数"""
    manager = RunPodHybridManager()
    
    print("🚀 RunPod ハイブリッドGPU管理システム")
    print("=" * 50)
    
    # GPU状態確認
    print("1. GPU状態確認...")
    gpu_status = manager.check_gpu_status()
    if gpu_status["success"]:
        print("✅ GPU状態確認成功")
        print(gpu_status["output"])
    else:
        print("❌ GPU状態確認失敗")
        print(gpu_status["error"])
    
    print("\n" + "=" * 50)
    
    # Web Terminalコマンド一覧
    print("2. Web Terminalで実行可能なGPUコマンド:")
    commands = manager.get_web_terminal_commands()
    for key, cmd in commands.items():
        print(f"\n📋 {cmd['description']}:")
        print(f"   {cmd['command']}")
    
    print("\n" + "=" * 50)
    
    # ファイル一覧
    print("3. ワークスペースファイル一覧:")
    files = manager.list_files()
    if files["success"]:
        print(files["output"])
    else:
        print("❌ ファイル一覧取得失敗")

if __name__ == "__main__":
    main()
