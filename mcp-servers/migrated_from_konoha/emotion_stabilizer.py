#!/usr/bin/env python3
"""
Emotion Stabilizer - 感情安定化システム

感情パラメータの暴走を防ぎ、穏やかな変化を維持します。

機能:
- Dampening（減衰）: 時間経過で感情を穏やかに
- Baseline Regression: ベースライン（平常状態）への回帰
- Smoothing: 急激な変化を緩和
"""

import sys
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict
import math

workspace = Path("/root/trinity_workspace")
sys.path.insert(0, str(workspace / "evolution"))

from emotion_system import EmotionState


class EmotionStabilizer:
    """感情安定化システム"""
    
    def __init__(self, agent: str):
        self.agent = agent
        
        # 減衰率（1秒あたり）
        self.dampening_rate = 0.98  # 2%減衰/秒
        
        # ベースライン（個性に基づく平常状態）
        self.baseline = self._get_baseline(agent)
        
        # 回帰率（ベースラインへの引き戻し強度）
        self.regression_rate = 0.1  # 10%/更新
        
        # スムージング（移動平均用）
        self.history = []
        self.history_size = 5
        
    def _get_baseline(self, agent: str) -> EmotionState:
        """エージェントのベースライン感情"""
        baselines = {
            'remi': EmotionState(confidence=0.75, enthusiasm=0.6, focus=0.85, stress=0.15),
            'luna': EmotionState(confidence=0.7, enthusiasm=0.7, focus=0.9, stress=0.2),
            'mina': EmotionState(confidence=0.7, enthusiasm=0.65, focus=0.8, stress=0.15),
            'aria': EmotionState(confidence=0.65, enthusiasm=0.75, focus=0.75, stress=0.1)
        }
        return baselines.get(agent, EmotionState())
        
    def stabilize(self, emotion: EmotionState, delta_t: float = 1.0) -> EmotionState:
        """感情を安定化"""
        # 1. Dampening（減衰）
        emotion = self._apply_dampening(emotion, delta_t)
        
        # 2. Baseline Regression（ベースライン回帰）
        emotion = self._apply_regression(emotion)
        
        # 3. Smoothing（スムージング）
        emotion = self._apply_smoothing(emotion)
        
        # 4. Clamping（範囲制限）
        emotion = self._apply_clamping(emotion)
        
        return emotion
        
    def _apply_dampening(self, emotion: EmotionState, delta_t: float) -> EmotionState:
        """減衰を適用"""
        factor = self.dampening_rate ** delta_t
        
        # 極端な値ほど強く減衰
        if emotion.confidence > 0.9:
            emotion.confidence *= factor * 0.9
        elif emotion.confidence < 0.3:
            emotion.confidence = emotion.confidence + (0.5 - emotion.confidence) * 0.1
            
        if emotion.enthusiasm > 0.9:
            emotion.enthusiasm *= factor * 0.9
            
        if emotion.focus > 0.95:
            emotion.focus *= factor * 0.95
            
        # ストレスは速く減衰
        if emotion.stress > 0:
            emotion.stress *= factor ** 1.5
            
        return emotion
        
    def _apply_regression(self, emotion: EmotionState) -> EmotionState:
        """ベースラインへの回帰"""
        rate = self.regression_rate
        
        emotion.confidence = emotion.confidence * (1 - rate) + self.baseline.confidence * rate
        emotion.enthusiasm = emotion.enthusiasm * (1 - rate) + self.baseline.enthusiasm * rate
        emotion.focus = emotion.focus * (1 - rate) + self.baseline.focus * rate
        emotion.stress = emotion.stress * (1 - rate) + self.baseline.stress * rate
        
        return emotion
        
    def _apply_smoothing(self, emotion: EmotionState) -> EmotionState:
        """スムージング（移動平均）"""
        # 履歴に追加
        self.history.append(emotion.to_dict())
        if len(self.history) > self.history_size:
            self.history.pop(0)
            
        # 履歴が少ない場合はそのまま
        if len(self.history) < 2:
            return emotion
            
        # 移動平均計算
        avg = {
            'confidence': sum(h['confidence'] for h in self.history) / len(self.history),
            'enthusiasm': sum(h['enthusiasm'] for h in self.history) / len(self.history),
            'focus': sum(h['focus'] for h in self.history) / len(self.history),
            'stress': sum(h['stress'] for h in self.history) / len(self.history)
        }
        
        # 現在値と平均をブレンド（70%現在、30%平均）
        emotion.confidence = emotion.confidence * 0.7 + avg['confidence'] * 0.3
        emotion.enthusiasm = emotion.enthusiasm * 0.7 + avg['enthusiasm'] * 0.3
        emotion.focus = emotion.focus * 0.7 + avg['focus'] * 0.3
        emotion.stress = emotion.stress * 0.7 + avg['stress'] * 0.3
        
        return emotion
        
    def _apply_clamping(self, emotion: EmotionState) -> EmotionState:
        """範囲制限（0.0 ~ 1.0）"""
        emotion.confidence = max(0.0, min(1.0, emotion.confidence))
        emotion.enthusiasm = max(0.0, min(1.0, emotion.enthusiasm))
        emotion.focus = max(0.0, min(1.0, emotion.focus))
        emotion.stress = max(0.0, min(1.0, emotion.stress))
        
        return emotion
        
    def check_stability(self, emotion: EmotionState) -> Dict:
        """安定性をチェック"""
        # 変動を計算
        if len(self.history) < 2:
            variance = 0.0
        else:
            recent = self.history[-5:] if len(self.history) >= 5 else self.history
            variances = []
            
            for key in ['confidence', 'enthusiasm', 'focus', 'stress']:
                values = [h[key] for h in recent]
                avg = sum(values) / len(values)
                var = sum((v - avg) ** 2 for v in values) / len(values)
                variances.append(var)
                
            variance = sum(variances) / len(variances)
            
        # ベースラインからの距離
        distance_from_baseline = math.sqrt(
            (emotion.confidence - self.baseline.confidence) ** 2 +
            (emotion.enthusiasm - self.baseline.enthusiasm) ** 2 +
            (emotion.focus - self.baseline.focus) ** 2 +
            (emotion.stress - self.baseline.stress) ** 2
        )
        
        # 安定性スコア（0-1、高いほど安定）
        stability_score = 1.0 - min(variance * 10, 1.0) - min(distance_from_baseline * 0.5, 0.5)
        stability_score = max(0.0, min(1.0, stability_score))
        
        return {
            'variance': variance,
            'distance_from_baseline': distance_from_baseline,
            'stability_score': stability_score,
            'status': self._get_stability_status(stability_score)
        }
        
    def _get_stability_status(self, score: float) -> str:
        """安定性ステータス"""
        if score >= 0.8:
            return 'stable'
        elif score >= 0.6:
            return 'moderately_stable'
        elif score >= 0.4:
            return 'unstable'
        else:
            return 'highly_unstable'


def test_stabilizer():
    """テスト実行"""
    print("🧪 Emotion Stabilizer Test\n")
    
    stabilizer = EmotionStabilizer('luna')
    
    # テスト: 極端な感情
    print("Test 1: Extreme emotion")
    extreme_emotion = EmotionState(confidence=1.0, enthusiasm=1.0, focus=1.0, stress=0.0)
    print(f"  Before: confidence={extreme_emotion.confidence:.3f}")
    
    stabilized = stabilizer.stabilize(extreme_emotion, delta_t=1.0)
    print(f"  After:  confidence={stabilized.confidence:.3f}")
    print()
    
    # テスト: 10秒間の安定化
    print("Test 2: 10-second stabilization")
    emotion = EmotionState(confidence=0.9, enthusiasm=0.85, focus=0.95, stress=0.3)
    
    for i in range(10):
        emotion = stabilizer.stabilize(emotion, delta_t=1.0)
        stability = stabilizer.check_stability(emotion)
        
        print(f"  {i+1}s: confidence={emotion.confidence:.3f}, "
              f"stability={stability['stability_score']:.3f} ({stability['status']})")
        time.sleep(0.1)  # 速度デモ用
        
    print()
    print("✅ Test complete")


if __name__ == '__main__':
    test_stabilizer()


