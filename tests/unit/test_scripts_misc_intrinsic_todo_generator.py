"""
Unit tests for scripts/misc/intrinsic_todo_generator.py
"""
import sys
import json
from unittest.mock import MagicMock, patch
from pathlib import Path

# ── mocks ─────────────────────────────────────────────────────────────────
_ml = MagicMock()
_ml.get_service_logger.return_value = MagicMock()
_ml.get_logger.return_value = MagicMock()
sys.modules.setdefault("manaos_logger", _ml)

_oi = MagicMock()
_oi.ObsidianIntegration = MagicMock()
sys.modules.setdefault("obsidian_integration", _oi)

_paths = MagicMock()
_paths.LEARNING_SYSTEM_PORT = 5200
_paths.METRICS_COLLECTOR_PORT = 5300
_paths.TASK_CRITIC_PORT = 5102
sys.modules.setdefault("_paths", _paths)

import pytest
from scripts.misc.intrinsic_todo_generator import (
    IntrinsicTodo,
    IntrinsicTodoGenerator,
)


def _todo(
    todo_id: str = "t1",
    title: str = "テスト",
    impact: float = 80.0,
    effort: float = 40.0,
    priority: int = 8,
    category: str = "Performance",
    hours: float = 2.0,
) -> IntrinsicTodo:
    return IntrinsicTodo(
        todo_id=todo_id,
        title=title,
        description="説明",
        impact_score=impact,
        effort_score=effort,
        priority=priority,
        category=category,
        estimated_hours=hours,
        requires_approval=False,
    )


@pytest.fixture
def gen(tmp_path):
    return IntrinsicTodoGenerator(storage_path=tmp_path / "gen_todos.json")


# ── TestIntrinsicTodoDataclass ────────────────────────────────────────────
class TestIntrinsicTodoDataclass:
    def test_created_at_auto(self):
        t = _todo()
        assert t.created_at  # 空でない

    def test_explicit_created_at(self):
        t = IntrinsicTodo(
            todo_id="x", title="T", description="D", impact_score=50,
            effort_score=50, priority=5, category="C", estimated_hours=1,
            requires_approval=False, created_at="2026-01-01T00:00:00",
        )
        assert t.created_at == "2026-01-01T00:00:00"

    def test_efficiency_score_normal(self):
        t = _todo(impact=80.0, effort=40.0)
        assert t.efficiency_score == pytest.approx(2.0)

    def test_efficiency_score_zero_effort(self):
        t = _todo(impact=100.0, effort=0.0)
        assert t.efficiency_score == 0.0

    def test_efficiency_score_high_impact(self):
        t1 = _todo(impact=90.0, effort=30.0)
        t2 = _todo(impact=60.0, effort=60.0)
        assert t1.efficiency_score > t2.efficiency_score


# ── TestInit ──────────────────────────────────────────────────────────────
class TestInit:
    def test_empty_todos(self, gen):
        assert gen.todos == []

    def test_loads_existing(self, tmp_path):
        storage = tmp_path / "load_test.json"
        data = {
            "todos": [{
                "todo_id": "e1", "title": "T", "description": "D",
                "impact_score": 80.0, "effort_score": 40.0, "priority": 5,
                "category": "C", "estimated_hours": 1.0,
                "requires_approval": False, "created_at": "2026-01-01T00:00:00",
            }]
        }
        storage.write_text(json.dumps(data), encoding="utf-8")
        g2 = IntrinsicTodoGenerator(storage_path=storage)
        assert len(g2.todos) == 1
        assert g2.todos[0].todo_id == "e1"


# ── TestSaveTodos ─────────────────────────────────────────────────────────
class TestSaveTodos:
    def test_creates_file(self, gen):
        gen.todos = [_todo("s1")]
        gen._save_todos()
        assert gen.storage_path.exists()

    def test_file_valid_json(self, gen):
        gen.todos = [_todo("s2")]
        gen._save_todos()
        content = json.loads(gen.storage_path.read_text(encoding="utf-8"))
        assert "todos" in content
        assert len(content["todos"]) == 1

    def test_last_updated_present(self, gen):
        gen.todos = []
        gen._save_todos()
        content = json.loads(gen.storage_path.read_text(encoding="utf-8"))
        assert "last_updated" in content


# ── TestGenerateWeeklyTop3 ────────────────────────────────────────────────
class TestGenerateWeeklyTop3:
    def test_returns_at_most_3(self, gen):
        # analyze_improvement_opportunities が httpx を使うので mock
        with patch.object(gen, "analyze_improvement_opportunities", return_value=[
            _todo("g1", impact=90, effort=10),
            _todo("g2", impact=80, effort=20),
            _todo("g3", impact=70, effort=30),
            _todo("g4", impact=60, effort=40),
        ]):
            result = gen.generate_weekly_top3()
        assert len(result) <= 3

    def test_deduplicates_by_title(self, gen):
        gen.todos = [_todo("x1", title="同じ")]
        with patch.object(gen, "analyze_improvement_opportunities", return_value=[
            _todo("x2", title="同じ"),
        ]):
            result = gen.generate_weekly_top3()
        titles = [t.title for t in gen.todos]
        assert titles.count("同じ") == 1

    def test_saves_after_generate(self, gen):
        with patch.object(gen, "analyze_improvement_opportunities", return_value=[]):
            gen.generate_weekly_top3()
        assert gen.storage_path.exists()

    def test_sorted_by_efficiency(self, gen):
        with patch.object(gen, "analyze_improvement_opportunities", return_value=[
            _todo("e1", title="Low", impact=40.0, effort=80.0),
            _todo("e2", title="High", impact=90.0, effort=10.0),
        ]):
            result = gen.generate_weekly_top3()
        if len(result) >= 2:
            assert result[0].efficiency_score >= result[1].efficiency_score


# ── TestCountPlaybooks ────────────────────────────────────────────────────
class TestCountPlaybooks:
    def test_returns_int(self, gen):
        count = gen._count_playbooks()
        assert isinstance(count, int)
        assert count >= 0
