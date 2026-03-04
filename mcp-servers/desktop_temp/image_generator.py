"""
画像生成ツール
様々な種類の画像を生成できます
"""

from PIL import Image, ImageDraw, ImageFont
import os
from datetime import datetime

def generate_solid_color_image(width=800, height=600, color=(255, 255, 255), filename=None):
    """
    単色の画像を生成
    
    Args:
        width: 画像の幅
        height: 画像の高さ
        color: RGB色 (R, G, B)
        filename: 保存するファイル名（Noneの場合は自動生成）
    """
    img = Image.new('RGB', (width, height), color)
    
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"solid_color_{timestamp}.png"
    
    img.save(filename)
    print(f"画像を保存しました: {filename}")
    return filename

def generate_gradient_image(width=800, height=600, start_color=(255, 0, 0), end_color=(0, 0, 255), direction='horizontal', filename=None):
    """
    グラデーション画像を生成
    
    Args:
        width: 画像の幅
        height: 画像の高さ
        start_color: 開始色 (R, G, B)
        end_color: 終了色 (R, G, B)
        direction: 'horizontal' または 'vertical'
        filename: 保存するファイル名
    """
    img = Image.new('RGB', (width, height))
    draw = ImageDraw.Draw(img)
    
    if direction == 'horizontal':
        for x in range(width):
            ratio = x / width
            r = int(start_color[0] * (1 - ratio) + end_color[0] * ratio)
            g = int(start_color[1] * (1 - ratio) + end_color[1] * ratio)
            b = int(start_color[2] * (1 - ratio) + end_color[2] * ratio)
            draw.line([(x, 0), (x, height)], fill=(r, g, b))
    else:  # vertical
        for y in range(height):
            ratio = y / height
            r = int(start_color[0] * (1 - ratio) + end_color[0] * ratio)
            g = int(start_color[1] * (1 - ratio) + end_color[1] * ratio)
            b = int(start_color[2] * (1 - ratio) + end_color[2] * ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b))
    
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"gradient_{timestamp}.png"
    
    img.save(filename)
    print(f"グラデーション画像を保存しました: {filename}")
    return filename

def generate_text_image(text, width=800, height=600, bg_color=(255, 255, 255), text_color=(0, 0, 0), font_size=60, filename=None):
    """
    テキストを含む画像を生成
    
    Args:
        text: 表示するテキスト
        width: 画像の幅
        height: 画像の高さ
        bg_color: 背景色
        text_color: テキスト色
        font_size: フォントサイズ
        filename: 保存するファイル名
    """
    img = Image.new('RGB', (width, height), bg_color)
    draw = ImageDraw.Draw(img)
    
    # フォントの読み込み（利用可能な場合）
    try:
        # Windowsの場合
        font = ImageFont.truetype("C:/Windows/Fonts/msgothic.ttc", font_size)
    except:
        try:
            # 代替フォント
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            # デフォルトフォント
            font = ImageFont.load_default()
    
    # テキストの中央配置
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    position = ((width - text_width) // 2, (height - text_height) // 2)
    
    draw.text(position, text, fill=text_color, font=font)
    
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"text_image_{timestamp}.png"
    
    img.save(filename)
    print(f"テキスト画像を保存しました: {filename}")
    return filename

def generate_pattern_image(width=800, height=600, pattern='checkerboard', color1=(255, 255, 255), color2=(0, 0, 0), tile_size=50, filename=None):
    """
    パターン画像を生成
    
    Args:
        width: 画像の幅
        height: 画像の高さ
        pattern: 'checkerboard'（チェッカー）または 'stripes'（縞模様）
        color1: 色1
        color2: 色2
        tile_size: タイルサイズ
        filename: 保存するファイル名
    """
    img = Image.new('RGB', (width, height))
    draw = ImageDraw.Draw(img)
    
    if pattern == 'checkerboard':
        for y in range(0, height, tile_size):
            for x in range(0, width, tile_size):
                if (x // tile_size + y // tile_size) % 2 == 0:
                    draw.rectangle([x, y, x + tile_size, y + tile_size], fill=color1)
                else:
                    draw.rectangle([x, y, x + tile_size, y + tile_size], fill=color2)
    elif pattern == 'stripes':
        for x in range(0, width, tile_size * 2):
            draw.rectangle([x, 0, x + tile_size, height], fill=color1)
            draw.rectangle([x + tile_size, 0, x + tile_size * 2, height], fill=color2)
    
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"pattern_{pattern}_{timestamp}.png"
    
    img.save(filename)
    print(f"パターン画像を保存しました: {filename}")
    return filename

def generate_circle_image(width=800, height=600, bg_color=(255, 255, 255), circle_color=(255, 0, 0), radius=100, filename=None):
    """
    円形の画像を生成
    
    Args:
        width: 画像の幅
        height: 画像の高さ
        bg_color: 背景色
        circle_color: 円の色
        radius: 円の半径
        filename: 保存するファイル名
    """
    img = Image.new('RGB', (width, height), bg_color)
    draw = ImageDraw.Draw(img)
    
    center_x = width // 2
    center_y = height // 2
    
    draw.ellipse(
        [center_x - radius, center_y - radius, center_x + radius, center_y + radius],
        fill=circle_color
    )
    
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"circle_{timestamp}.png"
    
    img.save(filename)
    print(f"円形画像を保存しました: {filename}")
    return filename

def main():
    """メイン関数 - サンプル画像を生成"""
    print("=" * 50)
    print("画像生成ツール")
    print("=" * 50)
    
    # 出力ディレクトリを作成
    output_dir = "generated_images"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    print("\n1. 単色画像を生成中...")
    generate_solid_color_image(
        width=800, 
        height=600, 
        color=(100, 150, 200),
        filename=os.path.join(output_dir, "solid_blue.png")
    )
    
    print("\n2. グラデーション画像を生成中...")
    generate_gradient_image(
        width=800,
        height=600,
        start_color=(255, 100, 100),
        end_color=(100, 100, 255),
        direction='horizontal',
        filename=os.path.join(output_dir, "gradient_horizontal.png")
    )
    
    print("\n3. テキスト画像を生成中...")
    generate_text_image(
        text="こんにちは！\n画像生成ツール",
        width=800,
        height=600,
        bg_color=(240, 240, 240),
        text_color=(50, 50, 50),
        font_size=60,
        filename=os.path.join(output_dir, "text_hello.png")
    )
    
    print("\n4. チェッカーパターン画像を生成中...")
    generate_pattern_image(
        width=800,
        height=600,
        pattern='checkerboard',
        color1=(255, 255, 255),
        color2=(100, 100, 100),
        tile_size=50,
        filename=os.path.join(output_dir, "checkerboard.png")
    )
    
    print("\n5. 円形画像を生成中...")
    generate_circle_image(
        width=800,
        height=600,
        bg_color=(255, 255, 255),
        circle_color=(255, 100, 100),
        radius=150,
        filename=os.path.join(output_dir, "circle.png")
    )
    
    print("\n" + "=" * 50)
    print("すべての画像生成が完了しました！")
    print(f"画像は '{output_dir}' フォルダに保存されています。")
    print("=" * 50)

if __name__ == "__main__":
    main()
