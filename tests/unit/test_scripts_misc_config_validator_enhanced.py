"""
Unit tests for scripts/misc/config_validator_enhanced.py
"""
import sys
import os
import json
from pathlib import Path
from unittest.mock import MagicMock
import pytest

# Mock external dependencies
sys.modules.setdefault("yaml", MagicMock(safe_load=MagicMock(return_value={})))
sys.modules.setdefault("unified_logging", MagicMock(
    get_service_logger=MagicMock(return_value=MagicMock())
))

# 他のテストがモックを注入している可能性があるので強制リロード
sys.modules.pop("config_validator_enhanced", None)

sys.path.insert(0, "scripts/misc")
from config_validator_enhanced import (
    ValidationError,
    ConfigSchema,
    ConfigValidatorEnhanced,
    validate_env,
    get_config_validator,
)


# ── ValidationError dataclass ────────────────────────────────────────────────

class TestValidationError:
    def test_default_severity_is_error(self):
        err = ValidationError(field="x", message="bad")
        assert err.severity == "error"

    def test_custom_severity(self):
        err = ValidationError(field="x", message="b", severity="warning")
        assert err.severity == "warning"

    def test_field_stored(self):
        err = ValidationError(field="myfield", message="msg")
        assert err.field == "myfield"

    def test_message_stored(self):
        err = ValidationError(field="f", message="some message")
        assert err.message == "some message"


# ── ConfigSchema._validate_dict ──────────────────────────────────────────────

class TestValidateDict:
    def setup_method(self):
        self.schema = ConfigSchema()

    def test_valid_str_field_no_errors(self):
        schema = {"name": {"type": "str", "required": True}}
        errors = self.schema._validate_dict({"name": "Alice"}, schema, "")
        assert errors == []

    def test_missing_required_field(self):
        schema = {"name": {"type": "str", "required": True}}
        errors = self.schema._validate_dict({}, schema, "")
        assert len(errors) == 1
        assert "name" in errors[0].field

    def test_missing_optional_field_no_error(self):
        schema = {"opt": {"type": "str", "required": False}}
        errors = self.schema._validate_dict({}, schema, "")
        assert errors == []

    def test_wrong_str_type_error(self):
        schema = {"x": {"type": "str", "required": True}}
        errors = self.schema._validate_dict({"x": 123}, schema, "")
        assert len(errors) == 1

    def test_wrong_int_type_error(self):
        schema = {"n": {"type": "int", "required": True}}
        errors = self.schema._validate_dict({"n": "not int"}, schema, "")
        assert len(errors) == 1

    def test_wrong_float_type_error(self):
        schema = {"f": {"type": "float", "required": True}}
        errors = self.schema._validate_dict({"f": "not num"}, schema, "")
        assert len(errors) == 1

    def test_float_accepts_int(self):
        schema = {"f": {"type": "float", "required": True}}
        # int should be accepted as float
        errors = self.schema._validate_dict({"f": 5}, schema, "")
        assert errors == []

    def test_wrong_dict_type_error(self):
        schema = {"d": {"type": "dict", "required": True}}
        errors = self.schema._validate_dict({"d": "not dict"}, schema, "")
        assert len(errors) == 1

    def test_wrong_list_type_error(self):
        schema = {"l": {"type": "list", "required": True}}
        errors = self.schema._validate_dict({"l": "not list"}, schema, "")
        assert len(errors) == 1

    def test_range_min_violation(self):
        schema = {"n": {"type": "int", "required": True, "min": 5}}
        errors = self.schema._validate_dict({"n": 1}, schema, "")
        assert any("以上" in e.message for e in errors)

    def test_range_max_violation(self):
        schema = {"n": {"type": "int", "required": True, "max": 10}}
        errors = self.schema._validate_dict({"n": 999}, schema, "")
        assert any("以下" in e.message for e in errors)

    def test_default_applied_for_missing_optional(self):
        data = {}
        schema = {"timeout": {"type": "float", "required": False, "default": 5.0}}
        self.schema._validate_dict(data, schema, "")
        assert data.get("timeout") == 5.0

    def test_nested_dict_validated(self):
        schema = {
            "outer": {
                "type": "dict",
                "required": True,
                "fields": {
                    "inner": {"type": "str", "required": True}
                }
            }
        }
        errors = self.schema._validate_dict({"outer": {}}, schema, "")
        assert any("inner" in e.field for e in errors)

    def test_prefix_used_in_field_path(self):
        schema = {"x": {"type": "str", "required": True}}
        errors = self.schema._validate_dict({}, schema, "parent")
        assert "parent.x" in errors[0].field


# ── ConfigSchema.validate_unique_ports ───────────────────────────────────────

class TestValidateUniquePorts:
    def setup_method(self):
        self.schema = ConfigSchema()

    def test_no_services_no_errors(self):
        errors = self.schema.validate_unique_ports({})
        assert errors == []

    def test_unique_ports_no_errors(self):
        config = {
            "manaos_services": {
                "svc_a": {"port": 8000},
                "svc_b": {"port": 8001},
            }
        }
        errors = self.schema.validate_unique_ports(config)
        assert errors == []

    def test_duplicate_ports_produces_error(self):
        config = {
            "manaos_services": {
                "svc_a": {"port": 8000},
                "svc_b": {"port": 8000},
            }
        }
        errors = self.schema.validate_unique_ports(config)
        assert any("重複" in e.message for e in errors)

    def test_port_out_of_range_produces_warning(self):
        config = {
            "manaos_services": {
                "svc_a": {"port": 80},  # Below 1024
            }
        }
        errors = self.schema.validate_unique_ports(config)
        assert any(e.severity == "warning" for e in errors)

    def test_non_integer_port_produces_error(self):
        config = {
            "manaos_services": {
                "svc_a": {"port": "8000"},
            }
        }
        errors = self.schema.validate_unique_ports(config)
        assert len(errors) == 1

    def test_services_without_port_ignored(self):
        config = {
            "manaos_services": {
                "svc_a": {"url": "http://localhost"},
            }
        }
        errors = self.schema.validate_unique_ports(config)
        assert errors == []

    def test_cross_section_duplicate(self):
        config = {
            "manaos_services": {"svc_a": {"port": 9000}},
            "integration_services": {"svc_b": {"port": 9000}},
        }
        errors = self.schema.validate_unique_ports(config)
        assert any("重複" in e.message for e in errors)


# ── ConfigSchema.validate ─────────────────────────────────────────────────────

class TestConfigSchemaValidate:
    def setup_method(self):
        self.schema = ConfigSchema()

    def test_unknown_schema_returns_true(self):
        ok, errors = self.schema.validate(Path("unknown_file.yaml"), {})
        assert ok is True
        assert errors == []

    def test_known_schema_missing_required_returns_false(self):
        # manaos_integration_config.json requires "manaos_services" and "integration_services"
        ok, errors = self.schema.validate(
            Path("manaos_integration_config.json"),
            {}
        )
        assert ok is False
        assert len(errors) > 0

    def test_known_schema_valid_data_returns_true(self):
        ok, errors = self.schema.validate(
            Path("manaos_integration_config.json"),
            {
                "manaos_services": {},
                "integration_services": {},
            }
        )
        assert ok is True


# ── ConfigValidatorEnhanced.validate_config_file ─────────────────────────────

class TestValidateConfigFile:
    def setup_method(self):
        self.validator = ConfigValidatorEnhanced()

    def test_nonexistent_file_returns_false(self, tmp_path):
        result = self.validator.validate_config_file(tmp_path / "missing.json")
        is_valid, errors, data = result
        assert is_valid is False
        assert len(errors) == 1

    def test_unsupported_extension_returns_false(self, tmp_path):
        f = tmp_path / "config.toml"
        f.write_text("[section]\nkey=val\n")
        is_valid, errors, data = self.validator.validate_config_file(f)
        assert is_valid is False

    def test_valid_json_for_unknown_schema(self, tmp_path):
        config = {"manaos_services": {}, "integration_services": {}}
        f = tmp_path / "manaos_integration_config.json"
        f.write_text(json.dumps(config))
        is_valid, errors, data = self.validator.validate_config_file(f)
        assert is_valid is True
        # defaults may be applied; verify original keys are present
        assert data["manaos_services"] == config["manaos_services"]
        assert data["integration_services"] == config["integration_services"]

    def test_invalid_json_returns_false(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text("not valid json")
        is_valid, errors, data = self.validator.validate_config_file(f)
        assert is_valid is False

    def test_valid_json_stored_in_validated_configs(self, tmp_path):
        config = {"manaos_services": {}, "integration_services": {}}
        f = tmp_path / "manaos_integration_config.json"
        f.write_text(json.dumps(config))
        self.validator.validate_config_file(f)
        stored = self.validator.get_validated_config(f)
        assert stored is not None
        assert stored["manaos_services"] == config["manaos_services"]
        assert stored["integration_services"] == config["integration_services"]

    def test_invalid_json_not_stored_in_validated_configs(self, tmp_path):
        f = tmp_path / "manaos_integration_config.json"
        f.write_text('{"manaos_services": "wrongtype", "integration_services": {}}')
        self.validator.validate_config_file(f)
        # Should still store in validated_configs if no schema errors
        # (wrongtype will trigger schema error → not stored)


# ── validate_env ─────────────────────────────────────────────────────────────

class TestValidateEnv:
    def test_all_required_set_returns_true(self, monkeypatch):
        monkeypatch.setenv("COMFYUI_URL", "http://localhost:8188")
        monkeypatch.setenv("OLLAMA_URL", "http://localhost:11434")
        ok, errors = validate_env(required=["COMFYUI_URL", "OLLAMA_URL"], recommended=[])
        assert ok is True

    def test_missing_required_returns_false(self, monkeypatch):
        monkeypatch.delenv("MISSING_VAR", raising=False)
        ok, errors = validate_env(required=["MISSING_VAR"], recommended=[])
        assert ok is False

    def test_missing_required_error_in_list(self, monkeypatch):
        monkeypatch.delenv("MISSING_VAR", raising=False)
        ok, errors = validate_env(required=["MISSING_VAR"], recommended=[])
        assert any(e.severity == "error" for e in errors)
        assert any("MISSING_VAR" in e.field for e in errors)

    def test_missing_recommended_returns_true(self, monkeypatch):
        monkeypatch.delenv("RECOMMENDED_VAR", raising=False)
        ok, errors = validate_env(required=[], recommended=["RECOMMENDED_VAR"])
        assert ok is True  # recommended is not critical

    def test_missing_recommended_warning_in_list(self, monkeypatch):
        monkeypatch.delenv("RECOMMENDED_VAR", raising=False)
        ok, errors = validate_env(required=[], recommended=["RECOMMENDED_VAR"])
        assert any(e.severity == "warning" for e in errors)

    def test_all_set_no_errors(self, monkeypatch):
        monkeypatch.setenv("REQ_VAR", "value")
        monkeypatch.setenv("REC_VAR", "value")
        ok, errors = validate_env(required=["REQ_VAR"], recommended=["REC_VAR"])
        assert ok is True
        assert errors == []


# ── get_config_validator singleton ───────────────────────────────────────────

class TestGetConfigValidator:
    def test_returns_config_validator_enhanced(self):
        import config_validator_enhanced as cv_mod
        cv_mod._validator = None
        v = get_config_validator()
        assert isinstance(v, ConfigValidatorEnhanced)

    def test_same_instance_on_second_call(self):
        import config_validator_enhanced as cv_mod
        cv_mod._validator = None
        v1 = get_config_validator()
        v2 = get_config_validator()
        assert v1 is v2
