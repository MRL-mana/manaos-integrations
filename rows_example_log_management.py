"""
Rows統合の実用例: ログ管理
システムログをRowsで管理・分析
"""

import requests
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any
import random

try:
    from manaos_integrations._paths import UNIFIED_API_PORT
except Exception:  # pragma: no cover
    try:
        from _paths import UNIFIED_API_PORT  # type: ignore
    except Exception:  # pragma: no cover
        UNIFIED_API_PORT = int(os.getenv("UNIFIED_API_PORT", "9502"))

API_BASE = os.getenv("MANAOS_INTEGRATION_API_URL", f"http://127.0.0.1:{UNIFIED_API_PORT}")


def create_log_spreadsheet():
    """ログ管理スプレッドシートを作成"""
    print("📋 ログ管理スプレッドシートを作成中...")
    
    data = {
        "title": f"システムログ_{datetime.now().strftime('%Y%m%d')}",
        "description": "ManaOSシステムログの管理と分析"
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
        return spreadsheet_id
    else:
        print(f"✗ 作成失敗: {response.status_code}")
        return None


def send_log_data(spreadsheet_id: str, logs: List[Dict[str, Any]]):
    """ログデータを送信"""
    print(f"\n📤 ログデータを送信中... ({len(logs)}件)")
    
    data = {
        "spreadsheet_id": spreadsheet_id,
        "data": logs,
        "sheet_name": "ログ",
        "append": True
    }
    
    response = requests.post(
        f"{API_BASE}/api/rows/data/send",
        json=data,
        timeout=30
    )
    
    if response.status_code == 200:
        print(f"✓ データ送信完了: {len(logs)}件")
        return True
    else:
        print(f"✗ 送信失敗: {response.status_code}")
        return False


def generate_sample_logs(count: int = 50) -> List[Dict[str, Any]]:
    """サンプルログデータを生成"""
    log_levels = ["INFO", "WARNING", "ERROR", "DEBUG"]
    services = ["ComfyUI", "GoogleDrive", "CivitAI", "LangChain", "Obsidian"]
    messages = [
        "サービス起動完了",
        "APIリクエスト成功",
        "認証エラー",
        "データ取得完了",
        "タイムアウトエラー",
        "処理完了",
        "接続失敗",
        "データ同期完了"
    ]
    
    logs = []
    base_time = datetime.now() - timedelta(days=1)
    
    for i in range(count):
        log_time = base_time + timedelta(minutes=i * 30)
        logs.append({
            "日時": log_time.strftime("%Y-%m-%d %H:%M:%S"),
            "レベル": random.choice(log_levels),
            "サービス": random.choice(services),
            "メッセージ": random.choice(messages),
            "レスポンス時間": f"{random.randint(10, 5000)}ms",
            "ステータス": "成功" if random.random() > 0.2 else "失敗"
        })
    
    return logs


def analyze_logs(spreadsheet_id: str):
    """ログをAIで分析"""
    print("\n🤖 AIでログを分析中...")
    
    queries = [
        "エラーログの傾向を分析して",
        "各サービスのレスポンス時間の平均を計算して",
        "最も多いエラーメッセージを抽出して",
        "時間帯別のログ発生数をグラフで表示して"
    ]
    
    results = []
    for query in queries:
        data = {
            "spreadsheet_id": spreadsheet_id,
            "query": query
        }
        
        response = requests.post(
            f"{API_BASE}/api/rows/ai/query",
            json=data,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            results.append({
                "query": query,
                "result": result.get("result", {})
            })
            print(f"✓ 分析完了: {query[:30]}...")
        else:
            print(f"✗ 分析失敗: {query[:30]}...")
    
    return results


def create_log_dashboard(spreadsheet_id: str):
    """ログダッシュボードを作成"""
    print("\n📊 ログダッシュボードを作成中...")
    
    dashboard_config = {
        "description": "システムログ分析ダッシュボード",
        "metrics": [
            "エラー率",
            "平均レスポンス時間",
            "サービス別ログ数",
            "時間帯別ログ数"
        ],
        "charts": [
            "エラーログの推移",
            "サービス別ログ分布",
            "レスポンス時間の分布"
        ]
    }
    
    data = {
        "spreadsheet_id": spreadsheet_id,
        "dashboard_config": dashboard_config,
        "sheet_name": "ダッシュボード"
    }
    
    response = requests.post(
        f"{API_BASE}/api/rows/dashboard/create",
        json=data,
        timeout=60
    )
    
    if response.status_code == 200:
        result = response.json()
        print("✓ ダッシュボード作成完了")
        return result
    else:
        print(f"✗ 作成失敗: {response.status_code}")
        return None


def export_logs_to_csv(spreadsheet_id: str):
    """ログをCSVにエクスポート"""
    print("\n💾 ログをCSVにエクスポート中...")
    
    output_path = f"logs_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    data = {
        "spreadsheet_id": spreadsheet_id,
        "sheet_name": "ログ",
        "range": "A1:Z1000",
        "output_path": output_path
    }
    
    response = requests.post(
        f"{API_BASE}/api/rows/export/csv",
        json=data,
        timeout=30
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✓ CSVエクスポート完了: {result.get('result', {}).get('output_path', output_path)}")
        return result
    else:
        print(f"✗ エクスポート失敗: {response.status_code}")
        return None


def main():
    """メイン処理"""
    print("="*60)
    print("Rows統合: ログ管理の実例")
    print("="*60)
    
    # 1. スプレッドシート作成
    spreadsheet_id = create_log_spreadsheet()
    if not spreadsheet_id:
        print("\n[エラー] スプレッドシートの作成に失敗しました")
        return
    
    # 2. サンプルログデータ生成
    logs = generate_sample_logs(50)
    
    # 3. ログデータ送信
    if not send_log_data(spreadsheet_id, logs):
        print("\n[エラー] データ送信に失敗しました")
        return
    
    # 4. AIでログ分析
    analyze_results = analyze_logs(spreadsheet_id)
    
    # 5. ダッシュボード作成
    dashboard_result = create_log_dashboard(spreadsheet_id)
    
    # 6. CSVエクスポート
    export_result = export_logs_to_csv(spreadsheet_id)
    
    print("\n" + "="*60)
    print("処理完了")
    print(f"スプレッドシートID: {spreadsheet_id}")
    print(f"分析結果: {len(analyze_results)}件")
    print("="*60)


if __name__ == "__main__":
    main()












