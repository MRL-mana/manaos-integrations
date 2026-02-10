"""
LTX-2 カスタムノード自動インストールスクリプト
Super LTX-2設定に必要なカスタムノードをインストール
- KJNodes (NAG機能のため)
- ComfyUI-GGUF (GGUFモデルサポート)
- その他の必要なノード
"""

import requests
import time
import json
import os
from pathlib import Path
import subprocess
import sys
import io

# Windows環境での文字エンコーディング設定
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding='utf-8', errors='replace'
    )
    sys.stderr = io.TextIOWrapper(
        sys.stderr.buffer, encoding='utf-8', errors='replace'
    )

COMFYUI_URL = os.getenv("COMFYUI_URL", "http://localhost:8188")
# ComfyUIパスを環境変数から取得（デフォルト: C:/ComfyUI）
COMFYUI_PATH = Path(os.getenv("COMFYUI_PATH", "C:/ComfyUI"))
CUSTOM_NODES_PATH = COMFYUI_PATH / "custom_nodes"

# 必要なカスタムノード（Super LTX-2設定）
REQUIRED_CUSTOM_NODES = [
    {
        "name": "ComfyUI-KJNodes",
        "url": "https://github.com/kijai/ComfyUI-KJNodes",
        "description": "NAG機能のために必要",
        "required": True
    },
    {
        "name": "ComfyUI-GGUF",
        "url": "https://github.com/city96/ComfyUI-GGUF",
        "description": "GGUFモデル（Q8 GGUFなど）をサポート",
        "required": True
    },
    {
        "name": "ComfyUI-LTXVideo",
        "url": "https://github.com/Lightricks/ComfyUI-LTXVideo",
        "description": "LTX-2動画生成ノード（必須）",
        "required": True
    },
    {
        "name": "ComfyUI-VideoHelperSuite",
        "url": "https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite",
        "description": "動画処理ユーティリティ（推奨）",
        "required": False
    },
    {
        "name": "ComfyUI-Manager",
        "url": "https://github.com/ltdrdata/ComfyUI-Manager",
        "description": "カスタムノード管理（推奨）",
        "required": False
    }
]


def check_comfyui_running():
    """ComfyUIが起動しているか確認"""
    try:
        response = requests.get(f"{COMFYUI_URL}/system_stats", timeout=5)
        return response.status_code == 200
    except Exception:
        return False


def install_custom_node_via_git(name, url):
    """Git経由でカスタムノードをインストール"""
    node_path = CUSTOM_NODES_PATH / name
    
    if node_path.exists():
        print(f"   [OK] {name} は既にインストールされています")
        # 最新バージョンに更新するか確認
        try:
            # Git pullを試行
            result = subprocess.run(
                ["git", "pull"],
                cwd=str(node_path),
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.returncode == 0:
                msg = f"   [INFO] {name} を最新バージョンに更新しました"
                print(msg)
        except Exception:
            pass  # 更新に失敗しても続行
        return True

    print(f"   📦 {name} をインストール中...")
    
    try:
        # Gitクローン
        result = subprocess.run(
            ["git", "clone", url, str(node_path)],
            cwd=str(CUSTOM_NODES_PATH),
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0:
            print(f"   [OK] {name} のインストールが完了しました")
            
            # requirements.txtがあればインストール
            requirements_file = node_path / "requirements.txt"
            if requirements_file.exists():
                print("   [INFO] 依存関係をインストール中...")
                try:
                    subprocess.run(
                        [
                            sys.executable, "-m", "pip", "install", "-r",
                            str(requirements_file)
                        ],
                        timeout=300,
                        check=True
                    )
                    msg = f"   [OK] {name} の依存関係をインストールしました"
                    print(msg)
                except subprocess.CalledProcessError as e:
                    msg = f"   [WARN] 依存関係のインストールに警告: {e}"
                    print(msg)
                except Exception as e:
                    msg = f"   [WARN] 依存関係のインストール中にエラー: {e}"
                    print(msg)
            
            return True
        else:
            print(f"   [NG] {name} のインストールに失敗しました: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print(f"   [WARN] {name} のインストールがタイムアウトしました")
        return False
    except Exception as e:
        print(f"   [ERROR] エラー: {e}")
        return False


def main():
    """メイン関数"""
    print("=" * 60)
    print("LTX-2 カスタムノード自動インストール")
    msg = "Super LTX-2設定に必要なカスタムノードをインストールします"
    print(msg)
    print("=" * 60)
    print()

    # ComfyUIの確認
    print("[1] ComfyUIの確認...")
    default_comfyui = os.getenv("COMFYUI_PATH", "C:/ComfyUI")
    search_paths = [
        Path(default_comfyui),
        Path.home() / "ComfyUI",
        Path.home() / "Desktop" / "ComfyUI",
        Path("D:/ComfyUI"),
        Path("E:/ComfyUI")
    ]

    found_path = None
    for path in search_paths:
        if path.exists():
            main_py = path / "main.py"
            if main_py.exists():
                found_path = path
                COMFYUI_PATH = path
                CUSTOM_NODES_PATH = path / "custom_nodes"
                break

    if not found_path:
        print("   [NG] ComfyUIが見つかりません")
        print("   ComfyUIをインストールしてください")
        print("   または、環境変数 COMFYUI_PATH を設定してください")
        return False

    print(f"   [OK] ComfyUIが見つかりました: {COMFYUI_PATH}")

    # ComfyUIが起動しているか確認（オプション）
    print()
    print("[2] ComfyUIサーバーの確認...")
    if check_comfyui_running():
        print("   [OK] ComfyUIサーバーが起動しています")
    else:
        msg1 = "   [INFO] ComfyUIサーバーは起動していませんが、"
        msg2 = "カスタムノードのインストールは続行します"
        print(f"{msg1}{msg2}")
        msg3 = "   （ComfyUIは起動していなくても、"
        msg4 = "Git経由でカスタムノードをインストールできます）"
        print(f"{msg3}{msg4}")

    # custom_nodesディレクトリの確認
    print()
    print("[3] カスタムノードディレクトリの確認...")
    if not CUSTOM_NODES_PATH.exists():
        CUSTOM_NODES_PATH.mkdir(parents=True, ok=True)
        print(f"   [OK] ディレクトリを作成しました: {CUSTOM_NODES_PATH}")
    else:
        print(f"   [OK] ディレクトリが存在します: {CUSTOM_NODES_PATH}")

    # カスタムノードのインストール
    print()
    print("[4] カスタムノードのインストール...")
    print()
    
    success_count = 0
    required_count = 0
    required_success = 0
    
    for node in REQUIRED_CUSTOM_NODES:
        required = node.get("required", False)
        if required:
            required_count += 1
        
        print(f"📦 {node['name']} ({node['description']})")
        if install_custom_node_via_git(node['name'], node['url']):
            success_count += 1
            if required:
                required_success += 1
        print()
    
    # 結果サマリー
    print("=" * 60)
    print("インストール結果")
    print("=" * 60)
    print(f"成功: {success_count}/{len(REQUIRED_CUSTOM_NODES)}")
    print(f"必須ノード成功: {required_success}/{required_count}")
    print()
    
    if required_success == required_count:
        msg = "[OK] すべての必須カスタムノードのインストールが完了しました！"
        print(msg)
        print()
        print("次のステップ:")
        msg1 = "1. ComfyUIを再起動してください"
        msg2 = "（カスタムノードを読み込むため）"
        print(f"{msg1}{msg2}")
        msg3 = "2. LTX-2モデル（Q8 GGUF）をダウンロードして配置"
        print(f"{msg3}してください")
        print("3. 動作確認を実行してください")
        print()
        print("推奨モデル:")
        print("  - LTX-2 Q8 GGUFモデル")
        hf_url = "https://huggingface.co/unsloth/LTX-2-GGUF"
        print(f"  - ダウンロード先: {hf_url}")
        print()
        print("モデルの配置場所:")
        model_path = COMFYUI_PATH / 'models' / 'unet'
        print(f"  - {model_path}")
        return True
    else:
        print("[WARN] 一部の必須カスタムノードのインストールに失敗しました")
        print("手動でインストールしてください:")
        print("1. ComfyUIを起動")
        print("2. ブラウザで http://localhost:8188 にアクセス")
        print("3. 「Manager」→「Install Missing Custom Nodes」を実行")
        print()
        print("必要な必須ノード:")
        for node in REQUIRED_CUSTOM_NODES:
            if node.get("required", False):
                print(f"  - {node['name']}: {node['url']}")
        
        return False


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n[INFO] インストールが中断されました")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] 予期しないエラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
