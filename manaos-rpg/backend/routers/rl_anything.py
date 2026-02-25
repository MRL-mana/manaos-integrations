"""RLAnything API — ダッシュボード & タスクイベント受信エンドポイント

  GET  /api/rl/dashboard  — 全体ステータス
  GET  /api/rl/skills     — 学習済みスキル一覧
  POST /api/rl/task/begin — タスク開始
  POST /api/rl/task/end   — タスク終了 (自動進化トリガー)
  POST /api/rl/tool       — ツール使用記録
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel

from fastapi import APIRouter, Body

# rl_anything パッケージへの PATH 追加
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent  # backend -> manaos-rpg -> manaos_integrations
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

router = APIRouter(prefix="/api/rl", tags=["rl_anything"])

# ── 遅延シングルトン ──────────────────────────────────
_rl = None


def _get_rl():
    global _rl
    if _rl is None:
        try:
            from rl_anything.orchestrator import RLAnythingOrchestrator

            _rl = RLAnythingOrchestrator()
        except Exception as e:
            raise RuntimeError(f"RLAnything init failed: {e}")
    return _rl


# ═══════════════════════════════════════════════════════
# GET エンドポイント
# ═══════════════════════════════════════════════════════

@router.get("/dashboard")
def dashboard() -> Dict[str, Any]:
    """システム全体のステータスダッシュボード"""
    try:
        return {"ok": True, **_get_rl().get_dashboard()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/skills")
def skills() -> Dict[str, Any]:
    """学習済みスキル一覧"""
    try:
        rl = _get_rl()
        return {
            "ok": True,
            "skills": [s.to_dict() for s in rl.evolution.skills],
            "prompt": rl.get_skills_for_prompt(),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ═══════════════════════════════════════════════════════
# POST エンドポイント
# ═══════════════════════════════════════════════════════

@router.post("/task/begin")
def task_begin(
    task_id: str = Body(...),
    description: str = Body(""),
    difficulty: Optional[str] = Body(None),
) -> Dict[str, Any]:
    """タスク開始"""
    try:
        _get_rl().begin_task(task_id, description, difficulty=difficulty)
        return {"ok": True, "task_id": task_id}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/task/end")
def task_end(
    task_id: str = Body(...),
    outcome: str = Body("unknown"),
    score: Optional[float] = Body(None),
    metadata: Optional[Dict[str, Any]] = Body(None),
) -> Dict[str, Any]:
    """タスク終了 → 自動進化トリガー"""
    try:
        result = _get_rl().end_task(task_id, outcome=outcome, score=score, metadata=metadata)
        return {"ok": True, **result}
    except Exception as e:
        return {"ok": False, "error": str(e), "trace": traceback.format_exc()}


@router.post("/tool")
def log_tool(
    tool_name: str = Body(...),
    params: Optional[Dict[str, Any]] = Body(None),
    result: Optional[str] = Body(None),
    error: Optional[str] = Body(None),
    task_id: Optional[str] = Body(None),
) -> Dict[str, Any]:
    """ツール使用記録 (post_tool_use_hook 相当)"""
    try:
        _get_rl().log_tool(tool_name, params=params, result=result, error=error, task_id=task_id)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/score")
def score_intermediate(
    task_id: str = Body(...),
    score: float = Body(...),
    reason: str = Body(""),
) -> Dict[str, Any]:
    """中間スコア記録"""
    try:
        _get_rl().score_intermediate(task_id, score, reason)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ═══════════════════════════════════════════════════════
# 履歴 / 管理エンドポイント (round 3)
# ═══════════════════════════════════════════════════════

@router.get("/history")
def history(limit: int = 50) -> Dict[str, Any]:
    """直近のサイクル履歴 (metrics.jsonl)"""
    try:
        entries = _get_rl().get_history(limit=limit)
        return {"ok": True, "entries": entries, "count": len(entries)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/cleanup")
def cleanup_stale(timeout_s: Optional[float] = Body(None)) -> Dict[str, Any]:
    """放置されたタスクを自動終了"""
    try:
        result = _get_rl().cleanup_stale_tasks(timeout_s=timeout_s)
        return {"ok": True, **result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/config/reload")
def config_reload() -> Dict[str, Any]:
    """config.json を再読み込み（再起動不要）"""
    try:
        return _get_rl().reload_config()
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ═══════════════════════════════════════════════════════
# Analytics / Scheduler (round 4)
# ═══════════════════════════════════════════════════════

@router.get("/analytics")
def analytics(windows: str = "5,10,20") -> Dict[str, Any]:
    """トレンド分析（rolling success rate, score, difficulty, skill growth）"""
    try:
        w = [int(x.strip()) for x in windows.split(",") if x.strip().isdigit()]
        return {"ok": True, **_get_rl().get_analytics(windows=w or None)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


class _SchedulerStartBody(BaseModel):
    interval_s: Optional[float] = None

@router.post("/scheduler/start")
def scheduler_start(body: _SchedulerStartBody = _SchedulerStartBody()) -> Dict[str, Any]:
    """Auto-scheduler 開始"""
    try:
        return _get_rl().start_scheduler(interval_s=body.interval_s)
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/scheduler/stop")
def scheduler_stop() -> Dict[str, Any]:
    """Auto-scheduler 停止"""
    try:
        return _get_rl().stop_scheduler()
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ═══════════════════════════════════════════════════════
# Replay Buffer / Experiments / Prometheus (round 5)
# ═══════════════════════════════════════════════════════

@router.get("/replay/stats")
def replay_stats() -> Dict[str, Any]:
    """Replay Buffer 統計"""
    try:
        return {"ok": True, **_get_rl().replay.get_stats()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/replay/sample")
def replay_sample(n: int = 8, prioritized: bool = False) -> Dict[str, Any]:
    """Replay Buffer からサンプリング"""
    try:
        buf = _get_rl().replay
        batch = buf.sample_prioritized(n) if prioritized else buf.sample(n)
        return {"ok": True, "samples": [e.to_dict() for e in batch], "count": len(batch)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/experiments")
def experiments_list() -> Dict[str, Any]:
    """全 A/B 実験一覧"""
    try:
        tracker = _get_rl().experiments
        return {"ok": True, "experiments": tracker.list_experiments(), **tracker.get_stats()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


class _ExperimentCreateBody(BaseModel):
    name: str
    config_overrides: Dict[str, Any] = {}

@router.post("/experiments/create")
def experiment_create(body: _ExperimentCreateBody) -> Dict[str, Any]:
    """新規 A/B 実験を作成"""
    try:
        exp_id = _get_rl().experiments.create(body.name, body.config_overrides)
        return {"ok": True, "exp_id": exp_id}
    except Exception as e:
        return {"ok": False, "error": str(e)}


class _ExperimentRecordBody(BaseModel):
    exp_id: str
    outcome: str
    score: float
    metadata: Optional[Dict[str, Any]] = None

@router.post("/experiments/record")
def experiment_record(body: _ExperimentRecordBody) -> Dict[str, Any]:
    """A/B 実験に結果を記録"""
    try:
        ok = _get_rl().experiments.record_result(body.exp_id, body.outcome, body.score, body.metadata)
        return {"ok": ok, "exp_id": body.exp_id}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/experiments/compare")
def experiment_compare(min_samples: int = 3) -> Dict[str, Any]:
    """全 A/B 実験の横比較レポート"""
    try:
        return {"ok": True, **_get_rl().experiments.compare(min_samples=min_samples)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/experiments/best")
def experiment_best(min_samples: int = 3) -> Dict[str, Any]:
    """最良バリアントを返す"""
    try:
        best = _get_rl().experiments.get_best(min_samples=min_samples)
        return {"ok": True, "best": best}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/experiments/conclude")
def experiment_conclude(exp_id: str = Body(..., embed=True)) -> Dict[str, Any]:
    """A/B 実験を終了"""
    try:
        ok = _get_rl().experiments.conclude(exp_id)
        return {"ok": ok, "exp_id": exp_id}
    except Exception as e:
        return {"ok": False, "error": str(e)}


from fastapi.responses import PlainTextResponse

@router.get("/metrics", response_class=PlainTextResponse)
def prometheus_metrics() -> str:
    """Prometheus /metrics 互換エンドポイント"""
    try:
        return _get_rl().prom.render()
    except Exception as e:
        return f"# error: {e}\n"
