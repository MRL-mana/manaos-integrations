"""
n8nワークフローの状態を確認するスクリプト
"""
import requests
import os
import sys
import json

# n8nの設定
N8N_BASE_URL = os.getenv("N8N_BASE_URL", "http://localhost:5679")
N8N_API_KEY = os.getenv("N8N_API_KEY", "")

def check_workflow_status(workflow_id):
    """ワークフローの状態を確認"""
    try:
        headers = {}
        if N8N_API_KEY:
            headers["X-N8N-API-KEY"] = N8N_API_KEY
        
        print("=" * 60)
        print("ワークフロー状態確認")
        print("=" * 60)
        print(f"ワークフローID: {workflow_id}")
        print(f"n8n URL: {N8N_BASE_URL}")
        print()
        
        # ワークフロー詳細を取得
        response = requests.get(
            f"{N8N_BASE_URL}/api/v1/workflows/{workflow_id}",
            headers=headers,
            timeout=5
        )
        
        print(f"ステータスコード: {response.status_code}")
        
        if response.status_code != 200:
            print(f"[NG] ワークフロー取得エラー: {response.status_code}")
            print(f"レスポンス: {response.text[:500]}")
            
            if response.status_code == 401:
                print()
                print("[情報] APIキーが必要です")
                print("n8nのWeb UIで新しいAPIキーを作成してください:")
                print("  1. http://localhost:5679 を開く")
                print("  2. 右上のユーザーアイコン → Settings → API")
                print("  3. Create API Key をクリック")
                print("  4. 生成されたAPIキーをコピー")
                print("  5. 環境変数に設定: $env:N8N_API_KEY = 'your-api-key'")
            
            return False
        
        workflow = response.json()
        
        print("[OK] ワークフローを取得しました")
        print()
        print("ワークフロー情報:")
        print(f"  名前: {workflow.get('name', 'N/A')}")
        print(f"  ID: {workflow.get('id', 'N/A')}")
        print(f"  有効: {'はい' if workflow.get('active', False) else 'いいえ'}")
        print()
        
        # ノード情報
        nodes = workflow.get("nodes", [])
        print(f"ノード数: {len(nodes)}")
        
        # Webhookノードを検索
        webhook_nodes = [
            n for n in nodes 
            if n.get("type") == "n8n-nodes-base.webhook"
        ]
        
        if webhook_nodes:
            print()
            print("Webhookノード:")
            for i, node in enumerate(webhook_nodes, 1):
                params = node.get("parameters", {})
                path = params.get("path", "")
                method = params.get("httpMethod", "POST")
                print(f"  {i}. Path: {path}")
                print(f"     メソッド: {method}")
                print(f"     Webhook URL: {N8N_BASE_URL}/webhook/{path}")
        else:
            print()
            print("[警告] Webhookノードが見つかりません")
        
        # Google Driveノード
        gdrive_nodes = [
            n for n in nodes 
            if n.get("type") == "n8n-nodes-base.googleDrive"
        ]
        if gdrive_nodes:
            print()
            print("Google Driveノード:")
            for i, node in enumerate(gdrive_nodes, 1):
                print(f"  {i}. {node.get('name', 'N/A')}")
                # 認証情報の確認
                credentials = node.get("credentials", {})
                if credentials:
                    print(f"     認証情報: 設定済み")
                else:
                    print(f"     認証情報: 未設定")
        
        # Slackノード
        slack_nodes = [
            n for n in nodes 
            if n.get("type") == "n8n-nodes-base.slack"
        ]
        if slack_nodes:
            print()
            print("Slackノード:")
            for i, node in enumerate(slack_nodes, 1):
                print(f"  {i}. {node.get('name', 'N/A')}")
                # 認証情報の確認
                credentials = node.get("credentials", {})
                if credentials:
                    print(f"     認証情報: 設定済み")
                else:
                    print(f"     認証情報: 未設定")
        
        print()
        return True
        
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
    success = check_workflow_status(workflow_id)
    sys.exit(0 if success else 1)











