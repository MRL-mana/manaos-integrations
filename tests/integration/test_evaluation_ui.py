#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""評価UIのテスト起動"""

import sys
import io
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

try:
    from flask import Flask, render_template_string, jsonify, request, send_from_directory
    import json
    from datetime import datetime
    from pathlib import Path
    
    app = Flask(__name__)
    
    COMFYUI_OUTPUT_DIR = Path("C:/ComfyUI/output")
    EVALUATION_DB = Path("C:/ComfyUI/input/mana_favorites/evaluation.json")
    
    # 評価データを読み込み
    evaluations = {}
    if EVALUATION_DB.exists():
        try:
            with open(EVALUATION_DB, 'r', encoding='utf-8') as f:
                evaluations = json.load(f)
        except Exception as e:
            print(f"評価データ読み込みエラー: {e}")
    
    @app.route('/')
    def index():
        return "評価UIテスト - 動作中です！<br><a href='/test'>テストページ</a>"
    
    @app.route('/test')
    def test():
        return "<h1>テスト成功！</h1><p>Flaskは正常に動作しています。</p>"
    
    @app.route('/api/images')
    def get_images():
        if not COMFYUI_OUTPUT_DIR.exists():
            return jsonify([])
        
        all_items = []
        for img_file in list(COMFYUI_OUTPUT_DIR.glob("ComfyUI_*.png"))[:10]:  # 最初の10件のみ
            img_path = str(img_file)
            eval_data = evaluations.get(img_path)
            all_items.append({
                "name": img_file.name,
                "path": img_path,
                "evaluated": eval_data is not None,
                "score": eval_data.get("score") if eval_data else None,
                "comment": eval_data.get("comment", "") if eval_data else ""
            })
        
        return jsonify(all_items)
    
except Exception as e:
    print(f"エラー: {e}")
    import traceback
    traceback.print_exc()
    input("Enterキーで終了...")
