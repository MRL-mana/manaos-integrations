"""Tests for validate_ledger.py — offline unit tests (no services required)."""
from __future__ import annotations

import pytest

from validate_ledger import ServiceRef, parse_services, validate_basic, validate_tier_integrity


# ─── helpers ────────────────────────────────────────────────────────────────

def _minimal_ledger(**overrides):
    """Return a minimal valid ledger dict, merging overrides into core."""
    base = {
        "core": {
            "memory":      {"port": 5105, "url": "http://127.0.0.1:5105", "enabled": True, "depends_on": [], "tier": 0,
                            "start_cmd": "python memory_server.py"},
            "learning":    {"port": 5126, "url": "http://127.0.0.1:5126", "enabled": True, "depends_on": [], "tier": 1,
                            "start_cmd": "python learning_server.py"},
            "llm_routing": {"port": 5111, "url": "http://127.0.0.1:5111", "enabled": True, "depends_on": [], "tier": 0,
                            "start_cmd": "python llm_routing_server.py"},
            "unified_api": {"port": 9502, "url": "http://127.0.0.1:9502", "enabled": True, "depends_on": [], "tier": 0,
                            "start_cmd": "python unified_api_server.py"},
        },
    }
    base["core"].update(overrides)
    return base


# ─── parse_services ──────────────────────────────────────────────────────────

class TestParseServices:
    def test_basic_parse(self):
        ledger = _minimal_ledger()
        services = parse_services(ledger)
        assert "memory" in services
        assert services["memory"].port == 5105
        assert services["memory"].tier == 0

    def test_optional_group_parsed(self):
        ledger = _minimal_ledger()
        ledger["optional"] = {
            "comfyui": {"port": 8188, "url": "http://127.0.0.1:8188", "enabled": True,
                        "depends_on": [], "tier": 2},
        }
        services = parse_services(ledger)
        assert "comfyui" in services
        assert services["comfyui"].group == "optional"

    def test_start_cmd_captured(self):
        ledger = _minimal_ledger()
        services = parse_services(ledger)
        assert services["unified_api"].start_cmd == "python unified_api_server.py"

    def test_start_cmd_none_for_virtual(self):
        ledger = _minimal_ledger()
        ledger["optional"] = {
            "shell_ui": {"port": 9502, "url": "http://127.0.0.1:9502", "enabled": True,
                         "depends_on": ["unified_api"], "tier": 2, "start_cmd": None},
        }
        services = parse_services(ledger)
        assert services["shell_ui"].start_cmd is None

    def test_invalid_service_dict_raises(self):
        ledger = {"core": {"bad": "not-a-dict"}}
        with pytest.raises(ValueError, match="must be a dict"):
            parse_services(ledger)

    def test_invalid_port_type_raises(self):
        ledger = _minimal_ledger(
            extra={"port": "not-int", "url": "http://x", "enabled": True, "depends_on": [], "tier": 1}
        )
        with pytest.raises(ValueError, match="port must be int"):
            parse_services(ledger)

    def test_depends_on_not_list_raises(self):
        ledger = _minimal_ledger(
            extra={"port": 9999, "url": "http://x", "enabled": True, "depends_on": "bad", "tier": 1}
        )
        with pytest.raises(ValueError, match="depends_on must be a list"):
            parse_services(ledger)


# ─── validate_basic ──────────────────────────────────────────────────────────

class TestValidateBasic:
    def test_no_errors_on_valid_ledger(self):
        services = parse_services(_minimal_ledger())
        assert validate_basic(services) == []

    def test_port_conflict_detected(self):
        ledger = _minimal_ledger(
            conflict={"port": 5105, "url": "http://127.0.0.1:5105", "enabled": True,
                      "depends_on": [], "tier": 1, "start_cmd": "python conflict.py"}
        )
        services = parse_services(ledger)
        errors = validate_basic(services)
        assert any("Port conflict" in e and "5105" in e for e in errors)

    def test_virtual_service_skips_port_conflict(self):
        """shell_ui shares port 9502 with unified_api but has start_cmd=None -> not a conflict."""
        ledger = _minimal_ledger()
        ledger["optional"] = {
            "shell_ui": {"port": 9502, "url": "http://127.0.0.1:9502", "enabled": True,
                         "depends_on": ["unified_api"], "tier": 2, "start_cmd": None},
        }
        services = parse_services(ledger)
        errors = validate_basic(services)
        assert not any("Port conflict" in e for e in errors)

    def test_unknown_depends_on(self):
        ledger = _minimal_ledger(
            svc_with_bad_dep={"port": 9999, "url": "http://x", "enabled": True,
                              "depends_on": ["nonexistent_svc"], "tier": 1}
        )
        services = parse_services(ledger)
        errors = validate_basic(services)
        assert any("Unknown depends_on" in e and "nonexistent_svc" in e for e in errors)

    def test_missing_required_core_service(self):
        ledger = {"core": {
            "memory":      {"port": 5105, "url": "http://x", "enabled": True, "depends_on": [], "tier": 0},
            "learning":    {"port": 5126, "url": "http://x", "enabled": True, "depends_on": [], "tier": 1},
            # llm_routing missing
            "unified_api": {"port": 9502, "url": "http://x", "enabled": True, "depends_on": [], "tier": 0},
        }}
        services = parse_services(ledger)
        errors = validate_basic(services)
        assert any("llm_routing" in e for e in errors)

    def test_enabled_no_port_or_url(self):
        ledger = _minimal_ledger(
            orphan={"port": None, "url": None, "enabled": True, "depends_on": [], "tier": 1}
        )
        services = parse_services(ledger)
        errors = validate_basic(services)
        assert any("orphan" in e and "neither port nor url" in e for e in errors)


# ─── validate_tier_integrity ─────────────────────────────────────────────────

class TestValidateTierIntegrity:
    def test_no_violations_on_valid(self):
        services = parse_services(_minimal_ledger())
        assert validate_tier_integrity(services) == []

    def test_core_depends_on_optional_is_violation(self):
        ledger = _minimal_ledger()
        ledger["optional"] = {
            "opt_svc": {"port": 8800, "url": "http://x", "enabled": True,
                        "depends_on": [], "tier": 2},
        }
        # patch memory to depend on optional service
        ledger["core"]["memory"]["depends_on"] = ["opt_svc"]
        services = parse_services(ledger)
        errors = validate_tier_integrity(services)
        assert any("core service" in e and "optional" in e for e in errors)

    def test_high_priority_tier_depends_on_lower_is_violation(self):
        ledger = _minimal_ledger()
        # memory (tier 0) depending on learning (tier 1) = violation
        ledger["core"]["memory"]["depends_on"] = ["learning"]
        services = parse_services(ledger)
        errors = validate_tier_integrity(services)
        assert any("Tier violation" in e and "memory" in e for e in errors)

    def test_lower_priority_depending_on_higher_is_ok(self):
        ledger = _minimal_ledger()
        # learning (tier 1) → memory (tier 0): fine
        ledger["core"]["learning"]["depends_on"] = ["memory"]
        services = parse_services(ledger)
        assert validate_tier_integrity(services) == []
