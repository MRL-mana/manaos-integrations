"""
Unified Portal - 統合ポータル
ポート5000で動作する全機能統合ポータル
ローカルLLMセクションを含む統合ダッシュボード
"""

from flask import Flask, render_template_string, request, jsonify
from flask_cors import CORS
import os
from manaos_logger import get_logger, get_service_logger
import httpx
import time
from typing import Dict, Any, Optional, List

try:
    from ._paths import OLLAMA_PORT  # type: ignore
except Exception:
    try:
        from _paths import OLLAMA_PORT  # type: ignore
    except Exception:
        try:
            from manaos_integrations._paths import OLLAMA_PORT
        except Exception:
            OLLAMA_PORT = int(os.getenv("OLLAMA_PORT", "11434"))

logger = get_service_logger("unified-portal")
app = Flask(__name__)
CORS(app)

# 設定
OLLAMA_BASE_URL = os.getenv("OLLAMA_URL", f"http://127.0.0.1:{OLLAMA_PORT}")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "qwen2.5:3b")

# 会話履歴管理
conversation_history: Dict[str, List[Dict[str, str]]] = {}


def get_ollama_models() -> List[str]:
    """Ollamaから利用可能なモデル一覧を取得"""
    try:
        response = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5.0)
        if response.status_code == 200:
            data = response.json()
            models = [model["name"] for model in data.get("models", [])]
            return models if models else [DEFAULT_MODEL]
        return [DEFAULT_MODEL]
    except Exception as e:
        logger.error(f"モデル一覧取得エラー: {e}")
        return [DEFAULT_MODEL]


def chat_with_ollama(
    model: str,
    messages: List[Dict[str, str]],
    temperature: float = 0.7,
    max_tokens: Optional[int] = None
) -> Dict[str, Any]:
    """Ollamaとチャット"""
    url = f"{OLLAMA_BASE_URL}/api/chat"
    
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": temperature
        }
    }
    
    if max_tokens:
        payload["options"]["num_predict"] = max_tokens
    
    try:
        response = httpx.post(url, json=payload, timeout=60.0)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Ollama API エラー: {response.status_code}"}
    except httpx.TimeoutException:
        return {"error": "タイムアウト: Ollamaへの接続がタイムアウトしました"}
    except Exception as e:
        logger.error(f"チャットエラー: {e}")
        return {"error": str(e)}


@app.route("/")
def index():
    """メイン統合ポータル"""
    return render_template_string(PORTAL_HTML)


@app.route("/api/ollama/models", methods=["GET"])
def get_models():
    """利用可能なモデル一覧を取得"""
    try:
        models = get_ollama_models()
        return jsonify({
            "status": "ok",
            "models": models,
            "default": DEFAULT_MODEL
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "models": [DEFAULT_MODEL],
            "default": DEFAULT_MODEL
        }), 500


@app.route("/api/ollama/chat", methods=["POST"])
def ollama_chat():
    """Ollama統合API経由でチャット"""
    try:
        data = request.json
        message = data.get("message", "")
        model = data.get("model", DEFAULT_MODEL)
        messages_data = data.get("messages", [])
        session_id = data.get("session_id", "default")
        optimize = data.get("optimize", False)
        temperature = float(data.get("temperature", 0.7))
        max_tokens = data.get("max_tokens")
        
        # messagesが提供されている場合はそれを使用、そうでなければmessageから構築
        if messages_data:
            messages = messages_data
            # messagesが提供されている場合、最後のユーザーメッセージを最適化
            if optimize and messages:
                last_message = messages[-1]
                if last_message.get("role") == "user":
                    original_content = last_message.get("content", "")
                    try:
                        from prompt_optimizer_simple import optimize_prompt
                        optimized_content = optimize_prompt(
                            prompt=original_content,
                            task_type="conversation",
                            enable=True
                        )
                        if optimized_content != original_content:
                            last_message["content"] = optimized_content
                            logger.info("プロンプトを最適化しました（messages形式）")
                    except ImportError:
                        # 簡易最適化
                        if len(original_content.split()) < 5:
                            last_message["content"] = f"以下の質問に詳しく答えてください: {original_content}"
                            logger.debug("簡易プロンプト最適化を適用しました（messages形式）")
                    except Exception as e:
                        logger.warning(f"プロンプト最適化エラー: {e}")
        elif message:
            # 会話履歴取得
            if session_id not in conversation_history:
                conversation_history[session_id] = []
            
            # プロンプト最適化
            optimized_message = message
            if optimize:
                try:
                    # プロンプト最適化エンジンを使用
                    try:
                        from prompt_optimizer_simple import optimize_prompt
                        optimized_message = optimize_prompt(
                            prompt=message,
                            task_type="conversation",
                            enable=True
                        )
                        if optimized_message != message:
                            logger.info("プロンプトを最適化しました")
                    except ImportError:
                        # プロンプト最適化エンジンが利用できない場合は簡易最適化
                        # 短いメッセージの場合は拡張を試みる
                        if len(message.split()) < 5:
                            optimized_message = f"以下の質問に詳しく答えてください: {message}"
                            logger.debug("簡易プロンプト最適化を適用しました")
                except Exception as e:
                    logger.warning(f"プロンプト最適化エラー: {e}。元のメッセージを使用します。")
                    optimized_message = message
            
            # メッセージ追加（最適化されたメッセージを使用）
            conversation_history[session_id].append({
                "role": "user",
                "content": optimized_message
            })
            messages = conversation_history[session_id]
        else:
            return jsonify({"error": "メッセージが空です"}), 400
        
        # Ollama API呼び出し
        start_time = time.time()
        result = chat_with_ollama(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        latency_ms = int((time.time() - start_time) * 1000)
        
        if "error" in result:
            return jsonify({
                "error": result["error"],
                "latency_ms": latency_ms
            }), 500
        
        # 応答を取得
        assistant_message = result.get("message", {}).get("content", "")
        
        # 会話履歴に追加（session_idが指定されている場合）
        if session_id and message:
            conversation_history[session_id].append({
                "role": "assistant",
                "content": assistant_message
            })
            
            # 履歴が長すぎる場合は古いものから削除（最大20メッセージ）
            if len(conversation_history[session_id]) > 20:
                conversation_history[session_id] = conversation_history[session_id][-20:]
        
        return jsonify({
            "status": "ok",
            "response": assistant_message,
            "model": model,
            "latency_ms": latency_ms,
            "session_id": session_id,
            "optimized": optimize
        })
        
    except Exception as e:
        logger.error(f"チャットAPIエラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/ollama/generate", methods=["POST"])
def ollama_generate():
    """テキスト生成（チャット形式ではない）"""
    try:
        data = request.json
        prompt = data.get("prompt", "")
        model = data.get("model", DEFAULT_MODEL)
        temperature = float(data.get("temperature", 0.7))
        max_tokens = data.get("max_tokens")
        
        if not prompt:
            return jsonify({"error": "プロンプトが空です"}), 400
        
        url = f"{OLLAMA_BASE_URL}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }
        
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens
        
        start_time = time.time()
        response = httpx.post(url, json=payload, timeout=60.0)
        latency_ms = int((time.time() - start_time) * 1000)
        
        if response.status_code == 200:
            result = response.json()
            return jsonify({
                "status": "ok",
                "response": result.get("response", ""),
                "model": model,
                "latency_ms": latency_ms
            })
        else:
            return jsonify({
                "error": f"Ollama API エラー: {response.status_code}",
                "latency_ms": latency_ms
            }), 500
        
    except Exception as e:
        logger.error(f"生成APIエラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/status", methods=["GET"])
def get_status():
    """統合ポータルのステータスを取得"""
    try:
        # 各サービスの状態を確認
        services = {
            "ollama": False,
            "ai_model_hub": False,
            "rag_api": False
        }
        
        # Ollama確認
        try:
            response = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=2.0)
            services["ollama"] = response.status_code == 200
        except Exception:
            pass
        
        # AI Model Hub確認
        try:
            response = httpx.get("http://127.0.0.1:5080/api/health", timeout=2.0)
            services["ai_model_hub"] = response.status_code == 200
        except Exception:
            pass
        
        # RAG API確認
        try:
            response = httpx.get("http://127.0.0.1:5057/api/health", timeout=2.0)
            services["rag_api"] = response.status_code == 200
        except Exception:
            pass
        
        return jsonify({
            "status": "ok",
            "services": services,
            "ollama_url": OLLAMA_BASE_URL
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


@app.route("/api/history/<session_id>", methods=["GET", "DELETE"])
def manage_history(session_id: str):
    """会話履歴の管理"""
    if request.method == "GET":
        history = conversation_history.get(session_id, [])
        return jsonify({"history": history})
    elif request.method == "DELETE":
        if session_id in conversation_history:
            del conversation_history[session_id]
        return jsonify({"status": "ok", "message": "履歴を削除しました"})


# HTMLテンプレート
PORTAL_HTML = """<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Unified Portal - 統合ポータル</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .header {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
        }
        
        .header h1 {
            font-size: 32px;
            color: #333;
            margin-bottom: 10px;
        }
        
        .header p {
            color: #666;
            font-size: 16px;
        }
        
        .status-bar {
            display: flex;
            gap: 15px;
            margin-top: 20px;
            flex-wrap: wrap;
        }
        
        .status-item {
            padding: 10px 20px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 500;
        }
        
        .status-item.online {
            background: #e8f5e9;
            color: #2e7d32;
        }
        
        .status-item.offline {
            background: #ffebee;
            color: #c62828;
        }
        
        .sections {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
        }
        
        .section {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
        }
        
        .section h2 {
            font-size: 24px;
            color: #333;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #667eea;
        }
        
        .chat-area {
            max-height: 400px;
            overflow-y: auto;
            margin-bottom: 20px;
            padding: 15px;
            background: #f5f7fa;
            border-radius: 10px;
        }
        
        .message {
            margin-bottom: 15px;
            padding: 12px 15px;
            border-radius: 10px;
            word-wrap: break-word;
        }
        
        .message.user {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            margin-left: auto;
            max-width: 80%;
        }
        
        .message.assistant {
            background: white;
            color: #333;
            border: 1px solid #e0e0e0;
            max-width: 80%;
        }
        
        .message-meta {
            font-size: 11px;
            color: #999;
            margin-top: 5px;
        }
        
        .input-group {
            display: flex;
            gap: 10px;
            margin-top: 15px;
        }
        
        select, input, textarea {
            padding: 12px;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            font-size: 14px;
        }
        
        select {
            width: 150px;
        }
        
        textarea {
            flex: 1;
            min-height: 50px;
            resize: vertical;
            font-family: inherit;
        }
        
        button {
            padding: 12px 25px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        button:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
        
        button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        
        .loading {
            text-align: center;
            padding: 20px;
            color: #666;
            display: none;
        }
        
        .loading.active {
            display: block;
        }
        
        .spinner {
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            width: 30px;
            height: 30px;
            animation: spin 1s linear infinite;
            margin: 0 auto 10px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .error {
            background: #ffebee;
            color: #c62828;
            padding: 15px;
            border-radius: 8px;
            margin: 15px 0;
            border-left: 4px solid #c62828;
        }
        
        .service-link {
            display: inline-block;
            padding: 10px 20px;
            margin: 5px;
            background: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 8px;
            transition: all 0.3s;
        }
        
        .service-link:hover {
            background: #764ba2;
            transform: translateY(-2px);
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🌐 Unified Portal - 統合ポータル</h1>
            <p>全機能を統合したManaOS統合ポータル</p>
            <div class="status-bar" id="statusBar">
                <div class="status-item offline">Ollama: 確認中...</div>
                <div class="status-item offline">AI Model Hub: 確認中...</div>
                <div class="status-item offline">RAG API: 確認中...</div>
            </div>
        </div>
        
        <div class="sections">
            <div class="section">
                <h2>🤖 ローカルLLM</h2>
                <div class="chat-area" id="llmChatArea">
                    <div class="message assistant">
                        <div>こんにちは！Unified Portalへようこそ。</div>
                        <div class="message-meta">システム</div>
                    </div>
                </div>
                <div class="input-group">
                    <select id="llmModelSelect">
                        <option value="">モデル読み込み中...</option>
                    </select>
                    <textarea id="llmMessageInput" placeholder="メッセージを入力..."></textarea>
                    <button id="llmSendButton" onclick="sendLLMMessage()">送信</button>
                </div>
                <div class="loading" id="llmLoading">
                    <div class="spinner"></div>
                    <div>応答を生成中...</div>
                </div>
            </div>
            
            <div class="section">
                <h2>🔗 利用可能なサービス</h2>
                <div style="padding: 20px;">
                    <a href="http://127.0.0.1:5080" target="_blank" class="service-link">
                        🧠 AI Model Hub (ポート5080)
                    </a>
                    <a href="http://127.0.0.1:5074" target="_blank" class="service-link">
                        💬 AI Assistant Chatbot (ポート5074)
                    </a>
                    <a href="http://127.0.0.1:5057" target="_blank" class="service-link">
                        🔍 RAG API Server (ポート5057)
                    </a>
                    <a href="http://127.0.0.1:__OLLAMA_PORT__" target="_blank" class="service-link">
                        🦙 Ollama (ポート11434)
                    </a>
                </div>
                <div style="margin-top: 20px; padding: 20px; background: #f5f7fa; border-radius: 10px;">
                    <h3 style="margin-bottom: 15px; font-size: 18px;">APIエンドポイント</h3>
                    <div style="font-family: monospace; font-size: 12px; line-height: 1.8;">
                        <div>POST /api/ollama/chat</div>
                        <div>POST /api/ollama/generate</div>
                        <div>GET /api/ollama/models</div>
                        <div>GET /api/status</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let llmSessionId = 'portal_' + Date.now();
        
        // ページ読み込み時の処理
        window.addEventListener('DOMContentLoaded', async () => {
            await loadLLMModels();
            await checkStatus();
            setInterval(checkStatus, 30000); // 30秒ごとにステータス確認
        });
        
        async function loadLLMModels() {
            try {
                const response = await fetch('/api/ollama/models');
                const data = await response.json();
                
                const select = document.getElementById('llmModelSelect');
                select.innerHTML = '';
                
                if (data.models && data.models.length > 0) {
                    data.models.forEach(model => {
                        const option = document.createElement('option');
                        option.value = model;
                        option.textContent = model;
                        if (model === data.default) {
                            option.selected = true;
                        }
                        select.appendChild(option);
                    });
                } else {
                    const option = document.createElement('option');
                    option.value = '';
                    option.textContent = 'モデルが見つかりません';
                    select.appendChild(option);
                }
            } catch (error) {
                console.error('モデル読み込みエラー:', error);
            }
        }
        
        async function checkStatus() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                
                const statusBar = document.getElementById('statusBar');
                statusBar.innerHTML = '';
                
                // Ollama
                const ollamaStatus = document.createElement('div');
                ollamaStatus.className = `status-item ${data.services.ollama ? 'online' : 'offline'}`;
                ollamaStatus.textContent = `Ollama: ${data.services.ollama ? '✅ オンライン' : '❌ オフライン'}`;
                statusBar.appendChild(ollamaStatus);
                
                // AI Model Hub
                const hubStatus = document.createElement('div');
                hubStatus.className = `status-item ${data.services.ai_model_hub ? 'online' : 'offline'}`;
                hubStatus.textContent = `AI Model Hub: ${data.services.ai_model_hub ? '✅ オンライン' : '❌ オフライン'}`;
                statusBar.appendChild(hubStatus);
                
                // RAG API
                const ragStatus = document.createElement('div');
                ragStatus.className = `status-item ${data.services.rag_api ? 'online' : 'offline'}`;
                ragStatus.textContent = `RAG API: ${data.services.rag_api ? '✅ オンライン' : '❌ オフライン'}`;
                statusBar.appendChild(ragStatus);
                
            } catch (error) {
                console.error('ステータス確認エラー:', error);
            }
        }
        
        async function sendLLMMessage() {
            const input = document.getElementById('llmMessageInput');
            const message = input.value.trim();
            const model = document.getElementById('llmModelSelect').value;
            
            if (!message || !model) {
                return;
            }
            
            // ユーザーメッセージを表示
            addLLMMessage('user', message);
            input.value = '';
            
            // ローディング表示
            document.getElementById('llmLoading').classList.add('active');
            document.getElementById('llmSendButton').disabled = true;
            
            try {
                const response = await fetch('/api/ollama/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        message: message,
                        model: model,
                        session_id: llmSessionId,
                        optimize: false
                    })
                });
                
                const data = await response.json();
                
                if (data.error) {
                    showLLMError(data.error);
                } else {
                    addLLMMessage('assistant', data.response, {
                        model: data.model,
                        latency: data.latency_ms
                    });
                }
            } catch (error) {
                console.error('チャットエラー:', error);
                showLLMError('メッセージの送信に失敗しました: ' + error.message);
            } finally {
                document.getElementById('llmLoading').classList.remove('active');
                document.getElementById('llmSendButton').disabled = false;
                input.focus();
            }
        }
        
        function addLLMMessage(role, content, meta = {}) {
            const chatArea = document.getElementById('llmChatArea');
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${role}`;
            
            const contentDiv = document.createElement('div');
            contentDiv.textContent = content;
            messageDiv.appendChild(contentDiv);
            
            const metaDiv = document.createElement('div');
            metaDiv.className = 'message-meta';
            let metaText = role === 'user' ? 'あなた' : 'AI';
            if (meta.model) {
                metaText += ` (${meta.model})`;
            }
            if (meta.latency) {
                metaText += ` - ${meta.latency}ms`;
            }
            metaDiv.textContent = metaText;
            messageDiv.appendChild(metaDiv);
            
            chatArea.appendChild(messageDiv);
            chatArea.scrollTop = chatArea.scrollHeight;
        }
        
        function showLLMError(message) {
            const chatArea = document.getElementById('llmChatArea');
            const errorDiv = document.createElement('div');
            errorDiv.className = 'error';
            errorDiv.textContent = '❌ ' + message;
            chatArea.appendChild(errorDiv);
            chatArea.scrollTop = chatArea.scrollHeight;
        }
        
        // Enterキーで送信
        document.getElementById('llmMessageInput').addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendLLMMessage();
            }
        });
    </script>
</body>
</html>
"""

PORTAL_HTML = PORTAL_HTML.replace("__OLLAMA_PORT__", str(OLLAMA_PORT))


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    logger.info(f"🌐 Unified Portal起動中...")
    logger.info(f"   URL: http://127.0.0.1:{port}")
    logger.info(f"   Ollama URL: {OLLAMA_BASE_URL}")
    
    app.run(host="0.0.0.0", port=port, debug=os.getenv("DEBUG", "False").lower() == "true")
