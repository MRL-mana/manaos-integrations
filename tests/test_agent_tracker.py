"""
test_agent_tracker.py — AgentTracker ユニットテスト
"""
import pytest
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "misc"))

from agent_tracker import (
    AgentTracker,
    AgentStats,
    AuditResult,
    UsageRecord,
    get_agent_tracker,
    RANK_THRESHOLDS,
    QUALITY_CRITERIA,
)


# ── フィクスチャ ─────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_singleton():
    import agent_tracker as _mod
    _mod._instance = None
    yield
    _mod._instance = None


@pytest.fixture
def at():
    return AgentTracker(db_path=":memory:")


@pytest.fixture
def agents_dir(tmp_path: Path) -> Path:
    """テスト用エージェント .md ファイルを含む一時ディレクトリ"""
    return tmp_path / "agents"


def _write_agent_md(agents_dir: Path, name: str, content: str):
    agents_dir.mkdir(parents=True, exist_ok=True)
    (agents_dir / f"{name}.md").write_text(content, encoding="utf-8")


# ── track ─────────────────────────────────────────────────────────────────

class TestTrack:
    def test_returns_usage_record(self, at):
        r = at.track("my-agent")
        assert isinstance(r, UsageRecord)
        assert r.agent_name == "my-agent"

    def test_recorded_at_set(self, at):
        r = at.track("agent-x")
        assert r.recorded_at != ""

    def test_task_summary_stored(self, at):
        r = at.track("agent-x", task_summary="タスク概要")
        assert r.task_summary == "タスク概要"

    def test_session_id_stored(self, at):
        r = at.track("agent-x", session_id="sess-001")
        assert r.session_id == "sess-001"

    def test_multiple_tracks_accumulate(self, at):
        for _ in range(5):
            at.track("repeat-agent")
        stats = at.get_stats("repeat-agent")
        assert stats.total_uses == 5


# ── calc_rank ────────────────────────────────────────────────────────────────

class TestCalcRank:
    def test_rank_n_zero(self):
        assert AgentTracker.calc_rank(0) == "N"

    def test_rank_nc(self):
        assert AgentTracker.calc_rank(1) == "N-C"
        assert AgentTracker.calc_rank(4) == "N-C"

    def test_rank_nb(self):
        assert AgentTracker.calc_rank(5) == "N-B"
        assert AgentTracker.calc_rank(9) == "N-B"

    def test_rank_na(self):
        assert AgentTracker.calc_rank(10) == "N-A"
        assert AgentTracker.calc_rank(19) == "N-A"

    def test_rank_ns(self):
        assert AgentTracker.calc_rank(20) == "N-S"
        assert AgentTracker.calc_rank(100) == "N-S"


# ── get_stats ────────────────────────────────────────────────────────────────

class TestGetStats:
    def test_new_agent(self, at):
        stats = at.get_stats("unseen-agent")
        assert isinstance(stats, AgentStats)
        assert stats.total_uses == 0
        assert stats.rank == "N"

    def test_rank_updates_with_use(self, at):
        for _ in range(5):
            at.track("agent-r")
        stats = at.get_stats("agent-r")
        assert stats.rank == "N-B"

    def test_last_used_at_set(self, at):
        at.track("agent-y")
        stats = at.get_stats("agent-y")
        assert stats.last_used_at != ""

    def test_days_since_use_fresh(self, at):
        at.track("agent-fresh")
        stats = at.get_stats("agent-fresh")
        assert stats.days_since_use is not None
        assert stats.days_since_use == 0

    def test_parking_candidate_unused(self, at):
        stats = at.get_stats("never-used")
        assert stats.is_parking_candidate is True


# ── list_all_ranks ────────────────────────────────────────────────────────────

class TestListAllRanks:
    def test_empty(self, at):
        result = at.list_all_ranks()
        assert isinstance(result, list)

    def test_includes_tracked_agents(self, at):
        at.track("agent-a")
        at.track("agent-b")
        names = [s.agent_name for s in at.list_all_ranks()]
        assert "agent-a" in names
        assert "agent-b" in names

    def test_all_are_agent_stats(self, at):
        at.track("agent-z")
        for s in at.list_all_ranks():
            assert isinstance(s, AgentStats)


# ── get_parking_candidates ────────────────────────────────────────────────────

class TestParkingCandidates:
    def test_highly_used_not_parking(self, at):
        for _ in range(10):
            at.track("popular-agent")
        parking = [p.agent_name for p in at.get_parking_candidates()]
        assert "popular-agent" not in parking

    def test_unused_is_parking(self, at):
        # DB から参照されないが agents_dir から見えるエージェント
        # ここでは DB に記録なし = stats が total_uses=0
        at_with_dir = AgentTracker(db_path=":memory:")
        stats = at_with_dir.get_stats("ghost-agent")
        assert stats.is_parking_candidate is True


# ── audit_agent_text ──────────────────────────────────────────────────────────

class TestAuditAgentText:
    PERFECT_MD = """\
---
name: perfect-agent
description: |
  Perfect agent.
  Use when: all conditions.
  Do not trigger: never.
model: claude-sonnet-4
isolation: worktree
---
# Perfect Agent
"""

    def test_perfect_score(self, at):
        result = at.audit_agent_text("perfect-agent", self.PERFECT_MD)
        assert isinstance(result, AuditResult)
        assert result.score == 100

    def test_empty_text_zero(self, at):
        result = at.audit_agent_text("empty", "")
        assert result.score == 0

    def test_no_use_when(self, at):
        md = "---\nname: x\ndescription: y\nmodel: claude\nisolation: worktree\n---"
        result = at.audit_agent_text("x", md)
        assert result.score < 100
        assert "Use when" in result.failed_criteria

    def test_no_model(self, at):
        md = "---\nname: x\ndescription: Use when: ...\nDo not trigger: ...\nisolation: worktree\n---"
        result = at.audit_agent_text("x", md)
        assert "model" in result.failed_criteria

    def test_returns_suggestions(self, at):
        result = at.audit_agent_text("empty", "")
        assert len(result.suggestions) > 0

    def test_passed_criteria_listed(self, at):
        result = at.audit_agent_text("perfect-agent", self.PERFECT_MD)
        assert "name + description" in result.passed_criteria

    def test_partial_score_additive(self, at):
        # name + description のみ
        md = "---\nname: x\ndescription: y\n---\n"
        result = at.audit_agent_text("x", md)
        assert result.score == QUALITY_CRITERIA["has_name_and_description"]


# ── audit_agents_dir ──────────────────────────────────────────────────────────

class TestAuditAgentsDir:
    def test_nonexistent_dir(self, at, tmp_path):
        result = at.audit_agents_dir(agents_dir=str(tmp_path / "no_such_dir"))
        assert "error" in result

    def test_empty_dir(self, at, tmp_path):
        (tmp_path / "agents").mkdir()
        result = at.audit_agents_dir(agents_dir=str(tmp_path / "agents"))
        assert result["total"] == 0

    def test_counts_files(self, at, agents_dir):
        _write_agent_md(agents_dir, "agent1", "---\nname: a1\n---")
        _write_agent_md(agents_dir, "agent2", "---\nname: a2\n---")
        result = at.audit_agents_dir(agents_dir=str(agents_dir))
        assert result["total"] == 2

    def test_low_quality_detected(self, at, agents_dir):
        _write_agent_md(agents_dir, "bad-agent", "")
        result = at.audit_agents_dir(agents_dir=str(agents_dir), min_score=50)
        assert result["failing"] >= 1

    def test_perfect_agent_passes(self, at, agents_dir):
        md = (
            "---\nname: perfect\ndescription: Use when: ... Do not trigger: ...\n"
            "model: claude\nisolation: worktree\n---\n"
        )
        _write_agent_md(agents_dir, "perfect", md)
        result = at.audit_agents_dir(agents_dir=str(agents_dir), min_score=60)
        assert result["passing"] >= 1


# ── stats ────────────────────────────────────────────────────────────────────

class TestStats:
    def test_empty_stats(self, at):
        s = at.stats()
        assert "total_agents" in s
        assert "rank_distribution" in s
        assert "parking_candidates" in s

    def test_total_after_tracks(self, at):
        at.track("a1")
        at.track("a2")
        s = at.stats()
        assert s["total_agents"] >= 2


# ── get_agent_tracker シングルトン ────────────────────────────────────────────

class TestSingleton:
    def test_same_instance(self):
        a = get_agent_tracker(db_path=":memory:")
        b = get_agent_tracker()
        assert a is b

    def test_reset_works(self):
        import agent_tracker as _mod
        a = get_agent_tracker(db_path=":memory:")
        _mod._instance = None
        b = get_agent_tracker(db_path=":memory:")
        assert a is not b
