#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
カレンダー操作処理スクリプト
YAML形式のカレンダー操作設定を読み込み、Google Calendarでイベントを操作
"""

import os
import sys
import json
import yaml
import requests
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List

# Google Calendar API
GOOGLE_CALENDAR_AVAILABLE = False
try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_CALENDAR_AVAILABLE = True
except ImportError:
    pass

# 設定
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
GOOGLE_CALENDAR_SCOPES = ['https://www.googleapis.com/auth/calendar']

project_root = Path(__file__).parent.parent
HISTORY_FILE = project_root / "data" / "skill_calendar_ops_history.json"
ARTIFACTS_DIR = project_root / "artifacts"
ARTIFACTS_DIR.mkdir(exist_ok=True)

# 認証情報のパス
CREDENTIALS_FILE = project_root / "credentials.json"
TOKEN_FILE = project_root / "token.json"


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


def get_calendar_service() -> Any:
    """Google Calendar APIサービスを取得"""
    if not GOOGLE_CALENDAR_AVAILABLE:
        return None
    
    creds = None
    
    # トークンファイルから認証情報を読み込む
    if TOKEN_FILE.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), GOOGLE_CALENDAR_SCOPES)  # type: ignore[possibly-unbound]
        except Exception as e:
            print(f"⚠️  トークンファイルの読み込みエラー: {e}")
    
    # 認証情報がない、または無効な場合は認証フローを実行
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())  # type: ignore[possibly-unbound]
        else:
            if not CREDENTIALS_FILE.exists():
                print(f"❌ credentials.jsonが見つかりません: {CREDENTIALS_FILE}")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(  # type: ignore[possibly-unbound]
                str(CREDENTIALS_FILE), GOOGLE_CALENDAR_SCOPES
            )
            creds = flow.run_local_server(port=0)
        
        # トークンを保存
        with open(TOKEN_FILE, 'w', encoding='utf-8') as token:
            token.write(creds.to_json())
    
    return build('calendar', 'v3', credentials=creds)  # type: ignore[possibly-unbound]


def create_event(data: Dict[str, Any]) -> Dict[str, Any]:
    """イベントを作成"""
    if not GOOGLE_CALENDAR_AVAILABLE:
        return {"success": False, "error": "google-api-python-clientがインストールされていません"}
    
    service = get_calendar_service()
    if not service:
        return {"success": False, "error": "Google Calendar APIサービスを取得できませんでした"}
    
    calendar_id = data.get("calendar_id", "primary")
    title = data.get("title", "")
    start_time = data.get("start_time", "")
    end_time = data.get("end_time", "")
    timezone = data.get("timezone", "Asia/Tokyo")
    attendees = data.get("attendees", [])
    description = data.get("description", "")
    location = data.get("location", "")
    
    if not title or not start_time or not end_time:
        return {"success": False, "error": "title, start_time, end_timeは必須です"}
    
    try:
        event = {
            'summary': title,
            'description': description,
            'location': location,
            'start': {
                'dateTime': start_time,
                'timeZone': timezone,
            },
            'end': {
                'dateTime': end_time,
                'timeZone': timezone,
            },
        }
        
        if attendees:
            event['attendees'] = [{'email': email} for email in attendees]
        
        event = service.events().insert(
            calendarId=calendar_id,
            body=event
        ).execute()
        
        return {
            "success": True,
            "event_id": event.get('id'),
            "html_link": event.get('htmlLink')
        }
    except HttpError as e:  # type: ignore[possibly-unbound]
        return {"success": False, "error": f"Google Calendar APIエラー: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def update_event(data: Dict[str, Any]) -> Dict[str, Any]:
    """イベントを更新"""
    if not GOOGLE_CALENDAR_AVAILABLE:
        return {"success": False, "error": "google-api-python-clientがインストールされていません"}
    
    service = get_calendar_service()
    if not service:
        return {"success": False, "error": "Google Calendar APIサービスを取得できませんでした"}
    
    calendar_id = data.get("calendar_id", "primary")
    event_id = data.get("event_id", "")
    
    if not event_id:
        return {"success": False, "error": "event_idは必須です"}
    
    try:
        # 既存のイベントを取得
        event = service.events().get(
            calendarId=calendar_id,
            eventId=event_id
        ).execute()
        
        # 更新するフィールドを設定
        if "title" in data:
            event['summary'] = data["title"]
        if "start_time" in data:
            event['start'] = {
                'dateTime': data["start_time"],
                'timeZone': data.get("timezone", "Asia/Tokyo"),
            }
        if "end_time" in data:
            event['end'] = {
                'dateTime': data["end_time"],
                'timeZone': data.get("timezone", "Asia/Tokyo"),
            }
        if "attendees" in data:
            event['attendees'] = [{'email': email} for email in data["attendees"]]
        if "description" in data:
            event['description'] = data["description"]
        if "location" in data:
            event['location'] = data["location"]
        
        # イベントを更新
        updated_event = service.events().update(
            calendarId=calendar_id,
            eventId=event_id,
            body=event
        ).execute()
        
        return {
            "success": True,
            "event_id": updated_event.get('id'),
            "html_link": updated_event.get('htmlLink')
        }
    except HttpError as e:  # type: ignore[possibly-unbound]
        return {"success": False, "error": f"Google Calendar APIエラー: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def list_events(data: Dict[str, Any]) -> Dict[str, Any]:
    """イベント一覧を取得"""
    if not GOOGLE_CALENDAR_AVAILABLE:
        return {"success": False, "error": "google-api-python-clientがインストールされていません"}
    
    service = get_calendar_service()
    if not service:
        return {"success": False, "error": "Google Calendar APIサービスを取得できませんでした"}
    
    calendar_id = data.get("calendar_id", "primary")
    start_time = data.get("start_time")
    end_time = data.get("end_time")
    max_results = data.get("max_results", 10)
    
    try:
        # デフォルトの時刻を設定
        if not start_time:
            start_time = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        if not end_time:
            end_time = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat().replace("+00:00", "Z")
        
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=start_time,
            timeMax=end_time,
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        event_list = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            event_list.append({
                "id": event.get('id'),
                "title": event.get('summary', '（タイトルなし）'),
                "start": start,
                "location": event.get('location', ''),
                "html_link": event.get('htmlLink', '')
            })
        
        return {
            "success": True,
            "events": event_list,
            "count": len(event_list)
        }
    except HttpError as e:  # type: ignore[possibly-unbound]
        return {"success": False, "error": f"Google Calendar APIエラー: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def delete_event(data: Dict[str, Any]) -> Dict[str, Any]:
    """イベントを削除"""
    if not GOOGLE_CALENDAR_AVAILABLE:
        return {"success": False, "error": "google-api-python-clientがインストールされていません"}
    
    service = get_calendar_service()
    if not service:
        return {"success": False, "error": "Google Calendar APIサービスを取得できませんでした"}
    
    calendar_id = data.get("calendar_id", "primary")
    event_id = data.get("event_id", "")
    
    if not event_id:
        return {"success": False, "error": "event_idは必須です"}
    
    try:
        service.events().delete(
            calendarId=calendar_id,
            eventId=event_id
        ).execute()
        
        return {
            "success": True,
            "event_id": event_id
        }
    except HttpError as e:  # type: ignore[possibly-unbound]
        return {"success": False, "error": f"Google Calendar APIエラー: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def send_slack_notification(action: str, result: Dict[str, Any]) -> bool:
    """Slack通知を送信"""
    if not SLACK_WEBHOOK_URL:
        print("⚠️  SLACK_WEBHOOK_URLが設定されていません。スキップします。")
        return False
    
    try:
        action_names = {
            "create_event": "イベント作成",
            "update_event": "イベント更新",
            "list_events": "イベント一覧取得",
            "delete_event": "イベント削除"
        }
        action_name = action_names.get(action, action)
        
        message = f"📅 *カレンダー操作: {action_name}*\n\n"
        
        if result.get("success"):
            message += f"✅ 成功\n"
            if "event_id" in result:
                message += f"イベントID: {result['event_id']}\n"
            if "html_link" in result:
                message += f"リンク: {result['html_link']}\n"
            if "count" in result:
                message += f"取得件数: {result['count']}件\n"
        else:
            message += f"❌ 失敗: {result.get('error', '不明なエラー')}\n"
        
        payload = {
            "text": message,
            "username": "ManaOS Calendar Ops",
            "icon_emoji": ":calendar:"
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
    if data.get("kind") != "calendar_ops":
        print("⚠️  kindが'calendar_ops'ではありません。スキップします。")
        return False
    
    idempotency_key = data.get("idempotency_key")
    if not idempotency_key:
        print("⚠️  idempotency_keyが設定されていません。スキップします。")
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
        if action == "create_event":
            result = create_event(data)
        elif action == "update_event":
            result = update_event(data)
        elif action == "list_events":
            result = list_events(data)
        elif action == "delete_event":
            result = delete_event(data)
        else:
            result = {"success": False, "error": f"不明なアクション: {action}"}
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
        print(f"❌ 処理失敗: {yaml_file} - {result.get('error', '')}")
        return False


def main():
    """メイン処理"""
    if len(sys.argv) < 2:
        print(
            "使用方法: python apply_skill_calendar_ops.py "
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
