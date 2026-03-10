#!/usr/bin/env python3
"""
Trinity Image Generator
Canva風・Adobe風の画像生成システム
"""

import os
import json
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from datetime import datetime
import random
from pathlib import Path

class TrinityImageGenerator:
    def __init__(self):
        self.output_dir = Path("/root/mana-workspace/outputs/images")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # カラーパレット
        self.color_palettes = {
            "vibrant": ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7"],
            "pastel": ["#FFB3BA", "#FFDFBA", "#FFFFBA", "#BAFFC9", "#BAE1FF"],
            "monochrome": ["#2C3E50", "#34495E", "#7F8C8D", "#BDC3C7", "#ECF0F1"],
            "sunset": ["#FF9A9E", "#FECFEF", "#FECFEF", "#FFD3A5", "#FD9853"],
            "ocean": ["#667eea", "#764ba2", "#f093fb", "#f5576c", "#4facfe"]
        }
        
        # フォント設定
        self.fonts = {
            "title": "arial.ttf",
            "body": "arial.ttf",
            "decorative": "arial.ttf"
        }
    
    def create_canva_style_poster(self, title, subtitle, theme="vibrant"):
        """Canva風ポスター作成"""
        width, height = 1080, 1350  # Instagram Post size
        
        # 背景作成
        bg_color = self.color_palettes[theme][0]
        image = Image.new('RGB', (width, height), bg_color)
        draw = ImageDraw.Draw(image)
        
        # グラデーション効果
        for i in range(height):
            alpha = i / height
            color = tuple(int(c * (1 - alpha * 0.3)) for c in Image.new('RGB', (1, 1), bg_color).getpixel((0, 0)))  # type: ignore[misc]
            draw.line([(0, i), (width, i)], fill=color)
        
        # 装飾的な図形
        for i in range(5):
            x = random.randint(0, width)
            y = random.randint(0, height)
            size = random.randint(50, 200)
            color = self.color_palettes[theme][random.randint(1, 4)]
            
            # 円形の装飾
            draw.ellipse([x-size//2, y-size//2, x+size//2, y+size//2], 
                        fill=color, outline=None)
        
        # テキスト追加
        try:
            title_font = ImageFont.truetype(self.fonts["title"], 80)
            subtitle_font = ImageFont.truetype(self.fonts["body"], 40)
        except:
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()
        
        # タイトル
        title_bbox = draw.textbbox((0, 0), title, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        title_x = (width - title_width) // 2
        title_y = height // 3
        
        # テキストシャドウ
        draw.text((title_x + 3, title_y + 3), title, font=title_font, fill=(0, 0, 0, 100))
        draw.text((title_x, title_y), title, font=title_font, fill=(255, 255, 255))
        
        # サブタイトル
        subtitle_bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
        subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
        subtitle_x = (width - subtitle_width) // 2
        subtitle_y = title_y + 120
        
        draw.text((subtitle_x, subtitle_y), subtitle, font=subtitle_font, fill=(255, 255, 255, 200))
        
        # 保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"canva_poster_{timestamp}.png"
        filepath = self.output_dir / filename
        image.save(filepath)
        
        return str(filepath)
    
    def create_infographic(self, data, title="Infographic"):
        """インフォグラフィック作成"""
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # データ可視化
        if isinstance(data, dict):
            categories = list(data.keys())
            values = list(data.values())
            
            # カラーマップ
            colors = plt.cm.Set3(np.linspace(0, 1, len(categories)))
            
            # 円グラフ
            wedges, texts, autotexts = ax.pie(values, labels=categories, colors=colors, 
                                             autopct='%1.1f%%', startangle=90)
            
            # スタイル調整
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')
        
        ax.set_title(title, fontsize=20, fontweight='bold', pad=20)
        
        # 背景色設定
        fig.patch.set_facecolor('#f0f0f0')
        ax.set_facecolor('white')
        
        # 保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"infographic_{timestamp}.png"
        filepath = self.output_dir / filename
        plt.savefig(filepath, dpi=300, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        plt.close()
        
        return str(filepath)
    
    def create_social_media_post(self, text, style="modern"):
        """ソーシャルメディア投稿用画像"""
        width, height = 1080, 1080  # Square format
        
        # スタイル別設定
        styles = {
            "modern": {"bg": "#2C3E50", "text": "#ECF0F1", "accent": "#3498DB"},
            "minimal": {"bg": "#FFFFFF", "text": "#2C3E50", "accent": "#E74C3C"},
            "vibrant": {"bg": "#FF6B6B", "text": "#FFFFFF", "accent": "#4ECDC4"},
            "nature": {"bg": "#27AE60", "text": "#FFFFFF", "accent": "#F39C12"}
        }
        
        colors = styles.get(style, styles["modern"])
        
        # 画像作成
        image = Image.new('RGB', (width, height), colors["bg"])
        draw = ImageDraw.Draw(image)
        
        # 装飾的な要素
        if style == "modern":
            # 幾何学的な装飾
            for i in range(3):
                x = random.randint(100, width-100)
                y = random.randint(100, height-100)
                size = random.randint(50, 150)
                draw.rectangle([x-size//2, y-size//2, x+size//2, y+size//2], 
                              outline=colors["accent"], width=3)
        
        # テキスト追加
        try:
            font = ImageFont.truetype(self.fonts["title"], 60)
        except:
            font = ImageFont.load_default()
        
        # テキストを複数行に分割
        words = text.split()
        lines = []
        current_line = ""
        
        for word in words:
            test_line = current_line + " " + word if current_line else word
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if bbox[2] - bbox[0] < width - 100:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        
        if current_line:
            lines.append(current_line)
        
        # テキスト描画
        total_height = len(lines) * 80
        start_y = (height - total_height) // 2
        
        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=font)
            line_width = bbox[2] - bbox[0]
            x = (width - line_width) // 2
            y = start_y + i * 80
            
            # テキストシャドウ
            draw.text((x + 2, y + 2), line, font=font, fill=(0, 0, 0, 100))
            draw.text((x, y), line, font=font, fill=colors["text"])
        
        # 保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"social_post_{style}_{timestamp}.png"
        filepath = self.output_dir / filename
        image.save(filepath)
        
        return str(filepath)
    
    def create_chart(self, data, chart_type="bar", title="Chart"):
        """チャート作成"""
        plt.style.use('seaborn-v0_8')
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        if chart_type == "bar":
            ax.bar(data.keys(), data.values(), color='#3498DB', alpha=0.8)
        elif chart_type == "line":
            ax.plot(data.keys(), data.values(), marker='o', linewidth=3, markersize=8)
        elif chart_type == "scatter":
            ax.scatter(data.keys(), data.values(), s=100, alpha=0.7, color='#E74C3C')
        
        ax.set_title(title, fontsize=16, fontweight='bold')
        ax.grid(True, alpha=0.3)
        
        # 保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"chart_{chart_type}_{timestamp}.png"
        filepath = self.output_dir / filename
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        return str(filepath)
    
    def create_logo(self, text, style="modern"):
        """ロゴ作成"""
        width, height = 400, 400
        
        # スタイル別設定
        styles = {
            "modern": {"bg": "#2C3E50", "text": "#ECF0F1", "accent": "#3498DB"},
            "minimal": {"bg": "#FFFFFF", "text": "#2C3E50", "accent": "#E74C3C"},
            "vibrant": {"bg": "#FF6B6B", "text": "#FFFFFF", "accent": "#4ECDC4"}
        }
        
        colors = styles.get(style, styles["modern"])
        
        # 画像作成
        image = Image.new('RGB', (width, height), colors["bg"])
        draw = ImageDraw.Draw(image)
        
        # 装飾的な要素
        if style == "modern":
            # 円形の装飾
            draw.ellipse([50, 50, 350, 350], outline=colors["accent"], width=5)
        
        # テキスト追加
        try:
            font = ImageFont.truetype(self.fonts["title"], 60)
        except:
            font = ImageFont.load_default()
        
        # テキスト中央配置
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (width - text_width) // 2
        y = (height - text_height) // 2
        
        draw.text((x, y), text, font=font, fill=colors["text"])
        
        # 保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"logo_{style}_{timestamp}.png"
        filepath = self.output_dir / filename
        image.save(filepath)
        
        return str(filepath)


def main():
    """メイン関数"""
    generator = TrinityImageGenerator()
    
    print("🎨 Trinity Image Generator 起動")
    print("=" * 50)
    
    # サンプル画像生成
    print("📊 サンプル画像を生成中...")
    
    # 1. Canva風ポスター
    poster_path = generator.create_canva_style_poster(
        "Trinity System", 
        "AI-Powered Automation Platform",
        "vibrant"
    )
    print(f"✅ ポスター作成完了: {poster_path}")
    
    # 2. インフォグラフィック
    data = {"Python": 40, "JavaScript": 25, "Go": 20, "Rust": 15}
    infographic_path = generator.create_infographic(data, "Programming Languages Usage")
    print(f"✅ インフォグラフィック作成完了: {infographic_path}")
    
    # 3. ソーシャルメディア投稿
    social_path = generator.create_social_media_post(
        "Trinity System\nAI-Powered Automation\nfor Modern Development",
        "modern"
    )
    print(f"✅ ソーシャルメディア投稿作成完了: {social_path}")
    
    # 4. チャート
    chart_data = {"Jan": 100, "Feb": 120, "Mar": 110, "Apr": 140, "May": 160}
    chart_path = generator.create_chart(chart_data, "line", "Monthly Performance")
    print(f"✅ チャート作成完了: {chart_path}")
    
    # 5. ロゴ
    logo_path = generator.create_logo("Trinity", "modern")
    print(f"✅ ロゴ作成完了: {logo_path}")
    
    print("\n🎉 すべての画像生成完了！")
    print(f"📁 出力ディレクトリ: {generator.output_dir}")


if __name__ == "__main__":
    main()


