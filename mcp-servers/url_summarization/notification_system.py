#!/usr/bin/env python3
"""
通知システム
新着情報通知、トレンドアラート、LINE/Slack通知統合
"""

import requests
import os
from typing import Dict, List


class NotificationSystem:
    """通知システム"""
    
    def __init__(self):
        self.line_notify_token = os.getenv("LINE_NOTIFY_TOKEN")
        self.slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    
    def send_line_notification(self, message: str, image_url: str = None) -> Dict:
        """LINE通知送信"""
        if not self.line_notify_token:
            return {"success": False, "error": "LINE_NOTIFY_TOKENが設定されていません"}
        
        try:
            url = "https://notify-api.line.me/api/notify"
            headers = {
                "Authorization": f"Bearer {self.line_notify_token}"
            }
            
            data = {"message": message}
            if image_url:
                data["imageThumbnail"] = image_url
                data["imageFullsize"] = image_url
            
            response = requests.post(url, headers=headers, data=data, timeout=10)
            response.raise_for_status()
            
            return {"success": True, "message": "LINE通知送信成功"}
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def send_slack_notification(self, message: str, channel: str = "#general") -> Dict:
        """Slack通知送信"""
        if not self.slack_webhook_url:
            return {"success": False, "error": "SLACK_WEBHOOK_URLが設定されていません"}
        
        try:
            payload = {
                "text": message,
                "channel": channel
            }
            
            response = requests.post(self.slack_webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            
            return {"success": True, "message": "Slack通知送信成功"}
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def send_alert(self, title: str, message: str, level: str = "info") -> Dict:
        """アラート送信"""
        emoji_map = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "❌",
            "critical": "🚨"
        }
        
        emoji = emoji_map.get(level, "ℹ️")
        alert_message = f"{emoji} **{title}**\n\n{message}"
        
        results = {
            "line": None,
            "slack": None
        }
        
        # LINE通知
        if self.line_notify_token:
            results["line"] = self.send_line_notification(alert_message)
        
        # Slack通知
        if self.slack_webhook_url:
            results["slack"] = self.send_slack_notification(alert_message)
        
        return {
            "success": True,
            "level": level,
            "results": results
        }
    
    def notify_new_articles(self, articles: List[Dict]) -> Dict:
        """新着記事通知"""
        try:
            message = "📰 **新着記事通知**\n\n"
            message += f"新しい記事が {len(articles)} 件見つかりました:\n\n"
            
            for i, article in enumerate(articles[:5], 1):
                message += f"{i}. {article.get('title', 'タイトルなし')}\n"
                message += f"   {article.get('url', '')}\n\n"
            
            return self.send_alert("新着記事", message, "info")
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def notify_trending(self, trends: List[Dict]) -> Dict:
        """トレンド通知"""
        try:
            message = "🔥 **トレンド通知**\n\n"
            message += f"新しいトレンドが {len(trends)} 件見つかりました:\n\n"
            
            for i, trend in enumerate(trends[:5], 1):
                message += f"{i}. {trend.get('keyword', '')}\n"
                message += f"   関連記事: {trend.get('article_count', 0)}件\n\n"
            
            return self.send_alert("トレンド", message, "warning")
        
        except Exception as e:
            return {"success": False, "error": str(e)}

