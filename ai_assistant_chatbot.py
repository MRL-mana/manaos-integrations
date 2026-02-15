"""
AI Assistant Chatbot - シンプルなチャットUI
ポート5074で動作するSocket.IO対応チャットインターフェース
"""

from flask import Flask, render_template_string, request, jsonify
from flask_cors import CORS
import os
import logging
import httpx
import time
from typing import Dict, Any, Optional, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Ollama設定
OLLAMA_BASE_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
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
    """メインWeb UI"""
    return render_template_string(CHATBOT_HTML)


@app.route("/api/models", methods=["GET"])
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


@app.route("/api/chat", methods=["POST"])
def chat():
    """チャットAPI"""
    try:
        data = request.json
        message = data.get("message", "")
        model = data.get("model", DEFAULT_MODEL)
        session_id = data.get("session_id", "default")
        temperature = float(data.get("temperature", 0.7))
        max_tokens = data.get("max_tokens")
        
        if not message:
            return jsonify({"error": "メッセージが空です"}), 400
        
        # 会話履歴取得
        if session_id not in conversation_history:
            conversation_history[session_id] = []
        
        # メッセージ追加
        conversation_history[session_id].append({
            "role": "user",
            "content": message
        })
        
        # Ollama API呼び出し
        start_time = time.time()
        result = chat_with_ollama(
            model=model,
            messages=conversation_history[session_id],
            temperature=temperature,
            max_tokens=max_tokens
        )
        latency_ms = int((time.time() - start_time) * 1000)
        
        if "error" in result:
            # エラーの場合は会話履歴からユーザーメッセージを削除
            if conversation_history[session_id] and conversation_history[session_id][-1]["role"] == "user":
                conversation_history[session_id].pop()
            
            return jsonify({
                "error": result["error"],
                "latency_ms": latency_ms
            }), 500
        
        # 応答を取得
        assistant_message = result.get("message", {}).get("content", "")
        
        # 会話履歴に追加
        conversation_history[session_id].append({
            "role": "assistant",
            "content": assistant_message
        })
        
        # 履歴が長すぎる場合は古いものから削除（最大30メッセージ）
        if len(conversation_history[session_id]) > 30:
            conversation_history[session_id] = conversation_history[session_id][-30:]
        
        return jsonify({
            "status": "ok",
            "response": assistant_message,
            "model": model,
            "latency_ms": latency_ms,
            "session_id": session_id
        })
        
    except Exception as e:
        logger.error(f"チャットAPIエラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/status", methods=["GET"])
def get_status():
    """ステータス確認"""
    try:
        # Ollama確認
        response = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=2.0)
        ollama_status = response.status_code == 200
        
        return jsonify({
            "status": "ok",
            "ollama_available": ollama_status,
            "ollama_url": OLLAMA_BASE_URL,
            "active_sessions": len(conversation_history)
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "ollama_available": False,
            "error": str(e)
        }), 503


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
CHATBOT_HTML = """<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Assistant Chatbot</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        
        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            width: 100%;
            max-width: 800px;
            height: 90vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .header h1 {
            font-size: 24px;
            font-weight: 600;
        }
        
        .header-controls {
            display: flex;
            gap: 10px;
            align-items: center;
        }
        
        select, button {
            padding: 8px 12px;
            border: none;
            border-radius: 6px;
            font-size: 13px;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        select {
            background: rgba(255, 255, 255, 0.2);
            color: white;
            backdrop-filter: blur(10px);
        }
        
        select option {
            background: #667eea;
            color: white;
        }
        
        button {
            background: rgba(255, 255, 255, 0.3);
            color: white;
            font-weight: 500;
        }
        
        button:hover {
            background: rgba(255, 255, 255, 0.4);
            transform: translateY(-2px);
        }
        
        .chat-area {
            flex: 1;
            overflow-y: auto;
            padding: 30px;
            background: #f5f7fa;
            display: flex;
            flex-direction: column;
            gap: 15px;
        }
        
        .message {
            max-width: 75%;
            padding: 12px 18px;
            border-radius: 18px;
            word-wrap: break-word;
            line-height: 1.6;
            animation: fadeIn 0.3s ease-in;
        }
        
        @keyframes fadeIn {
            from {
                opacity: 0;
                transform: translateY(10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .message.user {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            align-self: flex-end;
            border-bottom-right-radius: 4px;
        }
        
        .message.assistant {
            background: white;
            color: #333;
            align-self: flex-start;
            border-bottom-left-radius: 4px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }
        
        .message-meta {
            font-size: 11px;
            color: rgba(255, 255, 255, 0.8);
            margin-top: 6px;
        }
        
        .message.assistant .message-meta {
            color: #999;
        }
        
        .input-area {
            padding: 20px 30px;
            background: white;
            border-top: 1px solid #e0e0e0;
            display: flex;
            gap: 10px;
        }
        
        .message-input {
            flex: 1;
            padding: 12px 15px;
            border: 2px solid #e0e0e0;
            border-radius: 12px;
            font-size: 14px;
            resize: none;
            min-height: 50px;
            max-height: 150px;
            font-family: inherit;
            transition: border-color 0.3s;
        }
        
        .message-input:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .send-button {
            padding: 12px 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 12px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            align-self: flex-end;
        }
        
        .send-button:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
        
        .send-button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        
        .loading {
            display: none;
            padding: 20px;
            text-align: center;
            color: #666;
        }
        
        .loading.active {
            display: block;
        }
        
        .typing-indicator {
            display: inline-flex;
            gap: 4px;
            padding: 12px 18px;
            background: white;
            border-radius: 18px;
            border-bottom-left-radius: 4px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            align-self: flex-start;
            max-width: 75px;
        }
        
        .typing-indicator span {
            width: 8px;
            height: 8px;
            background: #667eea;
            border-radius: 50%;
            animation: typing 1.4s infinite;
        }
        
        .typing-indicator span:nth-child(2) {
            animation-delay: 0.2s;
        }
        
        .typing-indicator span:nth-child(3) {
            animation-delay: 0.4s;
        }
        
        @keyframes typing {
            0%, 60%, 100% {
                transform: translateY(0);
                opacity: 0.7;
            }
            30% {
                transform: translateY(-10px);
                opacity: 1;
            }
        }
        
        .error {
            background: #ffebee;
            color: #c62828;
            padding: 12px 18px;
            border-radius: 18px;
            border-left: 4px solid #c62828;
            max-width: 75%;
            align-self: center;
        }
        
        .status-indicator {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 6px;
        }
        
        .status-indicator.online {
            background: #4caf50;
            box-shadow: 0 0 6px rgba(76, 175, 80, 0.6);
        }
        
        .status-indicator.offline {
            background: #f44336;
            box-shadow: 0 0 6px rgba(244, 67, 54, 0.6);
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>💬 AI Assistant Chatbot</h1>
            <div class="header-controls">
                <select id="modelSelect">
                    <option value="">モデル読み込み中...</option>
                </select>
                <button onclick="clearHistory()">履歴クリア</button>
                <button onclick="checkStatus()">
                    <span class="status-indicator offline" id="statusIndicator"></span>
                    ステータス
                </button>
            </div>
        </div>
        
        <div class="chat-area" id="chatArea">
            <div class="message assistant">
                <div>こんにちは！AI Assistant Chatbotへようこそ。</div>
                <div class="message-meta">システム - モデルを選択してチャットを開始してください</div>
            </div>
        </div>
        
        <div class="input-area">
            <textarea 
                class="message-input" 
                id="messageInput" 
                placeholder="メッセージを入力... (Enterで送信、Shift+Enterで改行)"
                onkeydown="handleKeyDown(event)"
            ></textarea>
            <button class="send-button" id="sendButton" onclick="sendMessage()">
                送信
            </button>
        </div>
    </div>
    
    <script>
        let sessionId = 'chatbot_' + Date.now();
        let currentModel = '';
        let typingIndicator = null;
        
        // ページ読み込み時にモデル一覧を取得
        window.addEventListener('DOMContentLoaded', async () => {
            await loadModels();
            await checkStatus();
            setInterval(checkStatus, 30000); // 30秒ごとにステータス確認
        });
        
        async function loadModels() {
            try {
                const response = await fetch('/api/models');
                const data = await response.json();
                
                const select = document.getElementById('modelSelect');
                select.innerHTML = '';
                
                if (data.models && data.models.length > 0) {
                    data.models.forEach(model => {
                        const option = document.createElement('option');
                        option.value = model;
                        option.textContent = model;
                        if (model === data.default) {
                            option.selected = true;
                            currentModel = model;
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
                showError('モデルの読み込みに失敗しました');
            }
        }
        
        async function sendMessage() {
            const input = document.getElementById('messageInput');
            const message = input.value.trim();
            const model = document.getElementById('modelSelect').value;
            
            if (!message) {
                return;
            }
            
            if (!model) {
                showError('モデルを選択してください');
                return;
            }
            
            // ユーザーメッセージを表示
            addMessage('user', message);
            input.value = '';
            
            // タイピングインジケーター表示
            showTypingIndicator();
            
            // ボタン無効化
            const sendButton = document.getElementById('sendButton');
            sendButton.disabled = true;
            
            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        message: message,
                        model: model,
                        session_id: sessionId
                    })
                });
                
                const data = await response.json();
                
                // タイピングインジケーター非表示
                hideTypingIndicator();
                
                if (data.error) {
                    showError(data.error);
                } else {
                    addMessage('assistant', data.response, {
                        model: data.model,
                        latency: data.latency_ms
                    });
                }
            } catch (error) {
                console.error('チャットエラー:', error);
                hideTypingIndicator();
                showError('メッセージの送信に失敗しました: ' + error.message);
            } finally {
                sendButton.disabled = false;
                input.focus();
            }
        }
        
        function addMessage(role, content, meta = {}) {
            const chatArea = document.getElementById('chatArea');
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${role}`;
            
            const contentDiv = document.createElement('div');
            // 簡易Markdown処理
            contentDiv.innerHTML = formatMessage(content);
            
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
            
            messageDiv.appendChild(contentDiv);
            messageDiv.appendChild(metaDiv);
            chatArea.appendChild(messageDiv);
            
            // スクロールを最下部に
            chatArea.scrollTop = chatArea.scrollHeight;
        }
        
        function formatMessage(text) {
            // 簡易Markdown変換
            text = text.replace(/\n/g, '<br>');
            text = text.replace(/`([^`]+)`/g, '<code style="background: rgba(0,0,0,0.1); padding: 2px 6px; border-radius: 4px;">$1</code>');
            text = text.replace(/```([^`]+)```/g, '<pre style="background: rgba(0,0,0,0.05); padding: 10px; border-radius: 6px; overflow-x: auto; margin-top: 8px;">$1</pre>');
            return text;
        }
        
        function showTypingIndicator() {
            const chatArea = document.getElementById('chatArea');
            typingIndicator = document.createElement('div');
            typingIndicator.className = 'typing-indicator';
            typingIndicator.innerHTML = '<span></span><span></span><span></span>';
            chatArea.appendChild(typingIndicator);
            chatArea.scrollTop = chatArea.scrollHeight;
        }
        
        function hideTypingIndicator() {
            if (typingIndicator) {
                typingIndicator.remove();
                typingIndicator = null;
            }
        }
        
        function showError(message) {
            const chatArea = document.getElementById('chatArea');
            const errorDiv = document.createElement('div');
            errorDiv.className = 'error';
            errorDiv.textContent = '❌ ' + message;
            chatArea.appendChild(errorDiv);
            chatArea.scrollTop = chatArea.scrollHeight;
            
            // 3秒後に自動削除
            setTimeout(() => {
                errorDiv.remove();
            }, 5000);
        }
        
        function handleKeyDown(event) {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                sendMessage();
            }
        }
        
        async function clearHistory() {
            if (confirm('会話履歴を削除しますか？')) {
                try {
                    await fetch(`/api/history/${sessionId}`, {
                        method: 'DELETE'
                    });
                    sessionId = 'chatbot_' + Date.now();
                    document.getElementById('chatArea').innerHTML = `
                        <div class="message assistant">
                            <div>会話履歴をクリアしました。新しい会話を開始してください。</div>
                            <div class="message-meta">システム</div>
                        </div>
                    `;
                } catch (error) {
                    console.error('履歴削除エラー:', error);
                    showError('履歴の削除に失敗しました');
                }
            }
        }
        
        async function checkStatus() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                
                const indicator = document.getElementById('statusIndicator');
                if (data.ollama_available) {
                    indicator.className = 'status-indicator online';
                } else {
                    indicator.className = 'status-indicator offline';
                }
            } catch (error) {
                console.error('ステータス確認エラー:', error);
                const indicator = document.getElementById('statusIndicator');
                indicator.className = 'status-indicator offline';
            }
        }
        
        // モデル選択変更時の処理
        document.getElementById('modelSelect').addEventListener('change', (e) => {
            currentModel = e.target.value;
        });
    </script>
</body>
</html>
"""


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5074))
    logger.info(f"💬 AI Assistant Chatbot起動中...")
    logger.info(f"   URL: http://127.0.0.1:{port}")
    logger.info(f"   Ollama URL: {OLLAMA_BASE_URL}")
    logger.info(f"   デフォルトモデル: {DEFAULT_MODEL}")
    
    app.run(host="0.0.0.0", port=port, debug=os.getenv("DEBUG", "False").lower() == "true")
