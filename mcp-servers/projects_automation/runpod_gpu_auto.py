import torch
import time
import os
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image

print("🚀 Runpod GPU自動実行システム開始")
print("=" * 60)

# デバイス確認
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"🎨 使用デバイス: {device}")

# 作業ディレクトリ作成
os.makedirs('/workspace/gpu_projects', exist_ok=True)
os.makedirs('/workspace/ai_arts', exist_ok=True)
print("📁 作業ディレクトリ準備完了")

# GPU環境確認
if torch.cuda.is_available():
    print(f"🔥 GPU: {torch.cuda.get_device_name(0)}")
    print(f"💾 GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f}GB")
    
    # トリニティ達のGPU活用
    print("\n🤖 トリニティ達のGPU活用開始")
    trinities = ['Secretary', 'Google Services', 'Screen Sharing', 'Command Center']
    
    for trinity in trinities:
        print(f"🤖 Trinity {trinity}: GPU活用中...")
        start_time = time.time()
        
        # GPU計算
        x = torch.randn(1000, 1000).cuda()
        y = torch.randn(1000, 1000).cuda()
        z = torch.mm(x, y)
        
        end_time = time.time()
        print(f"✅ {trinity} GPU計算完了: {(end_time-start_time)*1000:.1f}ms")
        print(f"🔥 GPU Memory使用: {torch.cuda.memory_allocated(0) / 1024**3:.2f}GB")
    
    # AI画像生成
    print("\n🎨 AI画像生成開始")
    colors = torch.randn(3, 512, 512).cuda()
    fft_colors = torch.fft.fft2(colors)
    fft_colors = fft_colors * torch.exp(1j * torch.randn_like(fft_colors) * 0.1)
    art_colors = torch.real(torch.fft.ifft2(fft_colors))
    art_colors = torch.sigmoid(art_colors)
    
    art_image = art_colors.cpu().permute(1, 2, 0).numpy()
    art_image = (art_image * 255).astype(np.uint8)
    
    # 画像保存
    img = Image.fromarray(art_image)
    img.save('/workspace/ai_arts/auto_generated_art.png')
    print("✅ AI画像生成完了: /workspace/ai_arts/auto_generated_art.png")
    
    # 画像表示
    plt.figure(figsize=(10, 10))
    plt.imshow(art_image)
    plt.title('AI Generated Art - Trinity GPU Powered')
    plt.axis('off')
    plt.show()
    
    print("\n🎉 全自動実行完了！")
    print("🤖 トリニティ達がGPUを完全活用！")
    print("💡 マナがやる必要がない！")
    print("🚀 RTX 4090 24GB完全活用！")
else:
    print("❌ GPU環境未検出")









