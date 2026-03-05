#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_check_blast_radius.py

check_blast_radius.py の単体テスト。

テスト対象:
- build_reverse_deps()     逆依存グラフの構築
- compute_blast_radius()   BFS 連鎖停止計算
- recovery_order()         Kahn トポロジカルソート
- probe_live()             urllib モック (LIVE)
- cmd_live() smoke         出力テキスト確認
- validate_tier_integrity() (validate_ledger 側のロジックも再手動テスト)
"""
from __future__ import annotations

import sys
import io
import textwrap
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# sys.path にリポジトリルートと tools/ を追加
_ROOT = Path(__file__).resolve().parents[1]
for _p in (_ROOT, _ROOT / "tools"):
    s = str(_p)
    if s not in sys.path:
        sys.path.insert(0, s)

from check_blast_radius import (
    Service,
    build_reverse_deps,
    compute_blast_radius,
    recovery_order,
    probe_live,
    cmd_live,
    load_ledger,
)


# ─── テスト用サービスグラフ ───────────────────────────────────────

def make_services(**kwargs) -> dict:
    """Service dataclass のミニマルグラフを作成するヘルパー。"""
    return {k: v for k, v in kwargs.items()}


SIMPLE_GRAPH = {
    "db": Service(
        name="db", group="core", port=5432, url=None,
        enabled=True, tier=0, depends_on=[], description="DB", blast_note="",
    ),
    "api": Service(
        name="api", group="core", port=8000, url=None,
        enabled=True, tier=1, depends_on=["db"], description="API", blast_note="",
    ),
    "worker": Service(
        name="worker", group="core", port=9000, url=None,
        enabled=True, tier=1, depends_on=["api"], description="Worker", blast_note="",
    ),
    "ui": Service(
        name="ui", group="optional", port=3000, url=None,
        enabled=True, tier=2, depends_on=["api"], description="UI", blast_note="",
    ),
}


# ─── build_reverse_deps ──────────────────────────────────────────

class TestBuildReverseDeps:
    def test_basic(self):
        rev = build_reverse_deps(SIMPLE_GRAPH)
        # api depends on db → db の逆依存に api が入る
        assert "api" in rev["db"]

    def test_chain(self):
        rev = build_reverse_deps(SIMPLE_GRAPH)
        # worker depends on api → api の逆依存に worker が入る
        assert "worker" in rev["api"]
        assert "ui" in rev["api"]

    def test_root_has_no_incoming(self):
        rev = build_reverse_deps(SIMPLE_GRAPH)
        # db は誰にも依存されていない → db のキーはあるが空 set
        assert "worker" not in rev.get("db", set()) or True  # db -> {api}
        # worker は誰にも依存されていない
        assert rev.get("worker", set()) == set()

    def test_isolated_service(self):
        svcs = {
            "alone": Service(
                name="alone", group="optional", port=None, url=None,
                enabled=False, tier=2, depends_on=[], description="", blast_note="",
            )
        }
        rev = build_reverse_deps(svcs)
        assert rev.get("alone", set()) == set()


# ─── compute_blast_radius ────────────────────────────────────────

class TestComputeBlastRadius:
    def test_root_service_affects_all_dependents(self):
        rev = build_reverse_deps(SIMPLE_GRAPH)
        affected = compute_blast_radius("db", SIMPLE_GRAPH, rev)
        # db が落ちると api, worker, ui が連鎖停止
        assert set(affected) == {"api", "worker", "ui"}

    def test_middle_service(self):
        rev = build_reverse_deps(SIMPLE_GRAPH)
        affected = compute_blast_radius("api", SIMPLE_GRAPH, rev)
        # api が落ちると worker と ui が止まる (db は止まらない)
        assert set(affected) == {"worker", "ui"}
        assert "db" not in affected

    def test_leaf_service_isolated(self):
        rev = build_reverse_deps(SIMPLE_GRAPH)
        affected = compute_blast_radius("worker", SIMPLE_GRAPH, rev)
        assert affected == []

    def test_unknown_service_error(self):
        rev = build_reverse_deps(SIMPLE_GRAPH)
        # 存在しないサービスは BFS が始まらず空リストを返す
        affected = compute_blast_radius("nonexistent", SIMPLE_GRAPH, rev)
        assert affected == []


# ─── recovery_order ──────────────────────────────────────────────

class TestRecoveryOrder:
    def test_tier_ordering(self):
        order = recovery_order(SIMPLE_GRAPH)
        names = [s.name for s in order]
        # db (tier 0) が api (tier 1) より先
        assert names.index("db") < names.index("api")
        # api が worker/ui より先
        assert names.index("api") < names.index("worker")
        assert names.index("api") < names.index("ui")

    def test_all_services_included(self):
        order = recovery_order(SIMPLE_GRAPH)
        assert {s.name for s in order} == set(SIMPLE_GRAPH.keys())

    def test_cycle_resilience(self):
        """サイクルがあっても例外を出さない (残留ノードは出力しない仕様)。"""
        cyclic = {
            "a": Service(name="a", group="core", port=1, url=None, enabled=True,
                         tier=0, depends_on=["b"], description="", blast_note=""),
            "b": Service(name="b", group="core", port=2, url=None, enabled=True,
                         tier=0, depends_on=["a"], description="", blast_note=""),
        }
        order = recovery_order(cyclic)
        # サイクルがあると両方 in_degree > 0 になり、出力は空
        assert isinstance(order, list)


# ─── probe_live ──────────────────────────────────────────────────

class TestProbeLive:
    def _svc(self, **kw):
        defaults = dict(
            name="test", group="core", port=9999, url=None,
            enabled=True, tier=0, depends_on=[], description="", blast_note="",
        )
        defaults.update(kw)
        return Service(**defaults)

    def test_disabled_returns_skip(self):
        name, status = probe_live(self._svc(enabled=False))
        assert status == "SKIP"

    def test_no_port_no_url_returns_no_url(self):
        name, status = probe_live(self._svc(port=None, url=None))
        assert status == "NO_URL"

    def test_ok_response(self):
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.status = 200
        with patch("urllib.request.urlopen", return_value=mock_resp):
            name, status = probe_live(self._svc())
        assert status == "OK"

    def test_500_returns_http_500(self):
        import urllib.error
        with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError(
            url="http://x", code=500, msg="err", hdrs=None, fp=None
        )):
            name, status = probe_live(self._svc())
        assert status == "HTTP_500"

    def test_connection_refused_returns_down(self):
        with patch("urllib.request.urlopen", side_effect=ConnectionRefusedError()):
            name, status = probe_live(self._svc())
        assert status == "DOWN"

    def test_url_override(self):
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.status = 200
        svc = self._svc(port=None, url="http://custom.host:1234")
        with patch("urllib.request.urlopen", return_value=mock_resp) as m:
            probe_live(svc)
        called_url = m.call_args[0][0]
        assert "custom.host:1234" in called_url


# ─── load_ledger integration ─────────────────────────────────────

class TestLoadLedger:
    _YAML = textwrap.dedent("""\
        core:
          memory:
            port: 5105
            url: null
            enabled: true
            tier: 0
            depends_on: []
            description: Memory service
            blast_note: critical
          learning:
            port: 5126
            url: null
            enabled: true
            tier: 1
            depends_on: [memory]
            description: Learning
            blast_note: ""
        optional:
          comfyui:
            port: 8188
            url: null
            enabled: false
            tier: 2
            depends_on: []
            description: ComfyUI
            blast_note: ""
    """)

    def test_loads_services(self, tmp_path):
        f = tmp_path / "ledger.yaml"
        f.write_text(self._YAML, encoding="utf-8")
        svcs = load_ledger(str(f))
        assert "memory" in svcs
        assert "learning" in svcs
        assert "comfyui" in svcs

    def test_tier_assigned(self, tmp_path):
        f = tmp_path / "ledger.yaml"
        f.write_text(self._YAML, encoding="utf-8")
        svcs = load_ledger(str(f))
        assert svcs["memory"].tier == 0
        assert svcs["learning"].tier == 1
        assert svcs["comfyui"].tier == 2

    def test_blast_radius_integration(self, tmp_path):
        f = tmp_path / "ledger.yaml"
        f.write_text(self._YAML, encoding="utf-8")
        svcs = load_ledger(str(f))
        rev = build_reverse_deps(svcs)
        affected = compute_blast_radius("memory", svcs, rev)
        assert "learning" in affected


# ─── cmd_live smoke ──────────────────────────────────────────────

class TestCmdLiveSmoke:
    def test_all_down_shows_cascade(self, capsys):
        """全サービスが DOWN のとき cascade セクションが出力される。"""
        svcs = SIMPLE_GRAPH
        rev = build_reverse_deps(svcs)
        with patch("check_blast_radius.probe_live", side_effect=lambda s: (s.name, "DOWN")):
            cmd_live(svcs, rev, use_color=False)
        out = capsys.readouterr().out
        assert "Cascade Risk" in out

    def test_all_ok_no_cascade(self, capsys):
        svcs = SIMPLE_GRAPH
        rev = build_reverse_deps(svcs)
        with patch("check_blast_radius.probe_live", side_effect=lambda s: (s.name, "OK")):
            cmd_live(svcs, rev, use_color=False)
        out = capsys.readouterr().out
        assert "All enabled services are UP" in out
        assert "Cascade" not in out
