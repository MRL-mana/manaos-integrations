#!/usr/bin/env python3
"""
Trinity Web Interface
画像生成システムのWebインターフェース
"""

from flask import Flask, render_template_string, request, jsonify, send_file
import os
from pathlib import Path
import json
from datetime import datetime

app = Flask(__name__)

# HTMLテンプレート
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎨 Trinity Image Generator</title>
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
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
        }
        
        .header {
            text-align: center;
            margin-bottom: 40px;
        }
        
        .header h1 {
            color: #2c3e50;
            font-size: 3em;
            margin-bottom: 10px;
        }
        
        .header p {
            color: #7f8c8d;
            font-size: 1.2em;
        }
        
        .generator-section {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin-bottom: 40px;
        }
        
        .generator-card {
            background: #fff;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1);
            border: 2px solid #ecf0f1;
            transition: transform 0.3s ease;
        }
        
        .generator-card:hover {
            transform: translateY(-5px);
        }
        
        .generator-card h3 {
            color: #2c3e50;
            margin-bottom: 20px;
            font-size: 1.5em;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 8px;
            color: #34495e;
            font-weight: 600;
        }
        
        .form-group input,
        .form-group select,
        .form-group textarea {
            width: 100%;
            padding: 12px;
            border: 2px solid #ecf0f1;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.3s ease;
        }
        
        .form-group input:focus,
        .form-group select:focus,
        .form-group textarea:focus {
            outline: none;
            border-color: #3498db;
        }
        
        .btn {
            background: linear-gradient(135deg, #3498db, #2980b9);
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.3s ease;
            width: 100%;
        }
        
        .btn:hover {
            transform: translateY(-2px);
        }
        
        .btn:disabled {
            background: #bdc3c7;
            cursor: not-allowed;
            transform: none;
        }
        
        .gallery {
            margin-top: 40px;
        }
        
        .gallery h3 {
            color: #2c3e50;
            margin-bottom: 20px;
            font-size: 1.8em;
        }
        
        .image-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 20px;
        }
        
        .image-card {
            background: #fff;
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1);
            transition: transform 0.3s ease;
        }
        
        .image-card:hover {
            transform: scale(1.05);
        }
        
        .image-card img {
            width: 100%;
            height: 200px;
            object-fit: cover;
        }
        
        .image-info {
            padding: 15px;
        }
        
        .image-info h4 {
            color: #2c3e50;
            margin-bottom: 5px;
        }
        
        .image-info p {
            color: #7f8c8d;
            font-size: 0.9em;
        }
        
        .loading {
            display: none;
            text-align: center;
            margin: 20px 0;
        }
        
        .loading.show {
            display: block;
        }
        
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #3498db;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 10px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .status {
            margin-top: 20px;
            padding: 15px;
            border-radius: 8px;
            display: none;
        }
        
        .status.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        
        .status.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        
        .status.show {
            display: block;
        }
        
        @media (max-width: 768px) {
            .generator-section {
                grid-template-columns: 1fr;
            }
            
            .header h1 {
                font-size: 2em;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎨 Trinity Image Generator</h1>
            <p>AI-powered image generation system</p>
        </div>
        
        <div class="generator-section">
            <!-- Canva風画像生成 -->
            <div class="generator-card">
                <h3>🎨 Canva風画像生成</h3>
                <form id="canvaForm">
                    <div class="form-group">
                        <label for="canvaTitle">タイトル</label>
                        <input type="text" id="canvaTitle" name="title" placeholder="画像のタイトル" required>
                    </div>
                    <div class="form-group">
                        <label for="canvaSubtitle">サブタイトル</label>
                        <input type="text" id="canvaSubtitle" name="subtitle" placeholder="画像のサブタイトル">
                    </div>
                    <div class="form-group">
                        <label for="canvaTheme">テーマ</label>
                        <select id="canvaTheme" name="theme">
                            <option value="vibrant">Vibrant</option>
                            <option value="pastel">Pastel</option>
                            <option value="monochrome">Monochrome</option>
                            <option value="sunset">Sunset</option>
                            <option value="ocean">Ocean</option>
                        </select>
                    </div>
                    <button type="submit" class="btn">🎨 画像生成</button>
                </form>
            </div>
            
            <!-- AI画像生成 -->
            <div class="generator-card">
                <h3>🤖 AI画像生成</h3>
                <form id="aiForm">
                    <div class="form-group">
                        <label for="aiPrompt">プロンプト</label>
                        <textarea id="aiPrompt" name="prompt" rows="3" placeholder="生成したい画像の説明" required></textarea>
                    </div>
                    <div class="form-group">
                        <label for="aiStyle">スタイル</label>
                        <select id="aiStyle" name="style">
                            <option value="photorealistic">Photorealistic</option>
                            <option value="anime">Anime</option>
                            <option value="oil_painting">Oil Painting</option>
                            <option value="watercolor">Watercolor</option>
                            <option value="digital_art">Digital Art</option>
                            <option value="sketch">Sketch</option>
                            <option value="cartoon">Cartoon</option>
                            <option value="minimalist">Minimalist</option>
                        </select>
                    </div>
                    <button type="submit" class="btn">🤖 AI生成</button>
                </form>
            </div>
        </div>
        
        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p>画像を生成中...</p>
        </div>
        
        <div class="status" id="status"></div>
        
        <div class="gallery">
            <h3>🖼️ 生成された画像</h3>
            <div class="image-grid" id="imageGrid">
                <!-- 画像がここに動的に追加されます -->
            </div>
        </div>
    </div>
    
    <script>
        // フォーム送信処理
        document.getElementById('canvaForm').addEventListener('submit', function(e) {
            e.preventDefault();
            generateCanvaImage();
        });
        
        document.getElementById('aiForm').addEventListener('submit', function(e) {
            e.preventDefault();
            generateAIImage();
        });
        
        function generateCanvaImage() {
            const formData = new FormData(document.getElementById('canvaForm'));
            const data = Object.fromEntries(formData);
            
            showLoading();
            
            fetch('/generate/canva', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            })
            .then(response => response.json())
            .then(data => {
                hideLoading();
                if (data.success) {
                    showStatus('画像生成完了！', 'success');
                    loadImages();
                } else {
                    showStatus('エラー: ' + data.error, 'error');
                }
            })
            .catch(error => {
                hideLoading();
                showStatus('エラー: ' + error.message, 'error');
            });
        }
        
        function generateAIImage() {
            const formData = new FormData(document.getElementById('aiForm'));
            const data = Object.fromEntries(formData);
            
            showLoading();
            
            fetch('/generate/ai', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            })
            .then(response => response.json())
            .then(data => {
                hideLoading();
                if (data.success) {
                    showStatus('AI画像生成完了！', 'success');
                    loadImages();
                } else {
                    showStatus('エラー: ' + data.error, 'error');
                }
            })
            .catch(error => {
                hideLoading();
                showStatus('エラー: ' + error.message, 'error');
            });
        }
        
        function showLoading() {
            document.getElementById('loading').classList.add('show');
            document.getElementById('status').classList.remove('show');
        }
        
        function hideLoading() {
            document.getElementById('loading').classList.remove('show');
        }
        
        function showStatus(message, type) {
            const status = document.getElementById('status');
            status.textContent = message;
            status.className = 'status ' + type + ' show';
        }
        
        function loadImages() {
            fetch('/images')
            .then(response => response.json())
            .then(data => {
                const grid = document.getElementById('imageGrid');
                grid.innerHTML = '';
                
                data.images.forEach(image => {
                    const card = document.createElement('div');
                    card.className = 'image-card';
                    card.innerHTML = `
                        <img src="/image/${image.filename}" alt="${image.name}">
                        <div class="image-info">
                            <h4>${image.name}</h4>
                            <p>${image.date}</p>
                        </div>
                    `;
                    grid.appendChild(card);
                });
            });
        }
        
        // ページ読み込み時に画像を読み込み
        loadImages();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/generate/canva', methods=['POST'])
def generate_canva():
    try:
        data = request.get_json()
        
        # Canva風画像生成を実行
        from image_generator import TrinityImageGenerator
        generator = TrinityImageGenerator()
        
        result = generator.create_canva_style_poster(
            data['title'],
            data['subtitle'],
            data['theme']
        )
        
        return jsonify({
            'success': True,
            'filepath': result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/generate/ai', methods=['POST'])
def generate_ai():
    try:
        data = request.get_json()
        
        # AI画像生成を実行
        from ai_image_generator import CPUImageGenerator
        generator = CPUImageGenerator()
        
        result = generator.generate_with_style(
            data['prompt'],
            data['style']
        )
        
        return jsonify({
            'success': True,
            'filepath': result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/images')
def get_images():
    try:
        image_dir = Path("/root/mana-workspace/outputs/images")
        images = []
        
        for file_path in image_dir.glob("*.png"):
            stat = file_path.stat()
            images.append({
                'filename': file_path.name,
                'name': file_path.stem,
                'date': datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                'size': stat.st_size
            })
        
        # 日付順でソート（新しい順）
        images.sort(key=lambda x: x['date'], reverse=True)
        
        return jsonify({
            'images': images
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e)
        })

@app.route('/image/<filename>')
def serve_image(filename):
    try:
        image_path = Path("/root/mana-workspace/outputs/images") / filename
        if image_path.exists():
            return send_file(str(image_path))
        else:
            return "Image not found", 404
    except Exception as e:
        return str(e), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5091, debug=True)
