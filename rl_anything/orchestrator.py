#!/usr/bin/env python3
"""
RLAnything オーケストレータ
===========================
3 要素（方策・報酬・環境）を束ね、自己進化ループを駆動する司令塔。

使い方:
  from rl_anything.orchestrator import RLAnythingOrchestrator

  rl = RLAnythingOrchestrator()

  # タスク開始
  rl.begin_task("task-001", "Reactコンポーネントにテストを追加")

  # ツール使用を記録 (post_tool_use_hook)
  rl.log_tool("read_file", {"path": "src/App.tsx"}, result="...")
  rl.log_tool("create_file", {"path": "src/App.test.tsx"}, result="...")

  # 途中スコア (例: lint 通過)
  rl.score_intermediate("task-001", 0.8, "lint pass")

  # タスク終了 → 自動で 3 フィードバック + 進化
  result = rl.end_task("task-001", outcome="success", score=0.95)
"""

from __future__ import annotations

import json
import logging
import threading
import time
import urllib.request
import urllib.error
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .types import DifficultyLevel, TaskOutcome, TaskRecord
from .observation_hook import ObservationHook
from .feedback_engine import FeedbackEngine
from .evolution_engine import EvolutionEngine
from .replay_buffer import ReplayBuffer, Experience
from .experiment_tracker import ExperimentTracker
from .metrics_export import PrometheusExporter
from .auto_curriculum import AutoCurriculum
from .replay_evaluator import ReplayEvaluator
from .anomaly_detector import AnomalyDetector
from .policy_gradient import PolicyGradient
from .reward_shaper import RewardShaper
from .meta_controller import MetaController
from .multi_objective import MultiObjectiveOptimizer
from .transfer_learning import TransferLearning
from .ensemble_policy import EnsemblePolicy
from .curiosity_explorer import CuriosityExplorer
from .hierarchical_policy import HierarchicalPolicy
from .safety_constraint import SafetyConstraintManager

_DIR = Path(__file__).parent
_STATE_DIR = _DIR.parent / "logs" / "rl_anything"
_log = logging.getLogger("rl_anything")


class RLAnythingOrchestrator:
    """
    3 要素同時最適化の司令塔。
    各フェーズを統合し、タスクごとに自己進化ループを回す。
    永続化: state.json にサイクル数・難易度を保存し再起動後も継続。
    """

    # Stale task timeout (seconds) — 30分以上放置されたタスクを自動終了
    STALE_TIMEOUT_S = 30 * 60
    # Auto-scheduler interval (seconds) — 5分ごとに stale 掃除
    SCHEDULER_INTERVAL_S = 5 * 60

    def __init__(self, config_path: Optional[Path] = None):
        self._config_path = config_path
        cfg = self._load_config(config_path)

        # 3 コンポーネント
        self.observer = ObservationHook(config=cfg)
        self.feedback = FeedbackEngine(config=cfg)
        self.evolution = EvolutionEngine(config=cfg)

        # 永続化ディレクトリ（config の log_dir があればそちらを優先）
        obs_cfg = cfg.get("observation", {})
        if obs_cfg.get("log_dir"):
            raw_dir = Path(obs_cfg["log_dir"])
            # 相対パスは _DIR.parent (リポジトリルート) 基準に解決
            state_dir = raw_dir if raw_dir.is_absolute() else (_DIR.parent / raw_dir)
        else:
            state_dir = _STATE_DIR
        state_dir.mkdir(parents=True, exist_ok=True)
        self._state_path = state_dir / "state.json"
        self._metrics_path = state_dir / "metrics.jsonl"
        self._lock = threading.Lock()

        # ループカウンタ（永続化から復元）
        self._cycle_count = 0
        self._restore_state()

        # Webhook 設定
        self._webhooks: List[Dict[str, Any]] = cfg.get("webhooks", [])
        # イベントリスナー (in-process)
        self._event_listeners: List[Callable] = []

        # Auto-scheduler
        self._scheduler_running = False
        self._scheduler_thread: Optional[threading.Thread] = None
        auto_sched = cfg.get("auto_scheduler", {})
        if auto_sched.get("enabled"):
            self.start_scheduler(interval_s=auto_sched.get("interval_s", self.SCHEDULER_INTERVAL_S))

        # Replay Buffer
        replay_cfg = cfg.get("replay_buffer", {})
        replay_max = replay_cfg.get("max_size", 500)
        replay_path = state_dir / "replay.jsonl" if replay_cfg.get("persist", True) else None
        self.replay = ReplayBuffer(max_size=replay_max, persist_path=replay_path)

        # A/B Experiment Tracker
        exp_dir = state_dir / "experiments"
        self.experiments = ExperimentTracker(experiments_dir=exp_dir)

        # Prometheus Exporter
        self.prom = PrometheusExporter()
        self._init_prom_metrics()
        # 復元した状態から gauge を設定
        self.prom.set("rl_cycle_count", float(self._cycle_count))
        self.prom.set("rl_current_difficulty", float(
            ["concrete", "guided", "standard", "abstract"].index(
                self.evolution.current_difficulty.value
            )
        ))

        # Auto-Curriculum Engine
        self.curriculum = AutoCurriculum(config=cfg)

        # Replay Evaluator
        scoring_criteria = cfg.get("reward_model", {}).get("scoring_criteria", {})
        self.replay_evaluator = ReplayEvaluator(scoring_criteria=scoring_criteria)

        # Anomaly Detector
        self.anomaly_detector = AnomalyDetector(config=cfg)

        # Policy Gradient Estimator (Round 7)
        pg_persist = state_dir / "policy_gradient.json"
        self.policy_gradient = PolicyGradient(persist_path=pg_persist)

        # Reward Shaper (Round 7)
        self.reward_shaper = RewardShaper(config=cfg)

        # Meta-Controller (Round 7)
        self.meta_controller = MetaController(config=cfg)

        # Multi-Objective Optimizer (Round 8)
        mo_persist = state_dir / "multi_objective.json"
        self.multi_objective = MultiObjectiveOptimizer(persist_path=mo_persist)

        # Transfer Learning Engine (Round 8)
        tl_persist = state_dir / "transfer_learning.json"
        self.transfer_learning = TransferLearning(persist_path=tl_persist, config=cfg)

        # Ensemble Policy (Round 8)
        ep_persist = state_dir / "ensemble_policy.json"
        self.ensemble_policy = EnsemblePolicy(n_members=3, persist_path=ep_persist)

        # Curiosity Explorer (Round 9)
        ce_persist = state_dir / "curiosity_explorer.json"
        self.curiosity = CuriosityExplorer(persist_path=ce_persist, config=cfg)

        # Hierarchical Policy (Round 9)
        hp_persist = state_dir / "hierarchical_policy.json"
        self.hierarchical = HierarchicalPolicy(persist_path=hp_persist, config=cfg)

        # Safety Constraint Manager (Round 9)
        sc_persist = state_dir / "safety_constraint.json"
        self.safety = SafetyConstraintManager(persist_path=sc_persist, config=cfg)

    # ═══════════════════════════════════════════════════════
    # Prometheus メトリクス初期化
    # ═══════════════════════════════════════════════════════
    def _init_prom_metrics(self) -> None:
        """Prometheus メトリクス定義を登録"""
        self.prom.register("rl_cycles_total", "counter", "Total completed RL cycles")
        self.prom.register("rl_cycle_count", "gauge", "Current cycle count")
        self.prom.register("rl_current_difficulty", "gauge", "Current difficulty level (0=concrete..3=abstract)")
        self.prom.register("rl_score", "histogram", "Task scores distribution")
        self.prom.register("rl_skills_total", "gauge", "Total learned skills")
        self.prom.register("rl_replay_buffer_size", "gauge", "Replay buffer current size")
        self.prom.register("rl_active_experiments", "gauge", "Active A/B experiments")
        self.prom.register("rl_alerts_total", "counter", "Total anomaly alerts fired")
        self.prom.register("rl_curriculum_changes", "counter", "Auto-curriculum difficulty changes")
        self.prom.register("rl_policy_updates", "counter", "Policy gradient update steps")
        self.prom.register("rl_reward_shaped", "histogram", "Shaped reward values")
        self.prom.register("rl_meta_adjustments", "counter", "Meta-controller parameter adjustments")
        self.prom.register("rl_health_score", "gauge", "Meta-controller system health score")
        self.prom.register("rl_pareto_size", "gauge", "Multi-objective Pareto front size")
        self.prom.register("rl_transfer_count", "counter", "Knowledge transfer events")
        self.prom.register("rl_ensemble_decisions", "counter", "Ensemble policy decisions")
        self.prom.register("rl_ensemble_agreement", "histogram", "Ensemble agreement distribution")
        self.prom.register("rl_curiosity_bonus", "histogram", "Curiosity bonus distribution")
        self.prom.register("rl_novel_states", "gauge", "Total novel state discoveries")
        self.prom.register("rl_option_switches", "counter", "Hierarchical option switches")
        self.prom.register("rl_safety_violations", "counter", "Safety constraint violations")
        self.prom.register("rl_safety_score", "gauge", "Overall safety score")

    # ═══════════════════════════════════════════════════════
    # タスクライフサイクル
    # ═══════════════════════════════════════════════════════
    def begin_task(
        self,
        task_id: str,
        description: str,
        difficulty: Optional[str] = None,
    ) -> None:
        """タスク開始 — 難易度は指定がなければ進化エンジンの推奨値"""
        diff = difficulty or self.evolution.current_difficulty.value
        self.observer.on_task_start(task_id, description, difficulty=diff)

    def log_tool(
        self,
        tool_name: str,
        params: Optional[Dict[str, Any]] = None,
        result: Any = None,
        error: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> None:
        """ツール使用を記録 (post_tool_use_hook 相当)"""
        self.observer.on_tool_start(tool_name, params or {}, task_id=task_id)
        self.observer.on_tool_end(tool_name, result=result, error=error, task_id=task_id)

    def score_intermediate(self, task_id: str, score: float, reason: str = "") -> None:
        """途中経過スコア (統合フィードバック用)"""
        self.observer.on_intermediate_score(task_id, score, reason)

    def end_task(
        self,
        task_id: str,
        outcome: str = "unknown",
        score: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        タスク終了 → 自動スコアリング + 3 フィードバック + 進化サイクルを自動実行。
        score が None の場合、ヒューリスティックで自動計算する。
        """
        # 0) 自動スコアリング (score 未指定時)
        if score is None:
            score = self._auto_score(task_id, outcome)

        # 1) 観測完了
        record = self.observer.on_task_end(
            task_id, outcome=outcome, final_score=score, metadata=metadata
        )
        all_records = self.observer.get_completed_records(limit=200)

        # 2) フィードバック
        fb_result = self.feedback.run_full_feedback_cycle(record, all_records)

        # 3) 進化
        recommended = DifficultyLevel(fb_result["recommended_difficulty"])
        eval_data = fb_result.get("evaluation", {})
        success_rate = (eval_data.get("adjustments") or {}).get("success_rate", 0.5)

        evo_result = self.evolution.run_evolution_cycle(
            all_records, recommended, success_rate
        )

        old_difficulty = self.evolution.current_difficulty
        self._cycle_count += 1

        result = {
            "task_id": task_id,
            "outcome": outcome,
            "cycle": self._cycle_count,
            "feedback": fb_result,
            "evolution": evo_result,
            "stats": self.get_dashboard(),
        }

        # 永続化: state.json + metrics.jsonl
        self._persist_state()
        self._append_metric(task_id, outcome, score, fb_result, evo_result)

        # Replay Buffer に追加
        actions = record.actions if hasattr(record, "actions") else []
        self.replay.push(Experience(
            task_id=task_id,
            outcome=outcome,
            score=score,
            difficulty=self.evolution.current_difficulty.value,
            cycle=self._cycle_count,
            tool_count=len(actions),
            error_count=sum(1 for a in actions if a.error),
            skills_used=record.skills_used if hasattr(record, "skills_used") else [],
        ))

        # Prometheus メトリクス更新
        self.prom.inc("rl_cycles_total", labels={"outcome": outcome})
        self.prom.set("rl_cycle_count", float(self._cycle_count))
        self.prom.observe("rl_score", score, labels={"outcome": outcome})
        diff_idx = ["concrete", "guided", "standard", "abstract"].index(
            self.evolution.current_difficulty.value
        )
        self.prom.set("rl_current_difficulty", float(diff_idx))
        self.prom.set("rl_skills_total", float(len(self.evolution.skills)))
        self.prom.set("rl_replay_buffer_size", float(self.replay.size))
        self.prom.set("rl_active_experiments", float(
            self.experiments.get_stats().get("active_experiments", 0)
        ))

        # イベント発火
        self._emit_event("cycle_completed", {
            "task_id": task_id, "outcome": outcome, "cycle": self._cycle_count,
            "score": score, "difficulty": self.evolution.current_difficulty.value,
        })
        # 難易度変更イベント
        if self.evolution.current_difficulty != old_difficulty:
            self._emit_event("difficulty_changed", {
                "from": old_difficulty.value,
                "to": self.evolution.current_difficulty.value,
                "cycle": self._cycle_count,
            })
        # 新スキル獲得イベント
        new_skills = evo_result.get("new_skills", [])
        if new_skills:
            self._emit_event("skills_acquired", {
                "skills": [s.get("name", s) if isinstance(s, dict) else str(s) for s in new_skills],
                "total": len(self.evolution.skills),
                "cycle": self._cycle_count,
            })

        # ──── Auto-Curriculum 判定 ────
        history = self.get_history(limit=100)
        if len(history) >= 3:
            rec = self.curriculum.recommend(
                history, self.evolution.current_difficulty,
                replay_stats=self.replay.get_stats(),
            )
            if rec.changed and rec.confidence >= 0.5:
                self.evolution.current_difficulty = rec.recommended
                self._persist_state()
                self.prom.inc("rl_curriculum_changes")
                self._emit_event("auto_curriculum", rec.to_dict())
                result["auto_curriculum"] = rec.to_dict()

        # ──── Anomaly Detection ────
        alerts = self.anomaly_detector.check(history)
        if alerts:
            for a in alerts:
                self.prom.inc("rl_alerts_total", labels={"type": a.alert_type, "severity": a.severity})
            self._emit_event("anomaly_alerts", {
                "count": len(alerts),
                "alerts": [a.to_dict() for a in alerts],
                "cycle": self._cycle_count,
            })
            result["alerts"] = [a.to_dict() for a in alerts]

        # ──── Reward Shaping (Round 7) ────
        try:
            shaped = self.reward_shaper.shape(
                raw_score=score,
                outcome=outcome,
                difficulty=self.evolution.current_difficulty.value,
                success_rate=success_rate,
                avg_score=sum(e.get("score", 0) for e in history[-20:]) / max(1, len(history[-20:])),
            )
            result["shaped_reward"] = {
                "raw": shaped.raw, "shaped": shaped.shaped,
                "potential_bonus": shaped.potential_bonus,
                "curiosity_bonus": shaped.curiosity_bonus,
                "difficulty_bonus": shaped.difficulty_bonus,
                "consistency_bonus": shaped.consistency_bonus,
            }
            self.prom.observe("rl_reward_shaped", shaped.shaped, labels={"outcome": outcome})
        except Exception as e:
            _log.warning("reward shaping error: %s", e)
            shaped = None

        # ──── Policy Gradient (Round 7) ────
        try:
            pg_state = self.policy_gradient.encode_state(
                success_rate=success_rate,
                avg_score=sum(e.get("score", 0) for e in history[-20:]) / max(1, len(history[-20:])),
                difficulty=self.evolution.current_difficulty.value,
            )
            # 前回のアクション結果を報酬として記録
            reward_val = shaped.shaped if shaped else score
            # 推奨アクションを取得して記録
            action, log_prob = self.policy_gradient.select_action(pg_state)
            self.policy_gradient.record(pg_state, action, reward_val, log_prob, self._cycle_count)

            # 一定間隔でポリシー更新
            if self._cycle_count % 5 == 0 and self._cycle_count > 0:
                update_stats = self.policy_gradient.update()
                if update_stats:
                    self.prom.inc("rl_policy_updates")
                    result["policy_update"] = update_stats
        except Exception as e:
            _log.warning("policy gradient error: %s", e)

        # ──── Meta-Controller Tuning (Round 7) ────
        try:
            if self._cycle_count % 10 == 0 and len(history) >= 5:
                # 現在のパラメータを収集
                pg_snap = self.policy_gradient.get_snapshot()
                current_params = {
                    "learning_rate": pg_snap.get("learning_rate", 0.01),
                    "temperature": pg_snap.get("temperature", 1.0),
                    "curriculum_up_threshold": getattr(self.curriculum, 'up_threshold', 0.75),
                    "curriculum_down_threshold": getattr(self.curriculum, 'down_threshold', 0.30),
                    "anomaly_z_threshold": getattr(self.anomaly_detector, 'z_threshold', 2.0),
                }
                score_series = [e.get("score", 0) for e in history]
                # ポリシーエントロピ
                probs = self.policy_gradient.get_action_probs(pg_state)
                import math as _math
                entropy = -sum(p * _math.log(max(p, 1e-10)) for p in probs.values())

                meta_report = self.meta_controller.tune(
                    score_history=score_series,
                    current_params=current_params,
                    alert_count=len(alerts) if alerts else 0,
                    policy_entropy=entropy,
                    curriculum_changes=0,
                )
                # 調整を適用
                for adj in meta_report.adjustments:
                    self._apply_meta_adjustment(adj)
                    self.prom.inc("rl_meta_adjustments", labels={"param": adj.param_name})
                self.prom.set("rl_health_score", meta_report.health_score)
                if meta_report.adjustments:
                    self._emit_event("meta_tuning", meta_report.to_dict())
                    result["meta_tuning"] = meta_report.to_dict()
        except Exception as e:
            _log.warning("meta-controller error: %s", e)

        # ──── Multi-Objective Recording (Round 8) ────
        try:
            # 効率 = score / max(1, tool_count) — アクション数に対するスコア比
            tool_count = len(record.actions) if hasattr(record, "actions") else 1
            efficiency = score / max(1, tool_count) * 10  # スケーリング
            # 探索度 = ポリシーエントロピ (pg_state があれば)
            try:
                probs_for_mo = self.policy_gradient.get_action_probs(pg_state)
                import math as _math_mo
                exploration = -sum(p * _math_mo.log(max(p, 1e-10)) for p in probs_for_mo.values())
            except Exception:
                exploration = 0.5

            mo_values = {
                "score": score,
                "success_rate": success_rate,
                "efficiency": efficiency,
                "exploration": exploration,
            }
            sol = self.multi_objective.record_solution(self._cycle_count, mo_values)
            self.prom.set("rl_pareto_size", float(
                sum(1 for s in self.multi_objective._solutions if s.is_pareto)
            ))
            result["multi_objective"] = {
                "scalarized": sol.scalarized,
                "is_pareto": sol.is_pareto,
                "values": mo_values,
            }
        except Exception as e:
            _log.warning("multi-objective error: %s", e)

        # ──── Transfer Learning Domain Update (Round 8) ────
        try:
            # タスク説明からドメインを推定
            desc = ""
            if hasattr(record, "description"):
                desc = record.description or ""
            elif hasattr(record, "task_id"):
                desc = record.task_id or ""
            domain = self.transfer_learning.infer_domain(desc)
            self.transfer_learning.update_domain(
                domain=domain,
                score=score,
                outcome=outcome,
                difficulty=self.evolution.current_difficulty.value,
            )
            result["transfer_domain"] = domain
        except Exception as e:
            _log.warning("transfer learning error: %s", e)

        # ──── Ensemble Policy Decision (Round 8) ────
        try:
            ens_state = self.policy_gradient.encode_state(
                success_rate=success_rate,
                avg_score=sum(e.get("score", 0) for e in history[-20:]) / max(1, len(history[-20:])),
                difficulty=self.evolution.current_difficulty.value,
            )
            ens_decision = self.ensemble_policy.decide(ens_state)
            self.ensemble_policy.update_rewards(score)
            self.prom.inc("rl_ensemble_decisions")
            self.prom.observe("rl_ensemble_agreement", ens_decision.agreement)
            result["ensemble"] = {
                "action": ens_decision.action,
                "agreement": ens_decision.agreement,
                "confidence": ens_decision.confidence,
                "method": ens_decision.method,
            }
        except Exception as e:
            _log.warning("ensemble policy error: %s", e)

        # ──── Curiosity Exploration (Round 9) ────
        try:
            tools_used = [a.tool_name for a in (record.actions if hasattr(record, 'actions') else [])]
            domain = result.get("transfer_domain", "unknown")
            state_hash = CuriosityExplorer.hash_state(
                difficulty=self.evolution.current_difficulty.value,
                outcome=outcome,
                tool_names=tools_used,
                domain=domain,
            )
            signal = self.curiosity.observe(state_hash, score, self._cycle_count)
            self.prom.observe("rl_curiosity_bonus", signal.curiosity_bonus)
            self.prom.set("rl_novel_states", float(self.curiosity._novel_count))
            result["curiosity"] = signal.to_dict()
        except Exception as e:
            _log.warning("curiosity explorer error: %s", e)

        # ──── Hierarchical Policy Decision (Round 9) ────
        try:
            h_decision = self.hierarchical.decide(
                difficulty=self.evolution.current_difficulty.value,
                cycle=self._cycle_count,
            )
            self.hierarchical.update_reward(score, outcome)
            if h_decision.should_terminate:
                self.prom.inc("rl_option_switches")
            result["hierarchical"] = h_decision.to_dict()
        except Exception as e:
            _log.warning("hierarchical policy error: %s", e)

        # ──── Safety Constraint Check (Round 9) ────
        try:
            exploration_rate = self.curiosity.get_stats().get("exploration_rate", 0.5)
            safety_metrics = SafetyConstraintManager.extract_metrics(history, exploration_rate)
            safety_result = self.safety.check_all(safety_metrics, self._cycle_count)
            self.prom.set("rl_safety_score", self.safety.get_safety_score())
            if not safety_result["safe"]:
                self.prom.inc("rl_safety_violations")
                self._emit_event("safety_violation", {
                    "violations": safety_result["violations"],
                    "recovery": safety_result["recovery"],
                    "cycle": self._cycle_count,
                })
            result["safety"] = {
                "safe": safety_result["safe"],
                "total_penalty": safety_result["total_penalty"],
                "violation_count": len(safety_result["violations"]),
                "warning_count": len(safety_result["warnings"]),
                "recovery": safety_result["recovery"],
            }
        except Exception as e:
            _log.warning("safety constraint error: %s", e)

        return result

    # ═══════════════════════════════════════════════════════
    # Meta 調整の適用
    # ═══════════════════════════════════════════════════════
    def _apply_meta_adjustment(self, adj) -> None:
        """MetaAdjustment を対応コンポーネントに反映"""
        try:
            if adj.param_name == "learning_rate":
                self.policy_gradient.lr = adj.new_value
            elif adj.param_name == "temperature":
                self.policy_gradient.temperature = adj.new_value
            elif adj.param_name == "curriculum_up_threshold":
                if hasattr(self.curriculum, 'up_threshold'):
                    self.curriculum.up_threshold = adj.new_value
            elif adj.param_name == "curriculum_down_threshold":
                if hasattr(self.curriculum, 'down_threshold'):
                    self.curriculum.down_threshold = adj.new_value
            elif adj.param_name == "anomaly_z_threshold":
                if hasattr(self.anomaly_detector, 'z_threshold'):
                    self.anomaly_detector.z_threshold = adj.new_value
            _log.info("meta-adjustment applied: %s → %s", adj.param_name, adj.new_value)
        except Exception as e:
            _log.warning("meta-adjustment failed: %s → %s", adj.param_name, e)

    # ═══════════════════════════════════════════════════════
    # Round 7: Policy / Reward / Meta ダッシュボード
    # ═══════════════════════════════════════════════════════
    def get_policy_snapshot(self) -> Dict[str, Any]:
        """方策勾配パラメータとポリシーサンプル"""
        snap = self.policy_gradient.get_snapshot()
        stats = self.policy_gradient.get_stats()
        return {**snap, "stats": stats}

    def get_reward_stats(self) -> Dict[str, Any]:
        """報酬シェイパーの統計"""
        return self.reward_shaper.get_stats()

    def get_meta_status(self) -> Dict[str, Any]:
        """メタコントローラの状態"""
        stats = self.meta_controller.get_stats()
        health_trend = self.meta_controller.get_health_trend()
        return {
            **stats,
            "health_trend": health_trend,
        }

    def policy_recommend(self, success_rate: float = 0.5, avg_score: float = 0.5,
                         difficulty: Optional[str] = None) -> Dict[str, Any]:
        """方策からアクション推奨を取得"""
        diff = difficulty or self.evolution.current_difficulty.value
        state = self.policy_gradient.encode_state(success_rate, avg_score, diff)
        rec = self.policy_gradient.recommend_action(state)
        return {
            "recommended_action": rec.get("action", "stay"),
            "action_probabilities": rec.get("probs", {}),
            "entropy": rec.get("entropy", 0),
            "state": state,
            "difficulty": diff,
        }

    def manual_policy_update(self, batch_size: int = 10) -> Dict[str, Any]:
        """方策勾配の手動更新"""
        result = self.policy_gradient.update(batch_size=batch_size)
        if result:
            self.prom.inc("rl_policy_updates")
        return result or {"status": "no_update", "reason": "insufficient_trajectories"}

    def manual_meta_tune(self) -> Dict[str, Any]:
        """メタコントローラの手動チューニング"""
        history = self.get_history(limit=100)
        if len(history) < 3:
            return {"status": "skipped", "reason": "insufficient_history"}

        pg_snap = self.policy_gradient.get_snapshot()
        current_params = {
            "learning_rate": pg_snap.get("learning_rate", 0.01),
            "temperature": pg_snap.get("temperature", 1.0),
            "curriculum_up_threshold": getattr(self.curriculum, 'up_threshold', 0.75),
            "curriculum_down_threshold": getattr(self.curriculum, 'down_threshold', 0.30),
            "anomaly_z_threshold": getattr(self.anomaly_detector, 'z_threshold', 2.0),
        }
        score_series = [e.get("score", 0) for e in history]

        # ポリシーエントロピ計算
        import math as _math
        state = self.policy_gradient.encode_state(0.5, 0.5, self.evolution.current_difficulty.value)
        probs = self.policy_gradient.get_action_probs(state)
        entropy = -sum(p * _math.log(max(p, 1e-10)) for p in probs.values())

        report = self.meta_controller.tune(
            score_history=score_series,
            current_params=current_params,
            policy_entropy=entropy,
        )
        for adj in report.adjustments:
            self._apply_meta_adjustment(adj)
            self.prom.inc("rl_meta_adjustments", labels={"param": adj.param_name})
        self.prom.set("rl_health_score", report.health_score)
        return report.to_dict()

    # ═══════════════════════════════════════════════════════
    # Round 8: Multi-Objective / Transfer / Ensemble
    # ═══════════════════════════════════════════════════════
    def get_multi_objective_stats(self) -> Dict[str, Any]:
        """多目的最適化の統計とパレートフロント"""
        stats = self.multi_objective.get_stats()
        front = self.multi_objective.get_pareto_front()
        return {**stats, "pareto_front": front}

    def get_trade_off_analysis(self) -> Dict[str, Any]:
        """Objective 間のトレードオフ分析"""
        return self.multi_objective.get_trade_off_analysis()

    def get_transfer_stats(self) -> Dict[str, Any]:
        """転移学習の統計"""
        stats = self.transfer_learning.get_stats()
        similarity = self.transfer_learning.get_similarity_matrix()
        return {**stats, "similarity_matrix": similarity}

    def suggest_transfer(self, target_domain: str) -> Dict[str, Any]:
        """指定ドメインへの転移提案"""
        result = self.transfer_learning.suggest_transfer(target_domain)
        if result is None:
            return {"status": "no_transfer", "reason": "no suitable source found"}
        return result.to_dict()

    def apply_transfer(self, target_domain: str) -> Dict[str, Any]:
        """転移を適用"""
        result = self.transfer_learning.apply_transfer(target_domain)
        if result is None:
            return {"status": "no_transfer", "reason": "no suitable source found"}
        self.prom.inc("rl_transfer_count")
        self._emit_event("knowledge_transfer", {
            "source": result.get("source_domain"),
            "target": result.get("target_domain"),
            "similarity": result.get("similarity"),
        })
        return result

    def get_ensemble_stats(self) -> Dict[str, Any]:
        """アンサンブルポリシーの統計"""
        return self.ensemble_policy.get_stats()

    def ensemble_decide(self, success_rate: float = 0.5, avg_score: float = 0.5,
                        difficulty: Optional[str] = None,
                        method: Optional[str] = None) -> Dict[str, Any]:
        """アンサンブルで意思決定"""
        diff = difficulty or self.evolution.current_difficulty.value
        state = self.policy_gradient.encode_state(success_rate, avg_score, diff)
        decision = self.ensemble_policy.decide(state, method=method)
        self.prom.inc("rl_ensemble_decisions")
        self.prom.observe("rl_ensemble_agreement", decision.agreement)
        return decision.to_dict()

    def get_ensemble_diversity(self) -> Dict[str, Any]:
        """メンバー間の多様性指標"""
        return self.ensemble_policy.get_diversity()

    # ═══════════════════════════════════════════════════════
    # Round 9: Curiosity / Hierarchical / Safety
    # ═══════════════════════════════════════════════════════
    def get_curiosity_stats(self) -> Dict[str, Any]:
        """好奇心探索の統計"""
        stats = self.curiosity.get_stats()
        recent = self.curiosity.get_recent_signals(limit=10)
        recommendations = self.curiosity.recommend_exploration(top_k=5)
        return {**stats, "recent_signals": recent, "recommendations": recommendations}

    def get_novelty_map(self) -> Dict[str, Any]:
        """新規性マップ"""
        return self.curiosity.get_novelty_map()

    def get_hierarchical_stats(self) -> Dict[str, Any]:
        """階層型方策の統計"""
        stats = self.hierarchical.get_stats()
        recent = self.hierarchical.get_recent_decisions(limit=10)
        performance = self.hierarchical.get_option_performance()
        return {**stats, "recent_decisions": recent, "option_performance": performance}

    def hierarchical_decide(self, difficulty: Optional[str] = None) -> Dict[str, Any]:
        """階層的意思決定を実行"""
        diff = difficulty or self.evolution.current_difficulty.value
        decision = self.hierarchical.decide(difficulty=diff, cycle=self._cycle_count)
        if decision.should_terminate:
            self.prom.inc("rl_option_switches")
        return decision.to_dict()

    def get_safety_stats(self) -> Dict[str, Any]:
        """安全制約の統計"""
        stats = self.safety.get_stats()
        constraints = self.safety.get_constraints()
        safety_score = self.safety.get_safety_score()
        return {**stats, "constraints": constraints, "safety_score": safety_score}

    def check_safety(self) -> Dict[str, Any]:
        """安全制約をチェック"""
        history = self.get_history(limit=100)
        exploration_rate = self.curiosity.get_stats().get("exploration_rate", 0.5)
        metrics = SafetyConstraintManager.extract_metrics(history, exploration_rate)
        result = self.safety.check_all(metrics, self._cycle_count)
        self.prom.set("rl_safety_score", self.safety.get_safety_score())
        return result

    def get_safety_violations(self, limit: int = 50) -> Dict[str, Any]:
        """安全違反履歴"""
        violations = self.safety.get_violation_history(limit=limit)
        return {
            "violations": violations,
            "total": len(violations),
            "safety_score": self.safety.get_safety_score(),
        }

    def get_options(self) -> Dict[str, Any]:
        """階層型Optionsの一覧"""
        return self.hierarchical.get_options()

    # ═══════════════════════════════════════════════════════
    # 自動スコアリング
    # ═══════════════════════════════════════════════════════
    def _auto_score(self, task_id: str, outcome: str) -> float:
        """
        スコア未指定時のヒューリスティック自動計算。
        - outcome ベース (success=0.7, partial=0.5, failure=0.2, unknown=0.4)
        - エラー率で減点 (error / total_actions)
        - 中間スコアがあればその平均を加味
        - アクション数が極端に少ない or 多い場合の補正
        """
        # ベーススコア
        base_scores = {
            "success": 0.75,
            "partial": 0.50,
            "failure": 0.20,
            "unknown": 0.40,
        }
        score = base_scores.get(outcome, 0.40)

        # アクティブタスクの情報を参照
        record = self.observer._active_tasks.get(task_id)
        if record is None:
            return round(score, 4)

        actions = record.actions
        total = len(actions)

        if total > 0:
            # エラー率で減点 (最大 -0.25)
            error_count = sum(1 for a in actions if a.error)
            error_ratio = error_count / total
            score -= error_ratio * 0.25

            # アクション数のスイートスポット補正 (3-15 が理想)
            if total <= 2:
                score -= 0.05  # 少なすぎ: やっとけ感
            elif total > 30:
                score -= 0.10  # 多すぎ: 試行錯誤しすぎ

        # 中間スコアの平均を加味 (30%ウェイト)
        intermediate = record.intermediate_scores
        if intermediate:
            avg_inter = sum(intermediate) / len(intermediate)
            score = score * 0.7 + avg_inter * 0.3

        return round(max(0.0, min(1.0, score)), 4)

    # ═══════════════════════════════════════════════════════
    # ダッシュボード
    # ═══════════════════════════════════════════════════════
    def get_dashboard(self) -> Dict[str, Any]:
        """システム全体のステータス"""
        return {
            "observation": self.observer.get_stats(),
            "feedback": self.feedback.get_stats(),
            "evolution": self.evolution.get_stats(),
            "cycle_count": self._cycle_count,
            "current_difficulty": self.evolution.current_difficulty.value,
            "scoring_criteria": dict(self.feedback.scoring_criteria),
            "timestamp": datetime.now().isoformat(),
        }

    def get_skills_for_prompt(self) -> str:
        """
        現在のスキルをプロンプトに含められる形式で返す。
        CLAUDE.md や MEMORY.md に注入して方策を改善する。
        """
        if not self.evolution.skills:
            return ""

        lines = ["# 学習済み行動パターン（自動生成）", ""]
        sorted_skills = sorted(
            self.evolution.skills, key=lambda s: s.success_rate, reverse=True
        )
        for skill in sorted_skills[:10]:
            lines.append(
                f"- {skill.name}: {skill.description} "
                f"(成功率 {skill.success_rate:.0%})"
            )

        difficulty_hint = self.evolution._difficulty_to_instruction_hint(
            self.evolution.current_difficulty
        )
        lines.append("")
        lines.append(f"# 現在の難易度: {self.evolution.current_difficulty.value}")
        lines.append(difficulty_hint)

        return "\n".join(lines)

    # ═══════════════════════════════════════════════════════
    # Stale タスク自動クリーンアップ
    # ═══════════════════════════════════════════════════════
    def cleanup_stale_tasks(self, timeout_s: Optional[float] = None) -> Dict[str, Any]:
        """
        一定時間アクティブなままのタスクを自動終了 (outcome=unknown)。
        返り値: {"cleaned": [...task_ids], "count": N}
        """
        timeout = timeout_s or self.STALE_TIMEOUT_S
        now = time.time()
        cleaned: List[str] = []

        stale_ids = []
        for tid, record in list(self.observer._active_tasks.items()):
            try:
                started = datetime.fromisoformat(record.start_time).timestamp()
                if now - started > timeout:
                    stale_ids.append(tid)
            except Exception:
                pass

        for tid in stale_ids:
            try:
                self.end_task(tid, outcome="unknown", score=None)
                cleaned.append(tid)
            except Exception:
                pass

        return {"cleaned": cleaned, "count": len(cleaned)}

    # ═══════════════════════════════════════════════════════
    # メトリクス履歴
    # ═══════════════════════════════════════════════════════
    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        直近の完了サイクルを metrics.jsonl から返す。
        フロントエンド履歴チャート用。
        """
        if not self._metrics_path.exists():
            return []
        try:
            lines = self._metrics_path.read_text(encoding="utf-8").strip().splitlines()
            entries = []
            for line in lines[-limit:]:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
            return entries
        except Exception:
            return []

    # ═══════════════════════════════════════════════════════
    # Analytics — トレンド分析
    # ═══════════════════════════════════════════════════════
    def get_analytics(self, windows: Optional[List[int]] = None) -> Dict[str, Any]:
        """
        metrics.jsonl からローリング統計を算出。
        返り値:
          rolling_success_rate: {window_N: rate, ...}
          rolling_avg_score:    {window_N: avg, ...}
          difficulty_timeline:  [{cycle, difficulty}, ...]
          skill_growth:         [{cycle, skills_total}, ...]
          score_series:         [score1, score2, ...]
          outcome_distribution: {success: N, failure: N, ...}
        """
        windows = windows or [5, 10, 20]
        entries = self.get_history(limit=500)
        if not entries:
            return {
                "rolling_success_rate": {}, "rolling_avg_score": {},
                "difficulty_timeline": [], "skill_growth": [],
                "score_series": [], "outcome_distribution": {},
                "total_cycles": 0,
            }

        scores = [e.get("score", 0) for e in entries]
        outcomes = [e.get("outcome", "unknown") for e in entries]

        # Rolling success rate
        rolling_sr = {}
        for w in windows:
            recent = outcomes[-w:]
            if recent:
                rolling_sr[f"last_{w}"] = round(
                    sum(1 for o in recent if o == "success") / len(recent), 4
                )

        # Rolling avg score
        rolling_as = {}
        for w in windows:
            recent = scores[-w:]
            if recent:
                rolling_as[f"last_{w}"] = round(sum(recent) / len(recent), 4)

        # Difficulty timeline
        diff_timeline = []
        for e in entries:
            diff_timeline.append({"cycle": e.get("cycle"), "difficulty": e.get("difficulty")})

        # Skill growth
        skill_growth = []
        for e in entries:
            skill_growth.append({"cycle": e.get("cycle"), "skills_total": e.get("skills_total", 0)})

        # Outcome distribution
        dist: Dict[str, int] = defaultdict(int)
        for o in outcomes:
            dist[o] += 1

        return {
            "rolling_success_rate": rolling_sr,
            "rolling_avg_score": rolling_as,
            "difficulty_timeline": diff_timeline,
            "skill_growth": skill_growth,
            "score_series": scores,
            "outcome_distribution": dict(dist),
            "total_cycles": len(entries),
        }

    # ═══════════════════════════════════════════════════════
    # Event / Webhook システム
    # ═══════════════════════════════════════════════════════
    def add_event_listener(self, callback: Callable) -> None:
        """イベントリスナーを追加 (callback(event_type, payload))"""
        self._event_listeners.append(callback)

    def _emit_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        """
        イベントを発火:
        1) in-process リスナーに通知
        2) webhook に POST (非同期スレッドで送信)
        """
        full = {"event": event_type, "ts": datetime.now().isoformat(), **payload}

        # In-process listeners
        for cb in self._event_listeners:
            try:
                cb(event_type, full)
            except Exception:
                pass

        # Webhook 送信
        for wh in self._webhooks:
            url = wh.get("url", "")
            events = wh.get("events", [])  # 空 = 全イベント
            if not url:
                continue
            if events and event_type not in events:
                continue
            threading.Thread(
                target=self._fire_webhook, args=(url, full), daemon=True
            ).start()

    def _fire_webhook(self, url: str, payload: Dict[str, Any]) -> None:
        """HTTP POST で webhook を送信 (Slack 互換)"""
        try:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(
                url, data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                _log.debug("webhook sent to %s → %s", url, resp.status)
        except Exception as e:
            _log.warning("webhook failed: %s → %s", url, e)

    # ═══════════════════════════════════════════════════════
    # Auto-scheduler（バックグラウンドデーモン）
    # ═══════════════════════════════════════════════════════
    def start_scheduler(self, interval_s: Optional[float] = None) -> Dict[str, Any]:
        """
        定期タスク（stale 掃除）をバックグラウンドで実行開始。
        """
        if self._scheduler_running:
            return {"ok": True, "status": "already_running"}
        interval = interval_s or self.SCHEDULER_INTERVAL_S
        self._scheduler_running = True

        def _loop():
            while self._scheduler_running:
                try:
                    result = self.cleanup_stale_tasks()
                    if result["count"] > 0:
                        _log.info("scheduler: cleaned %d stale tasks", result["count"])
                        self._emit_event("scheduler_cleanup", result)
                except Exception as e:
                    _log.warning("scheduler error: %s", e)
                time.sleep(interval)

        self._scheduler_thread = threading.Thread(target=_loop, daemon=True, name="rl-scheduler")
        self._scheduler_thread.start()
        return {"ok": True, "status": "started", "interval_s": interval}

    def stop_scheduler(self) -> Dict[str, Any]:
        """スケジューラ停止"""
        if not self._scheduler_running:
            return {"ok": True, "status": "not_running"}
        self._scheduler_running = False
        return {"ok": True, "status": "stopped"}

    # ═══════════════════════════════════════════════════════
    # Config ホットリロード
    # ═══════════════════════════════════════════════════════
    def reload_config(self) -> Dict[str, Any]:
        """
        config.json を再読み込みして feedback の scoring_criteria を更新。
        再起動なしで設定変更を反映。
        """
        try:
            cfg = self._load_config(self._config_path)
            reward_cfg = cfg.get("reward_model", {})
            if reward_cfg.get("scoring_criteria"):
                self.feedback.scoring_criteria = dict(reward_cfg["scoring_criteria"])
            evo_cfg = cfg.get("evolution", {})
            if evo_cfg.get("skill_success_threshold"):
                self.evolution.success_threshold = evo_cfg["skill_success_threshold"]
            # Webhook 設定も再読み込み
            self._webhooks = cfg.get("webhooks", [])
            return {"ok": True, "reloaded": True, "criteria": dict(self.feedback.scoring_criteria)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ═══════════════════════════════════════════════════════
    # 永続化 (state.json)
    # ═══════════════════════════════════════════════════════
    def _persist_state(self) -> None:
        """cycle_count と difficulty を state.json に保存"""
        try:
            state = {
                "cycle_count": self._cycle_count,
                "current_difficulty": self.evolution.current_difficulty.value,
                "last_updated": datetime.now().isoformat(),
            }
            with self._lock:
                self._state_path.write_text(
                    json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8"
                )
        except Exception:
            pass

    def _restore_state(self) -> None:
        """起動時に state.json からサイクル数・難易度を復元"""
        if not self._state_path.exists():
            return
        try:
            data = json.loads(self._state_path.read_text(encoding="utf-8"))
            self._cycle_count = data.get("cycle_count", 0)
            diff_val = data.get("current_difficulty", "standard")
            self.evolution.current_difficulty = DifficultyLevel(diff_val)
        except Exception:
            pass

    def _append_metric(self, task_id: str, outcome: str, score: float,
                       fb_result: Dict, evo_result: Dict) -> None:
        """サイクル結果を metrics.jsonl に追記（履歴分析用）"""
        try:
            entry = {
                "ts": datetime.now().isoformat(),
                "cycle": self._cycle_count,
                "task_id": task_id,
                "outcome": outcome,
                "score": score,
                "difficulty": self.evolution.current_difficulty.value,
                "skills_total": len(self.evolution.skills),
                "integration_score": (fb_result.get("integration") or {}).get("score"),
                "consistency_score": (fb_result.get("consistency") or {}).get("score"),
                "new_skills": len((evo_result.get("new_skills") or [])),
                "success_rate": self.observer.get_stats().get("success_rate", 0),
            }
            with self._lock:
                with open(self._metrics_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass

    # ═══════════════════════════════════════════════════════
    # 設定
    # ═══════════════════════════════════════════════════════
    @staticmethod
    def _load_config(path: Optional[Path] = None) -> Dict[str, Any]:
        cfg_path = path or (_DIR / "config.json")
        if cfg_path.exists():
            with open(cfg_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
