#!/usr/bin/env python3
"""
ムフフ画像生成システム - モデルダウンローダー
CivitAIからモデルをダウンロードして、使用可能性をチェックするシステム
"""

import os
import sys
import json
import sqlite3
import requests
from flask import Flask, render_template, request, jsonify
import threading

# パスを追加
sys.path.append('/root/trinity_workspace/tools')

class MufufuModelDownloader:
    def __init__(self):
        self.models_dir = "/mnt/storage500/civitai_models"
        self.downloads_dir = "/root/trinity_workspace/model_downloads"
        self.db_path = "/root/mufufu_model_downloader.db"
        
        # ディレクトリ作成
        os.makedirs(self.models_dir, exist_ok=True)
        os.makedirs(self.downloads_dir, exist_ok=True)
        
        # CivitAI API設定
        self.civitai_api_key = os.getenv('CIVITAI_API_KEY', '')
        self.civitai_base_url = "https://civitai.com/api/v1"
        
        # データベース初期化
        self.init_database()
        
        # ダウンロードタスク管理
        self.download_tasks = {}
        self.task_counter = 0
    
    def init_database(self):
        """データベース初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # モデル情報テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS models (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_id INTEGER UNIQUE,
                name TEXT,
                description TEXT,
                tags TEXT,
                category TEXT,
                download_count INTEGER,
                rating REAL,
                file_size_mb REAL,
                download_url TEXT,
                local_path TEXT,
                status TEXT DEFAULT 'available',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # ダウンロード履歴テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS download_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_id INTEGER,
                status TEXT,
                progress REAL,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (model_id) REFERENCES models (model_id)
            )
        ''')
        
        # 使用可能性チェックテーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS compatibility_check (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_id INTEGER,
                check_result TEXT,
                error_details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (model_id) REFERENCES models (model_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def search_civitai_models(self, query="", category="", limit=20):
        """CivitAIからモデルを検索"""
        headers = {
            "Authorization": f"Bearer {self.civitai_api_key}" if self.civitai_api_key else ""
        }
        
        params = {
            "limit": limit,
            "sort": "Highest Rated"
        }
        
        if query:
            params["query"] = query
        if category:
            params["category"] = category
        
        try:
            response = requests.get(
                f"{self.civitai_base_url}/models",
                headers=headers,
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("items", [])
            else:
                print(f"❌ CivitAI API エラー: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ CivitAI API 接続エラー: {str(e)}")
            return []
    
    def get_model_details(self, model_id):
        """モデルの詳細情報を取得"""
        headers = {
            "Authorization": f"Bearer {self.civitai_api_key}" if self.civitai_api_key else ""
        }
        
        try:
            response = requests.get(
                f"{self.civitai_base_url}/models/{model_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ モデル詳細取得エラー: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ モデル詳細取得エラー: {str(e)}")
            return None
    
    def download_model(self, model_id, model_name):
        """モデルをダウンロード"""
        print(f"📥 モデルダウンロード開始: {model_name}")
        
        # モデル詳細を取得
        model_details = self.get_model_details(model_id)
        if not model_details:
            return False
        
        # 最新バージョンを取得
        latest_version = model_details.get("modelVersions", [{}])[0]
        if not latest_version:
            print("❌ モデルバージョンが見つかりません")
            return False
        
        # ダウンロードURLを取得
        download_url = latest_version.get("downloadUrl")
        if not download_url:
            print("❌ ダウンロードURLが見つかりません")
            return False
        
        # ファイル名を生成
        filename = f"{model_name}_{model_id}.safetensors"
        filepath = os.path.join(self.downloads_dir, filename)
        
        try:
            # ダウンロード開始
            response = requests.get(download_url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        # 進捗表示
                        if total_size > 0:
                            progress = (downloaded_size / total_size) * 100
                            print(f"📥 ダウンロード進捗: {progress:.1f}%")
            
            print(f"✅ ダウンロード完了: {filename}")
            
            # モデル情報をデータベースに保存
            self.save_model_info(model_details, filepath)
            
            return True
            
        except Exception as e:
            print(f"❌ ダウンロードエラー: {str(e)}")
            return False
    
    def save_model_info(self, model_details, filepath):
        """モデル情報をデータベースに保存"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        model_id = model_details.get("id")
        name = model_details.get("name")
        description = model_details.get("description")
        tags = json.dumps(model_details.get("tags", []))
        category = model_details.get("category")
        download_count = model_details.get("downloadCount")
        rating = model_details.get("rating")
        
        # ファイルサイズを取得
        file_size_mb = os.path.getsize(filepath) / (1024 * 1024) if os.path.exists(filepath) else 0
        
        cursor.execute('''
            INSERT OR REPLACE INTO models 
            (model_id, name, description, tags, category, download_count, rating, file_size_mb, local_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (model_id, name, description, tags, category, download_count, rating, file_size_mb, filepath))
        
        conn.commit()
        conn.close()
    
    def check_model_compatibility(self, model_path):
        """モデルの使用可能性をチェック"""
        print(f"🔍 モデル使用可能性チェック: {model_path}")
        
        try:
            # diffusersでモデルを読み込もうとする
            from diffusers import StableDiffusionPipeline
            import torch
            
            pipeline = StableDiffusionPipeline.from_single_file(
                model_path,
                torch_dtype=torch.float32,
                use_safetensors=True
            )
            
            # CPU最適化
            pipeline = pipeline.to("cpu")
            pipeline.enable_attention_slicing()
            
            print(f"✅ モデル使用可能: {model_path}")
            return True, "使用可能"
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ モデル使用不可: {model_path}")
            print(f"   エラー: {error_msg}")
            return False, error_msg
    
    def get_available_models(self):
        """利用可能なモデル一覧取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM models ORDER BY rating DESC
        ''')
        
        models = []
        for row in cursor.fetchall():
            models.append({
                "id": row[0],
                "model_id": row[1],
                "name": row[2],
                "description": row[3],
                "tags": json.loads(row[4]) if row[4] else [],
                "category": row[5],
                "download_count": row[6],
                "rating": row[7],
                "file_size_mb": row[8],
                "download_url": row[9],
                "local_path": row[10],
                "status": row[11],
                "created_at": row[12]
            })
        
        conn.close()
        return models
    
    def get_download_history(self):
        """ダウンロード履歴取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                dh.*,
                m.name,
                m.category
            FROM download_history dh
            JOIN models m ON dh.model_id = m.model_id
            ORDER BY dh.created_at DESC
            LIMIT 50
        ''')
        
        history = []
        for row in cursor.fetchall():
            history.append({
                "id": row[0],
                "model_id": row[1],
                "status": row[2],
                "progress": row[3],
                "error_message": row[4],
                "created_at": row[5],
                "name": row[6],
                "category": row[7]
            })
        
        conn.close()
        return history
    
    def get_compatibility_check_results(self):
        """使用可能性チェック結果取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                cc.*,
                m.name,
                m.local_path
            FROM compatibility_check cc
            JOIN models m ON cc.model_id = m.model_id
            ORDER BY cc.created_at DESC
        ''')
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "id": row[0],
                "model_id": row[1],
                "check_result": row[2],
                "error_details": row[3],
                "created_at": row[4],
                "name": row[5],
                "local_path": row[6]
            })
        
        conn.close()
        return results

# Flaskアプリケーション
app = Flask(__name__)
downloader = MufufuModelDownloader()

@app.route('/')
def index():
    """メインページ"""
    models = downloader.get_available_models()
    history = downloader.get_download_history()
    compatibility = downloader.get_compatibility_check_results()
    
    return render_template('mufufu_model_downloader.html', 
                         models=models,
                         history=history,
                         compatibility=compatibility)

@app.route('/api/search')
def api_search():
    """モデル検索API"""
    query = request.args.get('query', '')
    category = request.args.get('category', '')
    limit = int(request.args.get('limit', 20))
    
    models = downloader.search_civitai_models(query, category, limit)
    return jsonify(models)

@app.route('/api/download/<int:model_id>')
def api_download(model_id):
    """モデルダウンロードAPI"""
    model_name = request.args.get('name', f'model_{model_id}')
    
    # バックグラウンドでダウンロード
    def download_task():
        success = downloader.download_model(model_id, model_name)
        return success
    
    thread = threading.Thread(target=download_task)
    thread.daemon = True
    thread.start()
    
    return jsonify({"status": "started", "message": "ダウンロードを開始しました"})

@app.route('/api/check_compatibility/<int:model_id>')
def api_check_compatibility(model_id):
    """使用可能性チェックAPI"""
    conn = sqlite3.connect(downloader.db_path)
    cursor = conn.cursor()
    
    cursor.execute('SELECT local_path FROM models WHERE model_id = ?', (model_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        local_path = result[0]
        if os.path.exists(local_path):
            compatible, error = downloader.check_model_compatibility(local_path)
            return jsonify({"compatible": compatible, "error": error})
        else:
            return jsonify({"compatible": False, "error": "ファイルが見つかりません"})
    else:
        return jsonify({"compatible": False, "error": "モデルが見つかりません"})

@app.route('/api/models')
def api_models():
    """モデル一覧API"""
    return jsonify(downloader.get_available_models())

@app.route('/api/history')
def api_history():
    """ダウンロード履歴API"""
    return jsonify(downloader.get_download_history())

@app.route('/api/compatibility')
def api_compatibility():
    """使用可能性チェック結果API"""
    return jsonify(downloader.get_compatibility_check_results())

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
    <meta name="viewport" minimum-scale=1.0">
    <title>🎨 ムフフ画像生成 - モデルダウンローダー</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
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
        .search-section {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        .search-form {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        .search-input {
            flex: 1;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
        }
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            transition: transform 0.3s ease;
        }
        .btn:hover {
            transform: translateY(-2px);
        }
        .model-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            border-left: 4px solid #667eea;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        .model-title {
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 10px;
            color: #333;
        }
        .model-info {
            font-size: 14px;
            color: #666;
            margin-bottom: 10px;
        }
        .model-tags {
            display: flex;
            flex-wrap: wrap;
            gap: 5px;
            margin-bottom: 15px;
        }
        .tag {
            background: #667eea;
            color: white;
            padding: 3px 8px;
            border-radius: 10px;
            font-size: 12px;
        }
        .model-actions {
            display: flex;
            gap: 10px;
        }
        .status {
            padding: 5px 10px;
            border-radius: 15px;
            font-size: 12px;
            font-weight: bold;
        }
        .status.available {
            background: #d4edda;
            color: #155724;
        }
        .status.unavailable {
            background: #f8d7da;
            color: #721c24;
        }
        .status.downloading {
            background: #d1ecf1;
            color: #0c5460;
        }
        .history-item {
            background: white;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 10px;
            border-left: 4px solid #28a745;
        }
        .compatibility-item {
            background: white;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 10px;
            border-left: 4px solid #ffc107;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎨 ムフフ画像生成 - モデルダウンローダー</h1>
        
        <div class="tabs">
            <div class="tab active" onclick="showTab('search')">モデル検索</div>
            <div class="tab" onclick="showTab('models')">ダウンロード済み</div>
            <div class="tab" onclick="showTab('history')">ダウンロード履歴</div>
            <div class="tab" onclick="showTab('compatibility')">使用可能性チェック</div>
        </div>
        
        <!-- モデル検索タブ -->
        <div id="search" class="tab-content active">
            <h2>🔍 モデル検索</h2>
            <div class="search-section">
                <div class="search-form">
                    <input type="text" class="search-input" id="searchQuery" placeholder="モデル名で検索...">
                    <select class="search-input" id="searchCategory">
                        <option value="">全カテゴリ</option>
                        <option value="Checkpoint">Checkpoint</option>
                        <option value="LoRA">LoRA</option>
                        <option value="TextualInversion">TextualInversion</option>
                        <option value="Hypernetwork">Hypernetwork</option>
                    </select>
                    <button class="btn" onclick="searchModels()">検索</button>
                </div>
                <div id="searchResults"></div>
            </div>
        </div>
        
        <!-- ダウンロード済みモデルタブ -->
        <div id="models" class="tab-content">
            <h2>📦 ダウンロード済みモデル</h2>
            <div id="modelsList">
                {% for model in models %}
                <div class="model-card">
                    <div class="model-title">{{ model.name }}</div>
                    <div class="model-info">
                        <strong>カテゴリ:</strong> {{ model.category }}<br>
                        <strong>評価:</strong> {{ model.rating }}<br>
                        <strong>ダウンロード数:</strong> {{ model.download_count }}<br>
                        <strong>ファイルサイズ:</strong> {{ model.file_size_mb }}MB<br>
                        <strong>ステータス:</strong> <span class="status {{ model.status }}">{{ model.status }}</span>
                    </div>
                    <div class="model-tags">
                        {% for tag in model.tags %}
                        <span class="tag">{{ tag }}</span>
                        {% endfor %}
                    </div>
                    <div class="model-actions">
                        <button class="btn" onclick="checkCompatibility({{ model.model_id }})">使用可能性チェック</button>
                        <button class="btn" onclick="viewModel({{ model.model_id }})">詳細表示</button>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
        
        <!-- ダウンロード履歴タブ -->
        <div id="history" class="{% for item in history %}
        <div class="history-item">
            <strong>{{ item.name }}</strong><br>
            <small>ステータス: {{ item.status }} | 進捗: {{ item.progress }}% | {{ item.created_at }}</small>
            {% if item.error_message %}
            <br><small style="color: red;">エラー: {{ item.error_message }}</small>
            {% endif %}
        </div>
        {% endfor %}
        </div>
        
        <!-- 使用可能性チェックタブ -->
        <div id="compatibility" class="tab-content">
            <h2>🔍 使用可能性チェック結果</h2>
            {% for item in compatibility %}
            <div class="compatibility-item">
                <strong>{{ item.name }}</strong><br>
                <small>結果: {{ item.check_result }} | {{ item.created_at }}</small>
                {% if item.error_details %}
                <br><small style="color: red;">エラー: {{ item.error_details }}</small>
                {% endif %}
            </div>
            {% endfor %}
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
        
        function searchModels() {
            const query = document.getElementById('searchQuery').value;
            const category = document.getElementById('searchCategory').value;
            
            const resultsDiv = document.getElementById('searchResults');
            resultsDiv.innerHTML = '<p>検索中...</p>';
            
            fetch(`/api/search?query=${encodeURIComponent(query)}&category=${encodeURIComponent(category)}`)
            .then(response => response.json())
            .then(models => {
                if (models.length === 0) {
                    resultsDiv.innerHTML = '<p>モデルが見つかりませんでした</p>';
                    return;
                }
                
                resultsDiv.innerHTML = models.map(model => `
                    <div class="model-card">
                        <div class="model-title">${model.name}</div>
                        <div class="model-info">
                            <strong>カテゴリ:</strong> ${model.category}<br>
                            <strong>評価:</strong> ${model.rating}<br>
                            <strong>ダウンロード数:</strong> ${model.downloadCount}<br>
                            <strong>説明:</strong> ${model.description || '説明なし'}
                        </div>
                        <div class="model-tags">
                            ${(model.tags || []).map(tag => `<span class="tag">${tag}</span>`).join('')}
                        </div>
                        <div class="model-actions">
                            <button class="btn" onclick="downloadModel(${model.id}, '${model.name}')">ダウンロード</button>
                            <button class="btn" onclick="viewModelDetails(${model.id})">詳細表示</button>
                        </div>
                    </div>
                `).join('');
            })
            .catch(error => {
                resultsDiv.innerHTML = '<p>検索エラーが発生しました</p>';
            });
        }
        
        function downloadModel(modelId, modelName) {
            fetch(`/api/download/${modelId}?name=${encodeURIComponent(modelName)}`)
            .then(response => response.json())
            .then(result => {
                alert(result.message);
                if (result.status === 'started') {
                    setTimeout(() => {
                        location.reload();
                    }, 3000);
                }
            })
            .catch(error => {
                alert('ダウンロードエラーが発生しました');
            });
        }
        
        function checkCompatibility(modelId) {
            fetch(`/api/check_compatibility/${modelId}`)
            .then(response => response.json())
            .then(result => {
                if (result.compatible) {
                    alert('✅ このモデルは使用可能です！');
                } else {
                    alert(`❌ このモデルは使用できません。\nエラー: ${result.error}`);
                }
            })
            .catch(error => {
                alert('チェックエラーが発生しました');
            });
        }
        
        function viewModel(modelId) {
            alert(`モデルID ${modelId} の詳細を表示します`);
        }
        
        function viewModelDetails(modelId) {
            alert(`モデルID ${modelId} の詳細を表示します`);
        }
    </script>
</body>
</html>
    """
    
    with open('templates/mufufu_model_downloader.html', 'w', encoding='utf-8') as f:
        f.write(main_html)

if __name__ == '__main__':
    # テンプレート作成
    create_templates()
    
    print("🌐 ムフフ画像生成 - モデルダウンローダー 起動中...")
    print("=" * 60)
    print("📱 アクセスURL:")
    print("   http://localhost:5096")
    print("   http://163.44.120.49:5096")
    print("   http://100.93.120.33:5096")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5096, debug=os.getenv("DEBUG", "False").lower() == "true")






