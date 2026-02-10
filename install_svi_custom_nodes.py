"""
SVI × Wan 2.2 カスタムノード自動インストールスクリプト
ComfyUI Manager APIを使用してカスタムノードをインストール
"""

import requests
import time
import json
from pathlib import Path
import subprocess
import sys
import io

# Windows環境での文字エンコーディング設定
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import os
COMFYUI_URL = os.getenv("COMFYUI_URL", "http://localhost:8188")
# ComfyUIパスを環境変数から取得（デフォルト: C:/ComfyUI）
COMFYUI_PATH = Path(os.getenv("COMFYUI_PATH", "C:/ComfyUI"))
CUSTOM_NODES_PATH = COMFYUI_PATH / "custom_nodes"

# 必要なカスタムノード
REQUIRED_CUSTOM_NODES = [
    {
        "name": "ComfyUI-VideoHelperSuite",
        "url": "https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite",
        "description": "動画処理用"
    },
    {
        "name": "ComfyUI-AnimateDiff-Evolved",
        "url": "https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved",
        "description": "動画生成用"
    },
    {
        "name": "ComfyUI-Stable-Video-Diffusion",
        "url": "https://github.com/Fannovel16/comfyui-stable-video-diffusion",
        "description": "SVI統合用"
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
                print(f"   [INFO] 依存関係をインストール中...")
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-r", str(requirements_file)],
                    timeout=300
                )
            
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


def install_via_comfyui_manager_api():
    """ComfyUI Manager API経由でインストール（試行）"""
    try:
        # ComfyUI ManagerのAPIエンドポイントを試行
        # 注意: ComfyUI ManagerのAPIは公式に公開されていない可能性があります
        manager_api_url = f"{COMFYUI_URL}/customnode/install"
        
        for node in REQUIRED_CUSTOM_NODES:
            try:
                response = requests.post(
                    manager_api_url,
                    json={"url": node["url"]},
                    timeout=30
                )
                if response.status_code == 200:
                    print(f"   [OK] {node['name']} をAPI経由でインストールしました")
                else:
                    print(f"   [WARN] {node['name']} のAPIインストールに失敗（手動インストールが必要）")
            except Exception:
                pass
    except Exception:
        pass


def main():
    """メイン関数"""
    print("=" * 60)
    print("SVI × Wan 2.2 カスタムノード自動インストール")
    print("=" * 60)
    print()
    
    # ComfyUIの確認
    print("[1] ComfyUIの確認...")
    if not COMFYUI_PATH.exists():
        print(f"   [NG] ComfyUIが見つかりません: {COMFYUI_PATH}")
        print("   ComfyUIをインストールしてください")
        return False
    
    print(f"   [OK] ComfyUIが見つかりました: {COMFYUI_PATH}")
    
    # ComfyUIが起動しているか確認（オプション）
    print()
    print("[2] ComfyUIサーバーの確認...")
    if check_comfyui_running():
        print("   [OK] ComfyUIサーバーが起動しています")
    else:
        print("   [INFO] ComfyUIサーバーは起動していませんが、カスタムノードのインストールは続行します")
        print("   （ComfyUIは起動していなくても、Git経由でカスタムノードをインストールできます）")
    
    # custom_nodesディレクトリの確認
    print()
    print("[3] カスタムノードディレクトリの確認...")
    if not CUSTOM_NODES_PATH.exists():
        CUSTOM_NODES_PATH.mkdir(parents=True, exist_ok=True)
        print(f"   [OK] ディレクトリを作成しました: {CUSTOM_NODES_PATH}")
    else:
        print(f"   [OK] ディレクトリが存在します: {CUSTOM_NODES_PATH}")
    
    # カスタムノードのインストール
    print()
    print("[4] カスタムノードのインストール...")
    print()
    
    success_count = 0
    for node in REQUIRED_CUSTOM_NODES:
        print(f"📦 {node['name']} ({node['description']})")
        if install_custom_node_via_git(node['name'], node['url']):
            success_count += 1
        print()
    
    # 結果サマリー
    print("=" * 60)
    print("インストール結果")
    print("=" * 60)
    print(f"成功: {success_count}/{len(REQUIRED_CUSTOM_NODES)}")
    print()
    
    if success_count == len(REQUIRED_CUSTOM_NODES):
        print("[OK] すべてのカスタムノードのインストールが完了しました！")
        print()
        print("次のステップ:")
        print("1. ComfyUIを再起動してください（カスタムノードを読み込むため）")
        print("2. 動作確認を実行してください:")
        print("   python test_svi_wan22.py")
    else:
        print("[WARN] 一部のカスタムノードのインストールに失敗しました")
        print("手動でインストールしてください:")
        print("1. ComfyUIを起動")
        print("2. ブラウザで http://localhost:8188 にアクセス")
        print("3. 「Manager」→「Install Missing Custom Nodes」を実行")
    
    return success_count == len(REQUIRED_CUSTOM_NODES)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nインストールが中断されました")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nエラーが発生しました: {e}")
        sys.exit(1)

