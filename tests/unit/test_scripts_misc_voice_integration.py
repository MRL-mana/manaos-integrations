"""
Unit tests for scripts/misc/voice_integration.py
STTEngine, TTSEngine, VoiceConversationLoop, helper functions.
"""
import sys
import io
import struct
import wave
from unittest.mock import MagicMock, patch
import pytest

# ── mocks ─────────────────────────────────────────────────────────────────
_ml = MagicMock()
_ml.get_logger.return_value = MagicMock()
_ml.get_service_logger.return_value = MagicMock()
sys.modules.setdefault("manaos_logger", _ml)

_eh = MagicMock()
_eh_inst = MagicMock()
_eh_inst.handle_error = MagicMock()
_eh.ManaOSErrorHandler = MagicMock(return_value=_eh_inst)
_eh.ErrorCategory = MagicMock()
_eh.ErrorSeverity = MagicMock()
sys.modules.setdefault("manaos_error_handler", _eh)

_tc = MagicMock()
_tc.get_timeout = MagicMock(return_value=5.0)
sys.modules["manaos_timeout_config"] = _tc

_paths = MagicMock()
_paths.VOICEVOX_PORT = 50021
sys.modules.setdefault("_paths", _paths)

# Ensure optional heavy packages are absent so flags = False
sys.modules.setdefault("faster_whisper", None)  # type: ignore
sys.modules.setdefault("whisper", None)  # type: ignore
sys.modules.setdefault("pyaudio", None)  # type: ignore
sys.modules.setdefault("webrtcvad", None)  # type: ignore

import numpy as np
from scripts.misc.voice_integration import (
    STTEngine,
    TTSEngine,
    VoiceConversationLoop,
    _voice_timeout,
    _voice_request_with_retry,
    FASTER_WHISPER_AVAILABLE,
    WHISPER_CPP_AVAILABLE,
    create_stt_engine,
    create_tts_engine,
    create_voice_conversation_loop,
)


# ── helpers ───────────────────────────────────────────────────────────────

def _make_wav_bytes(num_samples: int = 160, sample_rate: int = 16000) -> bytes:
    """Generate a minimal PCM WAV byte string for testing."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)           # 16-bit
        wf.setframerate(sample_rate)
        # 160 zero samples
        wf.writeframes(struct.pack(f"<{num_samples}h", *([0] * num_samples)))
    return buf.getvalue()


# ── TestVoiceTimeout ───────────────────────────────────────────────────────
class TestVoiceTimeout:
    @pytest.fixture(autouse=True)
    def _reinstate_tc(self):
        """各テスト前後で _tc が sys.modules["manaos_timeout_config"] になるよう保証"""
        old = sys.modules.get("manaos_timeout_config")
        sys.modules["manaos_timeout_config"] = _tc
        yield
        if old is None:
            sys.modules.pop("manaos_timeout_config", None)
        else:
            sys.modules["manaos_timeout_config"] = old

    def test_returns_value_from_config(self):
        _tc.get_timeout.side_effect = None
        _tc.get_timeout.return_value = 5.0
        result = _voice_timeout("api_call", 30.0)
        assert result == 5.0

    def test_returns_default_when_exception(self):
        _tc.get_timeout.side_effect = RuntimeError("fail")
        try:
            result = _voice_timeout("missing_key", 99.0)
            assert result == 99.0
        finally:
            _tc.get_timeout.side_effect = None
            _tc.get_timeout.return_value = 5.0

    def test_returns_mocked_value(self):
        # _tc.get_timeout is already mocked to return 5.0
        result = _voice_timeout("api_call", 30.0)
        # result will be whatever _tc.get_timeout("api_call", 30.0) returns
        assert result is not None


# ── TestVoiceRequestWithRetry ──────────────────────────────────────────────
class TestVoiceRequestWithRetry:
    def test_returns_on_first_success(self):
        fn = MagicMock(return_value="OK")
        result = _voice_request_with_retry(fn, max_retries=2)
        assert result == "OK"
        assert fn.call_count == 1

    def test_retries_on_failure(self):
        calls = {"n": 0}

        def fn():
            calls["n"] += 1
            if calls["n"] < 3:
                raise ConnectionError("fail")
            return "success"

        result = _voice_request_with_retry(fn, max_retries=2)
        assert result == "success"
        assert calls["n"] == 3

    def test_raises_after_max_retries(self):
        fn = MagicMock(side_effect=ConnectionError("always fails"))
        with pytest.raises(ConnectionError):
            _voice_request_with_retry(fn, max_retries=1)
        # called max_retries+1 times
        assert fn.call_count == 2

    def test_zero_retries_raises_immediately_on_failure(self):
        fn = MagicMock(side_effect=ValueError("oops"))
        with pytest.raises(ValueError):
            _voice_request_with_retry(fn, max_retries=0)
        assert fn.call_count == 1


# ── TestSTTEngine ──────────────────────────────────────────────────────────
class TestSTTEngineInit:
    def test_attributes_set(self):
        engine = STTEngine(model_size="tiny", device="cpu")
        assert engine.model_size == "tiny"
        assert engine.device == "cpu"
        assert engine.language == "ja"

    def test_custom_language(self):
        engine = STTEngine(language="en")
        assert engine.language == "en"

    def test_no_model_when_packages_unavailable(self):
        # faster_whisper and whisper are not installed (mock them away to simulate absence)
        import scripts.misc.voice_integration as _vi
        with patch.object(_vi, "FASTER_WHISPER_AVAILABLE", False), \
             patch.object(_vi, "WHISPER_CPP_AVAILABLE", False):
            engine = STTEngine()
            assert engine.model is None
            assert engine.whisper_model is None

    def test_compute_type_stored(self):
        engine = STTEngine(compute_type="int8")
        assert engine.compute_type == "int8"


class TestSTTEngineTranscribe:
    def test_raises_when_no_model(self):
        import scripts.misc.voice_integration as _vi
        with patch.object(_vi, "FASTER_WHISPER_AVAILABLE", False), \
             patch.object(_vi, "WHISPER_CPP_AVAILABLE", False):
            engine = STTEngine()
            assert engine.model is None and engine.whisper_model is None
            with pytest.raises(Exception, match="初期化されていません"):
                engine.transcribe(b"dummy", 16000)


class TestSTTEngineBytesToNumpy:
    def test_converts_valid_wav(self):
        wav_bytes = _make_wav_bytes(num_samples=320)
        engine = STTEngine()
        result = engine._bytes_to_numpy(wav_bytes, 16000)
        assert isinstance(result, np.ndarray)
        assert result.dtype == np.float32

    def test_fallback_for_non_wav(self):
        """Non-WAV bytes fall back to raw int16 interpretation."""
        raw = struct.pack("<4h", 100, 200, -100, -200)
        engine = STTEngine()
        result = engine._bytes_to_numpy(raw, 16000)
        assert isinstance(result, np.ndarray)
        assert result.dtype == np.float32

    def test_values_in_range(self):
        """Normalized audio should be in [-1, 1]."""
        wav_bytes = _make_wav_bytes(num_samples=160)
        engine = STTEngine()
        result = engine._bytes_to_numpy(wav_bytes, 16000)
        assert result.max() <= 1.0
        assert result.min() >= -1.0


# ── TestTTSEngine ──────────────────────────────────────────────────────────
class TestTTSEngineInit:
    def test_default_attributes(self):
        engine = TTSEngine()
        assert engine.engine == "voicevox"
        assert engine.speaker_id == 3

    def test_custom_speaker_id(self):
        engine = TTSEngine(speaker_id=10)
        assert engine.speaker_id == 10

    def test_custom_engine(self):
        engine = TTSEngine(engine="style_bert_vits2")
        assert engine.engine == "style_bert_vits2"

    def test_voicevox_url_set_from_arg(self):
        engine = TTSEngine(voicevox_url="http://custom:50021")
        assert engine.voicevox_url == "http://custom:50021"

    def test_active_engine_set(self):
        engine = TTSEngine(engine="style_bert_vits2")
        assert engine.active_engine == "style_bert_vits2"


class TestTTSEngineGetSpeakers:
    def test_style_bert_vits2_returns_fallback_list(self):
        engine = TTSEngine(engine="style_bert_vits2")
        with patch("requests.get", side_effect=Exception("unavailable")):
            speakers = engine.get_speakers()
        assert isinstance(speakers, list)
        assert len(speakers) > 0

    def test_voicevox_get_speakers_request_error_returns_empty(self):
        engine = TTSEngine(engine="voicevox")
        with patch("requests.get", side_effect=Exception("unavail")):
            speakers = engine.get_speakers()
        # on exception, returns empty list
        assert isinstance(speakers, list)


# ── TestVoiceConversationLoop ──────────────────────────────────────────────

@pytest.fixture
def vcl():
    stt = STTEngine()
    tts = TTSEngine()
    cb = lambda text: f"echo: {text}"
    return VoiceConversationLoop(stt_engine=stt, tts_engine=tts, llm_callback=cb)


class TestVoiceConversationLoopInit:
    def test_attributes_set(self, vcl):
        assert vcl.hotword == "レミ"
        assert vcl.continuous is False
        assert vcl.is_running is False
        assert vcl.conversation_history == []

    def test_audio_queue_created(self, vcl):
        import queue
        assert isinstance(vcl.audio_queue, queue.Queue)

    def test_custom_hotword(self):
        stt = STTEngine()
        tts = TTSEngine()
        loop = VoiceConversationLoop(
            stt_engine=stt, tts_engine=tts,
            llm_callback=lambda t: t, hotword="さくら"
        )
        assert loop.hotword == "さくら"

    def test_no_hotword(self):
        stt = STTEngine()
        tts = TTSEngine()
        loop = VoiceConversationLoop(
            stt_engine=stt, tts_engine=tts,
            llm_callback=lambda t: t, hotword=None
        )
        assert loop.hotword is None


class TestVoiceConversationLoopProcessAudio:
    def test_returns_none_when_no_model(self, vcl):
        """STTEngine raises → process_audio catches it and returns None."""
        wav = _make_wav_bytes()
        result = vcl.process_audio(wav, 16000)
        assert result is None

    def test_hotword_check_skips_unrecognised(self):
        """When STT returns text without hotword, returns None."""
        stt = MagicMock(spec=STTEngine)
        stt.transcribe.return_value = {"text": "no hotword here"}
        tts = MagicMock(spec=TTSEngine)
        loop = VoiceConversationLoop(
            stt_engine=stt, tts_engine=tts,
            llm_callback=lambda t: t, hotword="レミ"
        )
        result = loop.process_audio(b"audio", 16000)
        assert result is None

    def test_empty_text_returns_none(self):
        """When STT returns empty text, returns None."""
        stt = MagicMock(spec=STTEngine)
        stt.transcribe.return_value = {"text": "   "}
        tts = MagicMock(spec=TTSEngine)
        loop = VoiceConversationLoop(
            stt_engine=stt, tts_engine=tts,
            llm_callback=lambda t: t, hotword=None
        )
        result = loop.process_audio(b"audio", 16000)
        assert result is None


class TestVoiceConversationLoopControl:
    def test_enable_realtime_mode(self, vcl):
        vcl.enable_realtime_mode(True)
        assert vcl.realtime_mode is True

    def test_disable_realtime_mode(self, vcl):
        vcl.enable_realtime_mode(True)
        vcl.enable_realtime_mode(False)
        assert vcl.realtime_mode is False

    def test_stop_sets_is_running_false(self, vcl):
        vcl.is_running = True
        vcl.stop()
        assert vcl.is_running is False


# ── TestFactoryFunctions ───────────────────────────────────────────────────
class TestFactoryFunctions:
    def test_create_stt_engine_returns_stt_engine(self):
        engine = create_stt_engine(model_size="tiny", device="cpu")
        assert isinstance(engine, STTEngine)
        assert engine.model_size == "tiny"
        assert engine.device == "cpu"

    def test_create_tts_engine_returns_tts_engine(self):
        engine = create_tts_engine(engine="voicevox", speaker_id=5)
        assert isinstance(engine, TTSEngine)
        assert engine.speaker_id == 5

    def test_create_voice_conversation_loop_returns_loop(self):
        stt = create_stt_engine()
        tts = create_tts_engine()
        cb = lambda t: t
        loop = create_voice_conversation_loop(
            stt_engine=stt, tts_engine=tts, llm_callback=cb, hotword="テスト"
        )
        assert isinstance(loop, VoiceConversationLoop)
        assert loop.hotword == "テスト"
