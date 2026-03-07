"""
Unit tests for scripts/misc/intrinsic_todo_queue.py
"""
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

# ── mocks ─────────────────────────────────────────────────────────────────
_ml = MagicMock()
_ml.get_service_logger.return_value = MagicMock()
_ml.get_logger.return_value = MagicMock()
sys.modules.setdefault("manaos_logger", _ml)

sys.modules.setdefault("flask_cors", MagicMock())

_paths = MagicMock()
_paths.INTRINSIC_MOTIVATION_PORT = 8095
sys.modules.setdefault("_paths", _paths)

import pytest
from scripts.misc.intrinsic_todo_queue import (
    IntrinsicTodo,
    IntrinsicTodoQueue,
    TodoState,
)


def _todo(
    todo_id: str = "t1",
    title: str = "テストToDo",
    tags: list = None,
    state: TodoState = TodoState.PROPOSED,
    created_at: str = "",
) -> IntrinsicTodo:
    return IntrinsicTodo(
        id=todo_id,
        title=title,
        reason="理由",
        impact="影響",
        risk="low",
        autonomy_level_required=1,
        estimated_minutes=30,
        tags=tags or ["test"],
        state=state,
        created_at=created_at,
    )


@pytest.fixture
def q(tmp_path):
    return IntrinsicTodoQueue(storage_path=tmp_path / "todos.json")


# ── TestTodoState ─────────────────────────────────────────────────────────
class TestTodoState:
    def test_values(self):
        assert TodoState.PROPOSED.value == "PROPOSED"
        assert TodoState.APPROVED.value == "APPROVED"
        assert TodoState.REJECTED.value == "REJECTED"
        assert TodoState.EXECUTED.value == "EXECUTED"
        assert TodoState.EXPIRED.value == "EXPIRED"

    def test_is_str_subclass(self):
        assert isinstance(TodoState.PROPOSED, str)


# ── TestIntrinsicTodo ─────────────────────────────────────────────────────
class TestIntrinsicTodo:
    def test_created_at_auto_set(self):
        t = _todo()
        assert t.created_at  # 空でない

    def test_default_state_proposed(self):
        t = _todo()
        assert t.state == TodoState.PROPOSED

    def test_explicit_created_at_kept(self):
        t = _todo(created_at="2026-01-01T00:00:00")
        assert t.created_at == "2026-01-01T00:00:00"


# ── TestInit ──────────────────────────────────────────────────────────────
class TestInit:
    def test_empty_todos_on_new(self, q):
        assert q.todos == []

    def test_loads_existing_todos(self, tmp_path):
        storage = tmp_path / "existing.json"
        todo_data = {
            "todos": [{
                "id": "e1", "title": "T", "reason": "R", "impact": "I",
                "risk": "low", "autonomy_level_required": 1,
                "estimated_minutes": 10, "tags": [], "state": "PROPOSED",
                "created_at": datetime.now().isoformat(),
                "approved_at": None, "executed_at": None,
                "rejected_at": None, "rejection_reason": None, "category": None
            }]
        }
        storage.write_text(json.dumps(todo_data), encoding="utf-8")
        q2 = IntrinsicTodoQueue(storage_path=storage)
        assert len(q2.todos) == 1
        assert q2.todos[0].id == "e1"


# ── TestAddTodo ───────────────────────────────────────────────────────────
class TestAddTodo:
    def test_appends_todo(self, q):
        t = _todo("add1")
        q.add_todo(t)
        assert len(q.todos) == 1

    def test_returns_todo(self, q):
        t = _todo("ret1")
        result = q.add_todo(t)
        assert result.id == "ret1"

    def test_persisted(self, q):
        q.add_todo(_todo("pers1"))
        q2 = IntrinsicTodoQueue(storage_path=q.storage_path)
        assert len(q2.todos) == 1


# ── TestGetTodos ──────────────────────────────────────────────────────────
class TestGetTodos:
    def test_returns_all(self, q):
        q.add_todo(_todo("g1"))
        q.add_todo(_todo("g2"))
        assert len(q.get_todos()) == 2

    def test_filter_by_state(self, q):
        q.add_todo(_todo("s1", state=TodoState.PROPOSED))
        q.add_todo(_todo("s2", state=TodoState.APPROVED))
        proposed = q.get_todos(state=TodoState.PROPOSED)
        assert all(t.state == TodoState.PROPOSED for t in proposed)


# ── TestApproveTodo ───────────────────────────────────────────────────────
class TestApproveTodo:
    def test_approves_proposed(self, q):
        q.add_todo(_todo("ap1"))
        with patch("scripts.misc.intrinsic_todo_queue.httpx"):
            result = q.approve_todo("ap1")
        assert result is True
        assert q.todos[0].state == TodoState.APPROVED

    def test_returns_false_for_missing(self, q):
        with patch("scripts.misc.intrinsic_todo_queue.httpx"):
            result = q.approve_todo("missing")
        assert result is False

    def test_cannot_approve_approved(self, q):
        q.add_todo(_todo("ap2", state=TodoState.APPROVED))
        with patch("scripts.misc.intrinsic_todo_queue.httpx"):
            result = q.approve_todo("ap2")
        assert result is False

    def test_approved_at_set(self, q):
        q.add_todo(_todo("ap3"))
        with patch("scripts.misc.intrinsic_todo_queue.httpx"):
            q.approve_todo("ap3")
        assert q.todos[0].approved_at is not None


# ── TestRejectTodo ────────────────────────────────────────────────────────
class TestRejectTodo:
    def test_rejects_proposed(self, q):
        q.add_todo(_todo("rej1"))
        with patch("scripts.misc.intrinsic_todo_queue.httpx"):
            result = q.reject_todo("rej1", reason="不要")
        assert result is True
        assert q.todos[0].state == TodoState.REJECTED

    def test_rejection_reason_stored(self, q):
        q.add_todo(_todo("rej2"))
        with patch("scripts.misc.intrinsic_todo_queue.httpx"):
            q.reject_todo("rej2", reason="リスクが高い")
        assert q.todos[0].rejection_reason == "リスクが高い"

    def test_returns_false_for_missing(self, q):
        with patch("scripts.misc.intrinsic_todo_queue.httpx"):
            result = q.reject_todo("nope")
        assert result is False


# ── TestCheckExpiredTodos ─────────────────────────────────────────────────
class TestCheckExpiredTodos:
    def test_old_proposed_expires(self, q):
        old_time = (datetime.now() - timedelta(hours=25)).isoformat()
        t = _todo("exp1", created_at=old_time)
        q.todos.append(t)
        q._check_expired_todos()
        assert q.todos[0].state == TodoState.EXPIRED

    def test_recent_proposed_stays(self, q):
        t = _todo("fresh1")
        q.add_todo(t)
        q._check_expired_todos()
        assert q.todos[0].state == TodoState.PROPOSED


# ── TestMergeDuplicateTodos ───────────────────────────────────────────────
class TestMergeDuplicateTodos:
    def test_merges_same_title_and_tags(self, q):
        t1 = _todo("dup1", title="同じタイトル", tags=["a"])
        t2 = _todo("dup2", title="同じタイトル", tags=["a"])
        q.todos = [t1, t2]
        q._merge_duplicate_todos()
        proposed = [t for t in q.todos if t.state == TodoState.PROPOSED]
        assert len(proposed) == 1

    def test_keeps_different_titles(self, q):
        t1 = _todo("diff1", title="タイトルA", tags=["a"])
        t2 = _todo("diff2", title="タイトルB", tags=["a"])
        q.todos = [t1, t2]
        q._merge_duplicate_todos()
        assert len(q.todos) == 2
