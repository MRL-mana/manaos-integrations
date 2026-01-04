"""
n8nワークフローを無効化→有効化してWebhookを再登録するスクリプト
"""
import requests
import os
import sys
import time

# n8nの設定
N8N_BASE_URL = os.getenv("N8N_BASE_URL", "http://localhost:5679")
N8N_API_KEY = os.getenv("N8N_API_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxZTMzZjMzOS1jNjRhLTQ3ZTUtYjI2OC0wMDhiYWZlNmVkYjAiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY2OTI2OTI5fQ.MGa7c6LW1dZbGU1Aa1YpYT16WAghiaZBbWx1bvCS3eE")

def reactivate_workflow(workflow_id):
    """ワークフローを無効化→有効化してWebhookを再登録"""
    try:
        headers = {"X-N8N-API-KEY": N8N_API_KEY} if N8N_API_KEY else {}
        
        print("=" * 60)
        print("ワークフロー再アクティベート")
        print("=" * 60)
        print(f"ワークフローID: {workflow_id}")
        print()
        
        # 現在の状態を確認
        response = requests.get(
            f"{N8N_BASE_URL}/api/v1/workflows/{workflow_id}",
            headers=headers,
            timeout=5
        )
        
        if response.status_code != 200:
            print(f"[NG] ワークフロー取得エラー: {response.status_code}")
            print(f"レスポンス: {response.text[:200]}")
            return False
        
        workflow = response.json()
        current_active = workflow.get("active", False)
        print(f"現在の状態: {'有効' if current_active else '無効'}")
        print()
        
        # 無効化
        print("1. ワークフローを無効化します...")
        response = requests.post(
            f"{N8N_BASE_URL}/api/v1/workflows/{workflow_id}/deactivate",
            headers=headers,
            timeout=10
        )
        
        if response.status_code not in [200, 204]:
            print(f"[警告] 無効化エラー: {response.status_code}")
            print(f"レスポンス: {response.text[:200]}")
        else:
            print("[OK] ワークフローを無効化しました")
        
        # 少し待つ
        print("   2秒待機中...")
        time.sleep(2)
        
        # 有効化
        print("2. ワークフローを有効化します...")
        response = requests.post(
            f"{N8N_BASE_URL}/api/v1/workflows/{workflow_id}/activate",
            headers=headers,
            timeout=10
        )
        
        if response.status_code not in [200, 204]:
            print(f"[NG] 有効化エラー: {response.status_code}")
            print(f"レスポンス: {response.text[:200]}")
            return False
        
        print("[OK] ワークフローを有効化しました")
        print()
        
        # 少し待つ（Webhook登録のため）
        print("   3秒待機中（Webhook登録のため）...")
        time.sleep(3)
        
        # 最終状態を確認
        response = requests.get(
            f"{N8N_BASE_URL}/api/v1/workflows/{workflow_id}",
            headers=headers,
            timeout=5
        )
        
        if response.status_code == 200:
            workflow = response.json()
            final_active = workflow.get("active", False)
            print(f"最終状態: {'有効' if final_active else '無効'}")
            
            if final_active:
                print()
                print("[OK] ワークフローが正常に再アクティベートされました")
                print("    Webhookが再登録されました")
                return True
            else:
                print("[NG] ワークフローが有効化されていません")
                return False
        else:
            print(f"[警告] 状態確認エラー: {response.status_code}")
            return False
        
    except requests.exceptions.ConnectionError:
        print(f"[NG] n8nに接続できません")
        print(f"     {N8N_BASE_URL} が起動しているか確認してください")
        return False
    except Exception as e:
        print(f"[NG] エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    workflow_id = sys.argv[1] if len(sys.argv) > 1 else "2ViGYzDtLBF6H4zn"
    success = reactivate_workflow(workflow_id)
    sys.exit(0 if success else 1)
