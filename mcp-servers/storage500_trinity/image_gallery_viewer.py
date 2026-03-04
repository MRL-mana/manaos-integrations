#!/usr/bin/env python3
"""
Image Gallery Viewer
生成された画像のギャラリービューアー
"""

from flask import Flask, render_template_string, jsonify, send_file
from pathlib import Path
import json
from datetime import datetime
import os

app = Flask(__name__)

# ギャラリービューアーのHTMLテンプレート
GALLERY_TEMPLATE = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🖼️ Trinity Image Gallery</title>
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
            max-width: 1400px;
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
        
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }
        
        .stat-card {
            background: #fff;
            border-radius: 15px;
            padding: 20px;
            text-align: center;
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1);
        }
        
        .stat-number {
            font-size: 2.5em;
            font-weight: bold;
            color: #3498db;
            margin-bottom: 10px;
        }
        
        .stat-label {
            color: #7f8c8d;
            font-size: 1.1em;
        }
        
        .filters {
            display: flex;
            gap: 15px;
            margin-bottom: 30px;
            flex-wrap: wrap;
            justify-content: center;
        }
        
        .filter-btn {
            padding: 10px 20px;
            border: 2px solid #3498db;
            background: transparent;
            color: #3498db;
            border-radius: 25px;
            cursor: pointer;
            transition: all 0.3s ease;
            font-weight: 600;
        }
        
        .filter-btn:hover,
        .filter-btn.active {
            background: #3498db;
            color: white;
        }
        
        .image-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 25px;
        }
        
        .image-card {
            background: #fff;
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 15px 30px rgba(0, 0, 0, 0.1);
            transition: transform 0.3s ease;
            position: relative;
        }
        
        .image-card:hover {
            transform: translateY(-10px);
        }
        
        .image-card img {
            width: 100%;
            height: 250px;
            object-fit: cover;
        }
        
        .image-info {
            padding: 20px;
        }
        
        .image-title {
            color: #2c3e50;
            font-size: 1.2em;
            font-weight: 600;
            margin-bottom: 8px;
        }
        
        .image-meta {
            color: #7f8c8d;
            font-size: 0.9em;
            margin-bottom: 5px;
        }
        
        .image-tags {
            display: flex;
            gap: 5px;
            flex-wrap: wrap;
            margin-top: 10px;
        }
        
        .tag {
            background: #ecf0f1;
            color: #2c3e50;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 0.8em;
        }
        
        .tag.enhanced { background: #e8f5e8; color: #27ae60; }
        .tag.hdr { background: #fff3cd; color: #856404; }
        .tag.cinematic { background: #d1ecf1; color: #0c5460; }
        .tag.vintage { background: #f8d7da; color: #721c24; }
        .tag.modern { background: #d4edda; color: #155724; }
        
        .loading {
            text-align: center;
            padding: 50px;
            color: #7f8c8d;
        }
        
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #3498db;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        @media (max-width: 768px) {
            .image-grid {
                grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
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
            <h1>🖼️ Trinity Image Gallery</h1>
            <p>Generated Images Collection</p>
        </div>
        
        <div class="stats" id="stats">
            <div class="stat-card">
                <div class="stat-number" id="totalImages">-</div>
                <div class="stat-label">Total Images</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="totalSize">-</div>
                <div class="stat-label">Total Size</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="enhancedImages">-</div>
                <div class="stat-label">Enhanced</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="aiImages">-</div>
                <div class="stat-label">AI Generated</div>
            </div>
        </div>
        
        <div class="filters">
            <button class="filter-btn active" data-filter="all">All Images</button>
            <button class="filter-btn" data-filter="enhanced">Enhanced</button>
            <button class="filter-btn" data-filter="hdr">HDR</button>
            <button class="filter-btn" data-filter="cinematic">Cinematic</button>
            <button class="filter-btn" data-filter="vintage">Vintage</button>
            <button class="filter-btn" data-filter="modern">Modern</button>
            <button class="filter-btn" data-filter="ai">AI Generated</button>
            <button class="filter-btn" data-filter="ultra">Ultra HD</button>
        </div>
        
        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p>Loading images...</p>
        </div>
        
        <div class="image-grid" id="imageGrid">
            <!-- 画像がここに動的に追加されます -->
        </div>
    </div>
    
    <script>
        let allImages = [];
        let filteredImages = [];
        
        // 画像データを読み込み
        async function loadImages() {
            try {
                const response = await fetch('/api/images');
                const data = await response.json();
                allImages = data.images;
                filteredImages = [...allImages];
                
                updateStats(data.stats);
                renderImages();
                hideLoading();
            } catch (error) {
                console.error('Error loading images:', error);
            }
        }
        
        function updateStats(stats) {
            document.getElementById('totalImages').textContent = stats.totalImages;
            document.getElementById('totalSize').textContent = stats.totalSize;
            document.getElementById('enhancedImages').textContent = stats.enhancedImages;
            document.getElementById('aiImages').textContent = stats.aiImages;
        }
        
        function renderImages() {
            const grid = document.getElementById('imageGrid');
            grid.innerHTML = '';
            
            filteredImages.forEach(image => {
                const card = document.createElement('div');
                card.className = 'image-card';
                card.innerHTML = `
                    <img src="/image/${image.filename}" alt="${image.name}" loading="lazy">
                    <div class="image-info">
                        <div class="image-title">${image.name}</div>
                        <div class="image-meta">Size: ${image.size}</div>
                        <div class="image-meta">Date: ${image.date}</div>
                        <div class="image-tags">
                            ${image.tags.map(tag => `<span class="tag ${tag}">${tag}</span>`).join('')}
                        </div>
                    </div>
                `;
                grid.appendChild(card);
            });
        }
        
        function filterImages(filter) {
            if (filter === 'all') {
                filteredImages = [...allImages];
            } else {
                filteredImages = allImages.filter(image => 
                    image.tags.includes(filter)
                );
            }
            renderImages();
        }
        
        function hideLoading() {
            document.getElementById('loading').style.display = 'none';
        }
        
        // フィルターボタンのイベントリスナー
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                // アクティブクラスを更新
                document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                this.classList.add('active');
                
                // フィルター適用
                const filter = this.dataset.filter;
                filterImages(filter);
            });
        });
        
        // ページ読み込み時に画像を読み込み
        loadImages();
    </script>
</body>
</html>
"""

@app.route('/')
def gallery():
    return render_template_string(GALLERY_TEMPLATE)

@app.route('/api/images')
def get_images():
    try:
        image_dir = Path("/root/mana-workspace/outputs/images")
        images = []
        
        # 統計情報
        total_size = 0
        enhanced_count = 0
        ai_count = 0
        
        for file_path in image_dir.glob("*.png"):
            stat = file_path.stat()
            size_mb = round(stat.st_size / (1024 * 1024), 2)
            total_size += stat.st_size
            
            # タグの判定
            tags = []
            filename = file_path.name.lower()
            
            if 'enhanced' in filename:
                tags.append('enhanced')
                enhanced_count += 1
            if 'hdr' in filename:
                tags.append('hdr')
            if 'cinematic' in filename:
                tags.append('cinematic')
            if 'vintage' in filename:
                tags.append('vintage')
            if 'modern' in filename:
                tags.append('modern')
            if 'ai_generated' in filename:
                tags.append('ai')
                ai_count += 1
            if 'ultra_hd' in filename:
                tags.append('ultra')
            if 'professional' in filename:
                tags.append('professional')
            if 'artistic' in filename:
                tags.append('artistic')
            
            images.append({
                'filename': file_path.name,
                'name': file_path.stem,
                'date': datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                'size': f"{size_mb}MB",
                'tags': tags
            })
        
        # 日付順でソート（新しい順）
        images.sort(key=lambda x: x['date'], reverse=True)
        
        # 統計情報
        stats = {
            'totalImages': len(images),
            'totalSize': f"{round(total_size / (1024 * 1024), 1)}MB",
            'enhancedImages': enhanced_count,
            'aiImages': ai_count
        }
        
        return jsonify({
            'images': images,
            'stats': stats
        })
        
    except Exception as e:
        return jsonify({'error': str(e)})

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
    app.run(host='0.0.0.0', port=5092, debug=True)


