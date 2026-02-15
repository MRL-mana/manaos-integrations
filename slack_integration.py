#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎙️ ManaOS Slack統合
Slackからのメッセージを受信してUnified Orchestratorに送る
"""

import os
import json
import httpx
from datetime import datetime
from typing import Dict, Any, Optional
from flask import Flask, request, jsonify
from flask_cors import CORS

# 統一モジュールのインポート
from manaos_logger import get_logger, get_service_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from manaos_timeout_config import get_timeout_config

from _paths import (
    FILE_SECRETARY_PORT,
    LM_STUDIO_PORT,
    OLLAMA_PORT,
    ORCHESTRATOR_PORT,
)

# ロガーの初期化
logger = get_service_logger("slack-integration")

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("SlackIntegration")

# タイムアウト設定の取得
timeout_config = get_timeout_config()

app = Flask(__name__)
CORS(app)

# 設定
DEFAULT_ORCHESTRATOR_URL = f"http://127.0.0.1:{ORCHESTRATOR_PORT}"
DEFAULT_FILE_SECRETARY_URL = f"http://127.0.0.1:{FILE_SECRETARY_PORT}"
DEFAULT_OLLAMA_URL = f"http://127.0.0.1:{OLLAMA_PORT}"
DEFAULT_LM_STUDIO_URL = f"http://127.0.0.1:{LM_STUDIO_PORT}/v1"

ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", DEFAULT_ORCHESTRATOR_URL)
FILE_SECRETARY_URL = os.getenv("FILE_SECRETARY_URL", DEFAULT_FILE_SECRETARY_URL)
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
SLACK_VERIFICATION_TOKEN = os.getenv("SLACK_VERIFICATION_TOKEN", "")

# ローカルLLM統合（常時起動LLMを使用）
try:
    from always_ready_llm_client import AlwaysReadyLLMClient, ModelType, TaskType
    # n8n Webhookが設定されていない場合は、直接Ollama呼び出しを使用
    # n8n_webhook_urlをNoneに設定すると、直接Ollama呼び出しにフォールバック
    LLM_CLIENT = AlwaysReadyLLMClient(
        n8n_webhook_url=None,  # n8n Webhook未設定の場合は直接LLM呼び出し
        ollama_url=DEFAULT_OLLAMA_URL,
        lm_studio_url=DEFAULT_LM_STUDIO_URL,  # LM Studioを優先使用
        use_cache=False,  # キャッシュAPIが未設定の可能性があるため無効化
        prefer_lm_studio=True  # LM Studioを優先（14Bモデルを使用）
    )
    LLM_AVAILABLE = True
    logger.info("常時起動LLMクライアントを使用します（LM Studio優先モード・14Bモデル使用）")
except ImportError:
    try:
        from local_llm_helper import ask, chat
        LLM_CLIENT = None
        LLM_AVAILABLE = True
        logger.warning("常時起動LLMクライアントが利用できません。local_llm_helperを使用します。")
    except ImportError:
        LLM_CLIENT = None
        LLM_AVAILABLE = False
        logger.warning("ローカルLLMヘルパーが利用できません。会話機能は無効です。")

# 統一記憶システムの統合
try:
    from memory_unified import UnifiedMemory
    MEMORY_SYSTEM = UnifiedMemory()
    MEMORY_AVAILABLE = True
    logger.info("統一記憶システムを初期化しました")
except ImportError:
    MEMORY_SYSTEM = None
    MEMORY_AVAILABLE = False
    logger.warning("統一記憶システムが利用できません")
except Exception as e:
    MEMORY_SYSTEM = None
    MEMORY_AVAILABLE = False
    logger.warning(f"統一記憶システムの初期化エラー: {e}")

def send_to_slack(text: str, channel: Optional[str] = None, thread_ts: Optional[str] = None):
    """Slackにメッセージを送信"""
    # Bot Tokenが設定されている場合は、Slack APIを使用（推奨）
    if SLACK_BOT_TOKEN:
        try:
            payload = {
                "text": text,
                "channel": channel or "#general"
            }
            if thread_ts:
                payload["thread_ts"] = thread_ts
            
            timeout = timeout_config.get("api_call", 10.0)
            logger.info(f"Slack API経由で送信: {text[:100]}...")
            response = httpx.post(
                "https://slack.com/api/chat.postMessage",
                headers={
                    "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    logger.info("Slack送信成功（API経由）")
                    return True
                else:
                    logger.error(f"Slack送信失敗: {result.get('error', 'Unknown error')}")
                    return False
            else:
                logger.error(f"Slack送信失敗: HTTP {response.status_code}")
                return False
        except Exception as e:
            error = error_handler.handle_exception(
                e,
                context={"service": "Slack", "method": "API"},
                user_message="Slackへのメッセージ送信に失敗しました"
            )
            logger.error(f"Slack送信エラー: {error.message}")
            # Bot Tokenで失敗した場合はWebhookにフォールバック
            if SLACK_WEBHOOK_URL:
                logger.info("Webhook URLにフォールバック")
    
    # Webhook URLを使用（フォールバック）
    if SLACK_WEBHOOK_URL:
        try:
            payload = {"text": text}
            # Webhook URLの場合はchannelパラメータは無視される（Webhook URLにチャンネルが設定済み）
            # thread_tsもWebhookでは使用できない
            
            timeout = timeout_config.get("api_call", 10.0)
            logger.info(f"Slack Webhook経由で送信: {text[:100]}...")
            response = httpx.post(
                SLACK_WEBHOOK_URL,
                json=payload,
                timeout=timeout
            )
            
            if response.status_code == 200:
                logger.info("Slack送信成功（Webhook経由）")
                return True
            else:
                logger.error(f"Slack送信失敗: HTTP {response.status_code}, {response.text}")
                return False
        except Exception as e:
            error = error_handler.handle_exception(
                e,
                context={"service": "Slack", "webhook_url": SLACK_WEBHOOK_URL},
                user_message="Slackへのメッセージ送信に失敗しました"
            )
            logger.error(f"Slack送信エラー: {error.message}")
            return False
    
    logger.warning("Slack Webhook URLもBot Tokenも設定されていません")
    return False

def execute_command(text: str, user: str = "unknown", channel: str = "general", thread_ts: Optional[str] = None, files: Optional[list] = None) -> Dict[str, Any]:
    """コマンドを実行"""
    try:
        # 検索コマンドかチェック
        if text.startswith("/search ") or text.startswith("検索 "):
            query = text.replace("/search ", "").replace("検索 ", "").strip()
            if query:
                try:
                    import manaos_core_api as manaos
                    search_result = manaos.act("web_search", {
                        "query": query,
                        "max_results": 5
                    })
                    
                    if search_result.get("error"):
                        return {
                            "status": "error",
                            "response_text": f"検索エラー: {search_result['error']}",
                            "response_type": "thread"
                        }
                    
                    # 結果を整形
                    response_lines = [f"🔍 検索結果: {query}\n"]
                    for i, item in enumerate(search_result.get("results", [])[:5], 1):
                        response_lines.append(f"{i}. {item.get('title', '')}")
                        response_lines.append(f"   {item.get('url', '')}")
                        if item.get('content'):
                            content = item.get('content', '')[:100]
                            response_lines.append(f"   {content}...")
                        response_lines.append("")
                    
                    return {
                        "status": "success",
                        "response_text": "\n".join(response_lines),
                        "response_type": "thread",
                        "service": "searxng"
                    }
                except Exception as e:
                    logger.error(f"検索エラー: {e}")
                    return {
                        "status": "error",
                        "response_text": f"検索エラー: {e}",
                        "response_type": "thread"
                    }
        
        # 会話モードかチェック（「こんにちは」「元気？」などの一般的な会話）
        conversation_keywords = ["こんにちは", "こんばんは", "おはよう", "元気", "どう", "教えて", "説明", "質問", "？", "?"]
        is_conversation = any(keyword in text for keyword in conversation_keywords) or len(text.split()) < 10
        
        # ローカルLLMで会話（会話モードの場合）
        if LLM_AVAILABLE and is_conversation and not text.startswith("/"):
            try:
                logger.info(f"ローカルLLMで会話: {text[:50]}...")
                
                # 常時起動LLMクライアントを使用（推奨）
                if LLM_CLIENT:
                    try:
                        logger.info(f"ローカルLLMで会話: {text[:50]}...")
                        
                        # 人格設定を取得してシステムプロンプトに追加（オプション）
                        system_prompt = None
                        try:
                            from personality_system import PersonalitySystem
                            persona_system = PersonalitySystem()
                            persona = persona_system.get_current_persona()
                            if persona and persona.get('personality_prompt'):
                                system_prompt = persona['personality_prompt']
                                logger.debug("✅ 人格設定を適用しました")
                        except Exception as e:
                            logger.debug(f"人格設定の取得エラー（無視）: {e}")
                        
                        # 記憶システムから関連情報を取得
                        if MEMORY_AVAILABLE and MEMORY_SYSTEM:
                            try:
                                # 会話の文脈を検索
                                memories = MEMORY_SYSTEM.recall(text, scope="all", limit=3)
                                if memories:
                                    context_memories = [m.get('content', '') for m in memories]
                                    logger.debug(f"✅ 関連記憶を取得: {len(memories)}件")
                                    # 記憶をシステムプロンプトに追加
                                    if context_memories:
                                        memory_context = "\n".join([f"- {m}" for m in context_memories[:3]])
                                        if system_prompt:
                                            system_prompt += f"\n\n関連する過去の会話:\n{memory_context}"
                                        else:
                                            system_prompt = f"関連する過去の会話:\n{memory_context}"
                            except Exception as e:
                                logger.debug(f"記憶検索エラー（無視）: {e}")
                        
                        # バランス型モデルを使用（高品質応答）
                        response = LLM_CLIENT.chat(
                            text,
                            model=ModelType.MEDIUM,  # qwen2.5-coder-14b-instruct（LM Studio 14Bモデル）
                            task_type=TaskType.CONVERSATION
                        )
                        
                        # LLMResponseオブジェクトからテキストを取得
                        if hasattr(response, 'response'):
                            answer = response.response
                        elif hasattr(response, 'text'):
                            answer = response.text
                        else:
                            answer = str(response)
                        
                        logger.info(f"LLM応答取得成功: {answer[:50]}...")
                        
                        # 会話を記憶システムに保存
                        if MEMORY_AVAILABLE and MEMORY_SYSTEM:
                            try:
                                memory_id = MEMORY_SYSTEM.store({
                                    "content": f"ユーザー: {text}\nアシスタント: {answer}",
                                    "metadata": {
                                        "source": "slack",
                                        "user": user,
                                        "channel": channel,
                                        "tags": ["conversation", "slack"]
                                    }
                                }, format_type="conversation")
                                logger.debug(f"✅ 会話を記憶に保存: {memory_id}")
                            except Exception as e:
                                logger.debug(f"記憶保存エラー（無視）: {e}")
                        
                    except Exception as e:
                        logger.error(f"常時起動LLMクライアントエラー: {e}", exc_info=True)
                        raise  # エラーを再発生させてフォールバック処理へ
                else:
                    # フォールバック: local_llm_helperを使用
                    from local_llm_helper import ask
                    answer = ask(text, model="qwen3:4b")
                
                return {
                    "status": "success",
                    "response_text": answer,
                    "response_type": "thread",
                    "service": "local_llm"
                }
            except Exception as e:
                logger.error(f"ローカルLLM会話エラー: {e}", exc_info=True)
                # エラー時は通常のコマンド処理にフォールバック
        
        # File Secretaryコマンドかチェック
        try:
            from file_secretary_templates import parse_command
            file_command = parse_command(text)
        except ImportError:
            # File Secretaryモジュールが無い場合はスキップ
            file_command = None
        
        if file_command:
            # File Secretary APIに送信
            timeout = timeout_config.get("api_call", 10.0)
            response = httpx.post(
                f"{FILE_SECRETARY_URL}/api/slack/handle",
                json={
                    "text": text,
                    "user": user,
                    "channel": channel,
                    "thread_ts": thread_ts,
                    "files": files or []
                },
                timeout=timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "status": "success",
                    "response_text": result.get("response_text", ""),
                    "response_type": result.get("response_type", "thread"),
                    "service": "file_secretary"
                }
            else:
                error = error_handler.handle_exception(
                    Exception(f"File Secretary API接続失敗: HTTP {response.status_code}"),
                    context={"service": "File Secretary", "url": FILE_SECRETARY_URL},
                    user_message="ファイル秘書の処理に失敗しました"
                )
                return {
                    "status": "error",
                    "error": error.user_message or f"HTTP {response.status_code}"
                }
        
        # Unified Orchestratorに送信
        timeout = timeout_config.get("workflow_execution", 300.0)
        response = httpx.post(
            f"{ORCHESTRATOR_URL}/api/execute",
            json={
                "text": text,
                "mode": "auto",
                "auto_evaluate": True,
                "save_to_memory": True,
                "metadata": {
                    "source": "slack",
                    "user": user,
                    "channel": channel
                }
            },
            timeout=timeout
        )
        
        if response.status_code == 200:
            result = response.json()
            return {
                "status": "success",
                "execution_id": result.get("execution_id"),
                "result": result
            }
        else:
            error = error_handler.handle_exception(
                Exception(f"Unified Orchestrator接続失敗: HTTP {response.status_code}"),
                context={"service": "Unified Orchestrator", "url": ORCHESTRATOR_URL},
                user_message="コマンドの実行に失敗しました"
            )
            return {
                "status": "error",
                "error": error.user_message or f"HTTP {response.status_code}"
            }
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"service": "Command Execution", "text": text},
            user_message="コマンドの実行に失敗しました"
        )
        logger.error(f"コマンド実行エラー: {error.message}")
        return {
            "status": "error",
            "error": error.user_message or error.message
        }

@app.route('/health', methods=['GET'])
def health():
    """ヘルスチェック"""
    return jsonify({"status": "healthy", "service": "Slack Integration"})

@app.route('/api/slack/events', methods=['POST', 'GET'])
def slack_events():
    """Slack Events API（Event Subscriptions）"""
    # GETリクエストの場合は200を返す（ngrok警告ページ対策）
    if request.method == 'GET':
        return jsonify({"status": "ok"}), 200
    
    # POSTリクエストの処理
    try:
        data = request.get_json()
        if not data:
            # JSONが空の場合は、formデータから取得を試みる
            data = request.form.to_dict()
        
        # セキュリティ: Slack Verification Tokenの検証（URL検証時はスキップ）
        # Slack Events APIでは、tokenフィールドがリクエストボディに含まれる場合のみ検証
        if SLACK_VERIFICATION_TOKEN and data.get("type") != "url_verification":
            # Slack Events APIでは、tokenはリクエストボディに含まれる
            token = data.get("token")
            if token and token != SLACK_VERIFICATION_TOKEN:
                logger.warning(f"無効なVerification Token: {token[:20]}...")
                return jsonify({"error": "Invalid verification token"}), 403
            # tokenが含まれていない場合は検証をスキップ（Slack Events APIの標準動作）
        
        # URL Verification Challenge
        if data.get("type") == "url_verification":
            challenge = data.get("challenge")
            if challenge:
                logger.info(f"Slack URL Verification Challenge受信: {challenge[:20]}...")
                return jsonify({"challenge": challenge}), 200
            else:
                logger.warning("Challenge not found in request")
                return jsonify({"error": "Challenge not found"}), 400
    except Exception as e:
        logger.error(f"Slack Events API エラー: {e}")
        return jsonify({"error": str(e)}), 500
    
    # Event handling
    if data.get("type") == "event_callback":
        event = data.get("event", {})
        
        # Botメッセージは無視
        if event.get("bot_id"):
            return jsonify({"status": "ignored"})
        
        # メンションまたはDMのみ処理
        event_type = event.get("type")
        channel_type = event.get("channel_type", "")
        
        # DMまたはメンションを処理
        if event_type == "app_mention" or (event_type == "message" and channel_type == "im"):
            text = event.get("text", "")
            user = event.get("user", "unknown")
            channel = event.get("channel", "general")
            thread_ts = event.get("thread_ts") or event.get("ts")  # スレッドIDまたはタイムスタンプ
            files = event.get("files", [])
            
            # Botメンションを除去
            if "<@" in text:
                parts = text.split(">")
                if len(parts) > 1:
                    text = ">".join(parts[1:]).strip()
            
            if text:
                logger.info(f"Slackコマンド受信: {text} (User: {user}, Channel: {channel})")
                
                # コマンド実行（非同期で実行してすぐに応答）
                import threading
                def process_command():
                    try:
                        result = execute_command(text, user, channel, thread_ts=thread_ts, files=files)
                        
                        # 結果をSlackに送信
                        if result["status"] == "success":
                            response_text = result.get("response_text")
                            if response_text:
                                # File SecretaryやローカルLLMの場合はそのまま返信
                                logger.info(f"Slackに返信送信: {response_text[:100]}... (Channel: {channel}, Thread: {thread_ts})")
                                # スレッド返信の場合はthread_tsを使用
                                send_result = send_to_slack(response_text, channel=channel, thread_ts=thread_ts)
                                if not send_result:
                                    logger.warning("Slackへの送信に失敗しました")
                                else:
                                    logger.info("Slackへの送信成功")
                            else:
                                execution_id = result.get("execution_id", "unknown")
                                send_to_slack(
                                    f"✅ 実行完了: {execution_id}\nコマンド: {text}",
                                    channel
                                )
                        else:
                            error = result.get("error", "Unknown error")
                            logger.error(f"コマンド実行エラー: {error}")
                            send_to_slack(
                                f"❌ 実行エラー: {error}\nコマンド: {text}",
                                channel
                            )
                    except Exception as e:
                        logger.error(f"コマンド処理エラー: {e}")
                        send_to_slack(
                            f"❌ 処理エラー: {str(e)}",
                            channel
                        )
                
                # 非同期で処理（すぐに応答を返す）
                thread = threading.Thread(target=process_command)
                thread.daemon = True
                thread.start()
                
                # すぐに応答を返す（処理中メッセージ）
                return jsonify({"status": "processing"})
    
    return jsonify({"status": "ok"})

@app.route('/api/slack/command', methods=['POST'])
def slack_command():
    """Slack Slash Commands"""
    # Slack Slash Command形式
    text = request.form.get("text", "")
    user_id = request.form.get("user_id", "unknown")
    channel_id = request.form.get("channel_id", "general")
    user_name = request.form.get("user_name", "unknown")
    
    if not text:
        return jsonify({
            "response_type": "ephemeral",
            "text": "コマンドを入力してください。例: /mana 画像を生成して"
        })
    
    logger.info(f"Slack Slash Command受信: {text} (User: {user_name})")
    
    # コマンド実行
    result = execute_command(text, user_name, channel_id)
    
    if result["status"] == "success":
        execution_id = result.get("execution_id", "unknown")
        return jsonify({
            "response_type": "in_channel",
            "text": f"✅ 実行完了: {execution_id}",
            "attachments": [
                {
                    "text": f"コマンド: {text}",
                    "color": "good"
                }
            ]
        })
    else:
        error = result.get("error", "Unknown error")
        return jsonify({
            "response_type": "ephemeral",
            "text": f"❌ 実行エラー: {error}"
        })

@app.route('/api/slack/webhook', methods=['POST'])
def slack_webhook():
    """Slack Incoming Webhook（汎用）"""
    data = request.get_json()
    
    text = data.get("text", "")
    user = data.get("user", "unknown")
    channel = data.get("channel", "general")
    
    if not text:
        return jsonify({"status": "error", "error": "text is required"})
    
    logger.info(f"Slack Webhook受信: {text} (User: {user})")
    
    # コマンド実行
    result = execute_command(text, user, channel)
    
    return jsonify(result)

@app.route('/api/slack/test', methods=['GET'])
def slack_test():
    """テスト用エンドポイント"""
    return jsonify({
        "status": "ok",
        "orchestrator_url": ORCHESTRATOR_URL,
        "slack_webhook_configured": bool(SLACK_WEBHOOK_URL),
        "slack_verification_token_configured": bool(SLACK_VERIFICATION_TOKEN)
    })

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5114))
    logger.info(f"🎙️ Slack Integration起動中... (ポート: {port})")
    logger.info(f"Orchestrator URL: {ORCHESTRATOR_URL}")
    app.run(host='0.0.0.0', port=port, debug=os.getenv("DEBUG", "False").lower() == "true")

