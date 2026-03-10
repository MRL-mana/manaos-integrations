#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CASTLE-EX 学習準備スクリプト
データセットの固定、分割、検証を一括実行
"""

import json
import argparse
from pathlib import Path
import sys
import subprocess

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]
    except (AttributeError, ValueError, TypeError):
        pass


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description='CASTLE-EX学習準備スクリプト')
    parser.add_argument('dataset_file', type=str, help='データセットJSONLファイル')
    parser.add_argument('--version', type=str, default='v1_0', help='バージョン名（デフォルト: v1_0）')
    parser.add_argument('--train-ratio', type=float, default=0.9, help='訓練データの割合（デフォルト: 0.9）')
    parser.add_argument('--eval-ratio', type=float, default=0.1, help='評価データの割合（デフォルト: 0.1）')
    
    args = parser.parse_args()
    
    dataset_path = Path(args.dataset_file)
    if not dataset_path.exists():
        print(f"エラー: データセットファイルが見つかりません: {args.dataset_file}")
        return 1
    
    print("=" * 60)
    print("CASTLE-EX 学習準備")
    print("=" * 60)
    
    # 1. データセットを固定版として保存
    fixed_file = f"castle_ex_dataset_{args.version}.jsonl"
    stats_file = f"castle_ex_dataset_{args.version}_stats.json"
    
    print(f"\n[1/4] データセットを固定版として保存...")
    print(f"  固定版: {fixed_file}")
    
    import shutil
    shutil.copy(dataset_path, fixed_file)
    
    # statsファイルもコピー（存在する場合）
    stats_source = dataset_path.parent / f"{dataset_path.stem}_stats.json"
    if stats_source.exists():
        shutil.copy(stats_source, stats_file)
        print(f"  統計ファイル: {stats_file}")
    
    # 2. データセット分割
    print(f"\n[2/4] データセットをtrain/evalに分割...")
    seed_hash = f"castle_ex_{args.version}"
    result = subprocess.run(
        [
            sys.executable,
            "castle_ex_dataset_splitter.py",
            fixed_file,
            "--train-ratio", str(args.train_ratio),
            "--eval-ratio", str(args.eval_ratio),
            "--seed-hash", seed_hash
        ],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace'
    )
    
    if result.returncode != 0:
        print(f"エラー: データセット分割に失敗しました")
        if result.stderr:
            try:
                print(result.stderr)
            except UnicodeEncodeError:
                print("エラー詳細（文字コード問題により表示できません）")
        return 1
    
    if result.stdout:
        try:
            print(result.stdout)
        except UnicodeEncodeError:
            print("分割完了（詳細は文字コード問題により表示できません）")
    
    # 3. データ検証
    print(f"\n[3/4] データセットを検証...")
    result = subprocess.run(
        [
            sys.executable,
            "castle_ex_data_validator.py",
            fixed_file
        ],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace'
    )
    
    if result.returncode != 0:
        print(f"警告: データ検証で問題が見つかりました")
        if result.stderr:
            try:
                print(result.stderr)
            except UnicodeEncodeError:
                print("検証エラー詳細（文字コード問題により表示できません）")
    else:
        if result.stdout:
            try:
                print(result.stdout)
            except UnicodeEncodeError:
                print("検証完了（詳細は文字コード問題により表示できません）")
    
    # 4. 統計情報表示
    print(f"\n[4/4] 統計情報を表示...")
    if Path(stats_file).exists():
        result = subprocess.run(
            [
                sys.executable,
                "castle_ex_stats_viewer.py",
                stats_file
            ],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        if result.stdout:
            try:
                print(result.stdout)
            except UnicodeEncodeError:
                print("統計情報表示完了（詳細は文字コード問題により表示できません）")
    
    print("\n" + "=" * 60)
    print("学習準備完了")
    print("=" * 60)
    print(f"\n固定版データセット: {fixed_file}")
    print(f"訓練データ: {Path(fixed_file).stem}_train.jsonl")
    print(f"評価データ: {Path(fixed_file).stem}_eval.jsonl")
    print(f"\n次のステップ:")
    print(f"  1. 学習スケジュールを生成")
    print(f"  2. 学習を実行")
    print(f"  3. 評価を実行")
    print(f"  4. 評価結果を分析してv1.1データを生成")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
