#!/usr/bin/env python3
"""
RLAnything テスト – 3 フェーズ統合テスト
"""

import json
import sys
import tempfile
from pathlib import Path

# パス解決
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rl_anything.types import (
    DifficultyLevel,
    FeedbackType,
    TaskOutcome,
    TaskRecord,
    ToolAction,
    Skill,
    RewardSignal,
)
from rl_anything.observation_hook import ObservationHook
from rl_anything.feedback_engine import FeedbackEngine
from rl_anything.evolution_engine import EvolutionEngine
from rl_anything.orchestrator import RLAnythingOrchestrator


def test_types():
    """型定義の基本テスト"""
    action = ToolAction(
        tool_name="read_file",
        parameters={"path": "src/app.py"},
        result_summary="file content...",
    )
    d = action.to_dict()
    assert d["tool_name"] == "read_file"
    assert "timestamp" in d

    record = TaskRecord(task_id="t-1", description="test task")
    d = record.to_dict()
    assert d["outcome"] == "unknown"
    assert d["difficulty"] == "standard"

    skill = Skill(
        skill_id="s1",
        name="テスト先行",
        description="テストを先に書く",
        pattern="test_first",
        context_tags=["tdd"],
        success_rate=0.85,
        sample_count=10,
    )
    assert skill.to_dict()["success_rate"] == 0.85
    print("  [PASS] types")


def test_observation_hook():
    """Phase 1: 観測フックテスト"""
    with tempfile.TemporaryDirectory() as tmpdir:
        hook = ObservationHook(log_dir=Path(tmpdir))

        # タスク開始
        hook.on_task_start("t-1", "Reactコンポーネント修正")
        assert "t-1" in hook.get_active_tasks()

        # ツール使用
        hook.on_tool_start("read_file", {"path": "App.tsx"})
        hook.on_tool_end("read_file", result="function App() {...}")

        hook.on_tool_start("create_file", {"path": "App.test.tsx"})
        hook.on_tool_end("create_file", result="test created")

        # 中間スコア
        hook.on_intermediate_score("t-1", 0.8, "lint pass")

        # タスク完了
        record = hook.on_task_end("t-1", outcome="success", final_score=0.95)
        assert record.outcome == TaskOutcome.SUCCESS
        assert len(record.actions) == 2
        assert record.intermediate_scores == [0.8]
        assert record.final_score == 0.95

        stats = hook.get_stats()
        assert stats["total"] == 1
        assert stats["success_rate"] == 1.0

        # JSONL が書き出されたか
        events_files = list(Path(tmpdir).glob("events_*.jsonl"))
        assert len(events_files) >= 1
        print("  [PASS] observation_hook")


def test_feedback_engine():
    """Phase 2: フィードバックエンジンテスト"""
    engine = FeedbackEngine()

    # 統合フィードバック
    record = TaskRecord(
        task_id="t-1",
        description="test",
        intermediate_scores=[0.6, 0.8],
        final_score=0.9,
        outcome=TaskOutcome.SUCCESS,
    )
    record.actions = [
        ToolAction("run_test", {}, "pass", None),
        ToolAction("create_file", {}, "created", None),
    ]
    signal = engine.compute_integration_feedback(record)
    assert 0.0 <= signal.score <= 1.0
    assert signal.feedback_type == FeedbackType.INTEGRATION
    print(f"    integration score = {signal.score:.3f}")

    # 一貫性フィードバック (最低 5 件必要)
    records = []
    for i in range(10):
        outcome = TaskOutcome.SUCCESS if i % 3 != 0 else TaskOutcome.FAILURE
        r = TaskRecord(
            task_id=f"t-{i}",
            description=f"task {i}",
            outcome=outcome,
        )
        r.actions = [
            ToolAction("read_file", {}, "read ok", None),
            ToolAction("run_test" if i % 2 == 0 else "edit_file", {}, "ok", None),
        ]
        records.append(r)

    consistency = engine.compute_consistency_feedback(records)
    assert consistency.feedback_type == FeedbackType.CONSISTENCY
    print(f"    consistency score = {consistency.score:.3f}")

    # 評価フィードバック
    difficulty, evaluation = engine.compute_evaluation_feedback(records)
    assert isinstance(difficulty, DifficultyLevel)
    print(f"    evaluation: difficulty={difficulty.value}, rate={evaluation.score:.3f}")

    print("  [PASS] feedback_engine")


def test_evolution_engine():
    """Phase 3: 自己進化エンジンテスト"""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = {
            "evolution": {
                "enabled": True,
                "skill_extraction_min_samples": 2,
                "skill_success_threshold": 0.50,
                "memory_md_path": str(Path(tmpdir) / "MEMORY.md"),
                "max_skills": 50,
                "auto_apply_skills": True,
            }
        }
        engine = EvolutionEngine(config=config)
        engine._data_dir = Path(tmpdir)
        engine.memory_md_path = Path(tmpdir) / "MEMORY.md"

        # テスト用レコード
        records = []
        for i in range(8):
            outcome = TaskOutcome.SUCCESS if i < 6 else TaskOutcome.FAILURE
            r = TaskRecord(
                task_id=f"t-{i}",
                description=f"task {i}",
                outcome=outcome,
            )
            # テスト先行パターン: 前半に test ツール
            r.actions = [
                ToolAction("run_test", {}, "test pass", None),
                ToolAction("read_file", {}, "read ok", None),
                ToolAction("create_file", {}, "created", None),
            ]
            records.append(r)

        # スキル抽出
        new_skills = engine.extract_skills(records)
        assert len(new_skills) > 0, "スキルが抽出されるべき"
        print(f"    extracted {len(new_skills)} skills")

        for skill in new_skills[:3]:
            print(f"      - {skill.name}: rate={skill.success_rate:.2f}")

        # 難易度調整
        adj = engine.adjust_difficulty(DifficultyLevel.ABSTRACT, 0.85)
        assert adj["changed"]
        assert engine.current_difficulty == DifficultyLevel.ABSTRACT

        # MEMORY.md 更新
        mem_result = engine.update_memory_md(force=True)
        assert mem_result.get("updated")
        memory_content = (Path(tmpdir) / "MEMORY.md").read_text(encoding="utf-8")
        assert "RLAnything" in memory_content
        assert "rl_anything:start" in memory_content
        print(f"    MEMORY.md written ({len(memory_content)} chars)")

        print("  [PASS] evolution_engine")


def test_orchestrator_full_cycle():
    """統合テスト: オーケストレータで完全サイクル"""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = {
            "observation": {
                "enabled": True,
                "log_dir": str(Path(tmpdir) / "logs"),
                "max_log_entries": 1000,
                "log_tool_params": True,
                "log_result_preview_chars": 200,
            },
            "reward_model": {
                "enabled": True,
                "intermediate_weight": 0.4,
                "final_weight": 0.6,
                "scoring_criteria": {
                    "test_written_first": 0.15,
                    "error_handled": 0.10,
                    "code_commented": 0.05,
                    "single_responsibility": 0.10,
                    "no_regressions": 0.20,
                    "task_completed": 0.40,
                },
            },
            "curriculum": {
                "enabled": True,
                "target_success_rate": 0.80,
                "window_size": 10,
                "difficulty_levels": {
                    "concrete": {"min_rate": 0.00, "max_rate": 0.20},
                    "guided": {"min_rate": 0.20, "max_rate": 0.50},
                    "standard": {"min_rate": 0.50, "max_rate": 0.80},
                    "abstract": {"min_rate": 0.80, "max_rate": 1.00},
                },
            },
            "evolution": {
                "enabled": True,
                "skill_extraction_min_samples": 2,
                "skill_success_threshold": 0.40,
                "memory_md_path": str(Path(tmpdir) / "MEMORY.md"),
                "max_skills": 50,
                "auto_apply_skills": True,
            },
        }

        # config.json を tmpdir に書き出さない → 直接渡す
        cfg_path = Path(tmpdir) / "config.json"
        cfg_path.write_text(json.dumps(config, indent=2), encoding="utf-8")

        rl = RLAnythingOrchestrator(config_path=cfg_path)

        # 複数タスクを実行
        outcomes = ["success", "success", "success", "failure", "success", "success"]
        for i, outcome in enumerate(outcomes):
            task_id = f"task-{i:03d}"
            rl.begin_task(task_id, f"テストタスク #{i}")

            # ツール使用
            rl.log_tool("read_file", {"path": f"src/file{i}.py"}, result="content...")
            if i % 2 == 0:
                rl.log_tool("run_test", {}, result="test passed")
            rl.log_tool("create_file", {"path": f"src/new{i}.py"}, result="created")

            # 中間スコア
            rl.score_intermediate(task_id, 0.7 + i * 0.03)

            # タスク終了
            score = 0.9 if outcome == "success" else 0.2
            result = rl.end_task(task_id, outcome=outcome, score=score)

        # ダッシュボード確認
        dashboard = rl.get_dashboard()
        assert dashboard["observation"]["total"] == len(outcomes)
        assert dashboard["cycle_count"] == len(outcomes)
        print(f"    cycles: {dashboard['cycle_count']}")
        print(f"    success_rate: {dashboard['observation']['success_rate']:.2f}")
        print(f"    difficulty: {dashboard['current_difficulty']}")
        print(f"    skills: {dashboard['evolution']['skills_count']}")
        print(f"    criteria: {json.dumps(dashboard['scoring_criteria'], indent=2)}")

        # プロンプト用スキル
        prompt_text = rl.get_skills_for_prompt()
        if prompt_text:
            print(f"    prompt snippet ({len(prompt_text)} chars):")
            for line in prompt_text.split("\n")[:5]:
                print(f"      {line}")

        # MEMORY.md が存在するか
        memory_path = Path(tmpdir) / "MEMORY.md"
        if memory_path.exists():
            print(f"    MEMORY.md exists ({memory_path.stat().st_size} bytes)")

        print("  [PASS] orchestrator_full_cycle")


def test_auto_score():
    """自動スコアリング: _auto_score のヒューリスティック検証"""
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg_path = Path(tmpdir) / "config.json"
        cfg_path.write_text(json.dumps({
            "observation": {"enabled": True, "log_dir": str(Path(tmpdir) / "logs")},
            "reward_model": {"enabled": True},
            "curriculum": {"enabled": True},
            "evolution": {
                "enabled": True,
                "skill_extraction_min_samples": 2,
                "skill_success_threshold": 0.40,
                "memory_md_path": str(Path(tmpdir) / "MEMORY.md"),
            },
        }, indent=2), encoding="utf-8")

        rl = RLAnythingOrchestrator(config_path=cfg_path)

        # --- Case 1: success outcome, score=None → auto_score ≈ 0.75 base ---
        rl.begin_task("auto-1", "auto-score success test")
        rl.log_tool("read_file", {"path": "a.py"}, result="ok")
        rl.log_tool("create_file", {"path": "b.py"}, result="ok")
        rl.log_tool("run_test", {}, result="pass")
        result1 = rl.end_task("auto-1", outcome="success", score=None)
        s1 = result1["feedback"]["integration"]["score"]
        print(f"    auto success → feedback score = {s1:.4f}")
        # success base 0.75 with 3 actions (sweet spot) → should be > 0.5
        assert s1 > 0.3, f"success auto-score too low: {s1}"

        # --- Case 2: failure with errors → low score ---
        rl.begin_task("auto-2", "auto-score failure test")
        rl.log_tool("run_test", {}, result=None, error="SyntaxError")
        rl.log_tool("run_test", {}, result=None, error="ImportError")
        result2 = rl.end_task("auto-2", outcome="failure", score=None)
        s2 = result2["feedback"]["integration"]["score"]
        print(f"    auto failure → feedback score = {s2:.4f}")
        assert s2 < 0.5, f"failure auto-score too high: {s2}"

        # --- Case 3: score=None + intermediate scores ---
        rl.begin_task("auto-3", "auto-score intermediate test")
        rl.log_tool("read_file", {}, result="ok")
        rl.score_intermediate("auto-3", 0.9, "lint pass")
        rl.score_intermediate("auto-3", 0.8, "type check ok")
        result3 = rl.end_task("auto-3", outcome="success", score=None)
        s3 = result3["feedback"]["integration"]["score"]
        print(f"    auto intermediate → feedback score = {s3:.4f}")
        # With high intermediate scores, final should be elevated
        assert s3 > 0.4, f"intermediate blend auto-score too low: {s3}"

        # --- Case 4: too many actions penalty ---
        rl.begin_task("auto-4", "auto-score many actions test")
        for i in range(35):
            rl.log_tool(f"tool_{i}", {}, result="ok")
        result4 = rl.end_task("auto-4", outcome="partial", score=None)
        s4 = result4["feedback"]["integration"]["score"]
        print(f"    auto many actions → feedback score = {s4:.4f}")
        # partial base 0.50 - 0.10 (too many) = 0.40
        assert s4 < 0.65, f"many-action penalty not applied: {s4}"

        print("  [PASS] auto_score")


def main():
    print("=" * 60)
    print("RLAnything テストスイート")
    print("=" * 60)

    tests = [
        ("types", test_types),
        ("observation_hook", test_observation_hook),
        ("feedback_engine", test_feedback_engine),
        ("evolution_engine", test_evolution_engine),
        ("orchestrator (full cycle)", test_orchestrator_full_cycle),
        ("auto_score", test_auto_score),
    ]

    passed = 0
    failed = 0
    for name, func in tests:
        print(f"\n▶ {name}")
        try:
            func()
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\n{'=' * 60}")
    print(f"結果: {passed} passed, {failed} failed / {len(tests)} total")
    print("=" * 60)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
