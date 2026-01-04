"""
n8nワークフローをインポートするCLIツール
MCPサーバーを使わずに直接インポートできる
"""
import os
import sys
import json
import requests
from pathlib import Path

# n8nの設定
N8N_BASE_URL = os.getenv("N8N_BASE_URL", "http://100.93.120.33:5678")
N8N_API_KEY = os.getenv("N8N_API_KEY", "")

def get_headers():
    """n8n APIリクエスト用のヘッダーを取得"""
    headers = {"Content-Type": "application/json"}
    if N8N_API_KEY:
        headers["X-N8N-API-KEY"] = N8N_API_KEY
    return headers

def import_workflow(workflow_file: str, activate: bool = True):
    """ワークフローをインポート"""
    print("=" * 60)
    print("n8nワークフロー インポート")
    print("=" * 60)
    
    # ワークフローファイルを読み込む
    if not os.path.exists(workflow_file):
        print(f"[NG] ファイルが見つかりません: {workflow_file}")
        return False
    
    print(f"[OK] ワークフローファイルを読み込み中: {workflow_file}")
    with open(workflow_file, "r", encoding="utf-8") as f:
        workflow_data = json.load(f)
    
    # n8nにインポート
    url = f"{N8N_BASE_URL}/api/v1/workflows"
    print(f"[OK] n8n APIに接続中: {url}")
    
    try:
        response = requests.post(
            url,
            json=workflow_data,
            headers=get_headers(),
            timeout=30
        )
        
        if response.status_code in [200, 201]:
            result = response.json()
            workflow_id = result.get("id")
            workflow_name = result.get("name")
            
            print(f"[OK] ワークフローをインポートしました")
            print(f"  - ID: {workflow_id}")
            print(f"  - 名前: {workflow_name}")
            
            # 有効化
            if activate and workflow_id:
                print(f"[OK] ワークフローを有効化中...")
                activate_url = f"{N8N_BASE_URL}/api/v1/workflows/{workflow_id}/activate"
                activate_response = requests.post(
                    activate_url,
                    headers=get_headers(),
                    timeout=30
                )
                
                if activate_response.status_code == 200:
                    print(f"[OK] ワークフローを有効化しました")
                else:
                    print(f"[警告] ワークフローの有効化に失敗しました")
                    print(f"  ステータスコード: {activate_response.status_code}")
                    print(f"  エラー: {activate_response.text}")
            
            print(f"[OK] ワークフローURL: {N8N_BASE_URL}/workflow/{workflow_id}")
            return True
        else:
            print(f"[NG] インポートに失敗しました")
            print(f"  ステータスコード: {response.status_code}")
            print(f"  エラー: {response.text}")
            
            if response.status_code == 401:
                print("\n[ヒント] n8nの認証が必要な可能性があります")
                print("  1. n8nのWeb UIにログイン")
                print("  2. Settings → API → API Keyを作成")
                print("  3. 環境変数 N8N_API_KEY に設定")
            
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"[NG] n8nサーバーに接続できません: {N8N_BASE_URL}")
        print("  - n8nサーバーが起動しているか確認してください")
        return False
    except Exception as e:
        print(f"[NG] エラーが発生しました: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法: python import_workflow_cli.py <workflow_file> [--no-activate]")
        print("例: python import_workflow_cli.py n8n_workflow_template.json")
        sys.exit(1)
    
    workflow_file = sys.argv[1]
    activate = "--no-activate" not in sys.argv
    
    success = import_workflow(workflow_file, activate)
    sys.exit(0 if success else 1)


















