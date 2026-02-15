"""
n8nのワークフロー一覧を詳細表示するスクリプト
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


def list_workflows():
    """ワークフロー一覧を取得"""
    try:
        api_key = _require_n8n_api_key()
        headers = {"X-N8N-API-KEY": api_key}

        response = requests.get(
            f"{N8N_BASE_URL}/api/v1/workflows",
            headers=headers,
            timeout=30
        )

        if response.status_code != 200:
            print(f"[NG] ワークフロー取得エラー: {response.status_code}")
            print(f"レスポンス: {response.text[:500]}")
            return

        workflows = response.json()
        if isinstance(workflows, dict) and "data" in workflows:
            workflows = workflows["data"]

        print("=" * 60)
        print("ワークフロー一覧")
        print("=" * 60)
        print()

        for i, wf in enumerate(workflows, 1):
            wf_id = wf.get("id", "N/A")
            name = wf.get("name", "N/A")
            active = wf.get("active", False)
            updated_at = wf.get("updatedAt", "N/A")
            created_at = wf.get("createdAt", "N/A")

            status = "[有効]" if active else "[無効]"
            status_color = "緑" if active else "赤"

            print(f"{i}. {name}")
            print(f"   ID: {wf_id}")
            print(f"   ステータス: {status} ({status_color})")
            print(f"   更新日時: {updated_at}")
            print(f"   作成日時: {created_at}")
            print()

        # 特定のIDを探す
        target_id = "2ViGYzDtLBF6H4zn"
        target_wf = next(
            (wf for wf in workflows if wf.get("id") == target_id),
            None,
        )

        if target_wf:
            print("=" * 60)
            print(f"ワークフローID {target_id} の詳細")
            print("=" * 60)
            print(f"名前: {target_wf.get('name')}")
            print(f"ステータス: {'[有効]' if target_wf.get('active') else '[無効]'}")
            print(f"更新日時: {target_wf.get('updatedAt')}")
            print()
        else:
            print(f"[警告] ワークフローID {target_id} が見つかりませんでした")
            print()

    except Exception as e:
        print(f"[NG] エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    list_workflows()
