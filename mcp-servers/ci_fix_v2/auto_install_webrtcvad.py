#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
webrtcvad自動インストールスクリプト
最適な方法を自動的に試行
"""

import sys
import subprocess
import os
from pathlib import Path

# Windowsコンソールのエンコーディング設定
if sys.platform == "win32":
    import io
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

def check_webrtcvad():
    """webrtcvadがインストールされているか確認"""
    try:
        import webrtcvad
        print("OK: webrtcvad は既にインストールされています")
        return True
    except ImportError:
        return False

def try_webrtcvad_wheels():
    """webrtcvad-wheels（ビルド済みwheel）をインストール（推奨）"""
    print("\n[方法1] webrtcvad-wheels（ビルド済みwheel）をインストール中...")
    print("  これは最も簡単な方法です！PyPIから直接インストールします。")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "webrtcvad-wheels"],
            capture_output=True,
            text=True,
            timeout=300
        )
        if result.returncode == 0:
            print("OK: webrtcvad-wheelsインストール成功")
            return True
        else:
            print(f"NG: webrtcvad-wheelsインストール失敗: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("NG: タイムアウト")
        return False
    except Exception as e:
        print(f"NG: エラー: {e}")
        return False

def try_github_install():
    """GitHubから直接インストール"""
    print("\n[方法1b] GitHubから直接インストール中...")
    print("  PyPIが使えない場合の代替方法です。")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "git+https://github.com/daanzu/py-webrtcvad-wheels.git"],
            capture_output=True,
            text=True,
            timeout=300
        )
        if result.returncode == 0:
            print("OK: GitHubからインストール成功")
            return True
        else:
            print(f"NG: GitHubインストール失敗: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("NG: タイムアウト")
        return False
    except Exception as e:
        print(f"NG: エラー: {e}")
        return False

def try_pip_install():
    """pipで直接インストールを試行"""
    print("\n[方法2] pipで直接インストールを試行中...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "webrtcvad"],
            capture_output=True,
            text=True,
            timeout=300
        )
        if result.returncode == 0:
            print("OK: pipインストール成功")
            return True
        else:
            print(f"NG: pipインストール失敗: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("NG: タイムアウト")
        return False
    except Exception as e:
        print(f"NG: エラー: {e}")
        return False

def try_conda_install():
    """condaでインストールを試行"""
    print("\n[方法3] condaでインストールを試行中...")
    try:
        result = subprocess.run(
            ["conda", "install", "-c", "conda-forge", "webrtcvad", "-y"],
            capture_output=True,
            text=True,
            timeout=300
        )
        if result.returncode == 0:
            print("OK: condaインストール成功")
            return True
        else:
            print(f"NG: condaインストール失敗（condaが利用できない可能性があります）")
            return False
    except FileNotFoundError:
        print("WARN: condaが見つかりません（スキップ）")
        return False
    except subprocess.TimeoutExpired:
        print("NG: タイムアウト")
        return False
    except Exception as e:
        print(f"NG: エラー: {e}")
        return False

def find_wheel_file():
    """ダウンロードフォルダからwheelファイルを検索"""
    print("\n[方法4] ビルド済みwheelファイルを検索中...")

    # 検索パス
    search_paths = [
        Path.home() / "Downloads",
        Path.home() / "Desktop",
        Path.cwd()
    ]

    for search_path in search_paths:
        if not search_path.exists():
            continue

        # webrtcvadのwheelファイルを検索
        wheel_files = list(search_path.glob("webrtcvad-*.whl"))
        if wheel_files:
            print(f"OK: wheelファイルが見つかりました: {wheel_files[0]}")
            return wheel_files[0]

    print("WARN: wheelファイルが見つかりませんでした")
    return None

def install_wheel(wheel_path):
    """wheelファイルをインストール"""
    print(f"\n[方法4] wheelファイルをインストール中: {wheel_path}")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", str(wheel_path)],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0:
            print("OK: wheelインストール成功")
            return True
        else:
            print(f"NG: wheelインストール失敗: {result.stderr}")
            return False
    except Exception as e:
        print(f"NG: エラー: {e}")
        return False

def main():
    """メイン関数"""
    print("=" * 60)
    print("webrtcvad 自動インストールスクリプト")
    print("=" * 60)

    # 既にインストールされているか確認
    if check_webrtcvad():
        return

    print("\nwebrtcvad が見つかりません。インストールを開始します...")

    # 方法1: webrtcvad-wheels（ビルド済みwheel）をインストール（推奨）
    if try_webrtcvad_wheels():
        if check_webrtcvad():
            print("\nOK: インストール完了！")
            return

    # 方法1b: GitHubから直接インストール
    if try_github_install():
        if check_webrtcvad():
            print("\nOK: インストール完了！")
            return

    # 方法2: pipで直接インストール
    if try_pip_install():
        if check_webrtcvad():
            print("\nOK: インストール完了！")
            return

    # 方法3: condaでインストール
    if try_conda_install():
        if check_webrtcvad():
            print("\nOK: インストール完了！")
            return

    # 方法4: ビルド済みwheelを使用
    wheel_file = find_wheel_file()
    if wheel_file:
        if install_wheel(wheel_file):
            if check_webrtcvad():
                print("\nOK: インストール完了！")
                return

    # すべて失敗した場合
    print("\n" + "=" * 60)
    print("NG: 自動インストールに失敗しました")
    print("=" * 60)
    print("\n手動インストール方法:")
    print("\n【推奨1】webrtcvad-wheelsを使用（PyPI）:")
    print("  pip install webrtcvad-wheels")
    print("\n【推奨2】GitHubから直接インストール:")
    print("  pip install git+https://github.com/daanzu/py-webrtcvad-wheels.git")
    print("\n【代替1】ビルド済みwheelを使用:")
    print("  1. https://www.lfd.uci.edu/~gohlke/pythonlibs/#webrtcvad からダウンロード")
    print("  2. pip install webrtcvad-*.whl")
    print("\n【代替2】Visual C++ Build Toolsをインストール:")
    print("  1. https://visualstudio.microsoft.com/visual-cpp-build-tools/ からダウンロード")
    print("  2. C++ ビルドツールをインストール")
    print("  3. pip install webrtcvad")
    print("\n詳細: docs/voice_webrtcvad_install_guide.md")

if __name__ == "__main__":
    main()
