#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CASTLE-EX 評価結果フォーマッター
評価結果を標準フォーマット（evaluation_v1_0.json）に変換
"""

import json
import argparse
from pathlib import Path
from typing import Dict, Any, List
import sys

if sys.platform == 'win32':
    try:
        import io
        if not isinstance(sys.stdout, io.TextIOWrapper):
            if hasattr(sys.stdout, 'buffer') and not sys.stdout.buffer.closed:
                sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    except (AttributeError, ValueError, TypeError):
        pass


def create_standard_evaluation_format(
    dataset_file: str,
    seed: str = "castle_ex_v1_0",
    output_file: str = "evaluation_v1_0.json"
) -> Dict[str, Any]:
    """
    標準評価フォーマットを作成（テンプレート）
    
    Args:
        dataset_file: 評価データセットファイル
        seed: シード
        output_file: 出力ファイル名
    
    Returns:
        標準評価フォーマット辞書
    """
    evaluation = {
        "dataset": dataset_file,
        "seed": seed,
        "overall": {
            "negative_detection": 0.00,
            "axis_consistency": 0.00,
            "context_sensitivity": 0.00,
            "emotion_appropriateness": 0.00,
            "paraphrase_robustness": 0.00,
            "causal_validity": 0.00
        },
        "by_layer": {
            "0": {"acc": 0.00},
            "1": {"acc": 0.00},
            "2": {"acc": 0.00},
            "3": {"acc": 0.00},
            "4": {"acc": 0.00},
            "5": {"acc": 0.00},
            "6": {"acc": 0.00}
        },
        "by_axes_combo": {
            "logic": {"acc": 0.00},
            "emotion": {"acc": 0.00},
            "context": {"acc": 0.00},
            "emotion,logic": {"acc": 0.00},
            "context,logic": {"acc": 0.00},
            "context,emotion,logic": {"acc": 0.00}
        },
        "negative_by_error_type": {
            "logic_error": {"precision": 0.00, "recall": 0.00},
            "missing_reason": {"precision": 0.00, "recall": 0.00},
            "emotion_mismatch": {"precision": 0.00, "recall": 0.00},
            "context_miss": {"precision": 0.00, "recall": 0.00},
            "overconfident": {"precision": 0.00, "recall": 0.00},
            "unsafe_action": {"precision": 0.00, "recall": 0.00}
        }
    }
    
    # ファイルに保存
    output_path = Path(output_file)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(evaluation, f, ensure_ascii=False, indent=2)
    
    print(f"[OK] 標準評価フォーマット（テンプレート）を作成しました: {output_file}")
    print(f"\nこのファイルを編集して、実際の評価結果を入力してください。")
    print(f"または、evaluatorの出力をこのフォーマットに変換してください。")
    
    return evaluation


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description='CASTLE-EX評価結果フォーマッター')
    parser.add_argument('--dataset', type=str, default='castle_ex_dataset_v1_0_eval.jsonl', help='評価データセットファイル')
    parser.add_argument('--seed', type=str, default='castle_ex_v1_0', help='シード（デフォルト: castle_ex_v1_0）')
    parser.add_argument('--output', type=str, default='evaluation_v1_0.json', help='出力ファイル名（デフォルト: evaluation_v1_0.json）')
    
    args = parser.parse_args()
    
    create_standard_evaluation_format(
        dataset_file=args.dataset,
        seed=args.seed,
        output_file=args.output
    )
    
    print("\n[OK] 評価フォーマット生成が完了しました")


if __name__ == '__main__':
    main()
