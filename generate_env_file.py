#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
環境変数設定ファイル（.env）を自動生成するスクリプト
現在の環境を検出して、適切な設定ファイルを生成します
"""

import os
import sys
from pathlib import Path
import io

# Windows環境での文字エンコーディング設定
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding='utf-8', errors='replace'
    )
    sys.stderr = io.TextIOWrapper(
        sys.stderr.buffer, encoding='utf-8', errors='replace'
    )


def detect_comfyui_path():
    """ComfyUIのパスを自動検出"""
    search_paths = [
        Path(os.getenv("COMFYUI_PATH", "C:/ComfyUI")),
        Path("C:/ComfyUI"),
        Path("D:/ComfyUI"),
        Path("E:/ComfyUI"),
        Path.home() / "ComfyUI",
        Path.home() / "Desktop" / "ComfyUI",
    ]

    for path in search_paths:
        main_py = path / "main.py"
        if main_py.exists():
            return str(path)

    return "C:/ComfyUI"  # デフォルト値


def detect_mana_models_path():
    """ManaOSモデルディレクトリを自動検出"""
    search_paths = [
        Path(os.getenv("MANA_MODELS_DIR", "C:/mana_workspace/models")),
        Path("C:/mana_workspace/models"),
        Path("D:/mana_workspace/models"),
        Path.home() / "mana_workspace" / "models",
    ]

    for path in search_paths:
        if path.exists():
            return str(path)

    return "C:/mana_workspace/models"  # デフォルト値


def detect_ollama_models_path():
    """Ollamaモデルパスを自動検出"""
    user_home = Path.home()
    ollama_paths = [
        Path(os.getenv("OLLAMA_MODELS", "")),
        user_home / ".ollama" / "models",
        Path("C:/Users") / user_home.name / ".ollama" / "models",
    ]

    for path in ollama_paths:
        if path and path.exists():
            return str(path)

    # デフォルト値
    return str(user_home / ".ollama" / "models")


def detect_mufufu_dirs():
    """ムフフ画像ディレクトリを自動検出"""
    user_home = Path.home()
    onedrive_desktop = user_home / "OneDrive" / "Desktop"
    desktop = user_home / "Desktop"

    dirs = {}
    lora_dir = "lora_output_mana_favorite_japanese_clear_gal (1)"
    search_paths = {
        "MUFUFU_IMAGES_DIR_1": onedrive_desktop / "mufufu_cyberrealistic_10",
        "MUFUFU_IMAGES_DIR_2": onedrive_desktop / "output",
        "MUFUFU_IMAGES_DIR_3": desktop / lora_dir,
        "MUFUFU_IMAGES_DIR_4": onedrive_desktop / "mufufu_combined_10",
    }

    for key, path in search_paths.items():
        if path.exists():
            dirs[key] = str(path)
        else:
            dirs[key] = str(path)  # 存在しなくてもデフォルト値として設定

    return dirs


def generate_env_file(output_path: Path = None):
    """環境変数設定ファイルを生成"""
    if output_path is None:
        output_path = Path(__file__).parent / ".env"

    # 現在の環境を検出
    comfyui_path = detect_comfyui_path()
    mana_models_dir = detect_mana_models_path()
    ollama_models = detect_ollama_models_path()
    mufufu_dirs = detect_mufufu_dirs()

    # 既存の.envファイルから値を取得（上書きしない）
    existing_values = {}
    if output_path.exists():
        with open(output_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    existing_values[key.strip()] = value.strip()

    # 環境変数から値を取得（優先）
    env_values = {
        "COMFYUI_PATH": os.getenv("COMFYUI_PATH", comfyui_path),
        "COMFYUI_URL": os.getenv("COMFYUI_URL", "http://localhost:8188"),
        "COMFYUI_MODELS_DIR": os.getenv(
            "COMFYUI_MODELS_DIR",
            f"{comfyui_path}/models/checkpoints"
        ),
        "COMFYUI_OUTPUT_DIR": os.getenv(
            "COMFYUI_OUTPUT_DIR",
            f"{comfyui_path}/output"
        ),
        "MANA_MODELS_DIR": os.getenv("MANA_MODELS_DIR", mana_models_dir),
        "GALLERY_PORT": os.getenv("GALLERY_PORT", "5559"),
        "GALLERY_IMAGES_DIR": os.getenv("GALLERY_IMAGES_DIR", "gallery_images"),
        "OLLAMA_MODELS": os.getenv("OLLAMA_MODELS", ollama_models),
    }

    # 既存の値があればそれを使用
    for key in env_values:
        if key in existing_values:
            env_values[key] = existing_values[key]

    # ムフフディレクトリを追加
    env_values.update(mufufu_dirs)

    # .envファイルを生成
    content = """# ManaOS統合システム - 環境変数設定
# このファイルは generate_env_file.py によって自動生成されました
# 必要に応じて値を編集してください

# ============================================
# ComfyUI設定
# ============================================
COMFYUI_PATH={COMFYUI_PATH}
COMFYUI_URL={COMFYUI_URL}
COMFYUI_MODELS_DIR={COMFYUI_MODELS_DIR}
COMFYUI_OUTPUT_DIR={COMFYUI_OUTPUT_DIR}

# ============================================
# ManaOS設定
# ============================================
MANA_MODELS_DIR={MANA_MODELS_DIR}

# ============================================
# Gallery API設定
# ============================================
GALLERY_PORT={GALLERY_PORT}
GALLERY_IMAGES_DIR={GALLERY_IMAGES_DIR}

# ============================================
# Ollama設定
# ============================================
OLLAMA_MODELS={OLLAMA_MODELS}

# ============================================
# ムフフ画像ディレクトリ
# ============================================
MUFUFU_IMAGES_DIR_1={MUFUFU_IMAGES_DIR_1}
MUFUFU_IMAGES_DIR_2={MUFUFU_IMAGES_DIR_2}
MUFUFU_IMAGES_DIR_3={MUFUFU_IMAGES_DIR_3}
MUFUFU_IMAGES_DIR_4={MUFUFU_IMAGES_DIR_4}

# ============================================
# Hugging Face設定（オプション）
# ============================================
# HF_TOKEN=your_huggingface_token_here

# ============================================
# その他の設定（必要に応じて追加）
# ============================================
""".format(**env_values)

    # 既存の.envファイルがある場合はバックアップ
    if output_path.exists():
        backup_path = output_path.with_suffix('.env.backup')
        msg = f"既存の.envファイルをバックアップ: {backup_path}"
        print(msg)
        with open(backup_path, 'w', encoding='utf-8') as f:
            with open(output_path, 'r', encoding='utf-8') as original:
                f.write(original.read())

    # .envファイルを書き込み
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"✅ .envファイルを生成しました: {output_path}")
    print()
    print("検出された設定:")
    print(f"  COMFYUI_PATH: {comfyui_path}")
    print(f"  MANA_MODELS_DIR: {mana_models_dir}")
    print(f"  OLLAMA_MODELS: {ollama_models}")
    print()
    print("必要に応じて .env ファイルを編集してください")


def main():
    """メイン処理"""
    print("=" * 60)
    print("環境変数設定ファイル（.env）自動生成")
    print("=" * 60)
    print()

    # 出力パスを確認
    output_path = Path(__file__).parent / ".env"

    # 非対話モードの場合は自動で上書き
    force_overwrite = os.getenv("FORCE_OVERWRITE", "").lower() == "true"

    if output_path.exists() and not force_overwrite:
        try:
            response = input(
                ".envファイルが既に存在します。上書きしますか？ (y/N): "
            )
            if response.lower() != 'y':
                print("キャンセルしました")
                return
        except EOFError:
            # 非対話モードの場合はスキップ
            print("非対話モード: 既存の.envファイルをスキップします")
            print("上書きする場合は FORCE_OVERWRITE=true を設定してください")
            return

    # .envファイルを生成
    generate_env_file(output_path)

    print()
    print("=" * 60)
    print("完了")
    print("=" * 60)
    print()
    print("次のステップ:")
    print("1. .envファイルの内容を確認")
    print("2. 必要に応じて値を編集")
    print("3. python-dotenvを使用して読み込む:")
    print("   from dotenv import load_dotenv")
    print("   load_dotenv()")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n処理が中断されました")
        sys.exit(1)
    except Exception as e:
        print(f"\nエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
