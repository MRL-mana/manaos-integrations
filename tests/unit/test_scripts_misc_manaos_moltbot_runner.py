"""tests/unit/test_scripts_misc_manaos_moltbot_runner.py

manaos_moltbot_runner.py の単体テスト
"""
import pytest

import scripts.misc.manaos_moltbot_runner as _mod
from moltbot_integration.schema import Plan, RiskLevel


class TestBuildListFilesOnlyPlan:
    def test_returns_plan(self):
        plan = _mod.build_list_files_only_plan()
        assert isinstance(plan, Plan)

    def test_plan_id_prefix(self):
        plan = _mod.build_list_files_only_plan()
        assert plan.plan_id.startswith("plan-")

    def test_intent(self):
        plan = _mod.build_list_files_only_plan()
        assert plan.intent == "list_files only"

    def test_single_step(self):
        plan = _mod.build_list_files_only_plan()
        assert len(plan.steps) == 1

    def test_step_action(self):
        plan = _mod.build_list_files_only_plan()
        assert plan.steps[0].action == "list_files"

    def test_custom_path(self):
        plan = _mod.build_list_files_only_plan(path="~/Documents")
        step = plan.steps[0]
        assert step.params["path"] == "~/Documents"

    def test_risk_level_low(self):
        plan = _mod.build_list_files_only_plan()
        assert plan.risk_level == RiskLevel.LOW


class TestBuildFileReadOnlyPlan:
    def test_returns_plan(self):
        plan = _mod.build_file_read_only_plan("/tmp/test.txt")
        assert isinstance(plan, Plan)

    def test_step_action_is_file_read(self):
        plan = _mod.build_file_read_only_plan("/tmp/test.txt")
        assert len(plan.steps) == 1
        assert plan.steps[0].action == "file_read"

    def test_step_contains_path(self):
        plan = _mod.build_file_read_only_plan("/tmp/test.txt")
        assert plan.steps[0].params["path"] == "/tmp/test.txt"


class TestBuildPhase1FileSortPlan:
    def test_returns_plan(self):
        plan = _mod.build_phase1_file_sort_plan("ダウンロードを整理して")
        assert isinstance(plan, Plan)

    def test_intent_matches_user_text(self):
        plan = _mod.build_phase1_file_sort_plan("ダウンロードを整理して")
        assert plan.intent == "ダウンロードを整理して"

    def test_has_multiple_steps(self):
        plan = _mod.build_phase1_file_sort_plan("整理")
        assert len(plan.steps) >= 2

    def test_first_step_is_list_files(self):
        plan = _mod.build_phase1_file_sort_plan("整理")
        assert plan.steps[0].action == "list_files"
