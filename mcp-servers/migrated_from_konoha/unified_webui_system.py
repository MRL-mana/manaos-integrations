#!/usr/bin/env python3
"""
Trinity AI Unified WebUI System
統合WebUIシステム
"""

import os
import json
import time
import threading
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory
from typing import Dict, List, Any
import logging

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UnifiedWebUISystem:
    def __init__(self):
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'trinity_ai_secret_key'
        
        # システム状態
        self.system_status = {
            "trinity_webui": {"port": 5092, "status": "running"},
            "simple_webui": {"port": 5093, "status": "running"},
            "comfyui": {"port": 8188, "status": "starting"},
            "a1111": {"port": 7860, "status": "downloading"}
        }
        
        # 画像生成統計
        self.generation_stats = {
            "total_generated": 0,
            "successful": 0,
            "failed": 0,
            "average_time": 0,
            "last_generation": None
        }
        
        # ユーザーセッション
        self.user_sessions = {}
        
        self._setup_routes()
    
    def _setup_routes(self):
        """ルートを設定する"""
        
        @self.app.route('/')
        def index():
            return render_template('unified_dashboard.html', 
                                 system_status=self.system_status,
                                 generation_stats=self.generation_stats)
        
        @self.app.route('/api/status')
        def api_status():
            return jsonify({
                "system_status": self.system_status,
                "generation_stats": self.generation_stats,
                "timestamp": datetime.now().isoformat()
            })
        
        @self.app.route('/api/generate', methods=['POST'])
        def api_generate():
            data = request.get_json()
            prompt = data.get('prompt', '')
            style = data.get('style', 'anime')
            size = data.get('size', '512x512')
            
            # 画像生成処理（実際の実装は省略）
            result = self._generate_image(prompt, style, size)
            
            return jsonify(result)
        
        @self.app.route('/api/templates')
        def api_templates():
            return jsonify(self._get_prompt_templates())
        
        @self.app.route('/api/history')
        def api_history():
            return jsonify(self._get_generation_history())
        
        @self.app.route('/api/favorites')
        def api_favorites():
            return jsonify(self._get_favorites())
        
        @self.app.route('/api/analytics')
        def api_analytics():
            return jsonify(self._get_analytics())
        
        @self.app.route('/gallery')
        def gallery():
            return render_template('gallery.html')
        
        @self.app.route('/api/images')
        def api_images():
            """画像一覧API"""
            try:
                # 画像ディレクトリから画像を取得
                images_dir = Path("/root/trinity_workspace/generated_images")
                images = []
                
                logger.info(f"画像ディレクトリ確認: {images_dir}")
                logger.info(f"ディレクトリ存在: {images_dir.exists()}")
                
                if images_dir.exists():
                    png_files = list(images_dir.glob("*.png"))
                    logger.info(f"PNGファイル数: {len(png_files)}")
                    
                    # 評価データを読み込み
                    evaluation_file = Path("/root/trinity_workspace/generated_images/evaluations.json")
                    evaluations = {}
                    if evaluation_file.exists():
                        with open(evaluation_file, 'r', encoding='utf-8') as f:
                            evaluations = json.load(f)
                    
                    for img_file in png_files:
                        stat = img_file.stat()
                        filename = img_file.stem
                        
                        # 保存された評価があるかチェック
                        if filename in evaluations:
                            # 保存された評価を使用
                            user_rating = evaluations[filename]["rating"]
                            user_comment = evaluations[filename]["comment"]
                        else:
                            # デフォルトの評価（Manaの評価待ち）
                            user_rating = None
                            user_comment = self._extract_tool_info(filename)["comment"]
                        
                        tool_info = self._extract_tool_info(filename)
                        
                        images.append({
                            "url": f"/image/{img_file.name}",
                            "title": img_file.stem,
                            "date": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            "size": stat.st_size,
                            "tags": ["ai", "generated"],
                            "model": tool_info["model"],
                            "tool": tool_info["tool"],
                            "settings": tool_info["settings"],
                            "rating": user_rating,
                            "comment": user_comment
                        })
                    
                    # 日付順でソート（新しいものが上）
                    images.sort(key=lambda x: x["date"], reverse=True)
                
                logger.info(f"API結果: {len(images)} 枚の画像")
                return jsonify(images)
            except Exception as e:
                logger.error(f"画像一覧取得エラー: {e}")
                return jsonify([])
        
        @self.app.route('/image/<filename>')
        def serve_image(filename):
            """画像ファイルを配信"""
            try:
                images_dir = Path("/root/trinity_workspace/generated_images")
                if not images_dir.exists():
                    logger.error(f"画像ディレクトリが存在しません: {images_dir}")
                    return "Image directory not found", 404
                
                img_path = images_dir / filename
                if not img_path.exists():
                    logger.error(f"画像ファイルが存在しません: {img_path}")
                    return "Image not found", 404
                
                return send_from_directory(images_dir, filename)
            except Exception as e:
                logger.error(f"画像配信エラー: {e}")
                return "Image not found", 404
    
    def _extract_tool_info(self, filename: str) -> Dict:
        """ファイル名からツール情報を推測"""
        filename_lower = filename.lower()
        
        # ツール判定
        if "comfyui" in filename_lower:
            tool = "ComfyUI"
            model = "Stable Diffusion XL"
            settings = "ノードベースワークフロー"
        elif "civitai" in filename_lower:
            tool = "Civitai"
            model = "MajicMIX Realistic"
            settings = "リアル系モデル"
        elif "canva" in filename_lower:
            tool = "Canva AI"
            model = "Canva Magic Design"
            settings = "デザインテンプレート"
        elif "adobe" in filename_lower:
            tool = "Adobe Firefly"
            model = "Firefly 2.0"
            settings = "Adobe Creative Suite"
        elif "instagram" in filename_lower:
            tool = "Instagram AI"
            model = "Meta AI"
            settings = "ソーシャルメディア最適化"
        else:
            tool = "Trinity AI Generator"
            model = "Stable Diffusion XL"
            settings = "カスタム設定"
        
        # スタイル判定（Manaの評価はまだ未実施）
        if "corporate" in filename_lower:
            style_comment = "ビジネス向けの洗練されたデザイン。プロフェッショナルな印象を与える配色とレイアウトが素晴らしい。"
            rating = None  # Manaの評価待ち
        elif "creative" in filename_lower:
            style_comment = "創造性に富んだ独創的な作品。アーティスティックな表現力が際立っている。"
            rating = None  # Manaの評価待ち
        elif "modern" in filename_lower:
            style_comment = "モダンで洗練されたデザイン。現代的でスタイリッシュな仕上がり。"
            rating = None  # Manaの評価待ち
        elif "vintage" in filename_lower:
            style_comment = "レトロでノスタルジックな雰囲気。懐かしさを感じさせる温かみのある作品。"
            rating = None  # Manaの評価待ち
        elif "cinematic" in filename_lower:
            style_comment = "映画的でドラマチックな構図。映画のワンシーンのような美しい仕上がり。"
            rating = None  # Manaの評価待ち
        elif "hdr" in filename_lower:
            style_comment = "HDR効果による鮮やかな色彩表現。コントラストと彩度のバランスが絶妙。"
            rating = None  # Manaの評価待ち
        elif "enhanced" in filename_lower:
            style_comment = "AI強化処理により、細部まで美しく仕上げられた高品質な作品。"
            rating = None  # Manaの評価待ち
        else:
            style_comment = "バランスの取れた美しい作品。色彩と構図が完璧に調和している。"
            rating = None  # Manaの評価待ち
        
        return {
            "model": model,
            "tool": tool,
            "settings": settings,
            "rating": rating,
            "comment": style_comment
        }
    
    def _setup_routes(self):
        """ルートを設定"""
        
        @self.app.route('/')
        def index():
            return render_template('unified_dashboard.html', 
                                 system_status=self.system_status,
                                 generation_stats=self.generation_stats)
        
        @self.app.route('/api/status')
        def api_status():
            return jsonify({
                "system_status": self.system_status,
                "generation_stats": self.generation_stats,
                "timestamp": datetime.now().isoformat()
            })
        
        @self.app.route('/api/generate', methods=['POST'])
        def api_generate():
            data = request.get_json()
            prompt = data.get('prompt', '')
            style = data.get('style', 'default')
            size = data.get('size', '1024x1024')
            
            result = self._generate_image(prompt, style, size)
            return jsonify(result)
        
        @self.app.route('/api/analytics')
        def api_analytics():
            return jsonify(self._get_analytics())
        
        @self.app.route('/gallery')
        def gallery():
            return render_template('gallery.html')
        
        @self.app.route('/api/images')
        def api_images():
            """画像一覧API"""
            try:
                # 画像ディレクトリから画像を取得
                images_dir = Path("/root/trinity_workspace/generated_images")
                images = []
                
                logger.info(f"画像ディレクトリ確認: {images_dir}")
                logger.info(f"ディレクトリ存在: {images_dir.exists()}")
                
                if images_dir.exists():
                    png_files = list(images_dir.glob("*.png"))
                    logger.info(f"PNGファイル数: {len(png_files)}")
                    
                    # 評価データを読み込み
                    evaluation_file = Path("/root/trinity_workspace/generated_images/evaluations.json")
                    evaluations = {}
                    if evaluation_file.exists():
                        with open(evaluation_file, 'r', encoding='utf-8') as f:
                            evaluations = json.load(f)
                    
                    for img_file in png_files:
                        stat = img_file.stat()
                        filename = img_file.stem
                        
                        # 保存された評価があるかチェック
                        if filename in evaluations:
                            # 保存された評価を使用
                            user_rating = evaluations[filename]["rating"]
                            user_comment = evaluations[filename]["comment"]
                        else:
                            # デフォルトの評価（Manaの評価待ち）
                            user_rating = None
                            user_comment = self._extract_tool_info(filename)["comment"]
                        
                        tool_info = self._extract_tool_info(filename)
                        
                        images.append({
                            "url": f"/image/{img_file.name}",
                            "title": img_file.stem,
                            "date": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            "size": stat.st_size,
                            "tags": ["ai", "generated"],
                            "model": tool_info["model"],
                            "tool": tool_info["tool"],
                            "settings": tool_info["settings"],
                            "rating": user_rating,
                            "comment": user_comment
                        })
                    
                    # 日付順でソート（新しいものが上）
                    images.sort(key=lambda x: x["date"], reverse=True)
                
                logger.info(f"API結果: {len(images)} 枚の画像")
                return jsonify(images)
            except Exception as e:
                logger.error(f"画像一覧取得エラー: {e}")
                return jsonify([])
        
        @self.app.route('/image/<filename>')
        def serve_image(filename):
            """画像ファイルを配信"""
            try:
                images_dir = Path("/root/trinity_workspace/generated_images")
                if not images_dir.exists():
                    logger.error(f"画像ディレクトリが存在しません: {images_dir}")
                    return "Image directory not found", 404
                
                img_path = images_dir / filename
                if not img_path.exists():
                    logger.error(f"画像ファイルが存在しません: {img_path}")
                    return "Image not found", 404
                
                return send_from_directory(images_dir, filename)
            except Exception as e:
                logger.error(f"画像配信エラー: {e}")
                return "Image not found", 404
        
        @self.app.route('/api/evaluate', methods=['POST'])
        def evaluate_image():
            """画像の評価を保存"""
            try:
                data = request.get_json()
                title = data.get('title')
                rating = data.get('rating')
                comment = data.get('comment')
                
                if not all([title, rating, comment]):
                    return jsonify({"success": False, "error": "必要な情報が不足しています"})
                
                # 評価データを保存（JSONファイルに保存）
                evaluation_file = Path("/root/trinity_workspace/generated_images/evaluations.json")
                evaluations = {}
                
                if evaluation_file.exists():
                    with open(evaluation_file, 'r', encoding='utf-8') as f:
                        evaluations = json.load(f)
                
                evaluations[title] = {
                    "rating": rating,
                    "comment": comment,
                    "evaluated_at": datetime.now().isoformat()
                }
                
                with open(evaluation_file, 'w', encoding='utf-8') as f:
                    json.dump(evaluations, f, ensure_ascii=False, indent=2)
                
                logger.info(f"評価を保存: {title} - {rating}★ - {comment[:50]}...")
                
                return jsonify({"success": True})
                
            except Exception as e:
                logger.error(f"評価保存エラー: {e}")
                return jsonify({"success": False, "error": str(e)})
        
        @self.app.route('/templates')
        def templates():
            return render_template('templates.html')
        
        @self.app.route('/analytics')
        def analytics():
            return render_template('analytics.html')
    
    def _generate_image(self, prompt: str, style: str, size: str) -> Dict:
        """画像生成処理"""
        try:
            start_time = time.time()
            
            # 実際の画像生成処理は省略（既存のシステムと連携）
            # ここではシミュレーション
            
            generation_time = time.time() - start_time
            
            # 統計を更新
            self.generation_stats["total_generated"] += 1
            self.generation_stats["successful"] += 1
            self.generation_stats["last_generation"] = datetime.now().isoformat()
            
            # 平均時間を更新
            total_time = self.generation_stats["average_time"] * (self.generation_stats["successful"] - 1)
            self.generation_stats["average_time"] = (total_time + generation_time) / self.generation_stats["successful"]
            
            return {
                "success": True,
                "generation_time": generation_time,
                "filepath": f"/generated_images/image_{int(time.time())}.png",
                "prompt": prompt,
                "style": style,
                "size": size
            }
        except Exception as e:
            self.generation_stats["failed"] += 1
            return {
                "success": False,
                "error": str(e)
            }
    
    def _get_prompt_templates(self) -> Dict:
        """プロンプトテンプレートを取得する"""
        return {
            "anime": {
                "base": "a beautiful anime girl, {style}, {quality}, {mood}",
                "styles": ["kawaii", "elegant", "cute", "cool", "mysterious"],
                "quality": ["high quality", "masterpiece", "best quality", "ultra detailed"],
                "mood": ["smiling", "serene", "confident", "shy", "playful"]
            },
            "realistic": {
                "base": "a beautiful woman, {style}, {quality}, {lighting}, {mood}",
                "styles": ["professional", "casual", "elegant", "sporty", "artistic"],
                "quality": ["photorealistic", "high resolution", "detailed", "sharp"],
                "lighting": ["soft lighting", "dramatic lighting", "natural light", "studio lighting"],
                "mood": ["confident", "serene", "friendly", "mysterious", "happy"]
            },
            "fantasy": {
                "base": "a {character_type}, {magical_elements}, {setting}, {quality}",
                "character_type": ["elf", "fairy", "wizard", "knight", "princess", "mage"],
                "magical_elements": ["magical aura", "sparkling effects", "mystical energy", "enchanted"],
                "setting": ["fantasy forest", "magical castle", "enchanted garden", "mystical realm"],
                "quality": ["fantasy art", "magical", "ethereal", "mystical"]
            }
        }
    
    def _get_generation_history(self) -> List[Dict]:
        """生成履歴を取得する"""
        # 実際の実装ではデータベースから取得
        return [
            {
                "id": 1,
                "prompt": "a beautiful anime girl, kawaii style, high quality",
                "style": "anime",
                "timestamp": datetime.now().isoformat(),
                "generation_time": 3.2,
                "success": True
            },
            {
                "id": 2,
                "prompt": "a professional woman, elegant style, photorealistic",
                "style": "realistic",
                "timestamp": datetime.now().isoformat(),
                "generation_time": 4.1,
                "success": True
            }
        ]
    
    def _get_favorites(self) -> List[Dict]:
        """お気に入りを取得する"""
        return [
            {
                "id": 1,
                "prompt": "a beautiful anime girl, kawaii style, high quality",
                "category": "anime",
                "added_at": datetime.now().isoformat()
            }
        ]
    
    def _get_analytics(self) -> Dict:
        """分析データを取得する"""
        return {
            "total_generated": self.generation_stats["total_generated"],
            "success_rate": (self.generation_stats["successful"] / max(self.generation_stats["total_generated"], 1)) * 100,
            "average_generation_time": self.generation_stats["average_time"],
            "popular_styles": ["anime", "realistic", "fantasy"],
            "popular_prompts": [
                "a beautiful anime girl, kawaii style",
                "a professional woman, elegant style",
                "a fantasy character, magical"
            ],
            "system_performance": {
                "cpu_usage": 45.2,
                "memory_usage": 78.5,
                "disk_usage": 85.7
            }
        }
    
    def create_templates(self):
        """HTMLテンプレートを作成する"""
        os.makedirs('/root/trinity_workspace/tools/templates', exist_ok=True)
        
        # 統合ダッシュボード
        dashboard_html = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Trinity AI Unified Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header { text-align: center; color: white; margin-bottom: 30px; }
        .header h1 { font-size: 2.5em; margin-bottom: 10px; }
        .header p { font-size: 1.2em; opacity: 0.9; }
        .dashboard { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .card { background: rgba(255, 255, 255, 0.95); border-radius: 15px; padding: 20px; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2); }
        .card h3 { color: #333; margin-bottom: 15px; font-size: 1.3em; }
        .status-item { display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid #eee; }
        .status-item:last-child { border-bottom: none; }
        .status { padding: 5px 10px; border-radius: 20px; font-size: 0.9em; font-weight: bold; }
        .status.running { background: #d4edda; color: #155724; }
        .status.starting { background: #fff3cd; color: #856404; }
        .status.error { background: #f8d7da; color: #721c24; }
        .stats-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }
        .stat-item { text-align: center; padding: 15px; background: #f8f9fa; border-radius: 10px; }
        .stat-value { font-size: 2em; font-weight: bold; color: #667eea; }
        .stat-label { color: #666; font-size: 0.9em; }
        .nav { display: flex; justify-content: center; gap: 20px; margin-top: 30px; }
        .nav a { color: white; text-decoration: none; padding: 10px 20px; background: rgba(255, 255, 255, 0.2); border-radius: 25px; transition: all 0.3s; }
        .nav a:hover { background: rgba(255, 255, 255, 0.3); transform: translateY(-2px); }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎨 Trinity AI Unified Dashboard</h1>
            <p>統合画像生成システム</p>
        </div>
        
        <div class="dashboard">
            <div class="card">
                <h3>🔧 システム状態</h3>
                <div class="status-item">
                    <span>Trinity WebUI</span>
                    <span class="status running">稼働中</span>
                </div>
                <div class="status-item">
                    <span>Simple WebUI</span>
                    <span class="status running">稼働中</span>
                </div>
                <div class="status-item">
                    <span>ComfyUI</span>
                    <span class="status starting">起動中</span>
                </div>
                <div class="status-item">
                    <span>A1111</span>
                    <span class="status starting">ダウンロード中</span>
                </div>
            </div>
            
            <div class="card">
                <h3>📊 生成統計</h3>
                <div class="stats-grid">
                    <div class="stat-item">
                        <div class="stat-value">{{ generation_stats.total_generated }}</div>
                        <div class="stat-label">総生成数</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">{{ generation_stats.successful }}</div>
                        <div class="stat-label">成功数</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">{{ "%.1f"|format(generation_stats.average_time) }}</div>
                        <div class="stat-label">平均時間(秒)</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">{{ generation_stats.failed }}</div>
                        <div class="stat-label">失敗数</div>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <h3>🚀 クイックアクセス</h3>
                <div style="display: flex; flex-direction: column; gap: 10px;">
                    <a href="http://127.0.0.1:5092" target="_blank" style="padding: 10px; background: #667eea; color: white; text-decoration: none; border-radius: 8px; text-align: center;">🖼️ 画像ギャラリー</a>
                    <a href="http://127.0.0.1:5093" target="_blank" style="padding: 10px; background: #764ba2; color: white; text-decoration: none; border-radius: 8px; text-align: center;">🎨 画像生成</a>
                    <a href="http://127.0.0.1:8188" target="_blank" style="padding: 10px; background: #28a745; color: white; text-decoration: none; border-radius: 8px; text-align: center;">🔧 ComfyUI</a>
                    <a href="http://127.0.0.1:7860" target="_blank" style="padding: 10px; background: #ffc107; color: black; text-decoration: none; border-radius: 8px; text-align: center;">⚡ A1111</a>
                </div>
            </div>
        </div>
        
        <div class="nav">
            <a href="/gallery">🖼️ ギャラリー</a>
            <a href="/templates">📝 テンプレート</a>
            <a href="/analytics">📊 分析</a>
        </div>
    </div>
</body>
</html>
        """
        
        with open('/root/trinity_workspace/tools/templates/unified_dashboard.html', 'w', encoding='utf-8') as f:
            f.write(dashboard_html)
    
    def run(self, host='0.0.0.0', port=5094, debug=False):
        """WebUIを起動する"""
        self.create_templates()
        # テンプレートディレクトリを設定
        self.app.template_folder = '/root/trinity_workspace/tools/templates'
        logger.info(f"🚀 Trinity AI Unified WebUI System 起動中...")
        logger.info(f"   URL: http://{host}:{port}")
        self.app.run(host=host, port=port, debug=debug)

def main():
    """メイン実行関数"""
    print("🚀 Trinity AI Unified WebUI System")
    print("=" * 60)
    
    unified_system = UnifiedWebUISystem()
    unified_system.run()

if __name__ == "__main__":
    main()
