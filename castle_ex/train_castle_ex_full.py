#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CASTLE-EX 完全学習スクリプト（Transformers直接使用）
現在の環境（Python 3.10.6 + PyTorch + Transformers）で学習を実行
"""

import sys
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import argparse

if sys.platform == 'win32':
    try:
        import io
        if not isinstance(sys.stdout, io.TextIOWrapper):
            if hasattr(sys.stdout, 'buffer') and not sys.stdout.buffer.closed:
                sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    except (AttributeError, ValueError, TypeError):
        pass

try:
    import torch
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        TrainingArguments,
        Trainer,
        DataCollatorForLanguageModeling,
        BitsAndBytesConfig
    )
    from datasets import Dataset
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


def load_dataset_jsonl(jsonl_file: str) -> List[Dict]:
    """JSONLファイルからデータセットを読み込む"""
    data = []
    with open(jsonl_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
                data.append(item)
            except json.JSONDecodeError as e:
                print(f"[警告] 行{line_num}でJSON解析エラー: {e}")
    
    return data


def format_messages_for_training(item: Dict, tokenizer) -> str:
    """messages形式のデータを学習用テキストに変換"""
    messages = item.get("messages", [])
    if not messages:
        return ""
    
    # Phi-3形式のチャットテンプレートを使用
    # または、シンプルな形式でフォーマット
    formatted_parts = []
    
    # システムメッセージがある場合は最初に配置
    system_content = None
    for msg in messages:
        if msg.get("role") == "system":
            system_content = msg.get("content", "")
            break
    
    if system_content:
        formatted_parts.append(f"<|system|>\n{system_content}<|end|>\n")
    
    # ユーザーとアシスタントの対話をフォーマット
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        
        if role == "system":
            continue  # 既に処理済み
        elif role == "user":
            formatted_parts.append(f"<|user|>\n{content}<|end|>\n")
        elif role == "assistant":
            formatted_parts.append(f"<|assistant|>\n{content}<|end|>\n")
    
    return "".join(formatted_parts)


def preprocess_dataset(data: List[Dict], tokenizer, max_length: int = 2048):
    """データセットを前処理"""
    processed = []
    
    for idx, item in enumerate(data):
        if idx % 100 == 0:
            print(f"  前処理中: {idx}/{len(data)}件", end='\r')
        
        text = format_messages_for_training(item, tokenizer)
        if not text:
            continue
        
        # トークン化（labelsも含める）
        encoded = tokenizer(
            text,
            truncation=True,
            max_length=max_length,
            padding=False,
            return_tensors=None
        )
        
        # labelsはinput_idsと同じ（言語モデリング用）
        input_ids = encoded["input_ids"]
        labels = input_ids.copy()
        
        processed.append({
            "input_ids": input_ids,
            "labels": labels,
            "attention_mask": encoded.get("attention_mask", [1] * len(input_ids))
        })
    
    print(f"  前処理完了: {len(processed)}/{len(data)}件")
    return processed


def check_environment():
    """環境確認"""
    print("=" * 60)
    print("環境確認")
    print("=" * 60)
    
    print(f"Python: {sys.version.split()[0]}")
    
    if not TRANSFORMERS_AVAILABLE:
        print(f"[エラー] Transformersが利用できません: {IMPORT_ERROR}")
        return False
    
    print(f"PyTorch: {torch.__version__}")
    print(f"Transformers: 利用可能")
    
    if torch.cuda.is_available():
        print(f"CUDA: 利用可能 ({torch.cuda.get_device_name(0)})")
        print(f"CUDA Device Count: {torch.cuda.device_count()}")
    else:
        print("CUDA: 利用不可（CPUモード）")
    
    return True


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description='CASTLE-EX 完全学習スクリプト')
    parser.add_argument('--model', type=str, default='microsoft/Phi-3-mini-4k-instruct',
                       help='ベースモデル（デフォルト: microsoft/Phi-3-mini-4k-instruct）')
    parser.add_argument('--train-data', type=str, default='castle_ex_dataset_v1_0_train.jsonl',
                       help='訓練データファイル')
    parser.add_argument('--eval-data', type=str, default='castle_ex_dataset_v1_0_eval.jsonl',
                       help='評価データファイル')
    parser.add_argument('--output-dir', type=str, default='./outputs/castle_ex_v1_0',
                       help='出力ディレクトリ')
    parser.add_argument('--epochs', type=int, default=25,
                       help='エポック数（デフォルト: 25）')
    parser.add_argument('--batch-size', type=int, default=2,
                       help='バッチサイズ（デフォルト: 2）')
    parser.add_argument('--learning-rate', type=float, default=2.0e-5,
                       help='学習率（デフォルト: 2.0e-5）')
    parser.add_argument('--max-length', type=int, default=2048,
                       help='最大シーケンス長（デフォルト: 2048）')
    parser.add_argument('--check-only', action='store_true',
                       help='環境確認のみ実行（学習は実行しない）')
    
    args = parser.parse_args()
    
    print("CASTLE-EX 完全学習スクリプト")
    print("=" * 60)
    
    # 環境確認
    if not check_environment():
        print("\n[エラー] 必要なライブラリがインストールされていません")
        print("以下のコマンドでインストールしてください:")
        print("  pip install transformers datasets accelerate")
        return 1
    
    # ファイル確認
    train_file = Path(args.train_data)
    if not train_file.exists():
        print(f"\n[エラー] 訓練データが見つかりません: {train_file}")
        return 1
    
    eval_file = Path(args.eval_data)
    if not eval_file.exists():
        print(f"\n[警告] 評価データが見つかりません: {eval_file}")
        eval_file = None
    
    # 学習スケジュール読み込み
    schedule = load_schedule()
    if schedule:
        print(f"\n学習スケジュール: {schedule['total_epochs']}エポック")
        print(f"Phase 1 (Epoch 1-3): ウォームアップ")
        print(f"Phase 2 (Epoch 4-10): 因果と統合へ寄せる")
        print(f"Phase 3 (Epoch 11-25): 実戦")
    
    if args.check_only:
        print("\n[OK] 環境確認完了")
        return 0
    
    print("\n" + "=" * 60)
    print("データセット読み込み")
    print("=" * 60)
    
    # データセット読み込み
    print(f"訓練データを読み込み中: {train_file}")
    train_data = load_dataset_jsonl(str(train_file))
    print(f"  読み込み完了: {len(train_data)}件")
    
    if eval_file:
        print(f"評価データを読み込み中: {eval_file}")
        eval_data = load_dataset_jsonl(str(eval_file))
        print(f"  読み込み完了: {len(eval_data)}件")
    else:
        eval_data = None
    
    print("\n" + "=" * 60)
    print("モデルとトークナイザーの読み込み")
    print("=" * 60)
    
    print(f"モデル: {args.model}")
    print("読み込み中...")
    
    try:
        print("トークナイザーを読み込み中...")
        tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        print("[OK] トークナイザー読み込み完了")
        
        print("モデルを読み込み中...")
        # VRAM節約のため、低リソース設定を使用
        # FP16はTrainingArgumentsで処理するため、モデルロード時はFP32にしておく
        model = AutoModelForCausalLM.from_pretrained(
            args.model,
            torch_dtype=torch.float32,  # TrainingArgumentsのfp16で自動的にFP16に変換
            device_map="auto" if torch.cuda.is_available() else None,
            trust_remote_code=True,
            low_cpu_mem_usage=True,  # RAM節約
        )
        print("[OK] モデル読み込み完了")
        
        # Gradient Checkpointingを有効化（VRAM節約）
        if hasattr(model, 'gradient_checkpointing_enable'):
            model.gradient_checkpointing_enable()
            print("[OK] Gradient Checkpointingを有効化しました（VRAM節約）")
        
        if torch.cuda.is_available():
            print(f"GPUメモリ使用量: {torch.cuda.memory_allocated(0) / 1024**3:.2f}GB / {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f}GB")
    except Exception as e:
        print(f"[エラー] モデルの読み込みに失敗しました: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    print("\n" + "=" * 60)
    print("データセット前処理")
    print("=" * 60)
    
    print("訓練データを前処理中...")
    train_processed = preprocess_dataset(train_data, tokenizer, args.max_length)
    print(f"  前処理完了: {len(train_processed)}件")
    
    if eval_data:
        print("評価データを前処理中...")
        eval_processed = preprocess_dataset(eval_data, tokenizer, args.max_length)
        print(f"  前処理完了: {len(eval_processed)}件")
    else:
        eval_processed = None
    
    # Datasetオブジェクトに変換
    print("\nデータセットオブジェクトを作成中...")
    train_dataset = Dataset.from_list(train_processed)
    print(f"  訓練データセット: {len(train_dataset)}件")
    
    if eval_processed:
        eval_dataset = Dataset.from_list(eval_processed)
        print(f"  評価データセット: {len(eval_dataset)}件")
    else:
        eval_dataset = None
        print("  評価データセット: なし")
    
    print("\n" + "=" * 60)
    print("学習設定")
    print("=" * 60)
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # VRAM節約のための設定
    # RTX 5080 (15.9GB) では batch_size=2, max_length=2048 は厳しい
    # より安全な設定に調整
    effective_batch_size = args.batch_size * 4  # gradient_accumulation_steps=4
    print(f"実効バッチサイズ: {effective_batch_size}")
    
    training_args = TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        gradient_accumulation_steps=4,
        learning_rate=args.learning_rate,
        warmup_steps=100,
        logging_steps=100,
        save_steps=500,
        eval_steps=500 if eval_dataset else None,
        eval_strategy="steps" if eval_dataset else "no",  # evaluation_strategy -> eval_strategy
        save_strategy="steps",
        load_best_model_at_end=True if eval_dataset else False,
        metric_for_best_model="loss" if eval_dataset else None,
        greater_is_better=False if eval_dataset else None,
        fp16=torch.cuda.is_available(),
        bf16=False,
        dataloader_num_workers=0,  # Windowsでの互換性のため
        report_to="tensorboard",
        logging_dir=str(output_dir / "logs"),
        gradient_checkpointing=True,  # VRAM節約
        optim="adamw_torch",  # メモリ効率の良いオプティマイザ
    )
    
    print(f"出力ディレクトリ: {output_dir}")
    print(f"エポック数: {args.epochs}")
    print(f"バッチサイズ: {args.batch_size}")
    print(f"学習率: {args.learning_rate}")
    print(f"最大シーケンス長: {args.max_length}")
    
    # DataCollator
    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False,
    )
    
    print("\n" + "=" * 60)
    print("学習開始")
    print("=" * 60)
    
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        data_collator=data_collator,
    )
    
    try:
        trainer.train()
        print("\n[OK] 学習完了")
        
        # モデルを保存
        print(f"\nモデルを保存中: {output_dir}")
        trainer.save_model()
        tokenizer.save_pretrained(str(output_dir))
        print("[OK] モデル保存完了")
        
    except Exception as e:
        print(f"\n[エラー] 学習中にエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    print("\n" + "=" * 60)
    print("学習完了")
    print("=" * 60)
    print(f"\n学習済みモデル: {output_dir}")
    print("\n次のステップ:")
    print("  1. 評価を実行:")
    print(f"     python castle_ex_evaluator_fixed.py \\")
    print(f"       --eval-data {args.eval_data} \\")
    print(f"       --output evaluation_v1_0.json \\")
    print(f"       --model-type transformers \\")
    print(f"       --model {output_dir}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
