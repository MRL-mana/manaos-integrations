#!/usr/bin/env python3
"""バッテリーデータをNotionに自動同期"""
import requests
import os
import time

PHASE3_URL = os.environ.get('PHASE3_URL', 'http://localhost:5003')
NOTION_API_KEY = os.environ.get('NOTION_API_KEY', '')
NOTION_BATTERY_DB_ID = os.environ.get('NOTION_BATTERY_DATABASE_ID', '')

def save_to_notion(battery_data):
    if not NOTION_API_KEY or not NOTION_BATTERY_DB_ID:
        return False
    
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    from datetime import datetime
    payload = {
        "parent": {"database_id": NOTION_BATTERY_DB_ID},
        "properties": {
            "Date": {"date": {"start": datetime.now().isoformat()}},
            "Battery Level": {"number": battery_data['battery_level']},
            "Health": {"number": battery_data['scores']['health']},
            "Fatigue": {"number": battery_data['scores']['fatigue']},
            "Motivation": {"number": battery_data['scores']['motivation']},
            "Mode": {"select": {"name": battery_data['mode']['mode']}}
        }
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False

def sync_loop():
    last_saved = None
    while True:
        try:
            response = requests.get(f'{PHASE3_URL}/battery/status', timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    battery_data = data['data']
                    if last_saved != battery_data['battery_level']:
                        if save_to_notion(battery_data):
                            print(f"✅ Notion保存: バッテリー {battery_data['battery_level']}")
                            last_saved = battery_data['battery_level']
        except Exception as e:
            print(f"❌ エラー: {e}")
        time.sleep(300)

if __name__ == '__main__':
    print("🔄 バッテリー→Notion同期開始")
    sync_loop()
