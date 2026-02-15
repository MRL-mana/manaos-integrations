"""
モデルバックアップ＆削除スクリプト
ローカルLLMと画像生成モデルをGoogle Driveにバックアップしてから削除
"""

import os
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional
import sys
import io
from datetime import datetime

# Windowsでのエンコーディング設定
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

try:
    from google_drive_integration import GoogleDriveIntegration
    GOOGLE_DRIVE_AVAILABLE = True
except ImportError:
    GOOGLE_DRIVE_AVAILABLE = False
    GoogleDriveIntegration = None


def get_ollama_models_path() -> Path:
    """Ollamaモデルの保存パスを取得"""
    ollama_models = os.getenv("OLLAMA_MODELS")
    if ollama_models:
        return Path(ollama_models)
    
    user_profile = os.getenv("USERPROFILE") or os.getenv("HOME")
    if user_profile:
        return Path(user_profile) / ".ollama" / "models"
    
    return Path.home() / ".ollama" / "models"


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


def backup_to_google_drive(
    local_path: Path,
    drive_folder: str,
    drive_integration: GoogleDriveIntegration
) -> bool:
    """
    ディレクトリをGoogle Driveにバックアップ
    
    Args:
        local_path: ローカルパス
        drive_folder: Google Drive上のフォルダ名
        drive_integration: Google Drive統合インスタンス
    
    Returns:
        成功したかどうか
    """
    if not local_path.exists():
        print(f"  ⚠️ パスが存在しません: {local_path}")
        return False
    
    print(f"  📤 Google Driveにバックアップ中: {drive_folder}...")
    
    try:
        # フォルダを作成（存在しない場合）
        folder_id = None
        try:
            files = drive_integration.list_files()
            for file in files:
                if file.get("name") == drive_folder and file.get("mimeType") == "application/vnd.google-apps.folder":
                    folder_id = file.get("id")
                    break
        except Exception as e:
            print(f"  ⚠️ フォルダ検索エラー: {e}")
        
        # ファイルをアップロード
        uploaded_count = 0
        failed_count = 0
        
        for root, dirs, files in os.walk(local_path):
            for file in files:
                file_path = Path(root) / file
                relative_path = file_path.relative_to(local_path)
                drive_path = f"{drive_folder}/{relative_path}"
                
                try:
                    result = drive_integration.upload_file(
                        str(file_path),
                        drive_path,
                        overwrite=True
                    )
                    if result:
                        uploaded_count += 1
                        if uploaded_count % 10 == 0:
                            print(f"    {uploaded_count}個のファイルをアップロードしました...")
                    else:
                        failed_count += 1
                except Exception as e:
                    print(f"    ⚠️ アップロードエラー ({file_path.name}): {e}")
                    failed_count += 1
        
        print(f"  ✓ バックアップ完了: {uploaded_count}個成功, {failed_count}個失敗")
        return uploaded_count > 0
        
    except Exception as e:
        print(f"  ❌ バックアップエラー: {e}")
        return False


def delete_directory(path: Path, dry_run: bool = False) -> bool:
    """
    ディレクトリを削除
    
    Args:
        path: 削除するパス
        dry_run: 実際には削除しない（確認のみ）
    
    Returns:
        成功したかどうか
    """
    if not path.exists():
        print(f"  ⚠️ パスが存在しません: {path}")
        return False
    
    if dry_run:
        print(f"  [DRY RUN] 削除予定: {path}")
        return True
    
    try:
        print(f"  🗑️ 削除中: {path}...")
        shutil.rmtree(path)
        print(f"  ✓ 削除完了")
        return True
    except Exception as e:
        print(f"  ❌ 削除エラー: {e}")
        return False


def main():
    """メイン処理"""
    import argparse
    
    parser = argparse.ArgumentParser(description="モデルバックアップ＆削除スクリプト")
    parser.add_argument("--dry-run", action="store_true", help="実際にはバックアップ・削除せず、結果を表示するだけ")
    parser.add_argument("--ollama-only", action="store_true", help="Ollamaモデルのみ処理")
    parser.add_argument("--comfyui-only", action="store_true", help="ComfyUIモデルのみ処理")
    parser.add_argument("--backup-only", action="store_true", help="バックアップのみ実行（削除しない）")
    args = parser.parse_args()
    
    print("=" * 70)
    print("モデルバックアップ＆削除スクリプト")
    print("=" * 70)
    print()
    
    if args.dry_run:
        print("⚠️ [DRY RUN モード] 実際にはバックアップ・削除しません\n")
    
    # Google Drive統合の確認
    if not GOOGLE_DRIVE_AVAILABLE:
        print("❌ Google Drive統合が利用できません")
        print("   google_drive_integration.py が必要です")
        return
    
    drive = GoogleDriveIntegration()
    if not drive.is_available():
        print("❌ Google Driveにアクセスできません")
        print("   認証情報を確認してください")
        return
    
    print("✓ Google Drive統合: 利用可能")
    print()
    
    # 処理対象を決定
    process_ollama = not args.comfyui_only
    process_comfyui = not args.ollama_only
    
    results = {
        "ollama": {"backed_up": False, "deleted": False},
        "comfyui": {"backed_up": False, "deleted": False}
    }
    
    # Ollamaモデルの処理
    if process_ollama:
        print("[1] Ollamaモデル")
        print("-" * 70)
        ollama_path = get_ollama_models_path()
        print(f"パス: {ollama_path}")
        
        if ollama_path.exists():
            size = get_directory_size(ollama_path)
            print(f"サイズ: {format_size(size)}")
            
            if size > 0:
                # バックアップ
                print("\nバックアップ:")
                if args.dry_run:
                    print("  [DRY RUN] バックアップ予定: ManaOS_Models/Ollama")
                else:
                    results["ollama"]["backed_up"] = backup_to_google_drive(
                        ollama_path,
                        "ManaOS_Models/Ollama",
                        drive
                    )
                
                # 削除
                if not args.backup_only and results["ollama"]["backed_up"]:
                    print("\n削除:")
                    results["ollama"]["deleted"] = delete_directory(ollama_path, args.dry_run)
            else:
                print("  ⚠️ モデルファイルが見つかりません（空のディレクトリ）")
        else:
            print("  ⚠️ パスが存在しません")
        
        print()
    
    # ComfyUIモデルの処理
    if process_comfyui:
        print("[2] ComfyUIモデル")
        print("-" * 70)
        comfyui_path = get_comfyui_models_path()
        print(f"パス: {comfyui_path}")
        
        if comfyui_path.exists():
            size = get_directory_size(comfyui_path)
            print(f"サイズ: {format_size(size)}")
            
            if size > 0:
                # バックアップ
                print("\nバックアップ:")
                if args.dry_run:
                    print("  [DRY RUN] バックアップ予定: ManaOS_Models/ComfyUI")
                else:
                    results["comfyui"]["backed_up"] = backup_to_google_drive(
                        comfyui_path,
                        "ManaOS_Models/ComfyUI",
                        drive
                    )
                
                # 削除
                if not args.backup_only and results["comfyui"]["backed_up"]:
                    print("\n削除:")
                    results["comfyui"]["deleted"] = delete_directory(comfyui_path, args.dry_run)
            else:
                print("  ⚠️ モデルファイルが見つかりません（空のディレクトリ）")
        else:
            print("  ⚠️ パスが存在しません")
        
        print()
    
    # 結果サマリー
    print("=" * 70)
    print("処理結果")
    print("=" * 70)
    
    if process_ollama:
        print(f"Ollamaモデル:")
        print(f"  バックアップ: {'✓ 完了' if results['ollama']['backed_up'] else '✗ 未実行' if not args.dry_run else '[DRY RUN]'}")
        print(f"  削除: {'✓ 完了' if results['ollama']['deleted'] else '✗ 未実行' if not args.dry_run else '[DRY RUN]'}")
    
    if process_comfyui:
        print(f"ComfyUIモデル:")
        print(f"  バックアップ: {'✓ 完了' if results['comfyui']['backed_up'] else '✗ 未実行' if not args.dry_run else '[DRY RUN]'}")
        print(f"  削除: {'✓ 完了' if results['comfyui']['deleted'] else '✗ 未実行' if not args.dry_run else '[DRY RUN]'}")
    
    print()
    
    if args.dry_run:
        print("💡 実際に実行するには、--dry-run オプションを外して実行してください")
    elif args.backup_only:
        print("💡 バックアップのみ実行しました（削除は行いませんでした）")
    else:
        print("✅ 処理が完了しました")


if __name__ == "__main__":
    main()
