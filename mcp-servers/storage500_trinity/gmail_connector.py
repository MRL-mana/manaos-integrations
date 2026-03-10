#!/usr/bin/env python3
"""
Trinity Living System - Gmail Connector
Gmail APIとの実際の接続
"""

import os
import json
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gmail_connector")

# Google API認証
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    import pickle
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False
    logger.warning("⚠️ Google API libraries not installed")


class GmailConnector:
    """Gmail API接続クラス"""
    
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
    
    def __init__(self, credentials_path="/root/.mana_vault/google_token.json"):
        """
        初期化
        
        Args:
            credentials_path: Google認証情報パス
        """
        self.credentials_path = credentials_path
        self.service = None
        
        if GOOGLE_API_AVAILABLE:
            self._authenticate()
        else:
            logger.warning("⚠️ Gmail Connector initialized in mock mode")
    
    def _authenticate(self):
        """Google認証"""
        try:
            creds = None
            token_path = self.credentials_path
            
            # トークンファイルがあれば読み込み
            if os.path.exists(token_path):
                with open(token_path, 'r') as token:
                    creds_data = json.load(token)
                    creds = Credentials.from_authorized_user_info(creds_data, self.SCOPES)  # type: ignore[possibly-unbound]
            
            # 認証が有効か確認
            if creds and creds.valid:
                self.service = build('gmail', 'v1', credentials=creds)  # type: ignore[possibly-unbound]
                logger.info("✅ Gmail authenticated successfully")
            else:
                logger.warning("⚠️ Gmail authentication required")
                # TODO: 認証フロー実装
                
        except Exception as e:
            logger.error(f"❌ Gmail authentication failed: {e}")
    
    def get_unread_count(self) -> int:
        """
        未読メール数を取得
        
        Returns:
            未読メール数
        """
        if not self.service:
            # Mock
            return 0
        
        try:
            results = self.service.users().messages().list(
                userId='me',
                labelIds=['UNREAD'],
                maxResults=100
            ).execute()
            
            messages = results.get('messages', [])
            count = len(messages)
            
            logger.info(f"📧 Unread emails: {count}")
            return count
            
        except Exception as e:
            logger.error(f"❌ Failed to get unread count: {e}")
            return 0
    
    def get_recent_emails(self, max_results: int = 10) -> List[Dict]:
        """
        最近のメールを取得
        
        Args:
            max_results: 最大取得件数
            
        Returns:
            メールリスト
        """
        if not self.service:
            # Mock
            return []
        
        try:
            results = self.service.users().messages().list(
                userId='me',
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            emails = []
            
            for msg in messages:
                # メッセージ詳細取得
                msg_data = self.service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='metadata',
                    metadataHeaders=['From', 'Subject', 'Date']
                ).execute()
                
                headers = {h['name']: h['value'] for h in msg_data['payload']['headers']}
                
                emails.append({
                    "id": msg['id'],
                    "from": headers.get('From', 'Unknown'),
                    "subject": headers.get('Subject', 'No Subject'),
                    "date": headers.get('Date', ''),
                    "snippet": msg_data.get('snippet', '')
                })
            
            logger.info(f"📧 Retrieved {len(emails)} emails")
            return emails
            
        except Exception as e:
            logger.error(f"❌ Failed to get emails: {e}")
            return []


class NotionConnector:
    """Notion API接続クラス（簡易版）"""
    
    def __init__(self, api_key: Optional[str] = None):
        """初期化"""
        self.api_key = api_key or os.getenv("NOTION_API_KEY")
        self.base_url = "https://api.notion.com/v1"
        
        if self.api_key:
            logger.info("✅ Notion Connector initialized")
        else:
            logger.warning("⚠️ Notion API key not found (mock mode)")
    
    def create_page(self, database_id: str, properties: Dict) -> Dict:
        """
        Notionページを作成
        
        Args:
            database_id: データベースID
            properties: ページプロパティ
            
        Returns:
            作成結果
        """
        if not self.api_key:
            # Mock
            return {"success": True, "id": "mock-page-id"}
        
        try:
            import requests
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Notion-Version": "2022-06-28"
            }
            
            data = {
                "parent": {"database_id": database_id},
                "properties": properties
            }
            
            response = requests.post(
                f"{self.base_url}/pages",
                headers=headers,
                json=data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ Notion page created: {result['id']}")
                return {"success": True, "id": result['id']}
            else:
                logger.error(f"❌ Notion API error: {response.status_code}")
                return {"success": False, "error": response.text}
                
        except Exception as e:
            logger.error(f"❌ Failed to create Notion page: {e}")
            return {"success": False, "error": str(e)}
    
    def get_todo_count(self) -> int:
        """未完了TODO数を取得（モック）"""
        # TODO: 実際のNotion API実装
        return 0


if __name__ == "__main__":
    # テスト
    gmail = GmailConnector()
    unread = gmail.get_unread_count()
    print(f"\n📧 未読メール: {unread}件")
    
    emails = gmail.get_recent_emails(max_results=5)
    if emails:
        print(f"\n📬 最近のメール:")
        for email in emails:
            print(f"  - {email['subject'][:50]}...")
    
    notion = NotionConnector()
    print(f"\n📋 Notion Connector: {'Ready' if notion.api_key else 'Mock mode'}")


