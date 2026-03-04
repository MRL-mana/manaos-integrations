"""
Rows統合のテストスクリプト
"""

import sys
import os
from pathlib import Path

# モジュールパスを追加
sys.path.insert(0, str(Path(__file__).parent))

from rows_integration import RowsIntegration
import requests
import json
from typing import Dict, Any

try:
    from manaos_integrations._paths import UNIFIED_API_PORT
except Exception:  # pragma: no cover
    try:
        from _paths import UNIFIED_API_PORT  # type: ignore
    except Exception:  # pragma: no cover
        UNIFIED_API_PORT = int(os.getenv("UNIFIED_API_PORT", "9510"))

API_BASE = os.getenv("MANAOS_INTEGRATION_API_URL", f"http://127.0.0.1:{UNIFIED_API_PORT}")


def test_rows_module():
    """Rows統合モジュールのテスト"""
    print("\n" + "="*60)
    print("Rows統合モジュールテスト")
    print("="*60)
    
    rows = RowsIntegration()
    
    if rows.is_available():
        print("✓ Rows統合が利用可能です")
        print(f"  API URL: {rows.base_url}")
    else:
        print("✗ Rows統合が利用できません")
        print("  → ROWS_API_KEY環境変数を設定してください")
        return False
    
    return True


def test_api_health():
    """APIサーバーのヘルスチェック"""
    print("\n[1] APIサーバーヘルスチェック")
    print("-" * 60)
    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        if response.status_code == 200:
            print("[OK] サーバーは正常に動作しています")
            print(f"   レスポンス: {response.json()}")
        else:
            print(f"[NG] サーバーエラー: {response.status_code}")
            return False
    except Exception as e:
        print(f"[NG] サーバーに接続できません: {e}")
        print("   → 統合APIサーバーを起動してください:")
        print("     python unified_api_server.py")
        return False
    return True


def test_rows_status():
    """Rows統合状態確認"""
    print("\n[2] Rows統合状態確認")
    print("-" * 60)
    try:
        response = requests.get(f"{API_BASE}/api/integrations/status", timeout=10)
        if response.status_code == 200:
            status = response.json()
            rows_status = status.get("integrations", {}).get("rows", {})
            
            if rows_status.get("available"):
                print("[OK] Rows統合: 利用可能")
            else:
                print("[NG] Rows統合: 利用不可")
                print("   → ROWS_API_KEYを設定してください")
                return False
        else:
            print(f"[NG] エラー: {response.status_code}")
            return False
    except Exception as e:
        print(f"[NG] エラー: {e}")
        return False
    return True


def test_create_spreadsheet():
    """スプレッドシート作成テスト"""
    print("\n[3] スプレッドシート作成テスト")
    print("-" * 60)
    try:
        data = {
            "title": f"テストスプレッドシート_{int(__import__('time').time())}",
            "description": "ManaOS統合テスト用"
        }
        response = requests.post(
            f"{API_BASE}/api/rows/spreadsheets",
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            spreadsheet = result.get("spreadsheet", {})
            spreadsheet_id = spreadsheet.get("id")
            print(f"[OK] スプレッドシート作成成功")
            print(f"   ID: {spreadsheet_id}")
            print(f"   タイトル: {spreadsheet.get('title')}")
            return spreadsheet_id
        else:
            print(f"[NG] 作成失敗: {response.status_code}")
            print(f"   レスポンス: {response.text}")
            return None
    except Exception as e:
        print(f"[NG] エラー: {e}")
        return None


def test_list_spreadsheets():
    """スプレッドシート一覧取得テスト"""
    print("\n[4] スプレッドシート一覧取得テスト")
    print("-" * 60)
    try:
        response = requests.get(
            f"{API_BASE}/api/rows/spreadsheets?limit=10",
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            spreadsheets = result.get("spreadsheets", [])
            print(f"[OK] 一覧取得成功: {len(spreadsheets)}件")
            for i, sheet in enumerate(spreadsheets[:3], 1):
                print(f"   {i}. {sheet.get('title', 'N/A')} (ID: {sheet.get('id', 'N/A')})")
            return True
        else:
            print(f"[NG] 取得失敗: {response.status_code}")
            return False
    except Exception as e:
        print(f"[NG] エラー: {e}")
        return False


def _test_send_data(spreadsheet_id: str):
    """データ送信テスト"""
    print("\n[5] データ送信テスト")
    print("-" * 60)
    if not spreadsheet_id:
        print("[SKIP] スプレッドシートIDがありません")
        return False
    
    try:
        data = {
            "spreadsheet_id": spreadsheet_id,
            "data": [
                {"日付": "2025-01-28", "売上": 100000, "利益": 30000},
                {"日付": "2025-01-29", "売上": 120000, "利益": 36000},
                {"日付": "2025-01-30", "売上": 150000, "利益": 45000}
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
            print("[OK] データ送信成功")
            result = response.json()
            print(f"   結果: {result.get('status')}")
            return True
        else:
            print(f"[NG] 送信失敗: {response.status_code}")
            print(f"   レスポンス: {response.text}")
            return False
    except Exception as e:
        print(f"[NG] エラー: {e}")
        return False


def _test_ai_query(spreadsheet_id: str):
    """AI自然言語クエリテスト"""
    print("\n[6] AI自然言語クエリテスト")
    print("-" * 60)
    if not spreadsheet_id:
        print("[SKIP] スプレッドシートIDがありません")
        return False
    
    try:
        data = {
            "spreadsheet_id": spreadsheet_id,
            "query": "この売上データ、傾向分析してグラフ出して"
        }
        response = requests.post(
            f"{API_BASE}/api/rows/ai/query",
            json=data,
            timeout=60
        )
        
        if response.status_code == 200:
            print("[OK] AIクエリ実行成功")
            result = response.json()
            print(f"   結果: {result.get('result', {}).get('summary', 'N/A')[:100]}")
            return True
        else:
            print(f"[NG] クエリ失敗: {response.status_code}")
            print(f"   レスポンス: {response.text}")
            return False
    except Exception as e:
        print(f"[NG] エラー: {e}")
        return False


def _test_ai_analyze(spreadsheet_id: str):
    """AIデータ分析テスト"""
    print("\n[7] AIデータ分析テスト")
    print("-" * 60)
    if not spreadsheet_id:
        print("[SKIP] スプレッドシートIDがありません")
        return False
    
    try:
        data = {
            "spreadsheet_id": spreadsheet_id,
            "analysis_type": "trend",
            "target_range": "A1:Z100"
        }
        response = requests.post(
            f"{API_BASE}/api/rows/ai/analyze",
            json=data,
            timeout=60
        )
        
        if response.status_code == 200:
            print("[OK] AI分析実行成功")
            result = response.json()
            print(f"   結果: {result.get('status')}")
            return True
        else:
            print(f"[NG] 分析失敗: {response.status_code}")
            print(f"   レスポンス: {response.text}")
            return False
    except Exception as e:
        print(f"[NG] エラー: {e}")
        return False


def test_webhook():
    """Webhook受信テスト"""
    print("\n[8] Webhook受信テスト")
    print("-" * 60)
    try:
        data = {
            "event_type": "cell_updated",
            "spreadsheet_id": "test_spreadsheet_id",
            "payload": {
                "cell": "A1",
                "value": "test_value"
            }
        }
        response = requests.post(
            f"{API_BASE}/api/rows/webhook",
            json=data,
            timeout=10
        )
        
        if response.status_code == 200:
            print("[OK] Webhook受信成功")
            result = response.json()
            print(f"   イベントタイプ: {result.get('event_type')}")
            return True
        else:
            print(f"[NG] Webhook受信失敗: {response.status_code}")
            return False
    except Exception as e:
        print(f"[NG] エラー: {e}")
        return False


def main():
    """メインテスト実行"""
    print("="*60)
    print("Rows統合テストスイート")
    print("="*60)
    
    # モジュールテスト
    if not test_rows_module():
        print("\n[警告] Rows統合モジュールが利用できません")
        print("  環境変数ROWS_API_KEYを設定してください")
        return
    
    # APIサーバーテスト
    if not test_api_health():
        return
    
    # 統合状態確認
    if not test_rows_status():
        return
    
    # スプレッドシート操作テスト
    spreadsheet_id = test_create_spreadsheet()
    test_list_spreadsheets()
    
    # データ操作テスト
    if spreadsheet_id:
        _test_send_data(spreadsheet_id)
        _test_ai_query(spreadsheet_id)
        _test_ai_analyze(spreadsheet_id)
    
    # Webhookテスト
    test_webhook()
    
    print("\n" + "="*60)
    print("テスト完了")
    print("="*60)
















