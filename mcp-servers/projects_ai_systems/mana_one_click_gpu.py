#!/usr/bin/env python3
"""
Mana ワンクリック GPU操作システム
ターミナル操作なしでRunPod GPUを使う
"""

import subprocess

class ManaOneClickGPU:
    """Mana専用ワンクリックGPUシステム"""
    
    def __init__(self):
        self.ssh_host = "8uv33dh7cewgeq-644114e0@ssh.runpod.io"
        self.ssh_key = "/root/.ssh/id_ed25519_runpod_latest"
    
    def execute_gpu_command(self, command):
        """GPUコマンドを実行"""
        try:
            # SSHでコマンド実行
            ssh_cmd = [
                "ssh", "-o", "StrictHostKeyChecking=no",
                "-i", self.ssh_key,
                self.ssh_host,
                "-T",
                f"cd /workspace && {command}"
            ]
            
            result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=60)
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr
            }
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": str(e)
            }
    
    def generate_images(self):
        """画像生成実行"""
        print("🎨 Mana ワンクリック画像生成開始")
        print("=" * 50)
        
        # 画像生成コード
        image_code = '''
python3 -c "
import torch
import torch.nn as nn
import matplotlib.pyplot as plt
import numpy as np
import time

print('🎨 Mana SSH直接画像生成開始')
print('=' * 50)

device = torch.device('cuda')
print(f'使用デバイス: {device}')
print(f'GPU名: {torch.cuda.get_device_name(0)}')

class Generator(nn.Module):
    def __init__(self):
        super().__init__()
        self.main = nn.Sequential(
            nn.ConvTranspose2d(512, 1024, 4, 1, 0),
            nn.BatchNorm2d(1024),
            nn.ReLU(True),
            nn.ConvTranspose2d(1024, 512, 4, 2, 1),
            nn.BatchNorm2d(512),
            nn.ReLU(True),
            nn.ConvTranspose2d(512, 256, 4, 2, 1),
            nn.BatchNorm2d(256),
            nn.ReLU(True),
            nn.ConvTranspose2d(256, 128, 4, 2, 1),
            nn.BatchNorm2d(128),
            nn.ReLU(True),
            nn.ConvTranspose2d(128, 64, 4, 2, 1),
            nn.BatchNorm2d(64),
            nn.ReLU(True),
            nn.ConvTranspose2d(64, 3, 4, 2, 1),
            nn.Tanh()
        )
    def forward(self, noise):
        return self.main(noise)

generator = Generator().to(device)
print(f'パラメータ数: {sum(p.numel() for p in generator.parameters()):,}')

noise = torch.randn(4, 512, 1, 1).to(device)
start_time = time.time()
with torch.no_grad():
    generated_images = generator(noise)
torch.cuda.synchronize()
end_time = time.time()

print(f'生成時間: {end_time - start_time:.4f}秒')
print(f'画像サイズ: {generated_images.shape}')
print('✅ Mana SSH直接画像生成完了！')
"
'''
        
        result = self.execute_gpu_command(image_code)
        
        if result["success"]:
            print("✅ 画像生成成功！")
            print("📊 結果:")
            print("-" * 40)
            print(result["output"])
            print("-" * 40)
        else:
            print("❌ 画像生成失敗")
            print(f"エラー: {result['error']}")
        
        return result
    
    def run_deep_learning(self):
        """深層学習実行"""
        print("\n🧠 Mana ワンクリック深層学習開始")
        print("=" * 50)
        
        dl_code = '''
python3 -c "
import torch
import torch.nn as nn
import time

print('🧠 Mana SSH直接深層学習開始')
print('=' * 50)

device = torch.device('cuda')
print(f'使用デバイス: {device}')

class LargeNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(784, 2048),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(2048, 1024),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(1024, 512),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(512, 10)
        )
    def forward(self, x):
        return self.network(x)

model = LargeNN().to(device)
print(f'パラメータ数: {sum(p.numel() for p in model.parameters()):,}')

x = torch.randn(1000, 784).to(device)
y = torch.randint(0, 10, (1000,)).to(device)
criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

start_time = time.time()
for epoch in range(50):
    optimizer.zero_grad()
    outputs = model(x)
    loss = criterion(outputs, y)
    loss.backward()
    optimizer.step()

torch.cuda.synchronize()
end_time = time.time()

print(f'学習時間: {end_time - start_time:.4f}秒')
print(f'最終損失: {loss.item():.4f}')
print('✅ Mana SSH直接深層学習完了！')
"
'''
        
        result = self.execute_gpu_command(dl_code)
        
        if result["success"]:
            print("✅ 深層学習成功！")
            print("📊 結果:")
            print("-" * 40)
            print(result["output"])
            print("-" * 40)
        else:
            print("❌ 深層学習失敗")
            print(f"エラー: {result['error']}")
        
        return result
    
    def check_gpu_status(self):
        """GPU状態確認"""
        print("🔥 Mana GPU状態確認")
        print("=" * 50)
        
        result = self.execute_gpu_command("nvidia-smi --query-gpu=name,memory.total,memory.used,utilization.gpu --format=csv,noheader,nounits")
        
        if result["success"]:
            print("✅ GPU状態確認成功")
            print("📊 GPU情報:")
            print("-" * 40)
            print(result["output"])
            print("-" * 40)
        else:
            print("❌ GPU状態確認失敗")
            print(f"エラー: {result['error']}")
        
        return result

def main():
    """メイン実行"""
    print("🚀 Mana ワンクリックGPUシステム")
    print("=" * 60)
    
    gpu = ManaOneClickGPU()
    
    # GPU状態確認
    gpu.check_gpu_status()
    
    # 画像生成
    gpu.generate_images()
    
    # 深層学習
    gpu.run_deep_learning()
    
    print("\n" + "=" * 60)
    print("🎉 Mana ワンクリックGPU操作完了！")
    print("💡 ターミナル操作なしでRunPod GPUを使用しました！")
    print("=" * 60)

if __name__ == "__main__":
    main()
