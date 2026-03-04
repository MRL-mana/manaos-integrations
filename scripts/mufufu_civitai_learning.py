#!/usr/bin/env python3
"""
ムフフ画像生成システム - CivitAI学習版
CivitAIのいいねしたモデルからマナの好みを学習するシステム
"""

import os
import sys
import json
import sqlite3
import requests
from flask import Flask, render_template, jsonify

# パスを追加
sys.path.append('/root/trinity_workspace/tools')

class MufufuCivitaiLearning:
    def __init__(self):
        self.images_dir = "/root/trinity_workspace/generated_images"
        self.models_dir = "/mnt/storage500/civitai_models"
        self.db_path = "/root/mufufu_civitai_learning.db"
        
        # CivitAI API設定
        self.civitai_api_key = os.getenv('CIVITAI_API_KEY', '')
        self.civitai_base_url = "https://civitai.com/api/v1"
        
        # データベース初期化
        self.init_database()
        
        # マナの好み分析
        self.mana_preferences = {
            "preferred_models": [],
            "preferred_tags": [],
            "preferred_styles": [],
            "preferred_artists": []
        }
    
    def init_database(self):
        """データベース初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # CivitAIモデル情報テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS civitai_models (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_id INTEGER UNIQUE,
                name TEXT,
                description TEXT,
                tags TEXT,
                category TEXT,
                download_count INTEGER,
                rating REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # マナのいいねテーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mana_favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_id INTEGER,
                favorite_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (model_id) REFERENCES civitai_models (model_id)
            )
        ''')
        
        # 学習データテーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS learning_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_id INTEGER,
                feature_type TEXT,
                feature_value TEXT,
                preference_score REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (model_id) REFERENCES civitai_models (model_id)
            )
        ''')
        
        # 生成画像テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS generated_images (
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
                image_url TEXT,
                mana_rating INTEGER,
                mana_comment TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def fetch_civitai_favorites(self):
        """CivitAIからマナのいいねしたモデルを取得"""
        if not self.civitai_api_key:
            print("❌ CivitAI APIキーが設定されていません")
            return []
        
        headers = {
            "Authorization": f"Bearer {self.civitai_api_key}"
        }
        
        try:
            # いいねしたモデルを取得
            response = requests.get(
                f"{self.civitai_base_url}/models",
                headers=headers,
                params={
                    "favorites": "true",
                    "limit": 100,
                    "sort": "Highest Rated"
                }
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
    
    def analyze_mana_preferences(self):
        """マナの好みを分析"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # いいねしたモデルの特徴を分析
        cursor.execute('''
            SELECT 
                cm.name,
                cm.tags,
                cm.category,
                cm.rating,
                cm.download_count
            FROM civitai_models cm
            JOIN mana_favorites mf ON cm.model_id = mf.model_id
            ORDER BY cm.rating DESC
        ''')
        
        favorites = cursor.fetchall()
        
        # タグ分析
        tag_counts = {}
        category_counts = {}
        
        for model in favorites:
            name, tags, category, rating, downloads = model
            
            # タグを解析
            if tags:
                try:
                    tag_list = json.loads(tags)
                    for tag in tag_list:
                        if tag in tag_counts:
                            tag_counts[tag] += 1
                        else:
                            tag_counts[tag] = 1
                except Exception:
                    pass
            
            # カテゴリを解析
            if category:
                if category in category_counts:
                    category_counts[category] += 1
                else:
                    category_counts[category] = 1
        
        # マナの好みを更新
        self.mana_preferences["preferred_tags"] = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:20]
        self.mana_preferences["preferred_models"] = [model[0] for model in favorites[:10]]
        self.mana_preferences["preferred_styles"] = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
        
        conn.close()
        
        return self.mana_preferences
    
    def generate_mana_preference_prompt(self):
        """マナの好みに基づいたプロンプト生成"""
        preferences = self.analyze_mana_preferences()
        
        # 高評価タグを取得
        top_tags = [tag for tag, count in preferences["preferred_tags"][:10]]
        
        # プロンプト生成
        prompt_base = "beautiful girl, high quality, detailed"
        
        if top_tags:
            prompt_base += f", {', '.join(top_tags[:5])}"
        
        return prompt_base
    
    def get_mana_recommendations(self):
        """マナの好みに基づいた推奨設定"""
        preferences = self.analyze_mana_preferences()
        
        recommendations = {
            "prompt_suggestions": [],
            "model_suggestions": [],
            "style_suggestions": []
        }
        
        # プロンプト提案
        for tag, count in preferences["preferred_tags"][:5]:
            recommendations["prompt_suggestions"].append({
                "tag": tag,
                "count": count,
                "prompt": f"beautiful girl, {tag}, high quality, detailed"
            })
        
        # モデル提案
        for model in preferences["preferred_models"][:5]:
            recommendations["model_suggestions"].append({
                "name": model,
                "reason": "マナがいいねしたモデル"
            })
        
        # スタイル提案
        for style, count in preferences["preferred_styles"][:5]:
            recommendations["style_suggestions"].append({
                "style": style,
                "count": count,
                "reason": f"マナが{count}回いいねしたスタイル"
            })
        
        return recommendations
    
    def save_civitai_model(self, model_data):
        """CivitAIモデル情報を保存"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO civitai_models 
            (model_id, name, description, tags, category, download_count, rating)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            model_data.get('id'),
            model_data.get('name'),
            model_data.get('description'),
            json.dumps(model_data.get('tags', [])),
            model_data.get('category'),
            model_data.get('downloadCount'),
            model_data.get('rating')
        ))
        
        conn.commit()
        conn.close()
    
    def add_mana_favorite(self, model_id, favorite_type="like"):
        """マナのいいねを追加"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO mana_favorites (model_id, favorite_type)
            VALUES (?, ?)
        ''', (model_id, favorite_type))
        
        conn.commit()
        conn.close()
    
    def get_learning_insights(self):
        """学習洞察を取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # マナの好み分析結果
        cursor.execute('''
            SELECT 
                cm.name,
                cm.tags,
                cm.category,
                cm.rating,
                COUNT(mf.id) as favorite_count
            FROM civitai_models cm
            JOIN mana_favorites mf ON cm.model_id = mf.model_id
            GROUP BY cm.model_id
            ORDER BY favorite_count DESC, cm.rating DESC
            LIMIT 20
        ''')
        
        insights = cursor.fetchall()
        conn.close()
        
        return insights

# Flaskアプリケーション
app = Flask(__name__)
learning_system = MufufuCivitaiLearning()

@app.route('/')
def index():
    """メインページ"""
    preferences = learning_system.analyze_mana_preferences()
    recommendations = learning_system.get_mana_recommendations()
    insights = learning_system.get_learning_insights()
    
    return render_template('mufufu_civitai_learning.html', 
                         preferences=preferences,
                         recommendations=recommendations,
                         insights=insights)

@app.route('/api/fetch_favorites')
def api_fetch_favorites():
    """CivitAIいいね取得API"""
    favorites = learning_system.fetch_civitai_favorites()
    
    # データベースに保存
    for model in favorites:
        learning_system.save_civitai_model(model)
        learning_system.add_mana_favorite(model.get('id'), 'like')
    
    return jsonify({"status": "success", "count": len(favorites)})

@app.route('/api/preferences')
def api_preferences():
    """マナの好みAPI"""
    preferences = learning_system.analyze_mana_preferences()
    return jsonify(preferences)

@app.route('/api/recommendations')
def api_recommendations():
    """推奨設定API"""
    recommendations = learning_system.get_mana_recommendations()
    return jsonify(recommendations)

@app.route('/api/insights')
def api_insights():
    """学習洞察API"""
    insights = learning_system.get_learning_insights()
    return jsonify(insights)

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
    <title>🎨 ムフフ画像生成 - CivitAI学習版</title>
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
        .preference-card {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            border-left: 4px solid #667eea;
        }
        .tag-cloud {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 15px;
        }
        .tag {
            background: #667eea;
            color: white;
            padding: 5px 10px;
            border-radius: 15px;
            font-size: 12px;
        }
        .recommendation-item {
            background: white;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 10px;
            border-left: 4px solid #28a745;
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
        .insight-item {
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
        <h1>🎨 ムフフ画像生成 - CivitAI学習版</h1>
        
        <div class="tabs">
            <div class="tab active" onclick="showTab('preferences')">マナの好み</div>
            <div class="tab" onclick="showTab('recommendations')">推奨設定</div>
            <div class="tab" onclick="showTab('insights')">学習洞察</div>
            <div class="tab" onclick="showTab('fetch')">データ取得</div>
        </div>
        
        <!-- マナの好みタブ -->
        <div id="preferences" class="tab-content active">
            <h2>💖 マナの好み分析</h2>
            
            <div class="preference-card">
                <h3>🏆 高評価モデル</h3>
                <div class="tag-cloud">
                    {% for model in preferences.preferred_models %}
                    <div class="tag">{{ model }}</div>
                    {% endfor %}
                </div>
            </div>
            
            <div class="preference-card">
                <h3>🏷️ 好みのタグ</h3>
                <div class="tag-cloud">
                    {% for tag, count in preferences.preferred_tags %}
                    <div class="tag">{{ tag }} ({{ count }})</div>
                    {% endfor %}
                </div>
            </div>
            
            <div class="preference-card">
                <h3>🎨 好みのスタイル</h3>
                <div class="tag-cloud">
                    {% for style, count in preferences.preferred_styles %}
                    <div class="tag">{{ style }} ({{ count }})</div>
                    {% endfor %}
                </div>
            </div>
        </div>
        
        <!-- 推奨設定タブ -->
        <div id="recommendations" class="tab-content">
            <h2>💡 推奨設定</h2>
            
            <div class="preference-card">
                <h3>📝 プロンプト提案</h3>
                {% for suggestion in recommendations.prompt_suggestions %}
                <div class="recommendation-item">
                    <strong>{{ suggestion.tag }}</strong> ({{ suggestion.count }}回)<br>
                    <code>{{ suggestion.prompt }}</code>
                </div>
                {% endfor %}
            </div>
            
            <div class="preference-card">
                <h3>🤖 モデル提案</h3>
                {% for suggestion in recommendations.model_suggestions %}
                <div class="recommendation-item">
                    <strong>{{ suggestion.name }}</strong><br>
                    <small>{{ suggestion.reason }}</small>
                </div>
                {% endfor %}
            </div>
            
            <div class="preference-card">
                <h3>🎨 スタイル提案</h3>
                {% for suggestion in recommendations.style_suggestions %}
                <div class.="recommendation-item">
                    <strong>{{ suggestion.style }}</strong> ({{ suggestion.count }}回)<br>
                    <small>{{ suggestion.reason }}</small>
                </div>
                {% endfor %}
            </div>
        </div>
        
        <!-- 学習洞察タブ -->
        <div id="insights" class="tab-content">
            <h2>🧠 学習洞察</h2>
            <div class="preference-card">
                <h3>📊 分析結果</h3>
                {% for insight in insights %}
                <div class="insight-item">
                    <strong>{{ insight[0] }}</strong><br>
                    <small>カテゴリ: {{ insight[2] }} | 評価: {{ insight[3] }} | いいね: {{ insight[4] }}回</small>
                </div>
                {% endfor %}
            </div>
        </div>
        
        <!-- データ取得タブ -->
        <div id="fetch" class="tab-content">
            <h2>📥 データ取得</h2>
            <div class="preference-card">
                <h3>CivitAIからデータを取得</h3>
                <p>CivitAIのいいねしたモデルを取得して、マナの好みを分析します。</p>
                <button class="btn" onclick="fetchFavorites()">いいねデータを取得</button>
                <div id="fetchStatus"></div>
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
        
        function fetchFavorites() {
            const statusDiv = document.getElementById('fetchStatus');
            statusDiv.innerHTML = '<p>データを取得中...</p>';
            
            fetch('/api/fetch_favorites')
            .then(response => response.json())
            .then(result => {
                if (result.status === 'success') {
                    statusDiv.innerHTML = `<p>✅ ${result.count}件のデータを取得しました！</p>`;
                    setTimeout(() => {
                        location.reload();
                    }, 2000);
                } else {
                    statusDiv.innerHTML = '<p>❌ データ取得に失敗しました</p>';
                }
            })
            .catch(error => {
                statusDiv.innerHTML = '<p>❌ エラーが発生しました</p>';
            });
        }
    </script>
</body>
</html>
    """
    
    with open('templates/mufufu_civitai_learning.html', 'w', encoding='utf-8') as f:
        f.write(main_html)

if __name__ == '__main__':
    # テンプレート作成
    create_templates()
    
    print("🌐 ムフフ画像生成 - CivitAI学習版 起動中...")
    print("=" * 60)
    print("📱 アクセスURL:")
    print("   http://localhost:5095")
    print("   http://163.44.120.49:5095")
    print("   http://100.93.120.33:5095")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5095, debug=os.getenv("DEBUG", "False").lower() == "true")






