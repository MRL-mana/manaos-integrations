#!/usr/bin/env python3
"""
Slack通知統合
タスク完了・エラー・重要イベントをSlackに通知
"""

import os
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

# APIトークンの読み込み
VAULT_DIR = Path("/root/.mana_vault")
SLACK_TOKEN_FILE = VAULT_DIR / "slack_bot_token.txt"
SLACK_CHANNEL_FILE = VAULT_DIR / "slack_channel.txt"


class SlackIntegration:
    """Slack通知システム"""
    
    def __init__(self):
        self.available = False
        self.client = None
        self.default_channel = "#manaos"
        
        # Slack Bot Token読み込み
        if SLACK_TOKEN_FILE.exists():
            try:
                with open(SLACK_TOKEN_FILE, 'r') as f:
                    token = f.read().strip()
                
                if token and token.startswith("xoxb-"):
                    from slack_sdk import WebClient
                    from slack_sdk.errors import SlackApiError
                    
                    self.client = WebClient(token=token)
                    self.SlackApiError = SlackApiError
                    
                    # チャンネル設定
                    if SLACK_CHANNEL_FILE.exists():
                        with open(SLACK_CHANNEL_FILE, 'r') as f:
                            self.default_channel = f.read().strip()
                    
                    # 接続テスト
                    try:
                        response = self.client.auth_test()
                        self.available = True
                        logger.info(f"✅ Slack connected: {response['team']} / {response['user']}")
                    except Exception as e:
                        logger.warning(f"⚠️  Slack auth test failed: {e}")
                else:
                    logger.warning("⚠️  Invalid Slack token format")
            
            except Exception as e:
                logger.warning(f"⚠️  Slack initialization failed: {e}")
        else:
            logger.info("ℹ️  Slack token not found - notifications disabled")
    
    def send_message(self, text: str, channel: Optional[str] = None, 
                    blocks: Optional[List[Dict]] = None) -> bool:
        """メッセージ送信"""
        if not self.available:
            logger.debug(f"[Slack disabled] {text}")
            return False
        
        try:
            target_channel = channel or self.default_channel
            
            if blocks:
                response = self.client.chat_postMessage(
                    channel=target_channel,
                    text=text,
                    blocks=blocks
                )
            else:
                response = self.client.chat_postMessage(
                    channel=target_channel,
                    text=text
                )
            
            logger.info(f"✅ Slack message sent: {target_channel}")
            return response["ok"]
        
        except self.SlackApiError as e:
            logger.error(f"❌ Slack API error: {e.response['error']}")
            return False
        except Exception as e:
            logger.error(f"❌ Slack send error: {e}")
            return False
    
    def notify_task_created(self, task: Dict[str, Any]) -> bool:
        """タスク作成通知"""
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*📋 新しいタスクが作成されました*\n\n*{task['title']}*"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*ID:*\n{task['id']}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*優先度:*\n{task.get('priority', 'N/A')}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*作成者:*\n{task.get('created_by', 'Unknown')}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*担当:*\n{task.get('assigned_to', '未定')}"
                    }
                ]
            }
        ]
        
        return self.send_message(
            text=f"新しいタスク: {task['title']}",
            blocks=blocks
        )
    
    def notify_task_completed(self, task: Dict[str, Any]) -> bool:
        """タスク完了通知"""
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*✅ タスクが完了しました*\n\n*{task['title']}*"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*ID:*\n{task['id']}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*担当:*\n{task.get('assigned_to', 'Unknown')}"
                    }
                ]
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"完了時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    }
                ]
            }
        ]
        
        return self.send_message(
            text=f"✅ タスク完了: {task['title']}",
            blocks=blocks
        )
    
    def notify_error(self, agent: str, error_message: str, context: Dict = {}) -> bool:
        """エラー通知"""
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*⚠️ エラーが発生しました*\n\n*Agent:* {agent}\n*Error:* {error_message}"
                }
            }
        ]
        
        if context:
            fields = []
            for key, value in list(context.items())[:4]:  # 最大4つ
                fields.append({
                    "type": "mrkdwn",
                    "text": f"*{key}:*\n{value}"
                })
            
            if fields:
                blocks.append({
                    "type": "section",
                    "fields": fields
                })
        
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"発生時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                }
            ]
        })
        
        return self.send_message(
            text=f"⚠️ Error in {agent}: {error_message}",
            blocks=blocks
        )
    
    def notify_system_alert(self, alert_type: str, message: str, severity: str = "warning") -> bool:
        """システムアラート通知"""
        emoji = {
            "critical": "🚨",
            "warning": "⚠️",
            "info": "ℹ️"
        }.get(severity, "📢")
        
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{emoji} System Alert*\n\n*Type:* {alert_type}\n*Message:* {message}"
                }
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Severity: {severity.upper()} | Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    }
                ]
            }
        ]
        
        return self.send_message(
            text=f"{emoji} {alert_type}: {message}",
            blocks=blocks
        )
    
    def notify_agent_activity(self, agent: str, activity: str, details: str = "") -> bool:
        """エージェント活動通知"""
        emoji_map = {
            "Remi": "🎯",
            "Luna": "⚙️",
            "Mina": "🔍",
            "Aria": "📖"
        }
        
        emoji = emoji_map.get(agent, "🤖")
        
        text = f"{emoji} *{agent}*: {activity}"
        if details:
            text += f"\n_{details}_"
        
        return self.send_message(text)
    
    def get_status(self) -> Dict[str, Any]:
        """Slack統合ステータス"""
        return {
            "available": self.available,
            "default_channel": self.default_channel if self.available else None,
            "team": self._get_team_info() if self.available else None
        }
    
    def _get_team_info(self) -> Optional[Dict]:
        """チーム情報取得"""
        try:
            response = self.client.auth_test()
            return {
                "team": response.get("team"),
                "user": response.get("user")
            }
        except:
            return None


# グローバルインスタンス
slack = SlackIntegration()


# 便利関数
def notify_task_created(task: Dict[str, Any]) -> bool:
    return slack.notify_task_created(task)

def notify_task_completed(task: Dict[str, Any]) -> bool:
    return slack.notify_task_completed(task)

def notify_error(agent: str, error_message: str, context: Dict = {}) -> bool:
    return slack.notify_error(agent, error_message, context)

def notify_system_alert(alert_type: str, message: str, severity: str = "warning") -> bool:
    return slack.notify_system_alert(alert_type, message, severity)

def notify_agent_activity(agent: str, activity: str, details: str = "") -> bool:
    return slack.notify_agent_activity(agent, activity, details)

def get_slack_status() -> Dict[str, Any]:
    return slack.get_status()

