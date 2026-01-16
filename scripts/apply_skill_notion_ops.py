#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Notion操作処理スクリプト
YAML形式のNotion操作設定を読み込み、Notion APIを使用してデータベース操作を実行
"""

import os
import sys
import json
import yaml
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# 設定
NOTION_API_KEY = os.getenv("NOTION_API_KEY", "")
NOTION_API_URL = "https://api.notion.com/v1"
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")

project_root = Path(__file__).parent.parent
HISTORY_FILE = project_root / "data" / "skill_notion_ops_history.json"
ARTIFACTS_DIR = project_root / "artifacts"
ARTIFACTS_DIR.mkdir(exist_ok=True)


def load_history() -> Dict[str, Any]:
    """処理履歴を読み込む"""
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  履歴ファイルの読み込みエラー: {e}")
    return {"processed": []}


def save_history(history: Dict[str, Any]):
    """処理履歴を保存"""
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def is_already_processed(
    idempotency_key: str, history: Dict[str, Any]
) -> bool:
    """既に処理済みかチェック"""
    processed_keys = [
        item.get("idempotency_key")
        for item in history.get("processed", [])
    ]
    return idempotency_key in processed_keys


def mark_as_processed(
    idempotency_key: str, history: Dict[str, Any], result: Dict[str, Any]
):
    """処理済みとしてマーク"""
    if "processed" not in history:
        history["processed"] = []

    history["processed"].append({
        "idempotency_key": idempotency_key,
        "processed_at": datetime.now().isoformat(),
        "result": result
    })


def get_headers() -> Dict[str, str]:
    """Notion API用のヘッダーを取得"""
    if not NOTION_API_KEY:
        raise ValueError("NOTION_API_KEYが設定されていません")
    
    return {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }


def convert_property_value(value: Any) -> Dict[str, Any]:
    """プロパティ値をNotion API形式に変換"""
    if isinstance(value, str):
        # タイトルまたはテキストとして扱う
        return {
            "title": [{"text": {"content": value}}]
        }
    elif isinstance(value, (int, float)):
        return {"number": value}
    elif isinstance(value, bool):
        return {"checkbox": value}
    elif isinstance(value, str) and value.startswith("http"):
        return {"url": value}
    else:
        # デフォルトはテキストとして扱う
        return {
            "rich_text": [{"text": {"content": str(value)}}]
        }


def convert_properties(properties: Dict[str, Any]) -> Dict[str, Any]:
    """プロパティをNotion API形式に変換"""
    converted = {}
    for key, value in properties.items():
        # タイトルフィールドを特別扱い（最初のフィールドまたは"title"/"Name"）
        if key.lower() in ["title", "name"] or key == list(properties.keys())[0]:
            converted[key] = {
                "title": [{"text": {"content": str(value)}}]
            }
        else:
            converted[key] = convert_property_value(value)
    
    return converted


def create_page(data: Dict[str, Any]) -> Dict[str, Any]:
    """Notionデータベースにページを作成"""
    database_id = data.get("database_id")
    if not database_id:
        raise ValueError("database_idが指定されていません")
    
    properties = data.get("properties", {})
    if not properties:
        raise ValueError("propertiesが指定されていません")
    
    converted_properties = convert_properties(properties)
    
    payload = {
        "parent": {"database_id": database_id},
        "properties": converted_properties
    }
    
    url = f"{NOTION_API_URL}/pages"
    response = requests.post(url, headers=get_headers(), json=payload, timeout=30)
    response.raise_for_status()
    
    result = response.json()
    return {
        "success": True,
        "page_id": result.get("id"),
        "url": result.get("url")
    }


def update_page(data: Dict[str, Any]) -> Dict[str, Any]:
    """Notionページを更新"""
    page_id = data.get("page_id")
    if not page_id:
        raise ValueError("page_idが指定されていません")
    
    properties = data.get("properties", {})
    if not properties:
        raise ValueError("propertiesが指定されていません")
    
    converted_properties = convert_properties(properties)
    
    payload = {
        "properties": converted_properties
    }
    
    url = f"{NOTION_API_URL}/pages/{page_id}"
    response = requests.patch(url, headers=get_headers(), json=payload, timeout=30)
    response.raise_for_status()
    
    result = response.json()
    return {
        "success": True,
        "page_id": result.get("id"),
        "url": result.get("url")
    }


def query_database(data: Dict[str, Any]) -> Dict[str, Any]:
    """Notionデータベースをクエリ"""
    database_id = data.get("database_id")
    if not database_id:
        raise ValueError("database_idが指定されていません")
    
    payload = {}
    if "filter" in data:
        payload["filter"] = data["filter"]
    if "sorts" in data:
        payload["sorts"] = data["sorts"]
    
    url = f"{NOTION_API_URL}/databases/{database_id}/query"
    response = requests.post(url, headers=get_headers(), json=payload, timeout=30)
    response.raise_for_status()
    
    result = response.json()
    return {
        "success": True,
        "results": result.get("results", []),
        "has_more": result.get("has_more", False)
    }


def send_slack_notification(action: str, result: Dict[str, Any]) -> bool:
    """Slack通知を送信"""
    if not SLACK_WEBHOOK_URL:
        print("⚠️  SLACK_WEBHOOK_URLが設定されていません。スキップします。")
        return False
    
    try:
        action_names = {
            "create_page": "ページ作成",
            "update_page": "ページ更新",
            "query_database": "データベースクエリ"
        }
        action_name = action_names.get(action, action)
        
        message = f"📝 *Notion {action_name}*\n\n"
        
        if result.get("success"):
            message += f"✅ 成功\n"
            if "page_id" in result:
                message += f"ページID: `{result['page_id']}`\n"
            if "url" in result:
                message += f"URL: {result['url']}\n"
            if "results" in result:
                message += f"結果: {len(result['results'])}件\n"
        else:
            message += f"❌ 失敗: {result.get('error', '不明なエラー')}\n"
        
        payload = {
            "text": message,
            "username": "ManaOS Notion Ops",
            "icon_emoji": ":memo:"
        }
        
        response = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
        
        if response.status_code == 200:
            print("✅ Slack通知送信完了")
            return True
        else:
            print(f"❌ Slack通知送信失敗: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Slack通知送信エラー: {e}")
        return False


def process_yaml_file(yaml_file: Path) -> bool:
    """YAMLファイルを処理"""
    print(f"\n📁 処理開始: {yaml_file}")
    
    # YAML読み込み
    try:
        with open(yaml_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
    except Exception as e:
        print(f"❌ YAMLファイル読み込みエラー: {e}")
        return False
    
    # バリデーション
    if data.get("kind") != "notion_ops":
        print("⚠️  kindが'notion_ops'ではありません。スキップします。")
        return False
    
    idempotency_key = data.get("idempotency_key")
    if not idempotency_key:
        print("⚠️  idempotency_keyが設定されていません。スキップします。")
        return False
    
    if not NOTION_API_KEY:
        print("❌ NOTION_API_KEYが設定されていません。")
        return False
    
    # 履歴チェック
    history = load_history()
    if is_already_processed(idempotency_key, history):
        print(f"⏭️  既に処理済みです: {idempotency_key}")
        return True
    
    # 処理実行
    action = data.get("action")
    result = {"success": False, "error": "不明なアクション"}
    
    try:
        if action == "create_page":
            result = create_page(data)
            # 作成されたページIDをYAMLに追記
            if result.get("success") and result.get("page_id"):
                data["page_id"] = result["page_id"]
                with open(yaml_file, 'w', encoding='utf-8') as f:
                    yaml.dump(data, f, allow_unicode=True, sort_keys=False)
        elif action == "update_page":
            result = update_page(data)
        elif action == "query_database":
            result = query_database(data)
            # クエリ結果をYAMLに追記
            if result.get("success"):
                data["results"] = result.get("results", [])
                with open(yaml_file, 'w', encoding='utf-8') as f:
                    yaml.dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
        else:
            result = {"success": False, "error": f"不明なアクション: {action}"}
    except requests.exceptions.HTTPError as e:
        error_msg = f"HTTPエラー: {e.response.status_code}"
        try:
            error_detail = e.response.json()
            error_msg += f" - {error_detail}"
        except:
            error_msg += f" - {e.response.text}"
        result = {"success": False, "error": error_msg}
        print(f"❌ Notion APIエラー: {error_msg}")
    except Exception as e:
        result = {"success": False, "error": str(e)}
        print(f"❌ 処理エラー: {e}")
    
    # Slack通知
    if data.get("notify", {}).get("slack", False):
        send_slack_notification(action, result)
    else:
        print("⏭️  Slack通知はスキップされます")
    
    # 履歴に記録
    mark_as_processed(idempotency_key, history, result)
    save_history(history)
    
    if result.get("success"):
        print(f"✅ 処理完了: {yaml_file}")
        return True
    else:
        print(f"❌ 処理失敗: {yaml_file}")
        return False


def main():
    """メイン処理"""
    if len(sys.argv) < 2:
        print(
            "使用方法: python apply_skill_notion_ops.py "
            "<yaml_file> [yaml_file2 ...]"
        )
        sys.exit(1)
    
    yaml_files = [Path(f) for f in sys.argv[1:]]
    
    success_count = 0
    for yaml_file in yaml_files:
        if not yaml_file.exists():
            print(f"❌ ファイルが見つかりません: {yaml_file}")
            continue
        
        if process_yaml_file(yaml_file):
            success_count += 1
    
    print(f"\n🎉 処理完了: {success_count}/{len(yaml_files)} ファイル")
    
    if success_count < len(yaml_files):
        sys.exit(1)


if __name__ == "__main__":
    main()
