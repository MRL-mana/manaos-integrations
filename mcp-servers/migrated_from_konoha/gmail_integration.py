#!/usr/bin/env python3
"""
Gmail統合
タスク完了・重要イベントをメールで通知
"""

import os
import logging
import base64
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

# 設定ファイル
VAULT_DIR = Path("/root/.mana_vault")
GMAIL_CREDENTIALS_FILE = VAULT_DIR / "gmail_credentials.json"
GMAIL_TOKEN_FILE = VAULT_DIR / "gmail_token.json"
GMAIL_CONFIG_FILE = VAULT_DIR / "gmail_config.json"


class GmailIntegration:
    """Gmail統合システム"""
    
    def __init__(self):
        self.available = False
        self.service = None
        self.sender_email = None
        
        # Gmail API初期化
        if GMAIL_TOKEN_FILE.exists():
            try:
                from google.auth.transport.requests import Request
                from google.oauth2.credentials import Credentials
                from googleapiclient.discovery import build
                
                # トークン読み込み
                creds = Credentials.from_authorized_user_file(str(GMAIL_TOKEN_FILE), 
                                                              ['https://www.googleapis.com/auth/gmail.send'])
                
                # トークン更新が必要な場合
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                    # 更新されたトークンを保存
                    with open(GMAIL_TOKEN_FILE, 'w') as token:
                        token.write(creds.to_json())
                
                if creds and creds.valid:
                    self.service = build('gmail', 'v1', credentials=creds)
                    self.available = True
                    
                    # 設定読み込み
                    if GMAIL_CONFIG_FILE.exists():
                        import json
                        with open(GMAIL_CONFIG_FILE, 'r') as f:
                            config = json.load(f)
                            self.sender_email = config.get('sender_email', 'me')
                    
                    logger.info(f"✅ Gmail connected: {self.sender_email or 'me'}")
                else:
                    logger.warning("⚠️  Gmail credentials invalid")
            
            except Exception as e:
                logger.warning(f"⚠️  Gmail initialization failed: {e}")
        else:
            logger.info("ℹ️  Gmail token not found - email disabled")
    
    def send_email(self, to: str, subject: str, body: str, 
                   html: bool = False) -> bool:
        """メール送信"""
        if not self.available:
            logger.debug(f"[Gmail disabled] To: {to}, Subject: {subject}")
            return False
        
        try:
            # メッセージ作成
            if html:
                message = MIMEMultipart('alternative')
                message['To'] = to
                message['From'] = self.sender_email or 'me'
                message['Subject'] = subject
                
                text_part = MIMEText(body, 'plain')
                html_part = MIMEText(body, 'html')
                message.attach(text_part)
                message.attach(html_part)
            else:
                message = MIMEText(body)
                message['To'] = to
                message['From'] = self.sender_email or 'me'
                message['Subject'] = subject
            
            # Base64エンコード
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            # 送信
            self.service.users().messages().send(  # type: ignore[union-attr]
                userId='me',
                body={'raw': raw}
            ).execute()
            
            logger.info(f"✅ Email sent: {to} - {subject}")
            return True
        
        except Exception as e:
            logger.error(f"❌ Email send error: {e}")
            return False
    
    def notify_task_created(self, task: Dict[str, Any], recipient: str) -> bool:
        """タスク作成通知メール"""
        subject = f"[ManaOS] 新しいタスク: {task['title']}"
        
        body = f"""
こんにちは！

新しいタスクが作成されました。

タスク: {task['title']}
ID: {task['id']}
優先度: {task.get('priority', 'N/A')}
担当: {task.get('assigned_to', '未定')}
作成者: {task.get('created_by', 'Unknown')}
作成日時: {task.get('created_at', 'N/A')}

{task.get('description', '')}

---
Trinity統合秘書システム
ManaOS
        """
        
        return self.send_email(recipient, subject, body.strip())
    
    def notify_task_completed(self, task: Dict[str, Any], recipient: str) -> bool:
        """タスク完了通知メール"""
        subject = f"[ManaOS] タスク完了: {task['title']}"
        
        body = f"""
こんにちは！

タスクが完了しました。

タスク: {task['title']}
ID: {task['id']}
担当: {task.get('assigned_to', 'Unknown')}
完了日時: {task.get('completed_at', datetime.now().isoformat())}

お疲れ様でした！ 🎉

---
Trinity統合秘書システム
ManaOS
        """
        
        return self.send_email(recipient, subject, body.strip())
    
    def notify_error(self, agent: str, error_message: str, 
                    recipient: str, context: Dict = {}) -> bool:
        """エラー通知メール"""
        subject = f"[ManaOS Alert] エラー発生: {agent}"
        
        context_str = "\n".join([f"{k}: {v}" for k, v in context.items()])
        
        body = f"""
⚠️ システムエラーが発生しました

エージェント: {agent}
エラー: {error_message}
発生日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

詳細:
{context_str}

確認をお願いします。

---
Trinity統合秘書システム
ManaOS
        """
        
        return self.send_email(recipient, subject, body.strip())
    
    def send_daily_summary(self, summary: Dict[str, Any], recipient: str) -> bool:
        """デイリーサマリーメール"""
        subject = f"[ManaOS] デイリーレポート - {datetime.now().strftime('%Y-%m-%d')}"
        
        body = f"""
こんにちは！

今日のManaOSレポートです。

【タスク統計】
- 作成: {summary.get('tasks_created', 0)}件
- 完了: {summary.get('tasks_completed', 0)}件
- 実行中: {summary.get('tasks_in_progress', 0)}件

【システム状態】
- 稼働時間: {summary.get('uptime', 'N/A')}
- ヘルススコア: {summary.get('health_score', 'N/A')}/100

【主な活動】
{summary.get('activities', '特になし')}

明日もよろしくお願いします！ 😊

---
Trinity統合秘書システム
ManaOS
        """
        
        return self.send_email(recipient, subject, body.strip())
    
    def get_status(self) -> Dict[str, Any]:
        """Gmail統合ステータス"""
        return {
            "available": self.available,
            "sender_email": self.sender_email if self.available else None
        }


# グローバルインスタンス
gmail = GmailIntegration()


# 便利関数
def send_email(to: str, subject: str, body: str, html: bool = False) -> bool:
    return gmail.send_email(to, subject, body, html)

def notify_task_created(task: Dict[str, Any], recipient: str) -> bool:
    return gmail.notify_task_created(task, recipient)

def notify_task_completed(task: Dict[str, Any], recipient: str) -> bool:
    return gmail.notify_task_completed(task, recipient)

def notify_error(agent: str, error_message: str, recipient: str, context: Dict = {}) -> bool:
    return gmail.notify_error(agent, error_message, recipient, context)

def send_daily_summary(summary: Dict[str, Any], recipient: str) -> bool:
    return gmail.send_daily_summary(summary, recipient)

def get_gmail_status() -> Dict[str, Any]:
    return gmail.get_status()

