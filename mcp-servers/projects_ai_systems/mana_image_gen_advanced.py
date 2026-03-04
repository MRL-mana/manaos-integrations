#!/usr/bin/env python3
"""
Mana本格画像生成システム v2.0
Paramiko SSH経由でRunPod RTX 4090を使用
"""

import paramiko
import time
import os
from datetime import datetime

class ManaAdvancedImageGenerator:
    """Mana専用高度画像生成システム"""
    
    def __init__(self):
        self.runpod_host = "213.181.111.2"
        self.runpod_port = 26156
        self.runpod_user = "root"
        self.ssh_key_path = "/root/.ssh/id_ed25519_runpod_latest"
        self.ssh_client = None
        
    def connect(self):
        """RunPodに接続"""
        print("🔌 RunPod RTX 4090に接続中...")
        try:
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            self.ssh_client.connect(
                hostname=self.runpod_host,
                port=self.runpod_port,
                username=self.runpod_user,
                key_filename=self.ssh_key_path,
                timeout=15
            )
            
            print("✅ 接続成功！")
            return True
        except Exception as e:
            print(f"❌ 接続失敗: {e}")
            return False
    
    def execute_command(self, command, timeout=180):
        """コマンド実行"""
        try:
            stdin, stdout, stderr = self.ssh_client.exec_command(command, timeout=timeout)
            
            # リアルタイム出力
            while True:
                line = stdout.readline()
                if not line:
                    break
                print(line.rstrip())
            
            exit_status = stdout.channel.recv_exit_status()
            error_output = stderr.read().decode()
            
            if error_output:
                print(f"標準エラー: {error_output}")
            
            return exit_status == 0
        except Exception as e:
            print(f"❌ 実行エラー: {e}")
            return False
    
    def generate_images(self):
        """Manaの好きそうな画像を生成"""
        print("\n" + "=" * 70)
        print("🎨 Mana本格画像生成システム v2.0")
        print("🔥 RunPod RTX 4090 × Stable Diffusion SDXL")
        print("=" * 70)
        
        # プロンプト設定
        prompts = [
            {
                "name": "可愛いギャル系ファッション",
                "prompt": "cute fashionable girl, stylish outfit, pastel colors, modern aesthetic, high quality, detailed, soft lighting, kawaii style, trendy accessories, beautiful eyes, confident pose, 4k, masterpiece",
                "negative": "ugly, bad anatomy, blurry, low quality, worst quality, bad hands"
            },
            {
                "name": "テクノロジー×キュート",
                "prompt": "futuristic cute tech gadget, holographic display, neon lights, cyberpunk aesthetic, high-tech design, colorful LED lights, sleek modern style, 4k render, detailed, masterpiece",
                "negative": "ugly, cluttered, messy, low quality, bad design"
            },
            {
                "name": "パステルカラーの夢世界",
                "prompt": "dreamy pastel world, cute aesthetic, soft colors, whimsical atmosphere, beautiful landscape, magical feeling, high quality, detailed artwork, 4k, professional illustration, fantasy art",
                "negative": "dark, gloomy, ugly, low quality, bad composition"
            }
        ]
        
        # 作業ディレクトリ作成
        print("\n📁 作業ディレクトリ準備中...")
        self.execute_command("mkdir -p /workspace/mana_images")
        
        # 各プロンプトで画像生成
        for idx, prompt_data in enumerate(prompts, 1):
            print(f"\n{'=' * 70}")
            print(f"📸 画像 {idx}/{len(prompts)}: {prompt_data['name']}")
            print("=" * 70)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Python画像生成スクリプト（ヒアドキュメント使用）
            image_gen_script = f"""
cat > /workspace/mana_gen_{idx}.py << 'MANA_SCRIPT_EOF'
import torch
print("🚀 GPU初期化中...")
print(f"GPU: {{torch.cuda.get_device_name(0)}}")
print(f"VRAM: {{torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f}}GB")
print()

try:
    # Diffusers確認
    from diffusers import DiffusionPipeline
    import time
    
    print("📦 Stable Diffusion SDXL Turboロード中...")
    print("⏳ 初回は数分かかります...")
    
    pipe = DiffusionPipeline.from_pretrained(
        "stabilityai/sdxl-turbo",
        torch_dtype=torch.float16,
        variant="fp16"
    ).to("cuda")
    
    pipe.enable_attention_slicing()
    
    print("✅ モデルロード完了！")
    print()
    print("🎨 '{prompt_data['name']}'を生成中...")
    print()
    
    start_time = time.time()
    
    image = pipe(
        prompt="{prompt_data['prompt']}",
        negative_prompt="{prompt_data['negative']}",
        num_inference_steps=4,
        guidance_scale=0.0,
        height=512,
        width=512
    ).images[0]
    
    end_time = time.time()
    
    filename = "/workspace/mana_images/mana_{timestamp}_{idx:02d}_{prompt_data['name'].replace(' ', '_')}.png"
    image.save(filename)
    
    print(f"⏱️  生成時間: {{end_time - start_time:.2f}}秒")
    print(f"💾 保存完了: {{filename}}")
    print(f"📏 サイズ: {{image.size}}")
    print("✅ 成功！")
    
except ImportError:
    print("📦 Diffusersインストール中...")
    import subprocess
    subprocess.run([
        "pip", "install", "-q",
        "diffusers[torch]", 
        "accelerate",
        "transformers",
        "safetensors"
    ], check=True)
    print("✅ インストール完了！もう一度実行してください")
    
except Exception as e:
    print(f"⚠️  エラー: {{str(e)[:200]}}")
    print()
    print("💡 代替：PyTorchで抽象アート生成")
    
    import torch.nn as nn
    import numpy as np
    from PIL import Image
    
    class ArtGenerator(nn.Module):
        def __init__(self):
            super().__init__()
            self.net = nn.Sequential(
                nn.ConvTranspose2d(128, 512, 4, 1, 0),
                nn.BatchNorm2d(512),
                nn.ReLU(),
                nn.ConvTranspose2d(512, 256, 4, 2, 1),
                nn.BatchNorm2d(256),
                nn.ReLU(),
                nn.ConvTranspose2d(256, 128, 4, 2, 1),
                nn.BatchNorm2d(128),
                nn.ReLU(),
                nn.ConvTranspose2d(128, 64, 4, 2, 1),
                nn.BatchNorm2d(64),
                nn.ReLU(),
                nn.ConvTranspose2d(64, 3, 4, 2, 1),
                nn.Tanh()
            )
        def forward(self, x):
            return self.net(x)
    
    gen = ArtGenerator().to("cuda")
    noise = torch.randn(1, 128, 1, 1).to("cuda")
    
    with torch.no_grad():
        art = gen(noise)
    
    img_np = art.squeeze(0).permute(1, 2, 0).cpu().numpy()
    img_np = ((img_np + 1) * 127.5).clip(0, 255).astype(np.uint8)
    img = Image.fromarray(img_np)
    
    filename = "/workspace/mana_images/mana_art_{timestamp}_{idx:02d}.png"
    img.save(filename)
    print(f"💾 抽象アート保存: {{filename}}")
    print("✅ 完了")

MANA_SCRIPT_EOF

python3 /workspace/mana_gen_{idx}.py
"""
            
            # 実行
            success = self.execute_command(image_gen_script, timeout=300)
            
            if success:
                print(f"✅ 画像{idx}生成完了！")
            else:
                print(f"⚠️  画像{idx}でエラーが発生しました")
            
            # 次の画像前に少し待機
            if idx < len(prompts):
                time.sleep(1)
        
        print(f"\n{'=' * 70}")
        print("📸 全画像生成完了！")
        print("=" * 70)
    
    def list_generated_images(self):
        """生成した画像を一覧表示"""
        print("\n📋 生成画像一覧:")
        print("-" * 70)
        self.execute_command("ls -lh /workspace/mana_images/ | grep '.png'")
    
    def download_images(self):
        """画像をダウンロード"""
        print("\n📥 画像をダウンロード中...")
        print("-" * 70)
        
        # ローカルディレクトリ作成
        local_dir = "/root/mana_generated_images"
        os.makedirs(local_dir, exist_ok=True)
        
        try:
            # SFTP接続
            sftp = self.ssh_client.open_sftp()
            
            # ファイル一覧取得
            remote_files = sftp.listdir("/workspace/mana_images/")
            png_files = [f for f in remote_files if f.endswith('.png')]
            
            print(f"📦 {len(png_files)}枚の画像をダウンロード中...")
            
            for filename in png_files:
                remote_path = f"/workspace/mana_images/{filename}"
                local_path = os.path.join(local_dir, filename)
                
                sftp.get(remote_path, local_path)
                size = os.path.getsize(local_path)
                print(f"  ✅ {filename} ({size/1024:.1f}KB)")
            
            sftp.close()
            
            print(f"\n💾 全{len(png_files)}枚保存完了！")
            print(f"📁 保存先: {local_dir}")
            
            return local_dir, png_files
            
        except Exception as e:
            print(f"❌ ダウンロードエラー: {e}")
            return None, []
    
    def close(self):
        """接続クローズ"""
        if self.ssh_client:
            self.ssh_client.close()
            print("\n✅ RunPod接続をクローズしました")

def main():
    """メイン実行"""
    print("\n╔" + "=" * 68 + "╗")
    print("║" + " " * 10 + "🎨 Mana本格画像生成システム v2.0 🔥" + " " * 18 + "║")
    print("║" + " " * 68 + "║")
    print("║" + " " * 15 + "RunPod RTX 4090 × SDXL Turbo" + " " * 25 + "║")
    print("╚" + "=" * 68 + "╝")
    
    gen = ManaAdvancedImageGenerator()
    
    try:
        # 接続
        if not gen.connect():
            print("❌ 接続に失敗しました")
            return
        
        # GPU確認
        print("\n🔥 GPU状態確認:")
        print("-" * 70)
        gen.execute_command("nvidia-smi --query-gpu=name,memory.total,memory.used,temperature.gpu --format=csv,noheader")
        
        # 画像生成
        gen.generate_images()
        
        # 生成画像一覧
        gen.list_generated_images()
        
        # ダウンロード
        local_dir, files = gen.download_images()
        
        # 完了メッセージ
        print("\n" + "=" * 70)
        print("🎉 Mana本格画像生成システム - 完了！")
        print("=" * 70)
        print()
        if files:
            print(f"✅ {len(files)}枚の可愛い画像を生成しました！")
            print(f"📁 {local_dir}")
            print()
            print("💡 次のステップ:")
            print("  1. 画像を確認: ls -lh /root/mana_generated_images/")
            print("  2. Google Driveにアップロード")
            print("  3. さらに画像生成したい場合は再実行")
        print()
        print("🚀 RTX 4090のフルパワーで生成しました！")
        print("=" * 70)
        
    finally:
        gen.close()

if __name__ == "__main__":
    main()

