#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI・画像生成・動画生成関連のディレクトリを検索
"""

import os
from pathlib import Path
from typing import List, Dict

# 検索対象ディレクトリ
SEARCH_DIRS = [
    Path.home(),
    Path("C:/Users/mana4/Desktop"),
    Path("C:/Users/mana4/Documents"),
    Path("C:/Users/mana4/Downloads"),
]

# 検索パターン（ディレクトリ名）
SEARCH_PATTERNS = [
    "*model*",
    "*ai*",
    "*checkpoint*",
    "*training*",
    "*huggingface*",
    "*stable*diffusion*",
    "*comfyui*",
    "*ltx*",
    "*video*",
    "*image*",
    "*generated*",
    "*gallery*",
    ".cache",
    ".hf_cache",
]

# 除外パス
EXCLUDE_PATHS = [
    ".git",
    "node_modules",
    "__pycache__",
    "venv",
    ".venv",
]


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


def should_exclude(path: Path) -> bool:
    """パスを除外すべきかチェック"""
    path_str = str(path).lower()
    for exclude in EXCLUDE_PATHS:
        if exclude in path_str:
            return True
    return False


def find_ai_directories() -> List[Dict]:
    """AI関連ディレクトリを検索"""
    results = []

    for search_dir in SEARCH_DIRS:
        if not search_dir.exists():
            continue

        print(f"検索中: {search_dir}")

        # 直接検索
        for pattern in SEARCH_PATTERNS:
            try:
                for path in search_dir.glob(pattern):
                    if should_exclude(path):
                        continue

                    if path.is_dir():
                        size = get_directory_size(path)
                        if size > 100 * 1024 * 1024:  # 100MB以上
                            results.append({
                                "path": str(path),
                                "size_gb": size / (1024 ** 3),
                                "type": "directory"
                            })
            except Exception as e:
                pass

    # サイズでソート
    results.sort(key=lambda x: x["size_gb"], reverse=True)
    return results


def main():
    """メイン処理"""
    print("=" * 70)
    print("AI・画像生成・動画生成関連ディレクトリ検索")
    print("=" * 70)
    print()

    results = find_ai_directories()

    if not results:
        print("大きなAI関連ディレクトリが見つかりませんでした")
        return

    print(f"見つかったディレクトリ: {len(results)}個")
    print()
    print("=" * 70)
    print("検索結果（100MB以上）")
    print("=" * 70)
    print()

    for i, result in enumerate(results[:20], 1):  # 上位20個
        print(f"{i}. {result['path']}")
        print(f"   サイズ: {result['size_gb']:.2f} GB")
        print()

    # Dドライブへの移動推奨リスト
    print("=" * 70)
    print("Dドライブへの移動推奨")
    print("=" * 70)
    print()

    ai_related_keywords = ["model", "ai", "checkpoint", "training", "huggingface",
                          "stable", "diffusion", "comfyui", "ltx", "video",
                          "image", "generated", "gallery", "cache"]

    recommended = []
    for result in results:
        path_lower = result["path"].lower()
        if any(keyword in path_lower for keyword in ai_related_keywords):
            recommended.append(result)

    if recommended:
        print("以下のディレクトリをDドライブに移動することを推奨します:")
        print()
        for i, result in enumerate(recommended[:10], 1):
            print(f"{i}. {result['path']}")
            print(f"   サイズ: {result['size_gb']:.2f} GB")
            print()
    else:
        print("移動推奨ディレクトリは見つかりませんでした")


if __name__ == "__main__":
    main()
