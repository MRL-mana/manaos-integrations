"""
RLAnything Bridge — 画像生成 ↔ RLAnything 評価ループ接続
==========================================================
image_generation_service が RLAnything の
begin_task / score_intermediate / end_task を呼び出す薄いラッパー。

接続パス:
  service.py → rl_bridge.py → rl_anything.orchestrator.RLAnythingOrchestrator

設計:
  - orchestrator を遅延ロードし、import 失敗時は gracefully degrade
  - 全呼び出しは try/except でガード（RL障害で生成を止めない）
  - 画像品質スコア → RLAnything の score として 0-1 正規化
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

_log = logging.getLogger("manaos.rl_bridge")

# 遅延ロード: rl_anything がインポートできない環境でも動作
_orchestrator = None
_init_attempted = False


def _get_orchestrator():
    """RLAnything Orchestrator のシングルトン取得"""
    global _orchestrator, _init_attempted
    if _init_attempted:
        return _orchestrator
    _init_attempted = True
    try:
        from rl_anything.orchestrator import RLAnythingOrchestrator
        _orchestrator = RLAnythingOrchestrator()
        _log.info("RLAnything orchestrator connected successfully")
    except Exception as e:
        _log.warning("RLAnything not available (graceful degrade): %s", e)
        _orchestrator = None
    return _orchestrator


def begin_image_task(job_id: str, prompt: str, metadata: Optional[Dict] = None) -> bool:
    """
    画像生成タスク開始をRLAnythingに通知。

    Args:
        job_id: 画像生成のジョブID
        prompt: 生成プロンプト
        metadata: 追加メタデータ

    Returns:
        True: 正常通知 / False: RL未接続 or エラー
    """
    rl = _get_orchestrator()
    if rl is None:
        return False
    try:
        description = f"Image generation: {prompt[:100]}"
        rl.begin_task(task_id=job_id, description=description)
        _log.debug("RL begin_task: %s", job_id)
        return True
    except Exception as e:
        _log.warning("RL begin_task failed (non-fatal): %s", e)
        return False


def score_image_quality(job_id: str, quality_overall: float, reason: str = "") -> bool:
    """
    品質評価の中間スコアをRLAnythingに通知。

    Args:
        job_id: ジョブID
        quality_overall: 品質スコア (0-10 → 0-1 に正規化)
        reason: スコアの根拠

    Returns:
        True: 正常通知
    """
    rl = _get_orchestrator()
    if rl is None:
        return False
    try:
        # RLAnything は 0-1 スケール、品質スコアは 0-10
        normalized = min(1.0, max(0.0, quality_overall / 10.0))
        rl.score_intermediate(task_id=job_id, score=normalized, reason=reason)
        _log.debug("RL score_intermediate: %s = %.3f", job_id, normalized)
        return True
    except Exception as e:
        _log.warning("RL score_intermediate failed (non-fatal): %s", e)
        return False


def end_image_task(
    job_id: str,
    outcome: str = "success",
    quality_overall: Optional[float] = None,
    generation_time_ms: Optional[int] = None,
    cost_yen: Optional[float] = None,
    revenue_yen: Optional[float] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """
    画像生成タスク終了をRLAnythingに通知。
    これにより自動で:
      - フィードバックサイクル
      - 進化サイクル
      - Reward Shaping
      - Policy Gradient 更新
      - Replay Buffer 蓄積
    が全て起動する。

    Args:
        job_id: ジョブID
        outcome: "success" / "failed" / "timeout"
        quality_overall: 品質スコア (0-10、None で自動計算)
        generation_time_ms: 生成時間 (ms)
        cost_yen: コスト (円)
        revenue_yen: 収益 (円) — 品質→収益ループ指標
        metadata: 追加データ

    Returns:
        RLAnything のサイクル結果 dict / None
    """
    rl = _get_orchestrator()
    if rl is None:
        return None
    try:
        score = None
        if quality_overall is not None:
            score = min(1.0, max(0.0, quality_overall / 10.0))

        meta = metadata or {}
        if generation_time_ms is not None:
            meta["generation_time_ms"] = generation_time_ms
        if cost_yen is not None:
            meta["cost_yen"] = cost_yen
        if revenue_yen is not None:
            meta["revenue_yen"] = revenue_yen
            # ROI = (収益 - コスト) / コスト — RLの reward shaping に使用
            if cost_yen and cost_yen > 0:
                meta["roi"] = round((revenue_yen - cost_yen) / cost_yen, 4)

        result = rl.end_task(
            task_id=job_id,
            outcome=outcome,
            score=score,
            metadata=meta,
        )
        _log.info(
            "RL end_task: %s outcome=%s score=%.3f cycle=%d revenue=¥%.2f",
            job_id, outcome, score or 0, result.get("cycle", 0),
            revenue_yen or 0,
        )
        return result
    except Exception as e:
        _log.warning("RL end_task failed (non-fatal): %s", e)
        return None


def log_tool_usage(tool_name: str, params: Optional[Dict] = None,
                   result: Any = None, job_id: Optional[str] = None) -> bool:
    """ツール使用をRLAnythingに記録（ComfyUI呼び出し等）"""
    rl = _get_orchestrator()
    if rl is None:
        return False
    try:
        rl.log_tool(tool_name=tool_name, params=params, result=result, task_id=job_id)
        return True
    except Exception as e:
        _log.warning("RL log_tool failed (non-fatal): %s", e)
        return False


def get_rl_dashboard() -> Optional[Dict[str, Any]]:
    """RLAnything ダッシュボードデータ取得"""
    rl = _get_orchestrator()
    if rl is None:
        return None
    try:
        return rl.get_dashboard()
    except Exception as e:
        _log.warning("RL get_dashboard failed: %s", e)
        return None
