#!/usr/bin/env python3
"""
Web Image Gallery
生成された画像をWebブラウザで表示するギャラリー
"""

import os
import base64
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template_string, send_file, jsonify
import threading
import time

class WebImageGallery:
    def __init__(self):
        self.app = Flask(__name__)
        self.images_dir = Path("/root/trinity_workspace/generated_images")
        self.storage_dir = Path("/mnt/storage500/trinity_images")
        self.port = 5092
        
        # ルート設定
        self.app.route('/')(self.index)
        self.app.route('/api/images')(self.api_images)
        self.app.route('/image/<filename>')(self.serve_image)
        self.app.route('/gallery')(self.gallery)
        
    def get_images(self):
        """画像一覧取得"""
        images = []
        
        # 元のディレクトリから画像を取得
        if self.images_dir.exists():
            for image_file in self.images_dir.glob("*.png"):
                if not image_file.name.endswith('.backup'):
                    try:
                        stat = image_file.stat()
                        images.append({
                            "name": image_file.name,
                            "path": str(image_file),
                            "size_mb": stat.st_size / (1024 * 1024),
                            "created": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            "url": f"/image/{image_file.name}"
                        })
                    except:
                        continue
        
        # 作成日時順でソート
        images.sort(key=lambda x: x['created'], reverse=True)
        return images
    
    def index(self):
        """メインページ"""
        images = self.get_images()
        
        html_template = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Trinity AI Image Gallery</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
        }
        
        h1 {
            text-align: center;
            color: #333;
            margin-bottom: 30px;
            font-size: 2.5em;
        }
        
        .stats {
            background: #e9ecef;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
            text-align: center;
        }
        
        .stats h3 {
            margin-bottom: 10px;
            color: #333;
        }
        
        .gallery {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        
        .image-card {
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 10px 20px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
            background: white;
        }
        
        .image-card:hover {
            transform: translateY(-5px);
        }
        
        .image-card img {
            width: 100%;
            height: 300px;
            object-fit: cover;
            cursor: pointer;
        }
        
        .image-info {
            padding: 15px;
            background: #f8f9fa;
        }
        
        .image-name {
            font-weight: bold;
            color: #333;
            margin-bottom: 5px;
            word-break: break-all;
        }
        
        .image-details {
            font-size: 0.9em;
            color: #666;
        }
        
        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.9);
        }
        
        .modal-content {
            margin: auto;
            display: block;
            max-width: 90%;
            max-height: 90%;
            margin-top: 5%;
        }
        
        .close {
            position: absolute;
            top: 15px;
            right: 35px;
            color: #f1f1f1;
            font-size: 40px;
            font-weight: bold;
            cursor: pointer;
        }
        
        .close:hover {
            color: #bbb;
        }
        
        .no-images {
            text-align: center;
            color: #666;
            font-size: 1.2em;
            padding: 50px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎨 Trinity AI Image Gallery</h1>
        
        <div class="stats">
            <h3>📊 画像統計</h3>
            <p>総画像数: {{ images|length }}枚</p>
            <p>総サイズ: {{ "%.1f"|format(total_size) }}MB</p>
        </div>
        
        {% if images %}
        <div class="gallery">
            {% for image in images %}
            <div class="image-card">
                <img src="{{ image.url }}" alt="{{ image.name }}" onclick="openModal('{{ image.url }}')">
                <div class="image-info">
                    <div class="image-name">{{ image.name }}</div>
                    <div class="image-details">
                        サイズ: {{ "%.1f"|format(image.size_mb) }}MB<br>
                        作成日時: {{ image.created[:19] }}
                    </div>
                </div>
            </div>
            {% endfor %}
        </div>
        {% else %}
        <div class="no-images">
            <p>🖼️ 生成された画像がありません</p>
            <p>AI画像生成を実行してください</p>
        </div>
        {% endif %}
    </div>
    
    <!-- Modal -->
    <div id="imageModal" class="modal">
        <span class="close" onclick="closeModal()">&times;</span>
        <img class="modal-content" id="modalImage">
    </div>
    
    <script>
        function openModal(imageSrc) {
            document.getElementById('imageModal').style.display = 'block';
            document.getElementById('modalImage').src = imageSrc;
        }
        
        function closeModal() {
            document.getElementById('imageModal').style.display = 'none';
        }
        
        // ESCキーでモーダルを閉じる
        document.addEventListener('keydown', function(event) {
            if (event.key === 'Escape') {
                closeModal();
            }
        });
        
        // モーダル外クリックで閉じる
        document.getElementById('imageModal').addEventListener('click', function(event) {
            if (event.target === this) {
                closeModal();
            }
        });
    </script>
</body>
</html>
        """
        
        total_size = sum(img['size_mb'] for img in images)
        return render_template_string(html_template, images=images, total_size=total_size)
    
    def api_images(self):
        """API: 画像一覧"""
        images = self.get_images()
        return jsonify(images)
    
    def serve_image(self, filename):
        """画像ファイル配信"""
        image_path = self.images_dir / filename
        
        if not image_path.exists():
            return "画像が見つかりません", 404
        
        return send_file(str(image_path))
    
    def gallery(self):
        """ギャラリーページ（シンプル版）"""
        images = self.get_images()
        
        simple_html = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Trinity AI Gallery</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .gallery { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 15px; }
        .image-card { background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .image-card img { width: 100%; height: 250px; object-fit: cover; }
        .image-info { padding: 10px; }
        .image-name { font-weight: bold; margin-bottom: 5px; }
        .image-details { font-size: 0.9em; color: #666; }
    </style>
</head>
<body>
    <h1>🎨 Trinity AI Gallery</h1>
    <div class="gallery">
        {% for image in images %}
        <div class="image-card">
            <img src="{{ image.url }}" alt="{{ image.name }}">
            <div class="image-info">
                <div class="image-name">{{ image.name }}</div>
                <div class="image-details">{{ "%.1f"|format(image.size_mb) }}MB - {{ image.created[:19] }}</div>
            </div>
        </div>
        {% endfor %}
    </div>
</body>
</html>
        """
        
        return render_template_string(simple_html, images=images)
    
    def start_server(self):
        """サーバー起動"""
        print(f"🌐 Web Image Gallery 起動中...")
        print(f"📱 アクセスURL: http://127.0.0.1:{self.port}")
        print(f"📱 外部アクセス: http://163.44.120.49:{self.port}")
        print(f"📱 Tailscale: http://100.93.120.33:{self.port}")
        print("=" * 60)
        
        try:
            self.app.run(host='0.0.0.0', port=self.port, debug=False, threaded=True)
        except Exception as e:
            print(f"❌ サーバー起動エラー: {str(e)}")


def main():
    """メイン関数"""
    gallery = WebImageGallery()
    
    print("🎨 Trinity AI Web Image Gallery")
    print("=" * 60)
    
    # 画像一覧表示
    images = gallery.get_images()
    print(f"📸 検出された画像: {len(images)}枚")
    
    for i, image in enumerate(images, 1):
        print(f"{i:2d}. {image['name']} ({image['size_mb']:.1f}MB)")
    
    print()
    
    # サーバー起動
    gallery.start_server()


if __name__ == "__main__":
    main()


