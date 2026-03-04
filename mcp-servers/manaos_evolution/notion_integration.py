#!/usr/bin/env python3
"""Notion連携モジュール"""
import requests
import os
from datetime import datetime
from typing import Dict, Optional

class NotionIntegration:
    def __init__(self):
        self.api_key = os.environ.get('NOTION_API_KEY', '')
        self.database_id = os.environ.get('NOTION_TASKS_DATABASE_ID', '')
        self.battery_database_id = os.environ.get('NOTION_BATTERY_DATABASE_ID', '')
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
    
    def create_task(self, task_name: str, category: str = 'task', 
                   priority: str = 'medium', source: str = 'voice') -> Optional[Dict]:
        if not self.api_key or not self.database_id:
            return None
        url = "https://api.notion.com/v1/pages"
        payload = {
            "parent": {"database_id": self.database_id},
            "properties": {
                "Name": {"title": [{"text": {"content": task_name}}]},
                "Category": {"select": {"name": category}},
                "Priority": {"select": {"name": priority}},
                "Status": {"select": {"name": "Todo"}}
            }
        }
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error: {e}")
            return None
    
    def save_battery_record(self, battery_level: float, health: float, 
                           fatigue: float, motivation: float, mode: str) -> Optional[Dict]:
        if not self.api_key or not self.battery_database_id:
            return None
        url = "https://api.notion.com/v1/pages"
        payload = {
            "parent": {"database_id": self.battery_database_id},
            "properties": {
                "Date": {"date": {"start": datetime.now().isoformat()}},
                "Battery Level": {"number": battery_level},
                "Health": {"number": health},
                "Fatigue": {"number": fatigue},
                "Motivation": {"number": motivation},
                "Mode": {"select": {"name": mode}}
            }
        }
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error: {e}")
            return None
