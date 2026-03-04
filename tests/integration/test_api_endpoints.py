"""
統合APIサーバーのエンドポイントテストスクリプト
ComfyUIとCivitAIのAPIエンドポイントをテスト
"""

import requests
import json
import time
import os
from typing import Dict, Any

try:
    from manaos_integrations._paths import UNIFIED_API_PORT
except Exception:  # pragma: no cover
    try:
        from _paths import UNIFIED_API_PORT  # type: ignore
    except Exception:  # pragma: no cover
        UNIFIED_API_PORT = int(os.getenv("UNIFIED_API_PORT", "9510"))

API_BASE = os.getenv("MANAOS_INTEGRATION_API_URL", f"http://127.0.0.1:{UNIFIED_API_PORT}")

def test_health():
    """ヘルスチェック"""
    print("[1] ヘルスチェック")
    print("-" * 60)
    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        if response.status_code == 200:
            print("[OK] サーバーは正常に動作しています")
            print(f"   レスポンス: {response.json()}")
        else:
            print(f"[NG] サーバーエラー: {response.status_code}")
    except Exception as e:
        print(f"[NG] サーバーに接続できません: {e}")
        print("   → 統合APIサーバーを起動してください:")
        print("     python unified_api_server.py")
    print()

def test_integrations_status():
    """統合システム状態確認"""
    print("[2] 統合システム状態")
    print("-" * 60)
    try:
        response = requests.get(f"{API_BASE}/api/integrations/status", timeout=10)
        if response.status_code == 200:
            status = response.json()
            print("[OK] 統合システム状態を取得しました")
            
            # ComfyUI状態
            comfyui_status = status.get("comfyui", {})
            if comfyui_status.get("available"):
                print(f"   [OK] ComfyUI: 利用可能")
            else:
                print(f"   [NG] ComfyUI: 利用不可")
                print(f"      -> ComfyUIサーバーを起動してください")
            
            # CivitAI状態
            civitai_status = status.get("civitai", {})
            if civitai_status.get("available"):
                print(f"   [OK] CivitAI: 利用可能")
            else:
                print(f"   [NG] CivitAI: 利用不可")
                print(f"      -> CIVITAI_API_KEYを設定してください")
        else:
            print(f"[NG] エラー: {response.status_code}")
    except Exception as e:
        print(f"[NG] エラー: {e}")
    print()

def test_civitai_search():
    """CivitAI検索テスト"""
    print("[3] CivitAI検索テスト")
    print("-" * 60)
    try:
        params = {
            "query": "realistic",
            "limit": 3
        }
        response = requests.get(
            f"{API_BASE}/api/civitai/search",
            params=params,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            models = data.get("models", [])
            print(f"[OK] 検索成功: {len(models)}件のモデルを取得")
            for i, model in enumerate(models[:3], 1):
                name = model.get("name", "N/A")
                model_id = model.get("id", "N/A")
                downloads = model.get("downloadCount", 0)
                print(f"   {i}. {name}")
                print(f"      ID: {model_id}, ダウンロード数: {downloads}")
        elif response.status_code == 503:
            print("[NG] CivitAIが利用できません")
            print("   -> CIVITAI_API_KEYを設定してください")
        else:
            print(f"[NG] エラー: {response.status_code}")
            print(f"   レスポンス: {response.text}")
    except Exception as e:
        print(f"[NG] エラー: {e}")
    print()

def test_comfyui_generate():
    """ComfyUI画像生成テスト"""
    print("[4] ComfyUI画像生成テスト")
    print("-" * 60)
    try:
        payload = {
            "prompt": "a beautiful landscape, mountains, sunset, highly detailed",
            "negative_prompt": "blurry, low quality, distorted",
            "width": 512,
            "height": 512,
            "steps": 20,
            "cfg_scale": 7.0,
            "seed": -1
        }
        
        response = requests.post(
            f"{API_BASE}/api/comfyui/generate",
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            prompt_id = data.get("prompt_id")
            print(f"[OK] 画像生成を開始しました")
            print(f"   プロンプトID: {prompt_id}")
            print(f"   -> ComfyUIのUIで生成状況を確認してください")
        elif response.status_code == 503:
            print("[NG] ComfyUIが利用できません")
            print("   -> ComfyUIサーバーを起動してください")
            print("   -> ポート8188で起動しているか確認してください")
        else:
            print(f"[NG] エラー: {response.status_code}")
            print(f"   レスポンス: {response.text}")
    except Exception as e:
        print(f"[NG] エラー: {e}")
    print()

def main():
    print("=" * 60)
    print("ManaOS統合APIサーバー - エンドポイントテスト")
    print("=" * 60)
    print()
    
    # ヘルスチェック
    test_health()
    
    # 統合システム状態
    test_integrations_status()
    
    # CivitAI検索
    test_civitai_search()
    
    # ComfyUI画像生成
    test_comfyui_generate()
    
    print("=" * 60)
    print("テスト完了")
    print("=" * 60)
    print()
    print("次のステップ:")
    print("1. ComfyUIが利用不可の場合:")
    print("   → COMFYUI_SETUP.mdを参照してComfyUIを起動")
    print()
    print("2. CivitAIが利用不可の場合:")
    print("   → .envファイルにCIVITAI_API_KEYを設定")
    print()
    print("3. すべて正常に動作している場合:")
    print("   → 画像生成ワークフローを構築")
    print("   → Google Driveへの自動保存を設定")

