#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CASTLE-EXフレームワーク: 統合実行スクリプト

全機能を統合したワンストップ実行ツール
"""

import sys
import argparse
from pathlib import Path

# モジュール読み込み前にエンコーディング設定（一度だけ）
if sys.platform == 'win32':
    try:
        import io
        # 既にTextIOWrapperでラップされている場合はスキップ
        if not isinstance(sys.stdout, io.TextIOWrapper):
            if hasattr(sys.stdout, 'buffer') and not sys.stdout.buffer.closed:
                sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    except (AttributeError, ValueError, TypeError):
        pass

from castle_ex_data_generator import CastleEXDataGenerator
from castle_ex_data_validator import CastleEXDataValidator
from castle_ex_training_pipeline import CastleEXTrainingPipeline
from castle_ex_evaluator import CastleEXEvaluator
from castle_ex_stats_viewer import CastleEXStatsViewer


def generate_data(args):
    """データ生成コマンド"""
    try:
        print("\n" + "="*60)
        print("CASTLE-EX データ生成")
        print("="*60)
    except (ValueError, OSError):
        # stdoutが閉じられている場合はスキップ
        pass
    
    generator = CastleEXDataGenerator(random_seed=args.seed)
    stats = generator.generate_dataset(args.count, args.output)
    
    try:
        print("\n✓ データ生成が完了しました")
    except (ValueError, OSError):
        pass


def validate_data(args):
    """データ検証コマンド"""
    validator = CastleEXDataValidator()
    result = validator.validate_file(args.file)
    
    if result["valid"]:
        print("\n✓ すべてのデータが有効です")
        sys.exit(0)
    else:
        print("\n✗ 検証エラーが検出されました")
        sys.exit(1)


def create_training_schedule(args):
    """学習スケジュール生成コマンド"""
    pipeline = CastleEXTrainingPipeline(args.dataset, args.output_dir)
    pipeline.load_dataset()
    schedule = pipeline.generate_training_schedule(
        args.start_epoch, args.end_epoch, args.batch_size
    )
    pipeline.print_schedule_summary(schedule)
    
    print("\n✓ 学習スケジュール生成が完了しました")


def evaluate_model(args):
    """モデル評価コマンド"""
    evaluator = CastleEXEvaluator()
    results = evaluator.evaluate_all_layers()
    evaluator.print_report(args.output)
    
    try:
        print("\n[OK] 評価が完了しました")
    except (ValueError, OSError):
        pass


def view_stats(args):
    """データ分布レポート分析コマンド"""
    try:
        viewer = CastleEXStatsViewer(args.stats_file)
        viewer.print_report()
    except Exception as e:
        print(f"エラー: {e}")
        sys.exit(1)


def run_full_pipeline(args):
    """完全パイプライン実行（生成→検証→学習スケジュール生成）"""
    print("\n" + "="*60)
    print("CASTLE-EX 完全パイプライン実行")
    print("="*60)
    
    # 1. データ生成
    print("\n【ステップ1】データ生成")
    generator = CastleEXDataGenerator(random_seed=args.seed)
    dataset_file = args.output_dir / "castle_ex_dataset.jsonl"
    dataset_file.parent.mkdir(parents=True, exist_ok=True)
    generator.generate_dataset(args.count, str(dataset_file))
    
    # 2. データ検証
    print("\n【ステップ2】データ検証")
    validator = CastleEXDataValidator()
    result = validator.validate_file(str(dataset_file))
    
    if not result["valid"]:
        print("\n✗ データ検証エラーが検出されました")
        print("  データ生成は完了していますが、品質に問題があります")
        sys.exit(1)
    
    # 3. 学習スケジュール生成
    print("\n【ステップ3】学習スケジュール生成")
    training_dir = args.output_dir / "training"
    pipeline = CastleEXTrainingPipeline(str(dataset_file), str(training_dir))
    pipeline.load_dataset()
    schedule = pipeline.generate_training_schedule(
        args.start_epoch, args.end_epoch, args.batch_size
    )
    pipeline.print_schedule_summary(schedule)
    
    print("\n" + "="*60)
    print("✓ 完全パイプライン実行が完了しました")
    print("="*60)
    print(f"生成されたファイル:")
    print(f"  - データセット: {dataset_file}")
    print(f"  - 学習スケジュール: {training_dir / 'training_schedule.json'}")
    print(f"  - エポック別データ: {training_dir / 'epoch_*.jsonl'}")


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(
        description='CASTLE-EXフレームワーク統合実行ツール',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # データ生成のみ
  python castle_ex_integrated.py generate --count 1000 --output dataset.jsonl

  # データ検証のみ
  python castle_ex_integrated.py validate --file dataset.jsonl

  # 学習スケジュール生成のみ
  python castle_ex_integrated.py schedule --dataset dataset.jsonl --start-epoch 1 --end-epoch 25

  # 完全パイプライン実行（推奨）
  python castle_ex_integrated.py pipeline --count 1000

  # データ分布レポート分析
  python castle_ex_integrated.py view-stats dataset_stats.json
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='実行するコマンド')
    
    # generate コマンド
    parser_generate = subparsers.add_parser('generate', help='データ生成')
    parser_generate.add_argument('--count', type=int, default=1000, help='総データ数')
    parser_generate.add_argument('--output', type=str, default='castle_ex_dataset.jsonl', help='出力ファイル')
    parser_generate.add_argument('--seed', type=int, default=42, help='ランダムシード')
    
    # validate コマンド
    parser_validate = subparsers.add_parser('validate', help='データ検証')
    parser_validate.add_argument('file', type=str, help='検証するJSONLファイル')
    
    # schedule コマンド
    parser_schedule = subparsers.add_parser('schedule', help='学習スケジュール生成')
    parser_schedule.add_argument('dataset', type=str, help='入力データセットJSONLファイル')
    parser_schedule.add_argument('--output-dir', type=str, default='./castle_ex_training', help='出力ディレクトリ')
    parser_schedule.add_argument('--start-epoch', type=int, default=1, help='開始エポック')
    parser_schedule.add_argument('--end-epoch', type=int, default=25, help='終了エポック')
    parser_schedule.add_argument('--batch-size', type=int, default=100, help='バッチサイズ')
    
    # evaluate コマンド
    parser_evaluate = subparsers.add_parser('evaluate', help='モデル評価')
    parser_evaluate.add_argument('--output', type=str, default='castle_ex_evaluation.json', help='評価結果出力ファイル')
    
    # view-stats コマンド
    parser_view_stats = subparsers.add_parser('view-stats', help='データ分布レポート分析')
    parser_view_stats.add_argument('stats_file', type=str, help='stats.jsonファイルパス')
    
    # pipeline コマンド
    parser_pipeline = subparsers.add_parser('pipeline', help='完全パイプライン実行（推奨）')
    parser_pipeline.add_argument('--count', type=int, default=1000, help='総データ数')
    parser_pipeline.add_argument('--output-dir', type=Path, default=Path('./castle_ex_output'), help='出力ディレクトリ')
    parser_pipeline.add_argument('--start-epoch', type=int, default=1, help='開始エポック')
    parser_pipeline.add_argument('--end-epoch', type=int, default=25, help='終了エポック')
    parser_pipeline.add_argument('--batch-size', type=int, default=100, help='バッチサイズ')
    parser_pipeline.add_argument('--seed', type=int, default=42, help='ランダムシード')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # コマンド実行
    if args.command == 'generate':
        generate_data(args)
    elif args.command == 'validate':
        validate_data(args)
    elif args.command == 'schedule':
        create_training_schedule(args)
    elif args.command == 'evaluate':
        evaluate_model(args)
    elif args.command == 'view-stats':
        view_stats(args)
    elif args.command == 'pipeline':
        run_full_pipeline(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
