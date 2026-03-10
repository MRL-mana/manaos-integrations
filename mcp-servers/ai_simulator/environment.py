"""
AI Simulator Environment
AI行動パターン学習のための仮想環境
"""

import numpy as np
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod
import time

@dataclass
class EnvironmentState:
    """環境状態"""
    step: int
    timestamp: float
    observations: Dict[str, Any]
    reward: float
    done: bool
    info: Dict[str, Any]

@dataclass
class Action:
    """アクション"""
    action_type: str
    parameters: Dict[str, Any]
    timestamp: float

class BaseEnvironment(ABC):
    """ベース環境クラス"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = self._setup_logger()
        self.step_count = 0
        self.episode_count = 0
        self.current_state: Optional[EnvironmentState] = None
        
    def _setup_logger(self) -> logging.Logger:
        """ログ設定"""
        logger = logging.getLogger('environment')
        logger.setLevel(logging.INFO)
        
        handler = logging.FileHandler('/app/logs/environment.log')
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    @abstractmethod
    def reset(self) -> EnvironmentState:
        """環境リセット"""
        pass
    
    @abstractmethod
    def step(self, action: Action) -> EnvironmentState:
        """ステップ実行"""
        pass
    
    @abstractmethod
    def get_action_space(self) -> List[str]:
        """アクション空間取得"""
        pass
    
    @abstractmethod
    def get_observation_space(self) -> Dict[str, Any]:
        """観測空間取得"""
        pass
    
    def render(self):
        """環境描画"""
        if self.current_state:
            print(f"Step: {self.current_state.step}")
            print(f"Reward: {self.current_state.reward}")
            print(f"Done: {self.current_state.done}")
            print(f"Info: {self.current_state.info}")

class SimpleLearningEnvironment(BaseEnvironment):
    """シンプルな学習環境"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.state_size = config.get('state_size', 10)
        self.action_size = config.get('action_size', 5)
        self.goal_state = np.random.rand(self.state_size)
        self.current_state_vector = None
        self.max_steps = config.get('max_steps', 100)
        self.success_threshold = config.get('success_threshold', 0.95)
        
    def reset(self) -> EnvironmentState:
        """環境リセット"""
        self.step_count = 0
        self.current_state_vector = np.random.rand(self.state_size)
        
        observations = {
            'state_vector': self.current_state_vector.tolist(),
            'goal_distance': float(np.linalg.norm(self.current_state_vector - self.goal_state))
        }
        
        state = EnvironmentState(
            step=self.step_count,
            timestamp=time.time(),
            observations=observations,
            reward=0.0,
            done=False,
            info={'episode': self.episode_count}
        )
        
        self.current_state = state
        self.episode_count += 1
        
        self.logger.info(f"Environment reset - Episode {self.episode_count}")
        
        return state
    
    def step(self, action: Action) -> EnvironmentState:
        """ステップ実行"""
        self.step_count += 1
        
        # アクション処理
        action_value = self._process_action(action)
        
        # 状態更新
        if action.action_type == 'update_state':
            self.current_state_vector = np.clip(
                self.current_state_vector + action_value,
                -1.0,
                1.0
            )
        
        # 報酬計算
        distance = np.linalg.norm(self.current_state_vector - self.goal_state)  # type: ignore[operator]
        reward = -distance  # 距離が近いほど報酬が高い
        
        # 終了条件チェック
        done = False
        if distance < self.success_threshold:
            reward += 10.0  # 成功ボーナス
            done = True
            self.logger.info(f"Goal reached! Distance: {distance:.4f}")
        
        if self.step_count >= self.max_steps:
            done = True
        
        # 状態情報更新
        observations = {
            'state_vector': self.current_state_vector.tolist(),  # type: ignore[union-attr]
            'goal_distance': float(distance)
        }
        
        info = {
            'episode': self.episode_count,
            'distance': float(distance),
            'action_type': action.action_type
        }
        
        state = EnvironmentState(
            step=self.step_count,
            timestamp=time.time(),
            observations=observations,
            reward=reward,  # type: ignore
            done=done,
            info=info
        )
        
        self.current_state = state
        
        return state
    
    def _process_action(self, action: Action) -> np.ndarray:
        """アクション処理"""
        if 'direction' in action.parameters:
            # 方向ベクトル処理
            direction = action.parameters['direction']
            magnitude = action.parameters.get('magnitude', 0.1)
            return np.array(direction) * magnitude
        else:
            # ランダムアクション
            return np.random.randn(self.state_size) * 0.1
    
    def get_action_space(self) -> List[str]:
        """アクション空間取得"""
        return [
            'update_state',
            'explore',
            'exploit',
            'observe',
            'rest'
        ]
    
    def get_observation_space(self) -> Dict[str, Any]:
        """観測空間取得"""
        return {
            'state_vector': {
                'shape': (self.state_size,),
                'dtype': 'float32',
                'range': (-1.0, 1.0)
            },
            'goal_distance': {
                'shape': (1,),
                'dtype': 'float32',
                'range': (0.0, float('inf'))
            }
        }
    
    def get_state_info(self) -> Dict[str, Any]:
        """状態情報取得"""
        if self.current_state:
            return {
                'step': self.current_state.step,
                'reward': self.current_state.reward,
                'done': self.current_state.done,
                'observations': self.current_state.observations
            }
        return {}
    
    def set_goal(self, goal_state: np.ndarray):
        """ゴール設定"""
        if goal_state.shape == (self.state_size,):
            self.goal_state = goal_state
            self.logger.info("New goal set")
        else:
            self.logger.error(f"Invalid goal shape: {goal_state.shape}")
    
    def get_goal(self) -> np.ndarray:
        """ゴール取得"""
        return self.goal_state.copy()

def create_environment(config: Dict[str, Any]) -> BaseEnvironment:
    """環境作成"""
    env_type = config.get('type', 'simple')
    
    if env_type == 'simple':
        return SimpleLearningEnvironment(config)
    else:
        raise ValueError(f"Unknown environment type: {env_type}")

if __name__ == "__main__":
    # ログディレクトリ作成
    import os
    os.makedirs('/app/logs', exist_ok=True)
    
    # 環境設定
    config = {
        'type': 'simple',
        'state_size': 5,
        'action_size': 5,
        'max_steps': 50,
        'success_threshold': 0.9
    }
    
    # 環境作成・テスト
    env = create_environment(config)
    
    # リセット
    state = env.reset()
    
    print("Environment Test")
    print(f"Observation space: {env.get_observation_space()}")
    print(f"Action space: {env.get_action_space()}")
    
    # いくつかのステップ実行
    for i in range(10):
        action = Action(
            action_type='update_state',
            parameters={
                'direction': [1, 0, 0, 0, 0],
                'magnitude': 0.1
            },
            timestamp=time.time()
        )
        
        state = env.step(action)
        
        print(f"Step {i+1}: Reward={state.reward:.4f}, Done={state.done}")
        
        if state.done:
            break
    
    print("Environment test completed")