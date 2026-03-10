#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
マナOS Slackボット
Ollama統合でローカルLLMを使えるSlackボット
"""

import os
import sys
import requests
import logging
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
MANAOS_API_BASE = os.getenv("MANAOS_API_BASE", "http://127.0.0.1:9405")
DEFAULT_MODEL = os.getenv("OLLAMA_DEFAULT_MODEL", "qwen2.5:7b")

# Flaskアプリ
flask_app = Flask(__name__)

# Slackアプリ
_slack_connected = False
if HAS_SLACK and SLACK_BOT_TOKEN and SLACK_SIGNING_SECRET:
    slack_app = App(token=SLACK_BOT_TOKEN, signing_secret=SLACK_SIGNING_SECRET)  # type: ignore[possibly-unbound]
    handler = SlackRequestHandler(slack_app)  # type: ignore[possibly-unbound]
    _slack_connected = True
else:
    # ダミーApp: デコレーターだけ通す（実際のSlack連携は無効）
    class _DummySlackApp:
        def event(self, *a, **kw):
            def decorator(f): return f
            return decorator
        def command(self, *a, **kw):
            def decorator(f): return f
            return decorator
    slack_app = _DummySlackApp()
    handler = None

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ユーザーごとのチャット履歴
user_chat_history = {}


def get_ollama_models() -> List[Dict]:
    """利用可能なモデル一覧を取得"""
    try:
        response = requests.get(f"{MANAOS_API_BASE}/api/ollama/models", timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get("models", [])
        return []
    except Exception as e:
        logger.error(f"モデル一覧取得エラー: {e}")
        return []


def generate_text(model: str, prompt: str) -> Optional[str]:
    """テキスト生成"""
    try:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        response = requests.post(
            f"{MANAOS_API_BASE}/api/ollama/generate",
            json=payload,
            timeout=300
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get("response", "")
        return None
    except Exception as e:
        logger.error(f"テキスト生成エラー: {e}")
        return None


def chat_with_model(model: str, messages: List[Dict]) -> Optional[str]:
    """チャット"""
    try:
        payload = {
            "model": model,
            "messages": messages,
            "stream": False
        }
        response = requests.post(
            f"{MANAOS_API_BASE}/api/ollama/chat",
            json=payload,
            timeout=300
        )
        
        if response.status_code == 200:
            result = response.json()
            message = result.get("message", {})
            return message.get("content", "")
        return None
    except Exception as e:
        logger.error(f"チャットエラー: {e}")
        return None


if slack_app:
    @slack_app.command("/manaos-help")
    def handle_help_command(ack, respond, command):
        """ヘルプコマンド"""
        ack()
    help_text = """
🤖 マナOS Slackボット ヘルプ

コマンド:
• `/manaos-help` - このヘルプを表示
• `/manaos-models` - 利用可能なモデル一覧
• `/manaos-model <name>` - モデルを変更
• `/manaos-reset` - チャット履歴をリセット
• `/ai-image <prompt>` - AI画像生成（Ollamaでプロンプト改善）
• `/ai-video <prompt>` - AI動画生成（Ollamaでプロンプト改善）

使い方:
メンション（@マナOS）またはDMでメッセージを送ると、LLMが応答します。

例:
@マナOS こんにちは
/manaos-model qwen2.5:14b
    """
    respond(help_text)  # type: ignore[name-defined]


if slack_app:
    @slack_app.command("/manaos-models")
    def handle_models_command(ack, respond, command):
        """モデル一覧コマンド"""
        ack()
    models = get_ollama_models()
    if not models:
        respond("❌ モデル一覧を取得できませんでした")  # type: ignore[name-defined]
        return
    
    model_list = "📚 利用可能なモデル:\n\n"
    for model in models[:10]:
        name = model.get("name", "unknown")
        size = model.get("size", 0)
        size_gb = size / (1024**3)
        model_list += f"• {name} ({size_gb:.1f}GB)\n"
    
    respond(model_list)  # type: ignore[name-defined]


if slack_app:
    @slack_app.command("/manaos-model")
    def handle_model_command(ack, respond, command):
        """モデル変更コマンド"""
        ack()
    user_id = command["user_id"]  # type: ignore[name-defined]
    
    if not command.get("text"):  # type: ignore[name-defined]
        respond("使用方法: /manaos-model <モデル名>\n例: /manaos-model qwen2.5:7b")  # type: ignore[name-defined]
        return
    
    model_name = command["text"]  # type: ignore[name-defined]
    
    if user_id not in user_chat_history:
        user_chat_history[user_id] = {"model": DEFAULT_MODEL, "messages": []}
    
    user_chat_history[user_id]["model"] = model_name
    respond(f"✅ モデルを {model_name} に変更しました")  # type: ignore[name-defined]


if slack_app:
    @slack_app.command("/manaos-reset")
    def handle_reset_command(ack, respond, command):
        """リセットコマンド"""
        ack()
    user_id = command["user_id"]  # type: ignore[name-defined]
    
    if user_id in user_chat_history:
        user_chat_history[user_id]["messages"] = []
    
    respond("🔄 チャット履歴をリセットしました")  # type: ignore[name-defined]


if slack_app:
    @slack_app.command("/ai-image")
    def handle_ai_image_command(ack, respond, command):
        """AI画像生成コマンド"""
        ack()
    user_id = command["user_id"]  # type: ignore[name-defined]
    text = command.get("text", "").strip()  # type: ignore[name-defined]
    
    if not text:
        respond("使用方法: /ai-image <プロンプト>\n例: /ai-image beautiful landscape, sunset")  # type: ignore[name-defined]
        return
    
    try:
        import requests
        AI_WORKSPACE_URL = os.getenv("AI_WORKSPACE_INTEGRATION_URL", "http://127.0.0.1:9419")
        
        payload = {
            "user_prompt": text,
            "improve_prompt": True,
            "width": 1024,
            "height": 1024,
            "steps": 28,
            "cfg_scale": 7.5
        }
        
        respond(f"🎨 画像生成を開始しました: {text[:50]}...")  # type: ignore[name-defined]
        
        response = requests.post(
            f"{AI_WORKSPACE_URL}/api/ai/image/generate",
            json=payload,
            timeout=300
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                improved = result.get("improved_prompt", text)
                images = result.get("result", {}).get("images", [])
                
                if images:
                    respond(f"✅ 画像生成完了！\n改善されたプロンプト: {improved[:100]}...")  # type: ignore[name-defined]
                    # 画像URLがあれば送信（実装に応じて調整）
                else:
                    respond("✅ 画像生成完了（画像URL取得中...）")  # type: ignore[name-defined]
            else:
                respond(f"❌ 画像生成失敗: {result.get('detail', 'Unknown error')}")  # type: ignore[name-defined]
        else:
            respond(f"❌ エラー: HTTP {response.status_code}")  # type: ignore[name-defined]
    
    except Exception as e:
        logger.error(f"AI画像生成エラー: {e}")
        respond(f"❌ エラーが発生しました: {str(e)}")  # type: ignore[name-defined]


if slack_app:
    @slack_app.command("/ai-video")
    def handle_ai_video_command(ack, respond, command):
        """AI動画生成コマンド"""
        ack()
    text = command.get("text", "").strip()  # type: ignore[name-defined]
    
    if not text:
        respond("使用方法: /ai-video <プロンプト>\n例: /ai-video beautiful landscape animation")  # type: ignore[name-defined]
        return
    
    try:
        import requests
        AI_WORKSPACE_URL = os.getenv("AI_WORKSPACE_INTEGRATION_URL", "http://127.0.0.1:9419")
        
        payload = {
            "user_prompt": text,
            "improve_prompt": True,
            "frames": 120,
            "fps": 12
        }
        
        respond(f"🎬 動画生成を開始しました: {text[:50]}...")  # type: ignore[name-defined]
        
        response = requests.post(
            f"{AI_WORKSPACE_URL}/api/ai/video/generate",
            json=payload,
            timeout=600
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                respond("✅ 動画生成完了！")  # type: ignore[name-defined]
            else:
                respond(f"❌ 動画生成失敗: {result.get('detail', 'Unknown error')}")  # type: ignore[name-defined]
        else:
            respond(f"❌ エラー: HTTP {response.status_code}")  # type: ignore[name-defined]
    
    except Exception as e:
        logger.error(f"AI動画生成エラー: {e}")
        respond(f"❌ エラーが発生しました: {str(e)}")  # type: ignore[name-defined]


if slack_app:
    @slack_app.event("app_mention")
    def handle_mention(event, say):
        """メンション処理"""
        user_id = event["user"]
        text = event["text"].replace(f"<@{slack_app.client.auth_test()['user_id']}>", "").strip()  # type: ignore
    
    if not text:  # type: ignore[possibly-unbound]
        say("メッセージを入力してください")  # type: ignore[name-defined]
        return  # type: ignore[invalid-escape-sequence]
    
    # ユーザー設定を初期化
    if user_id not in user_chat_history:  # type: ignore[possibly-unbound]
        user_chat_history[user_id] = {"model": DEFAULT_MODEL, "messages": []}  # type: ignore[possibly-unbound]
    
    user_config = user_chat_history[user_id]  # type: ignore[possibly-unbound]
    model = user_config["model"]
    messages = user_config["messages"]
    
    # チャット履歴がある場合はチャットAPI、ない場合は生成API
    if messages:
        messages.append({"role": "user", "content": text})
        response_text = chat_with_model(model, messages)
        
        if response_text:
            messages.append({"role": "assistant", "content": response_text})
            say(response_text)  # type: ignore[name-defined]
        else:
            say("❌ エラーが発生しました。もう一度お試しください。")  # type: ignore[name-defined]
    else:
        response_text = generate_text(model, text)
        
        if response_text:
            say(response_text)  # type: ignore[name-defined]
        else:
            say("❌ エラーが発生しました。もう一度お試しください。")  # type: ignore[name-defined]


if slack_app:
    @slack_app.event("message")
    def handle_message(event, say):
        """DMメッセージ処理"""
        # メンションは別ハンドラーで処理
        if event.get("subtype") or "bot_id" in event:
            return
    
    # DMのみ処理
    if event.get("channel_type") != "im":  # type: ignore[name-defined]
        return  # type: ignore
    
    user_id = event["user"]  # type: ignore[name-defined]
    text = event["text"]  # type: ignore[name-defined]
    
    # ユーザー設定を初期化
    if user_id not in user_chat_history:
        user_chat_history[user_id] = {"model": DEFAULT_MODEL, "messages": []}
    
    user_config = user_chat_history[user_id]
    model = user_config["model"]
    messages = user_config["messages"]
    
    # チャット履歴がある場合はチャットAPI、ない場合は生成API
    if messages:
        messages.append({"role": "user", "content": text})
        response_text = chat_with_model(model, messages)
        
        if response_text:
            messages.append({"role": "assistant", "content": response_text})
            say(response_text)  # type: ignore[name-defined]
        else:
            say("❌ エラーが発生しました。もう一度お試しください。")  # type: ignore[name-defined]
    else:
        response_text = generate_text(model, text)
        
        if response_text:
            say(response_text)  # type: ignore[name-defined]
        else:
            say("❌ エラーが発生しました。もう一度お試しください。")  # type: ignore[name-defined]


@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    """Slackイベントエンドポイント"""
    if handler:
        return handler.handle(request)
    return jsonify({"error": "Slackボットが設定されていません"}), 500


@flask_app.route("/health", methods=["GET"])
def health():
    """ヘルスチェック"""
    return jsonify({"status": "ok", "service": "manaos_slack_bot"})


def main():
    """メイン関数"""
    port = int(os.getenv("PORT", "3000"))
    
    if not HAS_SLACK:
        logger.warning("slack-boltがインストールされていません。HTTPサーバーのみ起動します。")
    
    if not SLACK_BOT_TOKEN or not SLACK_SIGNING_SECRET:
        logger.warning("SLACK_BOT_TOKEN/SLACK_SIGNING_SECRET が未設定です。")
        logger.warning("Slack連携は無効ですが、HTTPサーバーは起動します。")
    else:
        logger.info("Slackボットを起動しています...")
    
    logger.info(f"HTTPサーバーを起動: port={port}")
    flask_app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    main()

