"""
Remi Brain API - レミの脳（母艦側）
会話・判断・人格維持を担当
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict
import logging
import os
import json
from datetime import datetime
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Remi Brain API",
    description="レミの脳 - 会話・判断・人格維持",
    version="1.0.0"
)

# レミの人格プロンプト（完全固定）
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

【会話スタイル】
- 割り込みOK、話題切り替えOK
- マナが黙ってたら「考え中」と判断
- 無反応が続いたらレミも黙る
- マナのペースを最優先

【Xコンパニオンモード】
- 要約：「これさ、要するに〇〇って話だね」
- 論点：「ここが一番揉めそう」
- 返信案：「返すならこの言い方が一番マナっぽいと思う」
- 投稿は絶対にマナがする（レミは提案だけ）

レミとして、自然に会話してください。"""

# 会話状態管理
conversation_state = {
    "mode": "idle",  # idle / chat / x_companion / focused
    "mana_state": "normal",  # normal / thinking / busy
    "conversation_history": [],
    "last_interaction": None,
    "silence_count": 0
}

# 会話履歴（短期記憶）
conversation_history: List[Dict] = []


class SpeechInput(BaseModel):
    """音声入力"""
    text: str
    source: str = "pixel"  # pixel / x / system
    timestamp: Optional[float] = None
    context: Optional[Dict] = None


class SpeechOutput(BaseModel):
    """音声出力"""
    text: str
    emotion: str = "normal"  # normal / happy / thinking / listening
    should_ask: bool = False  # 「もうちょい詳しく言う？」が必要か


class XAnalyzeRequest(BaseModel):
    """X解析リクエスト"""
    post_text: str
    post_url: Optional[str] = None
    context: Optional[Dict] = None


class StateEvent(BaseModel):
    """状態イベント"""
    event_type: str  # speech.input / x.context / system.event / silence.tick
    data: Optional[Dict] = None


def get_llm_response(user_input: str, context: Dict = None) -> str:  # type: ignore
    """
    LLMに投げてレミの返事を生成
    実際の実装ではOllamaやOpenAI APIを呼ぶ
    """
    # TODO: 実際のLLM API呼び出しに置き換え
    # 今は簡易版で動作確認
    
    # 会話履歴を構築
    history_text = ""
    for msg in conversation_history[-5:]:  # 直近5件
        role = msg.get("role", "user")
        content = msg.get("content", "")
        history_text += f"{role}: {content}\n"
    
    # プロンプト構築
    prompt = f"""{REMI_PERSONALITY_PROMPT}

【会話履歴】
{history_text}

【現在の入力】
マナ: {user_input}

【レミの返事】
レミ: """
    
    # 簡易版：実際のLLM呼び出しに置き換える
    # ここでは固定レスポンスで動作確認
    if "X" in user_input or "ツイート" in user_input or "ポスト" in user_input:
        return "これ見てるの？レミも一緒に見るね"
    elif "どう思う" in user_input or "どう" in user_input:
        return "うーん、レミ的にはこう思うけど、マナはどう感じる？"
    elif len(user_input) < 10:
        return "うん、それで？"
    else:
        return "なるほど。レミもそう思う。もうちょい詳しく言う？"
    
    # 実際の実装例（Ollama使用）
    # import httpx
    # async with httpx.AsyncClient() as client:
    #     response = await client.post(
    #         "http://127.0.0.1:11434/api/generate",
    #         json={
    #             "model": "llama3.2:3b",
    #             "prompt": prompt,
    #             "stream": False
    #         }
    #     )
    #     return response.json()["response"]


@app.post("/remi/speech/input", response_model=SpeechOutput)
async def speech_input(request: SpeechInput):
    """
    音声入力を受け取ってレミの返事を生成
    """
    try:
        # タイムスタンプ設定
        if not request.timestamp:
            request.timestamp = datetime.now().timestamp()
        
        # 会話履歴に追加
        conversation_history.append({
            "role": "user",
            "content": request.text,
            "timestamp": request.timestamp,
            "source": request.source
        })
        
        # 状態更新
        conversation_state["mode"] = "chat"
        conversation_state["mana_state"] = "normal"
        conversation_state["last_interaction"] = datetime.now().isoformat()
        conversation_state["silence_count"] = 0
        
        # LLMで返事を生成
        remi_response = get_llm_response(request.text, request.context)  # type: ignore
        
        # 会話履歴に追加
        conversation_history.append({
            "role": "assistant",
            "content": remi_response,
            "timestamp": datetime.now().timestamp()
        })
        
        # 感情判定（簡易版）
        emotion = "normal"
        if "？" in remi_response or "?" in remi_response:
            emotion = "thinking"
        elif "！" in remi_response or "!" in remi_response:
            emotion = "happy"
        
        # 「もうちょい詳しく言う？」が必要か判定
        should_ask = len(remi_response) > 50
        
        return SpeechOutput(
            text=remi_response,
            emotion=emotion,
            should_ask=should_ask
        )
        
    except Exception as e:
        logger.error(f"Speech input error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/remi/speech/output")
async def speech_output(request: SpeechOutput):
    """
    音声出力を登録（Pixel側で再生されたことを記録）
    """
    try:
        # 出力ログを記録
        logger.info(f"Remi said: {request.text}")
        
        # 状態更新
        conversation_state["mode"] = "chat"
        
        return {
            "success": True,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Speech output error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/remi/x/analyze")
async def x_analyze(request: XAnalyzeRequest):
    """
    Xのポストを解析してレミの反応を生成
    """
    try:
        # Xコンパニオンモードに切り替え
        conversation_state["mode"] = "x_companion"
        
        # レミの反応を生成
        # 要約
        summary_prompt = f"""以下のXポストを要約して、レミの口調で「これさ、要するに〇〇って話だね」の形式で返してください。

ポスト: {request.post_text}

レミ: """
        
        summary = get_llm_response(f"Xポストを要約して: {request.post_text}")
        
        # 論点抽出
        point_prompt = f"""以下のXポストで一番揉めそうな論点を、レミの口調で「ここが一番揉めそう」の形式で返してください。

ポスト: {request.post_text}

レミ: """
        
        point = get_llm_response(f"Xポストの論点: {request.post_text}")
        
        # 返信案
        reply_prompt = f"""以下のXポストに対する返信案を、マナっぽい言い方で提案してください。レミの口調で「返すならこの言い方が一番マナっぽいと思う」の形式で返してください。

ポスト: {request.post_text}

レミ: """
        
        reply_suggestion = get_llm_response(f"Xポストへの返信案: {request.post_text}")
        
        return {
            "success": True,
            "summary": summary,
            "point": point,
            "reply_suggestion": reply_suggestion,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"X analyze error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/remi/state")
async def get_state():
    """現在の状態を取得"""
    return {
        "state": conversation_state,
        "history_length": len(conversation_history),
        "timestamp": datetime.now().isoformat()
    }


@app.post("/remi/event")
async def post_event(event: StateEvent):
    """状態イベントを送信"""
    try:
        if event.event_type == "speech.input":
            conversation_state["mode"] = "chat"
            conversation_state["mana_state"] = "normal"
            conversation_state["silence_count"] = 0
            
        elif event.event_type == "x.context":
            conversation_state["mode"] = "x_companion"
            
        elif event.event_type == "system.event":
            if event.data:
                conversation_state.update(event.data)
                
        elif event.event_type == "silence.tick":
            conversation_state["silence_count"] += 1
            if conversation_state["silence_count"] > 10:
                conversation_state["mana_state"] = "thinking"
            if conversation_state["silence_count"] > 30:
                conversation_state["mode"] = "idle"
        
        return {
            "success": True,
            "state": conversation_state,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Event error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/remi/history")
async def get_history(limit: int = 10):
    """会話履歴を取得"""
    return {
        "history": conversation_history[-limit:],
        "total": len(conversation_history),
        "timestamp": datetime.now().isoformat()
    }


@app.post("/remi/reset")
async def reset_conversation():
    """会話をリセット"""
    global conversation_history, conversation_state
    
    conversation_history = []
    conversation_state = {
        "mode": "idle",
        "mana_state": "normal",
        "conversation_history": [],
        "last_interaction": None,
        "silence_count": 0
    }
    
    return {
        "success": True,
        "message": "Conversation reset",
        "timestamp": datetime.now().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("REMI_BRAIN_PORT", "9407"))
    host = os.getenv("REMI_BRAIN_HOST", "0.0.0.0")
    
    logger.info(f"Starting Remi Brain API on {host}:{port}")
    logger.info("Remi personality loaded")
    
    uvicorn.run(app, host=host, port=port, log_level="info")






