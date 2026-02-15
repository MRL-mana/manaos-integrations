#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CASTLE-EX 学習監視スクリプト
学習の進行状況を確認
"""

import sys
import json
from pathlib import Path

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except (AttributeError, ValueError, TypeError):
        pass

REPO_ROOT = Path(__file__).resolve().parents[1]


def check_training_progress(output_dir: str = "./outputs/castle_ex_v1_0"):
    """学習の進行状況を確認"""
    # どこから実行しても同じ結果になるように、リポジトリルート基準にする
    output_path = (REPO_ROOT / output_dir).resolve()
    
    print("=" * 60)
    print("CASTLE-EX 学習進行状況")
    print("=" * 60)
    print(f"出力ディレクトリ: {output_dir}")
    print()
    
    if not output_path.exists():
        print("[状態] 学習ディレクトリがまだ作成されていません")
        print("       → 学習は初期化段階です")
        return
    
    # チェックポイントの確認
    checkpoints = list(output_path.glob("checkpoint-*"))
    if checkpoints:
        print(f"[OK] チェックポイント: {len(checkpoints)}個見つかりました")
        latest = max(checkpoints, key=lambda p: int(p.name.split("-")[1]))
        print(f"     最新: {latest.name}")
    else:
        print("[状態] チェックポイントはまだ保存されていません")
        print("       → 学習は初期化または最初の500ステップ未満です")
    
    # ログディレクトリの確認
    logs_dir = output_path / "logs"
    if logs_dir.exists():
        log_files = list(logs_dir.glob("*.json"))
        if log_files:
            print(f"[OK] ログファイル: {len(log_files)}個見つかりました")
        else:
            print("[状態] ログファイルはまだ生成されていません")
    else:
        print("[状態] ログディレクトリがまだ作成されていません")
    
    # トレーニング状態の確認
    training_state_file = output_path / "trainer_state.json"
    if training_state_file.exists():
        try:
            with open(training_state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
            
            print("\n" + "=" * 60)
            print("学習状態")
            print("=" * 60)
            print(f"エポック: {state.get('epoch', 'N/A')}")
            print(f"ステップ: {state.get('global_step', 'N/A')}")
            last_loss = "N/A"
            if state.get("log_history"):
                last_loss = state.get("log_history", [{}])[-1].get("train_loss", "N/A")
            print(f"学習損失: {last_loss}")
            
            if state.get('best_metric'):
                print(f"ベストメトリック: {state.get('best_metric', 'N/A')}")
        except Exception as e:
            print(f"[警告] 学習状態の読み込みに失敗: {e}")
    else:
        print("\n[状態] 学習状態ファイルはまだ生成されていません")
    
    print("\n" + "=" * 60)
    print("次のアクション")
    print("=" * 60)
    print("1. TensorBoardで可視化:")
    print(f"   tensorboard --logdir {output_dir}/logs")
    print("2. チェックポイントから再開:")
    print(f"   python castle_ex/train_castle_ex_full.py --model {output_dir}")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='CASTLE-EX 学習監視')
    parser.add_argument('--output-dir', type=str, default='./outputs/castle_ex_v1_0',
                       help='出力ディレクトリ')
    args = parser.parse_args()
    
    check_training_progress(args.output_dir)
