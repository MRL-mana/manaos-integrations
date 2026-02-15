#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CASTLE-EX 学習ヘルパースクリプト
学習スケジュールを読み込んで、外部トレーナー用の設定を生成
"""

import json
import argparse
from pathlib import Path
import sys

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except (AttributeError, ValueError, TypeError):
        pass


def load_schedule(schedule_file: str) -> dict:
    """学習スケジュールを読み込む"""
    schedule_path = Path(schedule_file)
    if not schedule_path.exists():
        raise FileNotFoundError(f"学習スケジュールファイルが見つかりません: {schedule_file}")
    
    with open(schedule_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def print_epoch_config(schedule: dict, epoch: int):
    """指定されたepochの設定を表示"""
    if epoch < 1 or epoch > schedule['total_epochs']:
        print(f"エラー: Epoch {epoch}は範囲外です（1-{schedule['total_epochs']}）")
        return
    
    epoch_config = schedule['epochs'][epoch - 1]
    
    print(f"\n=== Epoch {epoch} 設定 ===")
    print(f"Phase: {epoch_config['phase']}")
    print(f"Layer Weights:")
    for layer, weight in sorted(epoch_config['layer_weights'].items(), key=lambda x: int(x[0])):
        print(f"  Layer {layer}: {weight:.2f} ({weight*100:.1f}%)")
    print(f"Negative Ratio: {epoch_config['negative_ratio']:.2f} ({epoch_config['negative_ratio']*100:.1f}%)")
    
    # 学習率の推奨値（Phaseに応じて）
    if epoch <= 3:
        lr = 2.0e-5
    elif epoch <= 10:
        lr = 1.5e-5 - (epoch - 4) * 0.5e-5 / 7  # 1.5e-5 → 1e-5
    else:
        lr = 8e-6 - (epoch - 11) * 3e-6 / 15  # 8e-6 → 5e-6
    
    print(f"推奨学習率: {lr:.2e}")


def print_all_phases(schedule: dict):
    """全Phaseの設定を表示"""
    print("=" * 60)
    print("CASTLE-EX 学習スケジュール概要")
    print("=" * 60)
    
    print(f"\n総エポック数: {schedule['total_epochs']}")
    
    for phase_key, phase_info in schedule['phases'].items():
        epochs = phase_info['epochs']
        name = phase_info['name']
        print(f"\n{name} (Epoch {epochs[0]}-{epochs[-1]})")
        
        # 代表的なepochの設定を表示
        sample_epoch = epochs[len(epochs) // 2]
        print_epoch_config(schedule, sample_epoch)


def generate_training_summary(schedule_file: str, output_file: str = "training_summary.txt"):
    """学習サマリーを生成"""
    schedule = load_schedule(schedule_file)
    
    summary_lines = [
        "=" * 60,
        "CASTLE-EX 学習サマリー",
        "=" * 60,
        "",
        f"総エポック数: {schedule['total_epochs']}",
        "",
    ]
    
    for phase_key, phase_info in schedule['phases'].items():
        epochs = phase_info['epochs']
        name = phase_info['name']
        summary_lines.append(f"{name} (Epoch {epochs[0]}-{epochs[-1]})")
        
        # 代表的なepochの設定
        sample_epoch = epochs[len(epochs) // 2]
        epoch_config = schedule['epochs'][sample_epoch - 1]
        
        summary_lines.append(f"  Layer Weights: {epoch_config['layer_weights']}")
        summary_lines.append(f"  Negative Ratio: {epoch_config['negative_ratio']}")
        summary_lines.append("")
    
    summary_lines.extend([
        "=" * 60,
        "学習データ",
        "=" * 60,
        "訓練データ: castle_ex_dataset_v1_0_train.jsonl (3055件)",
        "評価データ: castle_ex_dataset_v1_0_eval.jsonl (354件)",
        "",
        "=" * 60,
        "次のステップ",
        "=" * 60,
        "1. 外部トレーナーで学習を実行",
        "2. 評価を実行（castle_ex_evaluator_fixed.py）",
        "3. 評価結果を分析",
        "4. v1.1データを生成",
    ])
    
    summary_text = "\n".join(summary_lines)
    
    if output_file:
        output_path = Path(output_file)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(summary_text)
        print(f"\n[OK] 学習サマリーを保存: {output_file}")
    
    print(summary_text)


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description='CASTLE-EX学習ヘルパー')
    parser.add_argument('--schedule', type=str, default='castle_ex_schedule_v1_0.json', help='学習スケジュールファイル')
    parser.add_argument('--epoch', type=int, default=None, help='特定のepochの設定を表示')
    parser.add_argument('--summary', type=str, default=None, help='学習サマリーを生成（ファイル名を指定）')
    
    args = parser.parse_args()
    
    schedule = load_schedule(args.schedule)
    
    if args.epoch:
        print_epoch_config(schedule, args.epoch)
    elif args.summary:
        generate_training_summary(args.schedule, args.summary)
    else:
        print_all_phases(schedule)
        print("\n[OK] 学習スケジュールを確認しました")
        print("\n次のステップ:")
        print("  1. 外部トレーナーで学習を実行")
        print("  2. 評価を実行（castle_ex_evaluator_fixed.py）")
        print("  3. 評価結果を分析")
        print("  4. v1.1データを生成")


if __name__ == '__main__':
    main()
