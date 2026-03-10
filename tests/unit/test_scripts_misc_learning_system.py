"""
Unit tests for scripts/misc/learning_system.py
"""
import sys
import json
from pathlib import Path
from unittest.mock import MagicMock

# ── mocks ─────────────────────────────────────────────────────────────────
_ml = MagicMock()
_ml.get_service_logger.return_value = MagicMock()
_ml.get_logger.return_value = MagicMock()
sys.modules.setdefault("manaos_logger", _ml)

_eh = MagicMock()
_eh_inst = MagicMock()
_eh_inst.handle_exception = MagicMock(return_value=MagicMock(message="err"))
_eh.ManaOSErrorHandler = MagicMock(return_value=_eh_inst)
_eh.ErrorCategory = MagicMock()
_eh.ErrorSeverity = MagicMock()
sys.modules.setdefault("manaos_error_handler", _eh)

_tc = MagicMock()
_tc.get_timeout_config = MagicMock(return_value={})
sys.modules.setdefault("manaos_timeout_config", _tc)

_cv = MagicMock()
_cv_inst = MagicMock()
_cv_inst.validate_config = MagicMock(return_value=(True, []))
_cv.ConfigValidator = MagicMock(return_value=_cv_inst)
sys.modules.setdefault("manaos_config_validator", _cv)

# mem0_integration / workflow_automation がなければ auto-skip
sys.modules.setdefault("mem0_integration", None)  # type: ignore
sys.modules.setdefault("workflow_automation", None)  # type: ignore

import pytest
from scripts.misc.learning_system import LearningSystem


@pytest.fixture
def ls(tmp_path):
    storage = tmp_path / "ls_state.json"
    return LearningSystem(storage_path=storage)


def _success_result():
    return {"status": "success", "data": "ok"}


def _fail_result():
    return {"status": "error", "data": "fail"}


# ── TestInit ──────────────────────────────────────────────────────────────
class TestInit:
    def test_empty_usage_patterns(self, ls):
        assert dict(ls.usage_patterns) == {}

    def test_empty_preferences(self, ls):
        assert ls.preferences == {}

    def test_empty_optimizations(self, ls):
        assert ls.optimizations == []

    def test_storage_path_set(self, tmp_path):
        p = tmp_path / "custom.json"
        inst = LearningSystem(storage_path=p)
        assert inst.storage_path == p


# ── TestSaveState ─────────────────────────────────────────────────────────
class TestSaveState:
    def test_creates_file(self, ls):
        ls._save_state()
        assert ls.storage_path.exists()

    def test_file_is_valid_json(self, ls):
        ls._save_state()
        data = json.loads(ls.storage_path.read_text(encoding="utf-8"))
        assert "usage_patterns" in data
        assert "preferences" in data

    def test_roundtrip(self, ls):
        ls.preferences = {"lang": "ja"}
        ls._save_state()
        ls2 = LearningSystem(storage_path=ls.storage_path)
        assert ls2.preferences == {"lang": "ja"}


# ── TestRecordUsage ───────────────────────────────────────────────────────
class TestRecordUsage:
    def test_appends_to_patterns(self, ls):
        ls.record_usage("gen_image", {"prompt": "cat"}, _success_result())
        assert len(ls.usage_patterns["gen_image"]) == 1

    def test_success_flag_true(self, ls):
        ls.record_usage("act", {}, _success_result())
        assert ls.usage_patterns["act"][0]["success"] is True

    def test_success_flag_false(self, ls):
        ls.record_usage("act", {}, _fail_result())
        assert ls.usage_patterns["act"][0]["success"] is False

    def test_multiple_records(self, ls):
        for i in range(5):
            ls.record_usage("action_a", {"i": i}, _success_result())
        assert len(ls.usage_patterns["action_a"]) == 5

    def test_cap_at_100(self, ls):
        for i in range(110):
            ls.record_usage("cap_test", {}, _success_result())
        assert len(ls.usage_patterns["cap_test"]) == 100

    def test_persisted_after_record(self, ls):
        ls.record_usage("save_test", {}, _success_result())
        ls2 = LearningSystem(storage_path=ls.storage_path)
        assert len(ls2.usage_patterns["save_test"]) == 1


# ── TestAnalyzePatterns ───────────────────────────────────────────────────
class TestAnalyzePatterns:
    def test_empty_returns_dict(self, ls):
        result = ls.analyze_patterns()
        assert isinstance(result, dict)

    def test_most_used_actions_present(self, ls):
        ls.record_usage("img", {}, _success_result())
        ls.record_usage("img", {}, _success_result())
        result = ls.analyze_patterns()
        assert "most_used_actions" in result
        counts = {a["action"]: a["count"] for a in result["most_used_actions"]}
        assert counts.get("img") == 2

    def test_success_rates_calculated(self, ls):
        ls.record_usage("task", {}, _success_result())
        ls.record_usage("task", {}, _success_result())
        ls.record_usage("task", {}, _fail_result())
        result = ls.analyze_patterns()
        rate = result["success_rates"]["task"]["rate"]
        assert abs(rate - 66.67) < 1.0

    def test_recommendations_is_list(self, ls):
        result = ls.analyze_patterns()
        assert isinstance(result["recommendations"], list)

    def test_low_success_rate_recommendation(self, ls):
        # 6回以上 失敗率 > 50% → recommended
        for _ in range(6):
            ls.record_usage("bad_action", {}, _fail_result())
        result = ls.analyze_patterns()
        types = [r["type"] for r in result["recommendations"]]
        assert "low_success_rate" in types

    def test_frequent_action_recommendation(self, ls):
        # 11回以上 → frequent_action recommendation
        for _ in range(11):
            ls.record_usage("hot_action", {}, _success_result())
        result = ls.analyze_patterns()
        types = [r["type"] for r in result["recommendations"]]
        assert "frequent_action" in types
