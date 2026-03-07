#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for tools/validate_ledger.py — validate_basic, validate_tier_integrity."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# リポジトリルートと tools/ を sys.path に追加 (test_check_blast_radius.py と同じパターン)
_ROOT = Path(__file__).resolve().parents[1]
for _p in (_ROOT, _ROOT / "tools"):
    _s = str(_p)
    if _s not in sys.path:
        sys.path.insert(0, _s)

from validate_ledger import (  # noqa: E402
    ServiceRef,
    parse_services,
    validate_basic,
    validate_tier_integrity,
    validate_readme,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _svc(
    name: str,
    group: str = "core",
    port: int | None = 5000,
    url: str | None = None,
    enabled: bool = True,
    depends_on: list[str] | None = None,
    tier: int = 1,
    start_cmd: str | None = "python server.py",
) -> ServiceRef:
    return ServiceRef(
        name=name,
        group=group,
        port=port,
        url=url,
        enabled=enabled,
        depends_on=depends_on or [],
        tier=tier,
        start_cmd=start_cmd,
    )


def _services(*svcs: ServiceRef) -> dict[str, ServiceRef]:
    return {s.name: s for s in svcs}


# ---------------------------------------------------------------------------
# validate_basic — port conflict
# ---------------------------------------------------------------------------

class TestValidateBasicPortConflict:
    def test_no_conflict_ok(self):
        svcs = _services(_svc("a", port=5001), _svc("b", port=5002))
        errors = validate_basic(svcs)
        # これらの 2 サービスは required_core_services に含まれないので
        # "Missing core service" エラーが出るが port conflict エラーは出ない
        port_errors = [e for e in errors if "Port conflict" in e]
        assert port_errors == []

    def test_duplicate_port_detected(self):
        svcs = _services(_svc("a", port=9999), _svc("b", port=9999))
        errors = validate_basic(svcs)
        port_errors = [e for e in errors if "Port conflict" in e]
        assert len(port_errors) == 1
        assert "9999" in port_errors[0]

    def test_null_port_no_conflict(self):
        """port=None のサービスが複数あっても conflict にならない"""
        svcs = _services(_svc("a", port=None), _svc("b", port=None))
        errors = validate_basic(svcs)
        port_errors = [e for e in errors if "Port conflict" in e]
        assert port_errors == []


# ---------------------------------------------------------------------------
# validate_basic — unknown depends_on
# ---------------------------------------------------------------------------

class TestValidateBasicDepsUnknown:
    def test_unknown_dependency_detected(self):
        svc = _svc("a", depends_on=["ghost_service"])
        svcs = _services(svc)
        errors = validate_basic(svcs)
        dep_errors = [e for e in errors if "Unknown depends_on" in e]
        assert any("ghost_service" in e for e in dep_errors)

    def test_known_dependency_ok(self):
        svcs = _services(_svc("a", port=5001, depends_on=["b"]), _svc("b", port=5002))
        errors = validate_basic(svcs)
        dep_errors = [e for e in errors if "Unknown depends_on" in e]
        assert dep_errors == []


# ---------------------------------------------------------------------------
# validate_basic — required core services
# ---------------------------------------------------------------------------

class TestValidateBasicRequiredCore:
    def _full_core(self) -> dict[str, ServiceRef]:
        return _services(
            _svc("memory",      port=5105, group="core", tier=0),
            _svc("learning",    port=5126, group="core", tier=1),
            _svc("llm_routing", port=5111, group="core", tier=0),
            _svc("unified_api", port=9502, group="core", tier=0),
        )

    def test_all_required_present_no_error(self):
        svcs = self._full_core()
        errors = validate_basic(svcs)
        missing = [e for e in errors if "Missing core service" in e]
        wrong_group = [e for e in errors if "must be under core" in e]
        assert missing == []
        assert wrong_group == []

    def test_missing_memory_detected(self):
        svcs = self._full_core()
        del svcs["memory"]
        errors = validate_basic(svcs)
        assert any("memory" in e for e in errors)

    def test_required_service_in_wrong_group_detected(self):
        svcs = self._full_core()
        svcs["memory"] = _svc("memory", port=5105, group="optional", tier=2)
        errors = validate_basic(svcs)
        assert any("must be under core" in e and "memory" in e for e in errors)


# ---------------------------------------------------------------------------
# validate_tier_integrity — core → optional violation
# ---------------------------------------------------------------------------

class TestValidateTierIntegrityGroupViolation:
    def test_core_depends_on_optional_raises_error(self):
        svcs = _services(
            _svc("core_svc",     group="core",     port=5001, tier=1, depends_on=["opt_svc"]),
            _svc("opt_svc",      group="optional", port=5002, tier=2),
        )
        errors = validate_tier_integrity(svcs)
        assert any("core_svc" in e and "optional" in e for e in errors)

    def test_optional_depends_on_core_is_ok(self):
        """optional が core に依存するのは正常"""
        svcs = _services(
            _svc("core_svc", group="core",     port=5001, tier=1),
            _svc("opt_svc",  group="optional", port=5002, tier=2, depends_on=["core_svc"]),
        )
        errors = validate_tier_integrity(svcs)
        assert errors == []

    def test_optional_depends_on_optional_is_ok(self):
        svcs = _services(
            _svc("opt_a", group="optional", port=5001, tier=2),
            _svc("opt_b", group="optional", port=5002, tier=2, depends_on=["opt_a"]),
        )
        errors = validate_tier_integrity(svcs)
        assert errors == []


# ---------------------------------------------------------------------------
# validate_tier_integrity — tier regression (priority inversion)
# ---------------------------------------------------------------------------

class TestValidateTierIntegrityRegression:
    def test_tier0_depends_on_tier1_raises_error(self):
        svcs = _services(
            _svc("high", group="core", port=5001, tier=0, depends_on=["low"]),
            _svc("low",  group="core", port=5002, tier=1),
        )
        errors = validate_tier_integrity(svcs)
        assert any("high" in e and "tier 0" in e for e in errors)

    def test_tier1_depends_on_tier2_raises_error(self):
        svcs = _services(
            _svc("mid",  group="core",     port=5001, tier=1, depends_on=["bot"]),
            _svc("bot",  group="optional", port=5002, tier=2),
        )
        errors = validate_tier_integrity(svcs)
        # core→optional 違反 と tier regression 違反の両方が出る
        assert len(errors) >= 1

    def test_same_tier_ok(self):
        svcs = _services(
            _svc("a", group="core", port=5001, tier=1, depends_on=["b"]),
            _svc("b", group="core", port=5002, tier=1),
        )
        errors = validate_tier_integrity(svcs)
        assert errors == []

    def test_no_deps_no_errors(self):
        svcs = _services(
            _svc("a", group="core",     port=5001, tier=0),
            _svc("b", group="optional", port=5002, tier=2),
        )
        errors = validate_tier_integrity(svcs)
        assert errors == []

    def test_unknown_dep_is_skipped(self):
        """validate_basic でキャッチ済みの unknown dep は tier チェックを skips"""
        svcs = _services(
            _svc("a", group="core", port=5001, tier=0, depends_on=["nonexistent"]),
        )
        errors = validate_tier_integrity(svcs)
        # nonexistent は services にないので continue → エラー出ない
        assert errors == []


# ---------------------------------------------------------------------------
# parse_services — tier field extraction
# ---------------------------------------------------------------------------

class TestParseServicesLedsger:
    def test_tier_default_optional(self):
        """optional グループでtier未指定 → 2"""
        ledger = {
            "core": {},
            "optional": {"svc_x": {"port": 5050, "enabled": True}},
        }
        svcs = parse_services(ledger)
        assert svcs["svc_x"].tier == 2

    def test_tier_default_core(self):
        """core グループでtier未指定 → 1"""
        ledger = {
            "core": {"svc_y": {"port": 5051, "enabled": True}},
            "optional": {},
        }
        svcs = parse_services(ledger)
        assert svcs["svc_y"].tier == 1

    def test_tier_explicit_override(self):
        ledger = {
            "core": {"svc_z": {"port": 5052, "enabled": True, "tier": 0}},
            "optional": {},
        }
        svcs = parse_services(ledger)
        assert svcs["svc_z"].tier == 0

    def test_depends_on_parsed(self):
        ledger = {
            "core": {
                "svc_a": {"port": 5001, "enabled": True, "depends_on": ["svc_b"]},
                "svc_b": {"port": 5002, "enabled": True},
            },
            "optional": {},
        }
        svcs = parse_services(ledger)
        assert "svc_b" in svcs["svc_a"].depends_on


# ---------------------------------------------------------------------------
# validate_readme — lightweight smoke
# ---------------------------------------------------------------------------

class TestValidateReadme:
    def test_nonexistent_readme_returns_no_errors(self, tmp_path):
        result = validate_readme(str(tmp_path / "MISSING.md"))
        assert result == []

    def test_readme_missing_ssot_ref_errors(self, tmp_path):
        readme = tmp_path / "README.md"
        readme.write_text("# Docs\nNo mention of ledger here.", encoding="utf-8")
        errors = validate_readme(str(readme))
        assert any("services_ledger" in e for e in errors)

    def test_readme_with_ssot_ref_ok(self, tmp_path):
        readme = tmp_path / "README.md"
        readme.write_text("See config/services_ledger.yaml for details.", encoding="utf-8")
        errors = validate_readme(str(readme))
        ssot_errors = [e for e in errors if "services_ledger" in e]
        assert ssot_errors == []


# ---------------------------------------------------------------------------
# Integration smoke — real ledger file
# ---------------------------------------------------------------------------

class TestRealLedgerIntegration:
    LEDGER = Path(__file__).resolve().parent.parent / "config" / "services_ledger.yaml"

    def test_real_ledger_parse_succeeds(self):
        if not self.LEDGER.exists():
            pytest.skip("services_ledger.yaml not found")
        import yaml
        with open(self.LEDGER, encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)
        svcs = parse_services(raw)
        assert len(svcs) > 0

    def test_real_ledger_tier_integrity_clean(self):
        if not self.LEDGER.exists():
            pytest.skip("services_ledger.yaml not found")
        import yaml
        with open(self.LEDGER, encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)
        svcs = parse_services(raw)
        errors = validate_tier_integrity(svcs)
        assert errors == [], f"Tier integrity failures: {errors}"
