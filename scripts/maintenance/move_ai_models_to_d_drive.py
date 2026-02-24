"""
AI/モデル関連ファイルをDドライブに移動
"""
import os
import shutil
from pathlib import Path

# 移動対象（検索結果から）
MOVE_TARGETS = [
    {
        "source": Path(r"C:\Users\mana4\.ollama\models"),
        "destination": Path(r"D:\manaos_integrations\.ollama\models"),
        "description": "Ollama Models (346.38 GB)",
        "create_symlink": True,
    },
    {
        "source": Path(r"C:\Users\mana4\.lmstudio\models"),
        "destination": Path(r"D:\manaos_integrations\.lmstudio\models"),
        "description": "LM Studio Models (105.95 GB)",
        "create_symlink": True,
    },
    {
        "source": Path(r"C:\Users\mana4\OneDrive\Desktop\AI_Data"),
        "destination": Path(r"D:\manaos_integrations\AI_Data"),
        "description": "OneDrive AI_Data (74.77 GB)",
        "create_symlink": True,
    },
    {
        "source": Path(r"C:\Users\mana4\OneDrive\Desktop\Projects\lora_output_mana_favorite_incremental"),
        "destination": Path(r"D:\manaos_integrations\lora_output_mana_favorite_incremental"),
        "description": "LoRA Output Incremental (51.72 GB)",
        "create_symlink": True,
    },
    {
        "source": Path(r"C:\Users\mana4\AppData\Local\pip\cache"),
        "destination": Path(r"D:\manaos_integrations\pip_cache"),
        "description": "pip cache (4.89 GB)",
        "create_symlink": True,
    },
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

def move_directory(source, destination, create_symlink=True):
    """
    ディレクトリを移動し、必要に応じてシンボリックリンクを作成

    Returns:
        (success, message, size_freed)
    """
    if not source.exists():
        return False, f"ソースが存在しません: {source}", 0

    if not source.is_dir():
        return False, f"ソースはディレクトリではありません: {source}", 0

    # 既にシンボリックリンクの場合はスキップ
    try:
        if source.is_symlink():
            return False, f"既にシンボリックリンクです: {source}", 0
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
                import subprocess
                # 管理者権限が必要な場合があるので、subprocessで実行
                result = subprocess.run(
                    ["cmd", "/c", "mklink", "/D", str(source), str(destination)],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    print(f"[OK] シンボリックリンク作成: {source} -> {destination}")
                else:
                    print(f"[WARN] シンボリックリンク作成に失敗（管理者権限が必要）: {result.stderr}")
                    print(f"手動で実行: mklink /D {source} {destination}")
            except Exception as e:
                print(f"[WARN] シンボリックリンクの作成に失敗しました: {e}")
                print(f"手動でシンボリックリンクを作成してください: mklink /D {source} {destination}")

        return True, f"移動完了: {source.name}", size

    except Exception as e:
        return False, f"エラー: {e}", 0

def main():
    print("=" * 70)
    print("AI/モデル関連ファイルをDドライブに移動")
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
            total_size += size

            move_list.append({
                **target,
                "size": size,
            })

            print(f"[{target['description']}]")
            print(f"  ソース: {source}")
            print(f"  移動先: {target['destination']}")
            print(f"  サイズ: {format_size(size)}")
            print()

    print(f"合計移動サイズ: {format_size(total_size)}")
    print()

    # 確認
    if not move_list:
        print("移動対象がありません")
        return

    if d_free < total_size:
        print(f"[WARN] Dドライブの空き容量が不足しています")
        print(f"  必要: {format_size(total_size)}")
        print(f"  利用可能: {format_size(d_free)}")
        print()
        return

    print("自動実行モード: 移動を開始します...")
    print()
    print("=" * 70)
    print("移動実行")
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
        create_symlink = target.get("create_symlink", True)

        print(f"[{description}]")
        success, message, size_freed = move_directory(
            source,
            destination,
            create_symlink
        )

        if success:
            print(f"[OK] {message}")
            success_count += 1
            total_freed += size_freed
        else:
            print(f"[ERROR] {message}")
            errors.append(f"{description}: {message}")

        print()

    # 結果表示
    print("=" * 70)
    print("結果")
    print("=" * 70)
    print()
    print(f"成功: {success_count}/{len(move_list)}")
    print(f"解放された容量: {format_size(total_freed)}")

    if errors:
        print()
        print("エラー:")
        for error in errors:
            print(f"  - {error}")

    print()
    print("注意: シンボリックリンクの作成に失敗した場合は、")
    print("管理者権限でPowerShellを実行して手動で作成してください。")
    print()

if __name__ == "__main__":
    main()
