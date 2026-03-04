#!/usr/bin/env python3
"""
ManaOS ナビAI Server (モック版)
OpenAI APIキーがなくても動作するテスト版
"""

from flask import Flask, request, jsonify
import os
import logging
from datetime import datetime

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NaviAI:
    """ナビAI コアエンジン（モック版）"""
    
    def get_morning_proposal(self, context: dict) -> dict:
        """朝の最適ルート提案（モック）"""
        return {
            "priority_tasks": [
                {
                    "task": "重要なタスクを1つ完了させる",
                    "reason": "朝の集中力が高い時間帯に最重要タスクを処理",
                    "estimated_time": "2時間",
                    "energy_level": "high"
                },
                {
                    "task": "メールとSlackの返信",
                    "reason": "情報を整理してから本格作業に集中",
                    "estimated_time": "30分",
                    "energy_level": "medium"
                },
                {
                    "task": "新しいプロジェクトの設計",
                    "reason": "クリエイティブな作業に最適な時間",
                    "estimated_time": "1.5時間",
                    "energy_level": "high"
                }
            ],
            "energy_allocation": {
                "morning": "最重要タスク（集中力MAX）",
                "afternoon": "ルーチン作業と連絡",
                "evening": "振り返りと明日の準備"
            },
            "recommended_order": [
                "重要なタスクを1つ完了させる",
                "メールとSlackの返信",
                "新しいプロジェクトの設計"
            ],
            "motivational_message": "今日も最高の一日になる！朝の集中力で一気に進めよう🔥"
        }
    
    def get_noon_proposal(self, context: dict) -> dict:
        """昼の集中復帰ポイント提案（モック）"""
        battery = context.get('current_battery', 7)
        
        if battery < 5:
            return {
                "next_task": {
                    "task": "軽いタスクや自動化できる作業",
                    "reason": "バッテリーが低いので無理をしない",
                    "focus_mode": "shallow",
                    "estimated_time": "1時間"
                },
                "break_needed": True,
                "break_suggestion": "15分の休憩とムフフ生成でリフレッシュ🍓",
                "motivation_boost": "疲れた時は無理せず休むことも大切！"
            }
        else:
            return {
                "next_task": {
                    "task": "午後の最重要タスクに集中",
                    "reason": "まだバッテリーが残っているので攻める",
                    "focus_mode": "deep",
                    "estimated_time": "2時間"
                },
                "break_needed": False,
                "break_suggestion": "集中を保ったまま進められる",
                "motivation_boost": "午後も最高のパフォーマンスで行こう！🔥"
            }
    
    def get_night_proposal(self, context: dict) -> dict:
        """夜のリフレクション+改善提案（モック）"""
        completed = context.get('today_completed', '')
        emotion = context.get('emotion_score', 7)
        
        return {
            "reflection": {
                "achievements": [
                    "重要なタスクを完了",
                    "計画通りに進捗",
                    "バッテリー管理ができた"
                ],
                "challenges": [
                    "集中が途切れた時間があった",
                    "予定外のタスクが入った"
                ],
                "learning": "朝の集中力が高い時間を最大限活用すると効率的"
            },
            "one_improvement": {
                "area": "集中力の維持",
                "suggestion": "ポモドーロテクニックを導入してみる",
                "tomorrow_focus": "朝の最重要タスクを前日に決めておく"
            },
            "reward_suggestion": {
                "needed": True if emotion >= 8 else False,
                "type": "mufufu" if emotion >= 8 else "rest",
                "message": "よく頑張った！今日はゆっくり休もう🍓" if emotion >= 8 else "明日も頑張ろう！"
            },
            "tomorrow_prep": {
                "morning_task": "朝一番にやるタスクを決める",
                "setup_needed": "明日のカレンダーを確認"
            }
        }


navi_ai = NaviAI()

@app.route('/propose/morning', methods=['POST'])
def propose_morning():
    """朝の提案"""
    try:
        context = request.get_json() or {}
        proposal = navi_ai.get_morning_proposal(context)
        return jsonify({
            'status': 'success',
            'proposal': proposal,
            'timestamp': datetime.now().isoformat(),
            'mode': 'mock'
        }), 200
    except Exception as e:
        logger.error(f"Error in morning proposal: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/propose/noon', methods=['POST'])
def propose_noon():
    """昼の提案"""
    try:
        context = request.get_json() or {}
        proposal = navi_ai.get_noon_proposal(context)
        return jsonify({
            'status': 'success',
            'proposal': proposal,
            'timestamp': datetime.now().isoformat(),
            'mode': 'mock'
        }), 200
    except Exception as e:
        logger.error(f"Error in noon proposal: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/propose/night', methods=['POST'])
def propose_night():
    """夜の提案"""
    try:
        context = request.get_json() or {}
        proposal = navi_ai.get_night_proposal(context)
        return jsonify({
            'status': 'success',
            'proposal': proposal,
            'timestamp': datetime.now().isoformat(),
            'mode': 'mock'
        }), 200
    except Exception as e:
        logger.error(f"Error in night proposal: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'service': 'navi-ai-mock',
        'mode': 'mock (OpenAI API not required)'
    }), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5002))
    logger.info(f"Starting NaviAI Mock Server on port {port}")
    logger.info("Mode: MOCK (OpenAI API not required)")
    app.run(host="0.0.0.0", port=port, debug=os.getenv("DEBUG", "False").lower() == "true")
