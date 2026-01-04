"""
SVI × Wan 2.2 動作確認スクリプト
"""

import sys
import os
from pathlib import Path

# Windows環境での文字エンコーディング設定
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# パスを追加
sys.path.insert(0, str(Path(__file__).parent))

try:
    from svi_wan22_video_integration import SVIWan22VideoIntegration
except ImportError as e:
    print(f"❌ モジュールのインポートに失敗しました: {e}")
    print("依存関係をインストールしてください:")
    print("  pip install requests")
    sys.exit(1)

def test_comfyui_connection():
    """ComfyUIへの接続テスト"""
    print("=" * 60)
    print("SVI × Wan 2.2 動作確認テスト")
    print("=" * 60)
    print()
    
    print("[1] ComfyUIへの接続確認...")
    svi = SVIWan22VideoIntegration(base_url="http://localhost:8188")
    
    if not svi.is_available():
        print("   ❌ ComfyUIに接続できません")
        print("   確認事項:")
        print("   1. ComfyUIサーバーが起動しているか")
        print("   2. URLが正しいか（デフォルト: http://localhost:8188）")
        print("   3. ネットワーク接続が正常か")
        print()
        print("ComfyUIを起動するには:")
        print("  .\\start_comfyui_local.ps1")
        return False
    
    print("   ✅ ComfyUIに接続できました")
    print()
    
    print("[2] キュー状態の確認...")
    queue_status = svi.get_queue_status()
    if "error" in queue_status:
        print(f"   ⚠️  キュー状態の取得に問題がありました: {queue_status['error']}")
    else:
        print("   ✅ キュー状態を取得できました")
        if "queue_running" in queue_status:
            print(f"      実行中: {len(queue_status['queue_running'])}件")
        if "queue_pending" in queue_status:
            print(f"      待機中: {len(queue_status['queue_pending'])}件")
    print()
    
    print("[3] 実行履歴の確認...")
    history = svi.get_history(max_items=5)
    print(f"   ✅ 履歴を取得できました（{len(history)}件）")
    print()
    
    print("[4] ワークフロー作成テスト...")
    try:
        # テスト用のワークフローを作成（実際の画像パスは必要）
        test_image_path = "test_start_image.png"
        if not Path(test_image_path).exists():
            print(f"   ⚠️  テスト画像が見つかりません: {test_image_path}")
            print("   実際の画像パスを指定してテストしてください")
        else:
            workflow = svi.create_svi_wan22_workflow(
                start_image_path=test_image_path,
                prompt="a beautiful landscape",
                video_length_seconds=5,
                steps=6,
                motion_strength=1.3
            )
            print("   ✅ ワークフローの作成に成功しました")
            print(f"      ノード数: {len(workflow)}")
    except Exception as e:
        print(f"   ⚠️  ワークフロー作成でエラー: {e}")
    print()
    
    print("=" * 60)
    print("✅ 基本テスト完了")
    print("=" * 60)
    print()
    print("次のステップ:")
    print("1. 実際の画像を使用して動画生成をテスト")
    print("2. ManaOS統合APIサーバーから動作確認")
    print("3. 統合APIエンドポイントのテスト")
    print()
    
    return True


def test_api_endpoint():
    """統合APIエンドポイントのテスト"""
    print()
    print("=" * 60)
    print("統合APIエンドポイントのテスト")
    print("=" * 60)
    print()
    
    try:
        import requests
    except ImportError:
        print("❌ requestsライブラリがインストールされていません")
        print("   pip install requests")
        return False
    
    api_url = os.getenv("MANAOS_INTEGRATION_API_URL", "http://localhost:9500")
    
    print(f"[1] 統合APIサーバーへの接続確認 ({api_url})...")
    try:
        response = requests.get(f"{api_url}/health", timeout=5)
        if response.status_code == 200:
            print("   ✅ 統合APIサーバーに接続できました")
        else:
            print(f"   ⚠️  統合APIサーバーの応答が異常です: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"   ❌ 統合APIサーバーに接続できません: {e}")
        print("   統合APIサーバーを起動してください:")
        print("   python unified_api_server.py")
        return False
    
    print()
    print("[2] SVI動画生成エンドポイントの確認...")
    try:
        # エンドポイントの存在確認（実際の生成はしない）
        response = requests.get(f"{api_url}/api/integrations/status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if "svi_wan22" in str(data):
                print("   ✅ SVI動画生成統合が登録されています")
            else:
                print("   ⚠️  SVI動画生成統合が登録されていない可能性があります")
        else:
            print(f"   ⚠️  ステータス取得に失敗: {response.status_code}")
    except Exception as e:
        print(f"   ⚠️  エンドポイント確認でエラー: {e}")
    
    print()
    print("=" * 60)
    print("✅ APIテスト完了")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    # ComfyUI接続テスト
    comfyui_ok = test_comfyui_connection()
    
    # APIエンドポイントテスト
    api_ok = test_api_endpoint()
    
    # 結果サマリー
    print()
    print("=" * 60)
    print("テスト結果サマリー")
    print("=" * 60)
    print(f"ComfyUI接続: {'✅ OK' if comfyui_ok else '❌ NG'}")
    print(f"APIエンドポイント: {'✅ OK' if api_ok else '❌ NG'}")
    print()
    
    if comfyui_ok and api_ok:
        print("✅ すべてのテストが成功しました！")
        print("SVI × Wan 2.2動画生成機能を使用できます")
    else:
        print("⚠️  一部のテストが失敗しました")
        print("上記の確認事項を確認してください")

