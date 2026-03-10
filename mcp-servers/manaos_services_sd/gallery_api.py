#!/usr/bin/env python3
"""
ManaOS Gallery with SD Inference API Integration
API経由で画像生成・修正・強化を実行するギャラリー
"""

from flask import Flask, render_template, request, jsonify, send_file
import requests
import os
import sqlite3
import logging

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 設定
API_BASE_URL = "http://localhost:8000"
GENERATED_IMAGES_DIR = "/mnt/storage500/generated_images"
FIXED_IMAGES_DIR = "/mnt/storage500/fixed_images"
DATABASE_PATH = "/root/gallery.db"

class GalleryAPI:
    def __init__(self):
        self.api_base_url = API_BASE_URL
        self.session = requests.Session()
        self.init_database()
    
    def init_database(self):
        """データベース初期化"""
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT UNIQUE,
                prompt TEXT,
                model TEXT,
                rating INTEGER DEFAULT 0,
                comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                file_path TEXT,
                file_type TEXT DEFAULT 'generated'
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("✅ データベース初期化完了")
    
    def generate_image(self, prompt: str, model: str = "majicmixRealistic_v7.safetensors", 
                      steps: int = 30, guidance_scale: float = 7.5, 
                      negative_prompt: str = None, mufufu_mode: bool = False) -> dict:  # type: ignore
        """画像生成"""
        try:
            # ムフフモード時のネガティブプロンプト（服を除外）
            if mufufu_mode:
                if negative_prompt is None:
                    negative_prompt = "bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry, bad feet, clothes, clothing, shirt, dress, underwear, bra, panties, swimsuit, swimwear"
                else:
                    # 既存のネガティブプロンプトに服関連を追加
                    negative_prompt += ", clothes, clothing, shirt, dress, underwear, bra, panties, swimsuit, swimwear"
            
            payload = {
                "prompt": prompt,
                "model_name": model,
                "steps": steps,
                "guidance": guidance_scale,
                "width": 512,
                "height": 512
            }
            
            # ネガティブプロンプトが指定されている場合は追加
            if negative_prompt:
                payload["negative_prompt"] = negative_prompt
            
            response = self.session.post(f"{self.api_base_url}/generate", json=payload)
            response.raise_for_status()
            
            result = response.json()
            
            # データベースに記録
            self.save_image_record(result.get('filename', ''), prompt, model)
            
            logger.info(f"✅ 画像生成完了: {result.get('filename', 'unknown')} (ムフフモード: {mufufu_mode})")
            return {"success": True, "data": result}
            
        except Exception as e:
            logger.error(f"❌ 画像生成エラー: {e}")
            return {"success": False, "error": str(e)}
    
    def inpaint_face(self, image_path: str, face_prompt: str = "beautiful face") -> dict:
        """顔修正"""
        try:
            payload = {
                "image_path": image_path,
                "face_prompt": face_prompt
            }
            
            response = self.session.post(f"{self.api_base_url}/inpaint", json=payload)
            response.raise_for_status()
            
            result = response.json()
            
            # データベースに記録
            self.save_image_record(result.get('output_path', ''), face_prompt, "face_inpaint", "fixed")
            
            logger.info(f"✅ 顔修正完了: {result.get('output_path', 'unknown')}")
            return {"success": True, "data": result}
            
        except Exception as e:
            logger.error(f"❌ 顔修正エラー: {e}")
            return {"success": False, "error": str(e)}
    
    def enhance_adult(self, image_path: str, enhancement_type: str = "sexy") -> dict:
        """アダルト強化"""
        try:
            payload = {
                "image_path": image_path,
                "enhancement_type": enhancement_type
            }
            
            response = self.session.post(f"{self.api_base_url}/enhance", json=payload)
            response.raise_for_status()
            
            result = response.json()
            
            # データベースに記録
            self.save_image_record(result.get('output_path', ''), enhancement_type, "adult_enhance", "fixed")
            
            logger.info(f"✅ アダルト強化完了: {result.get('output_path', 'unknown')}")
            return {"success": True, "data": result}
            
        except Exception as e:
            logger.error(f"❌ アダルト強化エラー: {e}")
            return {"success": False, "error": str(e)}
    
    def get_models(self) -> dict:
        """利用可能モデル一覧取得"""
        try:
            response = self.session.get(f"{self.api_base_url}/models")
            response.raise_for_status()
            
            models = response.json()
            logger.info(f"✅ モデル一覧取得: {len(models)}個")
            return {"success": True, "data": models}
            
        except Exception as e:
            logger.error(f"❌ モデル一覧取得エラー: {e}")
            return {"success": False, "error": str(e)}
    
    def save_image_record(self, filename: str, prompt: str, model: str, file_type: str = "generated"):
        """画像記録をデータベースに保存"""
        try:
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()
            
            file_path = os.path.join(GENERATED_IMAGES_DIR if file_type == "generated" else FIXED_IMAGES_DIR, filename)
            
            cursor.execute('''
                INSERT OR REPLACE INTO images (filename, prompt, model, file_path, file_type)
                VALUES (?, ?, ?, ?, ?)
            ''', (filename, prompt, model, file_path, file_type))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ データベース保存エラー: {e}")
    
    def get_images(self, limit: int = 50) -> list:
        """画像一覧取得"""
        try:
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, filename, prompt, model, rating, comment, created_at, file_path, file_type
                FROM images
                ORDER BY created_at DESC
                LIMIT ?
            ''', (limit,))
            
            images = []
            for row in cursor.fetchall():
                images.append({
                    "id": row[0],
                    "filename": row[1],
                    "prompt": row[2],
                    "model": row[3],
                    "rating": row[4],
                    "comment": row[5],
                    "created_at": row[6],
                    "file_path": row[7],
                    "file_type": row[8]
                })
            
            conn.close()
            return images
            
        except Exception as e:
            logger.error(f"❌ 画像一覧取得エラー: {e}")
            return []
    
    def update_rating(self, image_id: int, rating: int) -> bool:
        """評価更新"""
        try:
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE images SET rating = ? WHERE id = ?
            ''', (rating, image_id))
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ 評価更新: ID {image_id} -> {rating}星")
            return True
            
        except Exception as e:
            logger.error(f"❌ 評価更新エラー: {e}")
            return False
    
    def update_comment(self, image_id: int, comment: str) -> bool:
        """コメント更新"""
        try:
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE images SET comment = ? WHERE id = ?
            ''', (comment, image_id))
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ コメント更新: ID {image_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ コメント更新エラー: {e}")
            return False

# グローバルAPIインスタンス
gallery_api = GalleryAPI()

@app.route('/')
def index():
    """メインページ"""
    return render_template('gallery_api.html')

@app.route('/api/generate', methods=['POST'])
def api_generate():
    """画像生成API"""
    data = request.json
    prompt = data.get('prompt', '')
    model = data.get('model', 'majicmixRealistic_v7.safetensors')
    steps = data.get('steps', 30)
    guidance_scale = data.get('guidance_scale', 7.5)
    
    result = gallery_api.generate_image(prompt, model, steps, guidance_scale)
    return jsonify(result)

@app.route('/api/inpaint', methods=['POST'])
def api_inpaint():
    """顔修正API"""
    data = request.json
    image_path = data.get('image_path', '')
    face_prompt = data.get('face_prompt', 'beautiful face')
    
    result = gallery_api.inpaint_face(image_path, face_prompt)
    return jsonify(result)

@app.route('/api/enhance', methods=['POST'])
def api_enhance():
    """アダルト強化API"""
    data = request.json
    image_path = data.get('image_path', '')
    enhancement_type = data.get('enhancement_type', 'sexy')
    
    result = gallery_api.enhance_adult(image_path, enhancement_type)
    return jsonify(result)

@app.route('/api/models', methods=['GET'])
def api_models():
    """モデル一覧API"""
    result = gallery_api.get_models()
    return jsonify(result)

@app.route('/api/images', methods=['GET'])
def api_images():
    """画像一覧API"""
    limit = request.args.get('limit', 50, type=int)
    images = gallery_api.get_images(limit)
    return jsonify({"images": images})

@app.route('/api/rating', methods=['POST'])
def api_rating():
    """評価更新API"""
    data = request.json
    image_id = data.get('id')
    rating = data.get('rating')
    
    success = gallery_api.update_rating(image_id, rating)
    return jsonify({"success": success})

@app.route('/api/comment', methods=['POST'])
def api_comment():
    """コメント更新API"""
    data = request.json
    image_id = data.get('id')
    comment = data.get('comment')
    
    success = gallery_api.update_comment(image_id, comment)
    return jsonify({"success": success})

@app.route('/images/<path:filename>')
def serve_image(filename):
    """画像ファイル配信"""
    # 生成画像と修正画像の両方をチェック
    generated_path = os.path.join(GENERATED_IMAGES_DIR, filename)
    fixed_path = os.path.join(FIXED_IMAGES_DIR, filename)
    
    if os.path.exists(generated_path):
        return send_file(generated_path)
    elif os.path.exists(fixed_path):
        return send_file(fixed_path)
    else:
        return "Image not found", 404

if __name__ == '__main__':
    logger.info("🎨 ManaOS Gallery with API Integration 起動中...")
    
    # API接続確認
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        if response.status_code == 200:
            logger.info("✅ SD Inference API接続成功")
        else:
            logger.error("❌ SD Inference API接続失敗")
    except Exception as e:
        logger.error(f"❌ SD Inference API接続エラー: {e}")
    
    logger.info("🌐 Gallery Server起動: http://localhost:5559")
    app.run(host="0.0.0.0", port=port, debug=os.getenv("DEBUG", "False").lower() == "true")  # type: ignore[name-defined]


