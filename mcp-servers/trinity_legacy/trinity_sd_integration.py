#!/usr/bin/env python3
"""
🎨 Trinity Stable Diffusion Integration
このはサーバー経由でStable Diffusion画像生成
"""
import os
from flask import Flask, request, jsonify, send_file
import requests
import base64
import time
from datetime import datetime

app = Flask(__name__)

# RunPod Stable Diffusion WebUI API
SD_API_URL = "https://8uv33dh7cewgeq-7860.proxy.runpod.net"  # ← RunPodのProxy URLに変更が必要

@app.route('/trinity/sd/status')
def sd_status():
    """Stable Diffusion WebUI状態確認"""
    try:
        response = requests.get(f"{SD_API_URL}/sdapi/v1/options", timeout=10)
        response.raise_for_status()
        return jsonify({
            'success': True,
            'status': 'online',
            'timestamp': datetime.now().isoformat(),
            'api_url': SD_API_URL
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'status': 'offline',
            'error': str(e),
            'message': 'Stable Diffusion WebUIが起動していない可能性があります'
        }), 500

@app.route('/trinity/sd/generate', methods=['POST'])
def sd_generate():
    """Stable Diffusion画像生成"""
    try:
        data = request.get_json()
        
        # デフォルト設定
        prompt = data.get('prompt', '')
        negative_prompt = data.get('negative_prompt', 'nsfw, nude, explicit, low quality, blurry')
        steps = data.get('steps', 20)
        width = data.get('width', 512)
        height = data.get('height', 768)
        cfg_scale = data.get('cfg_scale', 7)
        sampler = data.get('sampler', 'Euler a')
        
        if not prompt:
            return jsonify({'success': False, 'error': 'プロンプトが必要です'}), 400
        
        # Stable Diffusion WebUI APIリクエスト
        payload = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "steps": steps,
            "width": width,
            "height": height,
            "cfg_scale": cfg_scale,
            "sampler_name": sampler,
        }
        
        print(f"🎨 画像生成開始: {prompt[:50]}...")
        start_time = time.time()
        
        response = requests.post(
            f"{SD_API_URL}/sdapi/v1/txt2img",
            json=payload,
            timeout=120
        )
        response.raise_for_status()
        
        generation_time = time.time() - start_time
        result = response.json()
        
        # Base64画像をデコード
        if 'images' in result and len(result['images']) > 0:
            image_data = result['images'][0]
            image_id = str(int(time.time() * 1000))
            
            # 画像を一時保存（簡易実装）
            image_bytes = base64.b64decode(image_data)
            with open(f'/tmp/sd_image_{image_id}.png', 'wb') as f:
                f.write(image_bytes)
            
            print(f"✅ 画像生成完了: {generation_time:.2f}秒")
            
            return jsonify({
                'success': True,
                'timestamp': datetime.now().isoformat(),
                'image_id': image_id,
                'image_url': f'/trinity/sd/image/{image_id}',
                'prompt': prompt,
                'generation_time': f'{generation_time:.2f}秒',
                'width': width,
                'height': height
            })
        else:
            return jsonify({
                'success': False,
                'error': '画像生成失敗'
            }), 500
            
    except requests.exceptions.Timeout:
        return jsonify({
            'success': False,
            'error': 'タイムアウト（生成に時間がかかりすぎています）'
        }), 504
    except requests.exceptions.ConnectionError:
        return jsonify({
            'success': False,
            'error': 'Stable Diffusion WebUIに接続できません',
            'message': 'RunPodでWebUIを起動してください'
        }), 503
    except Exception as e:
        print(f"❌ エラー: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/trinity/sd/image/<image_id>')
def sd_get_image(image_id):
    """生成画像取得"""
    try:
        image_path = f'/tmp/sd_image_{image_id}.png'
        return send_file(image_path, mimetype='image/png')
    except Exception as e:
        return jsonify({'error': str(e)}), 404

@app.route('/trinity/sd/models')
def sd_models():
    """利用可能なモデル一覧"""
    try:
        response = requests.get(f"{SD_API_URL}/sdapi/v1/sd-models", timeout=10)
        response.raise_for_status()
        models = response.json()
        return jsonify({
            'success': True,
            'models': models
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/trinity/sd/info')
def sd_info():
    """統合情報"""
    return jsonify({
        'service': 'Trinity Stable Diffusion Integration',
        'version': '1.0',
        'api_url': SD_API_URL,
        'endpoints': {
            'status': '/trinity/sd/status',
            'generate': 'POST /trinity/sd/generate',
            'image': '/trinity/sd/image/<image_id>',
            'models': '/trinity/sd/models'
        },
        'example': {
            'curl': 'curl -X POST http://localhost:5014/trinity/sd/generate -H "Content-Type: application/json" -d \'{"prompt": "beautiful girl"}\''
        }
    })

if __name__ == '__main__':
    print("=" * 70)
    print("🎨 Trinity Stable Diffusion Integration 起動中...")
    print("=" * 70)
    print("📍 ポート: 5014")
    print(f"🔗 Stable Diffusion API: {SD_API_URL}")
    print()
    print("⚠️  注意: SD_API_URLをRunPodのProxy URLに変更してください")
    print("   RunPodダッシュボード → ポート7860のProxy URL")
    print()
    print("📖 詳細: /root/stable_diffusion_integration_guide.md")
    print("=" * 70)
    
    app.run(host='0.0.0.0', port=5014, debug=os.getenv("DEBUG", "False").lower() == "true")
