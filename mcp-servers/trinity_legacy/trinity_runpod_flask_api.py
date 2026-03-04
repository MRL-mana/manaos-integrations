#!/usr/bin/env python3
"""
🌟 Trinity達用 RunPod GPU Flask API
Trinity達がHTTP経由でRunPod GPUを操作
"""
import os
from flask import Flask, jsonify
import requests
import logging
from datetime import datetime

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

RUNPOD_API_URL = "https://8uv33dh7cewgeq-8080.proxy.runpod.net"

@app.route('/trinity/gpu/status', methods=['GET'])
def gpu_status():
    """GPU状態取得"""
    try:
        response = requests.get(f"{RUNPOD_API_URL}/", timeout=10)
        response.raise_for_status()
        data = response.json()
        return jsonify({
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'gpu_info': data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/trinity/gpu/generate', methods=['POST'])
def generate_images():
    """GPU画像生成"""
    try:
        response = requests.post(f"{RUNPOD_API_URL}/gpu/image_generation", timeout=30)
        response.raise_for_status()
        data = response.json()
        return jsonify({
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'result': data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/trinity/gpu/learn', methods=['POST'])
def deep_learning():
    """GPU深層学習"""
    try:
        response = requests.post(f"{RUNPOD_API_URL}/gpu/deep_learning", timeout=60)
        response.raise_for_status()
        data = response.json()
        return jsonify({
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'result': data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/trinity/gpu/test', methods=['GET'])
def full_test():
    """フル統合テスト"""
    results = []
    
    # GPU状態
    try:
        r = requests.get(f"{RUNPOD_API_URL}/", timeout=10)
        results.append({'test': 'GPU状態', 'success': True, 'data': r.json()})
    except Exception as e:
        results.append({'test': 'GPU状態', 'success': False, 'error': str(e)})
    
    # 画像生成
    try:
        r = requests.post(f"{RUNPOD_API_URL}/gpu/image_generation", timeout=30)
        results.append({'test': '画像生成', 'success': True, 'data': r.json()})
    except Exception as e:
        results.append({'test': '画像生成', 'success': False, 'error': str(e)})
    
    # 深層学習
    try:
        r = requests.post(f"{RUNPOD_API_URL}/gpu/deep_learning", timeout=60)
        results.append({'test': '深層学習', 'success': True, 'data': r.json()})
    except Exception as e:
        results.append({'test': '深層学習', 'success': False, 'error': str(e)})
    
    return jsonify({
        'success': True,
        'timestamp': datetime.now().isoformat(),
        'tests': results
    })

@app.route('/trinity/health', methods=['GET'])
def health():
    """ヘルスチェック"""
    return jsonify({
        'status': 'healthy',
        'service': 'Trinity RunPod GPU API',
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    print("🚀 Trinity RunPod GPU Flask API starting on port 5009...")
    app.run(host='0.0.0.0', port=5009, debug=os.getenv("DEBUG", "False").lower() == "true")
