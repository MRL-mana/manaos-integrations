#!/usr/bin/env python3
"""Phase 2: DiscoRL比較実験 - PPO/Actor-Critic vs Disco103"""

import json
import numpy as np
from pathlib import Path
from datetime import datetime
import time

import jax
import jax.numpy as jnp
from absl import app, flags, logging

from disco_rl import agent  # type: ignore[attr-defined]
from disco_rl.environments import jittable_envs

# 設定フラグ
flags.DEFINE_integer('num_steps', 1000, 'Total training steps')
flags.DEFINE_string('output_dir', '/root/logs/discorl', 'Output directory')
flags.DEFINE_integer('seed', 42, 'Random seed')
FLAGS = flags.FLAGS


def run_experiment(update_rule_name, num_steps, seed, output_dir):
    """指定された更新ルールで実験を実行"""
    
    logging.info(f"\n{'='*60}")
    logging.info(f"Running experiment: {update_rule_name}")
    logging.info(f"{'='*60}")
    
    # JAX設定
    jax.config.update('jax_enable_x64', False)
    rng_key = jax.random.PRNGKey(seed)
    
    # 環境作成
    def get_env(batch_size):
        return jittable_envs.CatchJittableEnvironment(
            batch_size=batch_size, env_settings=jittable_envs.get_config_catch()
        )
    
    num_envs = 2
    env = get_env(num_envs)
    
    # エージェント設定
    if update_rule_name == 'disco':
        agent_settings = agent.get_settings_disco()
    elif update_rule_name == 'actor_critic':
        agent_settings = agent.get_settings_actor_critic()
    else:
        raise ValueError(f"Unknown update rule: {update_rule_name}")
    
    agent_settings.net_settings.name = 'mlp'
    agent_settings.net_settings.net_args = dict(
        dense=(512, 512),
        model_arch_name='lstm',
        head_w_init_std=1e-2,
        model_kwargs=dict(
            head_mlp_hiddens=(128,),
            lstm_size=128,
        ),
    )
    agent_settings.learning_rate = 1e-2
    
    agent_instance = agent.Agent(
        agent_settings=agent_settings,
        single_observation_spec=env.single_observation_spec(),
        single_action_spec=env.single_action_spec(),
        batch_axis_name='i',
    )
    
    # Disco103の重みを読み込む（Discoの場合のみ）
    if update_rule_name == 'disco':
        disco_103_fname = Path(__file__).parent / 'disco_103.npz'
        def unflatten_params(flat_params):
            params = {}
            for key_wb in flat_params:
                key = '/'.join(key_wb.split('/')[:-1])
                if key not in params:
                    params[key] = {}
                params[key][key_wb.split('/')[-1]] = flat_params[key_wb]
            return params
        
        with open(disco_103_fname, 'rb') as f:
            disco_103_params = unflatten_params(np.load(f))
        update_rule_params = disco_103_params
    else:
        update_rule_params = None
    
    # 初期状態
    env_state, ts = env.reset(rng_key)
    learner_state = agent_instance.initial_learner_state(rng_key)
    actor_state = agent_instance.initial_actor_state(rng_key)
    
    # メトリクス記録
    rewards_history = []
    
    start_time = time.time()
    
    # 学習ループ
    for step in range(num_steps):
        rng_key, actor_rng = jax.random.split(rng_key)
        
        try:
            actor_timestep, actor_state = agent_instance.actor_step(
                learner_state.params, actor_rng, ts, actor_state
            )
            
            env_state, ts = env.step(env_state, actor_timestep.actions)
            
            rewards_history.append(float(jnp.mean(actor_timestep.rewards)))
            
            if step % 200 == 0:
                avg_reward = np.mean(rewards_history[-100:]) if rewards_history else 0
                logging.info(f"Step {step:4d} | Avg reward: {avg_reward:.4f}")
                
        except Exception as e:
            logging.error(f"Error at step {step}: {e}")
            break
    
    elapsed_time = time.time() - start_time
    
    # 結果計算
    results = {
        'update_rule': update_rule_name,
        'num_steps': len(rewards_history),
        'elapsed_time': elapsed_time,
        'final_avg_reward': float(np.mean(rewards_history[-100:]) if rewards_history else 0),
        'final_std_reward': float(np.std(rewards_history[-100:]) if len(rewards_history) >= 100 else 0),
        'max_reward': float(np.max(rewards_history)) if rewards_history else 0,
        'min_reward': float(np.min(rewards_history)) if rewards_history else 0,
        'rewards_history': [float(r) for r in rewards_history],
    }
    
    # 結果保存
    output_path = Path(output_dir) / f'phase2_{update_rule_name}_{seed}.json'
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    logging.info(f"Results saved to: {output_path}")
    logging.info(f"Final avg reward: {results['final_avg_reward']:.4f}")
    
    return results


def main(argv):
    del argv
    
    logging.set_verbosity(logging.INFO)
    output_dir = Path(FLAGS.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 比較実験：各更新ルールを3回実行
    update_rules = ['actor_critic', 'disco']
    seeds = [42, 123, 456]
    
    all_results = {}
    
    for update_rule in update_rules:
        update_rule_results = []
        
        for seed in seeds:
            logging.info(f"\n{'='*60}")
            logging.info(f"Starting: {update_rule} with seed {seed}")
            logging.info(f"{'='*60}")
            
            results = run_experiment(
                update_rule_name=update_rule,
                num_steps=FLAGS.num_steps,
                seed=seed,
                output_dir=output_dir
            )
            
            update_rule_results.append(results)
        
        all_results[update_rule] = update_rule_results
    
    # 統計サマリー
    logging.info(f"\n{'='*60}")
    logging.info("Comparison Summary")
    logging.info(f"{'='*60}")
    
    for update_rule, results_list in all_results.items():
        avg_rewards = [r['final_avg_reward'] for r in results_list]
        mean_reward = np.mean(avg_rewards)
        std_reward = np.std(avg_rewards)
        
        logging.info(f"\n{update_rule.upper()}:")
        logging.info(f"  Mean final reward: {mean_reward:.4f} ± {std_reward:.4f}")
        logging.info(f"  Min: {np.min(avg_rewards):.4f}, Max: {np.max(avg_rewards):.4f}")
    
    # サマリーを保存
    summary = {
        'timestamp': datetime.now().isoformat(),
        'config': {
            'num_steps': FLAGS.num_steps,
            'seeds': seeds,
        },
        'results': all_results,
    }
    
    summary_path = output_dir / 'phase2_summary.json'
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    
    logging.info(f"\nSummary saved to: {summary_path}")
    logging.info("\nPhase 2 Comparison completed!")


if __name__ == '__main__':
    app.run(main)
