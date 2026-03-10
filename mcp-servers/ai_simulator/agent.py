"""
AI Simulator Agent
AI学習エージェントの実装
"""

import numpy as np
import random
import logging
import json
import time
from typing import Dict, List, Any
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod

from ai_simulator.ai_core.environment import EnvironmentState, Action

@dataclass
class AgentState:
    """エージェント状態"""
    episode: int
    step: int
    total_reward: float
    best_reward: float
    action_history: List[Action]
    learning_rate: float
    epsilon: float

class BaseAgent(ABC):
    """ベースエージェントクラス"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = self._setup_logger()
        self.state = AgentState(
            episode=0,
            step=0,
            total_reward=0.0,
            best_reward=float('-inf'),
            action_history=[],
            learning_rate=config.get('learning_rate', 0.01),
            epsilon=config.get('epsilon', 0.1)
        )
    
    def _setup_logger(self) -> logging.Logger:
        """ログ設定"""
        logger = logging.getLogger('agent')
        logger.setLevel(logging.INFO)
        
        handler = logging.FileHandler('/app/logs/agent.log')
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    @abstractmethod
    def select_action(self, state: EnvironmentState) -> Action:
        """アクション選択"""
        pass
    
    @abstractmethod
    def learn(self, state: EnvironmentState, action: Action, next_state: EnvironmentState):
        """学習"""
        pass
    
    @abstractmethod
    def update_policy(self):
        """ポリシー更新"""
        pass
    
    def reset(self):
        """リセット"""
        self.state.episode += 1
        self.state.step = 0
        self.state.total_reward = 0.0
        self.state.action_history = []

class SimpleLearningAgent(BaseAgent):
    """シンプル学習エージェント"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        # パラメータ設定
        self.state_size = config.get('state_size', 10)
        self.action_size = config.get('action_size', 5)
        self.learning_rate = config.get('learning_rate', 0.01)
        self.epsilon = config.get('epsilon', 0.1)
        self.epsilon_decay = config.get('epsilon_decay', 0.995)
        self.min_epsilon = config.get('min_epsilon', 0.01)
        
        # Qテーブル初期化
        self.q_table = np.random.rand(self.state_size, self.action_size) * 0.01
        
        # 経験リプレイバッファ
        self.experience_buffer = []
        self.buffer_size = config.get('buffer_size', 10000)
        
        # 学習統計
        self.training_stats = {
            'episodes': [],
            'rewards': [],
            'losses': []
        }
    
    def select_action(self, state: EnvironmentState) -> Action:
        """アクション選択（ε-greedy）"""
        # 状態のインデックス取得（シンプルなハッシュベース）
        state_index = self._get_state_index(state)
        
        # ε-greedy選択
        if random.random() < self.state.epsilon:
            # ランダムアクション
            action_type = 'update_state'
            parameters = {
                'direction': self._get_random_direction(),
                'magnitude': 0.1
            }
        else:
            # 最適アクション
            action_index = np.argmax(self.q_table[state_index])
            action_type = self._get_action_type(action_index)  # type: ignore
            parameters = {
                'direction': self._get_direction_from_index(action_index),  # type: ignore
                'magnitude': 0.1
            }
        
        action = Action(
            action_type=action_type,
            parameters=parameters,
            timestamp=time.time()
        )
        
        return action
    
    def learn(self, state: EnvironmentState, action: Action, next_state: EnvironmentState):
        """Q学習"""
        # 状態インデックス
        state_index = self._get_state_index(state)
        action_index = self._get_action_index(action)
        next_state_index = self._get_state_index(next_state)
        
        # Q値更新
        current_q = self.q_table[state_index, action_index]
        next_max_q = np.max(self.q_table[next_state_index])
        
        # ベルマン方程式
        new_q = current_q + self.state.learning_rate * (
            next_state.reward + 0.99 * next_max_q - current_q
        )
        
        self.q_table[state_index, action_index] = new_q
        
        # 経験バッファに追加
        experience = {
            'state': state.observations,
            'action': action,
            'reward': next_state.reward,
            'next_state': next_state.observations,
            'done': next_state.done
        }
        
        self.experience_buffer.append(experience)
        if len(self.experience_buffer) > self.buffer_size:
            self.experience_buffer.pop(0)
        
        # 統計更新
        self.state.total_reward += next_state.reward
        self.state.step += 1
    
    def update_policy(self):
        """ポリシー更新"""
        # ε減衰
        if self.state.epsilon > self.min_epsilon:
            self.state.epsilon *= self.epsilon_decay
        
        # ベストリワード更新
        if self.state.total_reward > self.state.best_reward:
            self.state.best_reward = self.state.total_reward
        
        # 統計記録
        self.training_stats['episodes'].append(self.state.episode)
        self.training_stats['rewards'].append(self.state.total_reward)
    
    def _get_state_index(self, state: EnvironmentState) -> int:
        """状態インデックス取得"""
        # シンプルなハッシュ関数
        state_vector = state.observations.get('state_vector', [])
        if isinstance(state_vector, list):
            state_vector = np.array(state_vector)
        
        # 状態ベクトルを離散化
        discrete_state = np.clip(
            (state_vector * self.state_size).astype(int),
            0,
            self.state_size - 1
        )
        
        # インデックス計算
        index = int(np.sum(discrete_state)) % self.state_size
        return index
    
    def _get_action_index(self, action: Action) -> int:
        """アクションインデックス取得"""
        # シンプルなマッピング
        if action.action_type == 'update_state':
            direction = action.parameters.get('direction', [])
            if direction:
                return abs(hash(str(direction))) % self.action_size
        return 0
    
    def _get_action_type(self, action_index: int) -> str:
        """アクションタイプ取得"""
        action_types = ['update_state', 'explore', 'exploit', 'observe', 'rest']
        return action_types[action_index % len(action_types)]
    
    def _get_random_direction(self) -> List[float]:
        """ランダム方向取得"""
        direction = np.random.randn(self.state_size)
        direction = direction / np.linalg.norm(direction) if np.linalg.norm(direction) > 0 else direction
        return direction.tolist()
    
    def _get_direction_from_index(self, action_index: int) -> List[float]:
        """インデックスから方向取得"""
        direction = np.zeros(self.state_size)
        direction[action_index % self.state_size] = 1.0
        return direction.tolist()
    
    def get_training_stats(self) -> Dict[str, Any]:
        """学習統計取得"""
        if not self.training_stats['rewards']:
            return {}
        
        return {
            'episode': self.state.episode,
            'total_reward': self.state.total_reward,
            'best_reward': self.state.best_reward,
            'average_reward': np.mean(self.training_stats['rewards'][-100:]),
            'epsilon': self.state.epsilon,
            'learning_rate': self.state.learning_rate
        }
    
    def save_model(self, filepath: str):
        """モデル保存"""
        model_data = {
            'q_table': self.q_table.tolist(),
            'state': asdict(self.state),
            'training_stats': self.training_stats
        }
        
        with open(filepath, 'w') as f:
            json.dump(model_data, f)
        
        self.logger.info(f"Model saved to {filepath}")
    
    def load_model(self, filepath: str):
        """モデル読み込み"""
        with open(filepath, 'r') as f:
            model_data = json.load(f)
        
        self.q_table = np.array(model_data['q_table'])
        # その他のデータも復元
        
        self.logger.info(f"Model loaded from {filepath}")

if __name__ == "__main__":
    # ログディレクトリ作成
    import os
    os.makedirs('/app/logs', exist_ok=True)
    
    # エージェント設定
    config = {
        'state_size': 5,
        'action_size': 5,
        'learning_rate': 0.01,
        'epsilon': 0.1,
        'epsilon_decay': 0.995,
        'buffer_size': 1000
    }
    
    # エージェント作成・テスト
    agent = SimpleLearningAgent(config)
    
    print("Agent Test")
    print(f"Q-table shape: {agent.q_table.shape}")
    
    # 統計表示
    stats = agent.get_training_stats()
    print(f"Training stats: {stats}")
    
    print("Agent test completed")