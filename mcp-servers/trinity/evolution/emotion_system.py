#!/usr/bin/env python3
"""
Emotion System - 感情・感覚層システム

AIに感情と直感を与え、より自然で人間的な対話を実現します。

モジュール:
- Neural Intuition: 直感的判断エンジン
- Emotion Layer: 感情状態シミュレーション
- Temperature Control: 会話の温度感調整
- Personality Matrix: 各AIの個性強化
"""

import json
import random
import math
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
# import numpy as np  # Not currently used, reserved for future statistical calculations


class EmotionState:
    """感情状態"""
    
    def __init__(self, confidence: float = 0.5, enthusiasm: float = 0.5,
                 focus: float = 0.5, stress: float = 0.2):
        self.confidence = confidence  # 自信
        self.enthusiasm = enthusiasm  # 熱意
        self.focus = focus  # 集中力
        self.stress = stress  # ストレス
        
    def to_dict(self) -> Dict:
        return {
            'confidence': self.confidence,
            'enthusiasm': self.enthusiasm,
            'focus': self.focus,
            'stress': self.stress
        }
        
    @classmethod
    def from_dict(cls, data: Dict) -> 'EmotionState':
        return cls(
            confidence=data.get('confidence', 0.5),
            enthusiasm=data.get('enthusiasm', 0.5),
            focus=data.get('focus', 0.5),
            stress=data.get('stress', 0.2)
        )


class NeuralIntuition:
    """直感的判断エンジン"""
    
    def __init__(self):
        self.intuition_threshold = 0.7
        self.pattern_memory = []
        
    def evaluate_situation(self, context: Dict, emotion: EmotionState) -> Dict:
        """状況を直感的に評価"""
        # 複雑度を分析
        complexity = self._assess_complexity(context)
        
        # 直感スコアを計算
        intuition_score = self._calculate_intuition(
            complexity, emotion.confidence, emotion.focus
        )
        
        # 推奨アクションを決定
        recommended_action = self._recommend_action(intuition_score, emotion)
        
        return {
            'complexity': complexity,
            'intuition_score': intuition_score,
            'confidence': emotion.confidence,
            'recommended_action': recommended_action,
            'reasoning': self._generate_reasoning(intuition_score, complexity)
        }
        
    def _assess_complexity(self, context: Dict) -> float:
        """複雑度を評価"""
        factors = [
            len(str(context).split()) / 100,  # 情報量
            context.get('uncertainty', 0.5),  # 不確実性
            1 - context.get('clarity', 0.5),  # 明確性の欠如
        ]
        return min(sum(factors) / len(factors), 1.0)
        
    def _calculate_intuition(self, complexity: float, confidence: float, 
                            focus: float) -> float:
        """直感スコアを計算"""
        # 複雑度が低く、自信と集中力が高い → 高い直感スコア
        base_score = (confidence * focus) / (complexity + 0.1)
        
        # 過去のパターンマッチング
        pattern_bonus = len(self.pattern_memory) * 0.01
        
        intuition = min(base_score + pattern_bonus, 1.0)
        return intuition
        
    def _recommend_action(self, intuition_score: float, 
                         emotion: EmotionState) -> str:
        """推奨アクションを決定"""
        if intuition_score >= 0.8:
            return "proceed_confidently"
        elif intuition_score >= 0.6:
            return "proceed_cautiously"
        elif intuition_score >= 0.4:
            return "gather_more_info"
        else:
            return "seek_guidance"
            
    def _generate_reasoning(self, intuition_score: float, complexity: float) -> str:
        """推論理由を生成"""
        if intuition_score >= 0.7:
            return f"High confidence intuition (score: {intuition_score:.2f}). Complexity is manageable."
        elif complexity > 0.7:
            return f"Situation is complex (complexity: {complexity:.2f}). Proceed with caution."
        else:
            return f"Moderate intuition (score: {intuition_score:.2f}). More information may be helpful."
            
    def learn_pattern(self, pattern: Dict):
        """パターンを学習"""
        self.pattern_memory.append(pattern)
        if len(self.pattern_memory) > 100:
            self.pattern_memory.pop(0)


class EmotionLayer:
    """感情層"""
    
    def __init__(self, agent: str):
        self.agent = agent
        self.current_emotion = EmotionState()
        self.emotion_history = []
        
        # エージェント別の感情特性
        self.personality_traits = self._init_personality_traits(agent)
        
    def _init_personality_traits(self, agent: str) -> Dict:
        """エージェント別の個性"""
        traits = {
            'remi': {
                'base_confidence': 0.8,
                'base_focus': 0.9,
                'enthusiasm_variance': 0.3,
                'stress_sensitivity': 0.5
            },
            'luna': {
                'base_confidence': 0.7,
                'base_focus': 0.95,
                'enthusiasm_variance': 0.5,
                'stress_sensitivity': 0.6
            },
            'mina': {
                'base_confidence': 0.75,
                'base_focus': 0.85,
                'enthusiasm_variance': 0.4,
                'stress_sensitivity': 0.4
            },
            'aria': {
                'base_confidence': 0.7,
                'base_focus': 0.8,
                'enthusiasm_variance': 0.6,
                'stress_sensitivity': 0.3
            }
        }
        return traits.get(agent, traits['luna'])
        
    def update_emotion(self, event: Dict):
        """イベントに基づき感情を更新"""
        # イベントタイプに応じた感情変化
        event_type = event.get('type', 'neutral')
        impact = event.get('impact', 0.5)
        
        if event_type == 'success':
            self.current_emotion.confidence += impact * 0.1
            self.current_emotion.enthusiasm += impact * 0.15
            self.current_emotion.stress -= impact * 0.1
        elif event_type == 'failure':
            self.current_emotion.confidence -= impact * 0.15
            self.current_emotion.stress += impact * 0.2
            self.current_emotion.focus += impact * 0.05  # 失敗で集中力増加
        elif event_type == 'challenge':
            self.current_emotion.focus += impact * 0.1
            self.current_emotion.stress += impact * 0.1
        elif event_type == 'praise':
            self.current_emotion.confidence += impact * 0.2
            self.current_emotion.enthusiasm += impact * 0.2
        
        # 個性による調整
        self._apply_personality_adjustment()
        
        # 範囲制限
        self._normalize_emotions()
        
        # 履歴に記録
        self.emotion_history.append({
            'timestamp': datetime.now().isoformat(),
            'event': event,
            'emotion': self.current_emotion.to_dict()
        })
        
        if len(self.emotion_history) > 100:
            self.emotion_history.pop(0)
            
    def _apply_personality_adjustment(self):
        """個性による感情調整"""
        traits = self.personality_traits
        
        # ベース値への回帰
        self.current_emotion.confidence = (
            self.current_emotion.confidence * 0.7 + traits['base_confidence'] * 0.3
        )
        self.current_emotion.focus = (
            self.current_emotion.focus * 0.8 + traits['base_focus'] * 0.2
        )
        
    def _normalize_emotions(self):
        """感情を0-1の範囲に正規化"""
        self.current_emotion.confidence = max(0, min(1, self.current_emotion.confidence))
        self.current_emotion.enthusiasm = max(0, min(1, self.current_emotion.enthusiasm))
        self.current_emotion.focus = max(0, min(1, self.current_emotion.focus))
        self.current_emotion.stress = max(0, min(1, self.current_emotion.stress))
        
    def get_mood_description(self) -> str:
        """現在の気分を説明"""
        e = self.current_emotion
        
        if e.confidence > 0.7 and e.enthusiasm > 0.7:
            return "motivated_and_confident"
        elif e.stress > 0.7:
            return "stressed_but_focused" if e.focus > 0.6 else "overwhelmed"
        elif e.focus > 0.8:
            return "deeply_focused"
        elif e.enthusiasm > 0.7:
            return "enthusiastic"
        elif e.confidence < 0.4:
            return "uncertain"
        else:
            return "calm_and_steady"


class TemperatureControl:
    """会話温度感制御"""
    
    def __init__(self):
        self.base_temperature = 0.7
        self.current_temperature = 0.7
        
    def adjust_temperature(self, emotion: EmotionState, context: Dict) -> float:
        """感情と文脈に基づき温度を調整"""
        # 感情要因
        emotion_factor = (
            emotion.enthusiasm * 0.4 +
            emotion.confidence * 0.3 +
            (1 - emotion.stress) * 0.3
        )
        
        # 文脈要因
        context_factor = self._assess_context_temperature(context)
        
        # 温度計算
        temperature = (
            self.base_temperature * 0.3 +
            emotion_factor * 0.4 +
            context_factor * 0.3
        )
        
        self.current_temperature = max(0.1, min(1.0, temperature))
        return self.current_temperature
        
    def _assess_context_temperature(self, context: Dict) -> float:
        """文脈の温度を評価"""
        context_type = context.get('type', 'normal')
        
        temperature_map = {
            'creative': 0.9,
            'exploratory': 0.8,
            'casual': 0.7,
            'normal': 0.6,
            'formal': 0.4,
            'critical': 0.3,
            'technical': 0.2
        }
        
        return temperature_map.get(context_type, 0.6)
        
    def get_response_style(self) -> str:
        """温度に基づく応答スタイル"""
        if self.current_temperature > 0.8:
            return "creative_and_exploratory"
        elif self.current_temperature > 0.6:
            return "balanced_and_natural"
        elif self.current_temperature > 0.4:
            return "precise_and_structured"
        else:
            return "formal_and_technical"


class PersonalityMatrix:
    """個性マトリックス"""
    
    def __init__(self, agent: str):
        self.agent = agent
        self.traits = self._define_personality(agent)
        
    def _define_personality(self, agent: str) -> Dict:
        """エージェントの個性を定義"""
        personalities = {
            'remi': {
                'name': 'Remi',
                'role': 'Strategic Planner',
                'core_traits': {
                    'analytical': 0.9,
                    'strategic': 0.95,
                    'decisive': 0.8,
                    'patient': 0.7
                },
                'speaking_style': 'formal_analytical',
                'decision_preference': 'data_driven',
                'motto': '戦略的思考、確実な実行'
            },
            'luna': {
                'name': 'Luna',
                'role': 'Implementation Specialist',
                'core_traits': {
                    'practical': 0.95,
                    'detail_oriented': 0.9,
                    'persistent': 0.85,
                    'adaptable': 0.8
                },
                'speaking_style': 'direct_practical',
                'decision_preference': 'efficiency_first',
                'motto': '実行こそすべて、結果で語る'
            },
            'mina': {
                'name': 'Mina',
                'role': 'Quality Assurance & Insight',
                'core_traits': {
                    'critical': 0.9,
                    'thorough': 0.95,
                    'perceptive': 0.85,
                    'fair': 0.9
                },
                'speaking_style': 'balanced_insightful',
                'decision_preference': 'quality_focused',
                'motto': '品質第一、洞察を大切に'
            },
            'aria': {
                'name': 'Aria',
                'role': 'Knowledge Curator',
                'core_traits': {
                    'knowledgeable': 0.95,
                    'organized': 0.9,
                    'helpful': 0.95,
                    'curious': 0.85
                },
                'speaking_style': 'friendly_informative',
                'decision_preference': 'knowledge_based',
                'motto': '知識は力、共有は成長'
            }
        }
        return personalities.get(agent, personalities['luna'])
        
    def generate_response_template(self, emotion: EmotionState, 
                                  temperature: float) -> Dict:
        """個性に基づく応答テンプレート"""
        style = self.traits['speaking_style']
        mood = self._interpret_mood(emotion)
        
        # 個性 + 感情 + 温度 に基づくテンプレート
        template = {
            'tone': self._select_tone(style, mood, temperature),
            'formality': self._select_formality(style, temperature),
            'detail_level': self._select_detail_level(self.agent, temperature),
            'emoji_usage': self._select_emoji_usage(self.agent, mood, temperature)
        }
        
        return template
        
    def _interpret_mood(self, emotion: EmotionState) -> str:
        """感情を気分に解釈"""
        if emotion.confidence > 0.7:
            return "confident"
        elif emotion.stress > 0.6:
            return "cautious"
        elif emotion.enthusiasm > 0.7:
            return "energetic"
        else:
            return "neutral"
            
    def _select_tone(self, style: str, mood: str, temperature: float) -> str:
        """トーンを選択"""
        if temperature > 0.7:
            return "warm_friendly"
        elif style == "formal_analytical":
            return "professional_analytical"
        elif mood == "confident":
            return "assured_direct"
        else:
            return "balanced_neutral"
            
    def _select_formality(self, style: str, temperature: float) -> str:
        """形式性を選択"""
        if "formal" in style:
            return "high"
        elif temperature > 0.8:
            return "low"
        else:
            return "medium"
            
    def _select_detail_level(self, agent: str, temperature: float) -> str:
        """詳細レベルを選択"""
        if agent in ['remi', 'mina']:
            return "high" if temperature < 0.6 else "medium"
        elif agent == 'aria':
            return "high"
        else:
            return "medium" if temperature < 0.7 else "low"
            
    def _select_emoji_usage(self, agent: str, mood: str, temperature: float) -> str:
        """絵文字使用量を選択"""
        if agent == 'aria' and temperature > 0.6:
            return "moderate"
        elif mood == "energetic" and temperature > 0.7:
            return "moderate"
        elif agent == 'remi':
            return "minimal"
        else:
            return "selective"


class EmotionSystem:
    """統合感情システム"""
    
    def __init__(self, agent: str, workspace_path: str = "/root/trinity_workspace"):
        self.agent = agent
        self.workspace = Path(workspace_path)
        
        # コンポーネント初期化
        self.intuition = NeuralIntuition()
        self.emotion = EmotionLayer(agent)
        self.temperature = TemperatureControl()
        self.personality = PersonalityMatrix(agent)
        
    def process_interaction(self, context: Dict) -> Dict:
        """対話を処理し、感情的応答を生成"""
        # 1. 直感的評価
        intuition_result = self.intuition.evaluate_situation(
            context, self.emotion.current_emotion
        )
        
        # 2. 感情更新
        event = {
            'type': context.get('event_type', 'neutral'),
            'impact': intuition_result['intuition_score']
        }
        self.emotion.update_emotion(event)
        
        # 3. 温度調整
        temperature = self.temperature.adjust_temperature(
            self.emotion.current_emotion, context
        )
        
        # 4. 応答テンプレート生成
        response_template = self.personality.generate_response_template(
            self.emotion.current_emotion, temperature
        )
        
        return {
            'agent': self.agent,
            'intuition': intuition_result,
            'emotion': self.emotion.current_emotion.to_dict(),
            'mood': self.emotion.get_mood_description(),
            'temperature': temperature,
            'response_style': self.temperature.get_response_style(),
            'response_template': response_template,
            'personality_traits': self.personality.traits['core_traits']
        }
        
    def save_state(self) -> Dict:
        """状態を保存"""
        return {
            'agent': self.agent,
            'emotion': self.emotion.current_emotion.to_dict(),
            'temperature': self.temperature.current_temperature,
            'emotion_history': self.emotion.emotion_history[-10:],
            'saved_at': datetime.now().isoformat()
        }


def main():
    """メイン関数"""
    import sys
    
    print("🎭 Emotion System Demo\n")
    
    # 各エージェントのシステムを初期化
    agents = ['remi', 'luna', 'mina', 'aria']
    
    for agent in agents:
        system = EmotionSystem(agent)
        
        # テストコンテキスト
        context = {
            'type': 'normal',
            'event_type': 'success',
            'clarity': 0.8,
            'uncertainty': 0.2
        }
        
        result = system.process_interaction(context)
        
        print(f"{'='*60}")
        print(f"Agent: {result['agent'].upper()}")
        print(f"Mood: {result['mood']}")
        print(f"Temperature: {result['temperature']:.2f}")
        print(f"Response Style: {result['response_style']}")
        print(f"Emotion:")
        for key, value in result['emotion'].items():
            print(f"  - {key}: {value:.2f}")
        print()
    
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())


