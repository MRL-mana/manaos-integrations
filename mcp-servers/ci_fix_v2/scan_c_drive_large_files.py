#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cドライブの大きなファイルとディレクトリをスキャン
"""

import os
from pathlib import Path
from collections import defaultdict
import json

# スキャン対象のディレクトリ（ユーザーディレクトリと一般的な場所）
SCAN_DIRS = [
    Path("C:/Users/mana4"),
    Path("C:/ProgramData"),
    Path("C:/Windows/Temp"),
    Path("C:/Temp"),
]

# 除外パス
EXCLUDE_PATTERNS = [
    "AppData/Local/Microsoft/Windows/INetCache",
    "AppData/Local/Microsoft/Windows/WebCache",
    "AppData/Local/Temp",
    "AppData/Roaming",
    ".git",
    "node_modules",
    "__pycache__",
    ".cache",
]

# AI/モデル関連のキーワード
AI_KEYWORDS = [
    "model", "models", "checkpoint", "checkpoints", "huggingface", "hugging_face",
    "stable", "diffusion", "comfyui", "comfy", "ltx", "ltx2",
    "ai_workspace", "ai_", "training", "weights", "pytorch_model",
    "safetensors", "onnx", "tensorflow", "keras", "generated", "gallery",
    "output", "cache", "civitai", "civitai_cache",
]

def should_exclude(path_str):
    """除外すべきパスかチェック"""
    path_lower = path_str.lower().replace("\\", "/")
    for pattern in EXCLUDE_PATTERNS:
        if pattern.lower() in path_lower:
            return True
    return False

def is_ai_related(path_str):
    """AI関連のパスかチェック"""
    path_lower = path_str.lower().replace("\\", "/")
    return any(keyword in path_lower for keyword in AI_KEYWORDS)

def get_directory_size(path):
    """ディレクトリのサイズを取得"""
    total = 0
    try:
        for entry in path.rglob('*'):
            if entry.is_file():
                try:
                    total += entry.stat().st_size
                except (OSError, PermissionError):
                    pass
    except (OSError, PermissionError):
        pass
    return total

def format_size(size_bytes):
    """サイズを読みやすい形式に変換"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"

def scan_large_directories(root_dir, min_size_gb=0.1):
    """大きなディレクトリをスキャン"""
    results = []
    min_size = int(min_size_gb * 1024 * 1024 * 1024)
    
    print(f"スキャン中: {root_dir}")
    
    if not root_dir.exists():
        return results
    
    try:
        # 直接のサブディレクトリをチェック
        for item in root_dir.iterdir():
            if should_exclude(str(item)):
                continue
            
            if item.is_dir():
                try:
                    size = get_directory_size(item)
                    if size >= min_size:
                        results.append({
                            "path": str(item),
                            "size": size,
                            "size_gb": size / (1024**3),
                            "is_ai_related": is_ai_related(str(item)),
                            "type": "directory"
                        })
                except (OSError, PermissionError) as e:
                    pass
    except (OSError, PermissionError) as e:
        pass
    
    return results

def scan_large_files(root_dir, min_size_mb=100):
    """大きなファイルをスキャン"""
    results = []
    min_size = int(min_size_mb * 1024 * 1024)
    
    print(f"大きなファイルをスキャン中: {root_dir}")
    
    if not root_dir.exists():
        return results
    
    try:
        for item in root_dir.rglob('*'):
            if should_exclude(str(item)):
                continue
            
            if item.is_file():
                try:
                    size = item.stat().st_size
                    if size >= min_size:
                        results.append({
                            "path": str(item),
                            "size": size,
                            "size_gb": size / (1024**3),
                            "is_ai_related": is_ai_related(str(item)),
                            "type": "file"
                        })
                except (OSError, PermissionError):
                    pass
    except (OSError, PermissionError):
        pass
    
    return results

def main():
    print("=" * 70)
    print("Cドライブ 大きなファイル/ディレクトリ スキャン")
    print("=" * 70)
    print()
    
    all_results = []
    
    # ディレクトリをスキャン
    print("大きなディレクトリをスキャン中...")
    for scan_dir in SCAN_DIRS:
        dirs = scan_large_directories(scan_dir, min_size_gb=0.1)
        all_results.extend(dirs)
    
    # 大きなファイルをスキャン（ユーザーディレクトリのみ、時間がかかるので）
    print()
    print("大きなファイルをスキャン中（ユーザーディレクトリのみ）...")
    user_dir = Path("C:/Users/mana4")
    if user_dir.exists():
        files = scan_large_files(user_dir, min_size_mb=100)
        all_results.extend(files)
    
    # サイズでソート
    all_results.sort(key=lambda x: x["size"], reverse=True)
    
    # 結果を表示
    print()
    print("=" * 70)
    print("結果")
    print("=" * 70)
    print()
    
    ai_related = [r for r in all_results if r["is_ai_related"]]
    other_large = [r for r in all_results if not r["is_ai_related"]]
    
    print(f"AI関連: {len(ai_related)}個")
    print(f"その他: {len(other_large)}個")
    print()
    
    # AI関連を表示
    if ai_related:
        print("=" * 70)
        print("AI/モデル関連（Dドライブに移動推奨）")
        print("=" * 70)
        print()
        total_ai_size = 0
        for i, result in enumerate(ai_related[:30], 1):
            print(f"{i}. {result['path']}")
            print(f"   サイズ: {result['size_gb']:.2f} GB ({result['type']})")
            print()
            total_ai_size += result['size']
        print(f"合計: {format_size(total_ai_size)}")
        print()
    
    # その他の大きなファイル/ディレクトリ
    if other_large:
        print("=" * 70)
        print("その他の大きなファイル/ディレクトリ（上位20個）")
        print("=" * 70)
        print()
        for i, result in enumerate(other_large[:20], 1):
            print(f"{i}. {result['path']}")
            print(f"   サイズ: {result['size_gb']:.2f} GB ({result['type']})")
            print()
    
    # JSONに保存
    output_file = Path(__file__).parent / "c_drive_scan_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "ai_related": ai_related,
            "other_large": other_large,
            "total_count": len(all_results)
        }, f, indent=2, ensure_ascii=False)
    
    print(f"結果を保存しました: {output_file}")
    print()
    
    # 移動推奨の合計サイズ
    if ai_related:
        total_move_size = sum(r["size"] for r in ai_related)
        print("=" * 70)
        print("移動推奨サイズ")
        print("=" * 70)
        print(f"AI関連ファイル: {format_size(total_move_size)}")
        print()

if __name__ == "__main__":
    main()
