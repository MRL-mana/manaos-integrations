"""
n8nワークフローを有効化して実行するスクリプト
"""
import requests
import os
import sys
import json
from datetime import datetime

# n8nの設定
N8N_BASE_URL = os.getenv("N8N_BASE_URL", "http://127.0.0.1:5679")
N8N_API_KEY = os.getenv("N8N_API_KEY")


def _require_n8n_api_key() -> str:
    api_key = (N8N_API_KEY or "").strip()
    if api_key:
        return api_key
    print("[NG] N8N_API_KEY が未設定です")
    print("     例 (PowerShell):")
    print("       $env:N8N_API_KEY = \"your_n8n_api_key_here\"")
    print("     例 (Windows 永続):")
    print(
        "       [Environment]::SetEnvironmentVariable("
        "'N8N_API_KEY','your_n8n_api_key_here','User')"
    )
    sys.exit(2)


def activate_workflow(workflow_id):
    """ワークフローを有効化"""
    try:
        api_key = _require_n8n_api_key()
        headers = {"X-N8N-API-KEY": api_key, "Content-Type": "application/json"}

        # ワークフロー詳細を取得
        response = requests.get(
            f"{N8N_BASE_URL}/api/v1/workflows/{workflow_id}",
            headers=headers,
            timeout=30
        )

        if response.status_code != 200:
            print(f"[NG] ワークフロー取得エラー: {response.status_code}")
            return False

        workflow = response.json()

        # 既に有効化されているか確認
        if workflow.get("active"):
            print("[OK] ワークフローは既に有効化されています")
            return True

        # ワークフローを有効化
        workflow["active"] = True
        response = requests.put(
            f"{N8N_BASE_URL}/api/v1/workflows/{workflow_id}",
            headers=headers,
            json=workflow,
            timeout=30
        )

        if response.status_code in [200, 201]:
            print("[OK] ワークフローを有効化しました")
            return True
        print(f"[NG] ワークフロー有効化エラー: {response.status_code}")
        print(f"レスポンス: {response.text[:500]}")
        return False

    except Exception as e:
        print(f"[NG] エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        return False


def get_webhook_url(workflow_id):
    """ワークフローのWebhook URLを取得"""
    try:
        api_key = _require_n8n_api_key()
        headers = {"X-N8N-API-KEY": api_key}

        response = requests.get(
            f"{N8N_BASE_URL}/api/v1/workflows/{workflow_id}",
            headers=headers,
            timeout=30
        )

        if response.status_code != 200:
            return None

        workflow = response.json()
        nodes = workflow.get("nodes", [])

        webhook_nodes = [
            n for n in nodes
            if n.get("type") == "n8n-nodes-base.webhook"
        ]

        if not webhook_nodes:
            return None

        params = webhook_nodes[0].get("parameters", {})
        path = params.get("path", "")
        if path:
            return f"{N8N_BASE_URL}/webhook/{path}"
        return f"{N8N_BASE_URL}/webhook/{workflow_id}"

    except Exception:
        return None


def execute_workflow(workflow_id, payload=None):
    """ワークフローを実行（Webhook経由）"""
    try:
        webhook_url = get_webhook_url(workflow_id)
        if not webhook_url:
            print("[NG] Webhook URLを取得できませんでした")
            return False

        print(f"Webhook URL: {webhook_url}")

        if payload is None:
            payload = {
                "prompt_id": "test-execution",
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

        print("送信ペイロード:")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        print()

        response = requests.post(
            webhook_url,
            json=payload,
            timeout=30
        )

        print(f"ステータスコード: {response.status_code}")

        if response.status_code in [200, 201]:
            print("[OK] ワークフローが正常に実行されました")
            try:
                result = response.json()
                print("レスポンス:")
                print(json.dumps(result, indent=2, ensure_ascii=False))
            except Exception:
                print(f"レスポンス: {response.text[:500]}")
            return True
        print(f"[NG] ワークフロー実行エラー: {response.status_code}")
        print(f"レスポンス: {response.text[:500]}")
        return False

    except Exception as e:
        print(f"[NG] エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    workflow_id = sys.argv[1] if len(sys.argv) > 1 else "2ViGYzDtLBF6H4zn"

    print("=" * 60)
    print("ワークフロー有効化と実行")
    print("=" * 60)
    print(f"ワークフローID: {workflow_id}")
    print()
    
    # ワークフローを有効化
    if not activate_workflow(workflow_id):
        print("[NG] ワークフローの有効化に失敗しました")
        sys.exit(1)

    print()

    # 少し待ってから実行
    import time

    time.sleep(2)

    # ワークフローを実行
    payload = None
    if len(sys.argv) > 2:
        try:
            payload = json.loads(sys.argv[2])
        except Exception:
            pass

    success = execute_workflow(workflow_id, payload)
    sys.exit(0 if success else 1)

