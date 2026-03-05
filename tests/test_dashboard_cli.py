#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for tools/dashboard_cli.py — blast BFS helpers."""

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

from dashboard_cli import (  # noqa: E402
    ServiceRow,
    _bfs_blast,
    _build_rev_deps,
    print_blast_alerts,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _row(
    name: str,
    depends_on: list[str] | None = None,
    enabled: bool = True,
    summary: str = "OK",
) -> ServiceRow:
    return ServiceRow(
        section="core",
        name=name,
        enabled=enabled,
        port=5000,
        url=f"http://127.0.0.1:5000/{name}",
        depends_on=depends_on or [],
        summary=summary,
    )


# ---------------------------------------------------------------------------
# _build_rev_deps
# ---------------------------------------------------------------------------

class TestBuildRevDeps:
    def test_empty_rows(self):
        assert _build_rev_deps([]) == {}

    def test_single_dep(self):
        rows = [_row("a", depends_on=["b"]), _row("b")]
        rev = _build_rev_deps(rows)
        assert rev == {"b": {"a"}}

    def test_multiple_dependants(self):
        rows = [
            _row("a", depends_on=["x"]),
            _row("b", depends_on=["x"]),
            _row("x"),
        ]
        rev = _build_rev_deps(rows)
        assert rev["x"] == {"a", "b"}

    def test_no_deps_empty_rev(self):
        rows = [_row("a"), _row("b")]
        rev = _build_rev_deps(rows)
        assert rev == {}

    def test_chain_deps(self):
        # a → b → c
        rows = [_row("a", ["b"]), _row("b", ["c"]), _row("c")]
        rev = _build_rev_deps(rows)
        assert rev["b"] == {"a"}
        assert rev["c"] == {"b"}


# ---------------------------------------------------------------------------
# _bfs_blast
# ---------------------------------------------------------------------------

class TestBfsBlast:
    def test_no_downstream(self):
        """依存されていないノードのブラスト半径は空"""
        rev = {}
        assert _bfs_blast("svc_a", rev) == []

    def test_direct_downstream(self):
        rev = {"svc_a": {"svc_b"}}
        result = _bfs_blast("svc_a", rev)
        assert result == ["svc_b"]

    def test_transitive_chain(self):
        # a → b → c  (a がダウンしたら b, c が影響)
        rev = {"a": {"b"}, "b": {"c"}}
        result = _bfs_blast("a", rev)
        assert sorted(result) == ["b", "c"]

    def test_fan_out(self):
        # a → {b, c}
        rev = {"a": {"b", "c"}}
        result = sorted(_bfs_blast("a", rev))
        assert result == ["b", "c"]

    def test_diamond_shape(self):
        # a → b, a → c, b → d, c → d
        rev = {"a": {"b", "c"}, "b": {"d"}, "c": {"d"}}
        result = sorted(_bfs_blast("a", rev))
        # d は b と c 両方から到達できるが 1 回しか数えない
        assert result == ["b", "c", "d"]

    def test_cyclic_tolerance(self):
        """循環があっても無限ループしない"""
        rev = {"a": {"b"}, "b": {"a"}}
        result = _bfs_blast("a", rev)
        assert "b" in result

    def test_returns_sorted_list(self):
        rev = {"a": {"z_svc", "m_svc", "a_svc"}}
        result = _bfs_blast("a", rev)
        assert result == sorted(result)


# ---------------------------------------------------------------------------
# print_blast_alerts
# ---------------------------------------------------------------------------

class TestPrintBlastAlerts:
    def test_no_down_services_no_output(self, capsys):
        rows = [_row("a", summary="OK"), _row("b", summary="OK")]
        print_blast_alerts(rows, use_color=False)
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_disabled_service_skipped(self, capsys):
        rows = [_row("a", summary="DOWN", enabled=False)]
        print_blast_alerts(rows, use_color=False)
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_down_isolated_service_shows_isolated(self, capsys):
        rows = [_row("a", summary="DOWN")]
        print_blast_alerts(rows, use_color=False)
        captured = capsys.readouterr()
        assert "BLAST RISK" in captured.out
        assert "isolated" in captured.out.lower()

    def test_down_service_with_cascade_shows_names(self, capsys):
        rows = [
            _row("a", depends_on=[],    summary="DOWN"),
            _row("b", depends_on=["a"], summary="OK"),
        ]
        print_blast_alerts(rows, use_color=False)
        captured = capsys.readouterr()
        assert "BLAST RISK" in captured.out
        assert "b" in captured.out

    def test_timeout_service_also_triggers_blast(self, capsys):
        rows = [
            _row("a", depends_on=[],    summary="TIMEOUT"),
            _row("b", depends_on=["a"], summary="OK"),
        ]
        print_blast_alerts(rows, use_color=False)
        captured = capsys.readouterr()
        assert "[BLAST]" in captured.out

    def test_truncation_for_many_affected(self, capsys):
        """8 個超えたら '+N more' と表示される"""
        rows = [_row("root", summary="DOWN")] + [
            _row(f"svc_{i:02d}", depends_on=["root"]) for i in range(12)
        ]
        print_blast_alerts(rows, use_color=False)
        captured = capsys.readouterr()
        assert "more" in captured.out

    def test_no_color_flag_strips_ansi(self, capsys):
        rows = [_row("a", summary="DOWN")]
        print_blast_alerts(rows, use_color=False)
        captured = capsys.readouterr()
        assert "\x1b[" not in captured.out

    def test_total_count_shown(self, capsys):
        rows = [
            _row("root", summary="DOWN"),
            _row("child1", depends_on=["root"]),
            _row("child2", depends_on=["root"]),
        ]
        print_blast_alerts(rows, use_color=False)
        captured = capsys.readouterr()
        assert "2 total" in captured.out
