"""
Google Calendar, Tasks, Sheets, Keep 統合モジュール
マナOS向けのGoogle生産性ツール統合
"""

import os
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from enum import Enum

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False

from base_integration import BaseIntegration


class GoogleProductivityIntegration(BaseIntegration):
    """Google Calendar・Tasks・Sheets・Keep統合クラス"""

    CORE_SCOPES = [
        'https://www.googleapis.com/auth/calendar',
        'https://www.googleapis.com/auth/tasks',
        'https://www.googleapis.com/auth/spreadsheets',
    ]

    KEEP_SCOPE = 'https://www.googleapis.com/auth/keep'
    
    def __init__(
        self,
        credentials_path: str = "credentials.json",
        token_path: str = "token.json",
        enable_keep: Optional[bool] = None,
    ):
        """
        初期化
        
        Args:
            credentials_path: 認証情報ファイルのパス
            token_path: トークンファイルのパス
        """
        super().__init__("GoogleProductivity")
        module_dir = Path(__file__).parent
        credentials_candidate = Path(credentials_path)
        token_candidate = Path(token_path)
        
        self.credentials_path = (
            credentials_candidate
            if credentials_candidate.is_absolute()
            else module_dir / credentials_candidate
        )
        self.token_path = (
            token_candidate
            if token_candidate.is_absolute()
            else module_dir / token_candidate
        )
        
        self.creds = None
        self.calendar_service = None
        self.tasks_service = None
        self.sheets_service = None
        self.keep_service = None
        env_keep = os.getenv("MANAOS_ENABLE_GOOGLE_KEEP", "false").lower() in ("1", "true", "yes", "on")
        self.enable_keep = env_keep if enable_keep is None else enable_keep
        self.scopes = list(self.CORE_SCOPES)
        if self.enable_keep:
            self.scopes.append(self.KEEP_SCOPE)
    
    def _initialize_internal(self) -> bool:
        """
        内部初期化
        
        Returns:
            初期化成功かどうか
        """
        if not GOOGLE_API_AVAILABLE:
            self.logger.warning("Google API ライブラリがインストールされていません")
            return False
        
        return self._authenticate()
    
    def _check_availability_internal(self) -> bool:
        """
        内部の利用可能性チェック
        
        Returns:
            利用可能かどうか
        """
        return GOOGLE_API_AVAILABLE and self.creds is not None
    
    def _authenticate(self) -> bool:
        """
        認証を実行
        
        Returns:
            認証成功時True
        """
        if not GOOGLE_API_AVAILABLE:
            return False
        
        try:
            # 既存トークンを読み込み
            if self.token_path.exists():
                self.creds = Credentials.from_authorized_user_file(  # type: ignore[possibly-unbound]
                    str(self.token_path), self.scopes
                )
            
            # トークンが無効または存在しない場合、再認証
            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    self.creds.refresh(Request())  # type: ignore[possibly-unbound]
                elif self.credentials_path.exists():
                    flow = InstalledAppFlow.from_client_secrets_file(  # type: ignore[possibly-unbound]
                        str(self.credentials_path), self.scopes
                    )
                    self.creds = flow.run_local_server(port=0)
                    # トークンを保存
                    with open(str(self.token_path), 'w') as token:
                        token.write(self.creds.to_json())
                else:
                    self.logger.error(f"認証情報ファイルが見つかりません: {self.credentials_path}")
                    return False
            
            # 各サービスを初期化
            self.calendar_service = build('calendar', 'v3', credentials=self.creds)  # type: ignore[possibly-unbound]
            self.tasks_service = build('tasks', 'v1', credentials=self.creds)  # type: ignore[possibly-unbound]
            self.sheets_service = build('sheets', 'v4', credentials=self.creds)  # type: ignore[possibly-unbound]
            if self.enable_keep:
                try:
                    self.keep_service = build('keep', 'v1', credentials=self.creds)  # type: ignore[possibly-unbound]
                except Exception as e:
                    self.logger.warning(f"Keep サービスの初期化に失敗しました: {e}")
            else:
                self.logger.info("Google Keep は無効化されています（MANAOS_ENABLE_GOOGLE_KEEP=false）")
            
            return True
        
        except Exception as e:
            self.logger.error(f"認証エラー: {e}")
            return False
    
    # ===== Calendar 操作 =====
    
    def list_calendars(self) -> List[Dict[str, Any]]:
        """
        カレンダーのリストを取得
        
        Returns:
            カレンダーのリスト
        """
        if not self.calendar_service:
            return []
        
        try:
            result = self.calendar_service.calendarList().list().execute()
            return result.get('items', [])
        except Exception as e:
            self.logger.error(f"カレンダーリスト取得エラー: {e}")
            return []
    
    def list_events(self, calendar_id: str = 'primary', max_results: int = 10) -> List[Dict[str, Any]]:
        """
        イベントのリストを取得
        
        Args:
            calendar_id: カレンダーID（デフォルト: primary）
            max_results: 返す最大イベント数
        
        Returns:
            イベントのリスト
        """
        if not self.calendar_service:
            return []
        
        try:
            result = self.calendar_service.events().list(
                calendarId=calendar_id,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime',
                timeMin=datetime.utcnow().isoformat() + 'Z'
            ).execute()
            return result.get('items', [])
        except Exception as e:
            self.logger.error(f"イベントリスト取得エラー: {e}")
            return []
    
    def create_event(self, calendar_id: str, title: str, start_time: datetime, 
                    end_time: datetime, description: str = "") -> Optional[str]:
        """
        イベントを作成
        
        Args:
            calendar_id: カレンダーID
            title: イベントタイトル
            start_time: 開始時刻
            end_time: 終了時刻
            description: 説明
        
        Returns:
            作成されたイベントID
        """
        if not self.calendar_service:
            return None
        
        try:
            event = {
                'summary': title,
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
            
            result = self.calendar_service.events().insert(
                calendarId=calendar_id,
                body=event
            ).execute()
            
            self.logger.info(f"イベントを作成しました: {result['id']}")
            return result['id']
        except Exception as e:
            self.logger.error(f"イベント作成エラー: {e}")
            return None
    
    # ===== Tasks (TODO) 操作 =====
    
    def list_task_lists(self) -> List[Dict[str, Any]]:
        """
        タスク リストのリストを取得
        
        Returns:
            タスク リストのリスト
        """
        if not self.tasks_service:
            return []
        
        try:
            result = self.tasks_service.tasklists().list().execute()
            return result.get('items', [])
        except Exception as e:
            self.logger.error(f"タスク リスト取得エラー: {e}")
            return []
    
    def list_tasks(self, tasklist_id: str = '@default') -> List[Dict[str, Any]]:
        """
        タスクのリストを取得
        
        Args:
            tasklist_id: タスク リストID（デフォルト: @default）
        
        Returns:
            タスクのリスト
        """
        if not self.tasks_service:
            return []
        
        try:
            result = self.tasks_service.tasks().list(
                tasklist=tasklist_id,
                showCompleted=False
            ).execute()
            return result.get('items', [])
        except Exception as e:
            self.logger.error(f"タスクリスト取得エラー: {e}")
            return []
    
    def create_task(self, tasklist_id: str, title: str, 
                   due_date: Optional[datetime] = None, notes: str = "") -> Optional[str]:
        """
        タスクを作成
        
        Args:
            tasklist_id: タスク リストID
            title: タスク タイトル
            due_date: 期日
            notes: メモ
        
        Returns:
            作成されたタスクID
        """
        if not self.tasks_service:
            return None
        
        try:
            task = {
                'title': title,
                'notes': notes,
            }
            
            if due_date:
                task['due'] = due_date.isoformat() + 'Z'
            
            result = self.tasks_service.tasks().insert(
                tasklist=tasklist_id,
                body=task
            ).execute()
            
            self.logger.info(f"タスクを作成しました: {result['id']}")
            return result['id']
        except Exception as e:
            self.logger.error(f"タスク作成エラー: {e}")
            return None
    
    def mark_task_complete(self, tasklist_id: str, task_id: str) -> bool:
        """
        タスクを完了にマーク
        
        Args:
            tasklist_id: タスク リストID
            task_id: タスクID
        
        Returns:
            成功したかどうか
        """
        if not self.tasks_service:
            return False
        
        try:
            task = self.tasks_service.tasks().get(
                tasklist=tasklist_id,
                task=task_id
            ).execute()
            
            task['status'] = 'completed'
            self.tasks_service.tasks().update(
                tasklist=tasklist_id,
                task=task_id,
                body=task
            ).execute()
            
            self.logger.info(f"タスクを完了にマークしました: {task_id}")
            return True
        except Exception as e:
            self.logger.error(f"タスク更新エラー: {e}")
            return False
    
    # ===== Sheets 操作 =====
    
    def read_sheet(self, spreadsheet_id: str, range_name: str) -> Optional[List[List[Any]]]:
        """
        Sheets から値を読み込み
        
        Args:
            spreadsheet_id: スプレッドシート ID
            range_name: 範囲（例: 'Sheet1!A1:Z100'）
        
        Returns:
            値のリスト
        """
        if not self.sheets_service:
            return None
        
        try:
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()
            
            return result.get('values', [])
        except Exception as e:
            self.logger.error(f"Sheets 読み込みエラー: {e}")
            return None
    
    def write_sheet(self, spreadsheet_id: str, range_name: str, 
                   values: List[List[Any]]) -> bool:
        """
        Sheets に値を書き込み
        
        Args:
            spreadsheet_id: スプレッドシート ID
            range_name: 範囲（例: 'Sheet1!A1:Z100'）
            values: 書き込む値
        
        Returns:
            成功したかどうか
        """
        if not self.sheets_service:
            return False
        
        try:
            body = {'values': values}
            self.sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            
            self.logger.info(f"Sheets に書き込みました: {range_name}")
            return True
        except Exception as e:
            self.logger.error(f"Sheets 書き込みエラー: {e}")
            return False
    
    # ===== Keep (Keep Notes) 操作 =====
    
    def list_notes(self) -> List[Dict[str, Any]]:
        """
        Keep のメモをリスト
        
        Returns:
            メモのリスト
        """
        if not self.keep_service:
            return []
        
        try:
            result = self.keep_service.notes().list().execute()
            return result.get('notes', [])
        except Exception as e:
            self.logger.error(f"Keep メモリスト取得エラー: {e}")
            return []
    
    def get_note(self, note_id: str) -> Optional[Dict[str, Any]]:
        """
        Keep のメモを取得
        
        Args:
            note_id: メモID
        
        Returns:
            メモの内容
        """
        if not self.keep_service:
            return None
        
        try:
            result = self.keep_service.notes().get(name=note_id).execute()
            return result
        except Exception as e:
            self.logger.error(f"Keep メモ取得エラー: {e}")
            return None
    
    # ===== ボーナス操作 =====
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Google生産性ツール全体のサマリーを取得
        
        Returns:
            サマリー情報
        """
        summary = {
            'timestamp': datetime.now().isoformat(),
            'calendars': len(self.list_calendars()),
            'upcoming_events': len(self.list_events()),
            'task_lists': len(self.list_task_lists()),
            'pending_tasks': len(self.list_tasks()),
            'notes': len(self.list_notes()),
        }
        
        return summary
