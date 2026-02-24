#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
from datetime import datetime, timedelta

# 最新のcheckpointを検索
import os
checkpoint_dir = r'D:\castle_ex_training\castle_ex_v1_0'
checkpoints = [d for d in os.listdir(checkpoint_dir) if d.startswith('checkpoint-') and os.path.isdir(os.path.join(checkpoint_dir, d))]
latest_checkpoint = max(checkpoints, key=lambda x: int(x.split('-')[1]))
latest_checkpoint_path = os.path.join(checkpoint_dir, latest_checkpoint, 'trainer_state.json')

# 最新のcheckpointの状態を読み込み
with open(latest_checkpoint_path, 'r', encoding='utf-8') as f:
    state = json.load(f)

current_step = state['global_step']
current_epoch = state['epoch']
total_epochs = 25  # 学習設定

# 経過時間とペース計算
start_time = datetime(2026, 1, 24, 0, 21, 25)
now = datetime.now()
elapsed = now - start_time
elapsed_hours = elapsed.total_seconds() / 3600

# checkpoint-750から最新まで
latest_step = state['global_step']
steps_progress = latest_step - 750
rate_per_hour = steps_progress / elapsed_hours

# 1エポックあたりのステップ数
steps_per_epoch = current_step / current_epoch if current_epoch > 0 else 0

# 残り計算
remaining_epochs = total_epochs - current_epoch
remaining_steps = steps_per_epoch * remaining_epochs
remaining_hours = remaining_steps / rate_per_hour if rate_per_hour > 0 else 0

# 終了予定時刻
estimated_end = now + timedelta(hours=remaining_hours)

print("=" * 60)
print("学習進捗状況")
print("=" * 60)
print(f"現在のステップ: {current_step}")
print(f"現在のエポック: {current_epoch:.2f} / {total_epochs}")
print(f"進捗率: {current_epoch/total_epochs*100:.1f}%")
print()
print(f"経過時間: {elapsed_hours:.2f}時間 ({elapsed})")
print(f"進捗ステップ: {steps_progress}ステップ (750 → 1100)")
print(f"学習ペース: {rate_per_hour:.2f}ステップ/時間")
print(f"1エポックあたり: {steps_per_epoch:.0f}ステップ")
print()
print("=" * 60)
print("終了予定")
print("=" * 60)
print(f"残りエポック: {remaining_epochs:.2f}")
print(f"残りステップ: {remaining_steps:.0f}")
print(f"残り時間: {remaining_hours:.1f}時間 ({remaining_hours/24:.1f}日)")
print(f"終了予定時刻: {estimated_end.strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)
