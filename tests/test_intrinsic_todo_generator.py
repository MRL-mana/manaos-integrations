#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_intrinsic_todo_generator.py
IntrinsicTodoGenerator の単体テスト
外部依存（httpx / Obsidian）はすべてモック
"""

import json
import sys
from dataclasses import asdict
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest

# sys.path に scripts/misc を追加
_PROJECT_ROOT = Path(__file__).parent.parent
if str(_PROJECT_ROOT / "scripts" / "misc") not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT / "scripts" / "misc"))

# --- 外部モジュールのスタブ化 ---
_stubs = {}
for _mod in ("manaos_logger", "obsidian_integration", "_paths"):
    _m = MagicMock()
    _stubs[_mod] = _m
    sys.modules.setdefault(_mod, _m)

# _paths のポート定数
sys.modules["_paths"].LEARNING_SYSTEM_PORT = 5200
sys.modules["_paths"].METRICS_COLLECTOR_PORT = 5201
sys.modules["_paths"].TASK_CRITIC_PORT = 5202

# manaos_logger のスタブ
_logger_stub = MagicMock()
sys.modules["manaos_logger"].get_logger = MagicMock(return_value=_logger_stub)
sys.modules["manaos_logger"].get_service_logger = MagicMock(return_value=_logger_stub)

# obsidian_integration スタブ
_obs_stub = MagicMock()
sys.modules["obsidian_integration"].ObsidianIntegration = MagicMock(return_value=_obs_stub)

from intrinsic_todo_generator import IntrinsicTodo, IntrinsicTodoGenerator


# ======================================================
# IntrinsicTodo のテスト
# ======================================================

class TestIntrinsicTodo:
    def test_default_created_at_set(self):
        """created_at が自動設定される"""
        todo = IntrinsicTodo(
            todo_id="t1",
            title="テスト",
            description="説明",
            impact_score=80.0,
            effort_score=40.0,
            priority=8,
            category="Test",
            estimated_hours=2.0,
            requires_approval=False,
        )
        assert todo.created_at != ""
        # ISO フォーマットであること
        from datetime import datetime
        datetime.fromisoformat(todo.created_at)

    def test_explicit_created_at_preserved(self):
        """明示的に created_at を指定した場合は保持される"""
        ts = "2024-01-01T00:00:00"
        todo = IntrinsicTodo(
            todo_id="t2",
            title="テスト",
            description="説明",
            impact_score=80.0,
            effort_score=40.0,
            priority=8,
            category="Test",
            estimated_hours=2.0,
            requires_approval=False,
            created_at=ts,
        )
        assert todo.created_at == ts

    def test_efficiency_score_calculation(self):
        """efficiency_score = impact / effort"""
        todo = IntrinsicTodo(
            todo_id="t3",
            title="テスト",
            description="説明",
            impact_score=100.0,
            effort_score=50.0,
            priority=5,
            category="Test",
            estimated_hours=1.0,
            requires_approval=False,
        )
        assert todo.efficiency_score == pytest.approx(2.0)

    def test_efficiency_score_zero_effort(self):
        """effort_score=0 の場合は 0.0"""
        todo = IntrinsicTodo(
            todo_id="t4",
            title="テスト",
            description="説明",
            impact_score=100.0,
            effort_score=0.0,
            priority=5,
            category="Test",
            estimated_hours=1.0,
            requires_approval=False,
        )
        assert todo.efficiency_score == 0.0

    def test_asdict_serializable(self):
        """dataclasses.asdict で JSON シリアライズ可能"""
        todo = IntrinsicTodo(
            todo_id="t5",
            title="テスト",
            description="説明",
            impact_score=80.0,
            effort_score=40.0,
            priority=8,
            category="Test",
            estimated_hours=2.0,
            requires_approval=False,
        )
        d = asdict(todo)
        json_str = json.dumps(d, ensure_ascii=False)
        assert "テスト" in json_str


# ======================================================
# IntrinsicTodoGenerator のテスト
# ======================================================

def _make_todo(**kw):
    defaults = dict(
        todo_id="t1",
        title="改善タスク",
        description="説明",
        impact_score=80.0,
        effort_score=40.0,
        priority=8,
        category="Performance",
        estimated_hours=2.0,
        requires_approval=False,
        created_at="2024-01-01T00:00:00",
    )
    defaults.update(kw)
    return IntrinsicTodo(**defaults)


class TestIntrinsicTodoGenerator:

    @pytest.fixture
    def generator(self, tmp_path):
        """ストレージパスを tmp_path に向けた Generator"""
        with patch("httpx.get"):
            gen = IntrinsicTodoGenerator(storage_path=tmp_path / "todos.json")
        return gen

    # ── ロード/セーブ ──────────────────────────────────────

    def test_load_todos_empty_when_no_file(self, tmp_path):
        """ファイルがなければ空リスト"""
        gen = IntrinsicTodoGenerator(storage_path=tmp_path / "nonexistent.json")
        assert gen.todos == []

    def test_save_and_load_roundtrip(self, tmp_path):
        """セーブしたToDoが再ロードできる"""
        gen = IntrinsicTodoGenerator(storage_path=tmp_path / "todos.json")
        todo = _make_todo()
        gen.todos = [todo]
        gen._save_todos()

        gen2 = IntrinsicTodoGenerator(storage_path=tmp_path / "todos.json")
        assert len(gen2.todos) == 1
        assert gen2.todos[0].title == "改善タスク"

    def test_save_todos_creates_json(self, tmp_path):
        """_save_todos がファイルを作成する"""
        gen = IntrinsicTodoGenerator(storage_path=tmp_path / "todos.json")
        gen.todos = [_make_todo()]
        gen._save_todos()

        stored = json.loads((tmp_path / "todos.json").read_text(encoding="utf-8"))
        assert "todos" in stored
        assert len(stored["todos"]) == 1
        assert "last_updated" in stored

    def test_load_todos_invalid_json_fallback(self, tmp_path):
        """壊れた JSON はエラーなく空リストにフォールバック"""
        path = tmp_path / "todos.json"
        path.write_text("INVALID JSON", encoding="utf-8")
        gen = IntrinsicTodoGenerator(storage_path=path)
        assert gen.todos == []

    # ── analyze_improvement_opportunities ─────────────────

    def test_analyze_low_success_rate_generates_todo(self, tmp_path):
        """success_rate < 0.8 のとき成功率向上 ToDo が生成される"""
        metrics_data = {"success_rate": 0.5, "error_rate": 0.0, "avg_response_time": 100}
        learning_data = {"patterns_learned": 20}

        mock_resp_metrics = MagicMock()
        mock_resp_metrics.status_code = 200
        mock_resp_metrics.json.return_value = metrics_data

        mock_resp_learning = MagicMock()
        mock_resp_learning.status_code = 200
        mock_resp_learning.json.return_value = learning_data

        gen = IntrinsicTodoGenerator(storage_path=tmp_path / "todos.json")

        with patch("httpx.get", side_effect=[mock_resp_learning, mock_resp_metrics]):
            todos = gen.analyze_improvement_opportunities()

        titles = [t.title for t in todos]
        assert any("成功率" in t for t in titles)

    def test_analyze_high_error_rate_generates_todo(self, tmp_path):
        """error_rate > 0.1 のときエラー率削減 ToDo が生成される"""
        metrics_data = {"success_rate": 0.9, "error_rate": 0.3, "avg_response_time": 100}
        learning_data = {"patterns_learned": 20}

        mock_metrics = MagicMock(status_code=200)
        mock_metrics.json.return_value = metrics_data
        mock_learning = MagicMock(status_code=200)
        mock_learning.json.return_value = learning_data

        gen = IntrinsicTodoGenerator(storage_path=tmp_path / "todos.json")

        with patch("httpx.get", side_effect=[mock_learning, mock_metrics]):
            todos = gen.analyze_improvement_opportunities()

        titles = [t.title for t in todos]
        assert any("エラー率" in t for t in titles)

    def test_analyze_slow_response_generates_todo(self, tmp_path):
        """avg_response_time > 2000ms のときレスポンス時間 ToDo が生成される"""
        metrics_data = {"success_rate": 0.95, "error_rate": 0.05, "avg_response_time": 3000}
        learning_data = {"patterns_learned": 20}

        mock_metrics = MagicMock(status_code=200)
        mock_metrics.json.return_value = metrics_data
        mock_learning = MagicMock(status_code=200)
        mock_learning.json.return_value = learning_data

        gen = IntrinsicTodoGenerator(storage_path=tmp_path / "todos.json")

        with patch("httpx.get", side_effect=[mock_learning, mock_metrics]):
            todos = gen.analyze_improvement_opportunities()

        titles = [t.title for t in todos]
        assert any("レスポンス" in t for t in titles)

    def test_analyze_low_patterns_generates_todo(self, tmp_path):
        """patterns_learned < 10 のときパターン学習 ToDo が生成される"""
        metrics_data = {"success_rate": 0.95, "error_rate": 0.02, "avg_response_time": 100}
        learning_data = {"patterns_learned": 3}

        mock_metrics = MagicMock(status_code=200)
        mock_metrics.json.return_value = metrics_data
        mock_learning = MagicMock(status_code=200)
        mock_learning.json.return_value = learning_data

        gen = IntrinsicTodoGenerator(storage_path=tmp_path / "todos.json")

        with patch("httpx.get", side_effect=[mock_learning, mock_metrics]):
            todos = gen.analyze_improvement_opportunities()

        titles = [t.title for t in todos]
        assert any("パターン" in t for t in titles)

    def test_analyze_max_3_todos(self, tmp_path):
        """analyze は最大 3 件を返す"""
        metrics_data = {"success_rate": 0.3, "error_rate": 0.5, "avg_response_time": 5000}
        learning_data = {"patterns_learned": 0}

        mock_metrics = MagicMock(status_code=200)
        mock_metrics.json.return_value = metrics_data
        mock_learning = MagicMock(status_code=200)
        mock_learning.json.return_value = learning_data

        gen = IntrinsicTodoGenerator(storage_path=tmp_path / "todos.json")

        with patch("httpx.get", side_effect=[mock_learning, mock_metrics]):
            todos = gen.analyze_improvement_opportunities()

        assert len(todos) <= 3

    def test_analyze_http_error_returns_empty(self, tmp_path):
        """HTTP 呼び出し失敗時は空リストを返す（クラッシュしない）"""
        gen = IntrinsicTodoGenerator(storage_path=tmp_path / "todos.json")

        with patch("httpx.get", side_effect=Exception("Connection refused")):
            todos = gen.analyze_improvement_opportunities()

        assert isinstance(todos, list)

    def test_analyze_sorts_by_efficiency(self, tmp_path):
        """analyze 結果は efficiency_score 降順でソートされている"""
        metrics_data = {"success_rate": 0.3, "error_rate": 0.5, "avg_response_time": 3000}
        learning_data = {"patterns_learned": 1}

        mock_metrics = MagicMock(status_code=200)
        mock_metrics.json.return_value = metrics_data
        mock_learning = MagicMock(status_code=200)
        mock_learning.json.return_value = learning_data

        gen = IntrinsicTodoGenerator(storage_path=tmp_path / "todos.json")

        with patch("httpx.get", side_effect=[mock_learning, mock_metrics]):
            todos = gen.analyze_improvement_opportunities()

        scores = [t.efficiency_score for t in todos]
        assert scores == sorted(scores, reverse=True)

    # ── generate_weekly_top3 ───────────────────────────────

    def test_generate_weekly_top3_returns_list(self, tmp_path):
        """generate_weekly_top3 はリストを返す"""
        gen = IntrinsicTodoGenerator(storage_path=tmp_path / "todos.json")

        with patch.object(gen, "analyze_improvement_opportunities", return_value=[]):
            top3 = gen.generate_weekly_top3()

        assert isinstance(top3, list)
        assert len(top3) <= 3

    def test_generate_weekly_top3_deduplicates(self, tmp_path):
        """同タイトルの ToDo は重複排除される"""
        gen = IntrinsicTodoGenerator(storage_path=tmp_path / "todos.json")
        gen.todos = [_make_todo(todo_id="a"), _make_todo(todo_id="b")]  # 同タイトル

        with patch.object(gen, "analyze_improvement_opportunities", return_value=[]):
            top3 = gen.generate_weekly_top3()

        # 同タイトルは 1 件にまとめられる
        titles = [t.title for t in gen.todos]
        assert len(titles) == len(set(titles))

    def test_generate_weekly_top3_saves(self, tmp_path):
        """generate_weekly_top3 の後にファイルが保存されている"""
        gen = IntrinsicTodoGenerator(storage_path=tmp_path / "todos.json")

        with patch.object(gen, "analyze_improvement_opportunities", return_value=[]):
            gen.generate_weekly_top3()

        assert (tmp_path / "todos.json").exists()

    # ── _count_playbooks ───────────────────────────────────

    def test_count_playbooks_no_vault_returns_0(self, tmp_path):
        """Vault が存在しない場合は 0"""
        gen = IntrinsicTodoGenerator(storage_path=tmp_path / "todos.json")
        with patch("pathlib.Path.home", return_value=tmp_path):
            count = gen._count_playbooks()
        assert count == 0

    def test_count_playbooks_counts_md_files(self, tmp_path):
        """Vault が存在する場合は .md ファイル数を返す"""
        vault = tmp_path / "Documents" / "Obsidian Vault" / "ManaOS" / "System" / "Playbooks"
        vault.mkdir(parents=True)
        (vault / "play1.md").write_text("# playbook1")
        (vault / "play2.md").write_text("# playbook2")
        (vault / "ignore.txt").write_text("not md")

        gen = IntrinsicTodoGenerator(storage_path=tmp_path / "todos.json")
        with patch("pathlib.Path.home", return_value=tmp_path):
            count = gen._count_playbooks()

        assert count == 2


# ======================================================
# Flask API エンドポイントのテスト
# ======================================================

class TestFlaskAPI:
    @pytest.fixture
    def client(self, tmp_path):
        import intrinsic_todo_generator as itg
        itg.app.config["TESTING"] = True
        itg.todo_generator = None

        with patch.object(
            IntrinsicTodoGenerator,
            "__init__",
            lambda self, **kw: (
                setattr(self, "todos", []),
                setattr(self, "storage_path", tmp_path / "todos.json"),
            ) and None,
        ):
            yield itg.app.test_client()

    def test_health_endpoint(self, tmp_path):
        """GET /health が 200 を返す"""
        import intrinsic_todo_generator as itg
        itg.app.config["TESTING"] = True
        itg.todo_generator = None

        with itg.app.test_client() as c:
            # todo_generator を直接セット
            mock_gen = MagicMock()
            mock_gen.todos = []
            itg.todo_generator = mock_gen
            resp = c.get("/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "healthy"

    def test_get_todos_endpoint(self, tmp_path):
        """GET /api/todos が todos リストを返す"""
        import intrinsic_todo_generator as itg
        itg.app.config["TESTING"] = True

        mock_gen = MagicMock()
        mock_gen.todos = [_make_todo()]
        itg.todo_generator = mock_gen

        with itg.app.test_client() as c:
            resp = c.get("/api/todos")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "todos" in data
        assert data["count"] == 1
