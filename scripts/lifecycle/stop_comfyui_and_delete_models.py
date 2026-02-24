"""
ComfyUI停止＆モデル削除スクリプト
ComfyUIプロセスを停止してからモデルを削除
"""

import os
import shutil
import subprocess
from pathlib import Path
import sys
import io
import time

# Windowsでのエンコーディング設定
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')


def get_comfyui_models_path() -> Path:
    """ComfyUIモデルの保存パスを取得"""
    comfyui_path = os.getenv("COMFYUI_PATH")
    if comfyui_path:
        return Path(comfyui_path) / "models"
    
    default_comfyui = os.getenv("COMFYUI_PATH", "C:/ComfyUI")
    possible_paths = [
        Path(default_comfyui) / "models",
        Path("D:/ComfyUI/models"),
        Path.home() / "ComfyUI" / "models",
    ]
    
    for path in possible_paths:
        if path.exists():
            return path
    
    return Path(default_comfyui) / "models"


def get_directory_size(path: Path) -> int:
    """ディレクトリのサイズを取得"""
    if not path.exists():
        return 0
    
    total_size = 0
    try:
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                filepath = Path(dirpath) / filename
                try:
                    total_size += filepath.stat().st_size
                except (OSError, PermissionError):
                    pass
    except (OSError, PermissionError):
        pass
    
    return total_size


def format_size(size_bytes: int) -> str:
    """バイト数を読みやすい形式に変換"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def stop_comfyui_processes():
    """プロセスを停止 (ProcessManager経由)"""
    from manaos_process_manager import get_process_manager
    pm = get_process_manager("ComfyUIClean")

    print("[1] ComfyUIプロセスを確認中...")

    # ポート経由で終了
    killed_port = pm.kill_processes_by_port(8188)
    # キーワード経由で終了
    killed_kw = pm.kill_processes_by_keywords(["comfyui", "ComfyUI"])
    total = killed_port + killed_kw

    if total:
        print(f"  🛑 {total}個のComfyUIプロセスを終了しました")
        time.sleep(2)
    else:
        print("  ✓ ComfyUIプロセスは見つかりませんでした")
    return True


def delete_comfyui_models(dry_run: bool = False, force: bool = False):
    """ComfyUIモデルを削除"""
    print("=" * 70)
    print("ComfyUI停止＆モデル削除スクリプト")
    print("=" * 70)
    print()
    
    if dry_run:
        print("⚠️ [DRY RUN モード] 実際には削除しません\n")
    
    # ComfyUIプロセスを停止
    if not dry_run:
        if not stop_comfyui_processes():
            print("\n❌ ComfyUIプロセスを停止できませんでした")
            print("   手動でComfyUIを終了してから再度実行してください")
            return
        print()
    
    comfyui_path = get_comfyui_models_path()
    print("[2] ComfyUIモデル")
    print("-" * 70)
    print(f"パス: {comfyui_path}")
    
    if not comfyui_path.exists():
        print("❌ パスが存在しません")
        return
    
    size = get_directory_size(comfyui_path)
    print(f"サイズ: {format_size(size)}")
    print()
    
    if size == 0:
        print("⚠️ モデルファイルが見つかりません（空のディレクトリ）")
        return
    
    # 確認
    print("⚠️ 警告: ComfyUIモデルを削除します")
    print("   バックアップは作成しません")
    print()
    
    if dry_run:
        print("[DRY RUN] 削除予定:")
        print(f"  {comfyui_path}")
        print()
        print("💡 実際に削除するには、--dry-run オプションを外して実行してください")
        return
    
    # 確認プロンプト（forceがFalseの場合のみ）
    if not force:
        try:
            response = input("削除を実行しますか？ (yes/no): ")
            if response.lower() not in ['yes', 'y']:
                print("❌ 削除をキャンセルしました")
                return
        except (EOFError, KeyboardInterrupt):
            print("❌ 入力が中断されました。--force オプションを使用してください。")
            return
    
    # 削除実行（リトライ付き）
    max_retries = 3
    retry_delay = 3
    
    for attempt in range(max_retries):
        try:
            print()
            if attempt > 0:
                print(f"🔄 再試行中... ({attempt + 1}/{max_retries})")
                time.sleep(retry_delay)
            else:
                print("🗑️ 削除中...")
            
            shutil.rmtree(comfyui_path)
            print(f"✅ 削除完了: {comfyui_path}")
            return
            
        except PermissionError as e:
            if attempt < max_retries - 1:
                print(f"  ⚠️ ファイルが使用中のため待機中... ({retry_delay}秒)")
                time.sleep(retry_delay)
            else:
                print(f"❌ 削除エラー: {e}")
                print("   ⚠️ ファイルが使用中のままです")
                print("   💡 以下を試してください:")
                print("      1. ComfyUIを完全に終了（タスクマネージャーで確認）")
                print("      2. エクスプローラーでファイルが開いていないか確認")
                print("      3. システムを再起動")
                print("      4. 再度実行")
        except Exception as e:
            print(f"❌ 削除エラー: {e}")
            return


def main():
    """メイン処理"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ComfyUI停止＆モデル削除スクリプト")
    parser.add_argument("--dry-run", action="store_true", help="実際には削除せず、結果を表示するだけ")
    parser.add_argument("--force", action="store_true", help="確認なしで削除を実行")
    args = parser.parse_args()
    
    delete_comfyui_models(dry_run=args.dry_run, force=args.force)


if __name__ == "__main__":
    main()
