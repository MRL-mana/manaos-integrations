#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CASTLE-EX 学習実行スクリプト
学習開始の完全自動化
"""

import sys
import json
import subprocess
import os
from pathlib import Path

if sys.platform == 'win32':
    try:
        import io
        if not isinstance(sys.stdout, io.TextIOWrapper):
            if hasattr(sys.stdout, 'buffer') and not sys.stdout.buffer.closed:
                sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    except (AttributeError, ValueError, TypeError):
        pass

REPO_ROOT = Path(__file__).resolve().parents[1]

# 実行時は常にリポジトリルートを基準にする（cwd依存の事故防止）
try:
    os.chdir(REPO_ROOT)
except Exception:
    pass


def _first_existing(*candidates: str) -> Path:
    for rel in candidates:
        p = (REPO_ROOT / rel).resolve()
        if p.exists():
            return p
    return (REPO_ROOT / candidates[0]).resolve()


def check_environment():
    """環境確認"""
    print("=" * 60)
    print("環境確認")
    print("=" * 60)
    
    checks = {
        "Python": sys.version.split()[0],
        "作業ディレクトリ": str(Path.cwd()),
    }
    
    for name, value in checks.items():
        print(f"  {name}: {value}")
    
    return True


def verify_files():
    """ファイル確認"""
    print("\n" + "=" * 60)
    print("ファイル確認")
    print("=" * 60)
    
    required = {
        "castle_ex_dataset_v1_0_train.jsonl": "訓練データ",
        "castle_ex_dataset_v1_0_eval.jsonl": "評価データ",
        "castle_ex_schedule_v1_0.json": "学習スケジュール",
        "castle_ex_training_config.yaml": "設定ファイル",
        "castle_ex_evaluator_fixed.py": "評価ツール",
    }
    
    all_ok = True
    for file, desc in required.items():
        if file.endswith(".jsonl"):
            path = _first_existing(f"data/{file}", file, f"castle_ex/{file}")
        elif file.endswith(".yaml"):
            path = _first_existing(f"castle_ex/{file}", file)
        elif file.endswith(".py"):
            path = _first_existing(f"castle_ex/{file}", file)
        else:
            path = _first_existing(f"castle_ex/{file}", file)
        if path.exists():
            if file.endswith('.jsonl'):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        count = sum(1 for line in f if line.strip())
                    print(f"  [OK] {file} ({desc}, {count}件)")
                except Exception as e:
                    print(f"  [OK] {file} ({desc})")
            else:
                print(f"  [OK] {file} ({desc})")
        else:
            print(f"  [NG] {file} ({desc}) - 見つかりません")
            all_ok = False
    
    return all_ok


def check_training_tools():
    """外部トレーナー確認"""
    print("\n" + "=" * 60)
    print("外部トレーナー確認")
    print("=" * 60)
    
    tools = {
        "axolotl": "Axolotl",
        "llama-factory": "LLaMA-Factory"
    }
    
    available = []
    for cmd, name in tools.items():
        try:
            result = subprocess.run(
                [cmd, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print(f"  [OK] {name} が利用可能です")
                available.append((name, cmd))
            else:
                print(f"  [NG] {name} が見つかりません")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            print(f"  [NG] {name} が見つかりません")
        except Exception as e:
            print(f"  [NG] {name} の確認中にエラー: {e}")
    
    return available


def install_axolotl():
    """Axolotlのインストールを試行"""
    print("\n" + "=" * 60)
    print("Axolotlインストール試行")
    print("=" * 60)
    
    try:
        print("  pip install axolotl を実行中...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "axolotl"],
            capture_output=True,
            text=True,
            timeout=300
        )
        if result.returncode == 0:
            print("  [OK] Axolotlのインストールが完了しました")
            return True
        else:
            print(f"  [NG] Axolotlのインストールに失敗しました")
            print(f"  エラー: {result.stderr[:200]}")
            return False
    except subprocess.TimeoutExpired:
        print("  [NG] インストールがタイムアウトしました")
        return False
    except Exception as e:
        print(f"  [NG] インストール中にエラー: {e}")
        return False


def load_schedule():
    """学習スケジュール読み込み"""
    schedule_path = _first_existing("castle_ex/castle_ex_schedule_v1_0.json", "castle_ex_schedule_v1_0.json")
    if not schedule_path.exists():
        return None
    
    with open(schedule_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def print_schedule_summary(schedule):
    """スケジュール概要表示"""
    if not schedule:
        return
    
    print("\n" + "=" * 60)
    print("学習スケジュール概要")
    print("=" * 60)
    print(f"総エポック数: {schedule['total_epochs']}")
    
    for phase_key, phase_info in schedule['phases'].items():
        epochs = phase_info['epochs']
        name = phase_info['name']
        print(f"\n{name} (Epoch {epochs[0]}-{epochs[-1]})")
        
        sample_epoch = epochs[len(epochs) // 2]
        epoch_config = schedule['epochs'][sample_epoch - 1]
        print(f"  Layer Weights: {epoch_config['layer_weights']}")
        print(f"  Negative Ratio: {epoch_config['negative_ratio']:.2f}")


def generate_training_commands(available_tools):
    """学習コマンド生成"""
    print("\n" + "=" * 60)
    print("学習開始コマンド")
    print("=" * 60)
    
    if available_tools:
        for name, cmd in available_tools:
            if "axolotl" in cmd:
                print(f"\n[{name}の場合]")
                print("  axolotl train castle_ex/castle_ex_training_config.yaml")
            elif "llama-factory" in cmd:
                print(f"\n[{name}の場合]")
                print("  llama-factory train \\")
                print("    --model_name_or_path <ベースモデル> \\")
                print("    --dataset castle_ex_dataset_v1_0_train.jsonl \\")
                print("    --output_dir ./outputs/castle_ex_v1_0 \\")
                print("    --num_train_epochs 25")
    else:
        print("\n外部トレーナーが見つかりませんでした。")
        print("以下のいずれかをインストールしてください:")
        print("  - Axolotl: pip install axolotl")
        print("  - LLaMA-Factory: git clone https://github.com/hiyouga/LLaMA-Factory.git")


def create_training_script():
    """学習実行用バッチスクリプト作成"""
    print("\n" + "=" * 60)
    print("学習実行スクリプト生成")
    print("=" * 60)
    
    # Windows用バッチファイル
    batch_content = """@echo off
chcp 65001 > nul
echo ============================================================
echo CASTLE-EX 学習開始
echo ============================================================
echo.

REM Axolotlを使用する場合
if exist "axolotl" (
    echo Axolotlで学習を開始します...
    axolotl train castle_ex/castle_ex_training_config.yaml
    goto :end
)

REM LLaMA-Factoryを使用する場合
if exist "llama-factory" (
    echo LLaMA-Factoryで学習を開始します...
    llama-factory train ^
        --model_name_or_path <ベースモデル> ^
        --dataset castle_ex_dataset_v1_0_train.jsonl ^
        --output_dir ./outputs/castle_ex_v1_0 ^
        --num_train_epochs 25
    goto :end
)

echo [エラー] 外部トレーナーが見つかりません。
echo AxolotlまたはLLaMA-Factoryをインストールしてください。

:end
pause
"""
    
    batch_path = Path("start_training.bat")
    with open(batch_path, 'w', encoding='utf-8') as f:
        f.write(batch_content)
    print(f"  [OK] {batch_path} を生成しました")
    
    # Shellスクリプト（Linux/Mac用）
    shell_content = """#!/bin/bash
echo "============================================================"
echo "CASTLE-EX 学習開始"
echo "============================================================"
echo ""

# Axolotlを使用する場合
if command -v axolotl &> /dev/null; then
    echo "Axolotlで学習を開始します..."
    axolotl train castle_ex/castle_ex_training_config.yaml
    exit 0
fi

# LLaMA-Factoryを使用する場合
if command -v llama-factory &> /dev/null; then
    echo "LLaMA-Factoryで学習を開始します..."
    llama-factory train \\
        --model_name_or_path <ベースモデル> \\
        --dataset castle_ex_dataset_v1_0_train.jsonl \\
        --output_dir ./outputs/castle_ex_v1_0 \\
        --num_train_epochs 25
    exit 0
fi

echo "[エラー] 外部トレーナーが見つかりません。"
echo "AxolotlまたはLLaMA-Factoryをインストールしてください。"
exit 1
"""
    
    shell_path = Path("start_training.sh")
    with open(shell_path, 'w', encoding='utf-8') as f:
        f.write(shell_content)
    # 実行権限を付与（Unix系のみ）
    if sys.platform != 'win32':
        os.chmod(shell_path, 0o755)
    print(f"  [OK] {shell_path} を生成しました")


def main():
    """メイン処理"""
    print("CASTLE-EX 学習実行準備（完全自動化）")
    print("=" * 60)
    
    # 環境確認
    check_environment()
    
    # ファイル確認
    if not verify_files():
        print("\n[エラー] 必要なファイルが不足しています")
        return 1
    
    # 学習スケジュール表示
    schedule = load_schedule()
    print_schedule_summary(schedule)
    
    # 外部トレーナー確認
    available_tools = check_training_tools()
    
    # 外部トレーナーが無い場合、情報を表示
    if not available_tools:
        print("\n外部トレーナーが見つかりません。")
        print("以下のコマンドでインストールできます:")
        print("  pip install axolotl")
        print("  または")
        print("  git clone https://github.com/hiyouga/LLaMA-Factory.git")
        print("  cd LLaMA-Factory && pip install -e .")
    
    # 学習コマンド表示
    generate_training_commands(available_tools)
    
    # 学習実行スクリプト生成
    create_training_script()
    
    # 最終確認
    print("\n" + "=" * 60)
    print("準備完了")
    print("=" * 60)
    print("\n学習を開始するには:")
    if sys.platform == 'win32':
        print("  1. start_training.bat を実行")
        print("  または")
        print("  2. 上記のコマンドを手動で実行")
    else:
        print("  1. ./start_training.sh を実行")
        print("  または")
        print("  2. 上記のコマンドを手動で実行")
    
    print("\n学習完了後、評価を実行:")
    print("  python castle_ex/castle_ex_evaluator_fixed.py \\")
    print("    --eval-data castle_ex_dataset_v1_0_eval.jsonl \\")
    print("    --output evaluation_v1_0.json \\")
    print("    --model-type ollama --model <モデル名>")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
