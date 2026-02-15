"""
n8nワークフローのWebhook URLを取得するスクリプト
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


def get_webhook_url(workflow_id):
    """ワークフローのWebhook URLを取得"""
    try:
        api_key = _require_n8n_api_key()
        headers = {"X-N8N-API-KEY": api_key}

        # ワークフロー詳細を取得
        response = requests.get(
            f"{N8N_BASE_URL}/api/v1/workflows/{workflow_id}",
            headers=headers,
            timeout=5
        )

        if response.status_code != 200:
            print(f"[NG] ワークフロー取得エラー: {response.status_code}")
            print(f"     レスポンス: {response.text[:200]}")
            return None

        workflow = response.json()
        nodes = workflow.get("nodes", [])

        # Webhookノードを検索
        webhook_nodes = [
            n for n in nodes
            if n.get("type") == "n8n-nodes-base.webhook"
        ]

        if not webhook_nodes:
            print("[NG] Webhookノードが見つかりません")
            return None

        print("=" * 60)
        print("ワークフロー情報")
        print("=" * 60)
        print(f"名前: {workflow.get('name')}")
        print(f"ID: {workflow_id}")
        print(f"ステータス: {'有効' if workflow.get('active') else '無効'}")
        print()

        print("=" * 60)
        print("Webhook URL")
        print("=" * 60)

        for node in webhook_nodes:
            params = node.get("parameters", {})
            path = params.get("path", "")
            method = params.get("httpMethod", "POST")

            # Webhook URLを構築
            if path:
                webhook_url = f"{N8N_BASE_URL}/webhook/{path}"
            else:
                webhook_url = f"{N8N_BASE_URL}/webhook/{workflow_id}"

            print(f"ノード名: {node.get('name')}")
            print(f"HTTPメソッド: {method}")
            print(f"パス: {path if path else '(デフォルト)'}")
            print(f"Webhook URL: {webhook_url}")
            print()

        # 最初のWebhook URLを返す
        if webhook_nodes:
            params = webhook_nodes[0].get("parameters", {})
            path = params.get("path", "")
            if path:
                return f"{N8N_BASE_URL}/webhook/{path}"
            return f"{N8N_BASE_URL}/webhook/{workflow_id}"

        return None

    except requests.exceptions.ConnectionError:
        print("[NG] n8nに接続できません")
        print(f"     {N8N_BASE_URL} が起動しているか確認してください")
        return None
    except Exception as e:
        print(f"[NG] エラーが発生しました: {e}")
        return None


if __name__ == "__main__":
    workflow_id = sys.argv[1] if len(sys.argv) > 1 else "2ViGYzDtLBF6H4zn"
    webhook_url = get_webhook_url(workflow_id)

    if webhook_url:
        print("=" * 60)
        print("使用するWebhook URL")
        print("=" * 60)
        print(webhook_url)
        print()

