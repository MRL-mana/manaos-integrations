"""
Unit tests for scripts/misc/personality_system.py
"""
import sys
import json
from pathlib import Path
from unittest.mock import MagicMock

# ── mocks ─────────────────────────────────────────────────────────────────
_ml = MagicMock()
_ml.get_service_logger.return_value = MagicMock()
_ml.get_logger.return_value = MagicMock()
sys.modules.setdefault("manaos_logger", _ml)

_eh = MagicMock()
_eh_inst = MagicMock()
_eh_inst.handle_exception = MagicMock(
    return_value=MagicMock(user_message="err_msg", message="err_detail")
)
_eh.ManaOSErrorHandler = MagicMock(return_value=_eh_inst)
_eh.ErrorCategory = MagicMock(); _eh.ErrorSeverity = MagicMock()
sys.modules.setdefault("manaos_error_handler", _eh)

_tc = MagicMock()
_tc.get_timeout_config = MagicMock(return_value={})
sys.modules.setdefault("manaos_timeout_config", _tc)

_cv = MagicMock()
_cv_inst = MagicMock()
_cv_inst.validate_config = MagicMock(return_value=(True, []))
_cv.ConfigValidator = MagicMock(return_value=_cv_inst)
sys.modules.setdefault("manaos_config_validator", _cv)

sys.modules.setdefault("flask_cors", MagicMock())
sys.modules.setdefault("yaml", None)  # yaml が None の場合のテスト  # type: ignore

import pytest
from scripts.misc.personality_system import (
    PersonalityProfile,
    PersonalitySystem,
    PersonalityTrait,
)


@pytest.fixture
def ps(tmp_path):
    """tmp_path を config_path に使う PersonalitySystem"""
    cfg = tmp_path / "personality_config.json"
    return PersonalitySystem(config_path=cfg)


# ── TestPersonalityTrait ───────────────────────────────────────────────────
class TestPersonalityTrait:
    def test_values(self):
        assert PersonalityTrait.PURE.value == "pure"
        assert PersonalityTrait.FRIENDLY.value == "friendly"
        assert PersonalityTrait.CASUAL.value == "casual"
        assert PersonalityTrait.PROFESSIONAL.value == "professional"
        assert PersonalityTrait.HUMOROUS.value == "humorous"


# ── TestPersonalityProfile ────────────────────────────────────────────────
class TestPersonalityProfile:
    def test_fields(self):
        p = PersonalityProfile(
            name="test",
            traits=[PersonalityTrait.PURE],
            tone="friendly",
            response_style="casual",
            greeting_patterns=["こんにちは"],
            conversation_starters=["調子どう？"],
            personality_prompt="あなたはテスト用AIです",
            created_at="2026-01-01T00:00:00",
            updated_at="2026-01-01T00:00:00",
        )
        assert p.name == "test"
        assert p.personality_prompt == "あなたはテスト用AIです"


# ── TestInit ──────────────────────────────────────────────────────────────
class TestInit:
    def test_default_persona_exists(self, ps):
        assert ps.default_persona is not None
        assert isinstance(ps.default_persona.name, str)

    def test_current_persona_falls_back_to_default(self, ps):
        # config_path が空なので persona_profiles.json は存在しない
        # current_persona は default_persona と同じはず
        assert ps.current_persona is not None

    def test_default_config_keys(self, ps):
        config = ps._get_default_config()
        assert "default_persona" in config
        assert "enable_personality" in config
        assert "persona_storage_path" in config

    def test_enable_personality_default_true(self, ps):
        assert ps._get_default_config()["enable_personality"] is True


# ── TestGetPersonalityPrompt ──────────────────────────────────────────────
class TestGetPersonalityPrompt:
    def test_returns_string(self, ps):
        prompt = ps.get_personality_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 0


# ── TestApplyPersonalityToPrompt ──────────────────────────────────────────
class TestApplyPersonalityToPrompt:
    def test_base_prompt_present_in_result(self, ps):
        result = ps.apply_personality_to_prompt("You are a helpful assistant.")
        assert "You are a helpful assistant." in result

    def test_personality_disabled_returns_base(self, ps):
        ps.config["enable_personality"] = False
        result = ps.apply_personality_to_prompt("base only")
        assert result == "base only"
        ps.config["enable_personality"] = True  # reset

    def test_with_context(self, ps):
        result = ps.apply_personality_to_prompt("base", context="report")
        assert isinstance(result, str)
        assert "base" in result

    def test_with_memory_snippets(self, ps):
        result = ps.apply_personality_to_prompt(
            "base",
            memory_snippets=["過去の会話1", "過去の会話2"]
        )
        assert isinstance(result, str)


# ── TestLoadConfig ────────────────────────────────────────────────────────
class TestLoadConfig:
    def test_loads_existing_config(self, tmp_path):
        cfg = tmp_path / "ps_cfg.json"
        cfg.write_text(
            json.dumps({"default_persona": "pure_gal", "enable_personality": False}),
            encoding="utf-8"
        )
        ps = PersonalitySystem(config_path=cfg)
        # validate_config returns (True, []) so config is loaded
        assert isinstance(ps.config, dict)

    def test_missing_config_uses_defaults(self, tmp_path):
        cfg = tmp_path / "missing.json"
        ps = PersonalitySystem(config_path=cfg)
        assert ps.config["default_persona"] == "pure_gal"
