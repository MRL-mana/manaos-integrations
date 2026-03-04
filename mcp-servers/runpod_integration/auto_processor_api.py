#!/usr/bin/env python3
"""
自動処理システム API
ステータス確認・設定変更用のHTTP API
"""

from flask import Flask, jsonify, request
import sys

sys.path.insert(0, '/root/runpod_integration')
sys.path.insert(0, '/root')

from auto_processor import AutoProcessor

app = Flask(__name__)
processor = AutoProcessor()

@app.route('/api/status', methods=['GET'])
def get_status():
    """ステータス取得"""
    status = processor.get_status()
    return jsonify(status)

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """統計情報取得"""
    stats = processor.get_stats()
    return jsonify(stats)

@app.route('/api/config', methods=['GET'])
def get_config():
    """設定取得"""
    return jsonify(processor.config)

@app.route('/api/config', methods=['POST'])
def update_config():
    """設定更新"""
    data = request.json

    # 自動画像生成
    if 'auto_generate' in data:
        ag = data['auto_generate']
        if ag.get('enabled'):
            processor.enable_auto_generate(
                prompts=ag.get('prompts', []),
                interval_minutes=ag.get('interval_minutes', 60),
                count_per_run=ag.get('count_per_run', 5)
            )
        else:
            processor.config['auto_generate']['enabled'] = False
            processor.save_config()

    # 自動超解像
    if 'auto_upscale' in data:
        au = data['auto_upscale']
        if au.get('enabled'):
            processor.enable_auto_upscale(
                scale=au.get('scale', 2),
                method=au.get('method', 'simple')
            )
        else:
            processor.config['auto_upscale']['enabled'] = False
            processor.save_config()

    # 自動GIF生成
    if 'auto_gif' in data:
        agif = data['auto_gif']
        if agif.get('enabled'):
            processor.enable_auto_gif(
                batch_size=agif.get('batch_size', 5)
            )
        else:
            processor.config['auto_gif']['enabled'] = False
            processor.save_config()

    # 自動LoRA学習
    if 'auto_training' in data:
        at = data['auto_training']
        if at.get('enabled'):
            processor.enable_auto_training(
                auto_steps=at.get('auto_steps', 1000)
            )
        else:
            processor.config['auto_training']['enabled'] = False
            processor.save_config()

    return jsonify({"success": True, "config": processor.config})

@app.route('/api/start', methods=['POST'])
def start_processor():
    """自動処理を開始"""
    if processor.running:
        return jsonify({"success": False, "error": "既に実行中です"})

    processor.start()
    return jsonify({"success": True, "message": "自動処理を開始しました"})

@app.route('/api/stop', methods=['POST'])
def stop_processor():
    """自動処理を停止"""
    if not processor.running:
        return jsonify({"success": False, "error": "実行中ではありません"})

    processor.stop()
    return jsonify({"success": True, "message": "自動処理を停止しました"})

if __name__ == '__main__':
    print("🚀 自動処理API起動中...")
    print("   http://localhost:5557/api/status - ステータス確認")
    print("   http://localhost:5557/api/stats - 統計情報")
    print("   http://localhost:5557/api/config - 設定")
    app.run(host='0.0.0.0', port=5557, debug=False)




