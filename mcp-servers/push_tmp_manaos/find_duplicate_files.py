"""
重複ファイルを検出
"""
import os
import hashlib
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
}

# 検索対象のパス
SEARCH_PATHS = [
    Path(r"C:\Users"),
    Path(r"C:\Temp"),
    Path(r"C:\tmp"),
]

# スキップする拡張子（システムファイルなど）
SKIP_EXTENSIONS = {
    ".lnk", ".tmp", ".temp", ".log", ".cache",
}

def should_exclude(path_str):
    """除外すべきパスかチェック"""
    path_str_lower = path_str.lower()
    for exclude in EXCLUDE_PATHS:
        if exclude.lower() in path_str_lower:
            return True
    return False

def calculate_file_hash(file_path, chunk_size=8192):
    """ファイルのハッシュを計算"""
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, 'rb') as f:
            while chunk := f.read(chunk_size):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except (PermissionError, OSError, IOError):
        return None

def find_duplicates_by_size(search_paths):
    """サイズで重複候補を検索"""
    size_map = defaultdict(list)

    for search_path in search_paths:
        if not search_path.exists():
            continue

        print(f"スキャン中: {search_path}")

        try:
            for root, dirs, files in os.walk(search_path):
                if should_exclude(root):
                    dirs.clear()
                    continue

                for file in files:
                    file_path = os.path.join(root, file)

                    # 拡張子チェック
                    if any(file.lower().endswith(ext) for ext in SKIP_EXTENSIONS):
                        continue

                    try:
                        stat = os.stat(file_path)
                        size = stat.st_size

                        # 1MB以上のファイルのみ
                        if size >= 1024 * 1024:
                            size_map[size].append(file_path)
                    except (PermissionError, OSError):
                        pass
        except (PermissionError, OSError) as e:
            print(f"  エラー: {search_path} - {e}")

    # サイズが同じファイルが2個以上あるものを返す
    duplicates_by_size = {size: paths for size, paths in size_map.items() if len(paths) > 1}
    return duplicates_by_size

def verify_duplicates_by_hash(duplicates_by_size):
    """ハッシュで重複を確認"""
    verified_duplicates = defaultdict(list)

    print()
    print("ハッシュで重複を確認中...")
    print()

    total_groups = len(duplicates_by_size)
    processed = 0

    for size, paths in duplicates_by_size.items():
        processed += 1
        if processed % 100 == 0:
            print(f"  処理中: {processed}/{total_groups}")

        # ハッシュを計算
        hash_map = defaultdict(list)
        for path in paths:
            file_hash = calculate_file_hash(path)
            if file_hash:
                hash_map[file_hash].append(path)

        # 同じハッシュのファイルを重複として記録
        for file_hash, duplicate_paths in hash_map.items():
            if len(duplicate_paths) > 1:
                verified_duplicates[file_hash] = duplicate_paths

    return verified_duplicates

def calculate_space_saved(duplicates):
    """削除で節約できる容量を計算"""
    total_saved = 0

    for file_hash, paths in duplicates.items():
        if len(paths) > 1:
            # 最初の1つを残して、残りを削除
            try:
                size = os.path.getsize(paths[0])
                # 重複分のサイズ（最初の1つ以外）
                total_saved += size * (len(paths) - 1)
            except (OSError, PermissionError):
                pass

    return total_saved

def main():
    print("=" * 70)
    print("重複ファイル検出")
    print("=" * 70)
    print()

    # サイズで重複候補を検索
    print("サイズで重複候補を検索中...")
    print()
    duplicates_by_size = find_duplicates_by_size(SEARCH_PATHS)

    print(f"サイズが同じファイルグループ: {len(duplicates_by_size)}個")
    print()

    # ハッシュで確認
    verified_duplicates = verify_duplicates_by_hash(duplicates_by_size)

    print()
    print("=" * 70)
    print("検出された重複ファイル")
    print("=" * 70)
    print()

    if not verified_duplicates:
        print("重複ファイルは見つかりませんでした")
        return

    # 重複を表示
    total_duplicates = 0
    total_saved = 0

    for file_hash, paths in sorted(verified_duplicates.items(), key=lambda x: len(x[1]), reverse=True):
        if len(paths) > 1:
            total_duplicates += len(paths) - 1

            try:
                size = os.path.getsize(paths[0])
                saved = size * (len(paths) - 1)
                total_saved += saved

                print(f"重複グループ ({len(paths)}個, 削除可能: {len(paths)-1}個, 節約: {size * (len(paths)-1) / (1024**2):.2f} MB)")
                print(f"  サイズ: {size / (1024**2):.2f} MB")
                print(f"  ハッシュ: {file_hash[:16]}...")
                print()

                # 最初の1つを保持、残りを削除候補
                print(f"  [保持] {paths[0]}")
                for path in paths[1:]:
                    print(f"  [削除候補] {path}")
                print()
            except (OSError, PermissionError):
                pass

    print("=" * 70)
    print("サマリー")
    print("=" * 70)
    print()
    print(f"重複ファイルグループ: {len(verified_duplicates)}個")
    print(f"削除可能なファイル数: {total_duplicates}個")
    print(f"節約できる容量: {total_saved / (1024**3):.2f} GB")
    print()
    print("注意: 実際の削除は慎重に行ってください")
    print()

if __name__ == "__main__":
    main()
