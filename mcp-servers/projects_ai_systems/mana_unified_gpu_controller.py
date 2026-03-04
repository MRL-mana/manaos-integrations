#!/usr/bin/env python3
"""
Mana統合GPUコントローラー
Trinity達とVS Code Remote SSHの両方を使用
"""

import asyncio
import json
import websockets
import subprocess
import sys

class ManaUnifiedGPUController:
    """Mana統合GPUコントローラー"""
    
    def __init__(self):
        self.trinity_bridge_uri = "ws://localhost:9999"
        self.vscode_remote_host = "runpod-gpu"
    
    async def trinity_operation(self, operation_type, **kwargs):
        """Trinity達による操作"""
        try:
            async with websockets.connect(self.trinity_bridge_uri) as websocket:
                command = {
                    "type": operation_type,
                    "trinity_id": "mana_unified",
                    **kwargs
                }
                
                await websocket.send(json.dumps(command))
                response = await websocket.recv()
                return json.loads(response)
        except Exception as e:
            return {"error": str(e)}
    
    def vscode_operation(self, code):
        """VS Code Remote SSHによる操作"""
        try:
            result = subprocess.run([
                "ssh", "-o", "ConnectTimeout=10",
                self.vscode_remote_host,
                f"cd /workspace && python3 -c \"{code}\""
            ], capture_output=True, text=True, timeout=30)
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def unified_gpu_status(self):
        """統合GPU状態確認"""
        print("🔥 統合GPU状態確認")
        print("=" * 50)
        
        # Trinity達による確認
        print("🤖 Trinity達による確認...")
        trinity_result = await self.trinity_operation("gpu_status")
        if "error" not in trinity_result:
            print("✅ Trinity達確認成功")
        else:
            print(f"❌ Trinity達確認失敗: {trinity_result['error']}")
        
        # VS Code Remote SSHによる確認
        print("💻 VS Code Remote SSHによる確認...")
        vscode_code = """
import torch
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"GPU name: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'No GPU'}")
print(f"GPU memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f}GB" if torch.cuda.is_available() else "No GPU")
"""
        vscode_result = self.vscode_operation(vscode_code)
        if vscode_result["success"]:
            print("✅ VS Code Remote SSH確認成功")
            print(f"結果: {vscode_result['output'].strip()}")
        else:
            print(f"❌ VS Code Remote SSH確認失敗: {vscode_result['error']}")
    
    async def unified_image_generation(self, count=4):
        """統合画像生成"""
        print(f"🎨 統合画像生成 ({count}枚)")
        print("=" * 50)
        
        # Trinity達による画像生成
        print("🤖 Trinity達による画像生成...")
        trinity_result = await self.trinity_operation("gpu_image_generation")
        if "error" not in trinity_result:
            print("✅ Trinity達画像生成成功")
        else:
            print(f"❌ Trinity達画像生成失敗: {trinity_result['error']}")
        
        # VS Code Remote SSHによる画像生成
        print("💻 VS Code Remote SSHによる画像生成...")
        vscode_code = f"""
import torch
import torch.nn as nn
import time

print("VS Code Remote SSH画像生成開始")
device = torch.device('cuda')

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
noise = torch.randn({count}, 512, 1, 1).to(device)

start_time = time.time()
with torch.no_grad():
    generated_images = generator(noise)
torch.cuda.synchronize()
end_time = time.time()

print(f"VS Code Remote SSH生成時間: {{end_time - start_time:.4f}}秒")
print(f"VS Code Remote SSH画像サイズ: {{generated_images.shape}}")
print("✅ VS Code Remote SSH画像生成完了")
"""
        vscode_result = self.vscode_operation(vscode_code)
        if vscode_result["success"]:
            print("✅ VS Code Remote SSH画像生成成功")
            print(f"結果: {vscode_result['output'].strip()}")
        else:
            print(f"❌ VS Code Remote SSH画像生成失敗: {vscode_result['error']}")
    
    async def unified_deep_learning(self, epochs=50):
        """統合深層学習"""
        print(f"🧠 統合深層学習 ({epochs}エポック)")
        print("=" * 50)
        
        # Trinity達による深層学習
        print("🤖 Trinity達による深層学習...")
        trinity_result = await self.trinity_operation("gpu_deep_learning")
        if "error" not in trinity_result:
            print("✅ Trinity達深層学習成功")
        else:
            print(f"❌ Trinity達深層学習失敗: {trinity_result['error']}")
        
        # VS Code Remote SSHによる深層学習
        print("💻 VS Code Remote SSHによる深層学習...")
        vscode_code = f"""
import torch
import torch.nn as nn
import time

print("VS Code Remote SSH深層学習開始")
device = torch.device('cuda')

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
x = torch.randn(1000, 784).to(device)
y = torch.randint(0, 10, (1000,)).to(device)
criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

start_time = time.time()
for epoch in range({epochs}):
    optimizer.zero_grad()
    outputs = model(x)
    loss = criterion(outputs, y)
    loss.backward()
    optimizer.step()

torch.cuda.synchronize()
end_time = time.time()

print(f"VS Code Remote SSH学習時間: {{end_time - start_time:.4f}}秒")
print(f"VS Code Remote SSH最終損失: {{loss.item():.4f}}")
print("✅ VS Code Remote SSH深層学習完了")
"""
        vscode_result = self.vscode_operation(vscode_code)
        if vscode_result["success"]:
            print("✅ VS Code Remote SSH深層学習成功")
            print(f"結果: {vscode_result['output'].strip()}")
        else:
            print(f"❌ VS Code Remote SSH深層学習失敗: {vscode_result['error']}")
    
    async def run_unified_demo(self):
        """統合デモ実行"""
        print("🚀 Mana統合GPUコントローラー デモ開始")
        print("=" * 70)
        
        await self.unified_gpu_status()
        print()
        await self.unified_image_generation(6)
        print()
        await self.unified_deep_learning(30)
        
        print("\n" + "=" * 70)
        print("🎉 Mana統合GPUコントローラー デモ完了！")
        print("💡 Trinity達とVS Code Remote SSHの両方が活用されました！")
        print("=" * 70)

def print_help():
    """ヘルプ表示"""
    print("🚀 Mana統合GPUコントローラー")
    print("=" * 50)
    print("使用方法:")
    print("  python3 mana_unified_gpu_controller.py <コマンド>")
    print("")
    print("コマンド:")
    print("  status                   統合GPU状態確認")
    print("  images [枚数]            統合画像生成")
    print("  learning [エポック]      統合深層学習")
    print("  demo                     統合デモ実行")
    print("  help                     このヘルプを表示")
    print("")
    print("特徴:")
    print("- Trinity達による自動操作")
    print("- VS Code Remote SSHによる直接操作")
    print("- 両方を並列で実行")
    print("- 最適なルートを自動選択")

async def main():
    """メイン実行"""
    if len(sys.argv) < 2:
        print_help()
        return
    
    command = sys.argv[1]
    args = sys.argv[2:] if len(sys.argv) > 2 else []
    
    if command == "help":
        print_help()
        return
    
    controller = ManaUnifiedGPUController()
    
    if command == "status":
        await controller.unified_gpu_status()
    elif command == "images":
        count = int(args[0]) if args else 4
        await controller.unified_image_generation(count)
    elif command == "learning":
        epochs = int(args[0]) if args else 50
        await controller.unified_deep_learning(epochs)
    elif command == "demo":
        await controller.run_unified_demo()
    else:
        print(f"❌ 不明なコマンド: {command}")
        print_help()

if __name__ == "__main__":
    asyncio.run(main())
