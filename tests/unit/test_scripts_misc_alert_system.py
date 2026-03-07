"""
Unit tests for scripts/misc/alert_system.py

Tests: AlertSeverity enum, AlertRule/Alert dataclasses, comparison logic in
check_metric, add/remove rules, acknowledge, resolve, notification dispatch.
"""
import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock
from datetime import datetime

# Mock manaos_logger before importing the target module
sys.modules.setdefault("manaos_logger", MagicMock())

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts" / "misc"))
import alert_system  # noqa: E402
from alert_system import AlertSeverity, AlertRule, Alert, AlertSystem  # noqa: E402


# ---------------------------------------------------------------------------
# Fixture: minimal AlertSystem (no disk access)
# ---------------------------------------------------------------------------

@pytest.fixture
def system():
    """AlertSystem instance with clean state (no __init__ side-effects)."""
    obj = AlertSystem.__new__(AlertSystem)
    obj.rules = {}
    obj.active_alerts = {}
    obj.alert_history = []
    obj.notification_handlers = {}
    obj.storage_path = MagicMock()
    return obj


def _make_rule(
    rule_id="r1",
    name="Test Rule",
    metric="test.metric",
    threshold=50.0,
    comparison="gt",
    severity=AlertSeverity.WARNING,
    channels=None,
):
    return AlertRule(
        rule_id=rule_id,
        name=name,
        metric_name=metric,
        threshold=threshold,
        comparison=comparison,
        severity=severity,
        notification_channels=channels or [],
    )


# ---------------------------------------------------------------------------
# AlertSeverity
# ---------------------------------------------------------------------------

class TestAlertSeverity:
    def test_info_value(self):
        assert AlertSeverity.INFO.value == "info"

    def test_warning_value(self):
        assert AlertSeverity.WARNING.value == "warning"

    def test_error_value(self):
        assert AlertSeverity.ERROR.value == "error"

    def test_critical_value(self):
        assert AlertSeverity.CRITICAL.value == "critical"

    def test_all_members_unique(self):
        values = [s.value for s in AlertSeverity]
        assert len(values) == len(set(values))


# ---------------------------------------------------------------------------
# AlertRule dataclass
# ---------------------------------------------------------------------------

class TestAlertRule:
    def test_basic_creation(self):
        rule = _make_rule()
        assert rule.rule_id == "r1"
        assert rule.metric_name == "test.metric"
        assert rule.threshold == 50.0

    def test_default_enabled_true(self):
        rule = _make_rule()
        assert rule.enabled is True

    def test_default_duration(self):
        rule = _make_rule()
        assert rule.duration == 60

    def test_default_notification_channels_empty(self):
        rule = _make_rule()
        assert rule.notification_channels == []

    def test_severity_stored(self):
        rule = _make_rule(severity=AlertSeverity.CRITICAL)
        assert rule.severity == AlertSeverity.CRITICAL


# ---------------------------------------------------------------------------
# Alert dataclass
# ---------------------------------------------------------------------------

class TestAlert:
    def test_basic_creation(self):
        a = Alert(
            alert_id="a1",
            rule_id="r1",
            severity=AlertSeverity.ERROR,
            message="test message",
            metric_name="test.metric",
            metric_value=75.0,
            threshold=50.0,
        )
        assert a.alert_id == "a1"
        assert a.metric_value == 75.0

    def test_default_resolved_at_none(self):
        a = Alert(
            alert_id="a1", rule_id="r1", severity=AlertSeverity.INFO,
            message="m", metric_name="n", metric_value=1.0, threshold=0.0,
        )
        assert a.resolved_at is None

    def test_default_acknowledged_false(self):
        a = Alert(
            alert_id="a1", rule_id="r1", severity=AlertSeverity.INFO,
            message="m", metric_name="n", metric_value=1.0, threshold=0.0,
        )
        assert a.acknowledged is False

    def test_triggered_at_auto_set(self):
        before = datetime.now()
        a = Alert(
            alert_id="a1", rule_id="r1", severity=AlertSeverity.INFO,
            message="m", metric_name="n", metric_value=1.0, threshold=0.0,
        )
        after = datetime.now()
        assert before <= a.triggered_at <= after


# ---------------------------------------------------------------------------
# check_metric — comparison logic
# ---------------------------------------------------------------------------

class TestCheckMetricGt:
    def test_above_threshold_triggers_alert(self, system):
        system.add_rule(_make_rule(comparison="gt", threshold=50.0))
        system.check_metric("test.metric", 51.0)
        assert "r1" in system.active_alerts

    def test_at_threshold_no_alert(self, system):
        system.add_rule(_make_rule(comparison="gt", threshold=50.0))
        system.check_metric("test.metric", 50.0)
        assert "r1" not in system.active_alerts

    def test_below_threshold_no_alert(self, system):
        system.add_rule(_make_rule(comparison="gt", threshold=50.0))
        system.check_metric("test.metric", 10.0)
        assert "r1" not in system.active_alerts


class TestCheckMetricLt:
    def test_below_threshold_triggers_alert(self, system):
        system.add_rule(_make_rule(comparison="lt", threshold=50.0))
        system.check_metric("test.metric", 49.0)
        assert "r1" in system.active_alerts

    def test_at_threshold_no_alert(self, system):
        system.add_rule(_make_rule(comparison="lt", threshold=50.0))
        system.check_metric("test.metric", 50.0)
        assert "r1" not in system.active_alerts

    def test_above_threshold_no_alert(self, system):
        system.add_rule(_make_rule(comparison="lt", threshold=50.0))
        system.check_metric("test.metric", 99.0)
        assert "r1" not in system.active_alerts


class TestCheckMetricEq:
    def test_equal_value_triggers_alert(self, system):
        system.add_rule(_make_rule(comparison="eq", threshold=50.0))
        system.check_metric("test.metric", 50.0)
        assert "r1" in system.active_alerts

    def test_not_equal_no_alert(self, system):
        system.add_rule(_make_rule(comparison="eq", threshold=50.0))
        system.check_metric("test.metric", 51.0)
        assert "r1" not in system.active_alerts


class TestCheckMetricGte:
    def test_at_threshold_triggers(self, system):
        system.add_rule(_make_rule(comparison="gte", threshold=50.0))
        system.check_metric("test.metric", 50.0)
        assert "r1" in system.active_alerts

    def test_above_threshold_triggers(self, system):
        system.add_rule(_make_rule(comparison="gte", threshold=50.0))
        system.check_metric("test.metric", 90.0)
        assert "r1" in system.active_alerts

    def test_below_threshold_no_alert(self, system):
        system.add_rule(_make_rule(comparison="gte", threshold=50.0))
        system.check_metric("test.metric", 49.0)
        assert "r1" not in system.active_alerts


class TestCheckMetricLte:
    def test_at_threshold_triggers(self, system):
        system.add_rule(_make_rule(comparison="lte", threshold=50.0))
        system.check_metric("test.metric", 50.0)
        assert "r1" in system.active_alerts

    def test_below_threshold_triggers(self, system):
        system.add_rule(_make_rule(comparison="lte", threshold=50.0))
        system.check_metric("test.metric", 0.0)
        assert "r1" in system.active_alerts

    def test_above_threshold_no_alert(self, system):
        system.add_rule(_make_rule(comparison="lte", threshold=50.0))
        system.check_metric("test.metric", 51.0)
        assert "r1" not in system.active_alerts


class TestCheckMetricMisc:
    def test_different_metric_name_ignored(self, system):
        system.add_rule(_make_rule(comparison="gt", threshold=0.0, metric="cpu"))
        system.check_metric("memory", 100.0)  # wrong metric
        assert "r1" not in system.active_alerts

    def test_disabled_rule_not_triggered(self, system):
        rule = _make_rule(comparison="gt", threshold=0.0)
        rule.enabled = False
        system.add_rule(rule)
        system.check_metric("test.metric", 999.0)
        assert "r1" not in system.active_alerts

    def test_alert_added_to_history(self, system):
        system.add_rule(_make_rule(comparison="gt", threshold=0.0))
        system.check_metric("test.metric", 1.0)
        assert len(system.alert_history) == 1

    def test_duplicate_trigger_not_duplicated(self, system):
        system.add_rule(_make_rule(comparison="gt", threshold=0.0))
        system.check_metric("test.metric", 1.0)
        system.check_metric("test.metric", 2.0)  # already active
        assert len(system.alert_history) == 1


# ---------------------------------------------------------------------------
# add_rule / remove_rule
# ---------------------------------------------------------------------------

class TestAddRemoveRule:
    def test_add_rule_accessible_by_id(self, system):
        system.add_rule(_make_rule())
        assert "r1" in system.rules

    def test_add_multiple_rules(self, system):
        system.add_rule(_make_rule(rule_id="a"))
        system.add_rule(_make_rule(rule_id="b"))
        assert len(system.rules) == 2

    def test_remove_rule_removes_it(self, system):
        system.add_rule(_make_rule())
        system.remove_rule("r1")
        assert "r1" not in system.rules

    def test_remove_nonexistent_rule_no_error(self, system):
        system.remove_rule("does_not_exist")  # should not raise


# ---------------------------------------------------------------------------
# _resolve_alert
# ---------------------------------------------------------------------------

class TestResolveAlert:
    def test_resolve_removes_from_active(self, system):
        alert = Alert(
            alert_id="a1", rule_id="r1", severity=AlertSeverity.WARNING,
            message="test", metric_name="m", metric_value=1.0, threshold=0.0,
        )
        system.active_alerts["r1"] = alert
        system._resolve_alert("r1")
        assert "r1" not in system.active_alerts

    def test_resolve_sets_resolved_at(self, system):
        alert = Alert(
            alert_id="a1", rule_id="r1", severity=AlertSeverity.WARNING,
            message="test", metric_name="m", metric_value=1.0, threshold=0.0,
        )
        system.active_alerts["r1"] = alert
        before = datetime.now()
        system._resolve_alert("r1")
        assert alert.resolved_at >= before

    def test_resolve_nonexistent_no_error(self, system):
        system._resolve_alert("does_not_exist")  # should not raise


# ---------------------------------------------------------------------------
# acknowledge_alert
# ---------------------------------------------------------------------------

class TestAcknowledgeAlert:
    def test_acknowledge_sets_flag(self, system):
        alert = Alert(
            alert_id="a1", rule_id="r1", severity=AlertSeverity.INFO,
            message="m", metric_name="n", metric_value=1.0, threshold=0.0,
        )
        system.active_alerts["r1"] = alert
        result = system.acknowledge_alert("a1")
        assert result is True
        assert alert.acknowledged is True

    def test_acknowledge_unknown_returns_false(self, system):
        result = system.acknowledge_alert("unknown_id")
        assert result is False


# ---------------------------------------------------------------------------
# get_active_alerts / get_alert_history
# ---------------------------------------------------------------------------

class TestGetAlerts:
    def test_get_active_alerts_empty(self, system):
        assert system.get_active_alerts() == []

    def test_get_active_alerts_returns_list(self, system):
        alert = Alert(
            alert_id="a1", rule_id="r1", severity=AlertSeverity.INFO,
            message="m", metric_name="n", metric_value=1.0, threshold=0.0,
        )
        system.active_alerts["r1"] = alert
        assert len(system.get_active_alerts()) == 1

    def test_get_alert_history_respects_limit(self, system):
        for i in range(10):
            a = Alert(
                alert_id=f"a{i}", rule_id=f"r{i}", severity=AlertSeverity.INFO,
                message="m", metric_name="n", metric_value=float(i), threshold=0.0,
            )
            system.alert_history.append(a)
        result = system.get_alert_history(limit=5)
        assert len(result) == 5


# ---------------------------------------------------------------------------
# _send_notification
# ---------------------------------------------------------------------------

class TestSendNotification:
    def test_handler_called_for_matching_channel(self, system):
        handler = MagicMock()
        system.register_notification_handler = lambda ch, h: system.notification_handlers.update({ch: h})
        system.notification_handlers["slack"] = handler
        rule = _make_rule(channels=["slack"])
        alert = Alert(
            alert_id="a1", rule_id="r1", severity=AlertSeverity.WARNING,
            message="m", metric_name="n", metric_value=1.0, threshold=0.0,
        )
        system._send_notification(alert, rule)
        handler.assert_called_once_with(alert)

    def test_no_handler_for_unregistered_channel(self, system):
        rule = _make_rule(channels=["email"])
        alert = Alert(
            alert_id="a1", rule_id="r1", severity=AlertSeverity.WARNING,
            message="m", metric_name="n", metric_value=1.0, threshold=0.0,
        )
        system._send_notification(alert, rule)  # should not raise

    def test_no_notification_channels_no_call(self, system):
        rule = _make_rule(channels=[])
        alert = Alert(
            alert_id="a1", rule_id="r1", severity=AlertSeverity.INFO,
            message="m", metric_name="n", metric_value=1.0, threshold=0.0,
        )
        system._send_notification(alert, rule)  # no handlers — should not raise
