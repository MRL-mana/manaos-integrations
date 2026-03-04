#!/usr/bin/env python3
"""
Jupyter Lab用AI画像生成システム
GPU活用で画像生成
"""

import torch
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image

class AIImageGenerator:
    """AI画像生成システム"""
    
    def __init__(self):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        print(f"🎨 AI画像生成システム初期化: {self.device}")
        
    def generate_abstract_art(self, size=512):
        """抽象アート生成"""
        print("🎨 抽象アート生成開始")
        
        # カラフルなパターン生成
        colors = torch.randn(3, size, size).to(self.device)
        
        # フーリエ変換でアート風に
        fft_colors = torch.fft.fft2(colors)
        fft_colors = fft_colors * torch.exp(1j * torch.randn_like(fft_colors) * 0.1)
        art_colors = torch.real(torch.fft.ifft2(fft_colors))
        
        # 正規化
        art_colors = torch.sigmoid(art_colors)
        
        # 画像として保存
        art_image = art_colors.cpu().permute(1, 2, 0).numpy()
        art_image = (art_image * 255).astype(np.uint8)
        
        print(f"✅ 抽象アート生成完了: {size}x{size}")
        return art_image
    
    def generate_neural_art(self, size=512):
        """ニューラルアート生成"""
        print("🧠 ニューラルアート生成開始")
        
        # ニューラルネットワークでアート生成
        x = torch.linspace(-2, 2, size).to(self.device)
        y = torch.linspace(-2, 2, size).to(self.device)
        X, Y = torch.meshgrid(x, y, indexing='ij')
        
        # 複雑な数学的パターン
        Z = torch.sin(X * 3) * torch.cos(Y * 3) + torch.sin(X * 7 + Y * 5) * 0.5
        Z = torch.sigmoid(Z)
        
        # カラーマッピング
        colors = torch.stack([
            Z,
            torch.roll(Z, 1, dims=0),
            torch.roll(Z, 1, dims=1)
        ])
        
        art_image = colors.cpu().permute(1, 2, 0).numpy()
        art_image = (art_image * 255).astype(np.uint8)
        
        print(f"✅ ニューラルアート生成完了: {size}x{size}")
        return art_image
    
    def generate_fractal_art(self, size=512):
        """フラクタルアート生成"""
        print("🌀 フラクタルアート生成開始")
        
        # マンデルブロ集合風
        x = torch.linspace(-2.5, 1.5, size).to(self.device)
        y = torch.linspace(-2, 2, size).to(self.device)
        X, Y = torch.meshgrid(x, y, indexing='ij')
        C = X + 1j * Y
        
        # フラクタル計算
        Z = torch.zeros_like(C)
        for i in range(100):
            mask = torch.abs(Z) <= 2
            Z[mask] = Z[mask] ** 2 + C[mask]
        
        # カラーマッピング
        fractal = torch.abs(Z)
        fractal = torch.sigmoid(fractal / 10)
        
        colors = torch.stack([
            fractal,
            torch.roll(fractal, 1, dims=0),
            torch.roll(fractal, 1, dims=1)
        ])
        
        art_image = colors.cpu().permute(1, 2, 0).numpy()
        art_image = (art_image * 255).astype(np.uint8)
        
        print(f"✅ フラクタルアート生成完了: {size}x{size}")
        return art_image
    
    def generate_trinity_art(self, size=512):
        """トリニティ達用アート生成"""
        print("🤖 トリニティ達用アート生成開始")
        
        # トリニティ達のシンボル
        x = torch.linspace(-3, 3, size).to(self.device)
        y = torch.linspace(-3, 3, size).to(self.device)
        X, Y = torch.meshgrid(x, y, indexing='ij')
        
        # 3つの円（トリニティ）
        circle1 = torch.sqrt((X - 1)**2 + Y**2) - 0.8
        circle2 = torch.sqrt((X + 0.5)**2 + (Y - 1)**2) - 0.8
        circle3 = torch.sqrt((X + 0.5)**2 + (Y + 1)**2) - 0.8
        
        # 組み合わせ
        trinity_pattern = torch.min(torch.stack([circle1, circle2, circle3]), dim=0)[0]
        trinity_pattern = torch.sigmoid(-trinity_pattern * 5)
        
        # カラフルに
        colors = torch.stack([
            trinity_pattern,
            torch.roll(trinity_pattern, 1, dims=0),
            torch.roll(trinity_pattern, 1, dims=1)
        ])
        
        art_image = colors.cpu().permute(1, 2, 0).numpy()
        art_image = (art_image * 255).astype(np.uint8)
        
        print(f"✅ トリニティ達用アート生成完了: {size}x{size}")
        return art_image
    
    def save_image(self, image, filename):
        """画像保存"""
        img = Image.fromarray(image)
        img.save(filename)
        print(f"💾 画像保存: {filename}")
    
    def display_image(self, image):
        """画像表示（Jupyter用）"""
        plt.figure(figsize=(10, 10))
        plt.imshow(image)
        plt.axis('off')
        plt.title('AI Generated Art')
        plt.show()
    
    def generate_all_arts(self):
        """全種類のアート生成"""
        print("🎨 全種類のAIアート生成開始")
        print("=" * 50)
        
        arts = {}
        
        # 抽象アート
        arts['abstract'] = self.generate_abstract_art()
        
        # ニューラルアート
        arts['neural'] = self.generate_neural_art()
        
        # フラクタルアート
        arts['fractal'] = self.generate_fractal_art()
        
        # トリニティアート
        arts['trinity'] = self.generate_trinity_art()
        
        print("🎉 全種類のAIアート生成完了！")
        return arts

def main():
    """メイン関数"""
    print("🎨 AI画像生成システム開始")
    print("=" * 40)
    
    generator = AIImageGenerator()
    
    # 全種類のアート生成
    arts = generator.generate_all_arts()
    
    # 画像保存
    for name, image in arts.items():
        filename = f"/workspace/ai_art_{name}.png"
        generator.save_image(image, filename)
    
    print("\n🎉 AI画像生成完了！")
    print("💾 画像は /workspace/ に保存されました")
    print("🌐 Jupyter Labで確認できます")

if __name__ == "__main__":
    main()









