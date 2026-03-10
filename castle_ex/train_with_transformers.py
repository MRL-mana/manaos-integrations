#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CASTLE-EX 学習スクリプト（Transformers直接使用）
PyTorchとTransformersを使用して学習を実行
"""

import sys
import json
import os
from pathlib import Path
from typing import Dict, List, Optional

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]
    except (AttributeError, ValueError, TypeError):
        pass

try:
    import torch
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        TrainingArguments,
        Trainer,
        DataCollatorForLanguageModeling
    )
    from datasets import load_dataset
    TRANSFORMERS_AVAILABLE = True
except ImportError as e:
    TRANSFORMERS_AVAILABLE = False
    IMPORT_ERROR = str(e)


def load_schedule(schedule_file: str = "castle_ex_schedule_v1_0.json") -> Optional[Dict]:
    """学習スケジュールを読み込む"""
    schedule_path = Path(schedule_file)
    if not schedule_path.exists():
        print(f"[警告] 学習スケジュールファイルが見つかりません: {schedule_file}")
        return None
    
    with open(schedule_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_dataset_jsonl(jsonl_file: str):
    """JSONLファイルからデータセットを読み込む"""
    data = []
    with open(jsonl_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    item = json.loads(line)
                    data.append(item)
                except json.JSONDecodeError as e:
                    print(f"[警告] JSON解析エラー: {e}")
    
    return data


def format_messages_for_training(item: Dict) -> str:
    """messages形式のデータを学習用テキストに変換"""
    messages = item.get("messages", [])
    if not messages:
        return ""
    
    # シンプルなフォーマット: userとassistantを交互に
    formatted = ""
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "user":
            formatted += f"ユーザー: {content}\n"
        elif role == "assistant":
            formatted += f"アシスタント: {content}\n"
        elif role == "system":
            formatted += f"システム: {content}\n"
    
    return formatted.strip()


def check_environment():
    """環境確認"""
    print("=" * 60)
    print("環境確認")
    print("=" * 60)
    
    print(f"Python: {sys.version.split()[0]}")
    
    if TRANSFORMERS_AVAILABLE:
        print(f"PyTorch: {torch.__version__}")  # type: ignore[possibly-unbound]
        print(f"Transformers: 利用可能")
        if torch.cuda.is_available():  # type: ignore[possibly-unbound]
            print(f"CUDA: 利用可能 ({torch.cuda.get_device_name(0)})")  # type: ignore[possibly-unbound]
        else:
            print("CUDA: 利用不可（CPUモード）")
    else:
        print(f"[エラー] Transformersが利用できません: {IMPORT_ERROR}")
        return False
    
    return True


def main():
    """メイン処理"""
    print("CASTLE-EX 学習開始（Transformers直接使用）")
    print("=" * 60)
    
    # 環境確認
    if not check_environment():
        print("\n[エラー] 必要なライブラリがインストールされていません")
        print("以下のコマンドでインストールしてください:")
        print("  pip install transformers datasets accelerate")
        return 1
    
    # ファイル確認
    train_file = Path("castle_ex_dataset_v1_0_train.jsonl")
    if not train_file.exists():
        print(f"\n[エラー] 訓練データが見つかりません: {train_file}")
        return 1
    
    # 学習スケジュール読み込み
    schedule = load_schedule()
    if schedule:
        print(f"\n学習スケジュール: {schedule['total_epochs']}エポック")
    
    print("\n" + "=" * 60)
    print("学習設定")
    print("=" * 60)
    print("\n[注意] このスクリプトは基本的な学習フレームワークです。")
    print("実際の学習には以下が必要です:")
    print("  1. ベースモデルの指定")
    print("  2. 適切なハイパーパラメータの設定")
    print("  3. GPUリソース（推奨）")
    print("\n完全な学習を実行するには、以下のいずれかを選択してください:")
    print("  1. Python 3.11以上にアップグレードしてLLaMA-Factoryを使用")
    print("  2. Axolotlの依存関係を解決")
    print("  3. カスタム学習スクリプトを作成")
    
    print("\n" + "=" * 60)
    print("次のステップ")
    print("=" * 60)
    print("\n1. Python 3.11以上をインストール")
    print("2. LLaMA-Factoryを再インストール")
    print("   または")
    print("3. Axolotlの依存関係を解決")
    print("   または")
    print("4. カスタム学習スクリプトを作成")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
