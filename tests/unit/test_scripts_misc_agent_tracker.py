"""
Unit tests for scripts/misc/agent_tracker.py
"""
import sys
from unittest.mock import MagicMock

# manaos_logger は try/except で import されるので mock は念のため
_ml = MagicMock()
_ml.get_service_logger.return_value = MagicMock()
sys.modules.setdefault("manaos_logger", _ml)

import pytest
from scripts.misc.agent_tracker import (
    AgentTracker,
    AuditResult,
    AgentStats,
    UsageRecord,
    RANK_THRESHOLDS,
    QUALITY_CRITERIA,
)


# ── helpers ────────────────────────────────────────────────────────────────
def make_tracker(tmp_path=None) -> AgentTracker:
    """インメモリ AgentTracker を返す"""
    return AgentTracker(db_path=":memory:", agents_dir=str(tmp_path or ""))


# ── TestCalcRank ───────────────────────────────────────────────────────────
class TestCalcRank:
    def test_zero_uses_is_N(self):
        assert AgentTracker.calc_rank(0) == "N"

    def test_one_use_is_NC(self):
        assert AgentTracker.calc_rank(1) == "N-C"

    def test_four_uses_is_NC(self):
        assert AgentTracker.calc_rank(4) == "N-C"

    def test_five_uses_is_NB(self):
        assert AgentTracker.calc_rank(5) == "N-B"

    def test_nine_uses_is_NB(self):
        assert AgentTracker.calc_rank(9) == "N-B"

    def test_ten_uses_is_NA(self):
        assert AgentTracker.calc_rank(10) == "N-A"

    def test_nineteen_uses_is_NA(self):
        assert AgentTracker.calc_rank(19) == "N-A"

    def test_twenty_uses_is_NS(self):
        assert AgentTracker.calc_rank(20) == "N-S"

    def test_large_count_is_NS(self):
        assert AgentTracker.calc_rank(999) == "N-S"


# ── TestTrack ──────────────────────────────────────────────────────────────
class TestTrack:
    def test_returns_usage_record(self):
        tracker = make_tracker()
        result = tracker.track("my-agent", "summarize task", "sess-001")
        assert isinstance(result, UsageRecord)
        assert result.agent_name == "my-agent"

    def test_task_summary_stored(self):
        tracker = make_tracker()
        record = tracker.track("agent-x", "find bugs")
        assert record.task_summary == "find bugs"

    def test_session_id_stored(self):
        tracker = make_tracker()
        record = tracker.track("agent-y", "", "s-42")
        assert record.session_id == "s-42"

    def test_track_increments_count(self):
        tracker = make_tracker()
        for _ in range(3):
            tracker.track("agent-z")
        stats = tracker.get_stats("agent-z")
        assert stats.total_uses == 3

    def test_recorded_at_is_set(self):
        tracker = make_tracker()
        record = tracker.track("agent-w")
        assert record.recorded_at != ""


# ── TestGetStats ───────────────────────────────────────────────────────────
class TestGetStats:
    def test_untracked_agent_has_zero_uses(self):
        tracker = make_tracker()
        stats = tracker.get_stats("never_used")
        assert stats.total_uses == 0

    def test_untracked_agent_rank_is_N(self):
        tracker = make_tracker()
        stats = tracker.get_stats("never_used")
        assert stats.rank == "N"

    def test_untracked_agent_is_parking_candidate(self):
        tracker = make_tracker()
        stats = tracker.get_stats("never_used")
        assert stats.is_parking_candidate is True

    def test_well_used_agent_not_parking_candidate(self):
        tracker = make_tracker()
        for _ in range(10):
            tracker.track("popular-agent")
        stats = tracker.get_stats("popular-agent")
        assert stats.is_parking_candidate is False

    def test_rank_updates_after_tracking(self):
        tracker = make_tracker()
        for _ in range(5):
            tracker.track("rising-agent")
        assert tracker.get_stats("rising-agent").rank == "N-B"


# ── TestAuditAgentText ─────────────────────────────────────────────────────
class TestAuditAgentText:
    FULL_AGENT_TEXT = """\
---
name: my-agent
description: Does useful things. Use when you want to automate. Do not trigger if not needed.
model: claude-sonnet-4-5
isolation: worktree
---
"""

    def test_full_text_scores_100(self):
        tracker = make_tracker()
        result = tracker.audit_agent_text("my-agent", self.FULL_AGENT_TEXT)
        assert result.score == 100

    def test_empty_text_scores_zero(self):
        tracker = make_tracker()
        result = tracker.audit_agent_text("empty-agent", "")
        assert result.score == 0

    def test_returns_audit_result(self):
        tracker = make_tracker()
        result = tracker.audit_agent_text("a", self.FULL_AGENT_TEXT)
        assert isinstance(result, AuditResult)

    def test_partial_text_has_suggestions(self):
        tracker = make_tracker()
        result = tracker.audit_agent_text("partial", "name: x\ndescription: y")
        assert len(result.suggestions) > 0

    def test_partial_text_has_failed_criteria(self):
        tracker = make_tracker()
        result = tracker.audit_agent_text("partial", "name: x\ndescription: y")
        assert len(result.failed_criteria) > 0

    def test_model_criterion_detected(self):
        tracker = make_tracker()
        text = "name: x\ndescription: y\nmodel: claude-3"
        result = tracker.audit_agent_text("x", text)
        assert "model" in result.passed_criteria

    def test_isolation_criterion_detected(self):
        tracker = make_tracker()
        text = "name: x\ndescription: y\nisolation: worktree"
        result = tracker.audit_agent_text("x", text)
        assert "isolation" in result.passed_criteria


# ── TestAuditAgentsDir ─────────────────────────────────────────────────────
class TestAuditAgentsDir:
    def test_nonexistent_dir_returns_error(self, tmp_path):
        tracker = make_tracker(tmp_path)
        result = tracker.audit_agents_dir(str(tmp_path / "no_such_dir"))
        assert "error" in result
        assert result["total"] == 0

    def test_empty_dir_returns_zero(self, tmp_path):
        tracker = make_tracker(tmp_path)
        result = tracker.audit_agents_dir(str(tmp_path))
        assert result["total"] == 0
        assert result["passing"] == 0

    def test_single_md_counted(self, tmp_path):
        md = tmp_path / "my-agent.md"
        md.write_text("name: my-agent\ndescription: test", encoding="utf-8")
        tracker = make_tracker(tmp_path)
        result = tracker.audit_agents_dir(str(tmp_path))
        assert result["total"] == 1


# ── TestStats ─────────────────────────────────────────────────────────────
class TestStats:
    def test_stats_returns_dict(self):
        tracker = make_tracker()
        tracker.track("agent-a")
        st = tracker.stats()
        assert isinstance(st, dict)
        assert "total_agents" in st
        assert "rank_distribution" in st

    def test_stats_total_agents_count(self):
        tracker = make_tracker()
        tracker.track("a1")
        tracker.track("a2")
        st = tracker.stats()
        assert st["total_agents"] >= 2
