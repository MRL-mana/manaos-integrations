# -*- coding: utf-8 -*-
"""tests for scripts/misc/ui_operations_api.py"""
import json
import sqlite3
import sys
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.misc.ui_operations_api import (
    UIOperationsAPI,
    SystemMode,
    CostEntry,
)


def _make_api(tmp_path: Path) -> UIOperationsAPI:
    return UIOperationsAPI(
        cost_db_path=tmp_path / "cost.db",
        config_path=tmp_path / "cfg.json",
    )


# ---------------------------------------------------------------------------
# SystemMode
# ---------------------------------------------------------------------------
class TestSystemMode:
    def test_values(self):
        assert SystemMode.WORK.value == "work"
        assert SystemMode.CREATIVE.value == "creative"
        assert SystemMode.FUN.value == "fun"
        assert SystemMode.AUTO.value == "auto"

    def test_from_string(self):
        assert SystemMode("work") is SystemMode.WORK
        assert SystemMode("auto") is SystemMode.AUTO

    def test_is_str_subclass(self):
        assert isinstance(SystemMode.WORK, str)


# ---------------------------------------------------------------------------
# CostEntry
# ---------------------------------------------------------------------------
class TestCostEntry:
    def test_defaults(self):
        e = CostEntry(timestamp="2025-01-01T00:00:00", service="llm", operation="call", cost=0.1)
        assert e.currency == "JPY"
        assert e.metadata == {}

    def test_custom(self):
        e = CostEntry(timestamp="T", service="s", operation="o", cost=5.0, currency="USD", metadata={"k": "v"})
        assert e.currency == "USD"
        assert e.metadata == {"k": "v"}

    def test_cost_value(self):
        e = CostEntry(timestamp="T", service="s", operation="o", cost=1.23)
        assert e.cost == pytest.approx(1.23)


# ---------------------------------------------------------------------------
# Init / default config
# ---------------------------------------------------------------------------
class TestInit:
    def test_creates_db(self, tmp_path):
        api = _make_api(tmp_path)
        assert (tmp_path / "cost.db").exists()

    def test_default_mode_auto(self, tmp_path):
        api = _make_api(tmp_path)
        assert api.current_mode == SystemMode.AUTO

    def test_config_path_stored(self, tmp_path):
        api = _make_api(tmp_path)
        assert api.config_path == tmp_path / "cfg.json"

    def test_cost_tracking_enabled_default(self, tmp_path):
        api = _make_api(tmp_path)
        assert api.cost_tracking_enabled is True

    def test_default_config_loaded(self, tmp_path):
        api = _make_api(tmp_path)
        assert "cost_limits" in api.config

    def test_db_table_exists(self, tmp_path):
        api = _make_api(tmp_path)
        conn = sqlite3.connect(tmp_path / "cost.db")
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        conn.close()
        assert "cost_entries" in tables


class TestGetDefaultConfig:
    def test_keys(self, tmp_path):
        api = _make_api(tmp_path)
        cfg = api._get_default_config()
        assert "default_mode" in cfg
        assert "cost_tracking_enabled" in cfg
        assert "cost_limits" in cfg
        assert "service_costs" in cfg

    def test_default_mode_value(self, tmp_path):
        api = _make_api(tmp_path)
        assert api._get_default_config()["default_mode"] == "auto"

    def test_cost_limits_keys(self, tmp_path):
        api = _make_api(tmp_path)
        limits = api._get_default_config()["cost_limits"]
        assert "daily" in limits
        assert "monthly" in limits

    def test_service_costs_not_empty(self, tmp_path):
        api = _make_api(tmp_path)
        svc = api._get_default_config()["service_costs"]
        assert len(svc) > 0


# ---------------------------------------------------------------------------
# custom config loading
# ---------------------------------------------------------------------------
class TestLoadConfig:
    def test_loads_from_file(self, tmp_path):
        cfg_file = tmp_path / "cfg.json"
        cfg_file.write_text(json.dumps({"default_mode": "work", "cost_tracking_enabled": False}), encoding="utf-8")
        api = UIOperationsAPI(cost_db_path=tmp_path / "cost.db", config_path=cfg_file)
        assert api.current_mode == SystemMode.WORK
        assert api.cost_tracking_enabled is False

    def test_invalid_json_falls_back(self, tmp_path):
        cfg_file = tmp_path / "cfg.json"
        cfg_file.write_text("NOT JSON", encoding="utf-8")
        api = UIOperationsAPI(cost_db_path=tmp_path / "cost.db", config_path=cfg_file)
        assert api.config is not None


# ---------------------------------------------------------------------------
# Mode management
# ---------------------------------------------------------------------------
class TestModeManagement:
    def test_get_mode_default(self, tmp_path):
        api = _make_api(tmp_path)
        assert api.get_mode() == SystemMode.AUTO

    def test_set_mode_work(self, tmp_path):
        api = _make_api(tmp_path)
        api.set_mode(SystemMode.WORK)
        assert api.get_mode() == SystemMode.WORK

    def test_set_mode_creative(self, tmp_path):
        api = _make_api(tmp_path)
        api.set_mode(SystemMode.CREATIVE)
        assert api.current_mode == SystemMode.CREATIVE

    def test_set_mode_updates_config(self, tmp_path):
        api = _make_api(tmp_path)
        api.set_mode(SystemMode.FUN)
        assert api.config["default_mode"] == "fun"


# ---------------------------------------------------------------------------
# _is_allowed_in_mode
# ---------------------------------------------------------------------------
class TestIsAllowedInMode:
    def test_auto_allows_all(self, tmp_path):
        api = _make_api(tmp_path)
        for intent in ["unknown", "image_generation", "task_execution", "xyz"]:
            assert api._is_allowed_in_mode(intent, SystemMode.AUTO) is True

    def test_work_allows_task_execution(self, tmp_path):
        api = _make_api(tmp_path)
        assert api._is_allowed_in_mode("task_execution", SystemMode.WORK) is True

    def test_work_disallows_image_generation(self, tmp_path):
        api = _make_api(tmp_path)
        assert api._is_allowed_in_mode("image_generation", SystemMode.WORK) is False

    def test_creative_allows_image_generation(self, tmp_path):
        api = _make_api(tmp_path)
        assert api._is_allowed_in_mode("image_generation", SystemMode.CREATIVE) is True

    def test_creative_disallows_scheduling(self, tmp_path):
        api = _make_api(tmp_path)
        assert api._is_allowed_in_mode("scheduling", SystemMode.CREATIVE) is False

    def test_fun_allows_conversation(self, tmp_path):
        api = _make_api(tmp_path)
        assert api._is_allowed_in_mode("conversation", SystemMode.FUN) is True

    def test_fun_disallows_code_generation(self, tmp_path):
        api = _make_api(tmp_path)
        assert api._is_allowed_in_mode("code_generation", SystemMode.FUN) is False


# ---------------------------------------------------------------------------
# _get_priority_for_mode
# ---------------------------------------------------------------------------
class TestGetPriorityForMode:
    def test_work_high(self, tmp_path):
        api = _make_api(tmp_path)
        assert api._get_priority_for_mode(SystemMode.WORK) == "high"

    def test_creative_medium(self, tmp_path):
        api = _make_api(tmp_path)
        assert api._get_priority_for_mode(SystemMode.CREATIVE) == "medium"

    def test_fun_low(self, tmp_path):
        api = _make_api(tmp_path)
        assert api._get_priority_for_mode(SystemMode.FUN) == "low"

    def test_auto_medium(self, tmp_path):
        api = _make_api(tmp_path)
        assert api._get_priority_for_mode(SystemMode.AUTO) == "medium"


# ---------------------------------------------------------------------------
# _estimate_cost
# ---------------------------------------------------------------------------
class TestEstimateCost:
    def test_known_service(self, tmp_path):
        api = _make_api(tmp_path)
        assert api._estimate_cost("llm_api") == pytest.approx(0.01)

    def test_image_generation_cost(self, tmp_path):
        api = _make_api(tmp_path)
        assert api._estimate_cost("image_generation") == pytest.approx(0.05)

    def test_unknown_service_default(self, tmp_path):
        api = _make_api(tmp_path)
        assert api._estimate_cost("unknown_xyz") == pytest.approx(0.01)


# ---------------------------------------------------------------------------
# _record_cost & get_cost_summary
# ---------------------------------------------------------------------------
class TestCostTracking:
    def test_record_and_summary(self, tmp_path):
        api = _make_api(tmp_path)
        api._record_cost("llm_api", "call", 50.0)
        summary = api.get_cost_summary(days=1)
        assert summary["total_cost"] == pytest.approx(50.0)

    def test_multiple_records(self, tmp_path):
        api = _make_api(tmp_path)
        api._record_cost("llm_api", "call", 10.0)
        api._record_cost("llm_api", "call", 20.0)
        summary = api.get_cost_summary(days=1)
        assert summary["total_cost"] == pytest.approx(30.0)

    def test_service_costs_breakdown(self, tmp_path):
        api = _make_api(tmp_path)
        api._record_cost("svc_a", "op", 5.0)
        api._record_cost("svc_b", "op", 7.0)
        summary = api.get_cost_summary(days=1)
        assert "svc_a" in summary["service_costs"]
        assert "svc_b" in summary["service_costs"]

    def test_today_cost(self, tmp_path):
        api = _make_api(tmp_path)
        api._record_cost("svc", "op", 15.0)
        summary = api.get_cost_summary(days=1)
        assert summary["today_cost"] == pytest.approx(15.0)

    def test_currency_jpy(self, tmp_path):
        api = _make_api(tmp_path)
        summary = api.get_cost_summary(days=1)
        assert summary["currency"] == "JPY"

    def test_empty_db(self, tmp_path):
        api = _make_api(tmp_path)
        summary = api.get_cost_summary(days=1)
        assert summary["total_cost"] == pytest.approx(0.0)

    def test_days_returned(self, tmp_path):
        api = _make_api(tmp_path)
        summary = api.get_cost_summary(days=7)
        assert summary["days"] == 7


# ---------------------------------------------------------------------------
# _save_config
# ---------------------------------------------------------------------------
class TestSaveConfig:
    def test_saves_to_file(self, tmp_path):
        api = _make_api(tmp_path)
        api.config["custom_key"] = "test_value"
        api._save_config()
        saved = json.loads((tmp_path / "cfg.json").read_text(encoding="utf-8"))
        assert saved["custom_key"] == "test_value"

    def test_roundtrip(self, tmp_path):
        api = _make_api(tmp_path)
        api.set_mode(SystemMode.CREATIVE)
        saved = json.loads((tmp_path / "cfg.json").read_text(encoding="utf-8"))
        assert saved["default_mode"] == "creative"


# ---------------------------------------------------------------------------
# execute_task (httpx mocked)
# ---------------------------------------------------------------------------
class TestExecuteTask:
    def _mock_response(self, status_code: int, data: dict):
        mock = MagicMock()
        mock.status_code = status_code
        mock.json.return_value = data
        return mock

    def test_intent_router_failure_returns_unknown(self, tmp_path):
        api = _make_api(tmp_path)
        with patch("httpx.post", side_effect=Exception("connection refused")):
            result = api.execute_task("テスト")
        assert result["success"] is False

    def test_work_mode_blocks_image_generation(self, tmp_path):
        api = _make_api(tmp_path)
        api.set_mode(SystemMode.WORK)
        with patch("httpx.post", return_value=self._mock_response(200, {"intent_type": "image_generation", "confidence": 0.9})):
            result = api.execute_task("画像を生成して")
        assert result["success"] is False
        assert "許可されていません" in result.get("error", "")

    def test_task_planner_failure(self, tmp_path):
        api = _make_api(tmp_path)
        intent_resp = self._mock_response(200, {"intent_type": "task_execution", "confidence": 0.9})
        planner_resp = self._mock_response(500, {})
        with patch("httpx.post", side_effect=[intent_resp, planner_resp]):
            result = api.execute_task("テスト")
        assert result["success"] is False
