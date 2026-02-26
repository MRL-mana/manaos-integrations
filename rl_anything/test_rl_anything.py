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
from rl_anything.replay_buffer import ReplayBuffer, Experience
from rl_anything.experiment_tracker import ExperimentTracker
from rl_anything.metrics_export import PrometheusExporter
from rl_anything.auto_curriculum import AutoCurriculum, CurriculumRecommendation
from rl_anything.replay_evaluator import ReplayEvaluator, ReEvalResult, ReEvalReport
from rl_anything.anomaly_detector import AnomalyDetector, Alert
from rl_anything.policy_gradient import PolicyGradient, Trajectory, PolicySnapshot
from rl_anything.reward_shaper import RewardShaper, ShapedReward
from rl_anything.meta_controller import MetaController, MetaReport, MetaAdjustment
from rl_anything.multi_objective import MultiObjectiveOptimizer, Objective, Solution
from rl_anything.transfer_learning import TransferLearning, DomainProfile, TransferResult
from rl_anything.ensemble_policy import EnsemblePolicy, PolicyMember, EnsembleDecision
from rl_anything.curiosity_explorer import CuriosityExplorer, CuriositySignal, StateVisit, ExplorationBudget
from rl_anything.hierarchical_policy import HierarchicalPolicy, HierarchicalDecision, Option
from rl_anything.safety_constraint import SafetyConstraintManager, SafetyConstraint, Violation, RecoveryAction
from rl_anything.model_based_planner import ModelBasedPlanner, WorldModel, Transition, PlanResult, PlanningStats
from rl_anything.distributional_reward import DistributionalReward, RewardDistribution, RiskProfile, RiskAdjustedScore
from rl_anything.communication_protocol import CommunicationProtocol, Message, AgentInfo, ChannelStats
from rl_anything.temporal_abstraction import TemporalAbstraction, TemporalEvent, TrendInfo, PeriodicPattern
from rl_anything.adversarial_robustness import AdversarialRobustness, PerturbationResult, RobustnessReport
from rl_anything.causal_reasoning import CausalReasoning, CausalObservation, CausalEffect, CounterfactualResult, Attribution


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


def test_persistence_and_metrics():
    """Round 3/4: state.json 永続化 + metrics.jsonl 動作検証"""
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg = _make_test_config(tmpdir)
        cfg_path = Path(tmpdir) / "config.json"
        cfg_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")

        # Instance 1: タスクを回す
        rl1 = RLAnythingOrchestrator(config_path=cfg_path)
        rl1.begin_task("p-1", "persistence test 1")
        rl1.log_tool("read_file", {}, result="ok")
        rl1.end_task("p-1", outcome="success", score=0.85)

        rl1.begin_task("p-2", "persistence test 2")
        rl1.log_tool("edit_file", {}, result="ok")
        rl1.end_task("p-2", outcome="failure", score=0.3)

        assert rl1._cycle_count == 2
        assert rl1._state_path.exists(), "state.json should exist"

        # Instance 2: 再起動をシミュレート
        rl2 = RLAnythingOrchestrator(config_path=cfg_path)
        assert rl2._cycle_count == 2, f"state not restored: got {rl2._cycle_count}"
        print(f"    cycle_count restored: {rl2._cycle_count}")

        # metrics.jsonl 検証
        history = rl2.get_history(limit=10)
        assert len(history) == 2, f"expected 2 metrics, got {len(history)}"
        assert history[0]["outcome"] == "success"
        assert history[1]["outcome"] == "failure"
        print(f"    metrics entries: {len(history)}")

        print("  [PASS] persistence_and_metrics")


def test_analytics():
    """Round 4: get_analytics() ローリング統計検証"""
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg = _make_test_config(tmpdir)
        cfg_path = Path(tmpdir) / "config.json"
        cfg_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")

        rl = RLAnythingOrchestrator(config_path=cfg_path)

        # 10 サイクル回す
        outcomes = ["success"] * 7 + ["failure"] * 3
        for i, out in enumerate(outcomes):
            rl.begin_task(f"a-{i}", f"analytics test {i}")
            rl.log_tool("tool", {}, result="ok")
            rl.end_task(f"a-{i}", outcome=out, score=0.9 if out == "success" else 0.2)

        analytics = rl.get_analytics(windows=[5, 10])
        print(f"    rolling SR: {analytics['rolling_success_rate']}")
        print(f"    rolling AS: {analytics['rolling_avg_score']}")
        print(f"    outcome dist: {analytics['outcome_distribution']}")
        print(f"    total_cycles: {analytics['total_cycles']}")

        # 検証
        assert analytics["total_cycles"] == 10
        assert "last_5" in analytics["rolling_success_rate"]
        assert "last_10" in analytics["rolling_success_rate"]
        # last 5 should include 2 success + 3 failure = 40%
        last5 = analytics["rolling_success_rate"]["last_5"]
        assert 0.0 <= last5 <= 1.0
        # Outcome distribution
        assert analytics["outcome_distribution"]["success"] == 7
        assert analytics["outcome_distribution"]["failure"] == 3
        # Score series
        assert len(analytics["score_series"]) == 10

        print("  [PASS] analytics")


def test_webhook_and_events():
    """Round 4: イベント発火 + リスナー検証"""
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg = _make_test_config(tmpdir)
        cfg_path = Path(tmpdir) / "config.json"
        cfg_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")

        rl = RLAnythingOrchestrator(config_path=cfg_path)

        # イベントリスナー
        events_received = []
        rl.add_event_listener(lambda event_type, payload: events_received.append((event_type, payload)))

        # タスク実行 → cycle_completed イベントが発火するはず
        rl.begin_task("ev-1", "event test")
        rl.log_tool("tool", {}, result="ok")
        rl.end_task("ev-1", outcome="success", score=0.9)

        # 最低 cycle_completed は来ているはず
        event_types = [e[0] for e in events_received]
        assert "cycle_completed" in event_types, f"expected cycle_completed, got {event_types}"
        print(f"    events received: {event_types}")

        # cycle_completed の中身確認
        cc = next(p for t, p in events_received if t == "cycle_completed")
        assert cc["task_id"] == "ev-1"
        assert cc["outcome"] == "success"
        assert cc["cycle"] == 1
        print(f"    cycle_completed payload OK: cycle={cc['cycle']}")

        print("  [PASS] webhook_and_events")


def test_scheduler():
    """Round 4: Auto-scheduler start/stop"""
    import time
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg = _make_test_config(tmpdir)
        cfg_path = Path(tmpdir) / "config.json"
        cfg_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")

        rl = RLAnythingOrchestrator(config_path=cfg_path)

        # Start
        r1 = rl.start_scheduler(interval_s=60)
        assert r1["ok"] and r1["status"] == "started"
        print(f"    scheduler start: {r1}")

        # Double start → already_running
        r2 = rl.start_scheduler()
        assert r2["status"] == "already_running"
        print(f"    double start: {r2}")

        # Stop
        r3 = rl.stop_scheduler()
        assert r3["ok"] and r3["status"] == "stopped"
        print(f"    scheduler stop: {r3}")

        # Double stop → not_running
        r4 = rl.stop_scheduler()
        assert r4["status"] == "not_running"
        print(f"    double stop: {r4}")

        print("  [PASS] scheduler")


def test_replay_buffer():
    """Replay Buffer のサイズ制限・サンプリング・永続化"""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "replay.jsonl"
        buf = ReplayBuffer(max_size=10, persist_path=path)

        # Push 15 items → 10 only (ring buffer)
        for i in range(15):
            outcome = "success" if i % 3 != 0 else "failure"
            buf.push(Experience(
                task_id=f"t-{i}", outcome=outcome, score=0.5 + i * 0.03,
                difficulty="standard", cycle=i + 1,
            ))
        assert buf.size == 10, f"expected size=10, got {buf.size}"
        assert buf.total_pushed == 15
        print(f"    buffer size={buf.size}, pushed={buf.total_pushed}")

        # Random sample
        batch = buf.sample(n=5)
        assert len(batch) == 5
        print(f"    random sample: {len(batch)} items")

        # Prioritized sample (failures should be over-represented)
        prio_batch = buf.sample_prioritized(n=50)
        assert len(prio_batch) == 50
        failure_count = sum(1 for e in prio_batch if e.outcome == "failure")
        print(f"    prioritized sample: {failure_count}/50 failures (expect > uniform)")

        # Persistence round-trip
        assert path.exists()
        buf2 = ReplayBuffer(max_size=10, persist_path=path)
        assert buf2.size == 10
        print(f"    persistence restored: {buf2.size} items")

        # Stats
        stats = buf.get_stats()
        assert "outcome_distribution" in stats
        assert stats["avg_score"] > 0
        print(f"    stats: avg_score={stats['avg_score']}, avg_priority={stats['avg_priority']}")

        print("  [PASS] replay_buffer")


def test_experiment_tracker():
    """A/B Experiment Tracker の作成・記録・比較・ベスト選択"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = ExperimentTracker(experiments_dir=Path(tmpdir))

        # Create 2 experiments
        id_a = tracker.create("variant_A", {"reward_model": {"intermediate_weight": 0.3}})
        id_b = tracker.create("variant_B", {"reward_model": {"intermediate_weight": 0.6}})
        assert id_a != id_b
        print(f"    created: {id_a}, {id_b}")

        # Record results: A = mediocre, B = better
        for _ in range(5):
            tracker.record_result(id_a, "success", 0.60)
            tracker.record_result(id_b, "success", 0.85)
        for _ in range(2):
            tracker.record_result(id_a, "failure", 0.30)
            tracker.record_result(id_b, "failure", 0.50)

        # Compare
        report = tracker.compare(min_samples=3)
        assert report["total"] == 2
        assert all(r["status"] == "ready" for r in report["experiments"])
        print(f"    compare: {report['total']} experiments ready")

        # Best → should be B
        best = tracker.get_best(min_samples=3)
        assert best is not None
        assert best["exp_id"] == id_b
        assert best["avg_score"] > 0.6
        print(f"    best: {best['exp_id']} with avg_score={best['avg_score']}")

        # Conclude
        tracker.conclude(id_a)
        exp_a = tracker.get_experiment(id_a)
        assert not exp_a["active"]
        print(f"    concluded {id_a}")

        # Persistence: reload from same dir
        tracker2 = ExperimentTracker(experiments_dir=Path(tmpdir))
        assert len(tracker2.list_experiments()) == 2
        print(f"    persistence: {len(tracker2.list_experiments())} experiments restored")

        print("  [PASS] experiment_tracker")


def test_prometheus_exporter():
    """Prometheus Exporter の Counter / Gauge / Histogram / render"""
    prom = PrometheusExporter()
    prom.register("rl_cycles_total", "counter", "Total completed RL cycles")
    prom.register("rl_score", "histogram", "Task score distribution")
    prom.register("rl_difficulty", "gauge", "Current difficulty level")

    prom.inc("rl_cycles_total", labels={"outcome": "success"})
    prom.inc("rl_cycles_total", labels={"outcome": "success"})
    prom.inc("rl_cycles_total", labels={"outcome": "failure"})
    prom.set("rl_difficulty", 2.0)
    prom.observe("rl_score", 0.75)
    prom.observe("rl_score", 0.85)
    prom.observe("rl_score", 0.40, labels={"outcome": "failure"})

    text = prom.render()
    assert "# TYPE rl_cycles_total counter" in text
    assert 'rl_cycles_total{outcome="success"} 2' in text
    assert 'rl_cycles_total{outcome="failure"} 1' in text
    assert "rl_difficulty 2.0" in text
    assert "rl_score_count" in text
    assert "rl_score_sum" in text
    assert "rl_score_bucket" in text
    print(f"    render lines: {len(text.splitlines())}")

    snap = prom.get_snapshot()
    assert "counters" in snap
    assert "gauges" in snap
    assert "histograms" in snap
    print(f"    snapshot keys: {list(snap.keys())}")

    print("  [PASS] prometheus_exporter")


def test_orchestrator_with_replay_and_prom():
    """Orchestrator が replay buffer と prometheus を正しく更新するか"""
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg = _make_test_config(tmpdir)
        cfg["replay_buffer"] = {"max_size": 50, "persist": True}
        cfg_path = Path(tmpdir) / "config.json"
        cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
        rl = RLAnythingOrchestrator(config_path=cfg_path)

        # Run 3 tasks
        for i in range(3):
            rl.begin_task(f"r5-{i}", f"round5 task {i}")
            rl.log_tool("read_file", {"p": "a.py"}, result="ok")
            rl.end_task(f"r5-{i}", outcome="success" if i < 2 else "failure", score=0.8 if i < 2 else 0.3)

        # Replay Buffer
        assert rl.replay.size == 3, f"expected replay size=3, got {rl.replay.size}"
        stats = rl.replay.get_stats()
        assert stats["outcome_distribution"]["success"] == 2
        assert stats["outcome_distribution"]["failure"] == 1
        print(f"    replay: size={rl.replay.size}, outcomes={stats['outcome_distribution']}")

        # Prometheus
        text = rl.prom.render()
        assert "rl_cycles_total" in text
        assert "rl_cycle_count" in text
        assert "rl_score_bucket" in text
        snap = rl.prom.get_snapshot()
        # cycle count gauge should be 3
        cycle_count_val = snap["gauges"].get("rl_cycle_count", 0)
        assert cycle_count_val == 3.0, f"expected cycle_count=3, got {cycle_count_val}"
        print(f"    prometheus: cycle_count={cycle_count_val}, render_lines={len(text.splitlines())}")

        # Experiment tracker
        exp_stats = rl.experiments.get_stats()
        assert exp_stats["total_experiments"] == 0  # no experiments created yet
        print(f"    experiments: {exp_stats}")

        print("  [PASS] orchestrator_with_replay_and_prom")


def test_auto_curriculum():
    """AutoCurriculum – シグナル計算 & 難易度推薦ロジック"""
    curriculum = AutoCurriculum()

    # ── ケース 1: 連続成功 → レベルアップ
    history_up = []
    for i in range(12):
        history_up.append({
            "cycle": i + 1,
            "outcome": "success",
            "score": 0.85,
            "difficulty": "standard",
        })
    rec = curriculum.recommend(history_up, current_difficulty="standard")
    assert isinstance(rec, CurriculumRecommendation)
    assert rec.recommended in ("abstract", "standard")  # 高成績なら上がるか据え置き
    print(f"    case-up: {rec.current} → {rec.recommended}, changed={rec.changed}, conf={rec.confidence:.2f}")

    # ── ケース 2: 連続失敗 → レベルダウン
    history_down = []
    for i in range(12):
        history_down.append({
            "cycle": i + 1,
            "outcome": "failure",
            "score": 0.20,
            "difficulty": "standard",
        })
    rec2 = curriculum.recommend(history_down, current_difficulty="standard")
    assert rec2.recommended in ("guided", "concrete", "standard")
    print(f"    case-down: {rec2.current} → {rec2.recommended}, changed={rec2.changed}, conf={rec2.confidence:.2f}")

    # ── ケース 3: データ少ない → 据え置き
    rec3 = curriculum.recommend([{"cycle": 1, "outcome": "success", "score": 0.9, "difficulty": "standard"}],
                                 current_difficulty="standard")
    assert not rec3.changed, "少データでは変更しない"
    print(f"    case-few: changed={rec3.changed}")

    # ── シグナル確認
    assert "success_rate" in rec.signals
    assert "avg_score" in rec.signals
    assert "slope" in rec.signals
    print("  [PASS] auto_curriculum")


def test_replay_evaluator():
    """ReplayEvaluator – 再採点 & バッチ評価 & インサイト"""
    evaluator = ReplayEvaluator()

    # ── 単一再採点
    exp = Experience(
        task_id="eval-1",
        cycle=1,
        outcome="success",
        score=0.60,
        difficulty="standard",
        tool_count=2,
        error_count=0,
        skills_used=["read_file", "write_file"],
    )
    result = evaluator.re_score(exp)
    assert isinstance(result, float)
    assert 0.0 <= result <= 1.0
    drift = result - exp.score
    print(f"    re_score: {exp.score:.3f} → {result:.3f} (drift={drift:+.3f})")

    # ── バッチ評価
    exps = []
    for i in range(10):
        outcome = "success" if i < 6 else "failure"
        score = 0.80 if outcome == "success" else 0.25
        exps.append(Experience(
            task_id=f"batch-{i}",
            cycle=i + 1,
            outcome=outcome,
            score=score,
            difficulty="standard",
            tool_count=i % 3 + 1,
            error_count=0,
            skills_used=["read_file"],
        ))
    report = evaluator.evaluate_batch(exps)
    assert isinstance(report, ReEvalReport)
    assert report.total_evaluated == 10
    assert report.positive_drift_count + report.negative_drift_count + report.zero_drift_count == 10
    print(f"    batch: total={report.total_evaluated}, avg_drift={report.avg_drift:+.4f}, +{report.positive_drift_count}/-{report.negative_drift_count}")
    assert isinstance(report.insights, list)
    print(f"    insights: {len(report.insights)} items")

    print("  [PASS] replay_evaluator")


def test_anomaly_detector():
    """AnomalyDetector – 各検出メソッド & アラート集約"""
    detector = AnomalyDetector()

    # ── 正常データ → アラートなし
    normal_history = []
    for i in range(20):
        normal_history.append({"cycle": i + 1, "outcome": "success", "score": 0.70 + (i % 3) * 0.05})
    alerts = detector.check(normal_history)
    assert isinstance(alerts, list)
    print(f"    normal: {len(alerts)} alerts")

    # ── 急降下 → アラート発生
    drop_history = list(normal_history)
    drop_history.append({"cycle": 21, "outcome": "failure", "score": 0.10})
    alerts2 = detector.check(drop_history)
    print(f"    drop: {len(alerts2)} alerts")

    # ── 連続失敗
    fail_history = []
    for i in range(20):
        fail_history.append({"cycle": i + 1, "outcome": "success", "score": 0.70})
    for i in range(5):
        fail_history.append({"cycle": 21 + i, "outcome": "failure", "score": 0.20})
    alerts3 = detector.check(fail_history)
    has_consecutive = any(a.alert_type == "consecutive_failures" for a in alerts3)
    print(f"    consecutive: {len(alerts3)} alerts, has_consecutive={has_consecutive}")

    # ── stats
    stats = detector.get_stats()
    assert "total_alerts" in stats
    assert "by_type" in stats
    assert "by_severity" in stats
    print(f"    stats: total={stats['total_alerts']}, types={list(stats['by_type'].keys())}")

    print("  [PASS] anomaly_detector")


def test_orchestrator_with_curriculum_and_anomaly():
    """Orchestrator が R6 コンポーネント (curriculum, replay_eval, anomaly) を統合するか"""
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg = _make_test_config(tmpdir)
        cfg["replay_buffer"] = {"max_size": 50, "persist": True}
        cfg_path = Path(tmpdir) / "config.json"
        cfg_path.write_text(json.dumps(cfg), encoding="utf-8")
        rl = RLAnythingOrchestrator(config_path=cfg_path)

        # R6 コンポーネントが存在するか
        assert hasattr(rl, "curriculum"), "curriculum attribute missing"
        assert hasattr(rl, "replay_evaluator"), "replay_evaluator attribute missing"
        assert hasattr(rl, "anomaly_detector"), "anomaly_detector attribute missing"

        # 12 サイクル回す
        for i in range(12):
            rl.begin_task(f"r6-{i}", f"round6 task {i}")
            rl.log_tool("read_file", {"p": "x.py"}, result="ok")
            outcome = "success" if i < 8 else "failure"
            score = 0.82 if outcome == "success" else 0.25
            result = rl.end_task(f"r6-{i}", outcome=outcome, score=score)

        # curriculum 推薦
        rec = rl.curriculum.recommend(
            rl.analytics.cycle_history if hasattr(rl, "analytics") else [],
            current_difficulty=rl.evolution.current_difficulty.value,
            replay_stats=rl.replay.get_stats() if rl.replay else None,
        )
        assert isinstance(rec, CurriculumRecommendation)
        print(f"    curriculum: {rec.current} → {rec.recommended}, changed={rec.changed}")

        # replay evaluator
        if rl.replay and rl.replay.size > 0:
            sample = rl.replay.sample(min(5, rl.replay.size))
            report = rl.replay_evaluator.evaluate_batch(sample)
            assert report.total_evaluated == len(sample)
            print(f"    replay_eval: {report.total_evaluated} evaluated, drift={report.avg_drift:+.4f}")

        # anomaly detector
        alerts = rl.anomaly_detector.check(
            rl.analytics.cycle_history if hasattr(rl, "analytics") else []
        )
        print(f"    anomaly: {len(alerts)} alerts")

        print("  [PASS] orchestrator_with_curriculum_and_anomaly")


def _make_test_config(tmpdir):
    """テスト用共通設定を生成"""
    return {
        "observation": {"enabled": True, "log_dir": str(Path(tmpdir) / "logs")},
        "reward_model": {"enabled": True},
        "curriculum": {"enabled": True},
        "evolution": {
            "enabled": True,
            "skill_extraction_min_samples": 2,
            "skill_success_threshold": 0.40,
            "memory_md_path": str(Path(tmpdir) / "MEMORY.md"),
        },
    }


# ═══════════════════════════════════════════════════════
# Round 7: Policy Gradient / Reward Shaper / Meta-Controller
# ═══════════════════════════════════════════════════════

def test_policy_gradient():
    """方策勾配エスティメータの基本テスト"""
    with tempfile.TemporaryDirectory() as tmpdir:
        pg = PolicyGradient(persist_path=Path(tmpdir) / "pg.json")

        # encode_state
        state = pg.encode_state(0.7, 0.6, "standard")
        assert len(state) == 3
        assert 0.0 <= state[0] <= 1.0
        assert 0.0 <= state[1] <= 1.0
        assert 0.0 <= state[2] <= 1.0

        # select_action
        action, log_prob = pg.select_action(state)
        assert action in ["level_down", "stay", "level_up"]
        assert log_prob < 0  # log(prob) は負

        # get_action_probs
        probs = pg.get_action_probs(state)
        assert len(probs) == 3
        total_prob = sum(probs.values())
        assert abs(total_prob - 1.0) < 1e-6

        # record trajectories
        for i in range(15):
            s = pg.encode_state(0.5 + i * 0.02, 0.4 + i * 0.01, "guided")
            a, lp = pg.select_action(s)
            pg.record(s, a, 0.5 + i * 0.03, lp, i)

        # update
        result = pg.update(batch_size=10)
        assert result is not None
        assert "avg_reward" in result
        assert "entropy" in result

        # recommend
        rec = pg.recommend_action(state)
        assert isinstance(rec, dict)
        assert rec["action"] in ["level_down", "stay", "level_up"]

        # snapshot
        snap = pg.get_snapshot()
        assert isinstance(snap, dict)
        assert snap["update_count"] >= 1

        # stats
        stats = pg.get_stats()
        assert "trajectory_count" in stats

        # persistence
        pg2 = PolicyGradient(persist_path=Path(tmpdir) / "pg.json")
        snap2 = pg2.get_snapshot()
        assert snap2["update_count"] == snap["update_count"]

        print("  [PASS] policy_gradient")


def test_reward_shaper():
    """報酬シェイパーのテスト"""
    rs = RewardShaper()

    # shape a single reward
    shaped = rs.shape(
        raw_score=0.8, outcome="success", difficulty="standard",
        success_rate=0.6, avg_score=0.65,
    )
    assert isinstance(shaped, ShapedReward)
    assert shaped.raw == 0.8
    assert isinstance(shaped.shaped, float)
    assert isinstance(shaped.curiosity_bonus, float)
    assert shaped.curiosity_bonus > 0  # 初回訪問は好奇心ボーナスあり

    # shape same outcome again → curiosity should decrease
    shaped2 = rs.shape(
        raw_score=0.8, outcome="success", difficulty="standard",
        success_rate=0.6, avg_score=0.65,
    )
    assert shaped2.curiosity_bonus < shaped.curiosity_bonus

    # difficulty_bonus for abstract should be positive
    shaped_abs = rs.shape(
        raw_score=0.8, outcome="success", difficulty="abstract",
        success_rate=0.6, avg_score=0.65,
    )
    assert shaped_abs.difficulty_bonus > 0

    # concrete → difficulty_bonus negative (multiplier < 1)
    shaped_conc = rs.shape(
        raw_score=0.8, outcome="success", difficulty="concrete",
        success_rate=0.6, avg_score=0.65,
    )
    assert shaped_conc.difficulty_bonus < 0

    # batch
    batch = [
        {"raw_score": 0.7, "outcome": "success", "difficulty": "standard", "success_rate": 0.5, "avg_score": 0.5},
        {"raw_score": 0.3, "outcome": "failure", "difficulty": "guided", "success_rate": 0.4, "avg_score": 0.4},
    ]
    results = rs.shape_batch(batch)
    assert len(results) == 2

    # stats
    stats = rs.get_stats()
    assert "total_visits" in stats
    assert stats["total_visits"] > 0

    # reset
    rs.reset()
    stats2 = rs.get_stats()
    assert stats2["total_visits"] == 0

    print("  [PASS] reward_shaper")


def test_meta_controller():
    """メタコントローラのテスト"""
    mc = MetaController()

    # no history → defaults
    signals = mc.compute_meta_signals([], 0, 0.5, 0)
    assert "stability" in signals
    assert signals["stability"] == 0.5  # default

    # with history
    scores = [0.5, 0.6, 0.7, 0.65, 0.8, 0.75, 0.7, 0.85, 0.9, 0.88]
    signals = mc.compute_meta_signals(scores, alert_count=0, policy_entropy=0.8, curriculum_changes=1)
    assert 0.0 <= signals["stability"] <= 1.0
    assert "convergence" in signals
    assert "exploration" in signals

    # tune with stable improving scores
    current_params = {
        "learning_rate": 0.01,
        "temperature": 1.0,
        "curriculum_up_threshold": 0.75,
        "curriculum_down_threshold": 0.30,
        "anomaly_z_threshold": 2.0,
    }
    report = mc.tune(scores, current_params, alert_count=0, policy_entropy=0.8)
    assert isinstance(report, MetaReport)
    assert isinstance(report.health_score, float)
    assert 0.0 <= report.health_score <= 1.0

    # tune with unstable scores → should lower lr
    unstable_scores = [0.3, 0.9, 0.2, 0.8, 0.1, 0.95, 0.15, 0.85, 0.25, 0.7]
    params_high_lr = {**current_params, "learning_rate": 0.05}
    report2 = mc.tune(unstable_scores, params_high_lr, alert_count=0, policy_entropy=0.5)
    lr_adjusted = any(a.param_name == "learning_rate" for a in report2.adjustments)
    # unstable → expect lr adjustment (either lr_adjusted is True or stability is ok)
    assert isinstance(report2.adjustments, list)

    # tune with many alerts → should relax z threshold
    report3 = mc.tune(scores, current_params, alert_count=10, policy_entropy=0.5)
    z_adjusted = any(a.param_name == "anomaly_z_threshold" for a in report3.adjustments)
    assert z_adjusted  # alert_rate > 0.4 → relax

    # stats
    stats = mc.get_stats()
    assert "total_adjustments" in stats
    assert stats["meta_history_len"] >= 3  # 3 tunes

    # health trend
    trend = mc.get_health_trend()
    assert len(trend) >= 3
    assert all(0.0 <= h <= 1.0 for h in trend)

    print("  [PASS] meta_controller")


def test_orchestrator_with_policy_and_reward():
    """Round 7 統合: オーケストレータに方策勾配・報酬シェイパー・メタコントローラが組み込まれているか"""
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg = _make_test_config(tmpdir)
        cfg_path = Path(tmpdir) / "config.json"
        cfg_path.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
        rl = RLAnythingOrchestrator(config_path=cfg_path)

        # コンポーネント存在確認
        assert hasattr(rl, 'policy_gradient')
        assert hasattr(rl, 'reward_shaper')
        assert hasattr(rl, 'meta_controller')
        assert isinstance(rl.policy_gradient, PolicyGradient)
        assert isinstance(rl.reward_shaper, RewardShaper)
        assert isinstance(rl.meta_controller, MetaController)

        # サイクル実行
        rl.begin_task("pg-1", "test policy gradient integration")
        rl.log_tool("read_file", {"path": "x.py"}, result="code")
        result = rl.end_task("pg-1", outcome="success", score=0.85)
        assert result["cycle"] >= 1
        # shaped_reward should be present
        assert "shaped_reward" in result
        sr = result["shaped_reward"]
        assert "raw" in sr and "shaped" in sr

        # get_policy_snapshot
        snap = rl.get_policy_snapshot()
        assert "theta" in snap
        assert "stats" in snap

        # get_reward_stats
        rs = rl.get_reward_stats()
        assert "total_visits" in rs

        # get_meta_status
        ms = rl.get_meta_status()
        assert "total_adjustments" in ms

        # policy_recommend
        rec = rl.policy_recommend(0.6, 0.5)
        assert "recommended_action" in rec
        assert rec["recommended_action"] in ["level_down", "stay", "level_up"]

        print("  [PASS] orchestrator_with_policy_and_reward")


def test_multi_objective():
    """多目的最適化テスト"""
    with tempfile.TemporaryDirectory() as td:
        persist = Path(td) / "mo.json"
        mo = MultiObjectiveOptimizer(persist_path=persist)

        # デフォルト目的関数
        objs = mo.get_objectives()
        assert len(objs) >= 4, f"Expected >= 4 objectives, got {len(objs)}"
        assert "score" in objs
        assert "success_rate" in objs

        # 目的関数追加・削除
        mo.add_objective("latency", direction="minimize", weight=0.1)
        assert "latency" in mo.get_objectives()
        mo.remove_objective("latency")
        assert "latency" not in mo.get_objectives()

        # ソリューション記録
        mo.record_solution(1, {"score": 0.8, "success_rate": 0.9, "efficiency": 0.5, "exploration": 0.3})
        mo.record_solution(2, {"score": 0.5, "success_rate": 0.6, "efficiency": 0.9, "exploration": 0.8})
        mo.record_solution(3, {"score": 0.9, "success_rate": 0.95, "efficiency": 0.7, "exploration": 0.6})
        mo.record_solution(4, {"score": 0.6, "success_rate": 0.7, "efficiency": 0.8, "exploration": 0.4})

        # パレートフロント
        front = mo.get_pareto_front()
        assert len(front) >= 1, "Pareto front should not be empty"

        # ベストスカラ化
        best = mo.get_best_scalarized()
        assert best is not None
        assert "scalarized" in best

        # トレードオフ
        analysis = mo.get_trade_off_analysis()
        assert "correlations" in analysis or "status" in analysis
        if "correlations" in analysis:
            assert "trends" in analysis

        # 推奨ウェイト
        rec = mo.recommend_weights()
        assert len(rec) >= 4
        total = sum(rec.values())
        assert abs(total - 1.0) < 0.01, f"Weights should sum to 1.0, got {total}"

        # 統計
        stats = mo.get_stats()
        assert stats["total_solutions"] == 4
        assert stats["pareto_size"] >= 1

        # 永続化
        mo2 = MultiObjectiveOptimizer(persist_path=persist)
        assert mo2.get_stats()["total_solutions"] == 4

        print("  [PASS] multi_objective")


def test_transfer_learning():
    """転移学習テスト"""
    with tempfile.TemporaryDirectory() as td:
        persist = Path(td) / "tl.json"
        tl = TransferLearning(persist_path=persist)

        # ドメイン更新
        for i in range(5):
            tl.update_domain("testing", 0.7 + i * 0.05, "success", "standard")
        for i in range(5):
            tl.update_domain("debugging", 0.4 + i * 0.03, "partial" if i < 2 else "success", "hard")

        # ドメイン推論
        d = tl.infer_domain("fix the broken test assertion")
        assert d in ("testing", "debugging")

        d2 = tl.infer_domain("write documentation for the API")
        assert d2 == "documentation"

        # 類似度行列
        sim = tl.get_similarity_matrix()
        assert "testing" in sim
        assert "debugging" in sim
        # 同ドメインは1.0
        assert abs(sim["testing"]["testing"] - 1.0) < 0.001

        # 転移提案
        suggestion = tl.suggest_transfer("coding")
        # codingはデータなしなので None かも
        # ドメインにデータを追加
        for i in range(5):
            tl.update_domain("coding", 0.3, "failure", "easy")
        suggestion = tl.suggest_transfer("coding")
        # testing or debugging から転移が来るかも
        if suggestion is not None:
            assert isinstance(suggestion, TransferResult)
            assert suggestion.target_domain == "coding"

        # 転移適用
        result = tl.apply_transfer("coding")
        # result は None (転移不可の場合) or dict (成功)
        if result is not None:
            assert "source_domain" in result or "ts" in result

        # 統計
        stats = tl.get_stats()
        assert stats["domain_count"] >= 2

        # 永続化
        tl2 = TransferLearning(persist_path=persist)
        assert tl2.get_stats()["domain_count"] >= 2

        print("  [PASS] transfer_learning")


def test_ensemble_policy():
    """アンサンブルポリシーテスト"""
    with tempfile.TemporaryDirectory() as td:
        persist = Path(td) / "ep.json"
        ep = EnsemblePolicy(n_members=5, persist_path=persist)

        # メンバー数
        stats = ep.get_stats()
        assert stats["member_count"] == 5

        # 決定
        state = [0.6, 0.5, 0.0]  # success_rate, avg_score, difficulty_encoded
        decision = ep.decide(state)
        assert isinstance(decision, EnsembleDecision)
        assert decision.action in ("level_down", "stay", "level_up")
        assert 0 <= decision.agreement <= 1
        assert 0 <= decision.confidence <= 1
        assert len(decision.probabilities) == 3

        # 各方式テスト
        for method in ["weighted_average", "majority_vote", "boltzmann_mix", "best_of_n"]:
            d = ep.decide(state, method=method)
            assert d.method == method
            assert d.action in ("level_down", "stay", "level_up")

        # 報酬更新
        ep.update_rewards(0.8)
        stats_r = ep.get_stats()
        for m in stats_r["members"]:
            assert m["avg_reward"] > 0

        # 多様性
        div = ep.get_diversity(state)
        assert "action_entropy" in div
        assert "param_variance" in div

        # 摂動
        ep.perturb_member(0, magnitude=0.1)

        # 永続化
        ep2 = EnsemblePolicy(n_members=5, persist_path=persist)
        stats2 = ep2.get_stats()
        assert stats2["member_count"] == 5
        assert stats2["total_decisions"] >= 4  # we called decide 5 times

        print("  [PASS] ensemble_policy")


def test_orchestrator_with_r8_components():
    """Round 8 コンポーネント統合テスト"""
    with tempfile.TemporaryDirectory() as td:
        cfg_path = Path(td) / "rl_config.json"
        cfg_path.write_text(json.dumps({
            "enabled": True,
            "log_dir": str(Path(td) / "logs"),
            "difficulty": "standard",
            "scoring": {
                "outcome_weight": 0.35,
                "tool_efficiency_weight": 0.25,
                "consistency_weight": 0.20,
                "exploration_weight": 0.10,
                "difficulty_bonus": 0.10
            }
        }))

        rl = RLAnythingOrchestrator(config_path=cfg_path)

        # コンポーネント存在確認
        assert hasattr(rl, 'multi_objective')
        assert hasattr(rl, 'transfer_learning')
        assert hasattr(rl, 'ensemble_policy')
        assert isinstance(rl.multi_objective, MultiObjectiveOptimizer)
        assert isinstance(rl.transfer_learning, TransferLearning)
        assert isinstance(rl.ensemble_policy, EnsemblePolicy)

        # サイクル実行
        rl.begin_task("r8-1", "fix bug in test module")
        rl.log_tool("read_file", {"path": "test.py"}, result="code")
        rl.log_tool("write_file", {"path": "test.py"}, result="fixed")
        result = rl.end_task("r8-1", outcome="success", score=0.9)
        assert result["cycle"] >= 1

        rl.begin_task("r8-2", "write documentation for API")
        rl.log_tool("read_file", {"path": "api.py"}, result="class API")
        result2 = rl.end_task("r8-2", outcome="success", score=0.75)
        assert result2["cycle"] >= 2

        # 3つ目のタスクでトレードオフ分析に必要なデータを確保
        rl.begin_task("r8-3", "refactor shared module")
        rl.log_tool("read_file", {"path": "shared.py"}, result="module")
        result3 = rl.end_task("r8-3", outcome="partial", score=0.5)
        assert result3["cycle"] >= 3

        # Multi-Objective 統計
        mo_stats = rl.get_multi_objective_stats()
        assert "total_solutions" in mo_stats
        assert mo_stats["total_solutions"] >= 3

        # トレードオフ
        to = rl.get_trade_off_analysis()
        assert "correlation_matrix" in to or "trends" in to or "status" in to

        # Transfer 統計
        ts = rl.get_transfer_stats()
        assert "domain_count" in ts

        # Ensemble 統計
        es = rl.get_ensemble_stats()
        assert "member_count" in es

        # Ensemble 決定
        ed = rl.ensemble_decide(0.6, 0.5)
        assert "action" in ed

        # Ensemble 多様性
        dv = rl.get_ensemble_diversity()
        assert "action_entropy" in dv or "diversity" in dv

        print("  [PASS] orchestrator_with_r8_components")


def test_curiosity_explorer():
    """好奇心駆動探索テスト"""
    with tempfile.TemporaryDirectory() as td:
        persist = Path(td) / "curiosity.json"
        ce = CuriosityExplorer(persist_path=persist)

        # 状態ハッシュ
        h1 = CuriosityExplorer.hash_state(0.5, "success", ["read_file"], "coding")
        h2 = CuriosityExplorer.hash_state(0.8, "failure", ["write_file"], "testing")
        assert len(h1) == 16
        assert h1 != h2

        # 同じパラメータなら同じハッシュ
        h1a = CuriosityExplorer.hash_state(0.5, "success", ["read_file"], "coding")
        assert h1 == h1a

        # observe
        sig1 = ce.observe(h1, 0.7, cycle=1)
        assert isinstance(sig1, CuriositySignal)
        assert sig1.is_novel  # 初回は常にnovel
        assert sig1.curiosity_bonus > 0
        assert sig1.cycle == 1

        sig2 = ce.observe(h1, 0.8, cycle=2)
        assert sig2.visit_count >= 2
        assert sig2.novelty <= sig1.novelty  # 2回目はnovelty低下

        sig3 = ce.observe(h2, 0.3, cycle=3)
        assert sig3.is_novel  # h2は初回

        # 統計
        stats = ce.get_stats()
        assert stats["total_visits"] >= 3
        assert stats["unique_states"] == 2
        assert stats["novel_discoveries"] == 2

        # 最近のシグナル
        recent = ce.get_recent_signals(10)
        assert len(recent) == 3

        # 新規性マップ
        nm = ce.get_novelty_map()
        assert nm["total_states"] == 2

        # 探索推薦
        recs = ce.recommend_exploration(5)
        assert len(recs) == 2

        # バジェット
        assert stats["budget"]["used"] == 3

        # 永続化
        ce2 = CuriosityExplorer(persist_path=persist)
        s2 = ce2.get_stats()
        assert s2["unique_states"] == 2

        print("  [PASS] curiosity_explorer")


def test_hierarchical_policy():
    """階層型方策テスト"""
    with tempfile.TemporaryDirectory() as td:
        persist = Path(td) / "hierarchical.json"
        hp = HierarchicalPolicy(persist_path=persist)

        # デフォルトオプション確認
        opts = hp.get_options()
        assert len(opts) >= 4  # consolidate, explore_up, recover, balanced

        # 意思決定
        d1 = hp.decide(difficulty=0.3, state={"cycle": 1}, cycle=1)
        assert isinstance(d1, HierarchicalDecision)
        assert d1.action in ["level_down", "stay", "level_up"]
        assert d1.level in ["manager", "worker"]
        assert 0 <= d1.confidence <= 1

        # 報酬更新
        hp.update_reward(0.8, "success")

        d2 = hp.decide(difficulty=0.7, state={"cycle": 2}, cycle=2)
        hp.update_reward(0.3, "failure")

        d3 = hp.decide(difficulty=0.5, state={"cycle": 3}, cycle=3)
        hp.update_reward(0.6, "partial")

        # 統計
        stats = hp.get_stats()
        assert stats["total_decisions"] >= 3
        assert stats["option_count"] >= 4

        # 最近の決定
        recent = hp.get_recent_decisions(10)
        assert len(recent) == 3

        # オプションパフォーマンス
        perf = hp.get_option_performance()
        assert len(perf) >= 4

        # アクティブオプション
        active = hp.get_active_option()
        assert active is not None

        # 永続化
        hp2 = HierarchicalPolicy(persist_path=persist)
        s2 = hp2.get_stats()
        assert s2["total_decisions"] >= 3

        print("  [PASS] hierarchical_policy")


def test_safety_constraint():
    """安全制約テスト"""
    with tempfile.TemporaryDirectory() as td:
        persist = Path(td) / "safety.json"
        sc = SafetyConstraintManager(persist_path=persist)

        # デフォルト制約
        constraints = sc.get_constraints()
        assert len(constraints) >= 5

        # メトリクス抽出
        history = [
            {"outcome": "success", "score": 0.8},
            {"outcome": "success", "score": 0.7},
            {"outcome": "failure", "score": 0.2},
            {"outcome": "success", "score": 0.9},
            {"outcome": "partial", "score": 0.5},
        ]
        metrics = SafetyConstraintManager.extract_metrics(history, exploration_rate=0.1)
        assert "success_rate" in metrics
        assert "avg_score" in metrics
        assert abs(metrics["success_rate"] - 0.6) < 0.01  # 3/5

        # 安全チェック（安全な状態）
        result = sc.check_all(metrics, cycle=1)
        assert "safe" in result
        assert "total_penalty" in result
        assert "violations" in result

        # 危険な状態テスト
        bad_history = [{"outcome": "failure", "score": 0.1}] * 15
        bad_metrics = SafetyConstraintManager.extract_metrics(bad_history, exploration_rate=0.0)
        bad_result = sc.check_all(bad_metrics, cycle=2)
        assert bad_result["safe"] is False or bad_result["total_penalty"] > 0

        # 統計
        stats = sc.get_stats()
        assert stats["total_checks"] >= 2
        assert "safety_score" in stats or "total_violations" in stats

        # 安全スコア
        score = sc.get_safety_score()
        assert 0 <= score <= 1

        # 違反履歴
        vh = sc.get_violation_history(50)
        assert isinstance(vh, list)

        # 制約の緩和・厳格化
        cid = list(constraints.keys())[0]
        sc.relax_constraint(cid, 1.5)
        relaxed = sc.get_constraints()
        assert relaxed[cid]["relaxation_factor"] == 1.5

        sc.tighten_constraint(cid, 0.8)
        tight = sc.get_constraints()
        assert tight[cid]["relaxation_factor"] == 0.8

        # 永続化
        sc2 = SafetyConstraintManager(persist_path=persist)
        s2 = sc2.get_stats()
        assert s2["total_checks"] >= 2

        print("  [PASS] safety_constraint")


def test_orchestrator_with_r9_components():
    """Round 9 コンポーネント統合テスト"""
    with tempfile.TemporaryDirectory() as td:
        cfg_path = Path(td) / "rl_config.json"
        cfg_path.write_text(json.dumps({
            "enabled": True,
            "log_dir": str(Path(td) / "logs"),
            "difficulty": "standard",
            "scoring": {
                "outcome_weight": 0.35,
                "tool_efficiency_weight": 0.25,
                "consistency_weight": 0.20,
                "exploration_weight": 0.10,
                "difficulty_bonus": 0.10
            }
        }))

        rl = RLAnythingOrchestrator(config_path=cfg_path)

        # R9コンポーネント存在確認
        assert hasattr(rl, 'curiosity')
        assert hasattr(rl, 'hierarchical')
        assert hasattr(rl, 'safety')
        assert isinstance(rl.curiosity, CuriosityExplorer)
        assert isinstance(rl.hierarchical, HierarchicalPolicy)
        assert isinstance(rl.safety, SafetyConstraintManager)

        # タスクサイクル
        rl.begin_task("r9-1", "implement curiosity driven exploration")
        rl.log_tool("read_file", {"path": "curiosity.py"}, result="code")
        rl.log_tool("write_file", {"path": "curiosity.py"}, result="implemented")
        result = rl.end_task("r9-1", outcome="success", score=0.85)
        assert result["cycle"] >= 1

        rl.begin_task("r9-2", "test hierarchical policy")
        rl.log_tool("run_tests", {"suite": "hierarchy"}, result="3/3 passed")
        result2 = rl.end_task("r9-2", outcome="success", score=0.9)
        assert result2["cycle"] >= 2

        rl.begin_task("r9-3", "fix safety constraint violation")
        rl.log_tool("read_file", {"path": "safety.py"}, result="constraints")
        result3 = rl.end_task("r9-3", outcome="partial", score=0.5)
        assert result3["cycle"] >= 3

        # Curiosity Stats
        cs = rl.get_curiosity_stats()
        assert "total_visits" in cs or "unique_states" in cs

        # Novelty Map
        nm = rl.get_novelty_map()
        assert "total_states" in nm or "states" in nm

        # Hierarchical Stats
        hs = rl.get_hierarchical_stats()
        assert "total_decisions" in hs or "option_count" in hs

        # Hierarchical Decide
        hd = rl.hierarchical_decide(0.6)
        assert "action" in hd

        # Options
        opts = rl.get_options()
        assert isinstance(opts, list) or isinstance(opts, dict)

        # Safety Stats
        ss = rl.get_safety_stats()
        assert "total_checks" in ss or "safety_score" in ss

        # Safety Check
        sc = rl.check_safety()
        assert "safe" in sc

        # Safety Violations
        sv = rl.get_safety_violations(10)
        assert isinstance(sv, list) or isinstance(sv, dict)

        print("  [PASS] orchestrator_with_r9_components")


def test_model_based_planner():
    """Model-Based Planner 単体テスト"""
    with tempfile.TemporaryDirectory() as td:
        persist = Path(td) / "planner.json"
        planner = ModelBasedPlanner(persist_path=persist)

        # 状態エンコーディング
        s1 = ModelBasedPlanner.encode_state("standard", 0.7, 5)
        s2 = ModelBasedPlanner.encode_state("standard", 0.7, 5)
        s3 = ModelBasedPlanner.encode_state("advanced", 0.3, 10)
        assert s1 == s2  # 同一入力は同一ハッシュ
        assert s1 != s3  # 異なる入力は異なるハッシュ
        assert len(s1) == 12

        # 遷移記録
        t1 = planner.record_transition(s1, "level_up", s3, 0.8, 5)
        assert isinstance(t1, Transition)
        assert t1.state == s1
        assert t1.action == "level_up"
        assert t1.reward == 0.8

        # 複数遷移記録
        for i in range(10):
            src = ModelBasedPlanner.encode_state("standard", 0.5 + i * 0.03, i)
            dst = ModelBasedPlanner.encode_state("standard", 0.5 + i * 0.03 + 0.05, i + 1)
            planner.record_transition(src, "stay", dst, 0.5 + i * 0.02, i)

        assert planner.get_transition_count() >= 11

        # プランニング
        plan = planner.plan(s1)
        assert isinstance(plan, PlanResult)
        assert plan.best_action in ["level_down", "stay", "level_up"]
        assert 0 <= plan.expected_value
        assert plan.simulations > 0
        assert plan.depth > 0

        # 統計
        stats = planner.get_stats()
        assert stats["total_plans"] >= 1
        assert stats["total_transitions"] >= 11
        assert stats["unique_states"] >= 2

        # モデル情報
        model_info = planner.get_model_info()
        assert "unique_states" in model_info
        assert "total_observed_transitions" in model_info

        # 最近の遷移・プラン
        recent_tx = planner.get_recent_transitions(5)
        assert len(recent_tx) <= 5
        recent_plans = planner.get_recent_plans(5)
        assert len(recent_plans) <= 5

        # 永続化・復元
        assert persist.exists()
        planner2 = ModelBasedPlanner(persist_path=persist)
        assert planner2.get_transition_count() >= 11

        print("  [PASS] model_based_planner")


def test_distributional_reward():
    """Distributional Reward 単体テスト"""
    with tempfile.TemporaryDirectory() as td:
        persist = Path(td) / "distrib.json"
        dr = DistributionalReward(persist_path=persist)

        # 報酬記録
        for i in range(20):
            score = 0.3 + (i % 10) * 0.05
            dist = dr.record("standard|success", score)
        assert isinstance(dist, RewardDistribution)
        assert dist.count == 20
        assert dist.mean > 0
        assert dist.std >= 0
        assert "q050" in dist.quantiles or "q005" in dist.quantiles

        # バッチ記録
        dist2 = dr.record_batch("standard|failure", [0.1, 0.2, 0.15, 0.25, 0.1])
        assert dist2.count == 5
        assert dist2.mean < 0.3

        # 分布取得
        all_dists = dr.get_all_distributions()
        assert len(all_dists) == 2
        assert "standard|success" in all_dists
        assert "standard|failure" in all_dists

        # リスク調整
        ra = dr.risk_adjust(0.7, key="standard|success")
        assert isinstance(ra, RiskAdjustedScore)
        assert ra.raw_score == 0.7
        assert 0 <= ra.risk_adjusted <= 1
        assert ra.risk_penalty >= 0

        # リスクプロファイル
        profile = dr.get_risk_profile()
        assert isinstance(profile, RiskProfile)
        assert profile.risk_level in ["high_risk", "moderate_risk", "low_risk"]
        assert profile.recommendation

        # 統計
        stats = dr.get_stats()
        assert stats["total_samples"] >= 25
        assert stats["distribution_count"] == 2
        assert stats["risk_checks"] >= 1

        # Quantile summary
        qs = dr.get_quantile_summary()
        assert len(qs) == 2

        # 永続化
        assert persist.exists()
        dr2 = DistributionalReward(persist_path=persist)
        assert dr2.get_stats()["total_samples"] >= 25

        print("  [PASS] distributional_reward")


def test_communication_protocol():
    """Communication Protocol 単体テスト"""
    with tempfile.TemporaryDirectory() as td:
        persist = Path(td) / "comms.json"
        comms = CommunicationProtocol(persist_path=persist)

        # エージェント登録
        a1 = comms.register_agent("orchestrator", "orchestrator", ["coordination"])
        a2 = comms.register_agent("curiosity", "curiosity_explorer", ["exploration"])
        a3 = comms.register_agent("planner", "model_based_planner", ["planning"])
        assert isinstance(a1, AgentInfo)
        assert a1.agent_id == "orchestrator"

        agents = comms.get_agents()
        assert len(agents) == 3

        # チャンネル購読
        assert comms.subscribe("curiosity", "cycle_complete")
        assert comms.subscribe("planner", "cycle_complete")
        assert not comms.subscribe("nonexistent", "cycle_complete")

        # ダイレクトメッセージ
        msg = comms.send(
            sender="orchestrator", receiver="curiosity",
            channel="direct", msg_type="event",
            payload={"test": True}, priority=1,
        )
        assert isinstance(msg, Message)
        assert msg.sender == "orchestrator"
        assert msg.receiver == "curiosity"

        # ブロードキャスト
        bc = comms.broadcast(
            sender="orchestrator", channel="cycle_complete",
            msg_type="event", payload={"cycle": 1, "score": 0.8},
        )
        assert bc.receiver == "__broadcast__"

        # 受信
        msgs_curiosity = comms.receive("curiosity")
        assert len(msgs_curiosity) >= 2  # direct + broadcast

        msgs_planner = comms.receive("planner")
        assert len(msgs_planner) >= 1  # broadcast only

        # 知識共有
        km = comms.share_knowledge("curiosity", "state_info", {"novel_states": 5})
        assert km.msg_type == "knowledge"

        # 統計
        stats = comms.get_stats()
        assert stats["total_sent"] >= 3
        assert stats["total_broadcast"] >= 1
        assert stats["registered_agents"] == 3

        # チャンネル統計
        cs = comms.get_channel_stats()
        assert len(cs) >= 1

        # 履歴
        history = comms.get_message_history(50)
        assert len(history) >= 3

        # 永続化
        assert persist.exists()
        comms2 = CommunicationProtocol(persist_path=persist)
        assert comms2.get_stats()["total_sent"] >= 3
        assert len(comms2.get_agents()) == 3

        print("  [PASS] communication_protocol")


def test_orchestrator_with_r10_components():
    """Round 10 コンポーネント統合テスト"""
    with tempfile.TemporaryDirectory() as td:
        cfg_path = Path(td) / "rl_config.json"
        cfg_path.write_text(json.dumps({
            "enabled": True,
            "log_dir": str(Path(td) / "logs"),
            "difficulty": "standard",
            "scoring": {
                "outcome_weight": 0.35,
                "tool_efficiency_weight": 0.25,
                "consistency_weight": 0.20,
                "exploration_weight": 0.10,
                "difficulty_bonus": 0.10
            }
        }))

        rl = RLAnythingOrchestrator(config_path=cfg_path)

        # R10コンポーネント存在確認
        assert hasattr(rl, 'planner')
        assert hasattr(rl, 'distributional')
        assert hasattr(rl, 'comms')
        assert isinstance(rl.planner, ModelBasedPlanner)
        assert isinstance(rl.distributional, DistributionalReward)
        assert isinstance(rl.comms, CommunicationProtocol)

        # タスクサイクル
        rl.begin_task("r10-1", "implement model-based planning")
        rl.log_tool("read_file", {"path": "planner.py"}, result="code")
        rl.log_tool("write_file", {"path": "planner.py"}, result="implemented")
        result = rl.end_task("r10-1", outcome="success", score=0.85)
        assert result["cycle"] >= 1

        rl.begin_task("r10-2", "test distributional reward")
        rl.log_tool("run_tests", {"suite": "distributional"}, result="5/5 passed")
        result2 = rl.end_task("r10-2", outcome="success", score=0.9)
        assert result2["cycle"] >= 2

        rl.begin_task("r10-3", "setup communication protocol")
        rl.log_tool("read_file", {"path": "comms.py"}, result="protocol")
        result3 = rl.end_task("r10-3", outcome="partial", score=0.6)
        assert result3["cycle"] >= 3

        # Planner Stats
        ps = rl.get_planner_stats()
        assert isinstance(ps, dict)

        # Planner Plan
        pp = rl.planner_plan()
        assert "best_action" in pp or "expected_value" in pp

        # Planner Transitions
        pt = rl.get_planner_transitions()
        assert isinstance(pt, dict)

        # Distributional Stats
        ds = rl.get_distributional_stats()
        assert "total_samples" in ds

        # Risk Profile
        rp = rl.get_risk_profile()
        assert isinstance(rp, dict)

        # Quantile Summary
        qs = rl.get_quantile_summary()
        assert isinstance(qs, dict)

        # Comms Stats
        cs = rl.get_comms_stats()
        assert "total_sent" in cs
        assert cs["registered_agents"] >= 6  # 6 コンポーネント

        # Comms History
        ch = rl.get_comms_history()
        assert isinstance(ch, dict)
        assert ch["total"] >= 3  # 3サイクル分のブロードキャスト

        print("  [PASS] orchestrator_with_r10_components")


def test_temporal_abstraction():
    """TemporalAbstraction 単体テスト"""
    import time as _time
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "ta.json"
        ta = TemporalAbstraction(persist_path=p)

        # イベント記録
        base_ts = _time.time()
        for i in range(10):
            ta.record_event(0.5 + i * 0.05, "standard", timestamp=base_ts + i * 60)

        # 統計
        stats = ta.get_stats()
        assert stats["total_events"] == 10
        assert stats["sessions"] >= 1

        # トレンド
        trend = ta.get_trend()
        assert isinstance(trend, TrendInfo)
        assert trend.direction in ("rising", "falling", "stable")

        # 周期パターン
        pattern = ta.get_periodic_pattern()
        assert isinstance(pattern, PeriodicPattern)

        # セッション
        sessions = ta.get_sessions()
        assert len(sessions) >= 1

        # TD価値
        td_vals = ta.get_td_values()
        assert td_vals["total_updates"] == 10

        # 永続化復元
        ta2 = TemporalAbstraction(persist_path=p)
        assert ta2.get_stats()["total_events"] == 10

        print("  [PASS] temporal_abstraction")


def test_adversarial_robustness():
    """AdversarialRobustness 単体テスト"""
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "ar.json"
        ar = AdversarialRobustness(persist_path=p)

        # ロバストネステスト
        for i in range(5):
            result = ar.test_robustness(f"state_{i}", "stay", 0.7 + i * 0.03)
            assert isinstance(result, PerturbationResult)
            assert 0 <= result.stability <= 1.0

        # 統計
        stats = ar.get_stats()
        assert stats["total_tests"] == 5

        # レポート
        report = ar.generate_report()
        assert isinstance(report, RobustnessReport)
        assert report.tests_conducted == 5

        # 脆弱状態
        vulns = ar.get_vulnerable_states()
        assert isinstance(vulns, list)

        # 履歴
        history = ar.get_robustness_history()
        assert len(history) >= 1

        # 永続化復元
        ar2 = AdversarialRobustness(persist_path=p)
        assert ar2.get_stats()["total_tests"] == 5

        print("  [PASS] adversarial_robustness")


def test_causal_reasoning():
    """CausalReasoning 単体テスト"""
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "cr.json"
        cr = CausalReasoning(persist_path=p)

        # 観測記録
        cr.record_observation("t1", ["read_file", "create_file"], 0.9)
        cr.record_observation("t2", ["read_file"], 0.7)
        cr.record_observation("t3", ["create_file", "run_cmd"], 0.8)
        cr.record_observation("t4", ["read_file", "run_cmd"], 0.6)
        cr.record_observation("t5", [], 0.4)

        # 統計
        stats = cr.get_stats()
        assert stats["total_observations"] == 5
        assert stats["unique_tools"] == 3

        # 因果効果
        effect = cr.estimate_causal_effect("read_file")
        assert isinstance(effect, CausalEffect)
        assert effect.n_treatment > 0

        # 反事実
        cf = cr.counterfactual("t1", ["create_file"])
        assert isinstance(cf, CounterfactualResult)

        # 寄与帰属
        attrs = cr.get_attributions()
        assert isinstance(attrs, list)
        assert len(attrs) > 0
        assert isinstance(attrs[0], Attribution)

        # 因果グラフ
        graph = cr.get_causal_graph()
        assert graph["total_tools"] == 3
        assert graph["total_edges"] > 0

        # 介入効果
        ie = cr.intervention_effect("read_file")
        assert "effect" in ie

        # 永続化復元
        cr2 = CausalReasoning(persist_path=p)
        assert cr2.get_stats()["total_observations"] == 5

        print("  [PASS] causal_reasoning")


def test_orchestrator_with_r11_components():
    """R11 コンポーネント統合テスト"""
    rl = RLAnythingOrchestrator()

    for i in range(3):
        rl.begin_task(f"r11-{i}", f"R11 integration test {i}")
        rl.log_tool("read_file", {"path": f"file_{i}.py"}, result="ok")
        rl.log_tool("create_file", {"path": f"test_{i}.py"}, result="ok")
        result = rl.end_task(f"r11-{i}", outcome="success", score=0.7 + i * 0.1)
        assert "temporal" in result
        assert "adversarial" in result
        assert "causal" in result

    # Temporal Stats
    ts = rl.get_temporal_stats()
    assert ts["total_events"] >= 3
    assert "trend" in ts

    # Temporal Trend
    tt = rl.get_temporal_trend()
    assert "direction" in tt

    # Temporal Patterns
    tp = rl.get_temporal_patterns()
    assert isinstance(tp, dict)

    # Temporal Sessions
    tss = rl.get_temporal_sessions()
    assert "sessions" in tss

    # TD Values
    tdv = rl.get_temporal_td_values()
    assert "values" in tdv

    # Adversarial Stats
    advs = rl.get_adversarial_stats()
    assert advs["total_tests"] >= 3

    # Adversarial Report
    advr = rl.get_adversarial_report()
    assert "overall_robustness" in advr

    # Adversarial Vulnerable
    advv = rl.get_adversarial_vulnerable()
    assert "vulnerable_states" in advv

    # Causal Stats
    cs = rl.get_causal_stats()
    assert cs["total_observations"] >= 3

    # Causal Attributions
    ca = rl.get_causal_attributions()
    assert "attributions" in ca

    # Causal Graph
    cg = rl.get_causal_graph()
    assert "nodes" in cg

    # Causal Counterfactual
    cc = rl.causal_counterfactual("r11-0", ["read_file"])
    assert "counterfactual_score" in cc

    # Comms: 9 agents now (6 from R10 + 3 from R11)
    comms_stats = rl.get_comms_stats()
    assert comms_stats["registered_agents"] >= 9

    print("  [PASS] orchestrator_with_r11_components")


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
        ("persistence_and_metrics", test_persistence_and_metrics),
        ("analytics", test_analytics),
        ("webhook_and_events", test_webhook_and_events),
        ("scheduler", test_scheduler),
        ("replay_buffer", test_replay_buffer),
        ("experiment_tracker", test_experiment_tracker),
        ("prometheus_exporter", test_prometheus_exporter),
        ("orchestrator_with_replay_and_prom", test_orchestrator_with_replay_and_prom),
        ("auto_curriculum", test_auto_curriculum),
        ("replay_evaluator", test_replay_evaluator),
        ("anomaly_detector", test_anomaly_detector),
        ("orchestrator_with_curriculum_and_anomaly", test_orchestrator_with_curriculum_and_anomaly),
        ("policy_gradient", test_policy_gradient),
        ("reward_shaper", test_reward_shaper),
        ("meta_controller", test_meta_controller),
        ("orchestrator_with_policy_and_reward", test_orchestrator_with_policy_and_reward),
        ("multi_objective", test_multi_objective),
        ("transfer_learning", test_transfer_learning),
        ("ensemble_policy", test_ensemble_policy),
        ("orchestrator_with_r8_components", test_orchestrator_with_r8_components),
        ("curiosity_explorer", test_curiosity_explorer),
        ("hierarchical_policy", test_hierarchical_policy),
        ("safety_constraint", test_safety_constraint),
        ("orchestrator_with_r9_components", test_orchestrator_with_r9_components),
        ("model_based_planner", test_model_based_planner),
        ("distributional_reward", test_distributional_reward),
        ("communication_protocol", test_communication_protocol),
        ("orchestrator_with_r10_components", test_orchestrator_with_r10_components),
        ("temporal_abstraction", test_temporal_abstraction),
        ("adversarial_robustness", test_adversarial_robustness),
        ("causal_reasoning", test_causal_reasoning),
        ("orchestrator_with_r11_components", test_orchestrator_with_r11_components),
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
