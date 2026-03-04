"""
AI Simulator Behavior Analyzer
思考ログ分析と行動強化モデル
"""

import numpy as np
import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from collections import deque

@dataclass
class BehaviorLog:
    """行動ログ"""
    timestamp: float
    episode: int
    step: int
    action_type: str
    parameters: Dict[str, Any]
    state_before: Dict[str, Any]
    state_after: Dict[str, Any]
    reward: float
    success: bool

@dataclass
class BehaviorPattern:
    """行動パターン"""
    pattern_id: str
    action_type: str
    context: Dict[str, Any]
    success_rate: float
    average_reward: float
    usage_count: int
    last_used: float

@dataclass
class BehaviorRecommendation:
    """行動推奨"""
    recommended_action: str
    confidence: float
    reason: str
    similar_success_patterns: List[str]

class BehaviorAnalyzer:
    """行動分析クラス"""
    
    def __init__(self, buffer_size: int = 10000):
        self.buffer_size = buffer_size
        self.behavior_logs: deque = deque(maxlen=buffer_size)
        self.behavior_patterns: Dict[str, BehaviorPattern] = {}
        self.logger = self._setup_logger()
        
        # 統計情報
        self.statistics = {
            'total_logs': 0,
            'unique_actions': 0,
            'success_rate': 0.0,
            'average_reward': 0.0,
            'pattern_count': 0
        }
    
    def _setup_logger(self) -> logging.Logger:
        """ログ設定"""
        logger = logging.getLogger('behavior_analyzer')
        logger.setLevel(logging.INFO)
        
        handler = logging.FileHandler('/app/logs/behavior_analyzer.log')
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def log_behavior(self, behavior: BehaviorLog):
        """行動ログ記録"""
        self.behavior_logs.append(behavior)
        
        # 統計更新
        self.statistics['total_logs'] += 1
        
        # パターン分析
        self._analyze_pattern(behavior)
    
    def _analyze_pattern(self, behavior: BehaviorLog):
        """パターン分析"""
        # 行動タイプをキーとして使用
        action_key = behavior.action_type
        context_key = self._get_context_key(behavior.state_before)
        
        pattern_id = f"{action_key}_{context_key}"
        
        if pattern_id not in self.behavior_patterns:
            # 新規パターン作成
            pattern = BehaviorPattern(
                pattern_id=pattern_id,
                action_type=behavior.action_type,
                context=behavior.state_before,
                success_rate=1.0 if behavior.success else 0.0,
                average_reward=behavior.reward,
                usage_count=1,
                last_used=behavior.timestamp
            )
            self.behavior_patterns[pattern_id] = pattern
            self.statistics['pattern_count'] += 1
        else:
            # 既存パターン更新
            pattern = self.behavior_patterns[pattern_id]
            pattern.usage_count += 1
            pattern.last_used = behavior.timestamp
            
            # 成功率更新
            total_success = pattern.success_rate * (pattern.usage_count - 1) + (1.0 if behavior.success else 0.0)
            pattern.success_rate = total_success / pattern.usage_count
            
            # 平均報酬更新
            pattern.average_reward = (pattern.average_reward * (pattern.usage_count - 1) + behavior.reward) / pattern.usage_count
    
    def _get_context_key(self, state: Dict[str, Any]) -> str:
        """コンテキストキー取得"""
        # 状態の特徴量をハッシュ化
        state_vector = state.get('state_vector', [])
        if isinstance(state_vector, list):
            # 離散化
            discrete = [int(x * 10) for x in state_vector[:3]]  # 最初の3次元のみ
            return "_".join(map(str, discrete))
        return "unknown"
    
    def recommend_action(self, current_state: Dict[str, Any]) -> Optional[BehaviorRecommendation]:
        """行動推奨"""
        if not self.behavior_patterns:
            return None
        
        # 現在の状態に類似した成功パターンを検索
        context_key = self._get_context_key(current_state)
        
        # 関連パターンを取得
        relevant_patterns = [
            pattern for pattern in self.behavior_patterns.values()
            if pattern.context_key == context_key
        ]
        
        if not relevant_patterns:
            return None
        
        # 成功率の高いパターンを選択
        best_pattern = max(relevant_patterns, key=lambda p: p.success_rate)
        
        # 類似の成功パターン検索
        similar_patterns = [
            pattern.pattern_id
            for pattern in relevant_patterns
            if pattern.success_rate >= 0.7
            and pattern != best_pattern
        ][:3]
        
        recommendation = BehaviorRecommendation(
            recommended_action=best_pattern.action_type,
            confidence=best_pattern.success_rate,
            reason=f"Success rate: {best_pattern.success_rate:.2%}",
            similar_success_patterns=similar_patterns
        )
        
        return recommendation
    
    def get_statistics(self) -> Dict[str, Any]:
        """統計情報取得"""
        if not self.behavior_logs:
            return self.statistics
        
        # 行動ログから統計計算
        all_rewards = [log.reward for log in self.behavior_logs]
        successful_actions = [log for log in self.behavior_logs if log.success]
        
        self.statistics['unique_actions'] = len(set(log.action_type for log in self.behavior_logs))
        self.statistics['success_rate'] = len(successful_actions) / len(self.behavior_logs) if self.behavior_logs else 0.0
        self.statistics['average_reward'] = np.mean(all_rewards) if all_rewards else 0.0
        
        return self.statistics
    
    def get_top_patterns(self, limit: int = 10) -> List[BehaviorPattern]:
        """トップパターン取得"""
        sorted_patterns = sorted(
            self.behavior_patterns.values(),
            key=lambda p: (p.success_rate, p.usage_count),
            reverse=True
        )
        
        return sorted_patterns[:limit]
    
    def get_pattern_by_action_type(self, action_type: str) -> List[BehaviorPattern]:
        """アクションタイプ別パターン取得"""
        return [
            pattern for pattern in self.behavior_patterns.values()
            if pattern.action_type == action_type
        ]
    
    def export_analysis(self, filepath: str):
        """分析結果エクスポート"""
        data = {
            'statistics': self.statistics,
            'patterns': [asdict(pattern) for pattern in self.behavior_patterns.values()],
            'top_patterns': [asdict(pattern) for pattern in self.get_top_patterns(10)],
            'export_timestamp': datetime.now().isoformat()
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        self.logger.info(f"Analysis exported to {filepath}")
    
    def import_analysis(self, filepath: str):
        """分析結果インポート"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        self.statistics = data.get('statistics', self.statistics)
        
        # パターン復元
        for pattern_data in data.get('patterns', []):
            pattern = BehaviorPattern(**pattern_data)
            self.behavior_patterns[pattern.pattern_id] = pattern
        
        self.logger.info(f"Analysis imported from {filepath}")

class ReinforcementModel:
    """行動強化モデル"""
    
    def __init__(self, analyzer: BehaviorAnalyzer):
        self.analyzer = analyzer
        self.learning_rate = 0.1
        self.exploration_rate = 0.1
        self.logger = self._setup_logger()
    
    def _setup_logger(self) -> logging.Logger:
        """ログ設定"""
        logger = logging.getLogger('reinforcement_model')
        logger.setLevel(logging.INFO)
        
        handler = logging.FileHandler('/app/logs/reinforcement_model.log')
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def update_model(self, behavior: BehaviorLog):
        """モデル更新"""
        # 行動分析に記録
        self.analyzer.log_behavior(behavior)
        
        # 学習率調整（成功が多いほど学習率を下げる）
        if behavior.success:
            success_rate = self.analyzer.get_statistics()['success_rate']
            if success_rate > 0.8:
                self.learning_rate *= 0.99
                self.logger.debug(f"Decreasing learning rate to {self.learning_rate:.4f}")
    
    def get_reinforced_action(self, current_state: Dict[str, Any]) -> Optional[str]:
        """強化されたアクション取得"""
        # 推奨アクション取得
        recommendation = self.analyzer.recommend_action(current_state)
        
        if recommendation:
            # 探索率に基づいてランダムまたは推奨アクションを返す
            if np.random.random() < self.exploration_rate:
                self.logger.debug("Exploration: random action")
                return None  # ランダムアクション
            else:
                self.logger.debug(f"Exploitation: {recommendation.recommended_action}")
                return recommendation.recommended_action
        
        return None  # 推奨がなければランダム
    
    def get_recommendations(self, limit: int = 5) -> List[BehaviorRecommendation]:
        """推奨アクションリスト取得"""
        # 分析結果から推奨を生成
        top_patterns = self.analyzer.get_top_patterns(limit)
        
        recommendations = []
        for pattern in top_patterns:
            recommendation = BehaviorRecommendation(
                recommended_action=pattern.action_type,
                confidence=pattern.success_rate,
                reason=f"Success: {pattern.success_rate:.2%}, Used: {pattern.usage_count}",
                similar_success_patterns=[f"pattern_{i}" for i in range(3)]
            )
            recommendations.append(recommendation)
        
        return recommendations
    
    def get_model_statistics(self) -> Dict[str, Any]:
        """モデル統計取得"""
        return {
            'learning_rate': self.learning_rate,
            'exploration_rate': self.exploration_rate,
            'analyzer_statistics': self.analyzer.get_statistics(),
            'pattern_count': len(self.analyzer.behavior_patterns),
            'top_patterns': [
                {
                    'action': p.action_type,
                    'success_rate': p.success_rate,
                    'usage': p.usage_count
                }
                for p in self.analyzer.get_top_patterns(5)
            ]
        }

def main():
    """メイン関数"""
    import os
    os.makedirs('/app/logs', exist_ok=True)
    
    # 行動分析器と強化モデル作成
    analyzer = BehaviorAnalyzer()
    model = ReinforcementModel(analyzer)
    
    print("Behavior Analyzer and Reinforcement Model Test")
    
    # サンプル行動ログ作成
    for i in range(100):
        behavior = BehaviorLog(
            timestamp=time.time() + i,
            episode=i // 10,
            step=i % 10,
            action_type=['update_state', 'explore', 'exploit'][i % 3],
            parameters={'direction': [1, 0, 0, 0, 0]},
            state_before={'state_vector': [0.1, 0.2, 0.3, 0.4, 0.5]},
            state_after={'state_vector': [0.15, 0.25, 0.35, 0.45, 0.55]},
            reward=np.random.randn() * 0.1,
            success=np.random.random() > 0.5
        )
        
        model.update_model(behavior)
    
    # 統計表示
    stats = model.get_model_statistics()
    print("Model Statistics:")
    print(json.dumps(stats, indent=2))
    
    # 推奨取得
    current_state = {'state_vector': [0.1, 0.2, 0.3, 0.4, 0.5]}
    recommendation = model.get_reinforced_action(current_state)
    print(f"\nRecommended action: {recommendation}")
    
    # 分析エクスポート
    analyzer.export_analysis('/app/workspace/behavior_analysis.json')
    
    print("\nBehavior analysis test completed")

if __name__ == "__main__":
    import time
    main()