"""config_validator_enhanced.py のユニットテスト."""

import json
from pathlib import Path

import pytest

# テスト対象を遅延 import（モジュールレベル副作用を回避）
from config_validator_enhanced import (
    ConfigSchema,
    ConfigValidatorEnhanced,
    ValidationError,
    get_config_validator,
    validate_env,
)


# ======================================================================
# ConfigSchema.validate
# ======================================================================

class TestConfigSchemaValidate:
    """ConfigSchema.validate のテスト."""

    def setup_method(self):
        self.schema = ConfigSchema()

    def test_unknown_schema_returns_valid(self):
        """未知のスキーマ名は True を返す."""
        ok, errors = self.schema.validate(Path("never_seen.json"), {"x": 1})
        assert ok is True
        assert errors == []

    def test_timeout_config_required_field_missing(self):
        """timeouts が無いと必須フィールドエラー."""
        ok, errors = self.schema.validate(
            Path("manaos_timeout_config.json"),
            {},  # timeouts 無し
        )
        assert ok is False
        assert any(e.field == "timeouts" for e in errors)

    def test_timeout_config_valid(self):
        """最小構成で成功."""
        ok, errors = self.schema.validate(
            Path("manaos_timeout_config.json"),
            {"timeouts": {}},  # デフォルト値がセットされる
        )
        assert ok is True
        assert len(errors) == 0

    def test_auto_optimization_state_defaults(self):
        """auto_optimization_state: 空入力でもデフォルトが埋まる."""
        data: dict = {}
        ok, errors = self.schema.validate(
            Path("auto_optimization_state.json"),
            data,
        )
        assert ok is True
        assert data.get("history") == []
        assert data.get("rules") == []
        assert data.get("last_optimization") is None


# ======================================================================
# ConfigSchema._validate_dict — 型/範囲チェック
# ======================================================================

class TestValidateDictTypeChecks:
    """型・範囲バリデーションのテスト."""

    def setup_method(self):
        self.schema = ConfigSchema()

    def test_float_field_range_min_violation(self):
        """min を下回ると warning."""
        data = {"timeouts": {"health_check": 0.1}}  # min=1.0
        _, errors = self.schema.validate(
            Path("manaos_timeout_config.json"), data
        )
        warnings = [e for e in errors if e.severity == "warning"]
        assert len(warnings) >= 1
        assert "1.0 以上" in warnings[0].message

    def test_float_field_range_max_violation(self):
        """max を超えると warning."""
        data = {"timeouts": {"health_check": 999.0}}  # max=60.0
        _, errors = self.schema.validate(
            Path("manaos_timeout_config.json"), data
        )
        warnings = [e for e in errors if e.severity == "warning"]
        assert len(warnings) >= 1
        assert "60.0 以下" in warnings[0].message

    def test_wrong_type_string_for_float(self):
        """float フィールドに文字列を入れるとエラー."""
        data = {"timeouts": {"health_check": "not_a_number"}}
        ok, errors = self.schema.validate(
            Path("manaos_timeout_config.json"), data
        )
        assert ok is False
        type_errors = [e for e in errors if "数値" in e.message]
        assert len(type_errors) >= 1

    def test_dict_field_receives_non_dict(self):
        """dict 型フィールドに文字列を渡すとエラー."""
        data = {"timeouts": "should_be_dict"}
        ok, errors = self.schema.validate(
            Path("manaos_timeout_config.json"), data
        )
        assert ok is False
        assert any("辞書" in e.message for e in errors)

    def test_null_allowed_in_multi_type(self):
        """["str","null"] フィールドは None を許容."""
        data = {"history": [], "rules": [], "last_optimization": None}
        ok, errors = self.schema.validate(
            Path("auto_optimization_state.json"), data
        )
        assert ok is True


# ======================================================================
# ConfigValidatorEnhanced
# ======================================================================

class TestConfigValidatorEnhanced:
    """ConfigValidatorEnhanced のテスト."""

    def test_file_not_found(self, tmp_path: Path):
        v = ConfigValidatorEnhanced()
        ok, errors, data = v.validate_config_file(tmp_path / "nonexist.json")
        assert ok is False
        assert any("見つかりません" in e.message for e in errors)

    def test_unsupported_extension(self, tmp_path: Path):
        bad = tmp_path / "test.toml"
        bad.write_text("x = 1", encoding="utf-8")
        v = ConfigValidatorEnhanced()
        ok, errors, _ = v.validate_config_file(bad)
        assert ok is False
        assert any("サポートされていない" in e.message for e in errors)

    def test_valid_json_config(self, tmp_path: Path):
        """正常な JSON 設定ファイルの検証."""
        cfg = tmp_path / "manaos_timeout_config.json"
        cfg.write_text(json.dumps({"timeouts": {"health_check": 5.0}}), encoding="utf-8")
        v = ConfigValidatorEnhanced()
        ok, errors, data = v.validate_config_file(cfg)
        assert ok is True
        assert data["timeouts"]["health_check"] == 5.0

    def test_cached_after_validation(self, tmp_path: Path):
        """検証後のキャッシュに保存されている."""
        cfg = tmp_path / "manaos_timeout_config.json"
        cfg.write_text(json.dumps({"timeouts": {}}), encoding="utf-8")
        v = ConfigValidatorEnhanced()
        v.validate_config_file(cfg)
        assert v.get_validated_config(cfg) is not None

    def test_validate_all_configs_returns_dict(self, tmp_path: Path):
        """validate_all_configs は辞書を返す."""
        cfg = tmp_path / "manaos_timeout_config.json"
        cfg.write_text(json.dumps({"timeouts": {}}), encoding="utf-8")
        v = ConfigValidatorEnhanced()
        results = v.validate_all_configs(tmp_path)
        assert isinstance(results, dict)
        assert len(results) >= 1


# ======================================================================
# get_config_validator シングルトン
# ======================================================================

def test_singleton():
    """シングルトンが同一インスタンスを返す."""
    import config_validator_enhanced as mod
    mod._validator = None          # リセット
    a = get_config_validator()
    b = get_config_validator()
    assert a is b
    mod._validator = None          # クリーンアップ


# ======================================================================
# ポート重複検出
# ======================================================================

class TestUniquePortValidation:
    def setup_method(self):
        self.schema = ConfigSchema()

    def test_no_duplicate_ports(self):
        data = {
            "manaos_services": {"a": {"port": 5100}, "b": {"port": 5101}},
            "integration_services": {"c": {"port": 9500}},
        }
        errors = self.schema.validate_unique_ports(data)
        assert len(errors) == 0

    def test_duplicate_port_detected(self):
        data = {
            "manaos_services": {"a": {"port": 5100}, "b": {"port": 5100}},
            "integration_services": {},
        }
        errors = self.schema.validate_unique_ports(data)
        assert len(errors) == 1
        assert "重複" in errors[0].message

    def test_port_out_of_range(self):
        data = {
            "manaos_services": {"a": {"port": 80}},
            "integration_services": {},
        }
        errors = self.schema.validate_unique_ports(data)
        assert any("範囲外" in e.message for e in errors)


# ======================================================================
# manaos_integration_config.json スキーマ
# ======================================================================

class TestIntegrationConfigSchema:
    def setup_method(self):
        self.schema = ConfigSchema()

    def test_valid_integration_config(self):
        data = {
            "manaos_services": {"x": {"port": 5100}},
            "integration_services": {"y": {"port": 9500}},
        }
        ok, errors = self.schema.validate(
            Path("manaos_integration_config.json"), data
        )
        assert ok is True

    def test_missing_required_section(self):
        ok, errors = self.schema.validate(
            Path("manaos_integration_config.json"),
            {"manaos_services": {}},
        )
        assert ok is False
        assert any("integration_services" in e.field for e in errors)


# ======================================================================
# validate_env
# ======================================================================

class TestValidateEnv:
    def test_required_missing(self, monkeypatch):
        monkeypatch.delenv("COMFYUI_URL", raising=False)
        monkeypatch.delenv("OLLAMA_URL", raising=False)
        ok, errors = validate_env(
            required=["COMFYUI_URL", "OLLAMA_URL"], recommended=[]
        )
        assert ok is False
        assert len(errors) == 2

    def test_required_present(self, monkeypatch):
        monkeypatch.setenv("COMFYUI_URL", "http://127.0.0.1:8188")
        monkeypatch.setenv("OLLAMA_URL", "http://127.0.0.1:11434")
        ok, errors = validate_env(
            required=["COMFYUI_URL", "OLLAMA_URL"], recommended=[]
        )
        assert ok is True

    def test_recommended_missing_is_warning(self, monkeypatch):
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        ok, errors = validate_env(
            required=[], recommended=["GITHUB_TOKEN"]
        )
        assert ok is True  # warning only
        assert any(e.severity == "warning" for e in errors)
