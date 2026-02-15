#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""画像評価Web UI起動スクリプト"""

import sys
import os
from pathlib import Path

# 評価UIファイルを確認
evaluation_web_file = Path(__file__).parent / "image_evaluation_web.py"

if not evaluation_web_file.exists():
    print("⚠️ image_evaluation_web.py が見つかりません")
    print("評価UIファイルを再作成します...")
    
    # 簡易版の評価UIを作成
    from flask import Flask, render_template_string, jsonify, request, send_from_directory
    import json
    from datetime import datetime
    
    app = Flask(__name__)
    
    COMFYUI_OUTPUT_DIR = Path("C:/ComfyUI/output")
    EVALUATION_DB = Path("C:/ComfyUI/input/mana_favorites/evaluation.json")
    
    # 評価データを読み込み
    evaluations = {}
    if EVALUATION_DB.exists():
        try:
            with open(EVALUATION_DB, 'r', encoding='utf-8') as f:
                evaluations = json.load(f)
        except Exception:
            pass
    
    @app.route('/')
    def index():
        return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>画像評価</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1400px; margin: 0 auto; }
        h1 { color: #333; }
        .stats { background: white; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
        .image-card { background: white; border-radius: 5px; padding: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .image-card img { width: 100%; height: auto; border-radius: 5px; cursor: pointer; }
        .score-buttons { display: flex; gap: 5px; margin: 10px 0; }
        .score-btn { flex: 1; padding: 10px; border: 2px solid #ddd; border-radius: 5px; cursor: pointer; background: white; }
        .score-btn.active { background: #667eea; color: white; border-color: #667eea; }
        .comment-input { width: 100%; padding: 8px; border: 2px solid #ddd; border-radius: 5px; margin-top: 5px; }
        .save-btn { width: 100%; padding: 10px; background: #667eea; color: white; border: none; border-radius: 5px; cursor: pointer; margin-top: 10px; display: none; }
        .evaluated-badge { display: inline-block; padding: 5px 10px; background: #4CAF50; color: white; border-radius: 3px; font-size: 12px; margin-top: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>画像評価</h1>
        <div class="stats" id="stats">読み込み中...</div>
        <div class="grid" id="imageGrid"></div>
    </div>
    <script>
        let currentScore = {};
        let imagesData = [];
        
        async function loadImages() {
            const response = await fetch('/api/images');
            const data = await response.json();
            imagesData = Array.isArray(data) ? data : (data.items || []);
            updateStats();
            displayImages();
        }
        
        function updateStats() {
            const total = imagesData.length;
            const evaluated = imagesData.filter(img => img.evaluated).length;
            const highScore = imagesData.filter(img => img.evaluated && img.score <= 2).length;
            document.getElementById('stats').innerHTML = `
                <strong>統計:</strong> 総数: ${total}件 | 評価済み: ${evaluated}件 | 高評価: ${highScore}件
            `;
        }
        
        function displayImages() {
            const grid = document.getElementById('imageGrid');
            grid.innerHTML = '';
            
            imagesData.forEach(img => {
                const card = document.createElement('div');
                card.className = 'image-card';
                card.innerHTML = `
                    <img src="/images/${encodeURIComponent(img.name)}" alt="${img.name}" onclick="openModal('${img.name}')">
                    <div style="margin-top: 10px;">
                        <div class="score-buttons">
                            ${[1,2,3,4].map(score => `
                                <button class="score-btn ${(img.evaluated && img.score === score) ? 'active' : ''}" 
                                        onclick="setScore('${img.path}', ${score}, this)">
                                    ${score}<br><small>${score === 1 ? '最高' : score === 2 ? '高' : score === 3 ? '普通' : '低'}</small>
                                </button>
                            `).join('')}
                        </div>
                        <textarea class="comment-input" id="comment_${img.path.replace(/[^a-zA-Z0-9]/g, '_')}" 
                                  placeholder="コメント（オプション）">${(img.comment || '').trim()}</textarea>
                        <button class="save-btn" id="save_${img.path.replace(/[^a-zA-Z0-9]/g, '_')}" 
                                onclick="saveEvaluation('${img.path}', true)" 
                                style="display: ${(img.comment || '').trim() ? 'block' : 'none'}">保存</button>
                        ${img.evaluated ? `<div class="evaluated-badge">評価済み: ${img.score}点</div>` : ''}
                    </div>
                `;
                grid.appendChild(card);
            });
        }
        
        async function setScore(imagePath, score, buttonElement) {
            currentScore[imagePath] = score;
            const buttons = buttonElement.parentElement.querySelectorAll('.score-btn');
            buttons.forEach(btn => btn.classList.remove('active'));
            buttonElement.classList.add('active');
            
            const commentId = 'comment_' + imagePath.replace(/[^a-zA-Z0-9]/g, '_');
            const commentEl = document.getElementById(commentId);
            const hasComment = commentEl && commentEl.value.trim().length > 0;
            
            if (!hasComment) {
                await saveEvaluation(imagePath, false);
            } else {
                const saveBtn = document.getElementById('save_' + imagePath.replace(/[^a-zA-Z0-9]/g, '_'));
                if (saveBtn) saveBtn.style.display = 'block';
            }
        }
        
        async function saveEvaluation(imagePath, showErrorAlert) {
            const score = currentScore[imagePath];
            if (!score) {
                if (showErrorAlert) alert('評価を選択してください');
                return;
            }
            
            const commentId = 'comment_' + imagePath.replace(/[^a-zA-Z0-9]/g, '_');
            const commentEl = document.getElementById(commentId);
            const comment = commentEl ? commentEl.value.trim() : '';
            
            try {
                const response = await fetch('/api/evaluate', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({image_path: imagePath, score: score, comment: comment})
                });
                
                const result = await response.json();
                if (result.success) {
                    loadImages();
                } else {
                    if (showErrorAlert) alert('エラー: ' + result.error);
                }
            } catch (error) {
                console.error('評価保存エラー:', error);
                if (showErrorAlert) alert('評価の保存に失敗しました');
            }
        }
        
        function openModal(imgName) {
            window.open(`/images/${encodeURIComponent(imgName)}`, '_blank');
        }
        
        loadImages();
    </script>
</body>
</html>
        ''')
    
    @app.route('/api/images')
    def get_images():
        if not COMFYUI_OUTPUT_DIR.exists():
            return jsonify([])
        
        all_items = []
        for img_file in COMFYUI_OUTPUT_DIR.glob("ComfyUI_*.png"):
            img_path = str(img_file)
            eval_data = evaluations.get(img_path)
            all_items.append({
                "name": img_file.name,
                "path": img_path,
                "evaluated": eval_data is not None,
                "score": eval_data.get("score") if eval_data else None,
                "comment": eval_data.get("comment", "") if eval_data else ""
            })
        
        all_items.sort(key=lambda x: x["name"], reverse=True)
        return jsonify(all_items)
    
    @app.route('/api/evaluate', methods=['POST'])
    def evaluate():
        data = request.json
        img_path = data.get("image_path")
        score = data.get("score")
        comment = data.get("comment", "").strip()
        
        if not img_path or not score:
            return jsonify({"success": False, "error": "画像パスとスコアが必要です"})
        
        evaluations[img_path] = {
            "score": score,
            "comment": comment,
            "evaluated_at": datetime.now().isoformat()
        }
        
        try:
            EVALUATION_DB.parent.mkdir(parents=True, exist_ok=True)
            with open(EVALUATION_DB, 'w', encoding='utf-8') as f:
                json.dump(evaluations, f, ensure_ascii=False, indent=2)
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})
    
    @app.route('/images/<path:filename>')
    def serve_image(filename):
        return send_from_directory(str(COMFYUI_OUTPUT_DIR), filename)
    
    if __name__ == '__main__':
        import socket
        def get_local_ip():
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                s.close()
                return ip
            except Exception:
                return "localhost"
        
        local_ip = get_local_ip()
        
        print("=" * 60)
        print("画像評価Webサーバー起動")
        print("=" * 60)
        print(f"ローカルアクセス: http://127.0.0.1:9600")
        print(f"外部アクセス（同一Wi-Fi）: http://{local_ip}:9600")
        print(f"📱 Pixel 7からアクセス: http://{local_ip}:9600")
        print("=" * 60)
        print()
        
        app.run(host='0.0.0.0', port=9600, debug=True)

else:
    # 既存の評価UIファイルを実行
    print("既存の評価UIを起動します...")
    exec(open(evaluation_web_file).read())
