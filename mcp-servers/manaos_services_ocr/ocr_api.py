#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
統合OCR API
3つのエンジン（Tesseract, EasyOCR, Google Vision API）を統合
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import sys
import json
import time
from datetime import datetime
from werkzeug.utils import secure_filename
import logging
from pathlib import Path

# ベースディレクトリを取得（スクリプトの場所を基準）
BASE_DIR = Path(__file__).parent
LOGS_DIR = BASE_DIR.parent / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

# エンジンインポート
sys.path.insert(0, str(BASE_DIR))
from engines.tesseract_engine import TesseractEngine
from engines.easyocr_engine import EasyOCREngine
try:
    from engines.vision_api_engine import VisionAPIEngine
except ImportError:
    VisionAPIEngine = None  # Google Cloud Vision APIが利用できない場合

app = Flask(__name__)
CORS(app)

# 設定
UPLOAD_FOLDER = str(BASE_DIR / 'uploads')
RESULTS_FOLDER = str(BASE_DIR / 'results')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'webp'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

# ログ設定
logging.basicConfig(
    filename=str(LOGS_DIR / 'ocr_system.log'),
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# エンジン初期化
print("[OCR API] Initializing engines...")
engines = {}

try:
    engines['tesseract'] = TesseractEngine()
    logger.info("Tesseract engine initialized")
except Exception as e:
    logger.error(f"Tesseract initialization failed: {e}")

try:
    engines['easyocr'] = EasyOCREngine()
    logger.info("EasyOCR engine initialized")
except Exception as e:
    logger.error(f"EasyOCR initialization failed: {e}")

try:
    # 認証情報があれば使用
    cred_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    engines['vision_api'] = VisionAPIEngine(cred_path)
    logger.info("Vision API engine initialized")
except Exception as e:
    logger.error(f"Vision API initialization failed: {e}")

print(f"[OCR API] {len(engines)} engines ready: {list(engines.keys())}")

# 統計情報
stats = {
    'total_requests': 0,
    'by_engine': {name: 0 for name in engines.keys()},
    'success_count': 0,
    'error_count': 0,
    'total_processing_time': 0.0
}

def allowed_file(filename):
    """ファイル拡張子チェック"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_result(result: dict, image_filename: str):
    """結果をJSONファイルに保存"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    result_filename = f"{timestamp}_{image_filename}.json"
    result_path = os.path.join(RESULTS_FOLDER, result_filename)
    
    with open(result_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    return result_filename

@app.route('/')
def index():
    """ホーム"""
    return jsonify({
        'service': 'Mana OCR System',
        'version': '1.0.0',
        'engines': list(engines.keys()),
        'endpoints': {
            '/': 'This page',
            '/api/engines': 'Get engine info',
            '/api/extract': 'Extract text from image (POST)',
            '/api/compare': 'Compare all engines (POST)',
            '/api/stats': 'Get statistics',
            '/dashboard': 'Web dashboard'
        }
    })

@app.route('/api/engines')
def get_engines():
    """エンジン情報取得"""
    engine_info = {}
    
    for name, engine in engines.items():
        try:
            engine_info[name] = engine.get_info()
        except Exception as e:
            engine_info[name] = {'error': str(e)}
    
    return jsonify(engine_info)

@app.route('/api/extract', methods=['POST'])
def extract_text():
    """
    テキスト抽出API
    
    Parameters:
        - file: 画像ファイル (required)
        - engine: エンジン名 (optional, default: tesseract)
                 options: tesseract, easyocr, vision_api
        - lang: 言語 (optional, default: jpn+eng for tesseract)
    """
    stats['total_requests'] += 1
    
    # ファイルチェック
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': f'Invalid file type. Allowed: {ALLOWED_EXTENSIONS}'}), 400
    
    # エンジン選択
    engine_name = request.form.get('engine', 'tesseract').lower()
    
    if engine_name not in engines:
        return jsonify({
            'error': f'Invalid engine. Available: {list(engines.keys())}'
        }), 400
    
    # ファイル保存
    filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{timestamp}_{filename}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    logger.info(f"Processing {filename} with {engine_name}")
    
    # OCR実行
    try:
        engine = engines[engine_name]
        
        # エンジン別パラメータ
        if engine_name == 'tesseract':
            lang = request.form.get('lang', 'jpn+eng')
            result = engine.extract_text(filepath, lang=lang)
        else:
            result = engine.extract_text(filepath)
        
        # 統計更新
        stats['by_engine'][engine_name] += 1
        
        if result['success']:
            stats['success_count'] += 1
        else:
            stats['error_count'] += 1
        
        stats['total_processing_time'] += result.get('processing_time', 0)
        
        # 結果保存
        result['image_filename'] = filename
        result['timestamp'] = datetime.now().isoformat()
        result_filename = save_result(result, filename)
        result['result_filename'] = result_filename
        
        logger.info(f"Completed {filename}: success={result['success']}")
        
        return jsonify(result)
        
    except Exception as e:
        stats['error_count'] += 1
        logger.error(f"Error processing {filename}: {e}")
        
        return jsonify({
            'success': False,
            'error': str(e),
            'engine': engine_name
        }), 500

@app.route('/api/compare', methods=['POST'])
def compare_engines():
    """
    全エンジン比較
    同じ画像を3つのエンジンで処理して比較
    """
    stats['total_requests'] += 1
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file'}), 400
    
    # ファイル保存
    filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{timestamp}_{filename}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    logger.info(f"Comparing engines for {filename}")
    
    # 全エンジンで実行
    results = {}
    
    for engine_name, engine in engines.items():
        try:
            if engine_name == 'tesseract':
                result = engine.extract_text(filepath, lang='jpn+eng')
            else:
                result = engine.extract_text(filepath)
            
            results[engine_name] = result
            stats['by_engine'][engine_name] += 1
            
            if result['success']:
                stats['success_count'] += 1
            else:
                stats['error_count'] += 1
            
        except Exception as e:
            results[engine_name] = {
                'success': False,
                'error': str(e)
            }
            stats['error_count'] += 1
    
    # 比較結果
    comparison = {
        'image_filename': filename,
        'timestamp': datetime.now().isoformat(),
        'results': results,
        'summary': {
            'fastest': min(
                [(name, r.get('processing_time', float('inf'))) for name, r in results.items() if r.get('success')],
                key=lambda x: x[1],
                default=(None, None)
            )[0],
            'most_confident': max(
                [(name, r.get('confidence', 0)) for name, r in results.items() if r.get('success')],
                key=lambda x: x[1],
                default=(None, None)
            )[0],
            'longest_text': max(
                [(name, r.get('char_count', 0)) for name, r in results.items() if r.get('success')],
                key=lambda x: x[1],
                default=(None, None)
            )[0]
        }
    }
    
    # 結果保存
    result_filename = save_result(comparison, filename)
    comparison['result_filename'] = result_filename
    
    logger.info(f"Comparison completed for {filename}")
    
    return jsonify(comparison)

@app.route('/api/stats')
def get_stats():
    """統計情報取得"""
    avg_time = stats['total_processing_time'] / stats['total_requests'] if stats['total_requests'] > 0 else 0
    
    return jsonify({
        'total_requests': stats['total_requests'],
        'success_count': stats['success_count'],
        'error_count': stats['error_count'],
        'success_rate': f"{(stats['success_count'] / stats['total_requests'] * 100):.1f}%" if stats['total_requests'] > 0 else '0%',
        'by_engine': stats['by_engine'],
        'total_processing_time': f"{stats['total_processing_time']:.2f}s",
        'avg_processing_time': f"{avg_time:.2f}s",
        'uptime': time.time()
    })

@app.route('/dashboard')
def dashboard():
    """ダッシュボード（後で実装）"""
    return send_from_directory(str(BASE_DIR), 'dashboard.html')

if __name__ == '__main__':
    # ディレクトリ作成
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(RESULTS_FOLDER, exist_ok=True)
    
    print("=" * 60)
    print("🔍 Mana OCR System API")
    print("=" * 60)
    print(f"Engines: {list(engines.keys())}")
    print("Port: 5010")
    print("Dashboard: http://localhost:5010/dashboard")
    print("=" * 60)
    
    port = int(os.getenv("OCR_API_PORT", "9409"))
    app.run(host='0.0.0.0', port=port, debug=os.getenv("DEBUG", "False").lower() == "true")

