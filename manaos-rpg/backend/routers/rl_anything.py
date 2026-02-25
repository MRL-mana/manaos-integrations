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
