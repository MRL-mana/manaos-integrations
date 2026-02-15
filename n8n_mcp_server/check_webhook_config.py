"""
n8nワークフローのWebhook設定を確認するスクリプト
"""
import requests
import os
import sys

# n8nの設定
DEFAULT_N8N_BASE_URL = f"http://127.0.0.1:{os.getenv('N8N_PORT', '5678')}"
N8N_BASE_URL = os.getenv("N8N_BASE_URL", DEFAULT_N8N_BASE_URL).rstrip("/")
N8N_API_KEY = os.getenv("N8N_API_KEY")


def _require_n8n_api_key() -> str:
    api_key = (N8N_API_KEY or "").strip()
    if api_key:
        return api_key
    print("[NG] N8N_API_KEY が未設定です")
    print("     例: $env:N8N_API_KEY = \"your_n8n_api_key_here\"")
    sys.exit(2)


def check_webhook_config(workflow_id):
    """ワークフローのWebhook設定を確認"""
    try:
        api_key = _require_n8n_api_key()
        headers = {"X-N8N-API-KEY": api_key}

        response = requests.get(
            f"{N8N_BASE_URL}/api/v1/workflows/{workflow_id}",
            headers=headers,
            timeout=30
        )

        if response.status_code != 200:
            print(f"[NG] ワークフロー取得エラー: {response.status_code}")
            return

        workflow = response.json()

        print("=" * 60)
        print("ワークフロー情報")
        print("=" * 60)
        print(f"名前: {workflow.get('name')}")
        print(f"ID: {workflow_id}")
        print(f"有効: {workflow.get('active')}")
        print()

        nodes = workflow.get("nodes", [])
        webhook_nodes = [
            n for n in nodes
            if n.get("type") == "n8n-nodes-base.webhook"
        ]

        if not webhook_nodes:
            print("[NG] Webhookノードが見つかりません")
            return

        print("=" * 60)
        print("Webhookノード設定")
        print("=" * 60)

        for i, node in enumerate(webhook_nodes, 1):
            print(f"\n{i}. {node.get('name', 'Unnamed')}")
            params = node.get("parameters", {})
            path = params.get("path", "")
            method = params.get("httpMethod", "POST")
            response_mode = params.get("responseMode", "responseNode")

            print(f"   HTTPメソッド: {method}")
            print(f"   パス: {path if path else '(未設定)'}")
            print(f"   レスポンスモード: {response_mode}")

            if path:
                webhook_url = f"{N8N_BASE_URL}/webhook/{path}"
                print(f"   Webhook URL: {webhook_url}")
            else:
                print("   [警告] パスが設定されていません")

        print()
        print("=" * 60)
        print("推奨アクション")
        print("=" * 60)
        print("1. n8nのWeb UIでワークフローを開く")
        print("2. Webhookノードをクリック")
        print("3. 「Path」が正しく設定されているか確認")
        print("4. ワークフローを一度無効化してから再度有効化")
        print()

    except Exception as e:
        print(f"[NG] エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    workflow_id = "2ViGYzDtLBF6H4zn"
    check_webhook_config(workflow_id)
