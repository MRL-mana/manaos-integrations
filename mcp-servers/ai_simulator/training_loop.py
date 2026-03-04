"""
AI Simulator Training Loop
学習ループの実装
"""

import time
import logging
import json
from typing import Dict, List, Any
from dataclasses import dataclass, asdict

from ai_simulator.ai_core.environment import create_environment
from ai_simulator.ai_core.agent import SimpleLearningAgent

@dataclass
class TrainingMetrics:
    """学習メトリクス"""
    episode: int
    step: int
    total_reward: float
    average_reward: float
    best_reward: float
    epsilon: float
    elapsed_time: float
    timestamp: float

class TrainingLoop:
    """学習ループ"""
    
    def __init__(self, agent_config: Dict[str, Any], env_config: Dict[str, Any]):
        self.agent_config = agent_config
        self.env_config = env_config
        
        # エージェントと環境作成
        self.agent = SimpleLearningAgent(agent_config)
        self.env = create_environment(env_config)
        
        # ログ設定
        self.logger = self._setup_logger()
        
        # 学習統計
        self.metrics_history: List[TrainingMetrics] = []
        self.start_time = time.time()
        
        # 設定
        self.max_episodes = agent_config.get('max_episodes', 1000)
        self.save_interval = agent_config.get('save_interval', 100)
        self.log_interval = agent_config.get('log_interval', 10)
    
    def _setup_logger(self) -> logging.Logger:
        """ログ設定"""
        logger = logging.getLogger('training_loop')
        logger.setLevel(logging.INFO)
        
        handler = logging.FileHandler('/app/logs/training.log')
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def run_episode(self) -> TrainingMetrics:
        """エピソード実行"""
        state = self.env.reset()
        self.agent.reset()
        
        done = False
        step = 0
        
        while not done:
            # アクション選択
            action = self.agent.select_action(state)
            
            # ステップ実行
            next_state = self.env.step(action)
            
            # 学習
            self.agent.learn(state, action, next_state)
            
            # 状態更新
            state = next_state
            done = state.done
            step += 1
        
        # ポリシー更新
        self.agent.update_policy()
        
        # メトリクス計算
        agent_stats = self.agent.get_training_stats()
        
        metrics = TrainingMetrics(
            episode=self.agent.state.episode,
            step=step,
            total_reward=self.agent.state.total_reward,
            average_reward=agent_stats.get('average_reward', 0.0),
            best_reward=self.agent.state.best_reward,
            epsilon=self.agent.state.epsilon,
            elapsed_time=time.time() - self.start_time,
            timestamp=time.time()
        )
        
        self.metrics_history.append(metrics)
        
        return metrics
    
    def train(self) -> Dict[str, Any]:
        """学習実行"""
        self.logger.info("Starting training loop")
        
        for episode in range(1, self.max_episodes + 1):
            try:
                # エピソード実行
                metrics = self.run_episode()
                
                # ログ出力
                if episode % self.log_interval == 0:
                    self.logger.info(
                        f"Episode {episode}/{self.max_episodes} | "
                        f"Reward: {metrics.total_reward:.4f} | "
                        f"Best: {metrics.best_reward:.4f} | "
                        f"Epsilon: {metrics.epsilon:.4f}"
                    )
                
                # モデル保存
                if episode % self.save_interval == 0:
                    self._save_checkpoint(episode)
                
                # 早期終了条件チェック
                if self._check_early_stopping(metrics):
                    self.logger.info("Early stopping triggered")
                    break
                
            except KeyboardInterrupt:
                self.logger.info("Training interrupted by user")
                break
            except Exception as e:
                self.logger.error(f"Training error: {e}")
                continue
        
        # 最終モデル保存
        self._save_final_model()
        
        # 学習結果サマリー
        summary = self._generate_summary()
        
        return summary
    
    def _check_early_stopping(self, metrics: TrainingMetrics) -> bool:
        """早期終了条件チェック"""
        # 成功条件（例: 連続で高報酬）
        if len(self.metrics_history) >= 100:
            recent_rewards = [m.total_reward for m in self.metrics_history[-100:]]
            if all(r > 50.0 for r in recent_rewards[-10:]):
                return True
        
        return False
    
    def _save_checkpoint(self, episode: int):
        """チェックポイント保存"""
        checkpoint_path = f'/app/workspace/checkpoint_{episode}.json'
        self.agent.save_model(checkpoint_path)
        self.logger.info(f"Checkpoint saved: {checkpoint_path}")
    
    def _save_final_model(self):
        """最終モデル保存"""
        model_path = '/app/workspace/final_model.json'
        self.agent.save_model(model_path)
        self.logger.info(f"Final model saved: {model_path}")
    
    def _generate_summary(self) -> Dict[str, Any]:
        """学習結果サマリー生成"""
        if not self.metrics_history:
            return {}
        
        final_metrics = self.metrics_history[-1]
        
        summary = {
            'total_episodes': len(self.metrics_history),
            'total_time': final_metrics.elapsed_time,
            'final_reward': final_metrics.total_reward,
            'best_reward': final_metrics.best_reward,
            'average_reward': final_metrics.average_reward,
            'final_epsilon': final_metrics.epsilon,
            'training_stats': asdict(final_metrics)
        }
        
        return summary
    
    def get_current_metrics(self) -> TrainingMetrics:
        """現在のメトリクス取得"""
        if self.metrics_history:
            return self.metrics_history[-1]
        return TrainingMetrics(0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, time.time())
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """メトリクスサマリー取得"""
        if not self.metrics_history:
            return {}
        
        recent_metrics = self.metrics_history[-100:]  # 最新100エピソード
        
        rewards = [m.total_reward for m in recent_metrics]
        steps = [m.step for m in recent_metrics]
        epsilons = [m.epsilon for m in recent_metrics]
        
        return {
            'episodes': len(self.metrics_history),
            'average_reward': sum(rewards) / len(rewards),
            'best_reward': max(rewards),
            'worst_reward': min(rewards),
            'average_steps': sum(steps) / len(steps),
            'current_epsilon': epsilons[-1] if epsilons else 0.0,
            'training_progress': {
                'completed': len(self.metrics_history),
                'total': self.max_episodes,
                'percentage': (len(self.metrics_history) / self.max_episodes) * 100
            }
        }

def main():
    """メイン関数"""
    import os
    os.makedirs('/app/logs', exist_ok=True)
    os.makedirs('/app/workspace', exist_ok=True)
    
    # エージェント設定
    agent_config = {
        'state_size': 5,
        'action_size': 5,
        'learning_rate': 0.01,
        'epsilon': 0.1,
        'epsilon_decay': 0.995,
        'max_episodes': 100,
        'save_interval': 50,
        'log_interval': 10
    }
    
    # 環境設定
    env_config = {
        'type': 'simple',
        'state_size': 5,
        'action_size': 5,
        'max_steps': 50,
        'success_threshold': 0.9
    }
    
    # 学習ループ作成・実行
    training_loop = TrainingLoop(agent_config, env_config)
    
    print("Starting AI Simulator Training")
    print("=" * 50)
    
    summary = training_loop.train()
    
    print("=" * 50)
    print("Training completed!")
    print(f"Total episodes: {summary.get('total_episodes', 0)}")
    print(f"Best reward: {summary.get('best_reward', 0.0):.4f}")
    print(f"Average reward: {summary.get('average_reward', 0.0):.4f}")
    
    # メトリクスサマリー表示
    metrics_summary = training_loop.get_metrics_summary()
    print("\nMetrics Summary:")
    print(json.dumps(metrics_summary, indent=2))

if __name__ == "__main__":
    main()