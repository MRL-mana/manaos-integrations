"""
AI Model Hub - Web UI付きローカルLLMチャットインターフェース
ポート5080で動作するWBUUI（Web-Based User Interface）ローカルLLM
"""

from flask import Flask, render_template_string, request, jsonify, Response
from flask_cors import CORS
import os
import logging
import httpx
import json
import time
from typing import Dict, Any, Optional, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Ollama設定
OLLAMA_BASE_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "qwen2.5:3b")

# プロンプトテンプレート
PROMPT_TEMPLATES = {
    "chat": "{{message}}",
    "code_review": "以下のコードをレビューしてください。改善点、バグ、ベストプラクティスについてフィードバックをお願いします。\n\n```\n{{message}}\n```",
    "explain": "以下の内容について詳しく説明してください：\n\n{{message}}",
    "debug": "以下のエラーまたは問題をデバッグしてください：\n\n{{message}}",
    "translate": "以下のテキストを日本語に翻訳してください：\n\n{{message}}",
    "summarize": "以下のテキストを要約してください：\n\n{{message}}"
}

# 会話履歴管理（簡易版 - 本番環境ではRedisなどを推奨）
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
    stream: bool = False,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None
) -> Dict[str, Any]:
    """Ollamaとチャット"""
    url = f"{OLLAMA_BASE_URL}/api/chat"
    
    payload = {
        "model": model,
        "messages": messages,
        "stream": stream,
        "options": {
            "temperature": temperature
        }
    }
    
    if max_tokens:
        payload["options"]["num_predict"] = max_tokens
    
    try:
        if stream:
            # ストリーミング対応（将来実装）
            response = httpx.post(url, json=payload, timeout=60.0)
            return {"error": "ストリーミングは未実装です"}
        else:
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
    return render_template_string(HTML_TEMPLATE)


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
        logger.error(f"モデル取得エラー: {e}")
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
        template = data.get("template", "chat")
        temperature = float(data.get("temperature", 0.7))
        max_tokens = data.get("max_tokens")
        
        if not message:
            return jsonify({"error": "メッセージが空です"}), 400
        
        # テンプレート適用
        if template in PROMPT_TEMPLATES:
            prompt = PROMPT_TEMPLATES[template].replace("{{message}}", message)
        else:
            prompt = message
        
        # 会話履歴取得
        if session_id not in conversation_history:
            conversation_history[session_id] = []
        
        # メッセージ追加
        conversation_history[session_id].append({
            "role": "user",
            "content": prompt
        })
        
        # Ollama API呼び出し
        start_time = time.time()
        result = chat_with_ollama(
            model=model,
            messages=conversation_history[session_id],
            stream=False,
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
        
        # 会話履歴に追加
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
            "session_id": session_id
        })
        
    except Exception as e:
        logger.error(f"チャットAPIエラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/templates", methods=["GET"])
def get_templates():
    """プロンプトテンプレート一覧を取得"""
    templates = [
        {"id": "chat", "name": "通常チャット", "description": "通常の会話"},
        {"id": "code_review", "name": "コードレビュー", "description": "コードのレビューと改善提案"},
        {"id": "explain", "name": "説明", "description": "詳細な説明を求める"},
        {"id": "debug", "name": "デバッグ", "description": "エラーや問題のデバッグ"},
        {"id": "translate", "name": "翻訳", "description": "テキストの翻訳"},
        {"id": "summarize", "name": "要約", "description": "テキストの要約"}
    ]
    return jsonify({"templates": templates})


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


@app.route("/api/health", methods=["GET"])
def health():
    """ヘルスチェック"""
    try:
        # Ollama接続確認
        response = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=2.0)
        ollama_status = response.status_code == 200
        return jsonify({
            "status": "ok" if ollama_status else "degraded",
            "ollama_available": ollama_status,
            "ollama_url": OLLAMA_BASE_URL
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "ollama_available": False,
            "error": str(e)
        }), 503


# HTMLテンプレート
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Model Hub - ローカルLLMチャット</title>
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
            max-width: 1200px;
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
        
        .controls {
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
        }
        
        select, button {
            padding: 10px 15px;
            border: none;
            border-radius: 8px;
            font-size: 14px;
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
        }
        
        .message {
            margin-bottom: 20px;
            display: flex;
            flex-direction: column;
        }
        
        .message.user {
            align-items: flex-end;
        }
        
        .message.assistant {
            align-items: flex-start;
        }
        
        .message-content {
            max-width: 70%;
            padding: 15px 20px;
            border-radius: 18px;
            word-wrap: break-word;
            line-height: 1.6;
        }
        
        .message.user .message-content {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        
        .message.assistant .message-content {
            background: white;
            color: #333;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }
        
        .message-meta {
            font-size: 12px;
            color: #666;
            margin-top: 5px;
            padding: 0 5px;
        }
        
        .input-area {
            padding: 20px 30px;
            background: white;
            border-top: 1px solid #e0e0e0;
            display: flex;
            gap: 15px;
        }
        
        .template-select {
            width: 150px;
            padding: 12px;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            font-size: 14px;
        }
        
        .message-input {
            flex: 1;
            padding: 12px 15px;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            font-size: 14px;
            resize: none;
            min-height: 50px;
            max-height: 150px;
        }
        
        .send-button {
            padding: 12px 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
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
            background: #fee;
            color: #c33;
            padding: 15px;
            border-radius: 8px;
            margin: 20px;
            border-left: 4px solid #c33;
        }
        
        code {
            background: #f5f5f5;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
        }
        
        pre {
            background: #f5f5f5;
            padding: 15px;
            border-radius: 8px;
            overflow-x: auto;
            margin: 10px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧠 AI Model Hub</h1>
            <div class="controls">
                <select id="modelSelect">
                    <option value="">モデル読み込み中...</option>
                </select>
                <button onclick="clearHistory()">履歴クリア</button>
                <button onclick="checkHealth()">ヘルスチェック</button>
            </div>
        </div>
        
        <div class="chat-area" id="chatArea">
            <div class="message assistant">
                <div class="message-content">
                    <p>こんにちは！AI Model Hubへようこそ。</p>
                    <p>モデルを選択して、チャットを開始してください。</p>
                </div>
                <div class="message-meta">システム</div>
            </div>
        </div>
        
        <div class="loading" id="loading">
            <div class="spinner"></div>
            <div>応答を生成中...</div>
        </div>
        
        <div class="input-area">
            <select class="template-select" id="templateSelect">
                <option value="chat">通常チャット</option>
                <option value="code_review">コードレビュー</option>
                <option value="explain">説明</option>
                <option value="debug">デバッグ</option>
                <option value="translate">翻訳</option>
                <option value="summarize">要約</option>
            </select>
            <textarea 
                class="message-input" 
                id="messageInput" 
                placeholder="メッセージを入力..."
                onkeydown="handleKeyDown(event)"
            ></textarea>
            <button class="send-button" id="sendButton" onclick="sendMessage()">
                送信
            </button>
        </div>
    </div>
    
    <script>
        let sessionId = 'session_' + Date.now();
        let currentModel = '';
        
        // ページ読み込み時にモデル一覧を取得
        window.addEventListener('DOMContentLoaded', async () => {
            await loadModels();
            await loadTemplates();
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
        
        async function loadTemplates() {
            try {
                const response = await fetch('/api/templates');
                const data = await response.json();
                
                const select = document.getElementById('templateSelect');
                select.innerHTML = '';
                
                data.templates.forEach(template => {
                    const option = document.createElement('option');
                    option.value = template.id;
                    option.textContent = template.name;
                    option.title = template.description;
                    select.appendChild(option);
                });
            } catch (error) {
                console.error('テンプレート読み込みエラー:', error);
            }
        }
        
        async function sendMessage() {
            const input = document.getElementById('messageInput');
            const message = input.value.trim();
            const model = document.getElementById('modelSelect').value;
            const template = document.getElementById('templateSelect').value;
            
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
            
            // ローディング表示
            const loading = document.getElementById('loading');
            loading.classList.add('active');
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
                        session_id: sessionId,
                        template: template
                    })
                });
                
                const data = await response.json();
                
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
                showError('メッセージの送信に失敗しました: ' + error.message);
            } finally {
                loading.classList.remove('active');
                sendButton.disabled = false;
                input.focus();
            }
        }
        
        function addMessage(role, content, meta = {}) {
            const chatArea = document.getElementById('chatArea');
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${role}`;
            
            const contentDiv = document.createElement('div');
            contentDiv.className = 'message-content';
            
            // Markdownライクな処理（簡易版）
            const formattedContent = formatMessage(content);
            contentDiv.innerHTML = formattedContent;
            
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
            text = text.replace(/`([^`]+)`/g, '<code>$1</code>');
            text = text.replace(/```([^`]+)```/g, '<pre>$1</pre>');
            return text;
        }
        
        function showError(message) {
            const chatArea = document.getElementById('chatArea');
            const errorDiv = document.createElement('div');
            errorDiv.className = 'error';
            errorDiv.textContent = '❌ ' + message;
            chatArea.appendChild(errorDiv);
            chatArea.scrollTop = chatArea.scrollHeight;
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
                    sessionId = 'session_' + Date.now();
                    document.getElementById('chatArea').innerHTML = `
                        <div class="message assistant">
                            <div class="message-content">
                                <p>会話履歴をクリアしました。</p>
                            </div>
                            <div class="message-meta">システム</div>
                        </div>
                    `;
                } catch (error) {
                    console.error('履歴削除エラー:', error);
                    showError('履歴の削除に失敗しました');
                }
            }
        }
        
        async function checkHealth() {
            try {
                const response = await fetch('/api/health');
                const data = await response.json();
                
                if (data.ollama_available) {
                    alert('✅ 正常: Ollamaに接続できています');
                } else {
                    alert('⚠️ 警告: Ollamaに接続できません\nURL: ' + data.ollama_url);
                }
            } catch (error) {
                alert('❌ エラー: ヘルスチェックに失敗しました');
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
    port = int(os.getenv("PORT", 5080))
    logger.info(f"🧠 AI Model Hub起動中...")
    logger.info(f"   URL: http://localhost:{port}")
    logger.info(f"   Ollama URL: {OLLAMA_BASE_URL}")
    logger.info(f"   デフォルトモデル: {DEFAULT_MODEL}")
    
    app.run(host="0.0.0.0", port=port, debug=os.getenv("DEBUG", "False").lower() == "true")
