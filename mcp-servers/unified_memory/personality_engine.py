#!/usr/bin/env python3
"""
🎭 Personality Engine
Phase 8: Manaの性格・感情・価値観を完全モデリング

機能:
1. 性格モデリング（Big Five性格特性）
2. 感情状態の推定
3. 価値観ベースの意思決定
4. 時系列性格変化の学習
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List
from pathlib import Path
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Personality")


class PersonalityEngine:
    """パーソナリティエンジン - Manaを完全理解"""
    
    def __init__(self, unified_memory_api):
        logger.info("🎭 Personality Engine 初期化中...")
        
        self.memory_api = unified_memory_api
        
        # パーソナリティDB
        self.personality_db = Path('/root/.mana_personality.json')
        self.personality_data = self._load_personality()
        
        # 感情キーワード辞書
        self.emotion_keywords = {
            'happy': ['嬉しい', '楽しい', '最高', 'やった', 'できた', '成功', '完璧'],
            'excited': ['すごい', 'わくわく', '期待', '楽しみ', 'いいね'],
            'tired': ['疲れた', '眠い', 'しんどい', 'つらい', 'だるい'],
            'frustrated': ['イライラ', 'うまくいかない', '失敗', 'なんで', 'もう'],
            'focused': ['集中', '仕事', 'やる', '進める', '完成'],
            'relaxed': ['休憩', 'のんびり', 'ゆっくり', 'リラックス']
        }
        
        logger.info("✅ Personality Engine 準備完了")
    
    def _load_personality(self) -> Dict:
        """パーソナリティデータ読み込み"""
        if self.personality_db.exists():
            try:
                with open(self.personality_db, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        # デフォルトプロファイル
        return {
            'big_five': {
                'openness': 0.7,  # 開放性（新しいことへの好奇心）
                'conscientiousness': 0.85,  # 誠実性（計画性・責任感）
                'extraversion': 0.5,  # 外向性
                'agreeableness': 0.6,  # 協調性
                'neuroticism': 0.3  # 神経症傾向（ストレス耐性の逆）
            },
            'values': {
                'efficiency': 0.95,  # 効率性重視
                'cost_consciousness': 0.8,  # コスト意識
                'perfection': 0.88,  # 完璧主義
                'innovation': 0.75,  # 革新性
                'reliability': 0.9  # 信頼性重視
            },
            'emotion_history': [],
            'decision_history': [],
            'temporal_patterns': {}
        }
    
    def _save_personality(self):
        """パーソナリティデータ保存"""
        try:
            with open(self.personality_db, 'w') as f:
                json.dump(self.personality_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"パーソナリティ保存エラー: {e}")
    
    async def analyze_personality_from_text(self, text: str, 
                                           context: Dict = None) -> Dict:  # type: ignore
        """
        テキストから性格・感情を分析
        
        Args:
            text: 分析対象テキスト
            context: コンテキスト（時間帯、状況など）
            
        Returns:
            分析結果
        """
        logger.info(f"🔍 テキスト分析: '{text[:50]}...'")
        
        # 感情検出
        emotion = self._detect_emotion(text)
        
        # 価値観推定
        values_detected = self._infer_values(text)
        
        # 性格特性の更新
        personality_update = self._update_personality_traits(text, emotion)
        
        # 記録
        emotion_record = {
            'timestamp': datetime.now().isoformat(),
            'text': text[:200],
            'emotion': emotion,
            'values': values_detected,
            'context': context or {}
        }
        
        self.personality_data['emotion_history'].append(emotion_record)
        self.personality_data['emotion_history'] = \
            self.personality_data['emotion_history'][-1000:]
        
        self._save_personality()
        
        return {
            'emotion': emotion,
            'values_detected': values_detected,
            'personality_traits': self.personality_data['big_five'],
            'confidence': 0.7
        }
    
    def _detect_emotion(self, text: str) -> Dict:
        """感情検出"""
        text_lower = text.lower()
        
        emotion_scores = {}
        
        for emotion, keywords in self.emotion_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                emotion_scores[emotion] = score
        
        if not emotion_scores:
            return {'primary': 'neutral', 'intensity': 0.5}
        
        # 最も強い感情
        primary_emotion = max(emotion_scores.items(), key=lambda x: x[1])
        
        return {
            'primary': primary_emotion[0],
            'intensity': min(1.0, primary_emotion[1] * 0.3),
            'all_detected': emotion_scores
        }
    
    def _infer_values(self, text: str) -> List[str]:
        """価値観推定"""
        text_lower = text.lower()
        
        detected_values = []
        
        # 効率性
        if any(word in text_lower for word in ['効率', '速く', '時短', '最適化']):
            detected_values.append('efficiency')
        
        # コスト意識
        if any(word in text_lower for word in ['無料', '安い', '節約', 'コスト']):
            detected_values.append('cost_consciousness')
        
        # 完璧主義
        if any(word in text_lower for word in ['完璧', '完全', '全部', '徹底']):
            detected_values.append('perfection')
        
        # 革新性
        if any(word in text_lower for word in ['新しい', '最新', '革新', '進化']):
            detected_values.append('innovation')
        
        return detected_values
    
    def _update_personality_traits(self, text: str, emotion: Dict) -> Dict:
        """性格特性の更新（微調整）"""
        updates = {}
        
        text_lower = text.lower()
        
        # 完璧主義の検出（conscientiousness）
        if any(word in text_lower for word in ['全部', '完全', '完璧', '徹底的']):
            current = self.personality_data['big_five']['conscientiousness']
            self.personality_data['big_five']['conscientiousness'] = \
                min(1.0, current + 0.01)
            updates['conscientiousness'] = '+0.01'
        
        # 開放性の検出
        if any(word in text_lower for word in ['試したい', '新しい', 'やってみる']):
            current = self.personality_data['big_five']['openness']
            self.personality_data['big_five']['openness'] = \
                min(1.0, current + 0.01)
            updates['openness'] = '+0.01'
        
        # 神経症傾向（ストレス）
        if emotion['primary'] in ['tired', 'frustrated']:
            current = self.personality_data['big_five']['neuroticism']
            self.personality_data['big_five']['neuroticism'] = \
                min(1.0, current + 0.02)
            updates['neuroticism'] = '+0.02'
        elif emotion['primary'] in ['happy', 'relaxed']:
            current = self.personality_data['big_five']['neuroticism']
            self.personality_data['big_five']['neuroticism'] = \
                max(0.0, current - 0.01)
            updates['neuroticism'] = '-0.01'
        
        if updates:
            self._save_personality()
        
        return updates
    
    async def make_value_based_decision(self, options: List[Dict]) -> Dict:
        """
        価値観ベースの意思決定
        
        Args:
            options: 選択肢リスト [
                {'name': '選択肢A', 'efficiency': 0.9, 'cost': 0.3, ...},
                {'name': '選択肢B', 'efficiency': 0.6, 'cost': 0.9, ...}
            ]
            
        Returns:
            最適な選択肢 + 理由
        """
        logger.info(f"🤔 価値観ベース意思決定: {len(options)}個の選択肢")
        
        if not options:
            return {'error': '選択肢がありません'}
        
        scored_options = []
        
        for option in options:
            score = 0
            reasons = []
            
            # 各価値観に基づいてスコアリング
            for value, weight in self.personality_data['values'].items():
                if value in option:
                    value_score = option[value] * weight
                    score += value_score
                    
                    if value_score > 0.5:
                        reasons.append(f"{value}: {option[value]:.1%}")
            
            scored_options.append({
                'option': option,
                'score': score,
                'reasons': reasons
            })
        
        # 最高スコアの選択肢
        best_option = max(scored_options, key=lambda x: x['score'])
        
        logger.info(f"✅ 最適解: {best_option['option'].get('name', '不明')}")
        
        # 決定履歴に記録
        decision = {
            'timestamp': datetime.now().isoformat(),
            'options': [o['option'].get('name', str(o)) for o in options],
            'chosen': best_option['option'].get('name', '不明'),
            'score': best_option['score'],
            'reasons': best_option['reasons']
        }
        
        self.personality_data['decision_history'].append(decision)
        self.personality_data['decision_history'] = \
            self.personality_data['decision_history'][-100:]
        
        self._save_personality()
        
        return {
            'chosen': best_option['option'],
            'score': round(best_option['score'], 2),
            'reasons': best_option['reasons'],
            'confidence': min(1.0, best_option['score'] / len(self.personality_data['values']))
        }
    
    async def analyze_temporal_patterns(self) -> Dict:
        """時系列パターン分析（曜日・時間帯別の性格変化）"""
        logger.info("📊 時系列パターン分析中...")
        
        emotion_history = self.personality_data.get('emotion_history', [])
        
        if not emotion_history:
            return {'message': 'データ不足'}
        
        # 曜日別パターン
        weekday_emotions = {}
        
        # 時間帯別パターン
        hour_emotions = {}
        
        for record in emotion_history:
            try:
                dt = datetime.fromisoformat(record['timestamp'])
                weekday = dt.strftime('%A')
                hour = dt.hour
                
                emotion = record.get('emotion', {}).get('primary', 'neutral')
                
                # 曜日別集計
                if weekday not in weekday_emotions:
                    weekday_emotions[weekday] = {}
                weekday_emotions[weekday][emotion] = \
                    weekday_emotions[weekday].get(emotion, 0) + 1
                
                # 時間帯別集計
                if hour not in hour_emotions:
                    hour_emotions[hour] = {}
                hour_emotions[hour][emotion] = \
                    hour_emotions[hour].get(emotion, 0) + 1
                
            except:
                continue
        
        # 最も特徴的な曜日
        weekday_insights = {}
        for weekday, emotions in weekday_emotions.items():
            most_common = max(emotions.items(), key=lambda x: x[1])
            weekday_insights[weekday] = {
                'dominant_emotion': most_common[0],
                'count': most_common[1]
            }
        
        # 最も特徴的な時間帯
        hour_insights = {}
        for hour, emotions in hour_emotions.items():
            most_common = max(emotions.items(), key=lambda x: x[1])
            hour_insights[hour] = {
                'dominant_emotion': most_common[0],
                'count': most_common[1]
            }
        
        # パターンを保存
        self.personality_data['temporal_patterns'] = {
            'weekday': weekday_insights,
            'hourly': hour_insights,
            'last_updated': datetime.now().isoformat()
        }
        self._save_personality()
        
        return {
            'weekday_patterns': weekday_insights,
            'hourly_patterns': hour_insights
        }
    
    async def get_current_state(self) -> Dict:
        """現在の状態推定（性格・感情・推奨行動）"""
        now = datetime.now()
        hour = now.hour
        weekday = now.strftime('%A')
        
        # 時系列パターンから推定
        temporal = self.personality_data.get('temporal_patterns', {})
        
        current_hour_pattern = temporal.get('hourly', {}).get(hour, {})
        current_weekday_pattern = temporal.get('weekday', {}).get(weekday, {})
        
        # 最近の感情
        recent_emotions = self.personality_data.get('emotion_history', [])[-5:]
        recent_emotion = recent_emotions[-1].get('emotion', {}) if recent_emotions else {}
        
        # 推奨行動
        recommendations = []
        
        if current_hour_pattern.get('dominant_emotion') == 'tired':
            recommendations.append("この時間は疲労を感じやすい傾向です。休憩を取りませんか？")
        
        if current_hour_pattern.get('dominant_emotion') == 'focused':
            recommendations.append("集中力が高い時間帯です。重要なタスクに最適です。")
        
        if recent_emotion.get('primary') == 'frustrated':
            recommendations.append("イライラを検出。少し休憩してリフレッシュしましょう。")
        
        return {
            'timestamp': now.isoformat(),
            'personality_traits': self.personality_data['big_five'],
            'values': self.personality_data['values'],
            'current_emotion_estimate': current_hour_pattern.get('dominant_emotion', 'neutral'),
            'recent_emotion': recent_emotion.get('primary', 'neutral'),
            'recommendations': recommendations
        }


# テスト
async def test_personality():
    print("\n" + "="*70)
    print("🧪 Personality Engine - テスト")
    print("="*70)
    
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from core.unified_memory_api import UnifiedMemoryAPI
    
    memory_api = UnifiedMemoryAPI()
    personality = PersonalityEngine(memory_api)
    
    # テスト1: テキスト分析
    print("\n🔍 テスト1: 感情・性格分析")
    result = await personality.analyze_personality_from_text(
        "最高！全部完璧に完成した！効率的に進められて嬉しい！",
        {'time': '午前中'}
    )
    print(f"感情: {result['emotion']['primary']} (強度: {result['emotion']['intensity']:.1%})")
    print(f"価値観: {result['values_detected']}")
    
    # テスト2: 価値観ベース意思決定
    print("\n🤔 テスト2: 価値観ベース意思決定")
    options = [
        {'name': 'RunPod GPU', 'efficiency': 0.95, 'cost': 0.3, 'reliability': 0.9},
        {'name': 'ローカル実行', 'efficiency': 0.4, 'cost': 1.0, 'reliability': 0.7}
    ]
    decision = await personality.make_value_based_decision(options)
    print(f"選択: {decision['chosen']['name']}")
    print(f"スコア: {decision['score']}")
    print(f"理由: {', '.join(decision['reasons'])}")
    
    # テスト3: 現在状態
    print("\n🎭 テスト3: 現在の状態")
    state = await personality.get_current_state()
    print("性格特性:")
    for trait, value in state['personality_traits'].items():
        print(f"  {trait}: {value:.2f}")
    print(f"推奨: {len(state['recommendations'])}件")
    
    print("\n✅ テスト完了")


if __name__ == '__main__':
    asyncio.run(test_personality())

