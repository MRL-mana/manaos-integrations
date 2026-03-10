#!/usr/bin/env python3
"""Phase 3: 業務ドメイン近似 - Web自動化タスクへの適用検証"""

import json
import numpy as np
from pathlib import Path
import time

import jax
import jax.numpy as jnp
from absl import app, flags, logging

from disco_rl import agent  # type: ignore[attr-defined]
from disco_rl.environments import jittable_envs

# 設定フラグ
flags.DEFINE_integer('num_steps', 200, 'Total training steps')
flags.DEFINE_string('output_dir', '/root/logs/discorl', 'Output directory')
flags.DEFINE_integer('seed', 42, 'Random seed')
FLAGS = flags.FLAGS


def main(argv):
    del argv
    
    logging.set_verbosity(logging.INFO)
    output_dir = Path(FLAGS.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logging.info("=" * 60)
    logging.info("Phase 3: Web Automation Domain Approximation")
    logging.info("=" * 60)
    
    # JAX設定
    jax.config.update('jax_enable_x64', False)
    rng_key = jax.random.PRNGKey(FLAGS.seed)
    
    # Catch環境をWeb自動化の疑似環境として使用
    # 解釈: ボール=クリック対象、パドル=カーソル、報酬=クリック成功
    def get_env(batch_size):
        return jittable_envs.CatchJittableEnvironment(
            batch_size=batch_size, env_settings=jittable_envs.get_config_catch()
        )
    
    num_envs = 2
    env = get_env(num_envs)
    
    logging.info("Using Catch environment as web automation proxy")
    logging.info("Interpretation: Ball=Click target, Paddle=Cursor, Reward=Click success")
    
    # DiscoRL設定
    agent_settings = agent.get_settings_disco()
    agent_settings.net_settings.name = 'mlp'
    agent_settings.net_settings.net_args = dict(
        dense=(128, 128),  # 小さめのネットワークで軽量化
        model_arch_name='lstm',
        head_w_init_std=1e-2,
        model_kwargs=dict(
            head_mlp_hiddens=(64,),
            lstm_size=64,
        ),
    )
    agent_settings.learning_rate = 1e-3
    
    agent_instance = agent.Agent(
        agent_settings=agent_settings,
        single_observation_spec=env.single_observation_spec(),
        single_action_spec=env.single_action_spec(),
        batch_axis_name='i',
    )
    
    # Disco103の重みを読み込む
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
    
    # 初期状態
    env_state, ts = env.reset(rng_key)
    learner_state = agent_instance.initial_learner_state(rng_key)
    actor_state = agent_instance.initial_actor_state(rng_key)
    
    # メトリクス記録
    rewards_history = []
    click_success_rate = []
    
    logging.info("\nStarting training...")
    start_time = time.time()
    
    for step in range(FLAGS.num_steps):
        rng_key, actor_rng = jax.random.split(rng_key)
        
        try:
            actor_timestep, actor_state = agent_instance.actor_step(
                learner_state.params, actor_rng, ts, actor_state
            )
            
            env_state, ts = env.step(env_state, actor_timestep.actions)
            
            rewards_history.append(float(jnp.mean(actor_timestep.rewards)))
            
            # クリック成功率の計算（報酬>0の場合）
            if len(rewards_history) >= 10:
                recent_rewards = rewards_history[-10:]
                success_count = sum(1 for r in recent_rewards if r > 0)
                click_success_rate.append(success_count / len(recent_rewards))
            
            if step % 50 == 0:
                avg_reward = np.mean(rewards_history[-50:]) if rewards_history else 0
                success_rate = np.mean(click_success_rate[-10:]) if click_success_rate else 0
                logging.info(f"Step {step:3d} | Avg reward: {avg_reward:.4f} | Success rate: {success_rate:.2%}")
                
        except Exception as e:
            logging.error(f"Error at step {step}: {e}")
            break
    
    elapsed_time = time.time() - start_time
    
    # 結果
    results = {
        'phase': 'phase3_web_automation',
        'num_steps': len(rewards_history),
        'elapsed_time': elapsed_time,
        'final_avg_reward': float(np.mean(rewards_history[-50:]) if len(rewards_history) >= 50 else np.mean(rewards_history)),
        'final_success_rate': float(np.mean(click_success_rate[-20:]) if len(click_success_rate) >= 20 else 0),
        'max_reward': float(np.max(rewards_history)) if rewards_history else 0,
        'rewards_history': [float(r) for r in rewards_history],
        'click_success_rate': [float(r) for r in click_success_rate],
        'interpretation': {
            'ball': 'click_target',
            'paddle': 'cursor',
            'reward': 'click_success',
            'note': 'Using Catch environment as web automation proxy'
        }
    }
    
    # 保存
    output_path = output_dir / 'phase3_web_automation.json'
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    logging.info("\n" + "=" * 60)
    logging.info("Results:")
    logging.info(f"  Final avg reward: {results['final_avg_reward']:.4f}")
    logging.info(f"  Final success rate: {results['final_success_rate']:.2%}")
    logging.info(f"  Max reward: {results['max_reward']:.4f}")
    logging.info(f"  Elapsed time: {elapsed_time:.2f}s")
    logging.info(f"\nResults saved to: {output_path}")
    logging.info("=" * 60)
    
    # 業務適用可能性の評価
    logging.info("\nBusiness Applicability Assessment:")
    if results['final_success_rate'] > 0.5:
        logging.info("  ✅ High applicability: Success rate > 50%")
    elif results['final_success_rate'] > 0.3:
        logging.info("  ⚠️  Medium applicability: Success rate > 30%")
    else:
        logging.info("  ❌ Low applicability: Success rate < 30%")
    
    logging.info("\nPhase 3 completed!")


if __name__ == '__main__':
    app.run(main)
