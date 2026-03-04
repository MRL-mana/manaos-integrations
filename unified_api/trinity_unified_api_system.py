#!/usr/bin/env python3
"""
Trinity AI Unified API System
統合APIシステム
"""

from flask import Flask, request, jsonify, send_from_directory
import os
import json
import time
import threading
from datetime import datetime
from typing import Dict, List, Any
import logging

# 既存のモジュールをインポート
from optimized_batch_generator import OptimizedBatchGenerator
from advanced_style_transfer import AdvancedStyleTransfer
from smart_prompt_templates import SmartPromptTemplates

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# グローバルインスタンス
batch_generator = None
style_transfer = None
prompt_templates = None
generation_queue = []
generation_results = {}

def initialize_components():
    """コンポーネントを初期化"""
    global batch_generator, style_transfer, prompt_templates
    
    try:
        batch_generator = OptimizedBatchGenerator()
        style_transfer = AdvancedStyleTransfer()
        prompt_templates = SmartPromptTemplates()
        
        # デフォルトモデルを読み込み
        if batch_generator.models:
            model_name = batch_generator.models[0]["name"]
            batch_generator.load_model(model_name)
            logger.info(f"✅ デフォルトモデル読み込み完了: {model_name}")
        
        logger.info("✅ 全コンポーネント初期化完了")
        return True
    except Exception as e:
        logger.error(f"❌ コンポーネント初期化エラー: {e}")
        return False

@app.route('/')
def index():
    """メインページ"""
    return jsonify({
        "service": "Trinity AI Unified API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "generate": "/api/generate",
            "batch_generate": "/api/batch_generate",
            "style_transfer": "/api/style_transfer",
            "prompt_templates": "/api/prompts",
            "history": "/api/history",
            "status": "/api/status"
        }
    })

@app.route('/api/status')
def get_status():
    """システム状態を取得"""
    if not batch_generator:
        return jsonify({"error": "システムが初期化されていません"}), 500
    
    system_status = batch_generator.get_system_status()
    
    return jsonify({
        "system": {
            "cpu_percent": system_status["cpu_percent"],
            "memory_percent": system_status["memory_percent"],
            "disk_percent": system_status["disk_percent"]
        },
        "models": {
            "loaded": batch_generator.current_model_name,
            "available": len(batch_generator.models)
        },
        "queue": {
            "pending": len(generation_queue),
            "completed": len(generation_results)
        }
    })

@app.route('/api/generate', methods=['POST'])
def generate_image():
    """単一画像生成"""
    try:
        data = request.get_json()
        prompt = data.get('prompt', 'beautiful image, high quality')
        width = data.get('width', 512)
        height = data.get('height', 512)
        steps = data.get('steps', 20)
        seed = data.get('seed', None)
        
        if not batch_generator or not batch_generator.pipeline:
            return jsonify({"error": "モデルが読み込まれていません"}), 500
        
        # 画像生成
        filepath, gen_time = batch_generator.generate_single_image(
            prompt, width, height, steps, seed
        )
        
        if filepath:
            # 履歴に保存
            prompt_templates.save_prompt_history(prompt, "api", filepath)
            
            return jsonify({
                "success": True,
                "filepath": filepath,
                "generation_time": gen_time,
                "prompt": prompt
            })
        else:
            return jsonify({"error": "画像生成に失敗しました"}), 500
            
    except Exception as e:
        logger.error(f"画像生成エラー: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/batch_generate', methods=['POST'])
def batch_generate():
    """バッチ画像生成"""
    try:
        data = request.get_json()
        prompts = data.get('prompts', [])
        width = data.get('width', 512)
        height = data.get('height', 512)
        steps = data.get('steps', 20)
        seeds = data.get('seeds', None)
        
        if not batch_generator or not batch_generator.pipeline:
            return jsonify({"error": "モデルが読み込まれていません"}), 500
        
        if not prompts:
            return jsonify({"error": "プロンプトが指定されていません"}), 400
        
        # バッチ生成
        results = batch_generator.generate_batch(prompts, width, height, steps, seeds)
        
        return jsonify({
            "success": True,
            "results": results
        })
        
    except Exception as e:
        logger.error(f"バッチ生成エラー: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/style_transfer', methods=['POST'])
def style_transfer_api():
    """スタイル転送"""
    try:
        data = request.get_json()
        image_path = data.get('image_path')
        style = data.get('style', 'oil_painting')
        intensity = data.get('intensity', 0.8)
        
        if not image_path or not os.path.exists(image_path):
            return jsonify({"error": "画像ファイルが見つかりません"}), 400
        
        # スタイル転送実行
        output_path = style_transfer.apply_artistic_style(image_path, style, intensity)
        
        if output_path:
            return jsonify({
                "success": True,
                "output_path": output_path,
                "style": style,
                "intensity": intensity
            })
        else:
            return jsonify({"error": "スタイル転送に失敗しました"}), 500
            
    except Exception as e:
        logger.error(f"スタイル転送エラー: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/prompts', methods=['GET'])
def get_prompt_templates():
    """プロンプトテンプレートを取得"""
    try:
        category = request.args.get('category')
        
        if category:
            # 特定カテゴリのテンプレート
            template = prompt_templates.get_template(category)
            return jsonify({"category": category, "template": template})
        else:
            # 全カテゴリ一覧
            with open(prompt_templates.prompts_file, 'r', encoding='utf-8') as f:
                all_templates = json.load(f)
            return jsonify({"templates": all_templates})
            
    except Exception as e:
        logger.error(f"プロンプトテンプレート取得エラー: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/prompts/generate', methods=['POST'])
def generate_prompt():
    """プロンプトを生成"""
    try:
        data = request.get_json()
        category = data.get('category', 'anime')
        custom_elements = data.get('custom_elements', [])
        quality_level = data.get('quality_level', 'high')
        
        prompt = prompt_templates.generate_prompt(category, custom_elements, quality_level)
        
        return jsonify({
            "success": True,
            "prompt": prompt,
            "category": category
        })
        
    except Exception as e:
        logger.error(f"プロンプト生成エラー: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/history', methods=['GET'])
def get_history():
    """履歴を取得"""
    try:
        limit = request.args.get('limit', 20, type=int)
        history = prompt_templates.get_prompt_history(limit)
        
        return jsonify({
            "success": True,
            "history": history
        })
        
    except Exception as e:
        logger.error(f"履歴取得エラー: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/models', methods=['GET'])
def get_models():
    """利用可能なモデル一覧を取得"""
    try:
        if not batch_generator:
            return jsonify({"error": "システムが初期化されていません"}), 500
        
        models = []
        for model in batch_generator.models:
            models.append({
                "name": model["name"],
                "size": model["size"],
                "type": model["type"],
                "description": model["description"]
            })
        
        return jsonify({
            "success": True,
            "models": models,
            "current": batch_generator.current_model_name
        })
        
    except Exception as e:
        logger.error(f"モデル一覧取得エラー: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/models/load', methods=['POST'])
def load_model():
    """モデルを読み込む"""
    try:
        data = request.get_json()
        model_name = data.get('model_name')
        
        if not model_name:
            return jsonify({"error": "モデル名が指定されていません"}), 400
        
        if not batch_generator:
            return jsonify({"error": "システムが初期化されていません"}), 500
        
        success = batch_generator.load_model(model_name)
        
        if success:
            return jsonify({
                "success": True,
                "model": model_name,
                "message": f"モデル '{model_name}' を読み込みました"
            })
        else:
            return jsonify({"error": f"モデル '{model_name}' の読み込みに失敗しました"}), 500
            
    except Exception as e:
        logger.error(f"モデル読み込みエラー: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/queue', methods=['GET'])
def get_queue():
    """生成キューを取得"""
    return jsonify({
        "success": True,
        "queue": generation_queue,
        "results": generation_results
    })

@app.route('/api/optimize', methods=['POST'])
def optimize_prompt():
    """プロンプトを最適化"""
    try:
        data = request.get_json()
        prompt = data.get('prompt')
        
        if not prompt:
            return jsonify({"error": "プロンプトが指定されていません"}), 400
        
        optimized = prompt_templates.optimize_prompt(prompt)
        analysis = prompt_templates.analyze_prompt(prompt)
        
        return jsonify({
            "success": True,
            "original": prompt,
            "optimized": optimized,
            "analysis": analysis
        })
        
    except Exception as e:
        logger.error(f"プロンプト最適化エラー: {e}")
        return jsonify({"error": str(e)}), 500

def main():
    """メイン実行関数"""
    print("🚀 Trinity AI Unified API System")
    print("=" * 50)
    
    # コンポーネント初期化
    if initialize_components():
        print("✅ システム初期化完了")
        print("🌐 APIサーバー起動中...")
        print("📍 アクセス先: http://localhost:5094")
        
        app.run(host='0.0.0.0', port=5094, debug=False)
    else:
        print("❌ システム初期化に失敗しました")

if __name__ == "__main__":
    main()
