"""
Cドライブ全体で大きなファイルとディレクトリを検索
"""
import os
from pathlib import Path
from collections import defaultdict

# 検索対象外のパス
EXCLUDE_PATHS = {
    r"C:\Windows",
    r"C:\Program Files",
    r"C:\Program Files (x86)",
    r"C:\ProgramData",
    r"C:\System Volume Information",
    r"C:\$Recycle.Bin",
    r"C:\Recovery",
    r"C:\hiberfil.sys",
    r"C:\pagefile.sys",
    r"C:\swapfile.sys",
}

# 検索対象のパス（ユーザーディレクトリ中心）
SEARCH_PATHS = [
    Path(r"C:\Users"),
    Path(r"C:\Temp"),
    Path(r"C:\tmp"),
]

# AI/モデル関連のキーワード
AI_KEYWORDS = [
    "model", "models", "checkpoint", "checkpoints", "weights",
    "huggingface", "transformers", "stable", "diffusion",
    "comfyui", "automatic1111", "sd-webui", "ltx", "ltx2",
    "training", "dataset", "cache", "cached",
    "ai_workspace", "ai_", "generated", "output",
    ".safetensors", ".ckpt", ".pt", ".pth", ".bin",
    "pytorch", "tensorflow", "onnx",
]

def format_size(size_bytes):
    """サイズを読みやすい形式に変換"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"

def get_directory_size(path):
    """ディレクトリのサイズを計算"""
    total = 0
    try:
        for entry in os.scandir(path):
            try:
                if entry.is_file(follow_symlinks=False):
                    total += entry.stat(follow_symlinks=False).st_size
                elif entry.is_dir(follow_symlinks=False):
                    total += get_directory_size(entry.path)
            except (PermissionError, OSError):
                pass
    except (PermissionError, OSError):
        pass
    return total

def should_exclude(path_str):
    """除外すべきパスかチェック"""
    path_str_lower = path_str.lower()
    for exclude in EXCLUDE_PATHS:
        if exclude.lower() in path_str_lower:
            return True
    return False

def is_ai_related(path_str):
    """AI関連かチェック"""
    path_str_lower = path_str.lower()
    return any(keyword.lower() in path_str_lower for keyword in AI_KEYWORDS)

def find_large_directories(search_paths, min_size_gb=0.5):
    """大きなディレクトリを検索"""
    results = []
    min_size_bytes = min_size_gb * 1024 * 1024 * 1024

    for search_path in search_paths:
        if not search_path.exists():
            continue

        print(f"検索中: {search_path}")

        try:
            for root, dirs, files in os.walk(search_path):
                # 除外パスをスキップ
                if should_exclude(root):
                    dirs.clear()
                    continue

                try:
                    # ディレクトリのサイズを計算
                    size = get_directory_size(root)

                    if size >= min_size_bytes:
                        results.append({
                            "path": root,
                            "size": size,
                            "size_gb": size / (1024**3),
                            "is_ai_related": is_ai_related(root),
                        })
                except (PermissionError, OSError):
                    pass
        except (PermissionError, OSError) as e:
            print(f"  エラー: {search_path} - {e}")

    return results

def find_large_files(search_paths, min_size_mb=100):
    """大きなファイルを検索"""
    results = []
    min_size_bytes = min_size_mb * 1024 * 1024

    for search_path in search_paths:
        if not search_path.exists():
            continue

        print(f"ファイル検索中: {search_path}")

        try:
            for root, dirs, files in os.walk(search_path):
                # 除外パスをスキップ
                if should_exclude(root):
                    dirs.clear()
                    continue

                for file in files:
                    try:
                        file_path = os.path.join(root, file)
                        stat = os.stat(file_path)
                        size = stat.st_size

                        if size >= min_size_bytes:
                            results.append({
                                "path": file_path,
                                "size": size,
                                "size_gb": size / (1024**3),
                                "is_ai_related": is_ai_related(file_path),
                            })
                    except (PermissionError, OSError):
                        pass
        except (PermissionError, OSError) as e:
            print(f"  エラー: {search_path} - {e}")

    return results

def main():
    print("=" * 70)
    print("Cドライブ 大きなファイル・ディレクトリ検索")
    print("=" * 70)
    print()

    # 大きなディレクトリを検索
    print("大きなディレクトリを検索中...")
    print()
    dirs = find_large_directories(SEARCH_PATHS, min_size_gb=0.5)
    dirs.sort(key=lambda x: x["size"], reverse=True)

    print(f"見つかった大きなディレクトリ: {len(dirs)}個")
    print()

    # AI関連を優先表示
    ai_dirs = [d for d in dirs if d["is_ai_related"]]
    other_dirs = [d for d in dirs if not d["is_ai_related"]]

    print("=" * 70)
    print("AI/モデル関連ディレクトリ（Dドライブ移動推奨）")
    print("=" * 70)
    print()

    for i, result in enumerate(ai_dirs[:30], 1):
        print(f"{i}. {result['path']}")
        print(f"   サイズ: {result['size_gb']:.2f} GB")
        print()

    print("=" * 70)
    print("その他の大きなディレクトリ")
    print("=" * 70)
    print()

    for i, result in enumerate(other_dirs[:20], 1):
        print(f"{i}. {result['path']}")
        print(f"   サイズ: {result['size_gb']:.2f} GB")
        print()

    # 大きなファイルを検索
    print("=" * 70)
    print("大きなファイルを検索中...")
    print("=" * 70)
    print()

    files = find_large_files(SEARCH_PATHS, min_size_mb=100)
    files.sort(key=lambda x: x["size"], reverse=True)

    print(f"見つかった大きなファイル: {len(files)}個")
    print()

    ai_files = [f for f in files if f["is_ai_related"]]

    if ai_files:
        print("=" * 70)
        print("AI/モデル関連ファイル（Dドライブ移動推奨）")
        print("=" * 70)
        print()

        for i, result in enumerate(ai_files[:20], 1):
            print(f"{i}. {result['path']}")
            print(f"   サイズ: {result['size_gb']:.2f} GB")
            print()

    # サマリー
    total_ai_size = sum(d["size"] for d in ai_dirs) + sum(f["size"] for f in ai_files)

    print("=" * 70)
    print("サマリー")
    print("=" * 70)
    print()
    print(f"AI/モデル関連の合計サイズ: {format_size(total_ai_size)}")
    print(f"  - ディレクトリ: {len(ai_dirs)}個")
    print(f"  - ファイル: {len(ai_files)}個")
    print()
    print(f"その他の大きなディレクトリ: {len(other_dirs)}個")
    print()

if __name__ == "__main__":
    main()
