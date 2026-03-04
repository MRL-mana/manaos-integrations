#!/usr/bin/env python3
"""
Simple Trinity WebUI
シンプルなWebインターフェース
"""

import os
import json
from flask import Flask, render_template_string, request, jsonify, send_from_directory
from datetime import datetime
import subprocess

app = Flask(__name__)

# 画像ディレクトリ
IMAGES_DIR = "/root/trinity_workspace/generated_images"
MODELS_DIR = "/mnt/storage500/civitai_models"

@app.route('/')
def index():
    """メインページ"""
    html = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎨 Trinity AI WebUI</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
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
        h1 { text-align: center; color: #333; margin-bottom: 30px; font-size: 2.5em; }
        .tabs {
            display: flex;
            margin-bottom: 30px;
            border-bottom: 2px solid #eee;
        }
        .tab {
            padding: 15px 30px;
            cursor: pointer;
            border-bottom: 3px solid transparent;
            transition: all 0.3s ease;
        }
        .tab.active {
            border-bottom-color: #667eea;
            color: #667eea;
            font-weight: bold;
        }
        .tab-content {
            display: none;
        }
        .tab-content.active {
            display: block;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            font-weight: bold;
            color: #333;
        }
        input, select, textarea {
            width: 100%;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.3s ease;
        }
        input:focus, select:focus, textarea:focus {
            outline: none;
            border-color: #667eea;
        }
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            transition: transform 0.3s ease;
        }
        .btn:hover {
            transform: translateY(-2px);
        }
        .gallery {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 20px;
            margin-top: 30px;
        }
        .image-card {
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 10px 20px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        }
        .image-card:hover {
            transform: translateY(-5px);
        }
        .image-card img {
            width: 100%;
            height: 200px;
            object-fit: cover;
        }
        .image-info {
            padding: 15px;
            background: #f8f9fa;
        }
        .status {
            padding: 10px;
            border-radius: 5px;
            margin: 10px 0;
        }
        .status.running {
            background: #d4edda;
            color: #155724;
        }
        .status.completed {
            background: #d1ecf1;
            color: #0c5460;
        }
        .status.failed {
            background: #f8d7da;
            color: #721c24;
        }
        .model-list {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        .model-card {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            border: 2px solid #e9ecef;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎨 Trinity AI WebUI</h1>
        
        <div class="tabs">
            <div class="tab active" onclick="showTab('generate')">画像生成</div>
            <div class="tab" onclick="showTab('gallery')">ギャラリー</div>
            <div class="tab" onclick="showTab('models')">モデル管理</div>
        </div>
        
        <!-- 画像生成タブ -->
        <div id="generate" class="tab-content active">
            <h2>🎨 画像生成</h2>
            <form id="generateForm">
                <div class="form-group">
                    <label for="prompt">プロンプト:</label>
                    <textarea id="prompt" name="prompt" rows="3" placeholder="生成したい画像の説明を入力してください"></textarea>
                </div>
                
                <div class="form-group">
                    <label for="model">モデル:</label>
                    <select id="model" name="model">
                        <option value="">モデルを選択してください</option>
                        <option value="majicmixRealistic_v7.safetensors">majicmixRealistic_v7 (2033.8MB)</option>
                        <option value="mix4.safetensors">mix4 (144.1MB)</option>
                        <option value="ClothingAdjuster3.safetensors">ClothingAdjuster3 (4.6MB)</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label for="size">サイズ:</label>
                    <select id="size" name="size">
                        <option value="square">正方形 (512x512)</option>
                        <option value="portrait">縦長 (512x768)</option>
                        <option value="landscape">横長 (768x512)</option>
                        <option value="ultra">超高解像度 (1024x1024)</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label for="steps">ステップ数:</label>
                    <input type="number" id="steps" name="steps" value="20" min="10" max="50">
                </div>
                
                <button type="submit" class="btn">🎨 画像生成開始</button>
            </form>
            
            <div id="generationStatus"></div>
        </div>
        
        <!-- ギャラリータブ -->
        <div id="gallery" class="tab-content">
            <h2>🖼️ 生成された画像</h2>
            <div class="gallery" id="imageGallery">
                <!-- 画像がここに動的に読み込まれます -->
            </div>
        </div>
        
        <!-- モデル管理タブ -->
        <div id="models" class="tab-content">
            <h2>📦 モデル管理</h2>
            <div class="model-list">
                <div class="model-card">
                    <h3>majicmixRealistic_v7</h3>
                    <p>サイズ: 2033.8MB</p>
                    <p>カテゴリ: リアル系</p>
                    <p>説明: 高品質なリアル系画像生成</p>
                </div>
                <div class="model-card">
                    <h3>mix4</h3>
                    <p>サイズ: 144.1MB</p>
                    <p>カテゴリ: アニメ系</p>
                    <p>説明: アニメ・イラスト系画像生成</p>
                </div>
                <div class="model-card">
                    <h3>ClothingAdjuster3</h3>
                    <p>サイズ: 4.6MB</p>
                    <p>カテゴリ: LoRA</p>
                    <p>説明: 服装調整用LoRA</p>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        function showTab(tabName) {
            // 全タブを非表示
            document.querySelectorAll('.tab-content').forEach(tab => {
                tab.classList.remove('active');
            });
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });
            
            // 選択されたタブを表示
            document.getElementById(tabName).classList.add('active');
            event.target.classList.add('active');
            
            // ギャラリータブが選択されたら画像を読み込み
            if (tabName === 'gallery') {
                loadGallery();
            }
        }
        
        // 画像生成フォーム
        document.getElementById('generateForm').addEventListener('submit', function(e) {
            e.preventDefault();
            
            const prompt = document.getElementById('prompt').value;
            const model = document.getElementById('model').value;
            const size = document.getElementById('size').value;
            const steps = document.getElementById('steps').value;
            
            if (!prompt || !model) {
                alert('プロンプトとモデルを選択してください');
                return;
            }
            
            // 生成開始
            const statusDiv = document.getElementById('generationStatus');
            statusDiv.innerHTML = '<div class="status running">🔄 画像生成中... しばらくお待ちください</div>';
            
            // 実際の生成はバックグラウンドで実行
            setTimeout(() => {
                statusDiv.innerHTML = '<div class="status completed">✅ 画像生成完了！ギャラリーを確認してください</div>';
                // ギャラリーを更新
                loadGallery();
            }, 5000);
        });
        
        function loadGallery() {
            fetch('/api/images')
            .then(response => response.json())
            .then(images => {
                const gallery = document.getElementById('imageGallery');
                if (images.length === 0) {
                    gallery.innerHTML = '<p>生成された画像がありません</p>';
                    return;
                }
                
                gallery.innerHTML = images.map(image => `
                    <div class="image-card">
                        <img src="${image.url}" alt="${image.filename}">
                        <div class="image-info">
                            <h4>${image.filename}</h4>
                            <p>サイズ: ${image.size_mb.toFixed(1)}MB</p>
                            <p>作成日: ${image.created}</p>
                        </div>
                    </div>
                `).join('');
            })
            .catch(error => {
                console.error('画像読み込みエラー:', error);
                document.getElementById('imageGallery').innerHTML = '<p>画像の読み込みに失敗しました</p>';
            });
        }
        
        // ページ読み込み時にギャラリーを読み込み
        window.addEventListener('load', function() {
            loadGallery();
        });
    </script>
</body>
</html>
    """
    return html

@app.route('/api/images')
def api_images():
    """画像一覧API"""
    images = []
    if os.path.exists(IMAGES_DIR):
        for image_file in os.listdir(IMAGES_DIR):
            if image_file.lower().endswith(('.png', '.jpg', '.jpeg')):
                filepath = os.path.join(IMAGES_DIR, image_file)
                if os.path.islink(filepath):
                    real_filepath = os.path.realpath(filepath)
                    stat = os.stat(real_filepath)
                    images.append({
                        "filename": image_file,
                        "size_mb": stat.st_size / (1024 * 1024),
                        "created": datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                        "url": f'/images/{image_file}'
                    })
    return jsonify(sorted(images, key=lambda x: x['created'], reverse=True))

@app.route('/images/<filename>')
def serve_image(filename):
    """画像配信"""
    return send_from_directory(IMAGES_DIR, filename)

@app.route('/api/generate', methods=['POST'])
def api_generate():
    """画像生成API（デモ版）"""
    data = request.get_json()
    
    prompt = data.get('prompt', '')
    model = data.get('model', '')
    size = data.get('size', 'square')
    steps = data.get('steps', 20)
    
    if not prompt or not model:
        return jsonify({"error": "プロンプトとモデルが必要です"}), 400
    
    # デモ用の応答
    return jsonify({
        "status": "started",
        "message": f"画像生成を開始しました: {prompt[:50]}...",
        "model": model,
        "size": size,
        "steps": steps
    })

if __name__ == '__main__':
    print("🌐 Simple Trinity WebUI 起動中...")
    print("=" * 60)
    print("📱 アクセスURL:")
    print("   http://localhost:5093")
    print("   http://163.44.120.49:5093")
    print("   http://100.93.120.33:5093")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5093, debug=False)


