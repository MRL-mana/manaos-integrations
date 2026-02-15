"""
ManaOS 音声機能統合（STT + TTS + 会話ループ）
秘書レミ完全体の最後のピース
"""

import os
import io
import asyncio
import threading
import queue
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from pathlib import Path
import wave
import numpy as np

# 統一モジュールのインポート
from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity

# ロガーの初期化
logger = get_logger(__name__)

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("VoiceIntegration")


# タイムアウト設定（manaos_timeout_config から取得、未導入時はデフォルト）
def _voice_timeout(key: str, default: float = 30.0) -> float:
    try:
        from manaos_timeout_config import get_timeout

        return get_timeout(key, default)
    except Exception:
        return default


# リトライ（指数バックオフ、最大2回リトライ = 合計3回試行）
def _voice_request_with_retry(request_fn, max_retries: int = 2):
    import time

    last_exc = None
    for attempt in range(max_retries + 1):
        try:
            return request_fn()
        except Exception as e:
            last_exc = e
            if attempt < max_retries:
                delay = (2**attempt) * 1.0
                logger.warning(
                    f"音声APIリクエスト失敗（{attempt + 1}/{max_retries + 1}）、{delay:.1f}秒後にリトライ: {e}"
                )
                time.sleep(delay)
    raise last_exc


# ========================================
# STT (Speech-to-Text) - Whisper
# ========================================

FASTER_WHISPER_AVAILABLE = False
try:
    from faster_whisper import WhisperModel

    FASTER_WHISPER_AVAILABLE = True
    logger.info("✅ faster-whisper が利用可能です")
except ImportError:
    logger.warning(
        "⚠️ faster-whisper が利用できません。pip install faster-whisper を実行してください"
    )

WHISPER_CPP_AVAILABLE = False
try:
    import whisper

    WHISPER_CPP_AVAILABLE = True
    logger.info("✅ whisper (OpenAI) が利用可能です")
except ImportError:
    logger.warning("⚠️ whisper が利用できません。フォールバックとして使用可能です")

# ========================================
# TTS (Text-to-Speech) - VOICEVOX / Style-Bert-VITS2
# ========================================

VOICEVOX_AVAILABLE = False
try:
    import requests

    VOICEVOX_AVAILABLE = True
    logger.info("✅ VOICEVOX API が利用可能です")
except ImportError:
    logger.warning("⚠️ requests が利用できません")

STYLE_BERT_VITS2_AVAILABLE = False
try:
    # Style-Bert-VITS2は通常HTTP API経由で使用
    STYLE_BERT_VITS2_AVAILABLE = True
    logger.info("✅ Style-Bert-VITS2 API が利用可能です（HTTP経由）")
except Exception:
    pass

# ========================================
# 音声入力（マイク）
# ========================================

PYAUDIO_AVAILABLE = False
try:
    import pyaudio

    PYAUDIO_AVAILABLE = True
    logger.info("✅ pyaudio が利用可能です")
except ImportError:
    logger.warning("⚠️ pyaudio が利用できません。pip install pyaudio を実行してください")

# ========================================
# VAD (Voice Activity Detection)
# ========================================

WEBRTCVAD_AVAILABLE = False
try:
    import webrtcvad

    WEBRTCVAD_AVAILABLE = True
    logger.info("✅ webrtcvad が利用可能です")
except ImportError:
    logger.warning(
        "⚠️ webrtcvad が利用できません。pip install webrtcvad を実行してください（VAD改善機能）"
    )


class STTEngine:
    """音声認識エンジン（Whisper系）"""

    def __init__(
        self,
        model_size: str = "large-v3",
        device: str = "cuda",
        compute_type: str = "float16",
        language: str = "ja",
    ):
        """
        初期化

        Args:
            model_size: モデルサイズ（tiny, base, small, medium, large-v3）
            device: デバイス（cuda, cpu）
            compute_type: 計算タイプ（float16, int8, int8_float16）
            language: 言語コード（ja, en等）
        """
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.language = language
        self.model = None
        self.whisper_model = None

        # faster-whisper優先
        if FASTER_WHISPER_AVAILABLE:
            try:
                self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
                logger.info(f"✅ faster-whisper モデル読み込み完了: {model_size}")
            except Exception as e:
                logger.error(f"faster-whisper 初期化エラー: {e}")
                self.model = None

        # フォールバック: OpenAI Whisper
        if self.model is None and WHISPER_CPP_AVAILABLE:
            try:
                self.whisper_model = whisper.load_model(model_size)
                logger.info(f"✅ OpenAI Whisper モデル読み込み完了: {model_size}")
            except Exception as e:
                logger.error(f"Whisper 初期化エラー: {e}")
                self.whisper_model = None

    def transcribe(
        self, audio_data: bytes, sample_rate: int = 16000, format: str = "wav"
    ) -> Dict[str, Any]:
        """
        音声を文字起こし

        Args:
            audio_data: 音声データ（バイト列）
            sample_rate: サンプリングレート
            format: 音声フォーマット（wav, mp3等）

        Returns:
            認識結果（text, language, segments等）
        """
        if self.model is None and self.whisper_model is None:
            raise Exception("音声認識モデルが初期化されていません")

        try:
            # faster-whisper使用
            if self.model:
                # 音声データをnumpy配列に変換
                audio_array = self._bytes_to_numpy(audio_data, sample_rate)

                segments, info = self.model.transcribe(
                    audio_array, language=self.language, beam_size=5
                )

                # テキストを結合
                text = " ".join([segment.text for segment in segments])

                return {
                    "text": text.strip(),
                    "language": info.language,
                    "language_probability": info.language_probability,
                    "segments": [
                        {"start": segment.start, "end": segment.end, "text": segment.text}
                        for segment in segments
                    ],
                }

            # OpenAI Whisper使用（フォールバック）
            elif self.whisper_model:
                audio_array = self._bytes_to_numpy(audio_data, sample_rate)
                result = self.whisper_model.transcribe(audio_array, language=self.language)

                return {
                    "text": result["text"].strip(),
                    "language": result.get("language", self.language),
                    "segments": result.get("segments", []),
                }

        except Exception as e:
            logger.error(f"音声認識エラー: {e}", exc_info=True)
            error_handler.handle_error(
                error=e,
                category=ErrorCategory.PROCESSING,
                severity=ErrorSeverity.MEDIUM,
                context={"operation": "transcribe", "model_size": self.model_size},
            )
            raise

    def _bytes_to_numpy(self, audio_data: bytes, sample_rate: int) -> np.ndarray:
        """音声バイト列をnumpy配列に変換"""
        try:
            # WAV形式の場合
            audio_io = io.BytesIO(audio_data)
            with wave.open(audio_io, "rb") as wav_file:
                frames = wav_file.readframes(-1)
                sound_info = np.frombuffer(frames, dtype=np.int16)
                sound_info = sound_info.astype(np.float32) / 32768.0

                # サンプリングレート変換が必要な場合
                if wav_file.getframerate() != sample_rate:
                    # 簡易リサンプリング（必要に応じてlibrosa等を使用）
                    ratio = sample_rate / wav_file.getframerate()
                    indices = np.round(np.arange(0, len(sound_info), ratio))
                    indices = indices[indices < len(sound_info)].astype(int)
                    sound_info = sound_info[indices]

                return sound_info
        except Exception as e:
            logger.error(f"音声データ変換エラー: {e}")
            # フォールバック: 直接numpy配列として扱う
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            return audio_array.astype(np.float32) / 32768.0


class TTSEngine:
    """音声合成エンジン（VOICEVOX / Style-Bert-VITS2）"""

    def __init__(
        self,
        engine: str = "voicevox",
        voicevox_url: Optional[str] = None,
        style_bert_vits2_url: Optional[str] = None,
        speaker_id: int = 3,  # VOICEVOXのデフォルトスピーカーID
    ):
        """
        初期化

        Args:
            engine: エンジン名（voicevox, style_bert_vits2）
            voicevox_url: VOICEVOX API URL
            style_bert_vits2_url: Style-Bert-VITS2 API URL
            speaker_id: スピーカーID（VOICEVOX用）
        """
        from _paths import VOICEVOX_PORT
        
        self.engine = engine
        self.voicevox_url = voicevox_url or os.getenv("VOICEVOX_URL", f"http://127.0.0.1:{VOICEVOX_PORT}")
        self.style_bert_vits2_url = style_bert_vits2_url or os.getenv("STYLE_BERT_VITS2_URL", "http://127.0.0.1:5000")
        self.speaker_id = speaker_id

        # エンジン選択
        if engine == "voicevox" and VOICEVOX_AVAILABLE:
            self.active_engine = "voicevox"
        elif engine == "style_bert_vits2":
            self.active_engine = "style_bert_vits2"
        else:
            self.active_engine = "voicevox"  # デフォルト
            logger.warning(f"指定されたエンジン {engine} が利用できないため、voicevox を使用します")

    def synthesize(
        self,
        text: str,
        speaker_id: Optional[int] = None,
        speed: float = 1.0,
        pitch: float = 0.0,
        intonation: float = 1.0,
    ) -> bytes:
        """
        テキストを音声に変換

        Args:
            text: テキスト
            speaker_id: スピーカーID（Noneの場合はデフォルト）
            speed: 話速（0.5-2.0）
            pitch: 音高（-0.15-0.15）
            intonation: 抑揚（0.0-2.0）

        Returns:
            音声データ（WAV形式のバイト列）
        """
        speaker_id = speaker_id or self.speaker_id

        if self.active_engine == "voicevox":
            return self._synthesize_voicevox(text, speaker_id, speed, pitch, intonation)
        elif self.active_engine == "style_bert_vits2":
            return self._synthesize_style_bert_vits2(text, speaker_id, speed, pitch, intonation)
        else:
            raise Exception(f"不明なエンジン: {self.active_engine}")

    def _synthesize_voicevox(
        self, text: str, speaker_id: int, speed: float, pitch: float, intonation: float
    ) -> bytes:
        """VOICEVOXで音声合成"""
        try:
            # 1. 音声クエリを生成
            query_url = f"{self.voicevox_url}/audio_query"
            query_params = {"text": text, "speaker": speaker_id}

            timeout_sec = _voice_timeout("voice_tts", 30.0)
            response = _voice_request_with_retry(
                lambda: requests.post(query_url, params=query_params, timeout=timeout_sec)
            )
            response.raise_for_status()
            audio_query = response.json()

            # パラメータ調整
            audio_query["speedScale"] = speed
            audio_query["pitchScale"] = pitch
            audio_query["intonationScale"] = intonation

            # 2. 音声合成
            synthesis_url = f"{self.voicevox_url}/synthesis"
            synthesis_params = {"speaker": speaker_id}

            response = _voice_request_with_retry(
                lambda: requests.post(
                    synthesis_url, params=synthesis_params, json=audio_query, timeout=timeout_sec
                )
            )
            response.raise_for_status()

            return response.content

        except Exception as e:
            logger.error(f"VOICEVOX音声合成エラー: {e}", exc_info=True)
            error_handler.handle_error(
                error=e,
                category=ErrorCategory.EXTERNAL_SERVICE,
                severity=ErrorSeverity.MEDIUM,
                context={"operation": "voicevox_synthesize", "text": text[:50]},
            )
            raise

    def _synthesize_style_bert_vits2(
        self, text: str, speaker_id: int, speed: float, pitch: float, intonation: float
    ) -> bytes:
        """Style-Bert-VITS2で音声合成"""
        try:
            # Style-Bert-VITS2 API呼び出し
            api_url = f"{self.style_bert_vits2_url}/voice"

            payload = {
                "text": text,
                "id": speaker_id,
                "lang": "ja",
                "length": speed,
                "noise": 0.6,
                "noisew": 0.8,
                "sdp_ratio": 0.2,
            }

            timeout_sec = _voice_timeout("voice_tts", 30.0)
            response = _voice_request_with_retry(
                lambda: requests.post(api_url, json=payload, timeout=timeout_sec)
            )
            response.raise_for_status()

            return response.content

        except Exception as e:
            logger.error(f"Style-Bert-VITS2音声合成エラー: {e}", exc_info=True)
            error_handler.handle_error(
                error=e,
                category=ErrorCategory.EXTERNAL_SERVICE,
                severity=ErrorSeverity.MEDIUM,
                context={"operation": "style_bert_vits2_synthesize", "text": text[:50]},
            )
            raise

    def get_speakers(self) -> List[Dict[str, Any]]:
        """利用可能なスピーカー一覧を取得"""
        if self.active_engine == "voicevox":
            try:
                timeout_sec = _voice_timeout("voice_speakers", 10.0)
                response = _voice_request_with_retry(
                    lambda: requests.get(f"{self.voicevox_url}/speakers", timeout=timeout_sec)
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(f"スピーカー一覧取得エラー: {e}")
                return []
        else:
            # Style-Bert-VITS2: レミ等の固定リストを返す（API一覧が無い場合のフォールバック）
            return [
                {"name": "レミ", "id": 0, "styles": [{"name": "ノーマル", "id": 0}]},
                {"name": "デフォルト", "id": 0, "styles": [{"name": "ノーマル", "id": 0}]},
            ]


class VoiceConversationLoop:
    """音声会話ループ（STT → Intent Router → LLM → TTS）"""

    def __init__(
        self,
        stt_engine: STTEngine,
        tts_engine: TTSEngine,
        llm_callback: Callable[[str], str],
        hotword: Optional[str] = "レミ",
        continuous: bool = False,
        intent_router_callback: Optional[Callable[[str], Dict[str, Any]]] = None,
        task_registration_callback: Optional[Callable[[str, Dict[str, Any]], bool]] = None,
        conversation_save_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        """
        初期化

        Args:
            stt_engine: STTエンジン
            tts_engine: TTSエンジン
            llm_callback: LLM応答生成コールバック（text -> response_text）
            hotword: ホットワード（Noneの場合は常時監視）
            continuous: 連続会話モード
        """
        self.stt_engine = stt_engine
        self.tts_engine = tts_engine
        self.llm_callback = llm_callback
        self.hotword = hotword
        self.continuous = continuous
        self.intent_router_callback = intent_router_callback
        self.task_registration_callback = task_registration_callback
        self.conversation_save_callback = conversation_save_callback

        self.is_running = False
        self.audio_queue = queue.Queue()
        self.conversation_history = []

        # VAD（Voice Activity Detection）設定
        self.vad_enabled = True
        self.silence_threshold = 0.01  # 無音判定の閾値
        self.min_speech_duration = 0.5  # 最小音声長（秒）

        # WebRTC VAD（高精度VAD）
        self.webrtc_vad = None
        if WEBRTCVAD_AVAILABLE:
            try:
                self.webrtc_vad = webrtcvad.Vad(2)  # 0-3（2は中程度の敏感度）
                logger.info("✅ WebRTC VAD を有効化しました")
            except Exception as e:
                logger.warning(f"WebRTC VAD 初期化エラー: {e}")

        # リアルタイム処理設定
        self.realtime_mode = False
        self.streaming_buffer = []
        self.streaming_buffer_size = 16000 * 3  # 3秒分のバッファ

        # マイク入力（オプション）
        self.audio_stream = None
        self.audio_thread = None

        if PYAUDIO_AVAILABLE:
            self.pyaudio = pyaudio.PyAudio()
        else:
            self.pyaudio = None

    def start(self):
        """会話ループを開始"""
        if self.is_running:
            logger.warning("会話ループは既に実行中です")
            return

        self.is_running = True

        # マイク入力スレッドを開始（オプション）
        if self.pyaudio:
            self.audio_thread = threading.Thread(target=self._audio_capture_loop, daemon=True)
            self.audio_thread.start()

        logger.info("🎤 音声会話ループを開始しました")

    def stop(self):
        """会話ループを停止"""
        self.is_running = False

        if self.audio_stream:
            self.audio_stream.stop_stream()
            self.audio_stream.close()

        if self.pyaudio:
            self.pyaudio.terminate()

        logger.info("🛑 音声会話ループを停止しました")

    def process_audio(self, audio_data: bytes, sample_rate: int = 16000) -> Optional[bytes]:
        """
        音声データを処理（STT → LLM → TTS）

        Args:
            audio_data: 音声データ
            sample_rate: サンプリングレート

        Returns:
            音声応答データ（Noneの場合は応答なし）
        """
        try:
            # 1. STT: 音声をテキストに変換
            logger.info("🎤 音声認識中...")
            stt_result = self.stt_engine.transcribe(audio_data, sample_rate)
            user_text = stt_result["text"]

            if not user_text.strip():
                logger.warning("音声認識結果が空です")
                return None

            logger.info(f"📝 認識結果: {user_text}")

            # ホットワードチェック
            if self.hotword and self.hotword not in user_text:
                logger.debug(f"ホットワード '{self.hotword}' が検出されませんでした")
                return None

            # ホットワードを除去
            if self.hotword:
                user_text = user_text.replace(self.hotword, "").strip()

            if not user_text.strip():
                logger.warning("ホットワード除去後、テキストが空になりました")
                return None

            # 2. Intent Router: 意図分類（オプション）
            intent_result = None
            if self.intent_router_callback:
                try:
                    logger.info("🎯 意図分類中...")
                    intent_result = self.intent_router_callback(user_text)
                    logger.info(f"✅ 意図分類完了: {intent_result.get('intent_type', 'unknown')}")

                    # タスク登録が必要な場合
                    if self.task_registration_callback and intent_result:
                        intent_type = intent_result.get("intent_type", "")
                        if intent_type in ["task_execution", "scheduling"]:
                            logger.info("📋 タスク自動登録を試行...")
                            try:
                                success = self.task_registration_callback(user_text, intent_result)
                                if success:
                                    logger.info("✅ タスク自動登録完了")
                            except Exception as e:
                                logger.warning(f"タスク自動登録エラー: {e}")
                except Exception as e:
                    logger.warning(f"意図分類エラー: {e}")

            # 3. LLM: 応答を生成
            logger.info("🤖 LLM応答生成中...")
            response_text = self.llm_callback(user_text)

            if not response_text.strip():
                logger.warning("LLM応答が空です")
                return None

            logger.info(f"💬 応答: {response_text}")

            # 会話履歴に保存
            conversation_entry = {
                "timestamp": datetime.now().isoformat(),
                "user": user_text,
                "assistant": response_text,
                "intent": intent_result.get("intent_type", "unknown") if intent_result else None,
                "confidence": intent_result.get("confidence", 0.0) if intent_result else None,
            }
            self.conversation_history.append(conversation_entry)

            # 会話履歴を外部に保存（Notion/Slack等）
            if self.conversation_save_callback:
                try:
                    self.conversation_save_callback(conversation_entry)
                except Exception as e:
                    logger.warning(f"会話履歴保存エラー: {e}")

            # 4. TTS: テキストを音声に変換
            logger.info("🔊 音声合成中...")
            audio_response = self.tts_engine.synthesize(response_text)

            logger.info("✅ 音声応答生成完了")
            return audio_response

        except Exception as e:
            logger.error(f"音声会話処理エラー: {e}", exc_info=True)
            error_handler.handle_error(
                error=e,
                category=ErrorCategory.PROCESSING,
                severity=ErrorSeverity.MEDIUM,
                context={"operation": "voice_conversation"},
            )
            return None

    def _audio_capture_loop(self):
        """マイク入力キャプチャループ（バックグラウンドスレッド、VAD対応）"""
        if not self.pyaudio:
            return

        try:
            # マイク設定
            chunk = (
                320  # WebRTC VADは10ms, 20ms, 30msのチャンクが必要（320サンプル = 20ms @ 16kHz）
            )
            sample_rate = 16000
            channels = 1
            format = pyaudio.paInt16

            self.audio_stream = self.pyaudio.open(
                format=format,
                channels=channels,
                rate=sample_rate,
                input=True,
                frames_per_buffer=chunk,
            )

            logger.info("🎤 マイク入力開始（VAD対応）")

            # 音声区間バッファ
            speech_buffer = []
            silence_frames = 0
            max_silence_frames = 30  # 1秒の無音で区切り（30フレーム × 20ms = 600ms）

            while self.is_running:
                try:
                    # 音声データを読み取り
                    audio_data = self.audio_stream.read(chunk, exception_on_overflow=False)

                    # WebRTC VADで音声検出
                    is_speech = False
                    if self.webrtc_vad:
                        try:
                            is_speech = self.webrtc_vad.is_speech(audio_data, sample_rate)
                        except Exception as e:
                            # VADエラー時はフォールバック（簡易エネルギー判定）
                            audio_array = np.frombuffer(audio_data, dtype=np.int16)
                            energy = np.abs(audio_array).mean()
                            is_speech = energy > (self.silence_threshold * 32768)
                    else:
                        # フォールバック: 簡易エネルギー判定
                        audio_array = np.frombuffer(audio_data, dtype=np.int16)
                        energy = np.abs(audio_array).mean()
                        is_speech = energy > (self.silence_threshold * 32768)

                    if is_speech:
                        # 音声検出
                        speech_buffer.append(audio_data)
                        silence_frames = 0
                    else:
                        # 無音検出
                        silence_frames += 1

                        if speech_buffer:
                            # 無音が続いているが、まだバッファに音声がある
                            if silence_frames < max_silence_frames:
                                speech_buffer.append(audio_data)
                            else:
                                # 無音が続いたので、音声区間を確定
                                if len(speech_buffer) > 0:
                                    # 音声区間を結合
                                    complete_audio = b"".join(speech_buffer)

                                    # 最小音声長チェック
                                    duration = len(complete_audio) / (
                                        sample_rate * 2
                                    )  # 2バイト/サンプル
                                    if duration >= self.min_speech_duration:
                                        # キューに追加
                                        self.audio_queue.put(complete_audio)
                                        logger.debug(f"🎤 音声区間検出: {duration:.2f}秒")

                                    speech_buffer = []
                                    silence_frames = 0

                except Exception as e:
                    logger.error(f"マイク入力エラー: {e}")
                    break

            # 終了時に残っている音声を処理
            if speech_buffer:
                complete_audio = b"".join(speech_buffer)
                self.audio_queue.put(complete_audio)

        except Exception as e:
            logger.error(f"マイクキャプチャループエラー: {e}", exc_info=True)
        finally:
            if self.audio_stream:
                self.audio_stream.stop_stream()
                self.audio_stream.close()

    def enable_realtime_mode(self, enabled: bool = True):
        """リアルタイムモードを有効化/無効化"""
        self.realtime_mode = enabled
        if enabled:
            logger.info("✅ リアルタイムモードを有効化しました")
        else:
            logger.info("🛑 リアルタイムモードを無効化しました")

    async def process_streaming_audio(self, audio_stream):
        """
        ストリーミング音声を処理（非同期）

        Args:
            audio_stream: 音声ストリーム（AsyncGenerator）

        Yields:
            処理結果（音声応答データ）
        """
        buffer = []
        speech_detected = False

        async for audio_chunk in audio_stream:
            buffer.append(audio_chunk)

            # バッファサイズチェック
            if len(buffer) * len(audio_chunk) > self.streaming_buffer_size:
                # バッファが満杯になったら処理
                complete_audio = b"".join(buffer)
                response_audio = self.process_audio(complete_audio)

                if response_audio:
                    yield response_audio

                buffer = []


# ========================================
# 便利関数
# ========================================


def create_stt_engine(
    model_size: str = "large-v3", device: str = "cuda", compute_type: str = "float16"
) -> STTEngine:
    """STTエンジンを作成（簡易ファクトリー）"""
    return STTEngine(model_size=model_size, device=device, compute_type=compute_type, language="ja")


def create_tts_engine(
    engine: str = "voicevox", voicevox_url: Optional[str] = None, speaker_id: int = 3
) -> TTSEngine:
    """TTSエンジンを作成（簡易ファクトリー）"""
    return TTSEngine(engine=engine, voicevox_url=voicevox_url, speaker_id=speaker_id)


def create_voice_conversation_loop(
    stt_engine: STTEngine,
    tts_engine: TTSEngine,
    llm_callback: Callable[[str], str],
    hotword: Optional[str] = "レミ",
) -> VoiceConversationLoop:
    """音声会話ループを作成（簡易ファクトリー）"""
    return VoiceConversationLoop(
        stt_engine=stt_engine, tts_engine=tts_engine, llm_callback=llm_callback, hotword=hotword
    )
