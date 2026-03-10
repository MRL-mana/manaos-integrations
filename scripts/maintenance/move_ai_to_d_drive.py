#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI・画像生成・動画生成関連のディレクトリをDドライブに移動
"""

import os
import shutil
from pathlib import Path
from typing import List, Tuple, Dict

# Dドライブのベースパス
D_DRIVE_BASE = Path("D:/manaos_integrations")

# 移動対象（AI・画像生成・動画生成関連）
MOVE_TARGETS = [
    {
        "source": Path("C:/Users/mana4/ai_workspace_5080"),
        "destination": D_DRIVE_BASE / "ai_workspace_5080",
        "description": "AIワークスペース（5.08GB）"
    },
    {
        "source": Path("C:/Users/mana4/Desktop/manaos_integrations/comfyui"),
        "destination": D_DRIVE_BASE / "comfyui",
        "description": "ComfyUI（19GB）"
    },
    {
        "source": Path("C:/Users/mana4/Desktop/manaos_integrations/comfyui/models"),
        "destination": D_DRIVE_BASE / "comfyui" / "models",
        "description": "ComfyUIモデル",
        "parent_moved": True  # 親ディレクトリが移動済みの場合はスキップ
    },
    {
        "source": Path("C:/Users/mana4/Desktop/manaos_integrations/comfyui/output"),
        "destination": D_DRIVE_BASE / "comfyui" / "output",
        "description": "ComfyUI出力",
        "parent_moved": True
    },
    {
        "source": Path("C:/Users/mana4/Desktop/manaos_integrations/comfyui/input"),
        "destination": D_DRIVE_BASE / "comfyui" / "input",
        "description": "ComfyUI入力",
        "parent_moved": True
    },
    {
        "source": Path("C:/Users/mana4/Desktop/manaos_integrations/ltx2_templates"),
        "destination": D_DRIVE_BASE / "ltx2_templates",
        "description": "LTX2テンプレート"
    },
    {
        "source": Path("C:/Users/mana4/Desktop/manaos_integrations/ltx2_workflows"),
        "destination": D_DRIVE_BASE / "ltx2_workflows",
        "description": "LTX2ワークフロー"
    },
]

# シンボリックリンクを作成するか
CREATE_SYMLINKS = True


def get_directory_size(path: Path) -> int:
    """ディレクトリのサイズを取得"""
    total = 0
    try:
        for entry in path.rglob("*"):
            if entry.is_file():
                try:
                    total += entry.stat().st_size
                except Exception:
                    pass
    except Exception:
        pass
    return total


def format_size(size_bytes: int) -> str:
    """サイズを読みやすい形式に変換"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0  # type: ignore
    return f"{size_bytes:.2f} TB"


def move_directory(source: Path, destination: Path, create_symlink: bool = True, parent_moved: bool = False) -> Tuple[bool, str, int]:
    """
    ディレクトリを移動し、必要に応じてシンボリックリンクを作成

    Returns:
        (success, message, size_freed)
    """
    if not source.exists():
        return False, f"ソースが存在しません: {source}", 0

    if not source.is_dir():
        return False, f"ソースはディレクトリではありません: {source}", 0

    # 親ディレクトリが移動済みの場合はスキップ
    if parent_moved:
        # 親ディレクトリが既にシンボリックリンクかチェック
        parent = source.parent
        try:
            if parent.is_symlink() or str(destination.parent) in str(parent.resolve()):
                return False, f"親ディレクトリが既に移動済み: {source}", 0
        except Exception:
            pass

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
    print("AI・画像生成・動画生成関連ディレクトリをDドライブに移動")
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
        parent_moved = target.get("parent_moved", False)

        print(f"[{description}]")
        success, message, size_freed = move_directory(
            source,
            destination,
            CREATE_SYMLINKS,
            parent_moved
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
