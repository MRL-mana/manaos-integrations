"""
ManaOS統合システム完全統合テスト
STEP1-3のすべての機能をテスト
"""

import requests
import json
import time
from typing import Dict, Any

API_BASE = "http://localhost:9500"

def test_all_integrations():
    """すべての統合システムをテスト"""
    print("=" * 60)
    print("ManaOS統合システム - 完全統合テスト")
    print("=" * 60)
    print()
    
    # 1. ヘルスチェック
    print("[1] 統合APIサーバーのヘルスチェック")
    print("-" * 60)
    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        if response.status_code == 200:
            print("[OK] サーバーは正常に動作しています")
        else:
            print(f"[NG] サーバーエラー: {response.status_code}")
            return False
    except Exception as e:
        print(f"[NG] サーバーに接続できません: {e}")
        print("   -> 統合APIサーバーを起動してください:")
        print("     python unified_api_server.py")
        return False
    print()
    
    # 2. 統合システム状態確認
    print("[2] 統合システム状態")
    print("-" * 60)
    try:
        response = requests.get(f"{API_BASE}/api/integrations/status", timeout=10)
        if response.status_code == 200:
            status = response.json()
            print("[OK] 統合システム状態を取得しました")
            print()
            
            # 各システムの状態を表示
            systems = {
                "comfyui": "ComfyUI",
                "civitai": "CivitAI",
                "google_drive": "Google Drive",
                "obsidian": "Obsidian",
                "langchain": "LangChain"
            }
            
            for key, name in systems.items():
                sys_status = status.get(key, {})
                if sys_status.get("available"):
                    print(f"   [OK] {name}: 利用可能")
                else:
                    print(f"   [NG] {name}: 利用不可")
        else:
            print(f"[NG] エラー: {response.status_code}")
    except Exception as e:
        print(f"[NG] エラー: {e}")
    print()
    
    # 3. CivitAI検索テスト
    print("[3] CivitAI検索テスト")
    print("-" * 60)
    try:
        params = {"query": "realistic", "limit": 3}
        response = requests.get(f"{API_BASE}/api/civitai/search", params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            models = data.get("models", [])
            print(f"[OK] 検索成功: {len(models)}件のモデルを取得")
            if models:
                print(f"   例: {models[0].get('name', 'N/A')}")
        else:
            print(f"[NG] エラー: {response.status_code}")
    except Exception as e:
        print(f"[NG] エラー: {e}")
    print()
    
    # 4. ComfyUI画像生成テスト
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
            print(f"   -> n8n Webhookに通知が送信されました（設定済みの場合）")
        elif response.status_code == 503:
            print("[NG] ComfyUIが利用できません")
            print("   -> ComfyUIサーバーを起動してください")
        else:
            print(f"[NG] エラー: {response.status_code}")
            print(f"   レスポンス: {response.text}")
    except Exception as e:
        print(f"[NG] エラー: {e}")
    print()
    
    # 5. Google Drive統合テスト（オプション）
    print("[5] Google Drive統合テスト")
    print("-" * 60)
    try:
        # 統合システム状態から確認
        response = requests.get(f"{API_BASE}/api/integrations/status", timeout=10)
        if response.status_code == 200:
            status = response.json()
            google_drive_status = status.get("google_drive", {})
            if google_drive_status.get("available"):
                print("[OK] Google Drive統合が利用可能です")
                print("   -> ファイルアップロード機能が使用可能")
            else:
                print("[NG] Google Drive統合が利用できません")
                print("   -> 認証を完了してください")
    except Exception as e:
        print(f"[NG] エラー: {e}")
    print()
    
    # 6. n8n連携確認
    print("[6] n8n連携確認")
    print("-" * 60)
    n8n_webhook_url = None
    try:
        import os
        n8n_webhook_url = os.getenv("N8N_WEBHOOK_URL")
        if n8n_webhook_url:
            print(f"[OK] n8n Webhook URLが設定されています")
            print(f"   URL: {n8n_webhook_url}")
            print("   -> 画像生成完了時に自動通知されます")
        else:
            print("[INFO] n8n Webhook URLが設定されていません")
            print("   -> 設定する場合:")
            print("     $env:N8N_WEBHOOK_URL = 'http://100.93.120.33:5678/webhook/comfyui-generated'")
    except Exception as e:
        print(f"[NG] エラー: {e}")
    print()
    
    # まとめ
    print("=" * 60)
    print("テスト完了")
    print("=" * 60)
    print()
    print("次のステップ:")
    print("1. n8nワークフローの作成:")
    print("   -> n8n_ワークフローセットアップ.md を参照")
    print()
    print("2. 完全な自動化ループのテスト:")
    print("   -> 画像生成 → Google Drive保存 → Obsidian記録 → Slack通知")
    print()
    print("3. 環境変数の設定（n8n連携用）:")
    print("   -> $env:N8N_WEBHOOK_URL = 'http://100.93.120.33:5678/webhook/comfyui-generated'")
    print()

if __name__ == "__main__":
    test_all_integrations()


















