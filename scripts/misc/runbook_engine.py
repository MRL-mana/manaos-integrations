#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Runbook 実行エンジン（L4 用）
スケジュール・steps 実行・監査ログ。autonomy_system から呼び出す。
"""

from __future__ import annotations

import json
from datetime import datetime, date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx


def _cron_next_run_ok(schedule: str, last_run_iso: Optional[str]) -> bool:
    """
    次回実行時刻を過ぎているか。
    croniter が利用可能なら厳密に cron 解釈、否则は簡易ロジックで判定。
    """
    now = datetime.now()
    if not last_run_iso:
        return True

    try:
        from croniter import croniter
    except ImportError:
        return _cron_next_run_ok_fallback(schedule, last_run_iso)

    try:
        last = datetime.fromisoformat(last_run_iso.replace("Z", ""))
        if last.tzinfo:
            last = last.replace(tzinfo=None)
    except Exception:
        return True

    try:
        it = croniter(schedule, last)
        next_run = it.get_next(datetime)
        return now >= next_run
    except Exception:
        return _cron_next_run_ok_fallback(schedule, last_run_iso)


def _cron_next_run_ok_fallback(schedule: str, last_run_iso: Optional[str]) -> bool:
    """croniter なし時の簡易判定"""
    now = datetime.now()
    if not last_run_iso:
        return True
    try:
        last = datetime.fromisoformat(last_run_iso.replace("Z", ""))
        if last.tzinfo:
            last = last.replace(tzinfo=None)
    except Exception:
        return True
    elapsed_min = (now - last).total_seconds() / 60
    parts = schedule.strip().split()
    if len(parts) < 5:
        return elapsed_min >= 60
    minute = parts[0]
    if minute.startswith("*/"):
        n = int(minute[2:])
        return elapsed_min >= n
    return elapsed_min >= 60


def _load_runbook_state(config: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    base = Path(config.get("budget_usage_dir", Path(__file__).parent))
    path = base / "autonomy_runbook_state.json"
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_runbook_state(config: Dict[str, Any], state: Dict[str, Dict[str, Any]]) -> None:
    base = Path(config.get("budget_usage_dir", Path(__file__).parent))
    path = base / "autonomy_runbook_state.json"
    base.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def load_runbooks(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """config/runbooks/*.json から runbooks_enabled に含まれる Runbook を読み込む"""
    enabled = config.get("runbooks_enabled") or []
    if not enabled:
        return []
    base = Path(__file__).parent / "config" / "runbooks"
    if not base.exists():
        return []
    runbooks = []
    for p in base.glob("*.json"):
        if p.name.lower() == "readme.json":
            continue
        try:
            with open(p, "r", encoding="utf-8") as f:
                rb = json.load(f)
            if rb.get("id") in enabled:
                runbooks.append(rb)
        except Exception:
            continue
    return runbooks


def is_runbook_due(
    runbook: Dict[str, Any],
    state: Dict[str, Dict[str, Any]],
    config: Dict[str, Any],
) -> bool:
    """スケジュール・日次上限・quiet_hours を考慮して実行可能か"""
    rid = runbook.get("id")
    if not rid:
        return False
    conditions = runbook.get("conditions") or {}
    schedule = conditions.get("schedule", "0 * * * *")
    max_daily = conditions.get("max_daily_runs", 24)
    quiet_skip = conditions.get("quiet_hours_skip", True)

    if quiet_skip:
        try:
            from autonomy_gates import is_quiet_hours

            if is_quiet_hours(config):
                return False
        except ImportError:
            pass

    runbook_state = state.get(rid) or {}
    last_run = runbook_state.get("last_run")
    runs_today = runbook_state.get("runs_today", 0)
    day_start = runbook_state.get("day_start", "")

    today = date.today().isoformat()
    if day_start != today:
        runs_today = 0
    if runs_today >= max_daily:
        return False

    return _cron_next_run_ok(schedule, last_run)


def get_runbooks_due(
    config: Dict[str, Any],
    level_int: int,
) -> List[Dict[str, Any]]:
    """L4 以上かつ runbooks_enabled に含まれ、かつ due な Runbook のリスト"""
    if level_int < 4:
        return []
    runbooks = load_runbooks(config)
    state = _load_runbook_state(config)
    due = []
    for rb in runbooks:
        if is_runbook_due(rb, state, config):
            due.append(rb)
    return due


def _audit_runbook(
    config: Dict[str, Any],
    runbook_id: str,
    step_order: Optional[int],
    result: str,
    message: str = "",
    level: int = 4,
) -> None:
    try:
        from autonomy_gates import audit_log

        audit_log(
            config,
            plan_id=runbook_id,
            action_id=f"step_{step_order}" if step_order is not None else "runbook",
            tool_name="runbook",
            action_class="runbook",
            result=result,
            message=message,
            level=level,
        )
    except ImportError:
        pass


def execute_runbook_step(
    step: Dict[str, Any],
    runbook: Dict[str, Any],
    runbook_id: str,
    orchestrator_url: str,
    config: Dict[str, Any],
    step_results: List[Dict[str, Any]],
) -> Tuple[str, Optional[str], Dict[str, Any]]:
    """
    1 ステップ実行。戻り値 (result, error_message, extra)。
    result: success | failed | skipped。extra は step_results にマージする情報（例: mark_bridge_down）
    """
    action = step.get("action", "tool")
    on_failure = step.get("on_failure", "log_and_stop")

    if action == "condition":
        cond = step.get("condition_type", "")
        if cond == "any_device_unhealthy":
            for r in step_results:
                if r.get("status") != "success":
                    continue
                data = r.get("result") or r.get("data") or {}
                if isinstance(data, dict):
                    devices = data.get("devices") or data.get("items") or []
                    for d in devices:
                        if (
                            isinstance(d, dict)
                            and str(d.get("health", d.get("status", ""))).lower() != "healthy"
                        ):
                            return "success", None, {}
            return "skipped", "condition not met: no unhealthy device", {}
        if cond == "bridge_down":
            for r in step_results:
                if r.get("mark_bridge_down"):
                    return "success", None, {}
            return "skipped", "condition not met: bridge not down", {}
        return "success", None, {}

    runbook_safety = runbook.get("safety") or {}
    runbook_flags = config.get("runbook_flags") or {}

    if action == "tool":
        tool_name = step.get("tool_name", "")
        params = step.get("params") or {}
        text = f"ツール {tool_name} を実行してください。"
        if params:
            text += f" パラメータ: {json.dumps(params, ensure_ascii=False)}"
    elif action == "orchestrator":
        text = step.get("text", "")
        if not text:
            return "skipped", "empty orchestrator text", {}
        flag_key = runbook_safety.get("recovery_requires_runbook_flag")
        if flag_key and flag_key in runbook_flags:
            allowed = runbook_flags.get(flag_key, False)
            text += " （自動復旧は" + (
                "許可されています。"
                if allowed
                else "許可されていません。提案のみにしてください。）"
            )
    else:
        return "skipped", f"unknown action: {action}", {}

    timeout = 120
    try:
        resp = httpx.post(
            f"{orchestrator_url}/api/execute",
            json={
                "text": text,
                "mode": step.get("mode", "auto"),
                "auto_evaluate": True,
                "save_to_memory": False,
            },
            timeout=timeout,
        )
        if resp.status_code == 200:
            return "success", None, {}
        err_msg = f"HTTP {resp.status_code}: {resp.text[:200]}"
        extra = {"mark_bridge_down": True} if on_failure == "mark_bridge_down" else {}
        return "failed", err_msg, extra
    except Exception as e:
        err_msg = str(e)[:200]
        extra = {"mark_bridge_down": True} if on_failure == "mark_bridge_down" else {}
        if on_failure == "log_and_continue":
            return "failed", err_msg, extra
        return "failed", err_msg, extra


def execute_runbook(
    runbook: Dict[str, Any],
    orchestrator_url: str,
    config: Dict[str, Any],
    level_int: int = 4,
) -> Dict[str, Any]:
    """
    Runbook を先頭から実行。監査ログを記録し、状態を更新する。
    """
    rid = runbook.get("id", "unknown")
    steps = sorted(runbook.get("steps") or [], key=lambda s: s.get("order", 0))
    step_results = []
    final_status = "success"

    _audit_runbook(config, rid, None, "start", message=runbook.get("name", ""), level=level_int)

    for step in steps:
        order = step.get("order", 0)
        result, err, extra = execute_runbook_step(
            step, runbook, rid, orchestrator_url, config, step_results
        )
        step_results.append(
            {
                "order": order,
                "status": result,
                "error": err,
                "step": step,
                **extra,
            }
        )
        _audit_runbook(
            config,
            rid,
            order,
            result,
            message=err or "",
            level=level_int,
        )
        if result == "failed" and step.get("on_failure") == "log_and_stop":
            final_status = "failed"
            break
        if result == "skipped" and step.get("action") == "condition":
            final_status = "skipped"
            break

    _audit_runbook(config, rid, None, final_status, message="runbook end", level=level_int)

    state = _load_runbook_state(config)
    runbook_state = state.get(rid) or {}
    today = date.today().isoformat()
    if runbook_state.get("day_start") != today:
        runbook_state["runs_today"] = 1
    else:
        runbook_state["runs_today"] = runbook_state.get("runs_today", 0) + 1
    runbook_state["day_start"] = today
    runbook_state["last_run"] = datetime.now().isoformat()
    state[rid] = runbook_state
    _save_runbook_state(config, state)

    return {
        "runbook_id": rid,
        "status": final_status,
        "steps": step_results,
    }


def run_runbooks_due(
    orchestrator_url: str,
    config: Dict[str, Any],
    level_int: int,
) -> List[Dict[str, Any]]:
    """
    Due な Runbook を順に実行し、結果のリストを返す。
    """
    due = get_runbooks_due(config, level_int)
    results = []
    for runbook in due:
        try:
            r = execute_runbook(runbook, orchestrator_url, config, level_int)
            results.append(r)
        except Exception as e:
            results.append(
                {
                    "runbook_id": runbook.get("id", "?"),
                    "status": "error",
                    "error": str(e),
                }
            )
    return results
