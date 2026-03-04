#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CASTLE-EX 学習開始スクリプト
学習準備の確認と学習開始の案内
"""

import sys
import json
import subprocess
import os
from pathlib import Path

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except (AttributeError, ValueError, TypeError):
        pass

REPO_ROOT = Path(__file__).resolve().parents[1]

# 実行時は常にリポジトリルートを基準にする
try:
    os.chdir(REPO_ROOT)
except Exception:
    pass


def _first_existing(*candidates: str) -> Path:
    """
    互換のため複数候補から最初に存在するパスを返す。
    すべて無ければ先頭候補を返す（エラーメッセージ用）。
    """
    for rel in candidates:
        p = (REPO_ROOT / rel).resolve()
        if p.exists():
            return p
    return (REPO_ROOT / candidates[0]).resolve()


def check_files():
    """必要なファイルの存在確認"""
    required_files = {
        "データセット": [
            "castle_ex_dataset_v1_0_train.jsonl",
            "castle_ex_dataset_v1_0_eval.jsonl"
        ],
        "学習スケジュール": [
            "castle_ex_schedule_v1_0.json"
        ],
        "設定ファイル": [
            "castle_ex_training_config.yaml"
        ]
    }
    
    all_ok = True
    print("=" * 60)
    print("ファイル存在確認")
    print("=" * 60)
    
    for category, files in required_files.items():
        print(f"\n{category}:")
        for file in files:
            # 生成物/設定の置き場が変わっても動くように候補を持つ
            if file.endswith(".jsonl"):
                path = _first_existing(f"data/{file}", file, f"castle_ex/{file}")
            elif file.endswith(".yaml"):
                path = _first_existing(f"castle_ex/{file}", file)
            else:
                # schedule等
                path = _first_existing(f"castle_ex/{file}", file)
            if path.exists():
                # データセットの場合は件数も表示
                if file.endswith('.jsonl'):
                    try:
                        with open(path, 'r', encoding='utf-8') as f:
                            count = sum(1 for line in f if line.strip())
                        print(f"  [OK] {file} ({count}件)")
                    except Exception as e:
                        print(f"  [OK] {file} (件数取得失敗: {e})")
                else:
                    print(f"  [OK] {file}")
            else:
                print(f"  [NG] {file} (見つかりません)")
                all_ok = False
    
    return all_ok


def check_training_tools():
    """外部トレーナーの確認"""
    print("\n" + "=" * 60)
    print("外部トレーナー確認")
    print("=" * 60)
    
    tools = {
        "Axolotl": "axolotl",
        "LLaMA-Factory": "llama-factory"
    }
    
    available_tools = []
    for name, command in tools.items():
        try:
            result = subprocess.run(
                [command, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print(f"  [OK] {name} が利用可能です")
                available_tools.append((name, command))
            else:
                print(f"  [NG] {name} が見つかりません")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            print(f"  [NG] {name} が見つかりません")
        except Exception as e:
            print(f"  [NG] {name} の確認中にエラー: {e}")
    
    return available_tools


def load_schedule():
    """学習スケジュールを読み込んで表示"""
    schedule_path = Path("castle_ex_schedule_v1_0.json")
    if not schedule_path.exists():
        print("\n[エラー] 学習スケジュールファイルが見つかりません")
        return None
    
    with open(schedule_path, 'r', encoding='utf-8') as f:
        schedule = json.load(f)
    
    print("\n" + "=" * 60)
    print("学習スケジュール概要")
    print("=" * 60)
    print(f"総エポック数: {schedule['total_epochs']}")
    
    for phase_key, phase_info in schedule['phases'].items():
        epochs = phase_info['epochs']
        name = phase_info['name']
        print(f"\n{name} (Epoch {epochs[0]}-{epochs[-1]})")
        
        # 代表的なepochの設定を表示
        sample_epoch = epochs[len(epochs) // 2]
        epoch_config = schedule['epochs'][sample_epoch - 1]
        print(f"  Layer Weights: {epoch_config['layer_weights']}")
        print(f"  Negative Ratio: {epoch_config['negative_ratio']:.2f}")
    
    return schedule


def print_training_instructions(available_tools):
    """学習開始の指示を表示"""
    print("\n" + "=" * 60)
    print("学習開始手順")
    print("=" * 60)
    
    if available_tools:
        print("\n利用可能な外部トレーナーが見つかりました:")
        for name, command in available_tools:
            print(f"  - {name} ({command})")
        
        print("\n学習を開始するには、以下のコマンドを実行してください:")
        
        if any("axolotl" in tool[1] for tool in available_tools):
            print("\n[Axolotlの場合]")
            print("  axolotl train castle_ex/castle_ex_training_config.yaml")
        
        if any("llama-factory" in tool[1] for tool in available_tools):
            print("\n[LLaMA-Factoryの場合]")
            print("  llama-factory train \\")
            print("    --model_name_or_path <ベースモデル> \\")
            print("    --dataset castle_ex_dataset_v1_0_train.jsonl \\")
            print("    --output_dir ./outputs/castle_ex_v1_0 \\")
            print("    --num_train_epochs 25")
    else:
        print("\n外部トレーナーが見つかりませんでした。")
        print("以下のいずれかをインストールしてください:")
        print("  - Axolotl: https://github.com/OpenAccess-AI-Collective/axolotl")
        print("  - LLaMA-Factory: https://github.com/hiyouga/LLaMA-Factory")
    
    print("\n" + "=" * 60)
    print("重要事項")
    print("=" * 60)
    print("1. 各epochでlayer_weightsとnegative_ratioを適用してください")
    print("   (castle_ex/castle_ex_schedule_v1_0.json を優先して参照)")
    print("2. 学習完了後、評価を実行してください:")
    print("   python castle_ex/castle_ex_evaluator_fixed.py \\")
    print("     --eval-data castle_ex_dataset_v1_0_eval.jsonl \\")
    print("     --output evaluation_v1_0.json \\")
    print("     --model-type ollama --model <モデル名>")


def main():
    """メイン処理"""
    print("CASTLE-EX 学習開始準備チェック")
    print("=" * 60)
    
    # ファイル確認
    if not check_files():
        print("\n[エラー] 必要なファイルが不足しています")
        return 1
    
    # 外部トレーナー確認
    available_tools = check_training_tools()
    
    # 学習スケジュール表示
    schedule = load_schedule()
    
    # 学習開始指示
    print_training_instructions(available_tools)
    
    print("\n[OK] 準備確認完了")
    return 0


if __name__ == '__main__':
    sys.exit(main())
