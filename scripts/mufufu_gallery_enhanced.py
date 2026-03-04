#!/usr/bin/env python3
"""
ムフフ画像生成システム - ギャラリー強化版
詳細情報表示、評価システム、学習機能付きギャラリー
"""

import os
import sys
import json
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory

# パスを追加
sys.path.append('/root/trinity_workspace/tools')

class MufufuGalleryEnhanced:
    def __init__(self):
        self.images_dir = "/root/trinity_workspace/generated_images"
        self.models_dir = "/mnt/storage500/civitai_models"
        self.db_path = "/root/mufufu_gallery.db"

        # データベース初期化
        self.init_database()

        # 生成タスク管理
        self.generation_tasks = {}
        self.task_counter = 0

    def init_database(self):
        """データベース初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 画像情報テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT UNIQUE,
                model_name TEXT,
                prompt TEXT,
                negative_prompt TEXT,
                size_preset TEXT,
                num_steps INTEGER,
                guidance_scale REAL,
                generation_time REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                file_size_mb REAL,
                image_url TEXT
            )
        ''')

        # 評価テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ratings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_id INTEGER,
                rating INTEGER CHECK(rating >= 1 AND rating <= 5),
                comment TEXT,
                mana_preference TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (image_id) REFERENCES images (id)
            )
        ''')

        # 学習データテーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS learning_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_id INTEGER,
                feature_type TEXT,
                feature_value TEXT,
                preference_score REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (image_id) REFERENCES images (id)
            )
        ''')

        conn.commit()
        conn.close()

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
                        except Exception:
                            models.append({
                                "name": model_file,
                                "filename": model_file,
                                "size_mb": os.path.getsize(os.path.join(self.models_dir, model_file)) / (1024 * 1024),
                                "category": "unknown"
                            })
        return models

    def get_gallery_images(self):
        """ギャラリー画像一覧取得（評価情報付き）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # データベースに画像がない場合は、ファイルシステムから画像を取得
        cursor.execute('SELECT COUNT(*) FROM images')
        db_count = cursor.fetchone()[0]

        if db_count == 0:
            # ファイルシステムから画像ファイルを取得
            images = []
            if os.path.exists(self.images_dir):
                # ファイルの更新日時でソート（最新順）
                image_files = []
                for filename in os.listdir(self.images_dir):
                    if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                        filepath = os.path.join(self.images_dir, filename)
                        if os.path.isfile(filepath):
                            stat = os.stat(filepath)
                            image_files.append((filename, stat.st_mtime, stat.st_size))

                # 更新日時でソート（最新順）
                image_files.sort(key=lambda x: x[1], reverse=True)

                for i, (filename, mtime, size) in enumerate(image_files[:20]):  # 最新20枚
                    # この画像の評価を取得
                    cursor.execute('''
                        SELECT AVG(rating), COUNT(*), GROUP_CONCAT(comment)
                        FROM ratings
                        WHERE image_id = ?
                    ''', (i + 1,))

                    rating_result = cursor.fetchone()
                    avg_rating = round(rating_result[0], 1) if rating_result[0] else 0
                    rating_count = rating_result[1] if rating_result[1] else 0
                    comments = rating_result[2] if rating_result[2] else ""

                    images.append({
                        "id": i + 1,
                        "filename": filename,
                        "model_name": "Unknown",
                        "prompt": "Auto-discovered image",
                        "negative_prompt": "",
                        "size_preset": "Unknown",
                        "num_steps": 0,
                        "guidance_scale": 0,
                        "generation_time": 0,
                        "created_at": datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S'),
                        "file_size_mb": round(size / (1024 * 1024), 2),
                        "image_url": f'/images/{filename.replace(" ", "%20")}',
                        "avg_rating": avg_rating,
                        "rating_count": rating_count,
                        "comments": comments
                    })
        else:
            # データベースから画像を取得
            cursor.execute('''
                SELECT
                    i.*,
                    COALESCE(AVG(r.rating), 0) as avg_rating,
                    COUNT(r.id) as rating_count,
                    GROUP_CONCAT(r.comment) as comments
                FROM images i
                LEFT JOIN ratings r ON i.id = r.image_id
                GROUP BY i.id
                ORDER BY i.created_at DESC
            ''')

            images = []
            for row in cursor.fetchall():
                images.append({
                    "id": row[0],
                    "filename": row[1],
                    "model_name": row[2],
                    "prompt": row[3],
                    "negative_prompt": row[4],
                    "size_preset": row[5],
                    "num_steps": row[6],
                    "guidance_scale": row[7],
                    "generation_time": row[8],
                    "created_at": row[9],
                    "file_size_mb": row[10],
                    "image_url": row[11],
                    "avg_rating": round(row[12], 1) if row[12] else 0,
                    "rating_count": row[13],
                    "comments": row[14] if row[14] else ""
                })

        conn.close()
        return images

    def add_image_to_db(self, filename, model_name, prompt, negative_prompt,
                       size_preset, num_steps, guidance_scale, generation_time):
        """画像情報をデータベースに追加"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        filepath = os.path.join(self.images_dir, filename)
        file_size_mb = os.path.getsize(filepath) / (1024 * 1024) if os.path.exists(filepath) else 0

        cursor.execute('''
            INSERT INTO images (filename, model_name, prompt, negative_prompt,
                              size_preset, num_steps, guidance_scale, generation_time,
                              file_size_mb, image_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (filename, model_name, prompt, negative_prompt, size_preset,
              num_steps, guidance_scale, generation_time, file_size_mb,
              f'/images/{filename.replace(" ", "%20")}'))

        conn.commit()
        conn.close()

    def add_rating(self, image_id, rating, comment, mana_preference):
        """評価を追加"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # ファイルシステムベースの画像の場合は、一時的なIDを使用
        # 実際のデータベースに画像情報がない場合の処理
        cursor.execute('''
            INSERT INTO ratings (image_id, rating, comment, mana_preference)
            VALUES (?, ?, ?, ?)
        ''', (image_id, rating, comment, mana_preference))

        conn.commit()
        conn.close()

        return True

    def get_learning_insights(self):
        """学習データから洞察を取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 高評価画像の特徴を分析
        cursor.execute('''
            SELECT
                i.model_name,
                i.prompt,
                i.size_preset,
                AVG(r.rating) as avg_rating,
                COUNT(r.id) as rating_count
            FROM images i
            JOIN ratings r ON i.id = r.image_id
            WHERE r.rating >= 4
            GROUP BY i.model_name, i.prompt, i.size_preset
            ORDER BY avg_rating DESC
            LIMIT 10
        ''')

        insights = cursor.fetchall()
        conn.close()

        return insights

# Flaskアプリケーション
app = Flask(__name__)
gallery = MufufuGalleryEnhanced()

@app.route('/')
def index():
    """メインページ"""
    models = gallery.get_available_models()
    images = gallery.get_gallery_images()[:10]  # 最新10枚

    return render_template('mufufu_gallery_enhanced.html',
                         models=models,
                         images=images,
                         gallery=gallery)

@app.route('/api/models')
def api_models():
    """モデル一覧API"""
    return jsonify(gallery.get_available_models())

@app.route('/api/images')
def api_images():
    """画像一覧API"""
    return jsonify(gallery.get_gallery_images())

@app.route('/api/rate', methods=['POST'])
def api_rate():
    """評価API"""
    data = request.get_json()

    image_id = data.get('image_id')
    rating = data.get('rating')
    comment = data.get('comment', '')
    mana_preference = data.get('mana_preference', '')

    if not image_id or not rating:
        return jsonify({"error": "画像IDと評価が必要です"}), 400

    gallery.add_rating(image_id, rating, comment, mana_preference)

    return jsonify({"status": "success"})

@app.route('/api/insights')
def api_insights():
    """学習洞察API"""
    insights = gallery.get_learning_insights()
    return jsonify(insights)

@app.route('/api/clothing/change', methods=['POST'])
def api_clothing_change():
    """服変更API"""
    try:
        data = request.get_json()
        image_id = data.get('image_id')
        clothing_style = data.get('clothing_style', 'casual')
        clothing_weight = data.get('clothing_weight', 0.5)  # -1.0 to 1.0

        # 画像情報を取得
        images = gallery.get_gallery_images()
        target_image = None
        for img in images:
            if img['id'] == image_id:
                target_image = img
                break

        if not target_image:
            return jsonify({'status': 'error', 'message': '画像が見つかりません'})

        # 服変更用プロンプトを生成
        clothing_prompts = {
            'casual': 'casual clothes, everyday outfit, comfortable clothing',
            'formal': 'formal dress, business suit, elegant attire',
            'party': 'party dress, festive outfit, glamorous clothing',
            'sporty': 'sportswear, athletic clothes, active wear',
            'vintage': 'vintage clothing, retro style, classic fashion',
            'summer': 'summer dress, light clothing, beach wear',
            'winter': 'winter coat, warm clothing, cozy outfit'
        }

        base_prompt = target_image.get('prompt', 'beautiful girl')
        clothing_prompt = clothing_prompts.get(clothing_style, clothing_prompts['casual'])

        # ClothingAdjuster3を使用した新しいプロンプト
        new_prompt = f"{base_prompt}, {clothing_prompt}"

        # 画像生成（実際の実装では、ここで新しい画像を生成）
        result = {
            'status': 'success',
            'message': '服変更リクエストを受け付けました',
            'original_image': target_image['image_url'],
            'new_prompt': new_prompt,
            'clothing_style': clothing_style,
            'clothing_weight': clothing_weight
        }

        return jsonify(result)

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/clothing/styles')
def api_clothing_styles():
    """服スタイル一覧API"""
    styles = [
        {'id': 'casual', 'name': 'カジュアル', 'description': '普段着、リラックスした服装'},
        {'id': 'formal', 'name': 'フォーマル', 'description': '正装、ビジネススーツ'},
        {'id': 'party', 'name': 'パーティー', 'description': 'パーティードレス、華やかな服装'},
        {'id': 'sporty', 'name': 'スポーティー', 'description': 'スポーツウェア、アクティブな服装'},
        {'id': 'vintage', 'name': 'ヴィンテージ', 'description': 'レトロスタイル、クラシックな服装'},
        {'id': 'summer', 'name': 'サマー', 'description': '夏服、軽やかな服装'},
        {'id': 'winter', 'name': 'ウィンター', 'description': '冬服、暖かい服装'}
    ]
    return jsonify(styles)

@app.route('/images/<filename>')
def serve_image(filename):
    """画像配信"""
    return send_from_directory(gallery.images_dir, filename)

@app.route('/gallery')
def gallery_page():
    """ギャラリーページ"""
    images = gallery.get_gallery_images()
    return render_template('gallery.html', images=images, gallery=gallery)

@app.route('/admin')
def admin():
    """管理ページ"""
    return render_template('admin.html',
                         tasks=gallery.generation_tasks,
                         models=gallery.get_available_models(),
                         gallery=gallery)

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
    <title>🎨 ムフフ画像生成ギャラリー - 強化版</title>
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
        .gallery {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 30px;
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
            height: 250px;
            object-fit: cover;
        }
        .image-info {
            padding: 15px;
            background: #f8f9fa;
        }
        .image-title {
            font-weight: bold;
            margin-bottom: 10px;
            color: #333;
        }
        .image-details {
            font-size: 12px;
            color: #666;
            margin-bottom: 5px;
        }
        .rating-section {
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid #eee;
        }
        .rating-stars {
            display: flex;
            gap: 5px;
            margin-bottom: 10px;
        }
        .star {
            cursor: pointer;
            font-size: 20px;
            color: #ddd;
            transition: color 0.3s ease;
        }
        .star.active {
            color: #ffd700;
        }
        .rating-input {
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 5px;
            margin-bottom: 10px;
            font-size: 12px;
        }
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            font-size: 12px;
            cursor: pointer;
            transition: transform 0.3s ease;
        }
        .btn:hover {
            transform: translateY(-2px);
        }
        .insights-section {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin-top: 30px;
        }
        .insight-item {
            background: white;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 10px;
            border-left: 4px solid #667eea;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎨 ムフフ画像生成ギャラリー - 強化版</h1>

        <div class="tabs">
            <div class="tab active" onclick="showTab('gallery')">ギャラリー</div>
            <div class="tab" onclick="showTab('insights')">学習洞察</div>
            <div class="tab" onclick="showTab('admin')">管理</div>
        </div>

        <!-- ギャラリータブ -->
        <div id="gallery" class="tab-content active">
            <h2>🖼️ 生成された画像</h2>
            <div class="gallery" id="imageGallery">
                {% for image in images %}
                <div class="image-card">
                    <img src="{{ image.image_url }}" alt="{{ image.filename }}">
                    <div class="image-info">
                        <div class="image-title">{{ image.filename }}</div>
                        <div class="image-details">
                            <strong>モデル:</strong> {{ image.model_name }}<br>
                            <strong>サイズ:</strong> {{ image.size_preset }}<br>
                            <strong>ステップ数:</strong> {{ image.num_steps }}<br>
                            <strong>ガイダンス:</strong> {{ image.guidance_scale }}<br>
                            <strong>生成時間:</strong> {{ image.generation_time }}秒<br>
                            <strong>ファイルサイズ:</strong> {{ image.file_size_mb }}MB<br>
                            <strong>作成日:</strong> {{ image.created_at }}
                        </div>
                        <div class="rating-section">
                            <div class="rating-stars" data-image-id="{{ image.id }}">
                                <span class="star" data-rating="1">⭐</span>
                                <span class="star" data-rating="2">⭐</span>
                                <span class="star" data-rating="3">⭐</span>
                                <span class="star" data-rating="4">⭐</span>
                                <span class="star" data-rating="5">⭐</span>
                                <span style="margin-left: 10px; font-size: 14px;">
                                    平均: {{ image.avg_rating }} ({{ image.rating_count }}件)
                                </span>
                            </div>
                            <input type="text" class="rating-input" placeholder="コメントを入力..." data-image-id="{{ image.id }}">
                            <input type="text" class="rating-input" placeholder="マナの好みを入力..." data-image-id="{{ image.id }}">
                            <button class="btn" onclick="submitRating({{ image.id }})">評価を送信</button>
                        </div>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>

        <!-- 学習洞察タブ -->
        <div id="insights" class="tab-content">
            <h2>🧠 学習洞察</h2>
            <div class="insights-section">
                <h3>高評価画像の特徴</h3>
                <div id="insightsList">
                    <p>データを読み込み中...</p>
                </div>
            </div>
        </div>

        <!-- 管理タブ -->
        <div id="admin" class="tab-content">
            <h2>⚙️ 管理</h2>
            <div class="insights-section">
                <h3>システム情報</h3>
                <div class="insight-item">
                    <strong>データベース:</strong> {{ gallery.db_path }}
                </div>
                <div class="insight-item">
                    <strong>画像ディレクトリ:</strong> {{ gallery.images_dir }}
                </div>
                <div class="insight-item">
                    <strong>モデルディレクトリ:</strong> {{ gallery.models_dir }}
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

            // 学習洞察タブが選択されたらデータを読み込み
            if (tabName === 'insights') {
                loadInsights();
            }
        }

        // 星評価のクリック処理
        document.querySelectorAll('.rating-stars').forEach(stars => {
            stars.addEventListener('click', function(e) {
                if (e.target.classList.contains('star')) {
                    const rating = parseInt(e.target.dataset.rating);
                    const stars = this.querySelectorAll('.star');

                    // 星を更新
                    stars.forEach((star, index) => {
                        if (index < rating) {
                            star.classList.add('active');
                        } else {
                            star.classList.remove('active');
                        }
                    });

                    // 評価を保存
                    this.dataset.currentRating = rating;
                }
            });
        });

        function submitRating(imageId) {
            const stars = document.querySelector(`[data-image-id="${imageId}"]`);
            const rating = stars.dataset.currentRating;
            const comment = document.querySelector(`input[data-image-id="${imageId}"]`).value;
            const manaPreference = document.querySelectorAll(`input[data-image-id="${imageId}"]`)[1].value;

            if (!rating) {
                alert('評価を選択してください');
                return;
            }

            fetch('/api/rate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    image_id: imageId,
                    rating: parseInt(rating),
                    comment: comment,
                    mana_preference: manaPreference
                })
            })
            .then(response => response.json())
            .then(result => {
                if (result.status === 'success') {
                    alert('評価を送信しました！');
                    location.reload();
                } else {
                    alert('エラー: ' + result.error);
                }
            });
        }

        function loadInsights() {
            fetch('/api/insights')
            .then(response => response.json())
            .then(insights => {
                const insightsList = document.getElementById('insightsList');
                if (insights.length === 0) {
                    insightsList.innerHTML = '<p>まだ評価データがありません</p>';
                    return;
                }

                insightsList.innerHTML = insights.map(insight => `
                    <div class="insight-item">
                        <strong>モデル:</strong> ${insight[0]}<br>
                        <strong>プロンプト:</strong> ${insight[1]}<br>
                        <strong>サイズ:</strong> ${insight[2]}<br>
                        <strong>平均評価:</strong> ${insight[3]} (${insight[4]}件)
                    </div>
                `).join('');
            });
        }
    </script>
</body>
</html>
    """

    with open('templates/mufufu_gallery_enhanced.html', 'w', encoding='utf-8') as f:
        f.write(main_html)

if __name__ == '__main__':
    # テンプレート作成
    create_templates()

    print("🌐 ムフフ画像生成ギャラリー - 強化版 起動中...")
    print("=" * 60)
    print("📱 アクセスURL:")
    print("   http://localhost:5100")
    print("   http://163.44.120.49:5100")
    print("   http://100.93.120.33:5100")
    print("=" * 60)

    app.run(host='0.0.0.0', port=5100, debug=os.getenv("DEBUG", "False").lower() == "true")






