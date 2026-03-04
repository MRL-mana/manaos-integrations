#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ManaOS 秘書Slackボット
「レミ宛て」投稿で秘書が動く
"""

import os
import sys
import requests
import logging
import time
from typing import Optional, Dict, List
from flask import Flask, request, jsonify

try:
    from slack_bolt import App
    from slack_bolt.adapter.flask import SlackRequestHandler
    HAS_SLACK = True
except ImportError:
    HAS_SLACK = False
    print("slack-boltがインストールされていません")
    print("インストール: pip install slack-bolt")

# 設定
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET", "")
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "")
MOTHER_SHIP_OLLAMA_URL = os.getenv("MOTHER_SHIP_OLLAMA_URL", "http://100.73.247.100:11434")
SECRETARY_API_URL = os.getenv("SECRETARY_API_URL", "http://127.0.0.1:8080")

# Flaskアプリ
flask_app = Flask(__name__)

# Slackアプリ
if HAS_SLACK and SLACK_BOT_TOKEN and SLACK_SIGNING_SECRET:
    slack_app = App(token=SLACK_BOT_TOKEN, signing_secret=SLACK_SIGNING_SECRET)
    handler = SlackRequestHandler(slack_app)
else:
    slack_app = None
    handler = None

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# インテント分類キーワード（簡易版）
INTENT_KEYWORDS = {
    "TASK": ["予定", "タスク", "やること", "追加", "登録", "明日", "来週", "スケジュール", "カレンダー"],
    "EXEC": ["実行", "やって", "処理", "起動", "開始", "実行して"],
    "LOG": ["日記", "メモ", "記録", "実績", "今日は", "完了", "終わった"],
    "EMERGENCY": ["至急", "緊急", "すぐ", "今すぐ", "急いで", "緊急事態"],
    "INFO": ["何", "いつ", "どこ", "どう", "教えて", "確認", "予定", "今日の"]
}

def classify_intent(text: str) -> str:
    """簡易インテント分類"""
    text_lower = text.lower()
    
    # EMERGENCY最優先
    for keyword in INTENT_KEYWORDS["EMERGENCY"]:
        if keyword in text_lower:
            return "EMERGENCY"
    
    # その他の分類
    for intent, keywords in INTENT_KEYWORDS.items():
        if intent == "EMERGENCY":
            continue
        for keyword in keywords:
            if keyword in text_lower:
                return intent
    
    return "INFO"

def send_to_secretary_api(text: str, user_id: str, source: str = "slack") -> Dict:
    """秘書APIに送信"""
    try:
        payload = {
            "user": user_id,
            "text": text,
            "source": source,
            "timestamp": time.time()
        }
        
        response = requests.post(
            f"{SECRETARY_API_URL}/secretary",
            json=payload,
            timeout=15
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Secretary API error: {response.status_code}")
            return {"ok": False, "error": f"HTTP {response.status_code}"}
    except Exception as e:
        logger.error(f"Secretary API request error: {e}")
        return {"ok": False, "error": str(e)}

def send_to_n8n(payload: Dict) -> bool:
    """n8nに直接送信（フォールバック）"""
    if not N8N_WEBHOOK_URL:
        return False
    
    try:
        response = requests.post(N8N_WEBHOOK_URL, json=payload, timeout=15)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"n8n webhook error: {e}")
        return False

def get_llm_response(text: str, model: str = "qwen2.5:7b") -> Optional[str]:
    """LLMから応答を取得"""
    try:
        payload = {
            "model": model,
            "prompt": text,
            "stream": False
        }
        response = requests.post(
            f"{MOTHER_SHIP_OLLAMA_URL}/api/generate",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json().get("response", "")
        return None
    except Exception as e:
        logger.error(f"LLM API error: {e}")
        return None

def is_remi_mention(text: str) -> bool:
    """「レミ」宛てかチェック"""
    text_lower = text.lower()
    remi_keywords = ["レミ", "remi", "秘書", "manaos"]
    
    for keyword in remi_keywords:
        if keyword in text_lower:
            return True
    return False

if slack_app:
    @slack_app.event("app_mention")
    def handle_mention(event, say):
        """メンション処理（レミ宛て）"""
        _handle_mention(event, say)

def _handle_mention(event, say):
    """メンション処理（レミ宛て）"""
    user_id = event["user"]
    text = event["text"]
    
    # ボット自身のメンションを除去
    bot_user_id = slack_app.client.auth_test()["user_id"]
    text = text.replace(f"<@{bot_user_id}>", "").strip()
    
    if not text:
        say("メッセージを入力してください")
        return
    
    # レミ宛てチェック
    if not is_remi_mention(text):
        return
    
    # インテント分類
    intent = classify_intent(text)
    
    # 秘書APIに送信
    result = send_to_secretary_api(text, user_id, "slack")
    
    if result.get("ok"):
        intent = result.get("intent", intent)
        
        # INFO系はLLM応答を返す
        if intent == "INFO":
            llm_response = get_llm_response(text)
            if llm_response:
                say(f"💬 {llm_response}")
            else:
                say(f"✅ 処理しました（{intent}）")
        else:
            # その他は処理完了を通知
            say(f"✅ 処理しました（{intent}）\n「{text}」を記録・実行します")
    else:
        # フォールバック：n8nに直接送信
        payload = {
            "user": user_id,
            "text": text,
            "intent": intent,
            "source": "slack",
            "timestamp": time.time()
        }
        
        if send_to_n8n(payload):
            say(f"✅ 処理しました（{intent}）")
        else:
            say("❌ 処理に失敗しました。もう一度お試しください。")

if slack_app:
    @slack_app.event("message")
    def handle_message(event, say):
        """DMメッセージ処理（レミ宛て）"""
        _handle_message(event, say)

def _handle_message(event, say):
    """DMメッセージ処理（レミ宛て）"""
    # メンションは別ハンドラーで処理
    if event.get("subtype") or "bot_id" in event:
        return
    
    # DMのみ処理
    if event.get("channel_type") != "im":
        return
    
    user_id = event["user"]
    text = event["text"]
    
    # レミ宛てチェック
    if not is_remi_mention(text):
        # DMでレミ宛てじゃない場合は、デフォルトで処理
        pass
    
    # インテント分類
    intent = classify_intent(text)
    
    # 秘書APIに送信
    result = send_to_secretary_api(text, user_id, "slack")
    
    if result.get("ok"):
        intent = result.get("intent", intent)
        
        # INFO系はLLM応答を返す
        if intent == "INFO":
            llm_response = get_llm_response(text)
            if llm_response:
                say(f"💬 {llm_response}")
            else:
                say(f"✅ 処理しました（{intent}）")
        else:
            say(f"✅ 処理しました（{intent}）\n「{text}」を記録・実行します")
    else:
        # フォールバック
        payload = {
            "user": user_id,
            "text": text,
            "intent": intent,
            "source": "slack",
            "timestamp": time.time()
        }
        
        if send_to_n8n(payload):
            say(f"✅ 処理しました（{intent}）")
        else:
            say("❌ 処理に失敗しました。もう一度お試しください。")

if slack_app:
    @slack_app.command("/remi")
    def handle_remi_command(ack, respond, command):
        """レミコマンド（直接実行）"""
        _handle_remi_command(ack, respond, command)

def _handle_remi_command(ack, respond, command):
    """レミコマンド（直接実行）"""
    ack()
    user_id = command["user_id"]
    text = command.get("text", "").strip()
    
    if not text:
        respond("使用方法: /remi <メッセージ>\n例: /remi 明日の14時に会議")
        return
    
    # インテント分類
    intent = classify_intent(text)
    
    # 秘書APIに送信
    result = send_to_secretary_api(text, user_id, "slack")
    
    if result.get("ok"):
        intent = result.get("intent", intent)
        
        if intent == "INFO":
            llm_response = get_llm_response(text)
            if llm_response:
                respond(f"💬 {llm_response}")
            else:
                respond(f"✅ 処理しました（{intent}）")
        else:
            respond(f"✅ 処理しました（{intent}）\n「{text}」を記録・実行します")
    else:
        respond("❌ 処理に失敗しました。もう一度お試しください。")

if slack_app:
    @slack_app.command("/remi-help")
    def handle_remi_help(ack, respond):
        """レミヘルプ"""
        _handle_remi_help(ack, respond)

def _handle_remi_help(ack, respond):
    """レミヘルプ"""
    ack()
    help_text = """
🤖 ManaOS 秘書「レミ」ヘルプ

使い方:
• チャンネルで「@レミ」または「レミ」を含むメッセージを投稿
• DMで「レミ」を含むメッセージを送信
• `/remi <メッセージ>` コマンドで直接実行

例:
• 「レミ、明日の14時に会議」→ 予定追加
• 「レミ、今日の予定は？」→ 予定確認
• 「レミ、今日はA1111の設定を完了した」→ 実績記録

対応インテント:
• INFO: 質問・確認
• TASK: 予定・タスク追加
• EXEC: 実行・処理
• LOG: 日記・実績記録
• EMERGENCY: 緊急通知
    """
    respond(help_text)

@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    """Slackイベントエンドポイント"""
    if handler:
        return handler.handle(request)
    return jsonify({"error": "Slackボットが設定されていません"}), 500

@flask_app.route("/health", methods=["GET"])
def health():
    """ヘルスチェック"""
    return jsonify({
        "status": "ok",
        "service": "manaos_secretary_slack_bot",
        "slack_configured": bool(SLACK_BOT_TOKEN and SLACK_SIGNING_SECRET),
        "n8n_configured": bool(N8N_WEBHOOK_URL),
        "secretary_api_url": SECRETARY_API_URL
    })

def main():
    """メイン関数"""
    port = int(os.getenv("PORT", "3001"))
    
    if not HAS_SLACK:
        logger.warning("slack-boltがインストールされていません。HTTPサーバーのみ起動します。")
    
    if not SLACK_BOT_TOKEN or not SLACK_SIGNING_SECRET:
        logger.warning("SLACK_BOT_TOKEN/SLACK_SIGNING_SECRET が未設定です。")
        logger.warning("Slack連携は無効ですが、HTTPサーバーは起動します。")
    else:
        logger.info("ManaOS 秘書Slackボットを起動しています...")
        logger.info(f"Secretary API URL: {SECRETARY_API_URL}")
        logger.info(f"n8n Webhook URL: {'設定済み' if N8N_WEBHOOK_URL else '未設定'}")
    
    logger.info(f"HTTPサーバーを起動: port={port}")
    flask_app.run(host="0.0.0.0", port=port, debug=False)

if __name__ == "__main__":
    main()



