"""
n8nワークフローを有効化するスクリプト（activateエンドポイント使用）
"""
import requests
import os
import sys
import time
import json
from datetime import datetime

# n8nの設定
N8N_BASE_URL = os.getenv("N8N_BASE_URL", "http://localhost:5679")
N8N_API_KEY = os.getenv("N8N_API_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxZTMzZjMzOS1jNjRhLTQ3ZTUtYjI2OC0wMDhiYWZlNmVkYjAiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY2OTI2OTI5fQ.MGa7c6LW1dZbGU1Aa1YpYT16WAghiaZBbWx1bvCS3eE")

def activate_workflow(workflow_id):
    """ワークフローを有効化"""
    try:
        headers = {"X-N8N-API-KEY": N8N_API_KEY} if N8N_API_KEY else {}
        
        # まず無効化
        print("1. ワークフローを無効化中...")
        response = requests.post(
            f"{N8N_BASE_URL}/api/v1/workflows/{workflow_id}/deactivate",
            headers=headers,
            timeout=30
        )
        
        if response.status_code not in [200, 201, 404]:
            print(f"[警告] 無効化エラー: {response.status_code}")
        else:
            print("[OK] 無効化しました")
            time.sleep(2)
        
        # 有効化
        print("2. ワークフローを有効化中...")
        response = requests.post(
            f"{N8N_BASE_URL}/api/v1/workflows/{workflow_id}/activate",
            headers=headers,
            timeout=30
        )
        
        if response.status_code in [200, 201]:
            print("[OK] 有効化しました")
            print("    Webhookが再登録されました")
            return True
        else:
            print(f"[NG] 有効化エラー: {response.status_code}")
            print(f"レスポンス: {response.text[:500]}")
            return False
        
    except Exception as e:
        print(f"[NG] エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    workflow_id = "2ViGYzDtLBF6H4zn"
    
    print("=" * 60)
    print("ワークフロー再有効化")
    print("=" * 60)
    print(f"ワークフローID: {workflow_id}")
    print()
    
    success = activate_workflow(workflow_id)
    
    if success:
        print()
        print("3秒待機してからWebhookをテストします...")
        time.sleep(3)
        
        print("=" * 60)
        print("Webhookテスト")
        print("=" * 60)
        
        payload = {
            "prompt_id": "test-after-reactivate",
            "prompt": "test prompt",
            "negative_prompt": "test negative prompt",
            "width": 512,
            "height": 512,
            "steps": 20,
            "cfg_scale": 7.0,
            "seed": -1,
            "status": "generated",
            "timestamp": datetime.now().isoformat()
        }
        
        webhook_url = "http://localhost:5679/webhook/comfyui-generated"
        
        print(f"Webhook URL: {webhook_url}")
        print("送信ペイロード:")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        print()
        
        try:
            response = requests.post(
                webhook_url,
                json=payload,
                timeout=5
            )
            
            print(f"ステータスコード: {response.status_code}")
            
            if response.status_code in [200, 201]:
                print("[OK] Webhookが正常に実行されました")
                try:
                    result = response.json()
                    print("レスポンス:")
                    print(json.dumps(result, indent=2, ensure_ascii=False))
                except:
                    print(f"レスポンス: {response.text[:500]}")
            else:
                print(f"[NG] Webhookエラー: {response.status_code}")
                print(f"レスポンス: {response.text[:500]}")
        except requests.exceptions.Timeout:
            print("[OK] リクエストを送信しました（タイムアウトは正常です）")
            print("     ワークフローはバックグラウンドで実行中です")
            print("     n8nのWeb UIで実行状況を確認してください")
        except Exception as e:
            print(f"[NG] エラー: {e}")
    
    sys.exit(0 if success else 1)

