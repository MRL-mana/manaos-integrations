"""Tests for scripts/misc/voice_realtime_streaming.py"""
import sys
import types
from unittest.mock import MagicMock, AsyncMock, patch
import pytest
from pathlib import Path

_MISC = Path(__file__).parent.parent.parent / "scripts" / "misc"


def _stub_deps(monkeypatch):
    # voice_integration stub
    voice_mod = types.ModuleType("voice_integration")
    voice_mod.create_stt_engine = MagicMock(return_value=MagicMock())  # type: ignore
    voice_mod.create_tts_engine = MagicMock(return_value=MagicMock())  # type: ignore

    class _FakeConvLoop:
        def __init__(self, **kwargs):
            self.realtime = False
            for k, v in kwargs.items():
                setattr(self, k, v)
        def enable_realtime_mode(self, val):
            self.realtime = val
        async def start(self):
            pass

    voice_mod.VoiceConversationLoop = _FakeConvLoop  # type: ignore
    monkeypatch.setitem(sys.modules, "voice_integration", voice_mod)

    # unified_logging stub
    log_mod = types.ModuleType("unified_logging")
    log_mod.get_service_logger = MagicMock(return_value=MagicMock())  # type: ignore
    monkeypatch.setitem(sys.modules, "unified_logging", log_mod)

    # websockets stub
    ws_mod = types.ModuleType("websockets")
    ws_mod.serve = MagicMock()  # type: ignore
    ws_mod.connect = MagicMock()  # type: ignore
    monkeypatch.setitem(sys.modules, "websockets", ws_mod)


def _load(monkeypatch):
    sys.modules.pop("voice_realtime_streaming", None)
    monkeypatch.syspath_prepend(str(_MISC))
    _stub_deps(monkeypatch)
    with patch("builtins.print"):
        import voice_realtime_streaming as m
    return m


class TestVoiceRealtimeStreaming:
    def test_module_loads(self, monkeypatch):
        m = _load(monkeypatch)
        assert "voice_realtime_streaming" in sys.modules

    def test_class_exists(self, monkeypatch):
        m = _load(monkeypatch)
        assert hasattr(m, "RealtimeVoiceStreaming")

    def test_instantiate_class(self, monkeypatch):
        m = _load(monkeypatch)
        stt = MagicMock()
        tts = MagicMock()
        llm_callback = MagicMock()
        instance = m.RealtimeVoiceStreaming(
            stt_engine=stt,
            tts_engine=tts,
            llm_callback=llm_callback,
        )
        assert instance is not None

    def test_hotword_default(self, monkeypatch):
        m = _load(monkeypatch)
        instance = m.RealtimeVoiceStreaming(
            stt_engine=MagicMock(),
            tts_engine=MagicMock(),
            llm_callback=MagicMock(),
        )
        assert instance.hotword == "レミ"

    def test_custom_hotword(self, monkeypatch):
        m = _load(monkeypatch)
        instance = m.RealtimeVoiceStreaming(
            stt_engine=MagicMock(),
            tts_engine=MagicMock(),
            llm_callback=MagicMock(),
            hotword="マナ",
        )
        assert instance.hotword == "マナ"

    def test_realtime_mode_enabled(self, monkeypatch):
        m = _load(monkeypatch)
        instance = m.RealtimeVoiceStreaming(
            stt_engine=MagicMock(),
            tts_engine=MagicMock(),
            llm_callback=MagicMock(),
        )
        assert instance.conversation_loop.realtime is True

    def test_intent_router_optional(self, monkeypatch):
        m = _load(monkeypatch)
        instance = m.RealtimeVoiceStreaming(
            stt_engine=MagicMock(),
            tts_engine=MagicMock(),
            llm_callback=MagicMock(),
            intent_router_callback=None,
        )
        assert instance.intent_router_callback is None
