#!/usr/bin/env python3
"""
自動処理サービス（常駐型）
バックグラウンドで自動処理を実行
"""

import sys
import signal

sys.path.insert(0, '/root/runpod_integration')
sys.path.insert(0, '/root')

from auto_processor import AutoProcessor

# グローバル変数
processor = None

def signal_handler(sig, frame):
    """シグナルハンドラー（終了処理）"""
    global processor
    if processor:
        processor.stop()
    print("\n🛑 自動処理サービスを終了します")
    sys.exit(0)

def main():
    """メイン処理"""
    global processor

    # シグナルハンドラーを設定
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("🤖 自動処理サービス起動中...")
    print("=" * 60)

    processor = AutoProcessor()

    # 設定を表示
    print("📊 現在の設定:")
    config = processor.config
    print(f"   自動画像生成: {'✅ 有効' if config.get('auto_generate', {}).get('enabled') else '❌ 無効'}")
    print(f"   自動超解像: {'✅ 有効' if config.get('auto_upscale', {}).get('enabled') else '❌ 無効'}")
    print(f"   自動GIF生成: {'✅ 有効' if config.get('auto_gif', {}).get('enabled') else '❌ 無効'}")
    print(f"   自動LoRA学習: {'✅ 有効' if config.get('auto_training', {}).get('enabled') else '❌ 無効'}")
    print()

    # 統計情報を表示
    stats = processor.get_stats()
    print("📈 統計情報:")
    print(f"   生成画像: {stats.get('total_generated', 0)}枚")
    print(f"   超解像: {stats.get('total_upscaled', 0)}枚")
    print(f"   GIF生成: {stats.get('total_gifs', 0)}個")
    print(f"   LoRA学習: {stats.get('total_trainings', 0)}回")
    print()

    # 自動処理を開始
    processor.start()

    print("✅ 自動処理サービスを開始しました")
    print("   停止するには Ctrl+C を押してください")
    print("   ログファイル: /root/logs/auto_processor.log")
    print()

    # メインループ（シンプルに待機）
    try:
        while True:
            import time
            time.sleep(60)  # 1分ごとにチェック
    except KeyboardInterrupt:
        signal_handler(None, None)

if __name__ == "__main__":
    main()




