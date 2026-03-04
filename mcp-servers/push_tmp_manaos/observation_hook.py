#!/usr/bin/env python3
"""
Phase 1: 観測フック (Observation Hook)
======================================
post_tool_use_hook に相当する機構。エージェントの全行動をログに記録する。

使い方:
  from rl_anything.observation_hook import ObservationHook
  hook = ObservationHook()

  # ツール使用前
  hook.on_tool_start(tool_name, params)

  # ツール使用後
  hook.on_tool_end(tool_name, result, error=None)

  # タスク開始 / 終了
  hook.on_task_start(task_id, description)
  hook.on_task_end(task_id, outcome, score=None)
"""

from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .types import TaskOutcome, TaskRecord, ToolAction

_DIR = Path(__file__).parent
_DEFAULT_LOG_DIR = _DIR.parent / "logs" / "rl_anything"


class ObservationHook:
    """Phase 1: 全行動の観測・ログ収集"""

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        log_dir: Optional[Path] = None,
    ):
        cfg = config or self._load_config()
        obs_cfg = cfg.get("observation", {})

        self.enabled: bool = obs_cfg.get("enabled", True)
        self.log_dir: Path = Path(log_dir or obs_cfg.get("log_dir", str(_DEFAULT_LOG_DIR)))
        self.max_entries: int = obs_cfg.get("max_log_entries", 10000)
        self.log_params: bool = obs_cfg.get("log_tool_params", True)
        self.preview_chars: int = obs_cfg.get("log_result_preview_chars", 500)

        self.log_dir.mkdir(parents=True, exist_ok=True)

        # 進行中タスクの管理
        self._active_tasks: Dict[str, TaskRecord] = {}
        self._completed_records: List[TaskRecord] = []
        self._pending_action: Optional[Dict[str, Any]] = None

        # ファイルロック
        self._lock = threading.Lock()

        # コールバック (外部連携用)
        self.on_action_logged: Optional[Callable[[ToolAction], None]] = None
        self.on_task_completed: Optional[Callable[[TaskRecord], None]] = None

        # 既存ログの読み込み
        self._load_existing_records()

    # ─────────────────── パブリック API ───────────────────
    def on_task_start(self, task_id: str, description: str, difficulty: str = "standard") -> None:
        """タスク開始を記録"""
        if not self.enabled:
            return
        from .types import DifficultyLevel
        record = TaskRecord(
            task_id=task_id,
            description=description,
            difficulty=DifficultyLevel(difficulty),
        )
        with self._lock:
            self._active_tasks[task_id] = record
        self._append_event("task_start", {
            "task_id": task_id,
            "description": description,
            "difficulty": difficulty,
        })

    def on_tool_start(self, tool_name: str, params: Dict[str, Any], task_id: Optional[str] = None) -> None:
        """ツール使用開始"""
        if not self.enabled:
            return
        self._pending_action = {
            "tool_name": tool_name,
            "params": params if self.log_params else {},
            "task_id": task_id or self._infer_active_task_id(),
            "start_ms": time.time() * 1000,
        }

    def on_tool_end(
        self,
        tool_name: str,
        result: Any = None,
        error: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> None:
        """ツール使用完了 (post_tool_use_hook)"""
        if not self.enabled:
            return

        # 所要時間の計算
        duration_ms = None
        params: Dict[str, Any] = {}
        if self._pending_action and self._pending_action.get("tool_name") == tool_name:
            duration_ms = time.time() * 1000 - self._pending_action["start_ms"]
            params = self._pending_action.get("params", {})
            task_id = task_id or self._pending_action.get("task_id")
            self._pending_action = None

        # 結果のプレビュー作成
        result_str = str(result) if result is not None else ""
        result_preview = result_str[:self.preview_chars]

        action = ToolAction(
            tool_name=tool_name,
            parameters=params,
            result_summary=result_preview,
            error=error,
            duration_ms=duration_ms,
        )

        # アクティブタスクに追加
        tid = task_id or self._infer_active_task_id()
        if tid and tid in self._active_tasks:
            with self._lock:
                self._active_tasks[tid].actions.append(action)

        # イベントログ
        self._append_event("tool_use", {
            "tool_name": tool_name,
            "task_id": tid,
            "error": error,
            "duration_ms": duration_ms,
            "result_preview": result_preview[:200],
        })

        # コールバック
        if self.on_action_logged:
            try:
                self.on_action_logged(action)
            except Exception:
                pass

    def on_intermediate_score(self, task_id: str, score: float, reason: str = "") -> None:
        """途中経過のスコアを記録 (統合フィードバック用)"""
        if not self.enabled:
            return
        if task_id in self._active_tasks:
            with self._lock:
                self._active_tasks[task_id].intermediate_scores.append(score)
        self._append_event("intermediate_score", {
            "task_id": task_id,
            "score": score,
            "reason": reason,
        })

    def on_task_end(
        self,
        task_id: str,
        outcome: str = "unknown",
        final_score: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TaskRecord:
        """タスク終了を記録"""
        record = self._active_tasks.pop(task_id, None)
        if record is None:
            # 未登録タスクでも記録可能
            record = TaskRecord(task_id=task_id, description="(unregistered)")

        record.outcome = TaskOutcome(outcome)
        record.final_score = final_score
        record.end_time = datetime.now().isoformat()
        if metadata:
            record.metadata.update(metadata)

        with self._lock:
            self._completed_records.append(record)
            # 上限管理
            if len(self._completed_records) > self.max_entries:
                self._completed_records = self._completed_records[-self.max_entries:]

        # 永続化
        self._save_record(record)

        self._append_event("task_end", {
            "task_id": task_id,
            "outcome": outcome,
            "final_score": final_score,
            "action_count": len(record.actions),
        })

        # コールバック
        if self.on_task_completed:
            try:
                self.on_task_completed(record)
            except Exception:
                pass

        return record

    def get_active_tasks(self) -> List[str]:
        return list(self._active_tasks.keys())

    def get_completed_records(self, limit: int = 50) -> List[TaskRecord]:
        return self._completed_records[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """観測統計を返す"""
        total = len(self._completed_records)
        if total == 0:
            return {"total": 0, "success_rate": 0.0}
        successes = sum(1 for r in self._completed_records if r.outcome == TaskOutcome.SUCCESS)
        return {
            "total": total,
            "successes": successes,
            "failures": total - successes,
            "success_rate": round(successes / total, 4),
            "active_tasks": len(self._active_tasks),
            "avg_actions_per_task": round(
                sum(len(r.actions) for r in self._completed_records) / total, 1
            ),
        }

    # ─────────────────── 内部メソッド ───────────────────
    @staticmethod
    def _load_config() -> Dict[str, Any]:
        cfg_path = _DIR / "config.json"
        if cfg_path.exists():
            with open(cfg_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _infer_active_task_id(self) -> Optional[str]:
        """進行中タスクが 1 つならそれを返す"""
        tasks = list(self._active_tasks.keys())
        return tasks[0] if len(tasks) == 1 else None

    def _append_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """イベントを JSONL ファイルに追記"""
        entry = {
            "ts": datetime.now().isoformat(),
            "event": event_type,
            **data,
        }
        log_file = self.log_dir / f"events_{datetime.now().strftime('%Y-%m-%d')}.jsonl"
        try:
            with self._lock:
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass  # ログ書き込み失敗は無視

    def _save_record(self, record: TaskRecord) -> None:
        """完了したタスクを JSONL に保存"""
        records_file = self.log_dir / "completed_tasks.jsonl"
        try:
            with open(records_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
        except Exception:
            pass

    def _load_existing_records(self) -> None:
        """起動時に既存の完了タスクを読み込む"""
        records_file = self.log_dir / "completed_tasks.jsonl"
        if not records_file.exists():
            return
        try:
            with open(records_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    data = json.loads(line)
                    record = TaskRecord(
                        task_id=data.get("task_id", ""),
                        description=data.get("description", ""),
                        outcome=TaskOutcome(data.get("outcome", "unknown")),
                        final_score=data.get("final_score"),
                        difficulty=__import__("rl_anything.types", fromlist=["DifficultyLevel"]).DifficultyLevel(
                            data.get("difficulty", "standard")
                        ),
                        start_time=data.get("start_time", ""),
                        end_time=data.get("end_time"),
                    )
                    self._completed_records.append(record)
            # 上限
            if len(self._completed_records) > self.max_entries:
                self._completed_records = self._completed_records[-self.max_entries:]
        except Exception:
            pass
