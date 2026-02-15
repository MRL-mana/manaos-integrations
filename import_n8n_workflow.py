#!/usr/bin/env python3
"""
n8nワークフローインポートスクリプト
Browse AI統合用ワークフローをインポート
"""

import json
import requests
import sys
import os
import io
from pathlib import Path


def import_workflow(
    workflow_path,
    n8n_url="http://127.0.0.1:5678",
    api_key=None,
):
    """
    n8nワークフローをインポート

    Args:
        workflow_path: ワークフローJSONファイルのパス
        n8n_url: n8nのURL（デフォルト: http://127.0.0.1:5678）
        api_key: n8n APIキー（オプション）
    """
    # ワークフローファイルを読み込む
    if not os.path.exists(workflow_path):
        print(f"ERROR: Workflow file not found: {workflow_path}")
        return False

    with open(workflow_path, "r", encoding="utf-8") as f:
        workflow_data = json.load(f)

    print(f"OK: Workflow file loaded: {workflow_path}")
    print(f"   Workflow name: {workflow_data.get('name', 'Unknown')}")
    print(f"   Node count: {len(workflow_data.get('nodes', []))}")

    # n8n APIに送信
    headers = {
        "Content-Type": "application/json"
    }

    if api_key:
        # n8nのAPI認証: JWTトークンの場合はBearer、APIキーの場合はX-N8N-API-KEY
        # JWTトークンの場合（eyJで始まる）
        if api_key.startswith("eyJ"):
            headers["Authorization"] = f"Bearer {api_key}"
        else:
            headers["X-N8N-API-KEY"] = api_key
        print(f"Using API key: {api_key[:20]}...")

    try:
        # ワークフロー作成API
        response = requests.post(
            f"{n8n_url}/rest/workflows",
            json=workflow_data,
            headers=headers,
            timeout=10
        )

        if response.status_code == 200 or response.status_code == 201:
            result = response.json()
            print("OK: Workflow imported successfully!")
            print(f"   Workflow ID: {result.get('id', 'Unknown')}")
            print(f"   Name: {result.get('name', 'Unknown')}")
            return True
        elif response.status_code == 401:
            print("ERROR: Authentication failed (401)")
            print(f"   Response: {response.text}")
            print(f"   Headers used: {list(headers.keys())}")
            print("   Manual import method:")
            print(f"   1. Open browser: {n8n_url}")
            print("   2. Workflows -> Import from File")
            print(f"   3. Select file: {workflow_path}")
            return False
        else:
            print(f"ERROR: Import failed: {response.status_code}")
            print(f"   Response: {response.text}")
            print(f"   Headers: {response.headers}")
            return False

    except requests.exceptions.ConnectionError:
        print(f"ERROR: Cannot connect to n8n: {n8n_url}")
        print("   Please check if n8n is running")
        return False
    except Exception as e:
        print(f"ERROR: An error occurred: {e}")
        return False


def main():
    """メイン関数"""
    # スクリプトのディレクトリを取得
    script_dir = Path(__file__).parent
    workflow_path = script_dir / "n8n_workflows" / "browse_ai_manaos_integration.json"

    # 標準出力のエンコーディングを設定
    if sys.stdout.encoding != "utf-8":
        sys.stdout.reconfigure(encoding='utf-8')

    print("n8n workflow import started")
    print()

    # 環境変数からAPIキーを取得（オプション）
    api_key = os.getenv("N8N_API_KEY")

    # APIキーは機密情報のため、デフォルト値（ハードコード）は使用しない

    # ワークフローをインポート
    success = import_workflow(str(workflow_path), api_key=api_key)

    print()
    if success:
        print("OK: Import completed!")
        print()
        print("Next steps:")
        print("1. Check workflow in n8n: http://127.0.0.1:5678")
        print("2. Activate workflow")
        print("3. Check webhook URL: http://127.0.0.1:5678/webhook/browse-ai-webhook")
    else:
        print("WARNING: Auto import failed")
        print()
        print("Manual import method:")
        print("1. Open browser: http://127.0.0.1:5678")
        print("2. Login if needed")
        print("3. Workflows -> Import from File")
        print(f"4. Select file: {workflow_path}")
        print()
        print("Or via Portal UI:")
        print("1. Open browser: http://127.0.0.1:5000")
        print("2. Open n8n automation section")
        print("3. Click Import Workflow")
        print(f"4. Select file: {workflow_path}")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
