#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自律レベルゲート：Action Class・レベル別許可・Confirm Token・予算・監査

自律レベル = 権限セット（Scope + Guards）
- Scope: 通知だけ / 調査まで / 実行まで / 破壊的操作まで
- Guards: キー種別・Confirm Token・時間帯・予算・dry-run・監査
"""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, Set

# ---------------------------------------------------------------------------
# Action Class（C0〜C4）
# ---------------------------------------------------------------------------


class ActionClass(str, Enum):
    """アクション分類。レベルごとに許可するクラスを固定。"""

    C0 = "C0"  # Read-only: GET/status/search
    C1 = "C1"  # Append-only: Obsidian/Rows 追記
    C2 = "C2"  # Reversible: タグ付け・移動・n8n安全WF
    C3 = "C3"  # Costly: LLM大量・画像/動画生成・外部課金
    C4 = "C4"  # Destructive: Docker・削除・上書き・停止


# 重要操作は Confirm Token 必須
REQUIRE_CONFIRM_TOKEN_CLASSES: Set[ActionClass] = {ActionClass.C3, ActionClass.C4}


# ---------------------------------------------------------------------------
# レベル別 許可 Action Class（L0〜L6）
# ---------------------------------------------------------------------------

LEVEL_ALLOWED_ACTION_CLASSES: Dict[int, Set[ActionClass]] = {
    0: set(),  # L0 OFF: なし
    1: {ActionClass.C0},  # L1 Observe: 観測のみ
    2: {ActionClass.C0, ActionClass.C1},  # L2 Notify: + 追記・通知
    3: {ActionClass.C0, ActionClass.C1, ActionClass.C2},  # L3 Assist
    4: {ActionClass.C0, ActionClass.C1, ActionClass.C2},  # L4 Act: Runbook 内 C2 まで
    5: {ActionClass.C0, ActionClass.C1, ActionClass.C2},  # L5 Autopilot
    6: {  # L6 Ops: 全許可（運用時のみ）
        ActionClass.C0,
        ActionClass.C1,
        ActionClass.C2,
        ActionClass.C3,
        ActionClass.C4,
    },
}


# ---------------------------------------------------------------------------
# MCP ツール名 → Action Class マッピング
# ---------------------------------------------------------------------------

TOOL_ACTION_CLASS: Dict[str, ActionClass] = {
    # C0 Read-only
    "device_discover": ActionClass.C0,
    "device_get_status": ActionClass.C0,
    "device_get_health": ActionClass.C0,
    "device_get_resources": ActionClass.C0,
    "device_get_alerts": ActionClass.C0,
    "cache_stats": ActionClass.C0,
    "performance_stats": ActionClass.C0,
    "phase1_aggregate": ActionClass.C0,
    "phase1_compare_on_off": ActionClass.C0,
    "phase1_low_sat_history_view": ActionClass.C0,
    "phase2_get_memos": ActionClass.C0,
    "phase2_memo_summary": ActionClass.C0,
    "obsidian_search_notes": ActionClass.C0,
    "rows_query": ActionClass.C0,
    "rows_list_spreadsheets": ActionClass.C0,
    "file_secretary_inbox_status": ActionClass.C0,
    "moltbot_health": ActionClass.C0,
    "moltbot_get_result": ActionClass.C0,
    "n8n_list_workflows": ActionClass.C0,
    "konoha_health": ActionClass.C0,
    "nanokvm_console_url": ActionClass.C0,
    "nanokvm_health": ActionClass.C0,
    "voice_health": ActionClass.C0,
    "github_search": ActionClass.C0,
    "github_commits": ActionClass.C0,
    "research_status": ActionClass.C0,
    "openwebui_list_chats": ActionClass.C0,
    "openwebui_list_models": ActionClass.C0,
    "openwebui_get_chat": ActionClass.C0,
    "personality_get_persona": ActionClass.C0,
    "personality_get_prompt": ActionClass.C0,
    "learning_get_preferences": ActionClass.C0,
    "learning_get_optimizations": ActionClass.C0,
    "autonomy_list_tasks": ActionClass.C0,
    "autonomy_get_level": ActionClass.C0,
    "memory_recall": ActionClass.C0,
    "civitai_get_favorites": ActionClass.C0,
    "civitai_get_images": ActionClass.C0,
    "civitai_get_image_details": ActionClass.C0,
    "civitai_get_creators": ActionClass.C0,
    "image_stock_search": ActionClass.C0,
    "svi_get_queue_status": ActionClass.C0,
    "pixel7_get_resources": ActionClass.C0,
    "pixel7_get_apps": ActionClass.C0,
    "pixel7_screenshot": ActionClass.C0,
    "mothership_get_resources": ActionClass.C0,
    "x280_get_resources": ActionClass.C0,
    "google_drive_list_files": ActionClass.C0,
    "web_search": ActionClass.C0,
    "web_search_simple": ActionClass.C0,
    "brave_search": ActionClass.C0,
    "brave_search_simple": ActionClass.C0,
    # C1 Append-only
    "obsidian_create_note": ActionClass.C1,
    "rows_send_data": ActionClass.C1,
    "memory_store": ActionClass.C1,
    "notification_send": ActionClass.C1,
    "learning_record": ActionClass.C1,
    "phase1_low_sat_archive": ActionClass.C1,
    "phase2_backfill_memos": ActionClass.C1,
    # C2 Reversible
    "file_secretary_organize": ActionClass.C2,
    "moltbot_submit_plan": ActionClass.C2,
    "phase2_auto_cleanup": ActionClass.C2,
    "personality_update": ActionClass.C2,
    "secretary_morning_routine": ActionClass.C2,
    "secretary_noon_routine": ActionClass.C2,
    "secretary_evening_routine": ActionClass.C2,
    "secretary_file_organize": ActionClass.C2,
    "learning_analyze": ActionClass.C2,
    # C3 Costly
    "llm_chat": ActionClass.C3,
    "base_ai_chat": ActionClass.C3,
    "openwebui_create_chat": ActionClass.C3,
    "openwebui_send_message": ActionClass.C3,
    "research_quick": ActionClass.C3,
    "comfyui_generate_image": ActionClass.C3,
    "svi_generate_video": ActionClass.C3,
    "svi_extend_video": ActionClass.C3,
    "generate_sd_prompt": ActionClass.C3,
    "voice_synthesize": ActionClass.C3,
    "pixel7_tts": ActionClass.C3,
    "pixel7_transcribe": ActionClass.C3,
    "google_drive_upload": ActionClass.C3,
    "civitai_download_favorites": ActionClass.C3,
    "image_stock_add": ActionClass.C3,
    # C4 Destructive
    "n8n_execute_workflow": ActionClass.C4,
    "pixel7_execute": ActionClass.C4,
    "pixel7_push_file": ActionClass.C4,
    "pixel7_pull_file": ActionClass.C4,
    "mothership_execute": ActionClass.C4,
    "x280_execute": ActionClass.C4,
    "phase1_run_off_3rounds": ActionClass.C4,
    "phase1_run_on_rounds": ActionClass.C4,
    "phase1_run_extended": ActionClass.C4,
    "phase1_save_run": ActionClass.C4,
    "phase1_phase2_full_run": ActionClass.C4,
    "phase1_run_multi_thread": ActionClass.C4,
    "phase1_low_satisfaction": ActionClass.C4,
    "phase1_weekly_report": ActionClass.C4,
    "phase2_dedup_memos": ActionClass.C4,
    "autonomy_add_task": ActionClass.C4,
    "autonomy_execute_tasks": ActionClass.C4,
    "personality_apply": ActionClass.C4,
    "openwebui_update_settings": ActionClass.C4,
    # 未定義ツールは C4 扱いのため、以下は明示登録（VSCode/Pico HID）
    "vscode_open_file": ActionClass.C2,
    "vscode_open_folder": ActionClass.C2,
    "vscode_search_files": ActionClass.C0,
    "vscode_execute_command": ActionClass.C4,
    "pico_hid_mouse_move": ActionClass.C4,
    "pico_hid_mouse_click": ActionClass.C4,
    "pico_hid_key_press": ActionClass.C4,
    "pico_hid_type_text": ActionClass.C4,
    "pico_hid_scroll": ActionClass.C4,
    "pico_hid_mouse_move_absolute": ActionClass.C4,
    "pico_hid_mouse_click_at": ActionClass.C4,
    "pico_hid_key_combo": ActionClass.C4,
    "pico_hid_mouse_position": ActionClass.C0,
    "pico_hid_screen_size": ActionClass.C0,
    "pico_hid_screenshot": ActionClass.C0,
    "pico_hid_type_text_auto": ActionClass.C4,
    "pico_hid_clear_and_retype_auto": ActionClass.C4,
    "pico_hid_click_then_type_auto": ActionClass.C4,
}


def get_action_class_for_tool(tool_name: str) -> ActionClass:
    """ツール名から Action Class を返す。未定義は C4 として扱う（安全側）。"""
    return TOOL_ACTION_CLASS.get(tool_name, ActionClass.C4)


def get_usage_key_for_tool(tool_name: str) -> Optional[str]:
    """
    コスト予算の usage_key を返す。
    - llm_calls: LLM / テキスト系
    - image_jobs: 画像生成・画像追加
    - video_jobs: 動画生成
    その他のツールは None（予算カウント対象外）
    """
    c3_llm = {
        "llm_chat",
        "base_ai_chat",
        "openwebui_create_chat",
        "openwebui_send_message",
        "research_quick",
        "generate_sd_prompt",
        "web_search",
        "web_search_simple",
        "brave_search",
        "brave_search_simple",
    }
    c3_image = {
        "comfyui_generate_image",
        "image_stock_add",
        "civitai_download_favorites",
    }
    c3_video = {
        "svi_generate_video",
        "svi_extend_video",
    }
    if tool_name in c3_llm:
        return "llm_calls"
    if tool_name in c3_image:
        return "image_jobs"
    if tool_name in c3_video:
        return "video_jobs"
    return None


def is_confirm_token_required(action_class: ActionClass) -> bool:
    """当該 Action Class で Confirm Token が必須か"""
    return action_class in REQUIRE_CONFIRM_TOKEN_CLASSES


def action_allowed_at_level(level: int, action_class: ActionClass) -> bool:
    """指定レベルで当該 Action Class が許可されているか"""
    if level < 0 or level > 6:
        return False
    return action_class in LEVEL_ALLOWED_ACTION_CLASSES.get(level, set())


def check_gate(
    level: int,
    tool_name: str,
    confirm_token: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
) -> tuple[bool, str]:
    """
    Gate A + B をまとめてチェック。

    Returns:
        (allowed: bool, reason: str)
    """
    config = config or {}
    action_class = get_action_class_for_tool(tool_name)

    if not action_allowed_at_level(level, action_class):
        return False, (
            f"レベル L{level} では {action_class.value} は許可されていません"
            f"（ツール: {tool_name}）"
        )

    if is_confirm_token_required(action_class):
        required = config.get("require_confirm_token_classes", ["C3", "C4"])
        if action_class.value in required and not confirm_token:
            return False, f"{action_class.value} は Confirm Token が必須です（ツール: {tool_name}）"
        if confirm_token and not _verify_confirm_token(confirm_token, config):
            return False, "Confirm Token が無効または期限切れです"

    return True, ""


def _verify_confirm_token(token: str, config: Dict[str, Any]) -> bool:
    """
    Confirm Token を検証する。
    1) 時間ベース HMAC（confirm_token_hmac_secret が設定されている場合）
    2) 固定 allowlist（confirm_tokens_allowlist）
    """
    if not token or not token.strip():
        return False
    token = token.strip()
    allowlist = config.get("confirm_tokens_allowlist") or []
    if token in allowlist:
        return True
    secret = config.get("confirm_token_hmac_secret")
    if secret:
        window_sec = int(config.get("confirm_token_hmac_window_seconds", 300))
        if verify_hmac_confirm_token(token, secret, window_sec):
            return True
    return False


def generate_hmac_confirm_token(secret: str, window_seconds: int = 300) -> str:
    """
    時間ベースの Confirm Token を生成する。
    window_seconds ごとに同じトークンが生成される（例: 300 で5分窓）。
    """
    if not secret:
        raise ValueError("confirm_token_hmac_secret is required")
    window = int(datetime.now().timestamp() // window_seconds)
    msg = str(window).encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()
    return f"hmac_{window}_{sig[:16]}"


def verify_hmac_confirm_token(token: str, secret: str, window_seconds: int = 300) -> bool:
    """
    時間ベース HMAC Confirm Token を検証する。
    現在窓・前1窓・後1窓を許容（時計ずれ対策）。
    """
    if not token or not token.startswith("hmac_") or not secret:
        return False
    parts = token.split("_")
    if len(parts) != 3:
        return False
    try:
        window = int(parts[1])
        sig_got = parts[2]
    except (ValueError, IndexError):
        return False
    current = int(datetime.now().timestamp() // window_seconds)
    for w in (current, current - 1, current + 1):
        msg = str(w).encode("utf-8")
        expected = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()[:16]
        if hmac.compare_digest(expected, sig_got):
            return True
    return False


# ---------------------------------------------------------------------------
# Gate C: 予算（Cost Budget）
# ---------------------------------------------------------------------------


def get_budget_usage_path(config: Dict[str, Any]) -> Path:
    """予算使用量を記録するファイルパス"""
    base = Path(config.get("budget_usage_dir", Path(__file__).parent))
    return base / "autonomy_budget_usage.json"


def load_budget_usage(config: Dict[str, Any]) -> Dict[str, Any]:
    """現在の予算使用量を読み込み"""
    path = get_budget_usage_path(config)
    if not path.exists():
        return _default_budget_usage()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception:
        return _default_budget_usage()


def _default_budget_usage() -> Dict[str, Any]:
    now = datetime.now()
    return {
        "hour_start": now.replace(minute=0, second=0, microsecond=0).isoformat(),
        "day_start": now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat(),
        "per_hour": {"llm_calls": 0, "image_jobs": 0, "video_jobs": 0},
        "per_day": {"llm_calls": 0, "image_jobs": 0, "video_jobs": 0},
    }


def _reset_if_new_period(usage: Dict[str, Any], budget: Dict[str, Any]) -> Dict[str, Any]:
    """新しい時間/日になったらカウンタをリセット"""
    now = datetime.now()
    hour_start = datetime.fromisoformat(usage["hour_start"])
    day_start = datetime.fromisoformat(usage["day_start"])
    if (now - hour_start).total_seconds() >= 3600:
        usage["hour_start"] = now.replace(minute=0, second=0, microsecond=0).isoformat()
        usage["per_hour"] = {"llm_calls": 0, "image_jobs": 0, "video_jobs": 0}
    if (now - day_start).total_seconds() >= 86400:
        usage["day_start"] = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        usage["per_day"] = {"llm_calls": 0, "image_jobs": 0, "video_jobs": 0}
    return usage


def check_budget(
    config: Dict[str, Any],
    usage_key: str,  # "llm_calls" | "image_jobs" | "video_jobs"
    period: str = "per_hour",  # "per_hour" | "per_day"
) -> tuple[bool, Dict[str, Any]]:
    """
    予算内かチェック。枠を超えていれば (False, usage)、超えていなければ (True, usage)。
    呼び出し側で usage を increment して保存する想定。
    """
    budget = config.get("budget") or {}
    per = budget.get(period) or {}
    limit = per.get(usage_key, -1)
    if limit < 0:
        return True, load_budget_usage(config)

    usage = load_budget_usage(config)
    usage = _reset_if_new_period(usage, budget)
    current = (usage.get(period) or {}).get(usage_key, 0)
    if current >= limit:
        return False, usage
    return True, usage


def increment_budget_usage(
    config: Dict[str, Any],
    usage_key: str,
    period: str = "per_hour",
    amount: int = 1,
) -> None:
    """予算使用量を 1 増やして保存"""
    usage = load_budget_usage(config)
    usage = _reset_if_new_period(usage, config.get("budget") or {})
    if period not in usage:
        usage[period] = {"llm_calls": 0, "image_jobs": 0, "video_jobs": 0}
    usage[period][usage_key] = usage[period].get(usage_key, 0) + amount
    path = get_budget_usage_path(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(usage, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Gate D: 監査（Audit）
# ---------------------------------------------------------------------------


def get_audit_log_path(config: Dict[str, Any]) -> Path:
    """監査ログ JSONL のパス"""
    base = Path(config.get("audit_log_dir", Path(__file__).parent))
    return base / "autonomy_audit.jsonl"


def audit_log(
    config: Dict[str, Any],
    *,
    portal_trace_id: Optional[str] = None,
    plan_id: Optional[str] = None,
    action_id: Optional[str] = None,
    tool_name: str = "",
    action_class: str = "",
    input_hash: Optional[str] = None,
    result: str = "success",  # success | failed | error
    message: Optional[str] = None,
    level: int = 0,
) -> None:
    """自律アクションを 1 行 JSONL で追記"""
    path = get_audit_log_path(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now().isoformat(),
        "level": level,
        "tool": tool_name,
        "action_class": action_class,
        "portal_trace_id": portal_trace_id,
        "plan_id": plan_id,
        "action_id": action_id,
        "input_hash": input_hash,
        "result": result,
        "message": message or "",
    }
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def input_hash_for_audit(prompt_or_params: Any) -> str:
    """監査用の入力ハッシュ（プロンプト・設定の簡易ハッシュ）"""
    raw = json.dumps(prompt_or_params, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# 静音時間（quiet_hours）
# ---------------------------------------------------------------------------


def is_quiet_hours(config: Dict[str, Any]) -> bool:
    """現在が quiet_hours 内か"""
    q = config.get("quiet_hours") or {}
    start = q.get("start")  # 例: "22:00"
    end = q.get("end")  # 例: "07:00"
    if not start or not end:
        return False
    now = datetime.now()
    try:
        start_t = datetime.strptime(start, "%H:%M").time()
        end_t = datetime.strptime(end, "%H:%M").time()
    except Exception:
        return False
    now_t = now.time()
    if start_t <= end_t:  # 同一日内
        return start_t <= now_t <= end_t
    # 日をまたぐ（例 22:00〜07:00）
    return now_t >= start_t or now_t <= end_t


# ---------------------------------------------------------------------------
# 降格ポリシー（degrade_policy）
# ---------------------------------------------------------------------------


def get_degraded_level(config: Dict[str, Any], reason: str) -> int:
    """
    理由に応じた降格先レベルを返す。
    reason: "on_budget_exceeded" | "on_repeated_failures"
    """
    policy = config.get("degrade_policy") or {}
    if reason == "on_budget_exceeded":
        return int(policy.get("on_budget_exceeded", 2))
    if reason == "on_repeated_failures":
        return int(policy.get("on_repeated_failures", 3))
    return config.get("autonomy_level", 4)
