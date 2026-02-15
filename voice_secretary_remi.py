#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎤 秘書レミ完全体 - 音声会話システム
ホットワード「レミ」で呼び出せる音声秘書
"""

import os
import sys
import asyncio
import httpx
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

try:
    from manaos_integrations._paths import INTENT_ROUTER_PORT, LLM_ROUTING_PORT, UNIFIED_API_PORT
except Exception:  # pragma: no cover
    try:
        from _paths import INTENT_ROUTER_PORT, LLM_ROUTING_PORT, UNIFIED_API_PORT  # type: ignore
    except Exception:  # pragma: no cover
        UNIFIED_API_PORT = int(os.getenv("UNIFIED_API_PORT", "9510"))
        INTENT_ROUTER_PORT = int(os.getenv("INTENT_ROUTER_PORT", "5100"))
        LLM_ROUTING_PORT = int(os.getenv("LLM_ROUTING_PORT", "5111"))

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent))

from voice_integration import (
    create_stt_engine,
    create_tts_engine,
    VoiceConversationLoop
)
from unified_logging import get_service_logger
logger = get_service_logger("voice-secretary-remi")

# 設定
INTENT_ROUTER_URL = os.getenv("INTENT_ROUTER_URL", f"http://127.0.0.1:{INTENT_ROUTER_PORT}")
UNIFIED_API_URL = os.getenv("UNIFIED_API_URL", f"http://127.0.0.1:{UNIFIED_API_PORT}")
LLM_ROUTING_URL = os.getenv("LLM_ROUTING_URL", f"http://127.0.0.1:{LLM_ROUTING_PORT}")
NOTION_AVAILABLE = os.getenv("NOTION_API_KEY") is not None
SLACK_AVAILABLE = os.getenv("SLACK_WEBHOOK_URL") is not None


def create_llm_callback():
    """LLM応答生成コールバックを作成"""
    async def llm_chat_async(text: str) -> str:
        """非同期LLMチャット"""
        try:
            # LLMルーティングAPIを使用
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{LLM_ROUTING_URL}/api/route",
                    json={
                        "task_type": "conversation",
                        "prompt": text
                    }
                )
                if response.status_code == 200:
                    result = response.json()
                    return result.get("response", "すみません、応答を生成できませんでした。")
                else:
                    # フォールバック: 統合APIのLFM 2.5を使用
                    response = await client.post(
                        f"{UNIFIED_API_URL}/api/lfm25/chat",
                        json={"message": text}
                    )
                    if response.status_code == 200:
                        result = response.json()
                        return result.get("response", "すみません、応答を生成できませんでした。")
        except Exception as e:
            logger.error(f"LLM呼び出しエラー: {e}")
        
        # 最終フォールバック
        return f"「{text}」についてですね。確認しました。"
    
    def llm_callback(text: str) -> str:
        """同期ラッパー"""
        return asyncio.run(llm_chat_async(text))
    
    return llm_callback


def create_intent_router_callback():
    """Intent Routerコールバックを作成"""
    async def classify_intent_async(text: str) -> Dict[str, Any]:
        """非同期意図分類"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{INTENT_ROUTER_URL}/api/classify",
                    json={"text": text}
                )
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.warning(f"Intent Router呼び出しエラー: {e}")
        
        return {"intent_type": "conversation", "confidence": 0.5}
    
    def intent_router_callback(text: str) -> Dict[str, Any]:
        """同期ラッパー"""
        return asyncio.run(classify_intent_async(text))
    
    return intent_router_callback


def create_task_registration_callback():
    """タスク自動登録コールバックを作成"""
    async def register_task_async(text: str, intent_result: Dict[str, Any]) -> bool:
        """非同期タスク登録"""
        try:
            # タスクキューシステムに登録
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{UNIFIED_API_URL}/api/task/queue/add",
                    json={
                        "input_text": text,
                        "intent_type": intent_result.get("intent_type", "task_execution"),
                        "priority": "medium"
                    }
                )
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"タスク登録エラー: {e}")
            return False
    
    def task_registration_callback(text: str, intent_result: Dict[str, Any]) -> bool:
        """同期ラッパー"""
        return asyncio.run(register_task_async(text, intent_result))
    
    return task_registration_callback


def create_conversation_save_callback():
    """会話履歴保存コールバックを作成"""
    async def save_conversation_async(conversation_entry: Dict[str, Any]) -> None:
        """非同期会話履歴保存"""
        # Notionに保存
        if NOTION_AVAILABLE:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(
                        f"{UNIFIED_API_URL}/api/obsidian/create",
                        json={
                            "title": f"音声会話 - {conversation_entry['timestamp']}",
                            "content": f"**ユーザー**: {conversation_entry['user']}\n\n**レミ**: {conversation_entry['assistant']}\n\n**意図**: {conversation_entry.get('intent', 'unknown')}"
                        }
                    )
                    if response.status_code == 200:
                        logger.info("✅ 会話履歴をObsidianに保存しました")
            except Exception as e:
                logger.warning(f"Obsidian保存エラー: {e}")
        
        # Slackに通知（オプション）
        if SLACK_AVAILABLE:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(
                        os.getenv("SLACK_WEBHOOK_URL"),
                        json={
                            "text": f"🎤 音声会話\n**ユーザー**: {conversation_entry['user']}\n**レミ**: {conversation_entry['assistant']}"
                        }
                    )
                    if response.status_code == 200:
                        logger.info("✅ 会話履歴をSlackに送信しました")
            except Exception as e:
                logger.warning(f"Slack送信エラー: {e}")
    
    def conversation_save_callback(conversation_entry: Dict[str, Any]) -> None:
        """同期ラッパー"""
        asyncio.run(save_conversation_async(conversation_entry))
    
    return conversation_save_callback


def main():
    """メイン関数"""
    logger.info("🎤 秘書レミ完全体を起動中...")
    
    # エンジン初期化
    logger.info("📦 STTエンジンを初期化中...")
    stt_engine = create_stt_engine(
        model_size=os.getenv("VOICE_STT_MODEL", "large-v3"),
        device=os.getenv("VOICE_STT_DEVICE", "cuda"),
        compute_type=os.getenv("VOICE_STT_COMPUTE_TYPE", "float16")
    )
    
    logger.info("📦 TTSエンジンを初期化中...")
    tts_engine = create_tts_engine(
        engine=os.getenv("VOICE_TTS_ENGINE", "voicevox"),
        voicevox_url=os.getenv("VOICEVOX_URL", "http://127.0.0.1:50021"),
        speaker_id=int(os.getenv("VOICEVOX_SPEAKER_ID", "3"))
    )
    
    # コールバック作成
    logger.info("🔗 コールバックを設定中...")
    llm_callback = create_llm_callback()
    intent_router_callback = create_intent_router_callback()
    task_registration_callback = create_task_registration_callback()
    conversation_save_callback = create_conversation_save_callback()
    
    # 会話ループ作成
    logger.info("🎯 音声会話ループを作成中...")
    conversation_loop = VoiceConversationLoop(
        stt_engine=stt_engine,
        tts_engine=tts_engine,
        llm_callback=llm_callback,
        hotword="レミ",
        continuous=True,
        intent_router_callback=intent_router_callback,
        task_registration_callback=task_registration_callback,
        conversation_save_callback=conversation_save_callback
    )
    
    # 開始
    logger.info("🚀 音声会話ループを開始します...")
    logger.info("💡 ホットワード「レミ」で呼び出せます")
    logger.info("🛑 停止するには Ctrl+C を押してください")
    
    try:
        conversation_loop.start()
        
        # メインループ（音声ファイル処理モード）
        import time
        while True:
            # 音声ファイルを処理する場合は、ここでファイルを読み込んで処理
            # 現在は常時監視モード（マイク入力）を使用
            time.sleep(1)
    
    except KeyboardInterrupt:
        logger.info("🛑 停止シグナルを受信しました")
    finally:
        conversation_loop.stop()
        logger.info("✅ 秘書レミ完全体を停止しました")


if __name__ == "__main__":
    main()
