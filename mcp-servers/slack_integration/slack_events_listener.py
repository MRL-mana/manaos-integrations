#!/usr/bin/env python3
"""
Slack Events API Listener
TelegramBotと同じレベルの双方向会話を実現
メンション・DM受信 → ManaOS v3処理 → 自動返信
"""

import os
import asyncio
import httpx
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

app = Flask(__name__)
CORS(app)

# 設定
WORK_DIR = Path("/root/slack_integration")
LOGS_DIR = WORK_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

SLACK_TOKEN = os.environ.get('SLACK_BOT_TOKEN')
if not SLACK_TOKEN:
    token_file = WORK_DIR / "config" / "slack_token.txt"
    if token_file.exists():
        SLACK_TOKEN = token_file.read_text().strip()

# ManaOS v3 エンドポイント
MANAOS_ORCHESTRATOR_URL = "http://localhost:9200/run"
SLACK_SERVICE_URL = "http://localhost:5020"

# 処理済みイベント追跡（重複防止）
processed_events = set()


def log(message: str):
    """ログ記録"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"[{timestamp}] {message}"
    print(log_message)
    
    log_file = LOGS_DIR / f"events_{datetime.now().strftime('%Y%m%d')}.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_message + "\n")


async def process_with_manaos(
    message: str,
    channel: str,
    user: str,
    thread_ts: Optional[str] = None
) -> Dict[str, Any]:
    """
    メッセージをManaOS v3 Orchestratorで処理
    
    Args:
        message: ユーザーメッセージ
        channel: チャンネルID
        user: ユーザーID
        thread_ts: スレッドタイムスタンプ
    
    Returns:
        処理結果
    """
    log(f"🤖 ManaOS v3で処理中: {message[:50]}...")
    
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                MANAOS_ORCHESTRATOR_URL,
                json={
                    "text": message,
                    "context": {
                        "source": "slack",
                        "channel": channel,
                        "user": user,
                        "thread_ts": thread_ts
                    },
                    "actor": "luna",  # デフォルトはLuna
                    "user": "mana"
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                log(f"  ✅ ManaOS処理完了: {result.get('status')}")
                return result
            else:
                log(f"  ⚠️ ManaOS返答: HTTP {response.status_code}")
                return {
                    'success': False,
                    'message': f"処理に失敗しました（HTTP {response.status_code}）"
                }
    
    except Exception as e:
        log(f"  ❌ ManaOSエラー: {e}")
        return {
            'success': False,
            'message': f"エラーが発生しました: {str(e)}"
        }


def send_slack_reply(
    channel: str,
    message: str,
    thread_ts: Optional[str] = None
):
    """Slackに返信"""
    try:
        payload = {
            "channel": channel,
            "text": message
        }
        
        if thread_ts:
            payload["thread_ts"] = thread_ts
        
        response = requests.post(
            f"{SLACK_SERVICE_URL}/send",
            json=payload,
            timeout=5
        )
        
        result = response.json()
        if result.get("success"):
            log(f"📤 Slack返信送信: {message[:50]}...")
        else:
            log(f"❌ Slack送信失敗: {result.get('error')}")
        
        return result
    
    except Exception as e:
        log(f"❌ Slack送信エラー: {e}")
        return {"success": False, "error": str(e)}


@app.route('/slack/events', methods=['POST'])
def handle_events():
    """
    Slack Events APIハンドラー
    TelegramBotと同じように、メッセージを受信→処理→返信
    """
    try:
        data = request.json
        
        # URL検証（初回セットアップ時）
        if data.get('type') == 'url_verification':
            log("🔐 URL検証リクエスト受信")
            return jsonify({"challenge": data.get('challenge')})
        
        # イベント処理
        if data.get('type') == 'event_callback':
            event = data.get('event', {})
            event_type = event.get('type')
            event_id = data.get('event_id')
            
            # 重複イベント防止
            if event_id in processed_events:
                return jsonify({"ok": True})
            
            processed_events.add(event_id)
            
            # イベントタイプ別処理
            if event_type == 'app_mention':
                # @ManaOSBot メンションされた
                handle_mention(event)
            
            elif event_type == 'message':
                # DMまたはチャンネルメッセージ
                if event.get('channel_type') == 'im':
                    # ダイレクトメッセージ
                    handle_direct_message(event)
                elif 'bot_id' not in event:
                    # Bot自身のメッセージは無視
                    handle_channel_message(event)
        
        return jsonify({"ok": True})
    
    except Exception as e:
        log(f"❌ イベント処理エラー: {e}")
        return jsonify({"error": str(e)}), 500


def handle_mention(event: Dict[str, Any]):
    """
    メンション処理（@ManaOSBot への呼びかけ）
    Telegramの /start や通常メッセージと同等
    """
    channel = event.get('channel')
    user = event.get('user')
    text = event.get('text', '')
    thread_ts = event.get('thread_ts') or event.get('ts')
    
    # メンション部分を除去
    clean_text = text.split('>', 1)[-1].strip()
    
    log(f"👋 メンション受信: @{user} in #{channel}")
    log(f"   メッセージ: {clean_text}")
    
    # 非同期処理を同期的に実行
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # ManaOS v3で処理
        result = loop.run_until_complete(
            process_with_manaos(clean_text, channel, user, thread_ts)
        )
        
        # 応答メッセージ生成
        if result.get('success'):
            reply = result.get('message', '処理が完了しました')
            
            # 詳細情報があれば追加
            intent = result.get('intent', {})
            if intent:
                intent_name = intent.get('name', 'unknown')
                reply += f"\n\n_🎯 検出: {intent_name}_"
        else:
            reply = "申し訳ありません。処理中にエラーが発生しました。"
        
        # Slackに返信
        send_slack_reply(channel, reply, thread_ts)
    
    finally:
        loop.close()


def handle_direct_message(event: Dict[str, Any]):
    """
    ダイレクトメッセージ処理
    Telegram Botの個別チャットと同等
    """
    channel = event.get('channel')
    user = event.get('user')
    text = event.get('text', '')
    
    log(f"💬 DM受信: @{user}")
    log(f"   メッセージ: {text}")
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        result = loop.run_until_complete(
            process_with_manaos(text, channel, user)
        )
        
        reply = result.get('message', '処理が完了しました') if result.get('success') else "エラーが発生しました"
        send_slack_reply(channel, reply)
    
    finally:
        loop.close()


def handle_channel_message(event: Dict[str, Any]):
    """
    チャンネルメッセージ処理（オプション）
    特定のキーワードに反応する場合など
    """
    text = event.get('text', '')
    
    # "ManaOS" を含むメッセージに反応
    if 'manaos' in text.lower():
        channel = event.get('channel')
        user = event.get('user')
        thread_ts = event.get('thread_ts') or event.get('ts')
        
        log(f"🔍 キーワード検出: #{channel}")
        
        # 簡単な返信
        send_slack_reply(
            channel,
            "👋 ManaOSに関する質問ですか？ @ManaOSBot をメンションして話しかけてください！",
            thread_ts
        )


@app.route('/health')
def health():
    """ヘルスチェック"""
    return jsonify({
        "status": "healthy",
        "service": "Slack Events Listener",
        "manaos_url": MANAOS_ORCHESTRATOR_URL,
        "timestamp": datetime.now().isoformat()
    })


if __name__ == '__main__':
    log("=" * 60)
    log("👂 Slack Events Listener 起動")
    log("=" * 60)
    log(f"ManaOS v3: {MANAOS_ORCHESTRATOR_URL}")
    log(f"Slack Service: {SLACK_SERVICE_URL}")
    log("API起動中... (http://0.0.0.0:5022)")
    log("Ctrl+C で停止")
    log("")
    log("📝 設定方法:")
    log("  1. Slack App設定 → Event Subscriptions")
    log("  2. Request URL: http://your-server:5022/slack/events")
    log("  3. Subscribe to bot events:")
    log("     - app_mention")
    log("     - message.im")
    log("     - message.channels")
    log("")
    
    app.run(host='0.0.0.0', port=5022, debug=os.getenv("DEBUG", "False").lower() == "true")

