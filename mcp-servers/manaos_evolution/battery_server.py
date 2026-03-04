#!/usr/bin/env python3
"""
ManaOS バッテリー管理サーバー
体調/疲労/やる気スコアを管理
"""

from flask import Flask, request, jsonify
import os
import logging
from datetime import datetime
from typing import Dict, Optional
import requests

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 環境変数
NOTION_API_KEY = os.environ.get('NOTION_API_KEY', '')
NOTION_DATABASE_ID = os.environ.get('NOTION_DATABASE_ID', '')
PROMETHEUS_PUSHGATEWAY = os.environ.get('PROMETHEUS_PUSHGATEWAY', 'http://localhost:9091')

class BatteryManager:
    """バッテリー管理エンジン"""
    
    def __init__(self):
        self.scores = {
            'health': 5.0,
            'fatigue': 5.0,
            'motivation': 5.0
        }
        self.history = []
    
    def calculate_battery_level(self, health: float, fatigue: float, motivation: float) -> float:
        """バッテリーレベル計算（0-10）"""
        battery = (
            health * 0.3 +
            (10 - fatigue) * 0.4 +
            motivation * 0.3
        )
        return round(battery, 1)
    
    def get_mode(self, battery_level: float) -> Dict:
        """バッテリーレベルに応じたモード判定"""
        if battery_level < 4:
            return {
                'mode': 'rest_mode',
                'name': '休息モード 🍓',
                'actions': [
                    '自動化タスクを優先',
                    '音声入力モード推奨',
                    'ムフフ生成でご褒美',
                    '軽いタスクのみ',
                    '休憩を取る'
                ],
                'task_types': ['automation', 'voice', 'light'],
                'mufufu_recommended': True
            }
        elif battery_level < 7:
            return {
                'mode': 'normal_mode',
                'name': '通常運転 ⚡',
                'actions': [
                    'ルーチンタスク実行',
                    'バランスの取れた作業'
                ],
                'task_types': ['routine', 'normal'],
                'mufufu_recommended': False
            }
        else:
            return {
                'mode': 'attack_mode',
                'name': '攻めモード 🔥',
                'actions': [
                    '難易度の高いタスク',
                    'クリエイティブ作業',
                    '新しいチャレンジ'
                ],
                'task_types': ['hard', 'creative', 'challenge'],
                'mufufu_recommended': False
            }
    
    def update_scores(self, health: Optional[float] = None,
                     fatigue: Optional[float] = None,
                     motivation: Optional[float] = None):
        """スコア更新"""
        if health is not None:
            self.scores['health'] = health
        if fatigue is not None:
            self.scores['fatigue'] = fatigue
        if motivation is not None:
            self.scores['motivation'] = motivation
        
        battery_level = self.calculate_battery_level(
            self.scores['health'],
            self.scores['fatigue'],
            self.scores['motivation']
        )
        
        record = {
            'timestamp': datetime.now().isoformat(),
            'health': self.scores['health'],
            'fatigue': self.scores['fatigue'],
            'motivation': self.scores['motivation'],
            'battery_level': battery_level,
            'mode': self.get_mode(battery_level)['mode']
        }
        
        self.history.append(record)
        
        # 直近100件のみ保持
        if len(self.history) > 100:
            self.history = self.history[-100:]
        
        return record
    
    def get_current_status(self) -> Dict:
        """現在の状態取得"""
        battery_level = self.calculate_battery_level(
            self.scores['health'],
            self.scores['fatigue'],
            self.scores['motivation']
        )
        mode_info = self.get_mode(battery_level)
        
        return {
            'scores': self.scores.copy(),
            'battery_level': battery_level,
            'mode': mode_info,
            'timestamp': datetime.now().isoformat()
        }


battery_manager = BatteryManager()

@app.route('/battery/update', methods=['POST'])
def update_battery():
    """バッテリースコア更新"""
    try:
        data = request.get_json()
        
        health = data.get('health')
        fatigue = data.get('fatigue')
        motivation = data.get('motivation')
        
        record = battery_manager.update_scores(
            health=health,
            fatigue=fatigue,
            motivation=motivation
        )
        
        # Prometheusに送信
        try:
            metrics = f"""battery_health {record['health']}
battery_fatigue {record['fatigue']}
battery_motivation {record['motivation']}
battery_level {record['battery_level']}"""
            
            requests.post(
                f"{PROMETHEUS_PUSHGATEWAY}/metrics/job/manaos_battery",
                data=metrics,
                timeout=5
            )
        except Exception as e:
            logger.warning(f"Failed to push to Prometheus: {e}")
        
        return jsonify({
            'status': 'success',
            'record': record
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating battery: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/battery/status', methods=['GET'])
def get_status():
    """現在のバッテリー状態取得"""
    try:
        status = battery_manager.get_current_status()
        return jsonify({
            'status': 'success',
            'data': status
        }), 200
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/battery/history', methods=['GET'])
def get_history():
    """バッテリー履歴取得"""
    try:
        limit = request.args.get('limit', 24, type=int)  # デフォルト24時間分
        history = battery_manager.history[-limit:]
        return jsonify({
            'status': 'success',
            'history': history,
            'count': len(history)
        }), 200
    except Exception as e:
        logger.error(f"Error getting history: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'service': 'battery-management'}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5003))
    app.run(host="0.0.0.0", port=port, debug=os.getenv("DEBUG", "False").lower() == "true")
