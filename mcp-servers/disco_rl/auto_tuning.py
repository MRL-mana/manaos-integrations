#!/usr/bin/env python3
"""
DiscoRL Auto Hyperparameter Tuning
ハイパーパラメータ自動チューニングシステム

ManaOSの学習機能を使って最適なパラメータを自動発見
"""

import json
import itertools
import numpy as np
from pathlib import Path
from datetime import datetime
import time

import jax
import jax.numpy as jnp
from absl import app, flags, logging

from disco_rl import agent  # type: ignore[attr-defined]
from disco_rl.environments import jittable_envs
import sys
sys.path.append('/root/disco_rl_implementation')
from manaos_integration import DiscoRLManaOSBridge

flags.DEFINE_integer('max_iterations', 10, 'Maximum tuning iterations')
flags.DEFINE_string('output_dir', '/root/logs/discorl', 'Output directory')
FLAGS = flags.FLAGS


def run_experiment_with_config(config, num_steps=500, seed=42):
    """指定された設定で実験を実行"""
    
    jax.config.update('jax_enable_x64', False)
    rng_key = jax.random.PRNGKey(seed)
    
    # 環境作成
    def get_env(batch_size):
        return jittable_envs.CatchJittableEnvironment(
            batch_size=batch_size, env_settings=jittable_envs.get_config_catch()
        )
    
    env = get_env(2)
    
    # エージェント設定
    agent_settings = agent.get_settings_disco()
    agent_settings.net_settings.name = 'mlp'
    agent_settings.net_settings.net_args = dict(
        dense=config['dense_layers'],
        model_arch_name='lstm',
        head_w_init_std=config['head_w_init_std'],
        model_kwargs=dict(
            head_mlp_hiddens=config['head_mlp_hiddens'],
            lstm_size=config['lstm_size'],
        ),
    )
    agent_settings.learning_rate = config['learning_rate']
    
    agent_instance = agent.Agent(
        agent_settings=agent_settings,
        single_observation_spec=env.single_observation_spec(),
        single_action_spec=env.single_action_spec(),
        batch_axis_name='i',
    )
    
    # 初期状態
    env_state, ts = env.reset(rng_key)
    learner_state = agent_instance.initial_learner_state(rng_key)
    actor_state = agent_instance.initial_actor_state(rng_key)
    
    rewards_history = []
    
    for step in range(num_steps):
        rng_key, actor_rng = jax.random.split(rng_key)
        
        try:
            actor_timestep, actor_state = agent_instance.actor_step(
                learner_state.params, actor_rng, ts, actor_state
            )
            
            env_state, ts = env.step(env_state, actor_timestep.actions)
            rewards_history.append(float(jnp.mean(actor_timestep.rewards)))
            
        except Exception:
            break
    
    final_reward = np.mean(rewards_history[-100:]) if len(rewards_history) >= 100 else np.mean(rewards_history) if rewards_history else 0
    
    return {
        'config': config,
        'final_reward': float(final_reward),
        'num_steps': len(rewards_history),
        'rewards_history': [float(r) for r in rewards_history[:100]]  # 最初の100個だけ保存
    }


def main(argv):
    del argv
    
    logging.set_verbosity(logging.INFO)
    output_dir = Path(FLAGS.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # ManaOS統合
    bridge = DiscoRLManaOSBridge()
    
    logging.info("=" * 60)
    logging.info("DiscoRL Auto Hyperparameter Tuning")
    logging.info("=" * 60)
    
    # パラメータグリッド
    param_grid = {
        'learning_rate': [1e-3, 1e-2, 5e-2],
        'lstm_size': [64, 128],
        'head_mlp_hiddens': [(64,), (128,)],
        'head_w_init_std': [1e-2, 1e-3],
        'dense_layers': [(128, 128), (256, 256)],
    }
    
    # 全組み合わせ生成
    keys = param_grid.keys()
    values = param_grid.values()
    all_configs = [dict(zip(keys, v)) for v in itertools.product(*values)]
    
    # ManaOSから最良の設定を取得
    recommendations = bridge.get_recommendations()
    
    logging.info(f"\n探索空間: {len(all_configs)}通りの設定")
    logging.info(f"最大イテレーション: {FLAGS.max_iterations}")
    
    best_config = None
    best_reward = float('-inf')
    results = []
    
    # ランダムに設定を選択して実行
    np.random.seed(42)
    selected_configs = np.random.choice(len(all_configs), min(FLAGS.max_iterations, len(all_configs)), replace=False)
    
    for i, idx in enumerate(selected_configs):
        config = all_configs[idx]
        
        logging.info(f"\n{'='*60}")
        logging.info(f"Experiment {i+1}/{len(selected_configs)}")
        logging.info(f"Config: {config}")
        
        start_time = time.time()
        result = run_experiment_with_config(config, num_steps=500)
        elapsed_time = time.time() - start_time
        
        result['elapsed_time'] = elapsed_time
        results.append(result)
        
        logging.info(f"Final reward: {result['final_reward']:.4f}")
        logging.info(f"Elapsed time: {elapsed_time:.2f}s")
        
        # ManaOSに保存
        bridge.save_discorl_results(
            phase=f'AutoTuning_{i+1}',
            results=result,
            config=config
        )
        
        # 最良の設定を更新
        if result['final_reward'] > best_reward:
            best_reward = result['final_reward']
            best_config = config
            logging.info("🏆 New best config!")
    
    # サマリー
    logging.info(f"\n{'='*60}")
    logging.info("Tuning Summary")
    logging.info(f"{'='*60}")
    logging.info(f"Total experiments: {len(results)}")
    logging.info(f"Best reward: {best_reward:.4f}")
    logging.info(f"Best config: {best_config}")
    
    # 結果保存
    summary = {
        'timestamp': datetime.now().isoformat(),
        'total_experiments': len(results),
        'best_config': best_config,
        'best_reward': best_reward,
        'all_results': results
    }
    
    summary_path = output_dir / 'auto_tuning_summary.json'
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    
    logging.info(f"\nSummary saved to: {summary_path}")
    logging.info("Auto tuning completed!")


if __name__ == '__main__':
    app.run(main)
