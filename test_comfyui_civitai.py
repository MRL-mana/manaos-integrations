"""
ComfyUIとCivitAI統合のテストスクリプト
STEP1: ComfyUI起動確認とCivitAI APIキー設定確認
"""

import os
import sys
from pathlib import Path

# パスを追加
sys.path.insert(0, str(Path(__file__).parent))

# 環境変数の読み込み
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print("[OK] .envファイルを読み込みました")
    else:
        print("[INFO] .envファイルが見つかりません。環境変数を直接設定します。")
        # Secretsは直書きしません。必要なものは環境変数/.envで設定してください。
        os.environ["COMFYUI_URL"] = "http://127.0.0.1:8188"
        print("[OK] 環境変数を直接設定しました")
except ImportError:
    print("[WARN] python-dotenvがインストールされていません")
    # Secretsは直書きしません。必要なものは環境変数/.envで設定してください。
    os.environ["COMFYUI_URL"] = "http://127.0.0.1:8188"

print("\n" + "=" * 60)
print("ComfyUI & CivitAI 統合テスト")
print("=" * 60)
print()

# ComfyUI統合テスト
print("[1] ComfyUI統合テスト")
print("-" * 60)
try:
    from comfyui_integration import ComfyUIIntegration
    
    comfyui_url = os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")
    comfyui = ComfyUIIntegration(base_url=comfyui_url)
    
    if comfyui.is_available():
        print(f"[OK] ComfyUI: 利用可能 ({comfyui_url})")
        
        # キュー状態を確認
        queue_status = comfyui.get_queue_status()
        if "error" not in queue_status:
            print(f"   キュー状態: {queue_status}")
        else:
            print(f"   キュー状態: 取得できませんでした")
    else:
        print(f"[NG] ComfyUI: 利用不可 ({comfyui_url})")
        print("   -> ComfyUIサーバーを起動してください")
        print("   -> 母艦で起動する場合:")
        print("     .\\start_comfyui_local.ps1")
        print("   -> このはサーバー側で起動する場合:")
        print("     cd /root/ComfyUI && python main.py --port 8188")
        
except Exception as e:
    print(f"[ERROR] ComfyUI: エラー - {e}")

print()

# CivitAI統合テスト
print("[2] CivitAI統合テスト")
print("-" * 60)
try:
    from civitai_integration import CivitAIIntegration
    
    civitai_key = os.getenv("CIVITAI_API_KEY")
    if not civitai_key:
        print("[NG] CivitAI: APIキーが設定されていません")
        print("   -> .envファイルにCIVITAI_API_KEYを設定してください")
    else:
        civitai = CivitAIIntegration(api_key=civitai_key)
        
        if civitai.is_available():
            print(f"[OK] CivitAI: 利用可能 (APIキー設定済み)")
            
            # 簡単な検索テスト
            print("   テスト検索を実行中...")
            models = civitai.search_models(query="realistic", limit=3)
            if models:
                print(f"   [OK] 検索成功: {len(models)}件のモデルを取得")
                for i, model in enumerate(models[:3], 1):
                    print(f"      {i}. {model.get('name', 'N/A')} (ID: {model.get('id')})")
            else:
                print("   [WARN] 検索結果が空です（APIキーが無効の可能性）")
        else:
            print("[NG] CivitAI: 利用不可 (APIキーが無効の可能性)")
            
except Exception as e:
    print(f"[ERROR] CivitAI: エラー - {e}")

print()
print("=" * 60)
print("テスト完了")
print("=" * 60)
print()
print("次のステップ:")
print("1. ComfyUIが利用不可の場合:")
print("   → このはサーバー側でComfyUIを起動")
print("   → またはローカルでComfyUIを起動")
print()
print("2. 統合APIサーバーでの動作確認:")
print("   → python unified_api_server.py を起動")
print("   → POST http://127.0.0.1:9510/api/comfyui/generate")
print("   → GET http://127.0.0.1:9510/api/civitai/search?query=realistic")
print()

