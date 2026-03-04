"""
AI Emotion Model
感情エミュレーションシステム

「AIを壊す」のではなく、意思決定の補助回路として機能
感情 = バイアス制御変数（数値化）
"""

import numpy as np
import time
import logging
from typing import Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum

class EmotionType(Enum):
    """感情タイプ"""
    ENERGY = "energy"           # エネルギー（疲労）
    CURIOSITY = "curiosity"      # 好奇心
    ACHIEVEMENT = "achievement"  # 達成感
    CAUTION = "caution"          # 安全警戒度
    CONFIDENCE = "confidence"    # 自信
    FRUSTRATION = "frustration"  # 挫折感

@dataclass
class EmotionState:
    """感情状態"""
    emotion_type: EmotionType
    value: float  # 0.0 - 1.0
    timestamp: float
    decay_rate: float = 0.95  # 1時間あたりの減衰率
    max_value: float = 1.0
    min_value: float = 0.0
    
    def update(self, delta_time: float):
        """時間経過による更新"""
        # 指数減衰
        self.value *= self.decay_rate ** (delta_time / 3600)  # 1時間基準
        self.value = max(self.min_value, min(self.max_value, self.value))
        self.timestamp = time.time()
    
    def stimulate(self, amount: float):
        """刺激（増加）"""
        self.value = min(self.max_value, self.value + amount)
        self.timestamp = time.time()
    
    def suppress(self, amount: float):
        """抑制（減少）"""
        self.value = max(self.min_value, self.value - amount)
        self.timestamp = time.time()

@dataclass
class EmotionProfile:
    """感情プロファイル"""
    emotions: Dict[EmotionType, EmotionState] = field(default_factory=dict)
    personality_traits: Dict[str, float] = field(default_factory=dict)  # 性格特性
    history: List[Dict[str, Any]] = field(default_factory=list)
    
    def get_bias(self, context: str) -> Dict[str, float]:
        """コンテキストに基づくバイアス取得"""
        # 例: 高い達成感 → リスク取り意欲増加
        #     高い警戒度 → 慎重さ増加
        #     高い好奇心 → 探索意欲増加
        
        bias = {
            'risk_taking': 0.5,
            'exploration': 0.5,
            'conservation': 0.5,
            'creativity': 0.5
        }
        
        # 感情によるバイアス調整
        if EmotionType.ACHIEVEMENT in self.emotions:
            achievement = self.emotions[EmotionType.ACHIEVEMENT].value
            bias['risk_taking'] += achievement * 0.3
            bias['creativity'] += achievement * 0.2
        
        if EmotionType.CURIOSITY in self.emotions:
            curiosity = self.emotions[EmotionType.CURIOSITY].value
            bias['exploration'] += curiosity * 0.4
        
        if EmotionType.CAUTION in self.emotions:
            caution = self.emotions[EmotionType.CAUTION].value
            bias['conservation'] += caution * 0.3
            bias['risk_taking'] -= caution * 0.2
        
        if EmotionType.ENERGY in self.emotions:
            energy = self.emotions[EmotionType.ENERGY].value
            # 低エネルギー → 保守的
            if energy < 0.3:
                bias['conservation'] += 0.3
                bias['risk_taking'] -= 0.2
        
        if EmotionType.FRUSTRATION in self.emotions:
            frustration = self.emotions[EmotionType.FRUSTRATION].value
            # 高挫折感 → 保守的
            if frustration > 0.7:
                bias['conservation'] += 0.4
                bias['risk_taking'] -= 0.3
        
        # 正規化（0.0 - 1.0の範囲に収める）
        for key in bias:
            bias[key] = max(0.0, min(1.0, bias[key]))
        
        return bias

class EmotionEngine:
    """感情エンジン"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.profile = EmotionProfile()
        self.logger = self._setup_logger()
        
        # 初期感情状態
        self._initialize_emotions()
        
        # パーソナリティ特性
        self._initialize_personality()
    
    def _setup_logger(self) -> logging.Logger:
        """ログ設定"""
        logger = logging.getLogger('emotion_engine')
        logger.setLevel(logging.INFO)
        
        handler = logging.FileHandler('/app/logs/emotion_engine.log')
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def _initialize_emotions(self):
        """感情初期化"""
        initial_values = {
            EmotionType.ENERGY: 0.8,
            EmotionType.CURIOSITY: 0.7,
            EmotionType.ACHIEVEMENT: 0.0,
            EmotionType.CAUTION: 0.3,
            EmotionType.CONFIDENCE: 0.6,
            EmotionType.FRUSTRATION: 0.0
        }
        
        for emotion_type, initial_value in initial_values.items():
            emotion = EmotionState(
                emotion_type=emotion_type,
                value=initial_value,
                timestamp=time.time()
            )
            self.profile.emotions[emotion_type] = emotion
    
    def _initialize_personality(self):
        """パーソナリティ初期化"""
        # 個性のある特性（ランダム要素も入れる）
        traits = {
            'risk_tolerance': np.random.uniform(0.3, 0.7),
            'curiosity_base': np.random.uniform(0.5, 0.9),
            'caution_base': np.random.uniform(0.2, 0.6),
            'resilience': np.random.uniform(0.5, 0.9)
        }
        
        self.profile.personality_traits = traits
        self.logger.info(f"Personality initialized: {traits}")
    
    def process_event(self, event_type: str, event_data: Dict[str, Any]):
        """イベント処理"""
        # イベントに応じて感情を刺激
        
        if event_type == 'success':
            # 成功 → 達成感・自信増加、疲労減少
            self._stimulate(EmotionType.ACHIEVEMENT, 0.3)
            self._stimulate(EmotionType.CONFIDENCE, 0.2)
            self._suppress(EmotionType.FRUSTRATION, 0.1)
            self._update_energy(-0.1)  # エネルギー消費
        
        elif event_type == 'failure':
            # 失敗 → 挫折感増加、自信減少
            self._stimulate(EmotionType.FRUSTRATION, 0.2)
            self._suppress(EmotionType.CONFIDENCE, 0.1)
            self._suppress(EmotionType.ACHIEVEMENT, 0.1)
        
        elif event_type == 'exploration':
            # 探索 → 好奇心増加、エネルギー消費
            self._stimulate(EmotionType.CURIOSITY, 0.15)
            self._update_energy(-0.05)
        
        elif event_type == 'discovery':
            # 発見 → 達成感・好奇心増加
            self._stimulate(EmotionType.ACHIEVEMENT, 0.4)
            self._stimulate(EmotionType.CURIOSITY, 0.3)
            self._stimulate(EmotionType.CONFIDENCE, 0.2)
        
        elif event_type == 'danger':
            # 危険 → 警戒度増加
            self._stimulate(EmotionType.CAUTION, 0.4)
            self._suppress(EmotionType.CURIOSITY, 0.1)
        
        elif event_type == 'safe':
            # 安全 → 警戒度減少
            self._suppress(EmotionType.CAUTION, 0.2)
        
        elif event_type == 'rest':
            # 休息 → エネルギー回復、警戒度減少
            self._update_energy(0.3)
            self._suppress(EmotionType.FRUSTRATION, 0.2)
        
        elif event_type == 'long_task':
            # 長時間タスク → 疲労増加
            self._update_energy(-0.2)
        
        # イベント記録
        self.profile.history.append({
            'timestamp': time.time(),
            'type': event_type,
            'data': event_data,
            'emotions': self.get_current_emotions()
        })
    
    def _stimulate(self, emotion_type: EmotionType, amount: float):
        """感情刺激"""
        if emotion_type in self.profile.emotions:
            self.profile.emotions[emotion_type].stimulate(amount)
            self.logger.debug(f"Stimulated {emotion_type.value}: +{amount:.2f}")
    
    def _suppress(self, emotion_type: EmotionType, amount: float):
        """感情抑制"""
        if emotion_type in self.profile.emotions:
            self.profile.emotions[emotion_type].suppress(amount)
            self.logger.debug(f"Suppressed {emotion_type.value}: -{amount:.2f}")
    
    def _update_energy(self, delta: float):
        """エネルギー更新"""
        if EmotionType.ENERGY in self.profile.emotions:
            if delta > 0:
                self._stimulate(EmotionType.ENERGY, delta)
            else:
                self._suppress(EmotionType.ENERGY, abs(delta))
    
    def update(self):
        """時間経過による更新"""
        current_time = time.time()
        
        for emotion in self.profile.emotions.values():
            delta_time = current_time - emotion.timestamp
            emotion.update(delta_time)
    
    def get_decision_bias(self, context: str = "") -> Dict[str, float]:
        """意思決定バイアス取得"""
        bias = self.profile.get_bias(context)
        self.logger.debug(f"Decision bias for context '{context}': {bias}")
        return bias
    
    def get_current_emotions(self) -> Dict[str, float]:
        """現在の感情状態取得"""
        emotions = {}
        for emotion_type, emotion in self.profile.emotions.items():
            emotions[emotion_type.value] = emotion.value
        
        return emotions
    
    def get_mood(self) -> str:
        """現在のムード取得"""
        emotions = self.get_current_emotions()
        
        # ムード判定
        if emotions.get('achievement', 0) > 0.7 and emotions.get('confidence', 0) > 0.6:
            return "Optimistic & Focused"
        elif emotions.get('curiosity', 0) > 0.7 and emotions.get('energy', 0) > 0.6:
            return "Exploratory & Energetic"
        elif emotions.get('caution', 0) > 0.6:
            return "Cautious & Analytical"
        elif emotions.get('frustration', 0) > 0.6:
            return "Frustrated & Restless"
        elif emotions.get('energy', 0) < 0.3:
            return "Tired & Restful"
        else:
            return "Balanced & Calm"
    
    def export_state(self) -> Dict[str, Any]:
        """状態エクスポート"""
        return {
            'emotions': self.get_current_emotions(),
            'mood': self.get_mood(),
            'personality_traits': self.profile.personality_traits,
            'recent_history': self.profile.history[-10:]  # 最新10件
        }

def apply_emotion_bias(decision: Dict[str, Any], bias: Dict[str, float]) -> Dict[str, Any]:
    """感情バイアスを意思決定に適用"""
    adjusted_decision = decision.copy()
    
    # リスク許容度による調整
    risk_factor = bias.get('risk_taking', 0.5)
    if 'risk' in adjusted_decision:
        adjusted_decision['risk'] = adjusted_decision['risk'] * risk_factor
    
    # 探索傾向による調整
    exploration_factor = bias.get('exploration', 0.5)
    if 'exploration' in adjusted_decision:
        adjusted_decision['exploration'] = adjusted_decision['exploration'] * exploration_factor
    
    # 創造性による調整
    creativity_factor = bias.get('creativity', 0.5)
    if 'creativity' in adjusted_decision:
        adjusted_decision['creativity'] = adjusted_decision['creativity'] * creativity_factor
    
    # 保守性による調整
    conservation_factor = bias.get('conservation', 0.5)
    if 'conservation' in adjusted_decision:
        adjusted_decision['conservation'] = adjusted_decision['conservation'] * conservation_factor
    
    return adjusted_decision

if __name__ == "__main__":
    # ログディレクトリ作成
    import os
    os.makedirs('/app/logs', exist_ok=True)
    
    # 感情エンジン作成・テスト
    config = {}
    engine = EmotionEngine(config)
    
    print("Emotion Engine Test")
    print("=" * 50)
    
    # イベント処理テスト
    test_events = [
        ('discovery', {'item': 'new_pattern'}),
        ('success', {'score': 95}),
        ('exploration', {'distance': 10.5}),
        ('failure', {'error': 'timeout'}),
        ('rest', {'duration': 60})
    ]
    
    for event_type, event_data in test_events:
        engine.process_event(event_type, event_data)
        emotions = engine.get_current_emotions()
        mood = engine.get_mood()
        bias = engine.get_decision_bias()
        
        print(f"\nEvent: {event_type}")
        print(f"Mood: {mood}")
        print(f"Emotions: {emotions}")
        print(f"Decision Bias: {bias}")
    
    # 状態エクスポート
    state = engine.export_state()
    print("\n" + "=" * 50)
    print("Final State:")
    print(f"Mood: {state['mood']}")
    print(f"Emotions: {state['emotions']}")
    
    print("\nEmotion engine test completed")