"""
n8nワークフローの実行履歴を確認するスクリプト
"""
import requests
import os
import sys

# n8nの設定
N8N_BASE_URL = os.getenv("N8N_BASE_URL", "http://127.0.0.1:5679")
N8N_API_KEY = os.getenv("N8N_API_KEY")


def _require_n8n_api_key() -> str:
    api_key = (N8N_API_KEY or "").strip()
    if api_key:
        return api_key
    print("[NG] N8N_API_KEY が未設定です")
    print("     例: $env:N8N_API_KEY = \"your_n8n_api_key_here\"")
    sys.exit(2)


def check_executions(workflow_id):
    """ワークフローの実行履歴を確認"""
    try:
        api_key = _require_n8n_api_key()
        headers = {"X-N8N-API-KEY": api_key}

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
        print("[NG] タイムアウトしました")
        return False
    except Exception as e:
        print(f"[NG] エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    workflow_id = sys.argv[1] if len(sys.argv) > 1 else "2ViGYzDtLBF6H4zn"
    check_executions(workflow_id)
