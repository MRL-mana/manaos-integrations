#!/usr/bin/env python3
"""
RunPod Simple Bridge
シンプルなHTTPブリッジでRunPodにアクセスする
"""

import os
from flask import Flask, jsonify
import subprocess
from datetime import datetime

app = Flask(__name__)

@app.route('/')
def index():
    """メインページ"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>RunPod Simple Bridge</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #1a1a1a; color: white; }
            .container { max-width: 800px; margin: 0 auto; }
            .status { padding: 20px; margin: 10px 0; border-radius: 8px; background: #2d5a2d; }
            .code { background: #333; padding: 15px; border-radius: 5px; font-family: monospace; margin: 10px 0; }
            button { padding: 10px 20px; margin: 5px; background: #007acc; color: white; border: none; border-radius: 5px; cursor: pointer; }
            button:hover { background: #005a99; }
            .result { margin: 20px 0; padding: 15px; background: #333; border-radius: 5px; }
            a { color: #007acc; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🌉 RunPod Simple Bridge</h1>
            <p>RunPod GPUへのシンプルなアクセス方法</p>
            
            <div class="status">
                <h3>✅ 利用可能な直接アクセス</h3>
                <p><strong>Web Terminal:</strong> <a href="http://213.181.111.2:19123" target="_blank">http://213.181.111.2:19123</a></p>
                <p><strong>Jupyter Notebook:</strong> <a href="http://213.181.111.2:8888" target="_blank">http://213.181.111.2:8888</a></p>
            </div>
            
            <h3>🎯 推奨される使用方法</h3>
            <div class="code">
                <strong>1. Web Terminal経由（最も簡単）</strong><br>
                ブラウザで http://213.181.111.2:19123 にアクセス<br>
                直接GPUコマンドを実行可能<br><br>
                
                <strong>2. Jupyter Notebook経由</strong><br>
                ブラウザで http://213.181.111.2:8888 にアクセス<br>
                PythonコードでGPU操作可能
            </div>
            
            <h3>🔧 GPUテストコマンド</h3>
            <div class="code">
                # GPU確認<br>
                nvidia-smi<br><br>
                
                # Python GPUテスト<br>
                python3 -c "import torch; print(f'CUDA: {torch.cuda.is_available()}'); print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"なし\"}')"<br><br>
                
                # 画像生成テスト<br>
                python3 gpu_image_generation.py
            </div>
            
            <h3>📊 現在の状況</h3>
            <div class="result">
                <p><strong>✅ 動作確認済み:</strong></p>
                <ul>
                    <li>RunPod GPU: RTX 4090 24GB</li>
                    <li>PyTorch: インストール済み</li>
                    <li>API Server: ポート7860で動作中</li>
                    <li>Web Terminal: アクセス可能</li>
                    <li>Jupyter: アクセス可能</li>
                </ul>
                
                <p><strong>❌ 制限事項:</strong></p>
                <ul>
                    <li>外部ポート公開: 設定が必要</li>
                    <li>SSH PTY: エラーが発生</li>
                    <li>自動化: 手動操作が必要</li>
                </ul>
            </div>
            
            <h3>💡 解決策</h3>
            <div class="code">
                <strong>現実的な選択肢:</strong><br>
                1. Web Terminalで手動操作（確実）<br>
                2. Jupyter Notebookでコード実行<br>
                3. RunPodダッシュボードでポート公開設定
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/api/runpod/status')
def runpod_status():
    """RunPod状態確認"""
    try:
        # 簡単な接続確認
        result = subprocess.run([
            'curl', '-s', '--connect-timeout', '5', 
            'http://213.181.111.2:19123'
        ], capture_output=True, text=True)
        
        return jsonify({
            "web_terminal": "accessible" if result.returncode == 0 else "not_accessible",
            "timestamp": datetime.now().isoformat(),
            "message": "Web Terminal接続確認"
        })
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/runpod/gpu/simulation')
def gpu_simulation():
    """GPU状態シミュレーション"""
    return jsonify({
        "cuda_available": True,
        "gpu_name": "NVIDIA GeForce RTX 4090",
        "gpu_memory": "23.5GB",
        "method": "simulation",
        "note": "実際のGPU状態はWeb Terminalで確認してください",
        "timestamp": datetime.now().isoformat()
    })

def main():
    """メイン実行"""
    print("🌉 RunPod Simple Bridge")
    print("=" * 40)
    print("📡 アクセスURL: http://163.44.120.49:3001")
    print("📡 ローカルURL: http://localhost:3001")
    print("🎯 目的: RunPodへの代替アクセス方法を提供")
    
    app.run(host='0.0.0.0', port=3001, debug=os.getenv("DEBUG", "False").lower() == "true")

if __name__ == "__main__":
    main()
