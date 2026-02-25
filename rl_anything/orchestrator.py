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

        return result

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
