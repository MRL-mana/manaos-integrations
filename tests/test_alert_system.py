#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_alert_system.py
AlertSystem の単体テスト
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# sys.path に scripts/misc を追加
_PROJECT_ROOT = Path(__file__).parent.parent
if str(_PROJECT_ROOT / "scripts" / "misc") not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT / "scripts" / "misc"))

# manaos_logger スタブ
_logger_stub = MagicMock()
_logger_mod = MagicMock()
_logger_mod.get_logger = MagicMock(return_value=_logger_stub)
_logger_mod.get_service_logger = MagicMock(return_value=_logger_stub)
sys.modules.setdefault("manaos_logger", _logger_mod)

from alert_system import Alert, AlertRule, AlertSeverity, AlertSystem


# ──────────────────────────────────────────────
# ヘルパー
# ──────────────────────────────────────────────

def _make_system(tmp_path: Path | None = None) -> AlertSystem:
    with patch("pathlib.Path.mkdir"):
        sys_obj = AlertSystem()
    if tmp_path:
        sys_obj.storage_path = tmp_path / "alerts"
        sys_obj.storage_path.mkdir(parents=True, exist_ok=True)
    return sys_obj


def _make_rule(**kw) -> AlertRule:
    defaults = dict(
        rule_id="test_rule",
        name="テストルール",
        metric_name="test.metric",
        threshold=80.0,
        comparison="gte",
        severity=AlertSeverity.WARNING,
        notification_channels=[],
    )
    defaults.update(kw)
    return AlertRule(**defaults)


# ──────────────────────────────────────────────
# AlertSeverity のテスト
# ──────────────────────────────────────────────

class TestAlertSeverity:
    def test_all_values(self):
        assert AlertSeverity.INFO.value == "info"
        assert AlertSeverity.WARNING.value == "warning"
        assert AlertSeverity.ERROR.value == "error"
        assert AlertSeverity.CRITICAL.value == "critical"


# ──────────────────────────────────────────────
# AlertRule のテスト
# ──────────────────────────────────────────────

class TestAlertRule:
    def test_defaults(self):
        rule = _make_rule()
        assert rule.enabled is True
        assert rule.duration == 60
        assert rule.notification_channels == []

    def test_custom_values(self):
        rule = _make_rule(duration=300, enabled=False, notification_channels=["slack"])
        assert rule.duration == 300
        assert rule.enabled is False
        assert "slack" in rule.notification_channels


# ──────────────────────────────────────────────
# AlertSystem 初期化
# ──────────────────────────────────────────────

class TestAlertSystemInit:
    def test_default_rules_loaded(self):
        s = _make_system()
        assert len(s.rules) > 0

    def test_default_rule_ids(self):
        s = _make_system()
        expected_ids = {"cpu_high", "memory_high", "disk_high", "error_rate_high", "service_down"}
        assert expected_ids.issubset(set(s.rules.keys()))

    def test_empty_active_alerts(self):
        s = _make_system()
        assert s.active_alerts == {}

    def test_empty_alert_history(self):
        s = _make_system()
        assert s.alert_history == []


# ──────────────────────────────────────────────
# ルール管理
# ──────────────────────────────────────────────

class TestRuleManagement:
    def test_add_rule(self):
        s = _make_system()
        rule = _make_rule(rule_id="custom_rule")
        s.add_rule(rule)
        assert "custom_rule" in s.rules

    def test_remove_existing_rule(self):
        s = _make_system()
        rule = _make_rule(rule_id="to_remove")
        s.add_rule(rule)
        s.remove_rule("to_remove")
        assert "to_remove" not in s.rules

    def test_remove_nonexistent_rule_safe(self):
        """存在しないルール削除はクラッシュしない"""
        s = _make_system()
        s.remove_rule("nonexistent")  # 例外が出ないこと

    def test_register_notification_handler(self):
        s = _make_system()
        handler = MagicMock()
        s.register_notification_handler("slack", handler)
        assert "slack" in s.notification_handlers


# ──────────────────────────────────────────────
# check_metric / アラート発火
# ──────────────────────────────────────────────

class TestCheckMetric:
    def setup_method(self):
        self.s = _make_system()
        # デフォルトルールをクリアして独自ルールだけにする
        self.s.rules = {}
        self.s.active_alerts = {}

    def test_gte_triggers_alert(self):
        rule = _make_rule(metric_name="cpu", threshold=80.0, comparison="gte")
        self.s.add_rule(rule)
        self.s.check_metric("cpu", 90.0)
        assert "test_rule" in self.s.active_alerts

    def test_gte_no_trigger_below_threshold(self):
        rule = _make_rule(metric_name="cpu", threshold=80.0, comparison="gte")
        self.s.add_rule(rule)
        self.s.check_metric("cpu", 70.0)
        assert "test_rule" not in self.s.active_alerts

    def test_gt_triggers_alert(self):
        rule = _make_rule(metric_name="m", threshold=50.0, comparison="gt")
        self.s.add_rule(rule)
        self.s.check_metric("m", 51.0)
        assert "test_rule" in self.s.active_alerts

    def test_lt_triggers_alert(self):
        rule = _make_rule(metric_name="m", threshold=50.0, comparison="lt")
        self.s.add_rule(rule)
        self.s.check_metric("m", 49.0)
        assert "test_rule" in self.s.active_alerts

    def test_eq_triggers_alert(self):
        rule = _make_rule(metric_name="m", threshold=0.0, comparison="eq")
        self.s.add_rule(rule)
        self.s.check_metric("m", 0.0)
        assert "test_rule" in self.s.active_alerts

    def test_lte_triggers_alert(self):
        rule = _make_rule(metric_name="m", threshold=50.0, comparison="lte")
        self.s.add_rule(rule)
        self.s.check_metric("m", 50.0)
        assert "test_rule" in self.s.active_alerts

    def test_alert_added_to_history(self):
        rule = _make_rule(metric_name="cpu", threshold=80.0, comparison="gte")
        self.s.add_rule(rule)
        self.s.check_metric("cpu", 90.0)
        assert len(self.s.alert_history) == 1

    def test_duplicate_alert_not_stacked(self):
        """同じルールは一度だけアクティブになる（重複防止）"""
        rule = _make_rule(metric_name="cpu", threshold=80.0, comparison="gte")
        self.s.add_rule(rule)
        self.s.check_metric("cpu", 90.0)
        self.s.check_metric("cpu", 95.0)  # 2回目
        assert len(self.s.active_alerts) == 1
        assert len(self.s.alert_history) == 1

    def test_different_metric_not_triggered(self):
        """別メトリクスはトリガーされない"""
        rule = _make_rule(metric_name="cpu", threshold=80.0, comparison="gte")
        self.s.add_rule(rule)
        self.s.check_metric("memory", 99.0)
        assert "test_rule" not in self.s.active_alerts

    def test_disabled_rule_not_triggered(self):
        """enabled=False のルールは発火しない"""
        rule = _make_rule(metric_name="cpu", threshold=80.0, comparison="gte", enabled=False)
        self.s.add_rule(rule)
        self.s.check_metric("cpu", 99.0)
        assert "test_rule" not in self.s.active_alerts

    def test_recovery_resolves_alert(self):
        """閾値を下回ったらアラートが解消される"""
        rule = _make_rule(metric_name="cpu", threshold=80.0, comparison="gte")
        self.s.add_rule(rule)
        self.s.check_metric("cpu", 90.0)     # 発火
        assert "test_rule" in self.s.active_alerts
        self.s.check_metric("cpu", 70.0)     # 回復
        assert "test_rule" not in self.s.active_alerts

    def test_alert_severity_propagated(self):
        """アラートの severity がルールから伝播する"""
        rule = _make_rule(
            metric_name="cpu", threshold=80.0, comparison="gte",
            severity=AlertSeverity.CRITICAL
        )
        self.s.add_rule(rule)
        self.s.check_metric("cpu", 95.0)
        alert = self.s.active_alerts["test_rule"]
        assert alert.severity == AlertSeverity.CRITICAL

    def test_notification_handler_called(self):
        """チャンネルが登録されているとき通知ハンドラーが呼ばれる"""
        handler = MagicMock()
        self.s.register_notification_handler("slack", handler)
        rule = _make_rule(
            metric_name="cpu", threshold=80.0, comparison="gte",
            notification_channels=["slack"]
        )
        self.s.add_rule(rule)
        self.s.check_metric("cpu", 90.0)
        handler.assert_called_once()

    def test_notification_handler_exception_safe(self):
        """通知ハンドラーが例外を投げてもクラッシュしない"""
        def bad_handler(alert):
            raise RuntimeError("通知失敗")

        self.s.register_notification_handler("bad", bad_handler)
        rule = _make_rule(
            metric_name="cpu", threshold=80.0, comparison="gte",
            notification_channels=["bad"]
        )
        self.s.add_rule(rule)
        self.s.check_metric("cpu", 90.0)  # 例外が出ないこと


# ──────────────────────────────────────────────
# acknowledge_alert
# ──────────────────────────────────────────────

class TestAcknowledgeAlert:
    def test_acknowledge_existing_alert(self):
        s = _make_system()
        s.rules = {}
        rule = _make_rule(metric_name="cpu", threshold=80.0, comparison="gte")
        s.add_rule(rule)
        s.check_metric("cpu", 90.0)
        alert = list(s.active_alerts.values())[0]
        result = s.acknowledge_alert(alert.alert_id)
        assert result is True
        assert alert.acknowledged is True

    def test_acknowledge_nonexistent_returns_false(self):
        s = _make_system()
        assert s.acknowledge_alert("nonexistent_id") is False


# ──────────────────────────────────────────────
# get_active_alerts / get_alert_history
# ──────────────────────────────────────────────

class TestGetAlerts:
    def test_get_active_alerts_returns_list(self):
        s = _make_system()
        result = s.get_active_alerts()
        assert isinstance(result, list)

    def test_get_alert_history_empty(self):
        s = _make_system()
        assert s.get_alert_history() == []

    def test_get_alert_history_limit(self):
        s = _make_system()
        s.rules = {}
        for i in range(5):
            rule = _make_rule(rule_id=f"r_{i}", metric_name=f"m_{i}", threshold=1.0, comparison="gte")
            s.add_rule(rule)
            s.check_metric(f"m_{i}", 2.0)
        history = s.get_alert_history(limit=3)
        assert len(history) == 3


# ──────────────────────────────────────────────
# save_alerts
# ──────────────────────────────────────────────

class TestSaveAlerts:
    def test_save_alerts_creates_file(self, tmp_path):
        s = _make_system(tmp_path)
        s.rules = {}
        rule = _make_rule(metric_name="cpu", threshold=80.0, comparison="gte")
        s.add_rule(rule)
        s.check_metric("cpu", 90.0)
        s.save_alerts()

        file_path = s.storage_path / "alerts.json"
        assert file_path.exists()

    def test_save_alerts_json_structure(self, tmp_path):
        s = _make_system(tmp_path)
        s.rules = {}
        rule = _make_rule(metric_name="cpu", threshold=80.0, comparison="gte")
        s.add_rule(rule)
        s.check_metric("cpu", 90.0)
        s.save_alerts()

        data = json.loads((s.storage_path / "alerts.json").read_text(encoding="utf-8"))
        assert "active_alerts" in data
        assert "alert_history" in data
        assert len(data["active_alerts"]) == 1
        # severity は文字列
        assert data["active_alerts"][0]["severity"] in ("info", "warning", "error", "critical")

    def test_save_no_alerts_empty_lists(self, tmp_path):
        s = _make_system(tmp_path)
        s.save_alerts()
        data = json.loads((s.storage_path / "alerts.json").read_text(encoding="utf-8"))
        assert data["active_alerts"] == []
        assert data["alert_history"] == []


# ──────────────────────────────────────────────
# resolve_alert
# ──────────────────────────────────────────────

class TestResolveAlert:
    def test_resolve_sets_resolved_at(self):
        s = _make_system()
        s.rules = {}
        rule = _make_rule(metric_name="cpu", threshold=80.0, comparison="gte")
        s.add_rule(rule)
        s.check_metric("cpu", 90.0)
        alert = list(s.active_alerts.values())[0]
        assert alert.resolved_at is None

        s._resolve_alert("test_rule")
        assert alert.resolved_at is not None

    def test_resolve_removes_from_active(self):
        s = _make_system()
        s.rules = {}
        rule = _make_rule(metric_name="cpu", threshold=80.0, comparison="gte")
        s.add_rule(rule)
        s.check_metric("cpu", 90.0)
        s._resolve_alert("test_rule")
        assert "test_rule" not in s.active_alerts
