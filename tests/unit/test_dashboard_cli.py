"""Unit tests for tools/dashboard_cli.py pure functions."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tools"))
from dashboard_cli import (
    ServiceRow,
    _bfs_blast,
    _build_rev_deps,
    code_to_state,
    colorize,
    dependency_alerts,
    load_ledger,
    normalize_rows,
)

# ─────────────────────────────────────────────────────────────────────────────
# colorize
# ─────────────────────────────────────────────────────────────────────────────

class TestColorize:
    def test_no_color_returns_plain(self):
        assert colorize("hello", "ok", False) == "hello"

    def test_use_color_wraps_with_ansi(self):
        result = colorize("UP", "ok", True)
        assert "\x1b[" in result
        assert "UP" in result

    def test_unknown_tone_returns_text(self):
        # 未知のトーンは ANSI なしのまま返す
        result = colorize("text", "unknown_tone", True)
        assert "text" in result

    def test_fail_tone_wraps_red_ish(self):
        result = colorize("DOWN", "fail", True)
        assert "\x1b[" in result
        assert "DOWN" in result


# ─────────────────────────────────────────────────────────────────────────────
# code_to_state
# ─────────────────────────────────────────────────────────────────────────────

class TestCodeToState:
    def test_none_returns_unknown(self):
        assert code_to_state(None) == "UNKNOWN"

    def test_200_returns_ok(self):
        assert code_to_state(200) == "OK"

    def test_404_returns_no_endpoint(self):
        assert code_to_state(404) == "NO_ENDPOINT"

    def test_minus_one_returns_timeout(self):
        assert code_to_state(-1) == "TIMEOUT"

    def test_minus_two_returns_down(self):
        assert code_to_state(-2) == "DOWN"

    def test_500_returns_http_500(self):
        assert code_to_state(500) == "HTTP_500"

    def test_401_returns_http_401(self):
        assert code_to_state(401) == "HTTP_401"


# ─────────────────────────────────────────────────────────────────────────────
# load_ledger
# ─────────────────────────────────────────────────────────────────────────────

class TestLoadLedger:
    def test_valid_yaml_returns_dict(self, tmp_path):
        f = tmp_path / "ledger.yaml"
        f.write_text("core:\n  svc_a:\n    port: 8000\n", encoding="utf-8")
        result = load_ledger(str(f))
        assert isinstance(result, dict)
        assert "core" in result

    def test_non_dict_root_raises_value_error(self, tmp_path):
        f = tmp_path / "bad.yaml"
        f.write_text("- item1\n- item2\n", encoding="utf-8")
        with pytest.raises(ValueError, match="ledger root must be mapping"):
            load_ledger(str(f))

    def test_missing_file_raises_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_ledger(str(tmp_path / "nosuchfile.yaml"))


# ─────────────────────────────────────────────────────────────────────────────
# normalize_rows
# ─────────────────────────────────────────────────────────────────────────────

class TestNormalizeRows:
    def _ledger(self):
        return {
            "core": {
                "svc_a": {"enabled": True, "port": 8000},
                "svc_b": {"enabled": False, "url": "http://localhost:9000"},
            },
            "optional": {
                "svc_c": {"enabled": True, "port": 7777, "depends_on": ["svc_a"]},
            },
        }

    def test_correct_row_count(self):
        rows = normalize_rows(self._ledger())
        assert len(rows) == 3

    def test_section_assigned(self):
        rows = normalize_rows(self._ledger())
        sections = {r.name: r.section for r in rows}
        assert sections["svc_a"] == "core"
        assert sections["svc_c"] == "optional"

    def test_enabled_flag_parsed(self):
        rows = normalize_rows(self._ledger())
        name_map = {r.name: r for r in rows}
        assert name_map["svc_a"].enabled is True
        assert name_map["svc_b"].enabled is False

    def test_url_generated_from_port(self):
        rows = normalize_rows(self._ledger())
        name_map = {r.name: r for r in rows}
        assert name_map["svc_a"].url == "http://127.0.0.1:8000"

    def test_depends_on_parsed(self):
        rows = normalize_rows(self._ledger())
        name_map = {r.name: r for r in rows}
        assert "svc_a" in name_map["svc_c"].depends_on

    def test_empty_ledger_returns_empty_list(self):
        assert normalize_rows({}) == []

    def test_non_dict_section_skipped(self):
        ledger = {"core": ["not", "a", "dict"]}
        rows = normalize_rows(ledger)
        assert rows == []


# ─────────────────────────────────────────────────────────────────────────────
# dependency_alerts
# ─────────────────────────────────────────────────────────────────────────────

def _row(name, enabled=True, summary="OK", depends_on=None, section="core"):
    r = ServiceRow(
        section=section, name=name, enabled=enabled,
        port=None, url="", depends_on=depends_on or [],
    )
    r.summary = summary
    return r


class TestDependencyAlerts:
    def test_no_deps_no_alerts(self):
        rows = [_row("a"), _row("b")]
        assert dependency_alerts(rows) == []

    def test_dep_ok_produces_ok_alert(self):
        a = _row("a", depends_on=["b"])
        b = _row("b", summary="OK")
        alerts = dependency_alerts([a, b])
        assert any("OK" in alert for alert in alerts)

    def test_missing_dep_flagged(self):
        a = _row("a", depends_on=["missing"])
        alerts = dependency_alerts([a])
        assert any("MISSING" in alert for alert in alerts)

    def test_disabled_dep_flagged(self):
        a = _row("a", depends_on=["b"])
        b = _row("b", enabled=False)
        alerts = dependency_alerts([a, b])
        assert any("DISABLED" in alert for alert in alerts)

    def test_disabled_row_has_no_alerts(self):
        a = _row("a", enabled=False, depends_on=["b"])
        b = _row("b")
        alerts = dependency_alerts([a, b])
        assert alerts == []

    def test_down_dep_flagged(self):
        a = _row("a", depends_on=["b"])
        b = _row("b", summary="DOWN")
        alerts = dependency_alerts([a, b])
        assert any("DOWN" in alert for alert in alerts)


# ─────────────────────────────────────────────────────────────────────────────
# _build_rev_deps + _bfs_blast
# ─────────────────────────────────────────────────────────────────────────────

class TestBuildRevDeps:
    def test_no_deps_returns_empty(self):
        rows = [_row("a"), _row("b")]
        assert _build_rev_deps(rows) == {}

    def test_single_dep(self):
        a = _row("a", depends_on=["b"])
        rev = _build_rev_deps([a, _row("b")])
        assert "a" in rev.get("b", set())

    def test_multiple_dependants(self):
        a = _row("a", depends_on=["c"])
        b = _row("b", depends_on=["c"])
        rev = _build_rev_deps([a, b, _row("c")])
        assert rev["c"] == {"a", "b"}


class TestBfsBlast:
    def test_no_dependants_returns_empty(self):
        assert _bfs_blast("a", {}) == []

    def test_direct_dependants(self):
        rev = {"a": {"b", "c"}}
        result = _bfs_blast("a", rev)
        assert sorted(result) == ["b", "c"]

    def test_transitive_cascade(self):
        # a → b → c chain (a が落ちると b と c が影響)
        rev = {"a": {"b"}, "b": {"c"}}
        result = _bfs_blast("a", rev)
        assert sorted(result) == ["b", "c"]

    def test_diamond_not_duplicated(self):
        # a → b, a → c, both b and c → d
        rev = {"a": {"b", "c"}, "b": {"d"}, "c": {"d"}}
        result = _bfs_blast("a", rev)
        assert sorted(result) == ["b", "c", "d"]
