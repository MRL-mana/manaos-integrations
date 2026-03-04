#!/usr/bin/env python3
"""
Trinity WebUI
統合Webインターフェース - 画像生成・ギャラリー・管理
"""

import os
import json
from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for
from datetime import datetime
import subprocess
import threading
import time

app = Flask(__name__)

class TrinityWebUI:
    def __init__(self):
        self.images_dir = "/root/trinity_workspace/generated_images"
        self.models_dir = "/mnt/storage500/civitai_models"
        self.tools_dir = "/root/trinity_workspace/tools"
        
        # 生成タスク管理
        self.generation_tasks = {}
        self.task_counter = 0
    
    def get_available_models(self):
        """利用可能なモデル一覧取得"""
        models = []
        if os.path.exists(self.models_dir):
            for model_file in os.listdir(self.models_dir):
                if model_file.endswith('.safetensors'):
                    info_file = os.path.join(self.models_dir, model_file.replace('.safetensors', '.json'))
                    if os.path.exists(info_file):
                        try:
                            with open(info_file, 'r', encoding='utf-8') as f:
                                model_info = json.load(f)
                            models.append({
                                "name": model_info.get('name', model_file),
                                "filename": model_file,
                                "size_mb": os.path.getsize(os.path.join(self.models_dir, model_file)) / (1024 * 1024),
                                "category": model_info.get('category', 'unknown')
                            })
                        except:
                            models.append({
                                "name": model_file,
                                "filename": model_file,
                                "size_mb": os.path.getsize(os.path.join(self.models_dir, model_file)) / (1024 * 1024),
                                "category": "unknown"
                            })
        return models
    
    def get_generated_images(self):
        """生成された画像一覧取得"""
        images = []
        if os.path.exists(self.images_dir):
            for image_file in os.listdir(self.images_dir):
                if image_file.lower().endswith(('.png', '.jpg', '.jpeg')):
                    filepath = os.path.join(self.images_dir, image_file)
                    if os.path.islink(filepath):
                        real_filepath = os.path.realpath(filepath)
                        stat = os.stat(real_filepath)
                        images.append({
                            "filename": image_file,
                            "size_mb": stat.st_size / (1024 * 1024),
                            "created": datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                            "url": f'/images/{image_file}'
                        })
        return sorted(images, key=lambda x: x['created'], reverse=True)
    
    def start_generation_task(self, prompt, model_name, size_preset, num_steps):
        """画像生成タスク開始"""
        self.task_counter += 1
        task_id = f"task_{self.task_counter}"
        
        # タスク情報
        self.generation_tasks[task_id] = {
            "status": "running",
            "start_time": datetime.now().isoformat(),
            "prompt": prompt,
            "model": model_name,
            "size": size_preset,
            "steps": num_steps,
            "progress": 0,
            "result": None
        }
        
        # バックグラウンドで生成実行
        def run_generation():
            try:
                # 高度な画像生成スクリプトを実行
                cmd = [
                    "python3", f"{self.tools_dir}/advanced_image_generator.py",
                    "--prompt", prompt,
                    "--model", model_name,
                    "--size", size_preset,
                    "--steps", str(num_steps)
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.tools_dir)
                
                if result.returncode == 0:
                    self.generation_tasks[task_id]["status"] = "completed"
                    self.generation_tasks[task_id]["result"] = "success"
                else:
                    self.generation_tasks[task_id]["status"] = "failed"
                    self.generation_tasks[task_id]["result"] = result.stderr
                    
            except Exception as e:
                self.generation_tasks[task_id]["status"] = "failed"
                self.generation_tasks[task_id]["result"] = str(e)
        
        # スレッドで実行
        thread = threading.Thread(target=run_generation)
        thread.daemon = True
        thread.start()
        
        return task_id

# WebUIインスタンス
webui = TrinityWebUI()

@app.route('/')
def index():
    """メインページ"""
    models = webui.get_available_models()
    images = webui.get_generated_images()[:10]  # 最新10枚
    
    return render_template('trinity_webui.html', 
                         models=models, 
                         images=images,
                         size_presets={
                             "square": "512x512",
                             "portrait": "512x768", 
                             "landscape": "768x512",
                             "ultra": "1024x1024"
                         })

@app.route('/api/models')
def api_models():
    """モデル一覧API"""
    return jsonify(webui.get_available_models())

@app.route('/api/images')
def api_images():
    """画像一覧API"""
    return jsonify(webui.get_generated_images())

@app.route('/api/generate', methods=['POST'])
def api_generate():
    """画像生成API"""
    data = request.get_json()
    
    prompt = data.get('prompt', '')
    model_name = data.get('model', '')
    size_preset = data.get('size', 'square')
    num_steps = int(data.get('steps', 20))
    
    if not prompt or not model_name:
        return jsonify({"error": "プロンプトとモデルが必要です"}), 400
    
    # 生成タスク開始
    task_id = webui.start_generation_task(prompt, model_name, size_preset, num_steps)
    
    return jsonify({"task_id": task_id, "status": "started"})

@app.route('/api/task/<task_id>')
def api_task_status(task_id):
    """タスク状況API"""
    if task_id not in webui.generation_tasks:
        return jsonify({"error": "タスクが見つかりません"}), 404
    
    return jsonify(webui.generation_tasks[task_id])

@app.route('/images/<filename>')
def serve_image(filename):
    """画像配信"""
    return send_from_directory(webui.images_dir, filename)

@app.route('/gallery')
def gallery():
    """ギャラリーページ"""
    images = webui.get_generated_images()
    return render_template('gallery.html', images=images)

@app.route('/admin')
def admin():
    """管理ページ"""
    return render_template('admin.html', 
                         tasks=webui.generation_tasks,
                         models=webui.get_available_models())

# テンプレート作成
def create_templates():
    """HTMLテンプレート作成"""
    os.makedirs('templates', exist_ok=True)
    
    # メインページ
    main_html = """
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
                        {% for model in models %}
                        <option value="{{ model.filename }}">{{ model.name }} ({{ model.size_mb:.1f}}MB)</option>
                        {% endfor %}
                    </select>
                </div>
                
                <div class="form-group">
                    <label for="size">サイズ:</label>
                    <select id="size" name="size">
                        {% for preset, size in size_presets.items() %}
                        <option value="{{ preset }}">{{ preset }} ({{ size }})</option>
                        {% endfor %}
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
                {% for image in images %}
                <div class="image-card">
                    <img src="{{ image.url }}" alt="{{ image.filename }}">
                    <div class="image-info">
                        <h4>{{ image.filename }}</h4>
                        <p>サイズ: {{ image.size_mb:.1f}}MB</p>
                        <p>作成日: {{ image.created }}</p>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
        
        <!-- モデル管理タブ -->
        <div id="models" class="tab-content">
            <h2>📦 モデル管理</h2>
            <div id="modelList">
                {% for model in models %}
                <div class="model-item">
                    <h3>{{ model.name }}</h3>
                    <p>サイズ: {{ model.size_mb:.1f}}MB</p>
                    <p>カテゴリ: {{ model.category }}</p>
                </div>
                {% endfor %}
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
        }
        
        // 画像生成フォーム
        document.getElementById('generateForm').addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const data = Object.fromEntries(formData);
            
            fetch('/api/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            })
            .then(response => response.json())
            .then(result => {
                if (result.task_id) {
                    showGenerationStatus(result.task_id);
                } else {
                    alert('エラー: ' + result.error);
                }
            });
        });
        
        function showGenerationStatus(taskId) {
            const statusDiv = document.getElementById('generationStatus');
            statusDiv.innerHTML = '<div class="status running">🔄 画像生成中... タスクID: ' + taskId + '</div>';
            
            // 定期的にステータスをチェック
            const checkStatus = setInterval(() => {
                fetch('/api/task/' + taskId)
                .then(response => response.json())
                .then(status => {
                    if (status.status === 'completed') {
                        statusDiv.innerHTML = '<div class="status completed">✅ 画像生成完了！</div>';
                        clearInterval(checkStatus);
                        // ギャラリーを更新
                        loadGallery();
                    } else if (status.status === 'failed') {
                        statusDiv.innerHTML = '<div class="status failed">❌ 画像生成失敗: ' + status.result + '</div>';
                        clearInterval(checkStatus);
                    }
                });
            }, 2000);
        }
        
        function loadGallery() {
            fetch('/api/images')
            .then(response => response.json())
            .then(images => {
                const gallery = document.getElementById('imageGallery');
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
            });
        }
    </script>
</body>
</html>
    """
    
    with open('templates/trinity_webui.html', 'w', encoding='utf-8') as f:
        f.write(main_html)

if __name__ == '__main__':
    # テンプレート作成
    create_templates()
    
    print("🌐 Trinity WebUI 起動中...")
    print("=" * 60)
    print("📱 アクセスURL:")
    print("   http://localhost:5093")
    print("   http://163.44.120.49:5093")
    print("   http://100.93.120.33:5093")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5093, debug=False)


