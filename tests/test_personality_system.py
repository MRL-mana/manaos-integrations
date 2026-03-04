#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_personality_system.py — PersonalitySystem 単体テスト (13テスト)

テスト対象: scripts/misc/personality_system.py
- PersonalityTrait Enum の値検証
- PersonalityProfile の構造検証
- PersonalitySystem: デフォルト初期化・設定読み込み
- PersonalitySystem: get_personality_prompt / apply_personality_to_prompt
- PersonalitySystem: get_current_persona / update_persona
- PersonalitySystem: 保存・再読み込み
- PersonalitySystem: YAML 読み込みフォールバック
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

import pytest

# conftest がルートを sys.path に追加済み。scripts/misc も追加する。
_SCRIPTS_MISC = Path(__file__).parent.parent / "scripts" / "misc"
if str(_SCRIPTS_MISC) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_MISC))

from personality_system import (  # noqa: E402
    PersonalityProfile,
    PersonalitySystem,
    PersonalityTrait,
)


# ---------- fixtures ----------

@pytest.fixture
def system_no_yaml(tmp_path: Path) -> PersonalitySystem:
    """persona_config.yaml を無効化してデフォルト人格を使うシステム"""
    with patch.object(PersonalitySystem, "_load_persona_from_yaml", return_value=None):
        return PersonalitySystem(config_path=tmp_path / "cfg.json")


@pytest.fixture
def system_with_storage(tmp_path: Path) -> PersonalitySystem:
    """ストレージパスを tmp_path に向けたシステム"""
    storage = tmp_path / "personas.json"
    cfg = tmp_path / "cfg.json"
    cfg.write_text(
        json.dumps({
            "enable_personality": True,
            "default_persona": "pure_gal",
            "persona_storage_path": str(storage),
        }),
        encoding="utf-8",
    )
    with patch.object(PersonalitySystem, "_load_persona_from_yaml", return_value=None):
        return PersonalitySystem(config_path=cfg)


# ---------- PersonalityTrait ----------

class TestPersonalityTrait:
    def test_enum_values(self) -> None:
        assert PersonalityTrait.PURE == "pure"
        assert PersonalityTrait.FRIENDLY == "friendly"
        assert PersonalityTrait.CASUAL == "casual"
        assert PersonalityTrait.PROFESSIONAL == "professional"
        assert PersonalityTrait.HUMOROUS == "humorous"

    def test_value_access(self) -> None:
        # str, Enum の場合は .value で文字列値を取得する
        assert PersonalityTrait.CASUAL.value == "casual"


# ---------- PersonalityProfile ----------

class TestPersonalityProfile:
    def test_default_persona_fields(self, system_no_yaml: PersonalitySystem) -> None:
        p = system_no_yaml.default_persona
        assert isinstance(p, PersonalityProfile)
        assert p.name == "pure_gal"
        assert PersonalityTrait.PURE in p.traits
        assert len(p.greeting_patterns) >= 1
        assert len(p.conversation_starters) >= 1

    def test_asdict_contains_required_keys(self, system_no_yaml: PersonalitySystem) -> None:
        d = asdict(system_no_yaml.default_persona)
        for key in ("name", "traits", "tone", "personality_prompt", "created_at"):
            assert key in d, f"key '{key}' missing in asdict result"


# ---------- PersonalitySystem core ----------

class TestPersonalitySystemInit:
    def test_init_uses_default_persona_without_yaml(
        self, system_no_yaml: PersonalitySystem
    ) -> None:
        assert system_no_yaml.current_persona is not None
        assert system_no_yaml.current_persona.name == "pure_gal"

    def test_init_loads_config_defaults_when_no_file(
        self, system_no_yaml: PersonalitySystem
    ) -> None:
        assert system_no_yaml.config["enable_personality"] is True
        assert system_no_yaml.config["default_persona"] == "pure_gal"

    def test_init_loads_config_from_json(self, tmp_path: Path) -> None:
        cfg = tmp_path / "cfg.json"
        cfg.write_text(
            json.dumps({"enable_personality": True, "default_persona": "pure_gal"}),
            encoding="utf-8",
        )
        with patch.object(PersonalitySystem, "_load_persona_from_yaml", return_value=None):
            system = PersonalitySystem(config_path=cfg)
        assert system.config["enable_personality"] is True


class TestPersonalitySystemPrompt:
    def test_get_personality_prompt_returns_nonempty_str(
        self, system_no_yaml: PersonalitySystem
    ) -> None:
        prompt = system_no_yaml.get_personality_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 50

    def test_apply_prompt_report_context_injects_fact_instruction(
        self, system_no_yaml: PersonalitySystem
    ) -> None:
        result = system_no_yaml.apply_personality_to_prompt("テスト報告", context="report")
        assert "テスト報告" in result
        assert "事実" in result

    def test_apply_prompt_conversation_context(
        self, system_no_yaml: PersonalitySystem
    ) -> None:
        result = system_no_yaml.apply_personality_to_prompt("こんにちは", context="conversation")
        assert "こんにちは" in result

    def test_apply_prompt_no_context_appends_base(
        self, system_no_yaml: PersonalitySystem
    ) -> None:
        base = "任意プロンプト"
        result = system_no_yaml.apply_personality_to_prompt(base)
        assert base in result

    def test_apply_prompt_disabled_returns_base_unchanged(
        self, tmp_path: Path
    ) -> None:
        cfg = tmp_path / "cfg.json"
        cfg.write_text(
            json.dumps({"enable_personality": False}), encoding="utf-8"
        )
        with patch.object(PersonalitySystem, "_load_persona_from_yaml", return_value=None):
            system = PersonalitySystem(config_path=cfg)
        base = "Hello world"
        assert system.apply_personality_to_prompt(base) == base


class TestPersonalitySystemPersona:
    def test_get_current_persona_returns_dict(
        self, system_no_yaml: PersonalitySystem
    ) -> None:
        persona = system_no_yaml.get_current_persona()
        assert isinstance(persona, dict)
        assert "name" in persona
        assert "personality_prompt" in persona

    def test_update_persona_name(
        self, system_with_storage: PersonalitySystem
    ) -> None:
        updated = system_with_storage.update_persona({"name": "custom_persona"})
        assert updated.name == "custom_persona"
        assert system_with_storage.current_persona.name == "custom_persona"

    def test_update_persona_tone(
        self, system_with_storage: PersonalitySystem
    ) -> None:
        updated = system_with_storage.update_persona({"tone": "クールで知的"})
        assert updated.tone == "クールで知的"

    def test_update_persona_traits_from_str(
        self, system_with_storage: PersonalitySystem
    ) -> None:
        updated = system_with_storage.update_persona(
            {"traits": ["professional", "humorous"]}
        )
        assert PersonalityTrait.PROFESSIONAL in updated.traits
        assert PersonalityTrait.HUMOROUS in updated.traits

    def test_save_creates_storage_file(
        self, tmp_path: Path, system_with_storage: PersonalitySystem
    ) -> None:
        storage = Path(system_with_storage.config["persona_storage_path"])
        system_with_storage.update_persona({"tone": "saved_tone"})
        assert storage.exists(), "保存処理後 storage ファイルが存在するはず"
        data = json.loads(storage.read_text(encoding="utf-8"))
        assert "profiles" in data


class TestPersonalitySystemYaml:
    def test_yaml_loading_produces_nonempty_name(self, tmp_path: Path) -> None:
        """persona_config.yaml が存在する場合は name が空でないこと"""
        system = PersonalitySystem(config_path=tmp_path / "cfg.json")
        # yaml ロードが成功していれば active_style_preset が name になる
        assert system.current_persona.name != ""

    def test_yaml_fallback_to_default_when_load_returns_none(
        self, system_no_yaml: PersonalitySystem
    ) -> None:
        """YAML ロードを無効化するとデフォルト pure_gal が使われる"""
        assert system_no_yaml.current_persona.name == "pure_gal"


# ---------- 品質強化: 永続化ラウンドトリップ ----------

class TestPersonalitySaveRoundtrip:
    def test_update_and_reload(self, tmp_path: Path) -> None:
        """update_persona 後に PersonalitySystem を再生成しても変更が保持される"""
        storage = tmp_path / "personas.json"
        cfg = tmp_path / "cfg.json"
        cfg.write_text(
            json.dumps({
                "enable_personality": True,
                "default_persona": "pure_gal",
                "persona_storage_path": str(storage),
            }),
            encoding="utf-8",
        )
        with patch.object(PersonalitySystem, "_load_persona_from_yaml", return_value=None):
            sys1 = PersonalitySystem(config_path=cfg)
            sys1.update_persona({"tone": "ぐっとクールに"})

            # 同じ設定で再生成
            sys2 = PersonalitySystem(config_path=cfg)

        assert sys2.current_persona.tone == "ぐっとクールに"

    def test_default_persona_prompt_contains_keyword(self, tmp_path: Path) -> None:
        """デフォルトプロンプトに『清楚系ギャル』が含まれる"""
        with patch.object(PersonalitySystem, "_load_persona_from_yaml", return_value=None):
            sys = PersonalitySystem(config_path=tmp_path / "cfg.json")
        assert "清楚" in sys.default_persona.personality_prompt

    def test_apply_technical_context(self, tmp_path: Path) -> None:
        """technical コンテキストでも base が結果に含まれる"""
        with patch.object(PersonalitySystem, "_load_persona_from_yaml", return_value=None):
            sys = PersonalitySystem(config_path=tmp_path / "cfg.json")
        result = sys.apply_personality_to_prompt("コード解析タスク", context="technical")
        assert "コード解析タスク" in result

    def test_traits_survive_roundtrip(self, tmp_path: Path) -> None:
        """traits が JSON 経由で保存・復元されても PersonalityTrait として扱える"""
        storage = tmp_path / "personas.json"
        cfg = tmp_path / "cfg.json"
        cfg.write_text(
            json.dumps({
                "enable_personality": True,
                "default_persona": "pure_gal",
                "persona_storage_path": str(storage),
            }),
            encoding="utf-8",
        )
        with patch.object(PersonalitySystem, "_load_persona_from_yaml", return_value=None):
            sys1 = PersonalitySystem(config_path=cfg)
            sys1.update_persona({"traits": ["pure", "professional"]})
            sys2 = PersonalitySystem(config_path=cfg)

        # 復元されたトレイトが PersonalityTrait として機能するか確認
        trait_values = [t.value if hasattr(t, "value") else t for t in sys2.current_persona.traits]
        assert "pure" in trait_values
        assert "professional" in trait_values
