"""
Rows統合クイックスタートスクリプト
すぐに使える実用例
"""

import requests
import json
from datetime import datetime

API_BASE = "http://127.0.0.1:9510"


def quick_test():
    """クイックテスト"""
    print("="*60)
    print("Rows統合クイックスタート")
    print("="*60)
    
    # 1. ヘルスチェック
    print("\n[1] APIサーバーの状態確認...")
    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        if response.status_code == 200:
            print("✓ APIサーバーは正常に動作しています")
        else:
            print("✗ APIサーバーに問題があります")
            return
    except Exception as e:
        print(f"✗ APIサーバーに接続できません: {e}")
        print("  → 統合APIサーバーを起動してください: python unified_api_server.py")
        return
    
    # 2. Rows統合状態確認
    print("\n[2] Rows統合の状態確認...")
    try:
        response = requests.get(f"{API_BASE}/api/integrations/status", timeout=10)
        if response.status_code == 200:
            status = response.json()
            rows_status = status.get("integrations", {}).get("rows", {})
            if rows_status.get("available"):
                print("✓ Rows統合は利用可能です")
            else:
                print("✗ Rows統合が利用できません")
                print("  → ROWS_API_KEY環境変数を設定してください")
                return
        else:
            print("✗ 状態確認に失敗しました")
            return
    except Exception as e:
        print(f"✗ エラー: {e}")
        return
    
    # 3. スプレッドシート作成
    print("\n[3] スプレッドシートを作成...")
    try:
        data = {
            "title": f"クイックスタート_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "description": "Rows統合クイックスタート用"
        }
        response = requests.post(
            f"{API_BASE}/api/rows/spreadsheets",
            json=data,
            timeout=30
        )
        if response.status_code == 200:
            result = response.json()
            spreadsheet_id = result["spreadsheet"]["id"]
            print(f"✓ スプレッドシート作成完了: {spreadsheet_id}")
            
            # 4. サンプルデータを送信
            print("\n[4] サンプルデータを送信...")
            data = {
                "spreadsheet_id": spreadsheet_id,
                "data": [
                    {"項目": "売上", "値": 1000000, "日付": "2025-01-28"},
                    {"項目": "利益", "値": 300000, "日付": "2025-01-28"},
                    {"項目": "コスト", "値": 700000, "日付": "2025-01-28"}
                ],
                "sheet_name": "Sheet1",
                "append": True
            }
            response = requests.post(
                f"{API_BASE}/api/rows/data/send",
                json=data,
                timeout=30
            )
            if response.status_code == 200:
                print("✓ データ送信完了")
                
                # 5. AIで分析
                print("\n[5] AIでデータ分析...")
                data = {
                    "spreadsheet_id": spreadsheet_id,
                    "query": "このデータを要約して"
                }
                response = requests.post(
                    f"{API_BASE}/api/rows/ai/query",
                    json=data,
                    timeout=60
                )
                if response.status_code == 200:
                    print("✓ AI分析完了")
                    result = response.json()
                    print(f"\n分析結果:")
                    print(f"  {result.get('result', {}).get('summary', 'N/A')[:200]}")
                else:
                    print(f"✗ AI分析に失敗: {response.status_code}")
            else:
                print(f"✗ データ送信に失敗: {response.status_code}")
        else:
            print(f"✗ スプレッドシート作成に失敗: {response.status_code}")
    except Exception as e:
        print(f"✗ エラー: {e}")
    
    print("\n" + "="*60)
    print("クイックスタート完了")
    print("="*60)
    print("\n次のステップ:")
    print("  1. test_rows_integration.py で詳細テストを実行")
    print("  2. rows_example_sales_analysis.py で実用例を確認")
    print("  3. ROWS_INTEGRATION.md で詳細な使い方を確認")


if __name__ == "__main__":
    quick_test()

