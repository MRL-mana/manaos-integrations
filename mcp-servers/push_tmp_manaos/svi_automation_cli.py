"""
SVI自動化CLIツール
コマンドラインから自動化機能を操作
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent))

from svi_automation import SVIAutomation
from svi_wan22_video_integration import SVIWan22VideoIntegration


def cmd_watch(args):
    """フォルダ監視コマンド"""
    automation = SVIAutomation()
    
    print(f"📁 フォルダ監視を開始: {args.folder}")
    automation.watch_folder(
        folder_path=args.folder,
        auto_generate=args.auto_generate,
        default_prompt=args.prompt
    )
    
    print("監視中... (Ctrl+Cで停止)")
    try:
        automation.start_scheduler()
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n監視を停止します...")
        automation.stop_scheduler()


def cmd_schedule(args):
    """スケジュール追加コマンド"""
    automation = SVIAutomation()
    
    # 実行時刻を解析
    if args.time:
        # "HH:MM"形式
        hour, minute = map(int, args.time.split(':'))
        schedule_time = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
        if schedule_time < datetime.now():
            schedule_time += timedelta(days=1)
    elif args.datetime:
        # ISO形式
        schedule_time = datetime.fromisoformat(args.datetime)
    else:
        # デフォルト: 1時間後
        schedule_time = datetime.now() + timedelta(hours=1)
    
    automation.schedule_task(
        task_name=args.name or f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        schedule_time=schedule_time,
        image_path=args.image,
        prompt=args.prompt,
        video_length_seconds=args.length,
        repeat=args.repeat,
        repeat_interval=timedelta(hours=args.repeat_interval) if args.repeat_interval else None
    )
    
    print(f"✓ スケジュールタスクを追加: {schedule_time}")


def cmd_batch(args):
    """バッチ処理コマンド"""
    automation = SVIAutomation()
    
    print(f"📦 バッチ処理を開始: {args.folder}")
    execution_ids = automation.batch_process_folder(
        folder_path=args.folder,
        prompt=args.prompt,
        max_files=args.max_files
    )
    
    print(f"✓ バッチ処理完了: {len(execution_ids)}件")


def cmd_start_scheduler(args):
    """スケジューラー開始コマンド"""
    automation = SVIAutomation()
    automation.start_scheduler()
    
    print("✓ スケジューラーを開始しました")
    print("実行中... (Ctrl+Cで停止)")
    
    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nスケジューラーを停止します...")
        automation.stop_scheduler()


def main():
    parser = argparse.ArgumentParser(description="SVI自動化CLIツール")
    subparsers = parser.add_subparsers(dest='command', help='コマンド')
    
    # watchコマンド
    watch_parser = subparsers.add_parser('watch', help='フォルダを監視')
    watch_parser.add_argument('folder', help='監視するフォルダのパス')
    watch_parser.add_argument('--auto-generate', action='store_true', help='自動生成を有効化')
    watch_parser.add_argument('--prompt', help='デフォルトプロンプト')
    watch_parser.set_defaults(func=cmd_watch)
    
    # scheduleコマンド
    schedule_parser = subparsers.add_parser('schedule', help='スケジュールタスクを追加')
    schedule_parser.add_argument('--name', help='タスク名')
    schedule_parser.add_argument('--image', required=True, help='画像パス')
    schedule_parser.add_argument('--prompt', required=True, help='プロンプト')
    schedule_parser.add_argument('--time', help='実行時刻 (HH:MM)')
    schedule_parser.add_argument('--datetime', help='実行日時 (ISO形式)')
    schedule_parser.add_argument('--length', type=int, default=5, help='動画の長さ（秒）')
    schedule_parser.add_argument('--repeat', action='store_true', help='繰り返し実行')
    schedule_parser.add_argument('--repeat-interval', type=int, help='繰り返し間隔（時間）')
    schedule_parser.set_defaults(func=cmd_schedule)
    
    # batchコマンド
    batch_parser = subparsers.add_parser('batch', help='フォルダ内の画像を一括処理')
    batch_parser.add_argument('folder', help='処理するフォルダのパス')
    batch_parser.add_argument('--prompt', help='プロンプト')
    batch_parser.add_argument('--max-files', type=int, help='最大処理ファイル数')
    batch_parser.set_defaults(func=cmd_batch)
    
    # schedulerコマンド
    scheduler_parser = subparsers.add_parser('scheduler', help='スケジューラーを開始')
    scheduler_parser.set_defaults(func=cmd_start_scheduler)
    
    args = parser.parse_args()
    
    if args.command:
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()











