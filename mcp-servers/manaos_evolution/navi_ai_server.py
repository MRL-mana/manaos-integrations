#!/usr/bin/env python3
"""
ManaOS ナビAI Server
"今やると人生伸びること"を提案するAI
"""

from flask import Flask, request, jsonify
import openai
import os
import logging
from datetime import datetime
from typing import Dict

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 環境変数
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
NOTION_API_KEY = os.environ.get('NOTION_API_KEY', '')
NOTION_DATABASE_ID = os.environ.get('NOTION_DATABASE_ID', '')
CALENDAR_API_KEY = os.environ.get('CALENDAR_API_KEY', '')

openai.api_key = OPENAI_API_KEY

class NaviAI:
    """ナビAI コアエンジン"""
    
    def __init__(self):
        self.morning_prompt = self._load_morning_prompt()
        self.noon_prompt = self._load_noon_prompt()
        self.night_prompt = self._load_night_prompt()
    
    def _load_morning_prompt(self) -> str:
        return """あなたはマナOSのナビAIです。朝の最適ルートを提案してください。

入力情報:
- 今日の予定: {calendar_events}
- 未完了タスク: {pending_tasks}
- バッテリー残量: {battery_level}%
- 昨日の完了: {yesterday_completed}

出力形式（JSON）:
{{
  "priority_tasks": [
    {{"task": "タスク名", "reason": "なぜこれが最適か", "estimated_time": "時間", "energy_level": "high/medium/low"}}
  ],
  "energy_allocation": {{
    "morning": "タスクと説明",
    "afternoon": "タスクと説明",
    "evening": "タスクと説明"
  }},
  "recommended_order": ["タスク1", "タスク2", "タスク3"],
  "motivational_message": "今日を最大限に活かす一言"
}}"""
    
    def _load_noon_prompt(self) -> str:
        return """あなたはマナOSのナビAIです。昼の集中復帰ポイントを提案してください。

入力情報:
- 午前の進捗: {morning_progress}
- 現在のバッテリー: {current_battery}%
- 残りタスク: {remaining_tasks}
- 次の予定: {next_event}

出力形式（JSON）:
{{
  "next_task": {{
    "task": "タスク名",
    "reason": "なぜ今これか",
    "focus_mode": "deep/shallow",
    "estimated_time": "時間"
  }},
  "break_needed": true/false,
  "break_suggestion": "休憩の提案",
  "motivation_boost": "やる気を上げる一言"
}}"""
    
    def _load_night_prompt(self) -> str:
        return """あなたはマナOSのナビAIです。夜のリフレクション+改善を提案してください。

入力情報:
- 今日の完了: {today_completed}
- バッテリー消費: {battery_consumption}
- 感情スコア: {emotion_score}/10
- 未完了タスク: {incomplete_tasks}

出力形式（JSON）:
{{
  "reflection": {{
    "achievements": ["達成1", "達成2"],
    "challenges": ["課題1", "課題2"],
    "learning": "学んだこと"
  }},
  "one_improvement": {{
    "area": "改善領域",
    "suggestion": "具体的な改善提案",
    "tomorrow_focus": "明日の焦点"
  }},
  "reward_suggestion": {{
    "needed": true/false,
    "type": "mufufu/rest/other",
    "message": "ご褒美の提案"
  }},
  "tomorrow_prep": {{
    "morning_task": "明日朝やること",
    "setup_needed": "準備が必要なこと"
  }}
}}"""
    
    async def get_morning_proposal(self, context: Dict) -> Dict:
        """朝の最適ルート提案"""
        prompt = self.morning_prompt.format(**context)
        
        response = await openai.ChatCompletion.acreate(  # type: ignore[attr-defined]
            model="gpt-4",
            messages=[
                {"role": "system", "content": "あなたはマナOSのナビAIです。実用的で具体的な提案をしてください。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        
        import json
        return json.loads(response.choices[0].message.content)
    
    async def get_noon_proposal(self, context: Dict) -> Dict:
        """昼の集中復帰ポイント提案"""
        prompt = self.noon_prompt.format(**context)
        
        response = await openai.ChatCompletion.acreate(  # type: ignore[attr-defined]
            model="gpt-4",
            messages=[
                {"role": "system", "content": "あなたはマナOSのナビAIです。集中力を回復させる提案をしてください。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        
        import json
        return json.loads(response.choices[0].message.content)
    
    async def get_night_proposal(self, context: Dict) -> Dict:
        """夜のリフレクション+改善提案"""
        prompt = self.night_prompt.format(**context)
        
        response = await openai.ChatCompletion.acreate(  # type: ignore[attr-defined]
            model="gpt-4",
            messages=[
                {"role": "system", "content": "あなたはマナOSのナビAIです。前向きで建設的な振り返りをしてください。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        
        import json
        return json.loads(response.choices[0].message.content)


navi_ai = NaviAI()

@app.route('/propose/morning', methods=['POST'])
def propose_morning():
    """朝の提案"""
    try:
        context = request.get_json()
        proposal = navi_ai.get_morning_proposal(context)
        return jsonify({
            'status': 'success',
            'proposal': proposal,
            'timestamp': datetime.now().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Error in morning proposal: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/propose/noon', methods=['POST'])
def propose_noon():
    """昼の提案"""
    try:
        context = request.get_json()
        proposal = navi_ai.get_noon_proposal(context)
        return jsonify({
            'status': 'success',
            'proposal': proposal,
            'timestamp': datetime.now().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Error in noon proposal: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/propose/night', methods=['POST'])
def propose_night():
    """夜の提案"""
    try:
        context = request.get_json()
        proposal = navi_ai.get_night_proposal(context)
        return jsonify({
            'status': 'success',
            'proposal': proposal,
            'timestamp': datetime.now().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Error in night proposal: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'service': 'navi-ai'}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5002))
    app.run(host="0.0.0.0", port=port, debug=os.getenv("DEBUG", "False").lower() == "true")
