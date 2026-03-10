#!/usr/bin/env python3
"""
Trinity System用 Notion連携ツール
Cursorの設定に依存せず、直接Notion APIを使用

使い方:
  python3 notion_client.py search "キーワード"
  python3 notion_client.py create-page "タイトル" "親ページID"
  python3 notion_client.py list-pages
"""

import os
import sys
import json
import requests
from datetime import datetime
from typing import Optional, Dict, List

# APIキーを.mana_vaultから読み込み（またはハードコード）
NOTION_TOKEN = "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"
NOTION_VERSION = "2022-06-28"
BASE_URL = "https://api.notion.com/v1"

class NotionClient:
    def __init__(self, token: str = None):  # type: ignore
        self.token = token or NOTION_TOKEN
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json"
        }
    
    def search(self, query: str = "", page_size: int = 10) -> Dict:
        """Notionページ・データベースを検索"""
        url = f"{BASE_URL}/search"
        payload = {
            "query": query,
            "page_size": page_size,
            "sort": {
                "direction": "descending",
                "timestamp": "last_edited_time"
            }
        }
        response = requests.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json()
    
    def get_page(self, page_id: str) -> Dict:
        """ページ情報を取得"""
        url = f"{BASE_URL}/pages/{page_id}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def create_page(self, parent_id: str, title: str, content: str = "") -> Dict:
        """新しいページを作成"""
        url = f"{BASE_URL}/pages"
        payload = {
            "parent": {"page_id": parent_id},
            "properties": {
                "title": {
                    "title": [
                        {
                            "text": {
                                "content": title
                            }
                        }
                    ]
                }
            }
        }
        
        # コンテンツがあれば追加
        if content:
            payload["children"] = [
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": content
                                }
                            }
                        ]
                    }
                }
            ]
        
        response = requests.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json()
    
    def update_page(self, page_id: str, title: Optional[str] = None, archived: Optional[bool] = None) -> Dict:
        """ページを更新"""
        url = f"{BASE_URL}/pages/{page_id}"
        payload = {}
        
        if title:
            payload["properties"] = {
                "title": {
                    "title": [
                        {
                            "text": {
                                "content": title
                            }
                        }
                    ]
                }
            }
        
        if archived is not None:
            payload["archived"] = archived
        
        response = requests.patch(url, headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json()
    
    def append_block(self, page_id: str, content: str, block_type: str = "paragraph") -> Dict:
        """ページにブロックを追加"""
        url = f"{BASE_URL}/blocks/{page_id}/children"
        payload = {
            "children": [
                {
                    "object": "block",
                    "type": block_type,
                    block_type: {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": content
                                }
                            }
                        ]
                    }
                }
            ]
        }
        
        response = requests.patch(url, headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json()
    
    def query_database(self, database_id: str, filter_dict: Optional[Dict] = None) -> Dict:
        """データベースをクエリ"""
        url = f"{BASE_URL}/databases/{database_id}/query"
        payload = {}
        
        if filter_dict:
            payload["filter"] = filter_dict
        
        response = requests.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json()


def format_search_results(results: Dict) -> str:
    """検索結果を読みやすく整形"""
    output = []
    output.append(f"\n検索結果: {len(results.get('results', []))}件")
    output.append("=" * 60)
    
    for item in results.get('results', []):
        obj_type = item.get('object', 'unknown')
        page_id = item.get('id', 'N/A')
        url = item.get('url', 'N/A')
        
        # タイトル取得
        title = "Untitled"
        if 'properties' in item:
            for prop_name, prop_value in item['properties'].items():
                if prop_value.get('type') == 'title' and prop_value.get('title'):
                    title = prop_value['title'][0]['plain_text']
                    break
        
        output.append(f"\n[{obj_type.upper()}] {title}")
        output.append(f"  ID: {page_id}")
        output.append(f"  URL: {url}")
    
    return "\n".join(output)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    client = NotionClient()
    command = sys.argv[1]
    
    try:
        if command == "search":
            query = sys.argv[2] if len(sys.argv) > 2 else ""
            results = client.search(query)
            print(format_search_results(results))
            
        elif command == "list-pages":
            results = client.search()
            print(format_search_results(results))
            
        elif command == "get-page":
            if len(sys.argv) < 3:
                print("使い方: notion_client.py get-page <page_id>")
                sys.exit(1)
            page_id = sys.argv[2]
            page = client.get_page(page_id)
            print(json.dumps(page, indent=2, ensure_ascii=False))
            
        elif command == "create-page":
            if len(sys.argv) < 4:
                print("使い方: notion_client.py create-page <parent_id> <title> [content]")
                sys.exit(1)
            parent_id = sys.argv[2]
            title = sys.argv[3]
            content = sys.argv[4] if len(sys.argv) > 4 else ""
            result = client.create_page(parent_id, title, content)
            print(f"ページ作成成功！")
            print(f"ID: {result['id']}")
            print(f"URL: {result['url']}")
            
        elif command == "append":
            if len(sys.argv) < 4:
                print("使い方: notion_client.py append <page_id> <content>")
                sys.exit(1)
            page_id = sys.argv[2]
            content = sys.argv[3]
            result = client.append_block(page_id, content)
            print("ブロック追加成功！")
            
        else:
            print(f"不明なコマンド: {command}")
            print(__doc__)
            sys.exit(1)
            
    except requests.exceptions.HTTPError as e:
        print(f"APIエラー: {e}")
        print(f"レスポンス: {e.response.text}")
        sys.exit(1)
    except Exception as e:
        print(f"エラー: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

