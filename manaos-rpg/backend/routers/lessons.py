"""Lessons & Agent Tracker エンドポイント

  GET /api/lessons/stats          — 教訓の統計情報
  GET /api/lessons/search         — 教訓検索 (?q=&category=&limit=20)
  GET /api/agents/stats           — エージェント全体統計
  GET /api/agents/list            — 全エージェントのランク一覧
  GET /api/agents/parking         — 未使用エージェント（自動パーキング候補）
  GET /api/agents/audit           — エージェントディレクトリを品質監査
"""

from __future__ import annotations

import sys
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query

# REPO_ROOT を使って scripts/misc を sys.path に追加
from core.config import REPO_ROOT

_SCRIPTS_MISC = REPO_ROOT / "scripts" / "misc"
if str(_SCRIPTS_MISC) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_MISC))

try:
    from lessons_recorder import get_lessons_recorder
    _HAS_LESSONS = True
except ImportError:
    _HAS_LESSONS = False

try:
    from agent_tracker import get_agent_tracker
    _HAS_AGENTS = True
except ImportError:
    _HAS_AGENTS = False

router = APIRouter(prefix="/api", tags=["lessons"])
_log = logging.getLogger("manaos.rpg.lessons")


# ─────────────────────────────────────────────
# /api/lessons/*
# ─────────────────────────────────────────────

@router.get("/lessons/stats")
async def lessons_stats() -> Dict[str, Any]:
    """教訓の統計情報。lessons_recorder が無ければ degraded を返す。"""
    if not _HAS_LESSONS:
        return {"status": "unavailable", "detail": "lessons_recorder not found"}
    try:
        recorder = get_lessons_recorder()
        return {"status": "ok", **recorder.stats()}
    except Exception as e:
        _log.warning("lessons_stats error: %s", e)
        return {"status": "error", "detail": str(e)}


@router.get("/lessons/search")
async def lessons_search(
    q: Optional[str] = Query(None, description="検索キーワード"),
    category: Optional[str] = Query(None, description="カテゴリ絞り込み"),
    limit: int = Query(50, ge=1, le=200),
) -> Dict[str, Any]:
    """教訓を検索して返す。"""
    if not _HAS_LESSONS:
        return {"status": "unavailable", "items": []}
    try:
        recorder = get_lessons_recorder()
        results = recorder.search_lessons(query=q or "", category=category, limit=limit)
        items = [
            {
                "id": r.id,
                "instruction": r.instruction,
                "category": r.category,
                "created_at": r.created_at,
                "count": getattr(r, "count", 1),
            }
            for r in results
        ]
        return {"status": "ok", "total": len(items), "items": items}
    except Exception as e:
        _log.warning("lessons_search error: %s", e)
        return {"status": "error", "items": [], "detail": str(e)}


# ─────────────────────────────────────────────
# /api/agents/*
# ─────────────────────────────────────────────

@router.get("/agents/stats")
async def agents_stats() -> Dict[str, Any]:
    """エージェント全体の統計情報。"""
    if not _HAS_AGENTS:
        return {"status": "unavailable", "detail": "agent_tracker not found"}
    try:
        tracker = get_agent_tracker()
        return {"status": "ok", **tracker.stats()}
    except Exception as e:
        _log.warning("agents_stats error: %s", e)
        return {"status": "error", "detail": str(e)}


@router.get("/agents/list")
async def agents_list() -> Dict[str, Any]:
    """全エージェントのランク一覧。"""
    if not _HAS_AGENTS:
        return {"status": "unavailable", "items": []}
    try:
        tracker = get_agent_tracker()
        all_agents: List[Any] = tracker.list_all_ranks()
        items = [
            {
                "name": a.agent_name,
                "rank": a.rank,
                "total_uses": a.total_uses,
                "last_used": getattr(a, "last_used_at", None),
                "last_task": getattr(a, "last_task_summary", ""),
            }
            for a in all_agents
        ]
        return {"status": "ok", "total": len(items), "items": items}
    except Exception as e:
        _log.warning("agents_list error: %s", e)
        return {"status": "error", "items": [], "detail": str(e)}


@router.get("/agents/parking")
async def agents_parking() -> Dict[str, Any]:
    """30日未使用のパーキング候補エージェント一覧。"""
    if not _HAS_AGENTS:
        return {"status": "unavailable", "items": []}
    try:
        tracker = get_agent_tracker()
        candidates: List[Any] = tracker.get_parking_candidates()
        items = [
            {
                "name": a.agent_name,
                "rank": a.rank,
                "total_uses": a.total_uses,
                "last_used": getattr(a, "last_used_at", None),
            }
            for a in candidates
        ]
        return {"status": "ok", "total": len(items), "items": items}
    except Exception as e:
        _log.warning("agents_parking error: %s", e)
        return {"status": "error", "items": [], "detail": str(e)}


@router.get("/agents/audit")
async def agents_audit(
    agents_dir: Optional[str] = Query(None, description="監査対象ディレクトリ（省略時: REPO_ROOTの.claude/agents）")
) -> Dict[str, Any]:
    """エージェントディレクトリを品質スコアで監査。"""
    if not _HAS_AGENTS:
        return {"status": "unavailable", "items": []}
    try:
        tracker = get_agent_tracker()
        target = Path(agents_dir) if agents_dir else REPO_ROOT / ".claude" / "agents"
        if not target.exists():
            return {"status": "ok", "items": [], "note": f"{target} が存在しません"}
        results: List[Any] = tracker.audit_agents_dir(str(target))
        items = [
            {
                "name": r.name,
                "score": r.score,
                "max_score": getattr(r, "max_score", 100),
                "details": getattr(r, "details", {}),
            }
            for r in results
        ]
        items.sort(key=lambda x: x["score"], reverse=True)
        return {"status": "ok", "total": len(items), "items": items}
    except Exception as e:
        _log.warning("agents_audit error: %s", e)
        return {"status": "error", "items": [], "detail": str(e)}
