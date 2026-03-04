"""
Rows統合の実用例: 収益管理
収益データをRowsで管理・分析・予測
"""

import requests
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any

try:
    from manaos_integrations._paths import UNIFIED_API_PORT
except Exception:  # pragma: no cover
    try:
        from _paths import UNIFIED_API_PORT  # type: ignore
    except Exception:  # pragma: no cover
        UNIFIED_API_PORT = int(os.getenv("UNIFIED_API_PORT", "9502"))

API_BASE = os.getenv("MANAOS_INTEGRATION_API_URL", f"http://127.0.0.1:{UNIFIED_API_PORT}")


def create_revenue_spreadsheet():
    """収益管理スプレッドシートを作成"""
    print("💰 収益管理スプレッドシートを作成中...")
    
    data = {
        "title": f"収益管理_{datetime.now().strftime('%Y%m%d')}",
        "description": "月次・日次収益データの管理と分析"
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


def send_revenue_data(spreadsheet_id: str):
    """収益データを送信"""
    print("\n📈 収益データを送信中...")
    
    # サンプルデータ生成（過去12ヶ月分）
    revenue_data = []
    base_date = datetime.now() - timedelta(days=365)
    
    categories = ["広告収入", "サブスクリプション", "コンサルティング", "商品販売", "その他"]
    
    for i in range(12):
        month_date = base_date + timedelta(days=i * 30)
        month_str = month_date.strftime("%Y-%m")
        
        total_revenue = 0
        for category in categories:
            revenue = 100000 + (i * 10000) + hash(category) % 50000
            cost = int(revenue * 0.6)
            profit = revenue - cost
            
            revenue_data.append({
                "年月": month_str,
                "カテゴリ": category,
                "収益": revenue,
                "コスト": cost,
                "利益": profit,
                "利益率": f"{(profit/revenue*100):.1f}%"
            })
            total_revenue += revenue
    
    data = {
        "spreadsheet_id": spreadsheet_id,
        "data": revenue_data,
        "sheet_name": "収益データ",
        "append": True
    }
    
    response = requests.post(
        f"{API_BASE}/api/rows/data/send",
        json=data,
        timeout=30
    )
    
    if response.status_code == 200:
        print(f"✓ データ送信完了: {len(revenue_data)}件")
        return True
    else:
        print(f"✗ 送信失敗: {response.status_code}")
        return False


def analyze_revenue_trends(spreadsheet_id: str):
    """収益傾向をAIで分析"""
    print("\n🤖 AIで収益傾向を分析中...")
    
    queries = [
        "各カテゴリの収益推移をグラフで表示して",
        "月次収益の成長率を計算して",
        "最も利益率の高いカテゴリを特定して",
        "来月の収益を予測して"
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


def create_revenue_dashboard(spreadsheet_id: str):
    """収益ダッシュボードを作成"""
    print("\n📊 収益ダッシュボードを作成中...")
    
    dashboard_config = {
        "description": "収益分析ダッシュボード",
        "metrics": [
            "総収益",
            "総利益",
            "平均利益率",
            "成長率"
        ],
        "charts": [
            "月次収益推移",
            "カテゴリ別収益分布",
            "利益率の推移",
            "収益予測"
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


def send_to_slack(spreadsheet_id: str):
    """分析結果をSlackに送信"""
    print("\n💬 Slackに送信中...")
    
    data = {
        "spreadsheet_id": spreadsheet_id,
        "sheet_name": "収益データ",
        "channel": "#manaos-notifications"
    }
    
    response = requests.post(
        f"{API_BASE}/api/rows/export/slack",
        json=data,
        timeout=30
    )
    
    if response.status_code == 200:
        print("✓ Slack送信完了")
        return True
    else:
        print(f"✗ 送信失敗: {response.status_code}")
        return False


def main():
    """メイン処理"""
    print("="*60)
    print("Rows統合: 収益管理の実例")
    print("="*60)
    
    # 1. スプレッドシート作成
    spreadsheet_id = create_revenue_spreadsheet()
    if not spreadsheet_id:
        print("\n[エラー] スプレッドシートの作成に失敗しました")
        return
    
    # 2. 収益データ送信
    if not send_revenue_data(spreadsheet_id):
        print("\n[エラー] データ送信に失敗しました")
        return
    
    # 3. AIで収益分析
    analyze_results = analyze_revenue_trends(spreadsheet_id)
    
    # 4. ダッシュボード作成
    dashboard_result = create_revenue_dashboard(spreadsheet_id)
    
    # 5. Slackに送信（オプション）
    # send_to_slack(spreadsheet_id)
    
    print("\n" + "="*60)
    print("処理完了")
    print(f"スプレッドシートID: {spreadsheet_id}")
    print(f"分析結果: {len(analyze_results)}件")
    print("="*60)


if __name__ == "__main__":
    main()












