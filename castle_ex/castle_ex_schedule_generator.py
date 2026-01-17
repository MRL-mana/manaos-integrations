#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CASTLE-EX 学習スケジュール生成ツール
Phase設計に基づいてepochごとのlayer_weightsとnegative_ratioを生成
"""

import json
import argparse
from pathlib import Path
import sys

if sys.platform == 'win32':
    try:
        import io
        if not isinstance(sys.stdout, io.TextIOWrapper):
            if hasattr(sys.stdout, 'buffer') and not sys.stdout.buffer.closed:
                sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    except (AttributeError, ValueError, TypeError):
        pass


def generate_schedule(
    total_epochs: int = 25,
    seed: str = "castle_ex_v1_0",
    output_file: str = "castle_ex_schedule_v1_0.json"
) -> dict:
    """
    学習スケジュールを生成
    
    Args:
        total_epochs: 総エポック数（デフォルト: 25）
        seed: シード（デフォルト: castle_ex_v1_0）
        output_file: 出力ファイル名
    
    Returns:
        スケジュール辞書
    """
    schedule = {
        "seed": seed,
        "total_epochs": total_epochs,
        "phases": {
            "phase_1": {"epochs": [1, 2, 3], "name": "ウォームアップ"},
            "phase_2": {"epochs": [4, 5, 6, 7, 8, 9, 10], "name": "因果と統合へ寄せる"},
            "phase_3": {"epochs": list(range(11, total_epochs + 1)), "name": "実戦"}
        },
        "epochs": []
    }
    
    # Phase 1: Epoch 1-3（ウォームアップ）
    # Layer配分: L0-2: 45% / L3-4: 25% / L5-6: 30%
    phase1_weights = {
        "0": 0.15,  # Layer 0
        "1": 0.20,  # Layer 1
        "2": 0.10,  # Layer 2
        "3": 0.15,  # Layer 3
        "4": 0.10,  # Layer 4
        "5": 0.20,  # Layer 5
        "6": 0.10   # Layer 6
    }
    phase1_negative_ratio = 0.25  # 荒れにくく
    
    # Phase 2: Epoch 4-10（因果と統合へ寄せる）
    # Layer配分: L0-2: 25% / L3-4: 25% / L5-6: 50%
    phase2_weights = {
        "0": 0.08,  # Layer 0
        "1": 0.10,  # Layer 1
        "2": 0.07,  # Layer 2
        "3": 0.12,  # Layer 3
        "4": 0.13,  # Layer 4
        "5": 0.30,  # Layer 5
        "6": 0.20   # Layer 6
    }
    phase2_negative_ratio = 0.30  # 境界を育てる
    
    # Phase 3: Epoch 11-25（実戦）
    # Layer配分: L0-2: 15% / L3-4: 20% / L5: 25% / L6: 40%
    phase3_weights = {
        "0": 0.05,  # Layer 0
        "1": 0.07,  # Layer 1
        "2": 0.03,  # Layer 2
        "3": 0.10,  # Layer 3
        "4": 0.10,  # Layer 4
        "5": 0.25,  # Layer 5
        "6": 0.40   # Layer 6
    }
    phase3_negative_ratio = 0.33  # 実戦の切れ味
    
    # 各epochの設定を生成
    for epoch in range(1, total_epochs + 1):
        if epoch <= 3:
            # Phase 1
            layer_weights = phase1_weights.copy()
            negative_ratio = phase1_negative_ratio
            phase = "phase_1"
        elif epoch <= 10:
            # Phase 2
            layer_weights = phase2_weights.copy()
            negative_ratio = phase2_negative_ratio
            phase = "phase_2"
        else:
            # Phase 3
            layer_weights = phase3_weights.copy()
            negative_ratio = phase3_negative_ratio
            phase = "phase_3"
        
        schedule["epochs"].append({
            "epoch": epoch,
            "phase": phase,
            "layer_weights": layer_weights,
            "negative_ratio": negative_ratio
        })
    
    # ファイルに保存
    output_path = Path(output_file)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(schedule, f, ensure_ascii=False, indent=2)
    
    print(f"[OK] 学習スケジュールを生成しました: {output_file}")
    print(f"  総エポック数: {total_epochs}")
    print(f"  Phase 1 (Epoch 1-3): ウォームアップ")
    print(f"  Phase 2 (Epoch 4-10): 因果と統合へ寄せる")
    print(f"  Phase 3 (Epoch 11-{total_epochs}): 実戦")
    
    return schedule


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description='CASTLE-EX学習スケジュール生成ツール')
    parser.add_argument('--epochs', type=int, default=25, help='総エポック数（デフォルト: 25）')
    parser.add_argument('--seed', type=str, default='castle_ex_v1_0', help='シード（デフォルト: castle_ex_v1_0）')
    parser.add_argument('--output', type=str, default='castle_ex_schedule_v1_0.json', help='出力ファイル名（デフォルト: castle_ex_schedule_v1_0.json）')
    
    args = parser.parse_args()
    
    schedule = generate_schedule(
        total_epochs=args.epochs,
        seed=args.seed,
        output_file=args.output
    )
    
    print("\n[OK] 学習スケジュール生成が完了しました")
    print(f"\n次のステップ:")
    print(f"  1. 学習を実行（schedule.jsonを参照）")
    print(f"  2. 評価を実行（evaluation_v1_0.jsonを出力）")
    print(f"  3. 評価結果を分析してv1.1データを生成")


if __name__ == '__main__':
    main()
