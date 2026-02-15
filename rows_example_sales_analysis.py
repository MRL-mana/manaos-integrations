"""
Rows統合の実用例: 売上データ分析
「この売上データ、傾向分析してグラフ出して」を実現
"""

import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any

API_BASE = "http://127.0.0.1:9510"


def create_sales_spreadsheet():
    """売上管理スプレッドシートを作成"""
    print("📊 売上管理スプレッドシートを作成中...")
    
    data = {
        "title": f"売上分析_{datetime.now().strftime('%Y%m%d')}",
        "description": "月次売上データの分析と可視化"
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


def send_sales_data(spreadsheet_id: str):
    """売上データを送信"""
    print("\n📈 売上データを送信中...")
    
    # サンプルデータ生成（過去30日分）
    sales_data = []
    base_date = datetime.now() - timedelta(days=30)
    
    for i in range(30):
        date = base_date + timedelta(days=i)
        # ランダムな売上データ（実際のデータに置き換え可能）
        sales = 100000 + (i * 2000) + (i % 7) * 5000
        profit = int(sales * 0.3)
        
        sales_data.append({
            "日付": date.strftime("%Y-%m-%d"),
            "売上": sales,
            "利益": profit,
            "利益率": f"{(profit/sales*100):.1f}%"
        })
    
    data = {
        "spreadsheet_id": spreadsheet_id,
        "data": sales_data,
        "sheet_name": "売上データ",
        "append": True
    }
    
    response = requests.post(
        f"{API_BASE}/api/rows/data/send",
        json=data,
        timeout=30
    )
    
    if response.status_code == 200:
        print(f"✓ データ送信完了: {len(sales_data)}件")
        return True
    else:
        print(f"✗ 送信失敗: {response.status_code}")
        return False


def analyze_sales_trend(spreadsheet_id: str):
    """売上傾向をAIで分析"""
    print("\n🤖 AIで売上傾向を分析中...")
    
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
        result = response.json()
        print("✓ 分析完了")
        print(f"\n分析結果:")
        print(f"  {result.get('result', {}).get('summary', 'N/A')}")
        return result
    else:
        print(f"✗ 分析失敗: {response.status_code}")
        return None


def analyze_detailed(spreadsheet_id: str):
    """詳細分析を実行"""
    print("\n📊 詳細分析を実行中...")
    
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
        result = response.json()
        print("✓ 詳細分析完了")
        return result
    else:
        print(f"✗ 分析失敗: {response.status_code}")
        return None


def send_to_slack(spreadsheet_id: str):
    """分析結果をSlackに送信"""
    print("\n💬 Slackに送信中...")
    
    data = {
        "spreadsheet_id": spreadsheet_id,
        "sheet_name": "売上データ",
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
    print("Rows統合: 売上データ分析の実例")
    print("="*60)
    
    # 1. スプレッドシート作成
    spreadsheet_id = create_sales_spreadsheet()
    if not spreadsheet_id:
        print("\n[エラー] スプレッドシートの作成に失敗しました")
        return
    
    # 2. 売上データ送信
    if not send_sales_data(spreadsheet_id):
        print("\n[エラー] データ送信に失敗しました")
        return
    
    # 3. AIで傾向分析
    analyze_result = analyze_sales_trend(spreadsheet_id)
    
    # 4. 詳細分析
    detailed_result = analyze_detailed(spreadsheet_id)
    
    # 5. Slackに送信（オプション）
    # send_to_slack(spreadsheet_id)
    
    print("\n" + "="*60)
    print("処理完了")
    print(f"スプレッドシートID: {spreadsheet_id}")
    print("="*60)


if __name__ == "__main__":
    main()













