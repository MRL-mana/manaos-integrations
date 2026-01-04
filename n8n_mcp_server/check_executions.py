"""
n8nワークフローの実行履歴を確認するスクリプト
"""
import requests
import os
import sys
import json
from datetime import datetime, timedelta

# n8nの設定
N8N_BASE_URL = os.getenv("N8N_BASE_URL", "http://localhost:5679")
N8N_API_KEY = os.getenv("N8N_API_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxZTMzZjMzOS1jNjRhLTQ3ZTUtYjI2OC0wMDhiYWZlNmVkYjAiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY2OTI2OTI5fQ.MGa7c6LW1dZbGU1Aa1YpYT16WAghiaZBbWx1bvCS3eE")

def check_executions(workflow_id):
    """ワークフローの実行履歴を確認"""
    try:
        headers = {"X-N8N-API-KEY": N8N_API_KEY} if N8N_API_KEY else {}
        
        # 実行履歴を取得（最新10件）
        response = requests.get(
            f"{N8N_BASE_URL}/api/v1/executions",
            headers=headers,
            params={
                "workflowId": workflow_id,
                "limit": 10
            },
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"[NG] 実行履歴取得エラー: {response.status_code}")
            print(f"レスポンス: {response.text[:500]}")
            return False
        
        executions = response.json()
        
        if isinstance(executions, dict) and "data" in executions:
            executions = executions["data"]
        
        print("=" * 60)
        print("実行履歴")
        print("=" * 60)
        print(f"ワークフローID: {workflow_id}")
        print(f"実行数: {len(executions)}")
        print()
        
        if not executions:
            print("実行履歴がありません")
            return True
        
        for i, exec in enumerate(executions[:5], 1):
            status = exec.get("finished", False)
            status_text = "完了" if status else "実行中"
            mode = exec.get("mode", "unknown")
            started_at = exec.get("startedAt", "")
            
            print(f"{i}. {status_text} ({mode})")
            print(f"   開始時刻: {started_at}")
            if status:
                finished_at = exec.get("stoppedAt", "")
                print(f"   終了時刻: {finished_at}")
            print()
        
        return True
        
    except requests.exceptions.Timeout:
        print(f"[NG] タイムアウトしました")
        return False
    except Exception as e:
        print(f"[NG] エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    workflow_id = sys.argv[1] if len(sys.argv) > 1 else "2ViGYzDtLBF6H4zn"
    check_executions(workflow_id)













