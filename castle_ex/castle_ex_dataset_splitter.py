#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CASTLE-EX データセット分割ツール（ハッシュベース固定分割）
再現性を保つため、メッセージハッシュでtrain/evalを固定分割
"""

import json
import hashlib
import argparse
from pathlib import Path
from typing import List, Dict, Tuple
import sys

if sys.platform == 'win32':
    try:
        import io
        if not isinstance(sys.stdout, io.TextIOWrapper):
            if hasattr(sys.stdout, 'buffer') and not sys.stdout.buffer.closed:
                sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    except (AttributeError, ValueError, TypeError):
        pass


def get_message_hash(messages: List[Dict]) -> str:
    """メッセージからハッシュを生成（重複除去と同じロジック）"""
    if not messages:
        return ""
    
    # メッセージを正規化して結合
    normalized_parts = []
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        # 正規化（空白・句読点・絵文字・全角半角を統一）
        content_normalized = content.lower().strip()
        # 数字と固有名詞は保持（重複除去と同じロジック）
        normalized_parts.append(f"{role}:{content_normalized}")
    
    combined = "|".join(normalized_parts)
    return hashlib.md5(combined.encode('utf-8')).hexdigest()


def split_dataset(
    input_file: str,
    train_ratio: float = 0.9,
    eval_ratio: float = 0.1,
    output_dir: str = ".",
    seed_hash: str = "castle_ex_v1_0"
) -> Tuple[str, str]:
    """
    データセットをtrain/evalに分割（ハッシュベース固定分割）
    
    Args:
        input_file: 入力JSONLファイル
        train_ratio: 訓練データの割合（デフォルト: 0.9）
        eval_ratio: 評価データの割合（デフォルト: 0.1）
        output_dir: 出力ディレクトリ
        seed_hash: 分割の再現性を保つためのシードハッシュ
    
    Returns:
        (train_file, eval_file) のタプル
    """
    input_path = Path(input_file)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # データ読み込み
    print(f"データセット読み込み: {input_file}")
    all_data = []
    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                all_data.append(json.loads(line))
    
    print(f"  総データ数: {len(all_data)}件")
    
    # ハッシュベースで分割（再現性確保）
    train_data = []
    eval_data = []
    
    for item in all_data:
        # メッセージハッシュを取得
        messages = item.get("messages", [])
        msg_hash = get_message_hash(messages)
        
        # シードハッシュと組み合わせて決定論的に分割
        combined_hash = hashlib.md5(f"{seed_hash}:{msg_hash}".encode('utf-8')).hexdigest()
        hash_int = int(combined_hash[:8], 16)  # 最初の8文字を整数に変換
        hash_ratio = hash_int / (16 ** 8)  # 0.0-1.0の範囲に正規化
        
        if hash_ratio < train_ratio:
            train_data.append(item)
        else:
            eval_data.append(item)
    
    # 統計情報
    print(f"\n分割結果:")
    print(f"  訓練データ: {len(train_data)}件 ({len(train_data)/len(all_data)*100:.1f}%)")
    print(f"  評価データ: {len(eval_data)}件 ({len(eval_data)/len(all_data)*100:.1f}%)")
    
    # Layer別統計
    train_layers = {}
    eval_layers = {}
    for item in train_data:
        layer = item.get("layer", -1)
        train_layers[layer] = train_layers.get(layer, 0) + 1
    for item in eval_data:
        layer = item.get("layer", -1)
        eval_layers[layer] = eval_layers.get(layer, 0) + 1
    
    print(f"\nLayer別内訳（訓練/評価）:")
    for layer in sorted(set(list(train_layers.keys()) + list(eval_layers.keys()))):
        train_count = train_layers.get(layer, 0)
        eval_count = eval_layers.get(layer, 0)
        print(f"  Layer {layer}: {train_count}件 / {eval_count}件")
    
    # 正例/負例統計
    train_positive = sum(1 for item in train_data if item.get("positive", True))
    train_negative = len(train_data) - train_positive
    eval_positive = sum(1 for item in eval_data if item.get("positive", True))
    eval_negative = len(eval_data) - eval_positive
    
    print(f"\n正例/負例内訳（訓練/評価）:")
    print(f"  正例: {train_positive}件 / {eval_positive}件")
    print(f"  負例: {train_negative}件 / {eval_negative}件")
    
    # ファイル保存
    train_file = output_path / f"{input_path.stem}_train.jsonl"
    eval_file = output_path / f"{input_path.stem}_eval.jsonl"
    
    with open(train_file, 'w', encoding='utf-8') as f:
        for item in train_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    with open(eval_file, 'w', encoding='utf-8') as f:
        for item in eval_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    print(f"\n[OK] 分割完了:")
    print(f"  訓練データ: {train_file}")
    print(f"  評価データ: {eval_file}")
    
    return str(train_file), str(eval_file)


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description='CASTLE-EXデータセット分割ツール（ハッシュベース固定分割）')
    parser.add_argument('input', type=str, help='入力JSONLファイル')
    parser.add_argument('--train-ratio', type=float, default=0.9, help='訓練データの割合（デフォルト: 0.9）')
    parser.add_argument('--eval-ratio', type=float, default=0.1, help='評価データの割合（デフォルト: 0.1）')
    parser.add_argument('--output-dir', type=str, default='.', help='出力ディレクトリ（デフォルト: カレントディレクトリ）')
    parser.add_argument('--seed-hash', type=str, default='castle_ex_v1_0', help='分割の再現性を保つためのシードハッシュ（デフォルト: castle_ex_v1_0）')
    
    args = parser.parse_args()
    
    split_dataset(
        args.input,
        train_ratio=args.train_ratio,
        eval_ratio=args.eval_ratio,
        output_dir=args.output_dir,
        seed_hash=args.seed_hash
    )
    
    print("\n[OK] データセット分割が完了しました")


if __name__ == '__main__':
    main()
