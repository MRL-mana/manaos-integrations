"""
n8n MCPサーバーの接続確認スクリプト
"""
import requests
import os

# n8nの設定
N8N_BASE_URL = os.getenv("N8N_BASE_URL", "http://localhost:5679")
N8N_API_KEY = os.getenv("N8N_API_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxZTMzZjMzOS1jNjRhLTQ3ZTUtYjI2OC0wMDhiYWZlNmVkYjAiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY2OTI2OTI5fQ.MGa7c6LW1dZbGU1Aa1YpYT16WAghiaZBbWx1bvCS3eE")

def test_connection():
    """n8nへの接続をテスト"""
    print("=" * 50)
    print("n8n MCPサーバー接続確認")
    print("=" * 50)
    print()
    
    # Base URL確認
    print(f"Base URL: {N8N_BASE_URL}")
    print(f"API Key: {N8N_API_KEY[:30]}..." if N8N_API_KEY else "API Key: Not set")
    print()
    
    # ワークフロー一覧を取得
    try:
        headers = {"X-N8N-API-KEY": N8N_API_KEY} if N8N_API_KEY else {}
        response = requests.get(
            f"{N8N_BASE_URL}/api/v1/workflows",
            headers=headers,
            timeout=5
        )
        
        if response.status_code == 200:
            workflows = response.json().get("data", [])
            print(f"[OK] n8nへの接続成功")
            print(f"[OK] ワークフロー数: {len(workflows)}")
            print()
            
            if workflows:
                print("ワークフロー一覧:")
                for wf in workflows[:5]:  # 最初の5つを表示
                    status = "有効" if wf.get("active") else "無効"
                    print(f"  - {wf.get('name', 'Unknown')} (ID: {wf.get('id', 'Unknown')}) [{status}]")
            else:
                print("ワークフローは登録されていません")
        else:
            print(f"[NG] 接続エラー: {response.status_code}")
            print(f"     レスポンス: {response.text[:200]}")
            
    except requests.exceptions.ConnectionError:
        print(f"[NG] n8nに接続できません")
        print(f"     {N8N_BASE_URL} が起動しているか確認してください")
    except Exception as e:
        print(f"[NG] エラーが発生しました: {e}")
    
    print()
    print("=" * 50)
    print("MCPツールの確認")
    print("=" * 50)
    print()
    print("Cursorのチャットで以下を試してください:")
    print("  n8nのワークフロー一覧を取得してください")
    print()
    print("MCPツールが正常に動作している場合、")
    print("ワークフロー一覧が表示されます。")
    print()

if __name__ == "__main__":
    test_connection()














