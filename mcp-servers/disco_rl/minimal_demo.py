#!/usr/bin/env python3
"""DiscoRL Minimal Demo - Colabコードをベースにシンプルに"""

import collections
import jax
import jax.numpy as jnp
import numpy as np
from pathlib import Path
import json

from disco_rl import agent
from disco_rl.environments import base as base_env
from disco_rl.environments import jittable_envs

print("=" * 60)
print("DiscoRL Minimal Demo")
print("=" * 60)

# 設定
NUM_STEPS = 500
BATCH_SIZE = 8
ROLLOUT_LEN = 29
REPLAY_RATIO = 4
BUFFER_SIZE = 128
MIN_BUFFER_SIZE = 16
NUM_ENVS = BATCH_SIZE // REPLAY_RATIO
SEED = 42

# JAX設定
jax.config.update('jax_enable_x64', False)
rng_key = jax.random.PRNGKey(SEED)
devices = tuple(jax.devices()[:NUM_ENVS]) if NUM_ENVS > 0 else (jax.devices()[0],)

print("\nSettings:")
print(f"  NUM_STEPS: {NUM_STEPS}")
print(f"  BATCH_SIZE: {BATCH_SIZE}")
print(f"  NUM_ENVS: {NUM_ENVS}")
print(f"  Devices: {len(devices)} device(s)")

# 環境作成
def get_env(batch_size: int) -> base_env.Environment:
    return jittable_envs.CatchJittableEnvironment(
        batch_size=batch_size, env_settings=jittable_envs.get_config_catch()
    )

env = get_env(NUM_ENVS)

# エージェント設定
agent_settings = agent.get_settings_disco()
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

print("\nCreating agent...")
agent_instance = agent.Agent(
    agent_settings=agent_settings,
    single_observation_spec=env.single_observation_spec(),
    single_action_spec=env.single_action_spec(),
    batch_axis_name='i',
)

# Disco103の重みを読み込む
print("Loading Disco103 weights...")
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

print(f"  Loaded {len(disco_103_params)} parameter tensors")

# 初期状態
print("\nInitializing states...")
env_state, ts = env.reset(rng_key)
learner_state = agent_instance.initial_learner_state(rng_key)
actor_state = agent_instance.initial_actor_state(rng_key)
update_rule_params = disco_103_params

# Replay buffer（簡易版）
buffer = collections.deque(maxlen=BUFFER_SIZE)

# メトリクス
metrics_history = []
rewards_history = []

print("\nStarting training loop...")
print("=" * 60)

for step in range(NUM_STEPS):
    # Actor step
    rng_key, actor_rng = jax.random.split(rng_key)
    
    try:
        actor_timestep, actor_state = agent_instance.actor_step(
            learner_state.params, actor_rng, ts, actor_state
        )
        
        # 環境ステップ
        env_state, ts = env.step(env_state, actor_timestep.actions)
        
        # メトリクス記録
        rewards_history.append(float(jnp.mean(actor_timestep.rewards)))
        
        if step % 50 == 0:
            avg_reward = np.mean(rewards_history[-100:]) if rewards_history else 0
            print(f"Step {step:4d} | Avg reward: {avg_reward:.4f}")
            
    except Exception as e:
        print(f"Error at step {step}: {e}")
        break

print("=" * 60)
print("\nTraining completed!")
print(f"Final avg reward: {np.mean(rewards_history[-100:]) if rewards_history else 0:.4f}")

# 結果保存
output_dir = Path("/root/logs/discorl")
output_dir.mkdir(parents=True, exist_ok=True)

results = {
    'total_steps': len(rewards_history),
    'final_avg_reward': float(np.mean(rewards_history[-100:]) if rewards_history else 0),
    'max_reward': float(np.max(rewards_history)) if rewards_history else 0,
    'rewards_history': [float(r) for r in rewards_history],
}

with open(output_dir / 'minimal_results.json', 'w') as f:
    json.dump(results, f, indent=2)

print(f"\nResults saved to: {output_dir / 'minimal_results.json'}")
print("=" * 60)
