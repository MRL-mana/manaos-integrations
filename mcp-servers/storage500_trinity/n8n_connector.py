#!/usr/bin/env python3
"""
Trinity Living System - n8n Connector
n8n ワークフローエンジンとTrinity Orchestratorの橋渡し
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from flask import Flask, request, jsonify
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("n8n_connector")

app = Flask(__name__)

# Orchestrator API
ORCHESTRATOR_API = "http://localhost:9400"


class N8NConnector:
    """n8n ⇄ Orchestrator 連携クラス"""
    
    def __init__(self, orchestrator_url: str = ORCHESTRATOR_API):
        """初期化"""
        self.orchestrator_url = orchestrator_url
        logger.info(f"✅ n8n Connector initialized (Orchestrator: {orchestrator_url})")
    
    def trigger_orchestrator(self, goal: str, context: List[str] = None, budget_turns: int = 12) -> Dict:
        """
        Orchestratorをトリガー
        
        Args:
            goal: 目標
            context: コンテキスト
            budget_turns: 最大ターン数
            
        Returns:
            実行結果
        """
        try:
            response = requests.post(
                f"{self.orchestrator_url}/api/orchestrate",
                json={
                    "goal": goal,
                    "context": context or [],
                    "budget_turns": budget_turns
                },
                timeout=300  # 5分タイムアウト
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ Orchestrator triggered: {result.get('ticket_id')}")
                return {"success": True, "result": result}
            else:
                logger.error(f"❌ Orchestrator failed: {response.status_code}")
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            logger.error(f"❌ Orchestrator trigger failed: {e}")
            return {"success": False, "error": str(e)}
    
    def process_gmail_event(self, email_data: Dict) -> Dict:
        """
        Gmailイベントを処理
        
        Args:
            email_data: メールデータ {subject, from, body, ...}
            
        Returns:
            処理結果
        """
        subject = email_data.get("subject", "No Subject")
        from_addr = email_data.get("from", "Unknown")
        body_preview = email_data.get("body", "")[:200]
        
        goal = f"このメールを要約してNotionに登録: 件名『{subject}』"
        context = [
            f"差出人: {from_addr}",
            f"プレビュー: {body_preview}",
            "Notion登録必須",
            "重要度判定"
        ]
        
        return self.trigger_orchestrator(goal, context, budget_turns=10)
    
    def process_calendar_event(self, event_data: Dict) -> Dict:
        """
        カレンダーイベントを処理
        
        Args:
            event_data: イベントデータ {summary, start_time, ...}
            
        Returns:
            処理結果
        """
        summary = event_data.get("summary", "No Title")
        start_time = event_data.get("start_time", "Unknown")
        
        goal = f"カレンダー予定の準備: {summary} ({start_time})"
        context = [
            "準備すべきことをリストアップ",
            "Notionに記録",
            "必要なら資料作成"
        ]
        
        return self.trigger_orchestrator(goal, context, budget_turns=8)
    
    def daily_task_planning(self) -> Dict:
        """
        毎日のタスク計画（定期実行用）
        
        Returns:
            処理結果
        """
        goal = "今日のタスクを計画して優先順位付け"
        context = [
            "Googleカレンダーの予定確認",
            "Gmail未読メール確認",
            "Notion TODOリスト確認",
            "過去の優先順位パターンを参考",
            "Notionに「今日のタスク」ページ作成"
        ]
        
        return self.trigger_orchestrator(goal, context, budget_turns=15)


# Flask App

connector = N8NConnector()


@app.route('/health')
def health():
    """ヘルスチェック"""
    return jsonify({"status": "ok", "service": "n8n Connector"})


@app.route('/webhook/gmail', methods=['POST'])
def webhook_gmail():
    """
    Gmail Webhook
    n8nからのGmailイベントを受信
    """
    try:
        data = request.get_json()
        logger.info(f"📧 Gmail event received: {data.get('subject', 'No Subject')}")
        
        result = connector.process_gmail_event(data)
        return jsonify(result)
    except Exception as e:
        logger.error(f"❌ Gmail webhook error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/webhook/calendar', methods=['POST'])
def webhook_calendar():
    """
    Calendar Webhook
    n8nからのカレンダーイベントを受信
    """
    try:
        data = request.get_json()
        logger.info(f"📅 Calendar event received: {data.get('summary', 'No Title')}")
        
        result = connector.process_calendar_event(data)
        return jsonify(result)
    except Exception as e:
        logger.error(f"❌ Calendar webhook error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/webhook/daily_plan', methods=['POST'])
def webhook_daily_plan():
    """
    Daily Planning Webhook
    毎朝のタスク計画
    """
    try:
        logger.info("📋 Daily planning triggered")
        
        result = connector.daily_task_planning()
        return jsonify(result)
    except Exception as e:
        logger.error(f"❌ Daily planning error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/trigger/orchestrator', methods=['POST'])
def trigger_orchestrator():
    """
    汎用Orchestratorトリガー
    n8nから任意のタスクを実行
    """
    try:
        data = request.get_json()
        goal = data.get("goal")
        context = data.get("context", [])
        budget_turns = data.get("budget_turns", 12)
        
        if not goal:
            return jsonify({"success": False, "error": "goal is required"}), 400
        
        logger.info(f"🚀 Orchestrator triggered: {goal}")
        
        result = connector.trigger_orchestrator(goal, context, budget_turns)
        return jsonify(result)
    except Exception as e:
        logger.error(f"❌ Orchestrator trigger error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    logger.info("🚀 Starting n8n Connector...")
    logger.info("📍 Port: 9500")
    logger.info("🔗 Orchestrator: " + ORCHESTRATOR_API)
    logger.info("")
    logger.info("📡 Webhooks:")
    logger.info("  - POST /webhook/gmail (Gmail処理)")
    logger.info("  - POST /webhook/calendar (Calendar処理)")
    logger.info("  - POST /webhook/daily_plan (毎日のタスク計画)")
    logger.info("  - POST /trigger/orchestrator (汎用トリガー)")
    
    app.run(host="0.0.0.0", port=9500, debug=False)



