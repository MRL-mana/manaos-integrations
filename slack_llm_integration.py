"""
🎙️ Slack × 常時起動LLM統合
Slackから直接LLMを使えるようにする
"""

import os
import json
from typing import Dict, Any, Optional
from flask import Flask, request, jsonify
from flask_cors import CORS

# 統一モジュールのインポート
from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity

# LLMクライアントインポート
try:
    from always_ready_llm_integrated import IntegratedLLMClient, ModelType, TaskType
    LLM_CLIENT_AVAILABLE = True
except ImportError:
    try:
        from always_ready_llm_client import AlwaysReadyLLMClient, ModelType, TaskType
        LLM_CLIENT_AVAILABLE = True
    except ImportError:
        LLM_CLIENT_AVAILABLE = False

# ロガーの初期化
logger = get_logger(__name__)

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("SlackLLMIntegration")

app = Flask(__name__)
CORS(app)

# 設定
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
LLM_CLIENT = None

# LLMクライアント初期化
if LLM_CLIENT_AVAILABLE:
    try:
        LLM_CLIENT = IntegratedLLMClient(
            auto_save_obsidian=True,
            auto_notify_slack=False,  # 無限ループ防止
            auto_save_memory=True
        )
        logger.info("✅ Slack LLM統合クライアント初期化完了")
    except Exception as e:
        logger.warning(f"統合クライアント初期化失敗、基本クライアントを使用: {e}")
        try:
            from always_ready_llm_client import AlwaysReadyLLMClient
            LLM_CLIENT = AlwaysReadyLLMClient()
        except Exception as e2:
            logger.error(f"LLMクライアント初期化失敗: {e2}")


def send_to_slack(text: str, channel: Optional[str] = None, thread_ts: Optional[str] = None):
    """Slackにメッセージを送信"""
    if not SLACK_WEBHOOK_URL:
        logger.warning("Slack Webhook URLが設定されていません")
        return False
    
    try:
        import requests
        payload = {"text": text}
        if channel:
            payload["channel"] = channel
        if thread_ts:
            payload["thread_ts"] = thread_ts
        
        response = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Slack送信エラー: {e}")
        return False


def parse_slack_message(text: str) -> Dict[str, Any]:
    """
    Slackメッセージを解析
    
    Args:
        text: Slackメッセージテキスト
    
    Returns:
        解析結果（モデル、タスクタイプなど）
    """
    # デフォルト設定
    model = ModelType.LIGHT
    task_type = TaskType.CONVERSATION
    
    # モデル指定をチェック
    text_lower = text.lower()
    if "heavy" in text_lower or "高品質" in text_lower:
        model = ModelType.HEAVY
    elif "medium" in text_lower or "中型" in text_lower:
        model = ModelType.MEDIUM
    elif "reasoning" in text_lower or "推論" in text_lower:
        model = ModelType.REASONING
        task_type = TaskType.REASONING
    
    # タスクタイプをチェック
    if "コード" in text or "code" in text_lower or "生成" in text:
        task_type = TaskType.AUTOMATION
    elif "推論" in text or "分析" in text or "reasoning" in text_lower:
        task_type = TaskType.REASONING
    elif "生成" in text or "generate" in text_lower:
        task_type = TaskType.GENERATION
    
    # メンションやコマンドを除去
    cleaned_text = text
    if "<@" in cleaned_text:
        # Botメンションを除去
        parts = cleaned_text.split(">")
        if len(parts) > 1:
            cleaned_text = ">".join(parts[1:]).strip()
    
    return {
        "text": cleaned_text,
        "model": model,
        "task_type": task_type
    }


@app.route('/health', methods=['GET'])
def health():
    """ヘルスチェック"""
    return jsonify({
        "status": "healthy",
        "service": "Slack LLM Integration",
        "llm_available": LLM_CLIENT is not None
    })


@app.route('/api/slack/llm/chat', methods=['POST'])
def slack_llm_chat():
    """SlackからLLMチャット"""
    if not LLM_CLIENT:
        return jsonify({
            "error": "LLMクライアントが利用できません"
        }), 503
    
    try:
        data = request.get_json() or {}
        text = data.get("text", request.form.get("text", ""))
        user = data.get("user", "unknown")
        channel = data.get("channel", "general")
        thread_ts = data.get("thread_ts")
        
        if not text:
            return jsonify({
                "error": "textパラメータが必要です"
            }), 400
        
        logger.info(f"Slack LLMチャット受信: {text[:50]}... (User: {user})")
        
        # メッセージ解析
        parsed = parse_slack_message(text)
        
        # LLM呼び出し
        response = LLM_CLIENT.chat(
            parsed["text"],
            model=parsed["model"],
            task_type=parsed["task_type"],
            save_to_obsidian=True,
            notify_slack=False  # 無限ループ防止
        )
        
        # レスポンス生成
        result = {
            "status": "success",
            "response": response.response,
            "model": response.model,
            "latency_ms": response.latency_ms,
            "cached": response.cached,
            "integration_results": response.integration_results
        }
        
        # Slackに返信（オプション）
        if data.get("auto_reply", True):
            reply_text = f"""🤖 LLM応答

{response.response}

---
モデル: {response.model} | レイテンシ: {response.latency_ms:.2f}ms | キャッシュ: {'✅' if response.cached else '❌'}
"""
            send_to_slack(reply_text, channel, thread_ts)
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Slack LLMチャットエラー: {e}")
        error = error_handler.handle_exception(
            e,
            context={"service": "Slack LLM Chat"},
            user_message="LLMチャットに失敗しました"
        )
        return jsonify({
            "status": "error",
            "error": error.user_message or str(e)
        }), 500


@app.route('/api/slack/command', methods=['POST'])
def slack_command():
    """Slack Slash Commands（/llm コマンド）"""
    if not LLM_CLIENT:
        return jsonify({
            "response_type": "ephemeral",
            "text": "❌ LLMクライアントが利用できません"
        })
    
    try:
        # Slack Slash Command形式
        text = request.form.get("text", "")
        user_id = request.form.get("user_id", "unknown")
        channel_id = request.form.get("channel_id", "general")
        user_name = request.form.get("user_name", "unknown")
        
        if not text:
            return jsonify({
                "response_type": "ephemeral",
                "text": "コマンドを入力してください。例: /llm こんにちは！"
            })
        
        logger.info(f"Slack Slash Command受信: {text} (User: {user_name})")
        
        # メッセージ解析
        parsed = parse_slack_message(text)
        
        # LLM呼び出し
        response = LLM_CLIENT.chat(
            parsed["text"],
            model=parsed["model"],
            task_type=parsed["task_type"]
        )
        
        # レスポンス生成
        return jsonify({
            "response_type": "in_channel",
            "text": response.response,
            "attachments": [
                {
                    "color": "good" if response.cached else "#36a64f",
                    "fields": [
                        {
                            "title": "モデル",
                            "value": response.model,
                            "short": True
                        },
                        {
                            "title": "レイテンシ",
                            "value": f"{response.latency_ms:.2f}ms",
                            "short": True
                        },
                        {
                            "title": "キャッシュ",
                            "value": "✅" if response.cached else "❌",
                            "short": True
                        }
                    ]
                }
            ]
        })
    
    except Exception as e:
        logger.error(f"Slack Slash Commandエラー: {e}")
        return jsonify({
            "response_type": "ephemeral",
            "text": f"❌ エラー: {str(e)}"
        })


@app.route('/api/slack/events', methods=['POST'])
def slack_events():
    """Slack Events API（Botメンション）"""
    if not LLM_CLIENT:
        return jsonify({"status": "error", "error": "LLM unavailable"}), 503
    
    data = request.get_json()
    
    # URL Verification Challenge
    if data.get("type") == "url_verification":
        return jsonify({"challenge": data.get("challenge")})
    
    # Event handling
    if data.get("type") == "event_callback":
        event = data.get("event", {})
        
        # Botメッセージは無視
        if event.get("bot_id"):
            return jsonify({"status": "ignored"})
        
        # メンションまたはDMのみ処理
        event_type = event.get("type")
        if event_type == "app_mention" or (event_type == "message" and event.get("channel_type") == "im"):
            text = event.get("text", "")
            user = event.get("user", "unknown")
            channel = event.get("channel", "general")
            thread_ts = event.get("ts")
            
            # Botメンションを除去
            if "<@" in text:
                parts = text.split(">")
                if len(parts) > 1:
                    text = ">".join(parts[1:]).strip()
            
            if text:
                logger.info(f"Slack Botメンション受信: {text[:50]}... (User: {user})")
                
                try:
                    # メッセージ解析
                    parsed = parse_slack_message(text)
                    
                    # LLM呼び出し
                    response = LLM_CLIENT.chat(
                        parsed["text"],
                        model=parsed["model"],
                        task_type=parsed["task_type"]
                    )
                    
                    # Slackに返信
                    reply_text = f"""🤖 LLM応答

{response.response}

---
モデル: {response.model} | レイテンシ: {response.latency_ms:.2f}ms | キャッシュ: {'✅' if response.cached else '❌'}
"""
                    send_to_slack(reply_text, channel, thread_ts)
                    
                except Exception as e:
                    logger.error(f"Slack Botメンション処理エラー: {e}")
                    send_to_slack(
                        f"❌ エラー: {str(e)}",
                        channel,
                        thread_ts
                    )
    
    return jsonify({"status": "ok"})


@app.route('/api/slack/webhook', methods=['POST'])
def slack_webhook():
    """Slack Incoming Webhook（汎用）"""
    if not LLM_CLIENT:
        return jsonify({"status": "error", "error": "LLM unavailable"}), 503
    
    data = request.get_json()
    
    text = data.get("text", "")
    user = data.get("user", "unknown")
    channel = data.get("channel", "general")
    
    if not text:
        return jsonify({"status": "error", "error": "text is required"}), 400
    
    logger.info(f"Slack Webhook LLMチャット: {text[:50]}... (User: {user})")
    
    try:
        # メッセージ解析
        parsed = parse_slack_message(text)
        
        # LLM呼び出し
        response = LLM_CLIENT.chat(
            parsed["text"],
            model=parsed["model"],
            task_type=parsed["task_type"]
        )
        
        return jsonify({
            "status": "success",
            "response": response.response,
            "model": response.model,
            "latency_ms": response.latency_ms,
            "cached": response.cached
        })
    
    except Exception as e:
        logger.error(f"Slack Webhook LLMチャットエラー: {e}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


if __name__ == '__main__':
    port = int(os.getenv("SLACK_LLM_PORT", 5115))
    logger.info(f"🎙️ Slack LLM Integration起動中... (ポート: {port})")
    logger.info(f"LLMクライアント: {'利用可能' if LLM_CLIENT else '利用不可'}")
    app.run(host='0.0.0.0', port=port, debug=os.getenv("DEBUG", "False").lower() == "true")

