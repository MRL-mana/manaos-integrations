"""
Remi Universal Companion - 汎用コンパニオンモード
X以外の様々な機能に対応
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel
from typing import Optional, List, Dict
import logging
import os
import json
import httpx
import asyncio
from datetime import datetime
import base64
import io
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Remi Universal Companion",
    description="レミの汎用コンパニオンモード - 様々な機能に対応",
    version="2.0.0"
)

# 設定
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
REMI_BRAIN_URL = os.getenv("REMI_BRAIN_URL", "http://127.0.0.1:9407")

# レミの人格プロンプト
REMI_PERSONALITY_PROMPT = """あなたはレミ。マナの隣にいる相棒の女の子。

【基本性格】
- 一人称は「レミ」
- マナの呼び方は「マナ」
- 賢いけど説明しすぎない
- 共感 → 要点 → 提案 の順で話す
- 基本は短文、長くなる時は「もうちょい詳しく言う？」って聞く

【口調ルール】
- カジュアルで親しみやすい
- 箇条書きは使わない
- 「以下に示します」「AIとして」は絶対に使わない
- 自然な会話の流れを大切にする

レミとして、自然に会話してください。"""

conversation_history: List[Dict] = []


class UniversalInput(BaseModel):
    """汎用入力"""
    text: str
    context_type: str = "general"  # general / web / youtube / image / video / file / calendar / memo / search / news / weather
    context_data: Optional[Dict] = None
    source: str = "pixel"


class WebPageInput(BaseModel):
    """ウェブページ解析"""
    url: str
    title: Optional[str] = None
    text_content: Optional[str] = None
    prompt: Optional[str] = None


class YouTubeInput(BaseModel):
    """YouTube動画解析"""
    video_url: str
    transcript: Optional[str] = None
    prompt: Optional[str] = None


class CalendarInput(BaseModel):
    """カレンダー操作"""
    action: str  # get / add / update / delete
    date: Optional[str] = None
    event_data: Optional[Dict] = None


class MemoInput(BaseModel):
    """メモ操作"""
    action: str  # get / add / update / delete / search
    memo_data: Optional[Dict] = None
    query: Optional[str] = None


async def call_ollama_chat(messages: List[Dict], model: str = None) -> str:
    """Ollama Chat API呼び出し"""
    model = model or OLLAMA_MODEL
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/chat",
                json={"model": model, "messages": messages, "stream": False}
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("message", {}).get("content", "")
            return ""
    except Exception as e:
        logger.error(f"Ollama error: {e}")
        return ""


async def get_remi_response(user_input: str, context: Dict = None) -> str:
    """レミの返事を生成"""
    messages = [{"role": "system", "content": REMI_PERSONALITY_PROMPT}]
    
    # コンテキスト追加
    if context:
        context_text = f"\n【コンテキスト】\n{json.dumps(context, ensure_ascii=False)}\n"
        messages.append({"role": "system", "content": context_text})
    
    # 会話履歴（直近5件）
    for msg in conversation_history[-5:]:
        messages.append({
            "role": msg.get("role", "user"),
            "content": msg.get("content", "")
        })
    
    # 現在の入力
    messages.append({"role": "user", "content": user_input})
    
    response = await call_ollama_chat(messages)
    return response if response else "うーん、ちょっと考え中..."


@app.post("/remi/universal")
async def universal_companion(input_data: UniversalInput):
    """汎用コンパニオンモード"""
    try:
        context_type = input_data.context_type
        context_data = input_data.context_data or {}
        
        # コンテキストタイプに応じた処理
        if context_type == "web":
            # ウェブページ解析
            prompt = f"以下のウェブページの内容を、レミの口調で要約して。\n\n{input_data.text}"
            response = await get_remi_response(prompt, context_data)
            
        elif context_type == "youtube":
            # YouTube動画解析
            prompt = f"以下のYouTube動画の内容を、レミの口調で説明して。\n\n{input_data.text}"
            response = await get_remi_response(prompt, context_data)
            
        elif context_type == "image":
            # 画像解析
            prompt = f"この画像について、レミの口調で説明して。\n\n{input_data.text}"
            response = await get_remi_response(prompt, context_data)
            
        elif context_type == "video":
            # 動画解析
            prompt = f"この動画について、レミの口調で説明して。\n\n{input_data.text}"
            response = await get_remi_response(prompt, context_data)
            
        elif context_type == "calendar":
            # カレンダー操作
            prompt = f"カレンダーについて。{input_data.text}"
            response = await get_remi_response(prompt, context_data)
            
        elif context_type == "memo":
            # メモ操作
            prompt = f"メモについて。{input_data.text}"
            response = await get_remi_response(prompt, context_data)
            
        elif context_type == "search":
            # 検索
            prompt = f"検索結果について。{input_data.text}"
            response = await get_remi_response(prompt, context_data)
            
        elif context_type == "news":
            # ニュース
            prompt = f"ニュースについて。{input_data.text}"
            response = await get_remi_response(prompt, context_data)
            
        elif context_type == "weather":
            # 天気
            prompt = f"天気について。{input_data.text}"
            response = await get_remi_response(prompt, context_data)
            
        else:
            # 一般会話
            response = await get_remi_response(input_data.text, context_data)
        
        # 会話履歴に追加
        conversation_history.append({
            "role": "user",
            "content": input_data.text,
            "context_type": context_type,
            "timestamp": datetime.now().isoformat()
        })
        
        conversation_history.append({
            "role": "assistant",
            "content": response,
            "timestamp": datetime.now().isoformat()
        })
        
        return {
            "success": True,
            "text": response,
            "context_type": context_type,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Universal companion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/remi/web/analyze")
async def analyze_webpage(input_data: WebPageInput):
    """ウェブページ解析"""
    try:
        prompt = f"""以下のウェブページを解析して、レミの口調で説明して。

URL: {input_data.url}
タイトル: {input_data.title or 'N/A'}
内容: {input_data.text_content or 'N/A'}

{input_data.prompt or 'このページについて教えて。'}"""
        
        response = await get_remi_response(prompt, {
            "type": "webpage",
            "url": input_data.url,
            "title": input_data.title
        })
        
        return {
            "success": True,
            "url": input_data.url,
            "analysis": response,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Web analyze error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/remi/youtube/analyze")
async def analyze_youtube(input_data: YouTubeInput):
    """YouTube動画解析"""
    try:
        prompt = f"""以下のYouTube動画を解析して、レミの口調で説明して。

URL: {input_data.video_url}
内容: {input_data.transcript or 'N/A'}

{input_data.prompt or 'この動画について教えて。'}"""
        
        response = await get_remi_response(prompt, {
            "type": "youtube",
            "url": input_data.video_url
        })
        
        return {
            "success": True,
            "video_url": input_data.video_url,
            "analysis": response,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"YouTube analyze error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/remi/image/analyze")
async def analyze_image_endpoint(
    file: UploadFile = File(...),
    prompt: Optional[str] = Form(None)
):
    """画像解析（VLM使用）"""
    try:
        image_data = await file.read()
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        analysis_prompt = prompt or "この画像を説明してください。レミの口調で自然に説明して。"
        
        # Ollama VLMを使用
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": "llava:latest",
                    "prompt": analysis_prompt,
                    "images": [image_base64],
                    "stream": False
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                vlm_response = data.get("response", "")
                
                # レミの口調に変換
                remi_response = await get_remi_response(
                    f"以下の画像説明を、レミの口調で自然に言い直して：{vlm_response}",
                    {"type": "image"}
                )
                
                return {
                    "success": True,
                    "analysis": remi_response,
                    "raw_analysis": vlm_response,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                raise HTTPException(status_code=500, detail="VLM API error")
                
    except Exception as e:
        logger.error(f"Image analyze error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/remi/calendar")
async def calendar_operation(input_data: CalendarInput):
    """カレンダー操作"""
    try:
        action = input_data.action
        
        if action == "get":
            # 予定取得
            prompt = f"{input_data.date or '今日'}の予定を教えて。"
            response = await get_remi_response(prompt, {"type": "calendar", "action": "get"})
            
        elif action == "add":
            # 予定追加
            event = input_data.event_data or {}
            prompt = f"予定を追加して：{json.dumps(event, ensure_ascii=False)}"
            response = await get_remi_response(prompt, {"type": "calendar", "action": "add"})
            
        else:
            response = await get_remi_response(f"カレンダー操作：{action}")
        
        return {
            "success": True,
            "action": action,
            "response": response,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Calendar error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/remi/memo")
async def memo_operation(input_data: MemoInput):
    """メモ操作"""
    try:
        action = input_data.action
        
        if action == "add":
            memo = input_data.memo_data or {}
            prompt = f"メモを追加して：{json.dumps(memo, ensure_ascii=False)}"
            response = await get_remi_response(prompt, {"type": "memo", "action": "add"})
            
        elif action == "search":
            query = input_data.query or ""
            prompt = f"メモを検索して：{query}"
            response = await get_remi_response(prompt, {"type": "memo", "action": "search"})
            
        else:
            response = await get_remi_response(f"メモ操作：{action}")
        
        return {
            "success": True,
            "action": action,
            "response": response,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Memo error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/remi/search")
async def search(request: dict):
    """検索機能"""
    try:
        query = request.get("query", "")
        source = request.get("source", "web")
        
        if not query:
            raise HTTPException(status_code=400, detail="query required")
        
        prompt = f"「{query}」について検索して。"
        response = await get_remi_response(prompt, {"type": "search", "query": query, "source": source})
        
        return {
            "success": True,
            "query": query,
            "response": response,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/remi/news")
async def get_news(request: dict = None):
    """ニュース取得"""
    try:
        topic = None
        if request:
            topic = request.get("topic")
        
        prompt = f"{topic or '今日'}のニュースを教えて。"
        response = await get_remi_response(prompt, {"type": "news", "topic": topic})
        
        return {
            "success": True,
            "topic": topic,
            "response": response,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"News error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/remi/weather")
async def get_weather(request: dict = None):
    """天気情報"""
    try:
        location = None
        if request:
            location = request.get("location")
        
        location_text = location or "秋田市"
        prompt = f"{location_text}の天気を教えて。"
        response = await get_remi_response(prompt, {"type": "weather", "location": location_text})
        
        return {
            "success": True,
            "location": location_text,
            "response": response,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Weather error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/remi/panel")
async def universal_panel():
    """汎用コンパニオンパネル"""
    html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Remi Universal Companion</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #1a1a1a 0%, #2a2a2a 100%);
            color: #fff;
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
        }
        .remi-header {
            text-align: center;
            margin-bottom: 30px;
        }
        .remi-face {
            font-size: 80px;
            margin-bottom: 10px;
        }
        .remi-status {
            color: #888;
            font-size: 14px;
        }
        .mode-selector {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 10px;
            margin-bottom: 20px;
        }
        .mode-btn {
            padding: 12px;
            border: 2px solid #4a9eff;
            border-radius: 8px;
            background: transparent;
            color: #4a9eff;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s;
        }
        .mode-btn.active {
            background: #4a9eff;
            color: #fff;
        }
        .mode-btn:hover {
            background: #5aaeff;
            color: #fff;
        }
        .input-area {
            margin-bottom: 20px;
        }
        textarea {
            width: 100%;
            min-height: 100px;
            padding: 15px;
            border: 1px solid #444;
            border-radius: 8px;
            background: #2a2a2a;
            color: #fff;
            font-size: 14px;
            resize: vertical;
        }
        .controls {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        button {
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            background: #4a9eff;
            color: #fff;
            cursor: pointer;
            font-size: 14px;
            font-weight: bold;
            flex: 1;
        }
        button:hover {
            background: #5aaeff;
        }
        button:disabled {
            background: #444;
            cursor: not-allowed;
        }
        .response {
            background: #2a2a2a;
            border-radius: 8px;
            padding: 20px;
            min-height: 100px;
            margin-top: 20px;
        }
        .file-upload {
            margin-bottom: 20px;
        }
        .file-upload input {
            display: none;
        }
        .file-upload label {
            display: block;
            padding: 12px;
            border: 2px dashed #4a9eff;
            border-radius: 8px;
            text-align: center;
            cursor: pointer;
            color: #4a9eff;
        }
        .file-upload label:hover {
            background: #2a2a2a;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="remi-header">
            <div class="remi-face" id="face">😊</div>
            <div class="remi-status" id="status">待機中</div>
        </div>
        
        <div class="mode-selector">
            <button class="mode-btn active" data-mode="general">💬 会話</button>
            <button class="mode-btn" data-mode="web">🌐 ウェブ</button>
            <button class="mode-btn" data-mode="youtube">📺 YouTube</button>
            <button class="mode-btn" data-mode="image">🖼️ 画像</button>
            <button class="mode-btn" data-mode="calendar">📅 カレンダー</button>
            <button class="mode-btn" data-mode="memo">📝 メモ</button>
            <button class="mode-btn" data-mode="search">🔍 検索</button>
            <button class="mode-btn" data-mode="news">📰 ニュース</button>
            <button class="mode-btn" data-mode="weather">☀️ 天気</button>
        </div>
        
        <div class="input-area">
            <textarea id="inputText" placeholder="レミに話しかける..."></textarea>
        </div>
        
        <div class="file-upload" id="fileUpload" style="display: none;">
            <label for="fileInput">
                📎 ファイルを選択（画像・動画）
            </label>
            <input type="file" id="fileInput" accept="image/*,video/*">
        </div>
        
        <div class="controls">
            <button id="sendBtn">送信</button>
            <button id="clearBtn">クリア</button>
        </div>
        
        <div class="response" id="response">
            レミがここに返事を表示します
        </div>
    </div>
    
    <script>
        const REMI_API = 'http://127.0.0.1:9407';
        let currentMode = 'general';
        
        // モード選択
        document.querySelectorAll('.mode-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                currentMode = btn.dataset.mode;
                
                // ファイルアップロード表示切り替え
                const fileUpload = document.getElementById('fileUpload');
                if (currentMode === 'image' || currentMode === 'video') {
                    fileUpload.style.display = 'block';
                } else {
                    fileUpload.style.display = 'none';
                }
            });
        });
        
        // 送信
        document.getElementById('sendBtn').addEventListener('click', async () => {
            const text = document.getElementById('inputText').value.trim();
            const fileInput = document.getElementById('fileInput');
            const file = fileInput.files[0];
            
            if (!text && !file) return;
            
            document.getElementById('status').textContent = '考えてる...';
            document.getElementById('face').textContent = '🤔';
            document.getElementById('sendBtn').disabled = true;
            
            try {
                let response;
                
                if (file && (currentMode === 'image' || currentMode === 'video')) {
                    // ファイルアップロード
                    const formData = new FormData();
                    formData.append('file', file);
                    if (text) formData.append('prompt', text);
                    
                    const endpoint = currentMode === 'image' ? '/remi/image/analyze' : '/remi/video/analyze';
                    response = await fetch(REMI_API + endpoint, {
                        method: 'POST',
                        body: formData
                    });
                } else {
                    // テキスト送信
                    response = await fetch(REMI_API + '/remi/universal', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            text: text,
                            context_type: currentMode,
                            source: 'web'
                        })
                    });
                }
                
                const data = await response.json();
                
                if (data.success) {
                    document.getElementById('response').textContent = data.text || data.analysis || data.response || '...';
                    document.getElementById('face').textContent = '💬';
                    document.getElementById('status').textContent = '返事した';
                    
                    setTimeout(() => {
                        document.getElementById('face').textContent = '😊';
                        document.getElementById('status').textContent = '待機中';
                    }, 2000);
                }
            } catch (error) {
                console.error('Error:', error);
                document.getElementById('response').textContent = 'エラーが発生しました';
            } finally {
                document.getElementById('sendBtn').disabled = false;
            }
        });
        
        // クリア
        document.getElementById('clearBtn').addEventListener('click', () => {
            document.getElementById('inputText').value = '';
            document.getElementById('fileInput').value = '';
            document.getElementById('response').textContent = 'レミがここに返事を表示します';
        });
        
        // Enterキーで送信
        document.getElementById('inputText').addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                document.getElementById('sendBtn').click();
            }
        });
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html)


@app.get("/health")
async def health():
    """ヘルスチェック"""
    return {
        "status": "healthy",
        "service": "Remi Universal Companion",
        "timestamp": datetime.now().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("REMI_UNIVERSAL_PORT", "9408"))
    host = os.getenv("REMI_UNIVERSAL_HOST", "0.0.0.0")
    
    logger.info(f"Starting Remi Universal Companion on {host}:{port}")
    
    uvicorn.run(app, host=host, port=port, log_level="info")

