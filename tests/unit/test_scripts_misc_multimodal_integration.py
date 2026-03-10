"""
tests/unit/test_scripts_misc_multimodal_integration.py
Unit tests for scripts/misc/multimodal_integration.py
"""
import sys
import types
import base64
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open


def _make_integration(available: bool = True) -> MagicMock:
    m = MagicMock()
    m.is_available.return_value = available
    return m


# ---------------------------------------------------------------------------
# Stub hard dependencies
# ---------------------------------------------------------------------------
for _name in ("langchain_integration", "comfyui_integration", "obsidian_integration"):
    if _name not in sys.modules:
        _m = types.ModuleType(_name)
        for _cls in ("LangChainIntegration", "ComfyUIIntegration", "ObsidianIntegration"):
            setattr(_m, _cls, MagicMock(return_value=_make_integration()))
        sys.modules[_name] = _m

# speech_recognition / pyttsx3 → stub as unavailable so SPEECH_AVAILABLE=False
if "speech_recognition" not in sys.modules:
    sys.modules["speech_recognition"] = None  # triggers ImportError chain  # type: ignore
if "pyttsx3" not in sys.modules:
    sys.modules["pyttsx3"] = None  # type: ignore

import scripts.misc.multimodal_integration as _sut


def _make_obj(comfyui_avail=True, langchain_avail=True, obsidian_avail=True) -> "_sut.MultimodalIntegration":
    with patch.object(Path, "exists", return_value=False):
        obj = _sut.MultimodalIntegration()
    obj.comfyui = _make_integration(comfyui_avail)
    obj.langchain = _make_integration(langchain_avail)
    obj.obsidian = _make_integration(obsidian_avail)
    obj.speech_recognizer = None
    obj.speech_engine = None
    return obj


# ---------------------------------------------------------------------------
# Module-level
# ---------------------------------------------------------------------------
class TestModuleLevel:
    def test_multimodal_integration_class_exists(self):
        assert hasattr(_sut, "MultimodalIntegration")

    def test_speech_available_is_bool(self):
        assert isinstance(_sut.SPEECH_AVAILABLE, bool)


# ---------------------------------------------------------------------------
# __init__ / instantiation
# ---------------------------------------------------------------------------
class TestInit:
    def test_instantiation_succeeds(self):
        obj = _make_obj()
        assert isinstance(obj, _sut.MultimodalIntegration)

    def test_has_langchain_attr(self):
        obj = _make_obj()
        assert obj.langchain is not None

    def test_has_comfyui_attr(self):
        obj = _make_obj()
        assert obj.comfyui is not None


# ---------------------------------------------------------------------------
# text_to_image()
# ---------------------------------------------------------------------------
class TestTextToImage:
    def test_returns_dict(self):
        obj = _make_obj()
        obj.comfyui.generate_image.return_value = "prompt123"  # type: ignore
        result = obj.text_to_image("a cat")
        assert isinstance(result, dict)

    def test_success_when_comfyui_available_and_returns_id(self):
        obj = _make_obj()
        obj.comfyui.generate_image.return_value = "pid_abc"  # type: ignore
        result = obj.text_to_image("sunset")
        assert result["success"] is True
        assert result["prompt_id"] == "pid_abc"

    def test_includes_prompt_in_result(self):
        obj = _make_obj()
        obj.comfyui.generate_image.return_value = "pid"  # type: ignore
        result = obj.text_to_image("rainbow")
        assert result["prompt"] == "rainbow"

    def test_error_when_comfyui_unavailable(self):
        obj = _make_obj(comfyui_avail=False)
        result = obj.text_to_image("test")
        assert result["success"] is False
        assert "error" in result

    def test_not_success_when_generate_returns_none(self):
        obj = _make_obj()
        obj.comfyui.generate_image.return_value = None  # type: ignore
        result = obj.text_to_image("test")
        assert result["success"] is False


# ---------------------------------------------------------------------------
# image_to_text()
# ---------------------------------------------------------------------------
class TestImageToText:
    def test_error_when_langchain_unavailable(self):
        obj = _make_obj(langchain_avail=False)
        result = obj.image_to_text("fake.png")
        assert result["success"] is False
        assert "error" in result

    def test_error_on_file_not_found(self):
        obj = _make_obj()
        result = obj.image_to_text("/nonexistent/file.png")
        assert result["success"] is False
        assert "error" in result

    def test_success_with_valid_image(self, tmp_path):
        img = tmp_path / "test.png"
        img.write_bytes(b"\x89PNG fake")
        obj = _make_obj()
        obj.langchain.chat.return_value = "A beautiful landscape"  # type: ignore
        result = obj.image_to_text(str(img))
        assert result["success"] is True
        assert result["description"] == "A beautiful landscape"

    def test_includes_question_in_prompt(self, tmp_path):
        img = tmp_path / "test.png"
        img.write_bytes(b"data")
        obj = _make_obj()
        obj.langchain.chat.return_value = "Answer"  # type: ignore
        result = obj.image_to_text(str(img), question="What is this?")
        assert result["success"] is True
        call_args = obj.langchain.chat.call_args[0][0]  # type: ignore
        assert "What is this?" in call_args


# ---------------------------------------------------------------------------
# text_to_speech()
# ---------------------------------------------------------------------------
class TestTextToSpeech:
    def test_error_when_speech_unavailable(self):
        obj = _make_obj()
        # SPEECH_AVAILABLE is False (stubs loaded as None → ImportError)
        result = obj.text_to_speech("hello")
        assert result["success"] is False
        assert "error" in result

    def test_success_when_engine_available(self, tmp_path):
        obj = _make_obj()
        mock_engine = MagicMock()
        obj.speech_engine = mock_engine
        with patch.object(_sut, "SPEECH_AVAILABLE", True):
            result = obj.text_to_speech("hello")
        assert result["success"] is True

    def test_save_to_file_when_path_given(self, tmp_path):
        obj = _make_obj()
        mock_engine = MagicMock()
        obj.speech_engine = mock_engine
        save_path = str(tmp_path / "out.wav")
        with patch.object(_sut, "SPEECH_AVAILABLE", True):
            result = obj.text_to_speech("hello", save_path=save_path)
        assert result["success"] is True
        assert result["audio_path"] == save_path
        mock_engine.save_to_file.assert_called_once()


# ---------------------------------------------------------------------------
# speech_to_text()
# ---------------------------------------------------------------------------
class TestSpeechToText:
    def test_error_when_speech_unavailable(self):
        obj = _make_obj()
        result = obj.speech_to_text("fake.wav")
        assert result["success"] is False
        assert "error" in result


# ---------------------------------------------------------------------------
# multimodal_workflow()
# ---------------------------------------------------------------------------
class TestMultimodalWorkflow:
    def test_text_to_text_passthrough(self):
        obj = _make_obj()
        obj.langchain.chat.return_value = "processed"  # type: ignore
        result = obj.multimodal_workflow("text", "hello", "text")
        assert result["success"] is True
        assert "text" in result

    def test_text_to_image_workflow(self):
        obj = _make_obj()
        obj.comfyui.generate_image.return_value = "pid"  # type: ignore
        result = obj.multimodal_workflow("text", "a cat", "image")
        assert result["success"] is True

    def test_text_to_speech_workflow(self):
        obj = _make_obj()
        mock_engine = MagicMock()
        obj.speech_engine = mock_engine
        with patch.object(_sut, "SPEECH_AVAILABLE", True):
            result = obj.multimodal_workflow("text", "say this", "speech")
        assert result["success"] is True

    def test_speech_input_fails_without_recognizer(self):
        obj = _make_obj()
        result = obj.multimodal_workflow("speech", "fake.wav", "text")
        assert result["success"] is False


# ---------------------------------------------------------------------------
# create_multimodal_note()
# ---------------------------------------------------------------------------
class TestCreateMultimodalNote:
    def test_success_when_obsidian_available(self):
        obj = _make_obj()
        obj.obsidian.create_note.return_value = Path("/vault/note.md")  # type: ignore[union-attr]
        result = obj.create_multimodal_note("Title", "Content")
        assert result["success"] is True
        assert "note_path" in result

    def test_error_when_obsidian_unavailable(self):
        obj = _make_obj(obsidian_avail=False)
        result = obj.create_multimodal_note("Title", "Content")
        assert result["success"] is False
        assert "error" in result

    def test_includes_image_links(self):
        obj = _make_obj()
        obj.obsidian.create_note.return_value = Path("/vault/note.md")  # type: ignore[union-attr]
        result = obj.create_multimodal_note(
            "Title", "Body", image_paths=["img1.png", "img2.jpg"]
        )
        assert result["success"] is True
        # Verify create_note was called with content containing image markdown
        call_content = obj.obsidian.create_note.call_args[1]["content"]  # type: ignore[union-attr]
        assert "img1.png" in call_content
        assert "img2.jpg" in call_content

    def test_note_creation_failure_returns_error(self):
        obj = _make_obj()
        obj.obsidian.create_note.return_value = None  # type: ignore[union-attr]
        result = obj.create_multimodal_note("Title", "Content")
        assert result["success"] is False
