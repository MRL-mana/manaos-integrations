#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一時ファイル、キャッシュ、ログファイルのクリーンアップスクリプト
"""

import os
import shutil
from pathlib import Path
from typing import List, Tuple
from datetime import datetime, timedelta

# プロジェクトルート
project_root = Path(__file__).parent

# クリーンアップ対象
CLEANUP_TARGETS = [
    # __pycache__ディレクトリ
    {
        "pattern": "**/__pycache__",
        "type": "directory",
        "description": "Pythonキャッシュ"
    },
    # .pycファイル
    {
        "pattern": "**/*.pyc",
        "type": "file",
        "description": "Pythonコンパイル済みファイル"
    },
    # .pyoファイル
    {
        "pattern": "**/*.pyo",
        "type": "file",
        "description": "Python最適化ファイル"
    },
    # .cacheディレクトリ（プロジェクト内）
    {
        "pattern": ".cache",
        "type": "directory",
        "description": "キャッシュディレクトリ"
    },
    # 古いログファイル（30日以上）
    {
        "pattern": "**/*.log",
        "type": "file",
        "description": "古いログファイル（30日以上）",
        "max_age_days": 30
    },
    # 一時ファイル
    {
        "pattern": "**/*.tmp",
        "type": "file",
        "description": "一時ファイル"
    },
    {
        "pattern": "**/*.temp",
        "type": "file",
        "description": "一時ファイル"
    },
]

# 除外パス
EXCLUDE_PATHS = [
    ".git",
    "venv",
    ".venv",
    "env",
    "node_modules",
    "D:/",
]


def should_exclude(path: Path) -> bool:
    """パスを除外すべきかチェック"""
    path_str = str(path).replace("\\", "/")  # Windows バックスラッシュを正規化
    for exclude in EXCLUDE_PATHS:
        if exclude in path_str:
            return True
    return False


def get_file_age_days(file_path: Path) -> float:
    """ファイルの経過日数を取得"""
    try:
        mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
        age = datetime.now() - mtime
        return age.total_seconds() / 86400  # 日数に変換
    except Exception:
        return 0


def cleanup_files() -> Tuple[int, int, int]:
    """
    クリーンアップを実行

    Returns:
        (deleted_files, deleted_dirs, total_size_freed)
    """
    deleted_files = 0
    deleted_dirs = 0
    total_size_freed = 0

    for target in CLEANUP_TARGETS:
        pattern = target["pattern"]
        target_type = target["type"]
        description = target["description"]
        max_age_days = target.get("max_age_days")

        print(f"\n[{description}]")
        print(f"  パターン: {pattern}")

        if target_type == "file":
            files = list(project_root.glob(pattern))
            for file_path in files:
                if should_exclude(file_path):
                    continue

                if not file_path.exists():
                    continue

                # 年齢チェック
                if max_age_days:
                    age = get_file_age_days(file_path)
                    if age < max_age_days:
                        continue

                try:
                    size = file_path.stat().st_size
                    file_path.unlink()
                    deleted_files += 1
                    total_size_freed += size
                    print(f"  削除: {file_path.relative_to(project_root)} ({size/1024:.2f} KB)")
                except Exception as e:
                    print(f"  エラー: {file_path.relative_to(project_root)} - {e}")

        elif target_type == "directory":
            dirs = list(project_root.glob(pattern))
            for dir_path in dirs:
                if should_exclude(dir_path):
                    continue

                if not dir_path.exists() or not dir_path.is_dir():
                    continue

                try:
                    # ディレクトリのサイズを計算
                    size = sum(f.stat().st_size for f in dir_path.rglob('*') if f.is_file())

                    shutil.rmtree(str(dir_path))
                    deleted_dirs += 1
                    total_size_freed += size
                    print(f"  削除: {dir_path.relative_to(project_root)} ({size/1024/1024:.2f} MB)")
                except Exception as e:
                    print(f"  エラー: {dir_path.relative_to(project_root)} - {e}")

    return deleted_files, deleted_dirs, total_size_freed


def main():
    """メイン処理"""
    print("=" * 70)
    print("一時ファイル、キャッシュ、ログファイルのクリーンアップ")
    print("=" * 70)
    print()

    deleted_files, deleted_dirs, total_size_freed = cleanup_files()

    print()
    print("=" * 70)
    print("クリーンアップ完了")
    print("=" * 70)
    print(f"削除したファイル: {deleted_files}個")
    print(f"削除したディレクトリ: {deleted_dirs}個")
    print(f"解放された容量: {total_size_freed/1024/1024:.2f} MB")
    print()


if __name__ == "__main__":
    main()
