#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎤 リアルタイム音声ストリーミング処理
WebSocket経由でリアルタイム音声会話を実現
"""

import asyncio
import base64
import json
import websockets
from typing import AsyncGenerator, Optional
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from voice_integration import create_stt_engine, create_tts_engine, VoiceConversationLoop
from unified_logging import get_service_logger
logger = get_service_logger("voice-realtime-streaming")


class RealtimeVoiceStreaming:
    """リアルタイム音声ストリーミング処理"""

    def __init__(
        self,
        stt_engine,
        tts_engine,
        llm_callback,
        intent_router_callback=None,
        hotword: Optional[str] = "レミ",
    ):
        """
        初期化

        Args:
            stt_engine: STTエンジン
            tts_engine: TTSエンジン
            llm_callback: LLMコールバック
            intent_router_callback: Intent Routerコールバック（オプション）
            hotword: ホットワード
        """
        self.stt_engine = stt_engine
        self.tts_engine = tts_engine
        self.llm_callback = llm_callback
        self.intent_router_callback = intent_router_callback
        self.hotword = hotword

        # 会話ループ
        self.conversation_loop = VoiceConversationLoop(
            stt_engine=stt_engine,
            tts_engine=tts_engine,
            llm_callback=llm_callback,
            hotword=hotword,
            intent_router_callback=intent_router_callback,
        )

        # リアルタイムモード有効化
        self.conversation_loop.enable_realtime_mode(True)

    async def process_audio_stream(
        self, audio_stream: AsyncGenerator[bytes, None]
    ) -> AsyncGenerator[bytes, None]:
        """
        音声ストリームを処理

        Args:
            audio_stream: 音声ストリーム

        Yields:
            音声応答データ
        """
        buffer = []
        buffer_size = 16000 * 2  # 2秒分のバッファ

        async for audio_chunk in audio_stream:
            buffer.append(audio_chunk)

            # バッファが満杯になったら処理
            total_size = sum(len(chunk) for chunk in buffer)
            if total_size >= buffer_size:
                # 音声データを結合
                complete_audio = b"".join(buffer)

                # 会話処理
                response_audio = self.conversation_loop.process_audio(
                    complete_audio, sample_rate=16000
                )

                if response_audio:
                    yield response_audio

                buffer = []

        # 残りのバッファを処理
        if buffer:
            complete_audio = b"".join(buffer)
            response_audio = self.conversation_loop.process_audio(complete_audio, sample_rate=16000)

            if response_audio:
                yield response_audio

    async def handle_websocket(self, websocket, path):
        """
        WebSocket接続を処理

        Args:
            websocket: WebSocket接続
            path: パス
        """
        logger.info(f"🔌 WebSocket接続: {websocket.remote_address}")

        try:

            async def audio_stream() -> AsyncGenerator[bytes, None]:
                """音声ストリームを生成"""
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        if data.get("type") == "audio":
                            audio_data = base64.b64decode(data.get("data", ""))
                            yield audio_data
                    except json.JSONDecodeError:
                        # バイナリデータとして扱う
                        if isinstance(message, bytes):
                            yield message

            # 音声ストリームを処理
            async for response_audio in self.process_audio_stream(audio_stream()):
                # 応答を送信（受信と同様にBase64で統一）
                await websocket.send(
                    json.dumps(
                        {
                            "type": "audio",
                            "data": base64.b64encode(response_audio).decode("utf-8"),
                        }
                    )
                )

        except websockets.exceptions.ConnectionClosed:
            logger.info("🔌 WebSocket接続が閉じられました")
        except Exception as e:
            logger.error(f"WebSocket処理エラー: {e}", exc_info=True)


async def main():
    """メイン関数"""
    import os

    # エンジン初期化
    logger.info("📦 エンジンを初期化中...")
    stt_engine = create_stt_engine(
        model_size=os.getenv("VOICE_STT_MODEL", "medium"),  # リアルタイム用はmedium
        device=os.getenv("VOICE_STT_DEVICE", "cuda"),
        compute_type=os.getenv("VOICE_STT_COMPUTE_TYPE", "float16"),
    )

    tts_engine = create_tts_engine(
        engine=os.getenv("VOICE_TTS_ENGINE", "voicevox"),
        voicevox_url=os.getenv("VOICEVOX_URL", "http://127.0.0.1:50021"),
        speaker_id=int(os.getenv("VOICEVOX_SPEAKER_ID", "3")),
    )

    # LLMコールバック: UNIFIED_API / LLM_ROUTING と連携（voice_secretary_remi と同様）
    try:
        from voice_secretary_remi import create_llm_callback

        llm_callback = create_llm_callback()
        logger.info("✅ LLMコールバックを UNIFIED_API/LLM_ROUTING と連携しました")
    except Exception as e:
        logger.warning(f"voice_secretary_remi の LLM 連携に失敗しました。フォールバックを使用: {e}")

        def llm_callback(text: str) -> str:
            return f"「{text}」についてですね。了解しました。"

    # ストリーミング処理（ホットワードは VOICE_HOTWORD で変更可能）
    hotword = os.getenv("VOICE_HOTWORD", "レミ").strip() or "レミ"
    streaming = RealtimeVoiceStreaming(
        stt_engine=stt_engine, tts_engine=tts_engine, llm_callback=llm_callback, hotword=hotword
    )
    logger.info(f"ホットワード: 「{hotword}」")

    # WebSocketサーバー起動
    port = int(os.getenv("VOICE_WEBSOCKET_PORT", "8765"))
    host = os.getenv("VOICE_WEBSOCKET_HOST", "0.0.0.0")  # 0.0.0.0で全インターフェースでリッスン
    logger.info(f"🚀 WebSocketサーバーを起動: ws://{host}:{port}")

    async with websockets.serve(streaming.handle_websocket, host, port):
        await asyncio.Future()  # 永久に実行


if __name__ == "__main__":
    asyncio.run(main())
