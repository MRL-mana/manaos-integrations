#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CドライブからDドライブへの大容量ディレクトリ移動スクリプト
"""

import os
import shutil
from pathlib import Path
from typing import List, Tuple, Dict

# プロジェクトルート
project_root = Path(__file__).parent

# Dドライブのベースパス
D_DRIVE_BASE = Path("D:/manaos_integrations")

# 移動対象ディレクトリ（サイズ順）
MOVE_TARGETS = [
    {
        "source": project_root / "comfyui",
        "destination": D_DRIVE_BASE / "comfyui",
        "description": "ComfyUI（約19GB）"
    },
    {
        "source": project_root / "organized_images",
        "destination": D_DRIVE_BASE / "organized_images",
        "description": "整理済み画像（約606MB）"
    },
    {
        "source": project_root / "gallery_images",
        "destination": D_DRIVE_BASE / "gallery_images",
        "description": "ギャラリー画像（約406MB）"
    },
    {
        "source": project_root / "generated_images",
        "destination": D_DRIVE_BASE / "generated_images",
        "description": "生成画像（約1.6MB）"
    },
    {
        "source": project_root / "logs",
        "destination": D_DRIVE_BASE / "logs",
        "description": "ログファイル（約39MB）"
    },
    {
        "source": project_root / "outputs",
        "destination": D_DRIVE_BASE / "outputs",
        "description": "出力ファイル"
    },
    {
        "source": project_root / "data",
        "destination": D_DRIVE_BASE / "data",
        "description": "データファイル"
    },
    {
        "source": project_root / "snapshots",
        "destination": D_DRIVE_BASE / "snapshots",
        "description": "スナップショット"
    },
]

# シンボリックリンクを作成するか（True: シンボリックリンク、False: 移動のみ）
CREATE_SYMLINKS = True


def get_directory_size(path: Path) -> int:
    """ディレクトリのサイズを取得（バイト）"""
    total = 0
    try:
        for entry in path.rglob("*"):
            if entry.is_file():
                try:
                    total += entry.stat().st_size
                except (OSError, PermissionError):
                    pass
    except (OSError, PermissionError):
        pass
    return total


def format_size(size_bytes: int) -> str:
    """サイズを読みやすい形式に変換"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def move_directory(source: Path, destination: Path, create_symlink: bool = True) -> Tuple[bool, str, int]:
    """
    ディレクトリを移動し、必要に応じてシンボリックリンクを作成

    Returns:
        (success, message, size_freed)
    """
    if not source.exists():
        return False, f"ソースが存在しません: {source}", 0

    if not source.is_dir():
        return False, f"ソースはディレクトリではありません: {source}", 0

    # サイズを取得
    size = get_directory_size(source)

    try:
        # 移動先の親ディレクトリを作成
        destination.parent.mkdir(parents=True, exist_ok=True)

        # 既に移動先が存在する場合はスキップ
        if destination.exists():
            return False, f"移動先が既に存在します: {destination}", 0

        # ディレクトリを移動
        print(f"移動中: {source.name} -> {destination}")
        shutil.move(str(source), str(destination))

        # シンボリックリンクを作成
        if create_symlink:
            try:
                # Windowsでは管理者権限が必要な場合がある
                os.symlink(str(destination), str(source), target_is_directory=True)
                print(f"シンボリックリンク作成: {source} -> {destination}")
            except OSError as e:
                print(f"警告: シンボリックリンクの作成に失敗しました（管理者権限が必要な可能性があります）: {e}")
                print(f"手動でシンボリックリンクを作成してください: mklink /D {source} {destination}")

        return True, f"移動完了: {source.name}", size

    except Exception as e:
        return False, f"エラー: {e}", 0


def main():
    """メイン処理"""
    print("=" * 70)
    print("CドライブからDドライブへの大容量ディレクトリ移動")
    print("=" * 70)
    print()

    # Dドライブの確認
    if not Path("D:/").exists():
        print("[ERROR] Dドライブが見つかりません")
        return

    d_drive = Path("D:/")
    d_free = shutil.disk_usage(str(d_drive)).free
    print(f"Dドライブ空き容量: {format_size(d_free)}")
    print()

    # 移動対象を確認
    total_size = 0
    move_list = []

    for target in MOVE_TARGETS:
        source = target["source"]
        if source.exists():
            size = get_directory_size(source)
            if size > 0:
                total_size += size
                move_list.append({
                    **target,
                    "size": size
                })
                print(f"移動対象: {target['description']}")
                print(f"  パス: {source}")
                print(f"  サイズ: {format_size(size)}")
                print(f"  移動先: {target['destination']}")
                print()

    print(f"合計移動サイズ: {format_size(total_size)}")
    print()

    # 確認
    if not move_list:
        print("移動対象がありません")
        return

    # 自動実行（非対話モード）
    print("自動実行モード: 移動を開始します...")

    print()
    print("=" * 70)
    print("移動開始")
    print("=" * 70)
    print()

    # 移動実行
    success_count = 0
    total_freed = 0
    errors = []

    for target in move_list:
        source = target["source"]
        destination = target["destination"]
        description = target["description"]

        print(f"[{description}]")
        success, message, size_freed = move_directory(
            source,
            destination,
            CREATE_SYMLINKS
        )

        if success:
            print(f"[OK] {message}")
            print(f"   解放された容量: {format_size(size_freed)}")
            success_count += 1
            total_freed += size_freed
        else:
            print(f"[ERROR] {message}")
            errors.append(f"{description}: {message}")

        print()

    # 結果表示
    print("=" * 70)
    print("移動完了")
    print("=" * 70)
    print(f"成功: {success_count}/{len(move_list)}")
    print(f"解放された容量: {format_size(total_freed)}")

    if errors:
        print()
        print("エラー:")
        for error in errors:
            print(f"  - {error}")

    print()
    print("注意: シンボリックリンクの作成に失敗した場合は、")
    print("管理者権限でPowerShellを開き、以下のコマンドを実行してください:")
    print()
    for target in move_list:
        if target["source"].exists() and not target["destination"].exists():
            print(f'  mklink /D "{target["source"]}" "{target["destination"]}"')
    print()


if __name__ == "__main__":
    main()
