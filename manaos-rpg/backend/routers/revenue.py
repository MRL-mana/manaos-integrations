"""Revenue KPI — RPGダッシュボード向け収益可視化エンドポイント

image_generation_service の /revenue/kpi を中継して
RPGフロントエンドに統合KPIを表示する。

  GET  /api/revenue/kpi      — 統合KPI (billing + quality + RL + loop_health)
  GET  /api/revenue/history   — 日次収益推移
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict

from fastapi import APIRouter

router = APIRouter(prefix="/api/revenue", tags=["revenue"])

_log = logging.getLogger("manaos.rpg.revenue")

_IMAGE_GEN_BASE = os.getenv("IMAGE_GEN_API_BASE", "http://127.0.0.1:5560")
_DEFAULT_API_KEY = os.getenv("IMAGE_GEN_API_KEY", "default")


async def _fetch_image_gen(path: str) -> dict:
    """image_generation_service に GET リクエスト"""
    import urllib.request
    import json
    try:
        url = f"{_IMAGE_GEN_BASE}{path}"
        req = urllib.request.Request(
            url,
            headers={"X-API-Key": _DEFAULT_API_KEY},
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as e:
        _log.warning("Failed to fetch %s: %s", path, e)
        return {"status": "error", "detail": str(e)}


@router.get("/kpi")
async def revenue_kpi() -> Dict[str, Any]:
    """統合KPI — image_gen の /revenue/kpi を中継"""
    data = await _fetch_image_gen("/api/v1/images/revenue/kpi")
    if data.get("status") == "error":
        # image_gen が落ちてても RPG は壊れない
        return {
            "status": "degraded",
            "billing": {"mrr_yen": 0, "daily_sales_yen": 0, "active_users_30d": 0,
                        "active_keys": 0, "plan": "unknown"},
            "quality": {"avg_rating": None, "total_feedback": 0},
            "rl": {"enabled": False, "total_cycles": 0, "success_rate": None,
                   "avg_score": None, "skills_count": 0},
            "loop_health": {"score": 0, "level": "critical",
                            "breakdown": {"revenue": 0, "users": 0,
                                          "feedback": 0, "rl_success": 0,
                                          "rl_learning": 0}},
            "error": data.get("detail", "image_gen unreachable"),
        }
    return data


@router.get("/history")
async def revenue_history() -> Dict[str, Any]:
    """日次収益推移 — billing DB から直接取得（将来実装）"""
    # TODO: billing DB の usage_daily テーブルから日次推移を取得
    return {
        "status": "ok",
        "days": [],
        "hint": "Revenue history will be populated as transactions accumulate",
    }
