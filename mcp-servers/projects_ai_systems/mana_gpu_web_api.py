#!/usr/bin/env python3
"""
Mana GPU Web API
ブラウザから直接RunPod GPUを操作
"""

import os
from flask import Flask, render_template_string, jsonify
import subprocess

app = Flask(__name__)

# HTMLテンプレート
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Mana GPU操作パネル</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f0f0f0; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        h1 { color: #333; text-align: center; }
        .button { background: #4CAF50; color: white; padding: 15px 30px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; margin: 10px; width: 100%; }
        .button:hover { background: #45a049; }
        .result { background: #f9f9f9; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #4CAF50; }
        .error { border-left-color: #f44336; }
        .loading { color: #666; font-style: italic; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎮 Mana GPU操作パネル</h1>
        <p>RTX 4090 24GBをブラウザから直接操作！</p>
        
        <button class="button" onclick="checkGPU()">🔥 GPU状態確認</button>
        <button class="button" onclick="generateImages()">🎨 画像生成実行</button>
        <button class="button" onclick="runDeepLearning()">🧠 深層学習実行</button>
        <button class="button" onclick="runTransformers()">🤖 Transformers実行</button>
        
        <div id="result"></div>
    </div>

    <script>
        function showResult(message, isError = false) {
            const resultDiv = document.getElementById('result');
            resultDiv.innerHTML = `<div class="result ${isError ? 'error' : ''}">${message}</div>`;
        }
        
        function showLoading(message) {
            const resultDiv = document.getElementById('result');
            resultDiv.innerHTML = `<div class="result loading">${message}</div>`;
        }
        
        async function checkGPU() {
            showLoading('🔥 GPU状態確認中...');
            try {
                const response = await fetch('/api/gpu_status');
                const data = await response.json();
                if (data.success) {
                    showResult(`✅ GPU状態確認成功<br><pre>${data.output}</pre>`);
                } else {
                    showResult(`❌ GPU状態確認失敗: ${data.error}`, true);
                }
            } catch (error) {
                showResult(`❌ エラー: ${error}`, true);
            }
        }
        
        async function generateImages() {
            showLoading('🎨 画像生成中...');
            try {
                const response = await fetch('/api/generate_images');
                const data = await response.json();
                if (data.success) {
                    showResult(`✅ 画像生成成功！<br><pre>${data.output}</pre>`);
                } else {
                    showResult(`❌ 画像生成失敗: ${data.error}`, true);
                }
            } catch (error) {
                showResult(`❌ エラー: ${error}`, true);
            }
        }
        
        async function runDeepLearning() {
            showLoading('🧠 深層学習中...');
            try {
                const response = await fetch('/api/deep_learning');
                const data = await response.json();
                if (data.success) {
                    showResult(`✅ 深層学習成功！<br><pre>${data.output}</pre>`);
                } else {
                    showResult(`❌ 深層学習失敗: ${data.error}`, true);
                }
            } catch (error) {
                showResult(`❌ エラー: ${error}`, true);
            }
        }
        
        async function runTransformers() {
            showLoading('🤖 Transformers実行中...');
            try {
                const response = await fetch('/api/transformers');
                const data = await response.json();
                if (data.success) {
                    showResult(`✅ Transformers実行成功！<br><pre>${data.output}</pre>`);
                } else {
                    showResult(`❌ Transformers実行失敗: ${data.error}`, true);
                }
            } catch (error) {
                showResult(`❌ エラー: ${error}`, true);
            }
        }
    </script>
</body>
</html>
"""

def execute_runpod_command(command):
    """RunPodでコマンド実行"""
    try:
        ssh_cmd = [
            "ssh", "-o", "StrictHostKeyChecking=no",
            "-i", "/root/.ssh/id_ed25519_runpod_latest",
            "8uv33dh7cewgeq-644114e0@ssh.runpod.io",
            "-T",
            f"cd /workspace && {command}"
        ]
        
        result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=120)
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr
        }
    except Exception as e:
        return {
            "success": False,
            "output": "",
            "error": str(e)
        }

@app.route('/')
def index():
    """メインページ"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/gpu_status')
def api_gpu_status():
    """GPU状態確認API"""
    result = execute_runpod_command("nvidia-smi --query-gpu=name,memory.total,memory.used,utilization.gpu --format=csv,noheader,nounits")
    return jsonify(result)

@app.route('/api/generate_images')
def api_generate_images():
    """画像生成API"""
    image_code = '''
python3 -c "
import torch
import torch.nn as nn
import time

print('🎨 Mana Web API画像生成開始')
device = torch.device('cuda')
print(f'GPU: {torch.cuda.get_device_name(0)}')

class Generator(nn.Module):
    def __init__(self):
        super().__init__()
        self.main = nn.Sequential(
            nn.ConvTranspose2d(512, 1024, 4, 1, 0),
            nn.BatchNorm2d(1024),
            nn.ReLU(True),
            nn.ConvTranspose2d(1024, 512, 4, 2, 1),
            nn.BatchNorm2d(512),
            nn.ReLU(True),
            nn.ConvTranspose2d(512, 256, 4, 2, 1),
            nn.BatchNorm2d(256),
            nn.ReLU(True),
            nn.ConvTranspose2d(256, 128, 4, 2, 1),
            nn.BatchNorm2d(128),
            nn.ReLU(True),
            nn.ConvTranspose2d(128, 64, 4, 2, 1),
            nn.BatchNorm2d(64),
            nn.ReLU(True),
            nn.ConvTranspose2d(64, 3, 4, 2, 1),
            nn.Tanh()
        )
    def forward(self, noise):
        return self.main(noise)

generator = Generator().to(device)
noise = torch.randn(4, 512, 1, 1).to(device)

start_time = time.time()
with torch.no_grad():
    generated_images = generator(noise)
torch.cuda.synchronize()
end_time = time.time()

print(f'生成時間: {end_time - start_time:.4f}秒')
print(f'画像サイズ: {generated_images.shape}')
print('✅ Web API画像生成完了！')
"
'''
    result = execute_runpod_command(image_code)
    return jsonify(result)

@app.route('/api/deep_learning')
def api_deep_learning():
    """深層学習API"""
    dl_code = '''
python3 -c "
import torch
import torch.nn as nn
import time

print('🧠 Mana Web API深層学習開始')
device = torch.device('cuda')

class LargeNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(784, 2048),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(2048, 1024),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(1024, 512),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(512, 10)
        )
    def forward(self, x):
        return self.network(x)

model = LargeNN().to(device)
x = torch.randn(1000, 784).to(device)
y = torch.randint(0, 10, (1000,)).to(device)
criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

start_time = time.time()
for epoch in range(50):
    optimizer.zero_grad()
    outputs = model(x)
    loss = criterion(outputs, y)
    loss.backward()
    optimizer.step()

torch.cuda.synchronize()
end_time = time.time()

print(f'学習時間: {end_time - start_time:.4f}秒')
print(f'最終損失: {loss.item():.4f}')
print('✅ Web API深層学習完了！')
"
'''
    result = execute_runpod_command(dl_code)
    return jsonify(result)

@app.route('/api/transformers')
def api_transformers():
    """Transformers API"""
    transformers_code = '''
python3 -c "
import torch
from transformers import AutoTokenizer, AutoModel
import time

print('🤖 Mana Web API Transformers開始')
device = torch.device('cuda')

model_name = 'distilbert-base-uncased'
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModel.from_pretrained(model_name).to(device)

text = 'Hello, this is a test from Mana Web API!'
inputs = tokenizer(text, return_tensors='pt', padding=True, truncation=True)
inputs = {k: v.to(device) for k, v in inputs.items()}

start_time = time.time()
with torch.no_grad():
    outputs = model(**inputs)
torch.cuda.synchronize()
end_time = time.time()

print(f'推論時間: {end_time - start_time:.4f}秒')
print(f'出力形状: {outputs.last_hidden_state.shape}')
print('✅ Web API Transformers完了！')
"
'''
    result = execute_runpod_command(transformers_code)
    return jsonify(result)

if __name__ == '__main__':
    print("🚀 Mana GPU Web API起動中...")
    print("🌐 ブラウザで http://localhost:5000 にアクセスしてください")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=os.getenv("DEBUG", "False").lower() == "true")
