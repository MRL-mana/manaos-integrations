#!/usr/bin/env python3
"""
🎨 RunPod画像プロキシサーバー
このはサーバー経由でRunPod生成画像を確認
"""
from flask import Flask, send_file, jsonify, render_template_string
import requests
import os

app = Flask(__name__)

RUNPOD_API = "http://localhost:5009"

# HTML テンプレート
IMAGE_GALLERY_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎨 RunPod GPU画像ギャラリー</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        h1 {
            text-align: center;
            margin-bottom: 30px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        .controls {
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            padding: 20px;
            border-radius: 15px;
            margin-bottom: 30px;
            text-align: center;
        }
        .btn {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            border: none;
            padding: 15px 30px;
            font-size: 16px;
            border-radius: 25px;
            cursor: pointer;
            margin: 5px;
            transition: transform 0.2s;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0,0,0,0.3);
        }
        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .status {
            margin: 20px 0;
            padding: 15px;
            background: rgba(255,255,255,0.2);
            border-radius: 10px;
            text-align: center;
        }
        .gallery {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 30px;
        }
        .image-card {
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 15px;
            transition: transform 0.3s;
        }
        .image-card:hover {
            transform: scale(1.05);
        }
        .image-card img {
            width: 100%;
            height: auto;
            border-radius: 10px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        }
        .image-info {
            margin-top: 10px;
            text-align: center;
            font-size: 14px;
        }
        .loading {
            text-align: center;
            padding: 40px;
            font-size: 20px;
        }
        .spinner {
            border: 4px solid rgba(255,255,255,0.3);
            border-top: 4px solid white;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 20px auto;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎨 RunPod GPU画像ギャラリー</h1>
        
        <div class="controls">
            <button class="btn" onclick="generateImages()">🎨 新しい画像を生成（4枚）</button>
            <button class="btn" onclick="refreshGallery()">🔄 ギャラリー更新</button>
            <button class="btn" onclick="checkGPU()">📊 GPU状態確認</button>
        </div>
        
        <div class="status" id="status">
            準備完了
        </div>
        
        <div class="gallery" id="gallery">
            <div class="loading">
                <p>「ギャラリー更新」ボタンを押して画像を表示</p>
            </div>
        </div>
    </div>

    <script>
        async function generateImages() {
            const btn = event.target;
            btn.disabled = true;
            document.getElementById('status').innerHTML = '🎨 画像生成中...';
            document.getElementById('gallery').innerHTML = '<div class="loading"><div class="spinner"></div><p>GPU処理中...</p></div>';
            
            try {
                const response = await fetch('/api/generate', { method: 'POST' });
                const data = await response.json();
                
                if (data.success) {
                    document.getElementById('status').innerHTML = `✅ 画像生成完了！ ${data.images_generated}枚`;
                    setTimeout(() => refreshGallery(), 1000);
                } else {
                    document.getElementById('status').innerHTML = `❌ エラー: ${data.error}`;
                }
            } catch (error) {
                document.getElementById('status').innerHTML = `❌ エラー: ${error}`;
            } finally {
                btn.disabled = false;
            }
        }
        
        async function refreshGallery() {
            document.getElementById('status').innerHTML = '📥 画像読み込み中...';
            document.getElementById('gallery').innerHTML = '<div class="loading"><div class="spinner"></div></div>';
            
            try {
                const response = await fetch('/api/images');
                const data = await response.json();
                
                if (data.images && data.images.length > 0) {
                    let html = '';
                    data.images.forEach((img, index) => {
                        html += `
                            <div class="image-card">
                                <img src="/api/image/${index + 1}?t=${Date.now()}" alt="Image ${index + 1}">
                                <div class="image-info">
                                    画像 ${index + 1} / ${data.images.length}
                                </div>
                            </div>
                        `;
                    });
                    document.getElementById('gallery').innerHTML = html;
                    document.getElementById('status').innerHTML = `✅ ${data.images.length}枚の画像を表示中`;
                } else {
                    document.getElementById('gallery').innerHTML = '<div class="loading"><p>画像がまだ生成されていません</p></div>';
                    document.getElementById('status').innerHTML = '画像を生成してください';
                }
            } catch (error) {
                document.getElementById('status').innerHTML = `❌ エラー: ${error}`;
            }
        }
        
        async function checkGPU() {
            document.getElementById('status').innerHTML = '🔍 GPU状態確認中...';
            
            try {
                const response = await fetch('/api/gpu/status');
                const data = await response.json();
                
                if (data.success) {
                    const gpu = data.gpu_info;
                    document.getElementById('status').innerHTML = 
                        `📊 GPU: ${gpu.name} | VRAM: ${gpu.memory.toFixed(1)}GB | 状態: ${gpu.gpu ? '✅ 稼働中' : '❌ 停止'}`;
                } else {
                    document.getElementById('status').innerHTML = `❌ エラー: ${data.error}`;
                }
            } catch (error) {
                document.getElementById('status').innerHTML = `❌ エラー: ${error}`;
            }
        }
        
        // 初回読み込み時にGPU状態を確認
        window.onload = () => checkGPU();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """ギャラリーページ"""
    return render_template_string(IMAGE_GALLERY_HTML)

@app.route('/api/generate', methods=['POST'])
def generate_images():
    """画像生成"""
    try:
        response = requests.post(f"{RUNPOD_API}/trinity/gpu/generate", timeout=60)
        response.raise_for_status()
        result = response.json()
        return jsonify({
            'success': True,
            'images_generated': result.get('result', {}).get('images_generated', 0)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/gpu/status')
def gpu_status():
    """GPU状態"""
    try:
        response = requests.get(f"{RUNPOD_API}/trinity/gpu/status", timeout=10)
        response.raise_for_status()
        result = response.json()
        return jsonify({
            'success': True,
            'gpu_info': result.get('gpu_info', {})
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/images')
def list_images():
    """画像一覧（ダミー - 実際にはRunPodから取得が必要）"""
    # 注: 実際の実装では RunPod から画像リストを取得
    images = [f"gpu_boost_image_{i}.png" for i in range(1, 5)]
    return jsonify({'images': images})

@app.route('/api/image/<int:image_id>')
def get_image(image_id):
    """画像取得（ダミー画像生成）"""
    try:
        # ダミー画像を生成（実際にはRunPodから取得）
        import io
        from PIL import Image, ImageDraw
        import random
        
        # カラフルなダミー画像を生成
        img = Image.new('RGB', (256, 256), color=(
            random.randint(50, 200),
            random.randint(50, 200),
            random.randint(50, 200)
        ))
        draw = ImageDraw.Draw(img)
        
        # テキスト描画
        text = f"RunPod GPU\nImage #{image_id}"
        draw.text((80, 110), text, fill=(255, 255, 255))
        
        # バイトストリームに変換
        img_io = io.BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)
        
        return send_file(img_io, mimetype='image/png')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("🎨 RunPod画像プロキシサーバー起動中...")
    print("   アクセス: http://localhost:5012")
    print("   または: http://163.44.120.49:5012")
    app.run(host='0.0.0.0', port=5012, debug=os.getenv("DEBUG", "False").lower() == "true")
