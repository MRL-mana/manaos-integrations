"""
n8n MCPサーバーの接続確認スクリプト
"""
import requests
import os
import sys

# n8nの設定
N8N_BASE_URL = os.getenv("N8N_BASE_URL", "http://localhost:5679")
N8N_API_KEY = os.getenv("N8N_API_KEY")


def _require_n8n_api_key() -> str:
    api_key = (N8N_API_KEY or "").strip()
    if api_key:
        return api_key
    print("[NG] N8N_API_KEY が未設定です")
    print("     例: $env:N8N_API_KEY = \"your_n8n_api_key_here\"")
    sys.exit(2)


def test_connection():
    """n8nへの接続をテスト"""
    print("=" * 50)
    print("n8n MCPサーバー接続確認")
    print("=" * 50)
    print()

    # Base URL確認
    print(f"Base URL: {N8N_BASE_URL}")
    print("API Key: (redacted)" if (N8N_API_KEY or "").strip() else "API Key: Not set")
    print()

    # ワークフロー一覧を取得
    try:
        api_key = _require_n8n_api_key()
        headers = {"X-N8N-API-KEY": api_key}
        response = requests.get(
            f"{N8N_BASE_URL}/api/v1/workflows",
            headers=headers,
            timeout=5
        )

        if response.status_code == 200:
            workflows = response.json().get("data", [])
            print("[OK] n8nへの接続成功")
            print(f"[OK] ワークフロー数: {len(workflows)}")
            print()

            if workflows:
                print("ワークフロー一覧:")
                for wf in workflows[:5]:  # 最初の5つを表示
                    status = "有効" if wf.get("active") else "無効"
                    name = wf.get("name", "Unknown")
                    wf_id = wf.get("id", "Unknown")
                    print(f"  - {name} (ID: {wf_id}) [{status}]")
            else:
                print("ワークフローは登録されていません")
        else:
            print(f"[NG] 接続エラー: {response.status_code}")
            print(f"     レスポンス: {response.text[:200]}")

    except requests.exceptions.ConnectionError:
        print("[NG] n8nに接続できません")
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

