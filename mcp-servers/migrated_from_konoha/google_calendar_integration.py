#!/usr/bin/env python3
"""
Google Calendar統合
タスクをカレンダーイベントに自動同期
"""

import os
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# 設定ファイル
VAULT_DIR = Path("/root/.mana_vault")
CALENDAR_TOKEN_FILE = VAULT_DIR / "gmail_token.json"  # Gmailと共通
CALENDAR_CONFIG_FILE = VAULT_DIR / "calendar_config.json"


class GoogleCalendarIntegration:
    """Google Calendar統合システム"""
    
    def __init__(self):
        self.available = False
        self.service = None
        self.calendar_id = 'primary'
        
        # Calendar API初期化
        if CALENDAR_TOKEN_FILE.exists():
            try:
                from google.auth.transport.requests import Request
                from google.oauth2.credentials import Credentials
                from googleapiclient.discovery import build
                
                # トークン読み込み（Gmail認証と共通）
                scopes = [
                    'https://www.googleapis.com/auth/gmail.send',
                    'https://www.googleapis.com/auth/calendar'
                ]
                
                creds = Credentials.from_authorized_user_file(str(CALENDAR_TOKEN_FILE), scopes)
                
                # トークン更新が必要な場合
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                    with open(CALENDAR_TOKEN_FILE, 'w') as token:
                        token.write(creds.to_json())
                
                if creds and creds.valid:
                    self.service = build('calendar', 'v3', credentials=creds)
                    self.available = True
                    
                    # 設定読み込み
                    if CALENDAR_CONFIG_FILE.exists():
                        import json
                        with open(CALENDAR_CONFIG_FILE, 'r') as f:
                            config = json.load(f)
                            self.calendar_id = config.get('calendar_id', 'primary')
                    
                    logger.info(f"✅ Google Calendar connected: {self.calendar_id}")
                else:
                    logger.warning("⚠️  Calendar credentials invalid")
            
            except Exception as e:
                logger.warning(f"⚠️  Calendar initialization failed: {e}")
        else:
            logger.info("ℹ️  Calendar token not found - calendar disabled")
    
    def create_event(self, summary: str, description: str = "", 
                    start_time: Optional[datetime] = None,
                    end_time: Optional[datetime] = None,
                    all_day: bool = False) -> Optional[str]:
        """カレンダーイベント作成"""
        if not self.available:
            logger.debug(f"[Calendar disabled] Event: {summary}")
            return None
        
        try:
            # デフォルト時刻設定
            if start_time is None:
                start_time = datetime.now() + timedelta(hours=1)
            if end_time is None:
                end_time = start_time + timedelta(hours=1)
            
            # イベントデータ構築
            if all_day:
                event = {
                    'summary': summary,
                    'description': description,
                    'start': {
                        'date': start_time.strftime('%Y-%m-%d'),
                        'timeZone': 'Asia/Tokyo',
                    },
                    'end': {
                        'date': end_time.strftime('%Y-%m-%d'),
                        'timeZone': 'Asia/Tokyo',
                    },
                }
            else:
                event = {
                    'summary': summary,
                    'description': description,
                    'start': {
                        'dateTime': start_time.isoformat(),
                        'timeZone': 'Asia/Tokyo',
                    },
                    'end': {
                        'dateTime': end_time.isoformat(),
                        'timeZone': 'Asia/Tokyo',
                    },
                }
            
            # イベント作成
            result = self.service.events().insert(
                calendarId=self.calendar_id,
                body=event
            ).execute()
            
            event_id = result.get('id')
            logger.info(f"✅ Calendar event created: {summary} ({event_id})")
            return event_id
        
        except Exception as e:
            logger.error(f"❌ Calendar event creation error: {e}")
            return None
    
    def create_task_event(self, task: Dict[str, Any]) -> Optional[str]:
        """タスクからカレンダーイベントを作成"""
        summary = f"[Task] {task['title']}"
        description = f"""
タスクID: {task['id']}
優先度: {task.get('priority', 'N/A')}
担当: {task.get('assigned_to', '未定')}
作成者: {task.get('created_by', 'Unknown')}

{task.get('description', '')}

---
Trinity統合秘書システム
        """.strip()
        
        # 期限があれば使用
        if task.get('due_date'):
            try:
                due_date = datetime.fromisoformat(task['due_date'])
                start_time = due_date - timedelta(hours=1)
                end_time = due_date
            except:
                start_time = None
                end_time = None
        else:
            start_time = None
            end_time = None
        
        return self.create_event(summary, description, start_time, end_time)
    
    def update_event(self, event_id: str, summary: Optional[str] = None,
                    description: Optional[str] = None,
                    start_time: Optional[datetime] = None,
                    end_time: Optional[datetime] = None) -> bool:
        """イベント更新"""
        if not self.available:
            return False
        
        try:
            # 既存イベント取得
            event = self.service.events().get(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute()
            
            # 更新
            if summary:
                event['summary'] = summary
            if description:
                event['description'] = description
            if start_time:
                event['start']['dateTime'] = start_time.isoformat()
            if end_time:
                event['end']['dateTime'] = end_time.isoformat()
            
            # 保存
            self.service.events().update(
                calendarId=self.calendar_id,
                eventId=event_id,
                body=event
            ).execute()
            
            logger.info(f"✅ Calendar event updated: {event_id}")
            return True
        
        except Exception as e:
            logger.error(f"❌ Calendar event update error: {e}")
            return False
    
    def delete_event(self, event_id: str) -> bool:
        """イベント削除"""
        if not self.available:
            return False
        
        try:
            self.service.events().delete(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute()
            
            logger.info(f"✅ Calendar event deleted: {event_id}")
            return True
        
        except Exception as e:
            logger.error(f"❌ Calendar event deletion error: {e}")
            return False
    
    def get_upcoming_events(self, days: int = 7) -> List[Dict[str, Any]]:
        """今後のイベント取得"""
        if not self.available:
            return []
        
        try:
            now = datetime.utcnow().isoformat() + 'Z'
            max_time = (datetime.utcnow() + timedelta(days=days)).isoformat() + 'Z'
            
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=now,
                timeMax=max_time,
                maxResults=50,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            logger.info(f"✅ Retrieved {len(events)} upcoming events")
            return events
        
        except Exception as e:
            logger.error(f"❌ Calendar events retrieval error: {e}")
            return []
    
    def get_status(self) -> Dict[str, Any]:
        """Calendar統合ステータス"""
        return {
            "available": self.available,
            "calendar_id": self.calendar_id if self.available else None
        }


# グローバルインスタンス
calendar = GoogleCalendarIntegration()


# 便利関数
def create_event(summary: str, description: str = "", 
                start_time: Optional[datetime] = None,
                end_time: Optional[datetime] = None,
                all_day: bool = False) -> Optional[str]:
    return calendar.create_event(summary, description, start_time, end_time, all_day)

def create_task_event(task: Dict[str, Any]) -> Optional[str]:
    return calendar.create_task_event(task)

def update_event(event_id: str, summary: Optional[str] = None,
                description: Optional[str] = None,
                start_time: Optional[datetime] = None,
                end_time: Optional[datetime] = None) -> bool:
    return calendar.update_event(event_id, summary, description, start_time, end_time)

def delete_event(event_id: str) -> bool:
    return calendar.delete_event(event_id)

def get_upcoming_events(days: int = 7) -> List[Dict[str, Any]]:
    return calendar.get_upcoming_events(days)

def get_calendar_status() -> Dict[str, Any]:
    return calendar.get_status()

