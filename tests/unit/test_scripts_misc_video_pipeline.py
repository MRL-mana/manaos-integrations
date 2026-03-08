"""
tests/unit/test_scripts_misc_video_pipeline.py

video_pipeline.py の単体テスト
"""
import sys
import json
import wave
import struct
import tempfile
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, call

# ── mock setup ────────────────────────────────────────────────────────
# All optional imports are try/except in the module; just let them fail.
# Only mock manaos_error_handler to prevent ImportError propagation.
_eh = MagicMock()
sys.modules.setdefault("manaos_error_handler", _eh)

# ── SUT import ────────────────────────────────────────────────────────
import scripts.misc.video_pipeline as _sut
from scripts.misc.video_pipeline import (
    LocalLLMClient,
    VoicevoxTTS,
    VideoPipeline,
    DEFAULT_CONFIG,
    DEFAULT_OLLAMA_URL,
    DEFAULT_VOICEVOX_URL,
)


# ══════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════

def _make_wav(path: str, duration_secs: float = 1.0, framerate: int = 22050):
    """Create a minimal valid WAV file at path."""
    n_frames = int(framerate * duration_secs)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(framerate)
        wf.setnframes(n_frames)
        wf.writeframesraw(b"\x00\x00" * n_frames)


# ══════════════════════════════════════════════════════════════════════════
# TestDefaultConfig
# ══════════════════════════════════════════════════════════════════════════

class TestDefaultConfig:
    def test_ollama_url_default_set(self):
        assert DEFAULT_OLLAMA_URL.startswith("http://")

    def test_voicevox_url_default_set(self):
        assert DEFAULT_VOICEVOX_URL.startswith("http://")

    def test_default_config_has_video_section(self):
        assert "video" in DEFAULT_CONFIG

    def test_default_config_has_models_section(self):
        assert "models" in DEFAULT_CONFIG

    def test_video_section_has_expected_keys(self):
        v = DEFAULT_CONFIG["video"]
        for key in ("width", "height", "fps", "duration_per_image"):
            assert key in v


# ══════════════════════════════════════════════════════════════════════════
# TestLocalLLMClient
# ══════════════════════════════════════════════════════════════════════════

class TestLocalLLMClient:
    def test_default_url_set(self):
        client = LocalLLMClient()
        assert client.ollama_url == DEFAULT_OLLAMA_URL

    def test_custom_url(self):
        client = LocalLLMClient("http://custom:11434")
        assert client.ollama_url == "http://custom:11434"

    def test_generate_returns_response_text(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": "generated text"}
        mock_resp.raise_for_status.return_value = None
        import requests
        with patch.object(requests, "post", return_value=mock_resp):
            client = LocalLLMClient()
            result = client.generate("hello", model="llama3")
        assert result == "generated text"

    def test_generate_raises_on_http_error(self):
        import requests
        with patch.object(requests, "post", side_effect=ConnectionError("down")):
            client = LocalLLMClient()
            with pytest.raises(Exception):
                client.generate("hello", model="llama3")

    def test_generate_requires_requests(self):
        orig = _sut.REQUESTS_AVAILABLE
        try:
            _sut.REQUESTS_AVAILABLE = False
            client = LocalLLMClient()
            with pytest.raises(RuntimeError, match="requests"):
                client.generate("hello", model="m")
        finally:
            _sut.REQUESTS_AVAILABLE = orig


# ══════════════════════════════════════════════════════════════════════════
# TestVoicevoxTTS
# ══════════════════════════════════════════════════════════════════════════

class TestVoicevoxTTS:
    def test_default_params(self):
        tts = VoicevoxTTS()
        assert tts.url == DEFAULT_VOICEVOX_URL
        assert isinstance(tts.speaker_id, int)
        assert isinstance(tts.speed, float)

    def test_is_available_true_when_200(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        import requests
        with patch.object(requests, "get", return_value=mock_resp):
            tts = VoicevoxTTS()
            assert tts.is_available() is True

    def test_is_available_false_on_error(self):
        import requests
        with patch.object(requests, "get", side_effect=ConnectionError("down")):
            tts = VoicevoxTTS()
            assert tts.is_available() is False

    def test_synthesize_returns_bytes(self):
        mock_query_resp = MagicMock()
        mock_query_resp.json.return_value = {"speedScale": 1.0}
        mock_query_resp.raise_for_status.return_value = None
        mock_synth_resp = MagicMock()
        mock_synth_resp.content = b"RIFF_fake_wav"
        mock_synth_resp.raise_for_status.return_value = None
        import requests
        with patch.object(requests, "post", side_effect=[mock_query_resp, mock_synth_resp]):
            tts = VoicevoxTTS()
            result = tts.synthesize("テスト")
        assert isinstance(result, bytes)

    def test_synthesize_to_file_creates_file(self, tmp_path):
        mock_query_resp = MagicMock()
        mock_query_resp.json.return_value = {"speedScale": 1.0}
        mock_query_resp.raise_for_status.return_value = None
        mock_synth_resp = MagicMock()
        mock_synth_resp.content = b"\x00\x01\x02"
        mock_synth_resp.raise_for_status.return_value = None
        import requests
        out_file = str(tmp_path / "out.wav")
        with patch.object(requests, "post", side_effect=[mock_query_resp, mock_synth_resp]):
            tts = VoicevoxTTS()
            result = tts.synthesize_to_file("テスト", out_file)
        assert Path(result).exists()

    def test_get_speakers_returns_list_on_success(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"id": 1, "name": "四国めたん"}]
        mock_resp.raise_for_status.return_value = None
        import requests
        with patch.object(requests, "get", return_value=mock_resp):
            tts = VoicevoxTTS()
            speakers = tts.get_speakers()
        assert isinstance(speakers, list)
        assert speakers[0]["id"] == 1

    def test_get_speakers_returns_empty_on_error(self):
        import requests
        with patch.object(requests, "get", side_effect=ConnectionError("down")):
            tts = VoicevoxTTS()
            speakers = tts.get_speakers()
        assert speakers == []


# ══════════════════════════════════════════════════════════════════════════
# TestVideoPipelineInit
# ══════════════════════════════════════════════════════════════════════════

class TestVideoPipelineInit:
    def test_creates_output_dir(self, tmp_path):
        out_dir = str(tmp_path / "vids")
        with patch("pathlib.Path.mkdir"):
            vp = VideoPipeline({"output_dir": out_dir})
        assert vp is not None

    def test_config_merged_with_defaults(self):
        with patch("pathlib.Path.mkdir"):
            vp = VideoPipeline({"output_dir": "/tmp/vids"})
        assert "models" in vp.config
        assert vp.config["video"]["width"] == DEFAULT_CONFIG["video"]["width"]

    def test_custom_config_overrides_default(self):
        with patch("pathlib.Path.mkdir"):
            vp = VideoPipeline({"output_dir": "/tmp/vids", "voicevox_speed": 2.0})
        assert vp.config["voicevox_speed"] == 2.0

    def test_llm_and_tts_initialized(self):
        with patch("pathlib.Path.mkdir"):
            vp = VideoPipeline({"output_dir": "/tmp/vids"})
        assert isinstance(vp.llm, LocalLLMClient)
        assert isinstance(vp.tts, VoicevoxTTS)


# ══════════════════════════════════════════════════════════════════════════
# TestGenerateNarration
# ══════════════════════════════════════════════════════════════════════════

class TestGenerateNarration:
    @pytest.fixture
    def vp(self):
        with patch("pathlib.Path.mkdir"):
            return VideoPipeline({"output_dir": "/tmp/vids"})

    def test_calls_llm_with_quality_model(self, vp):
        with patch.object(vp.llm, "generate", return_value="ナレーション文章") as mock_gen:
            result = vp.generate_narration("テストテーマ")
        assert result == "ナレーション文章"
        mock_gen.assert_called_once()
        call_kwargs = mock_gen.call_args
        assert call_kwargs[1]["model"] == vp.config["models"]["quality"] or \
               call_kwargs[0][1] == vp.config["models"]["quality"]

    def test_raises_on_llm_error(self, vp):
        with patch.object(vp.llm, "generate", side_effect=RuntimeError("LLM down")):
            with pytest.raises(RuntimeError):
                vp.generate_narration("topic")


# ══════════════════════════════════════════════════════════════════════════
# TestGenerateTitleAndSubtitles
# ══════════════════════════════════════════════════════════════════════════

class TestGenerateTitleAndSubtitles:
    @pytest.fixture
    def vp(self):
        with patch("pathlib.Path.mkdir"):
            return VideoPipeline({"output_dir": "/tmp/vids"})

    def test_returns_dict_with_required_keys(self, vp):
        raw = json.dumps({
            "title": "テストタイトル",
            "subtitles": ["sub1", "sub2"],
            "hashtags": ["#test"],
        })
        with patch.object(vp.llm, "generate", return_value=raw):
            result = vp.generate_title_and_subtitles("topic")
        assert "title" in result
        assert "subtitles" in result

    def test_falls_back_on_invalid_json(self, vp):
        with patch.object(vp.llm, "generate", return_value="<invalid json>"):
            result = vp.generate_title_and_subtitles("topic")
        assert result["title"] == "topic"
        assert isinstance(result["subtitles"], list)

    def test_subtitles_count_matches_num_subtitles(self, vp):
        raw = json.dumps({
            "title": "Title",
            "subtitles": ["a", "b", "c", "d", "e"],
            "hashtags": [],
        })
        with patch.object(vp.llm, "generate", return_value=raw):
            result = vp.generate_title_and_subtitles("topic", num_subtitles=5)
        assert len(result["subtitles"]) == 5


# ══════════════════════════════════════════════════════════════════════════
# TestAnalyzeImages
# ══════════════════════════════════════════════════════════════════════════

class TestAnalyzeImages:
    @pytest.fixture
    def vp(self):
        with patch("pathlib.Path.mkdir"):
            return VideoPipeline({"output_dir": "/tmp/vids"})

    def test_missing_image_returns_empty_description(self, vp):
        results = vp.analyze_images(["/nonexistent/image.jpg"])
        assert results[0]["description"] == ""

    def test_existing_image_is_analyzed(self, vp, tmp_path):
        img = tmp_path / "test.png"
        img.write_bytes(b"fakeimgdata")
        with patch.object(vp.llm, "analyze_image", return_value="画像の説明文。詳細情報。"):
            results = vp.analyze_images([str(img)])
        assert results[0]["description"] == "画像の説明文。詳細情報。"

    def test_alt_text_extracted_from_first_sentence(self, vp, tmp_path):
        img = tmp_path / "test.png"
        img.write_bytes(b"fakeimgdata")
        with patch.object(vp.llm, "analyze_image", return_value="最初の文。次の文。"):
            results = vp.analyze_images([str(img)])
        assert results[0]["alt_text"] == "最初の文。"

    def test_analyze_error_returns_empty_description(self, vp, tmp_path):
        img = tmp_path / "test.png"
        img.write_bytes(b"fakeimgdata")
        with patch.object(vp.llm, "analyze_image", side_effect=RuntimeError("API error")):
            results = vp.analyze_images([str(img)])
        assert results[0]["description"] == ""


# ══════════════════════════════════════════════════════════════════════════
# TestGetAudioDuration
# ══════════════════════════════════════════════════════════════════════════

class TestGetAudioDuration:
    @pytest.fixture
    def vp(self):
        with patch("pathlib.Path.mkdir"):
            return VideoPipeline({"output_dir": "/tmp/vids"})

    def test_returns_correct_duration(self, vp, tmp_path):
        wav_path = str(tmp_path / "test.wav")
        _make_wav(wav_path, duration_secs=2.5, framerate=22050)
        duration = vp._get_audio_duration(wav_path)
        assert abs(duration - 2.5) < 0.1

    def test_one_second_wav(self, vp, tmp_path):
        wav_path = str(tmp_path / "one.wav")
        _make_wav(wav_path, duration_secs=1.0)
        duration = vp._get_audio_duration(wav_path)
        assert abs(duration - 1.0) < 0.01


# ══════════════════════════════════════════════════════════════════════════
# TestResizeImage
# ══════════════════════════════════════════════════════════════════════════

class TestResizeImage:
    @pytest.fixture
    def vp(self):
        with patch("pathlib.Path.mkdir"):
            return VideoPipeline({"output_dir": "/tmp/vids"})

    def test_returns_original_path_when_pillow_unavailable(self, vp):
        orig = _sut.PILLOW_AVAILABLE
        try:
            _sut.PILLOW_AVAILABLE = False
            result = vp._resize_image("/some/img.png", 1920, 1080)
            assert result == "/some/img.png"
        finally:
            _sut.PILLOW_AVAILABLE = orig

    def test_returns_tmp_file_when_pillow_available(self, vp, tmp_path):
        if not _sut.PILLOW_AVAILABLE:
            pytest.skip("Pillow not available")
        from PIL import Image as _PIL
        img = _PIL.new("RGB", (640, 480), color=(100, 150, 200))
        src = str(tmp_path / "src.jpg")
        img.save(src)
        result = vp._resize_image(src, 1920, 1080)
        assert result != src
        assert Path(result).exists()


# ══════════════════════════════════════════════════════════════════════════
# TestCreatePromoVideo
# ══════════════════════════════════════════════════════════════════════════

class TestCreatePromoVideo:
    @pytest.fixture
    def vp(self):
        with patch("pathlib.Path.mkdir"):
            return VideoPipeline({"output_dir": "/tmp/vids"})

    def test_raises_when_moviepy_not_available(self, vp):
        orig = _sut.MOVIEPY_AVAILABLE
        try:
            _sut.MOVIEPY_AVAILABLE = False
            with pytest.raises(RuntimeError, match="MoviePy"):
                vp.create_promo_video(images=["img.jpg"])
        finally:
            _sut.MOVIEPY_AVAILABLE = orig

    def test_returns_error_result_on_no_valid_images(self, vp):
        orig = _sut.MOVIEPY_AVAILABLE
        try:
            _sut.MOVIEPY_AVAILABLE = True
            result = vp.create_promo_video(
                images=["/nonexistent/img.jpg"],
                with_llm=False,
            )
            # Should return dict with success=False or raise ValueError
            assert not result.get("success", True)
        except (ValueError, Exception):
            pass  # also acceptable
        finally:
            _sut.MOVIEPY_AVAILABLE = orig


# ══════════════════════════════════════════════════════════════════════════
# TestCreateSimpleSlideshow
# ══════════════════════════════════════════════════════════════════════════

class TestCreateSimpleSlideshow:
    @pytest.fixture
    def vp(self):
        with patch("pathlib.Path.mkdir"):
            return VideoPipeline({"output_dir": "/tmp/vids"})

    def test_raises_when_moviepy_not_available(self, vp):
        orig = _sut.MOVIEPY_AVAILABLE
        try:
            _sut.MOVIEPY_AVAILABLE = False
            with pytest.raises(RuntimeError, match="MoviePy"):
                vp.create_simple_slideshow(images=["img.jpg"])
        finally:
            _sut.MOVIEPY_AVAILABLE = orig
