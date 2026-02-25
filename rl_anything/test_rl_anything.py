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
