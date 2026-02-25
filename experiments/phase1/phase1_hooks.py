#!/usr/bin/env python3
"""
フェーズ1 自己観察実験：ManaOS 統合用フック（入口1枚噛ませ）。
phase1_reflection を直接あちこちで呼ばない。必ずここ経由にする。

ルールA: thread_id / turn_id を「唯一の場所」で管理（このモジュールの in-memory）
ルールB: phase1 は観測のみ。応答内容に影響しない。反省文はユーザーに見せない（ログだけ）。
"""

import os
import uuid
from typing import Optional

try:
    from phase1_reflection import (
        FIXED_INFERENCE_PARAMS,
        append_conversation_log,
        log_reflection_off,
        log_reflection_on,
    )

    PHASE1_AVAILABLE = True
except ImportError:
    PHASE1_AVAILABLE = False

# ─── RLAnything ブリッジ ───
try:
    import sys as _sys
    from pathlib import Path as _Path

    _rl_root = str(_Path(__file__).resolve().parent.parent.parent)
    if _rl_root not in _sys.path:
        _sys.path.insert(0, _rl_root)
    from rl_anything.orchestrator import RLAnythingOrchestrator

    _RL_AVAILABLE = True
except ImportError:
    _RL_AVAILABLE = False

_rl_instance: Optional["RLAnythingOrchestrator"] = None


def _get_rl() -> Optional["RLAnythingOrchestrator"]:
    """RLAnything シングルトンを遅延初期化。"""
    global _rl_instance
    if not _RL_AVAILABLE:
        return None
    if os.environ.get("RL_ANYTHING", "").strip().lower() not in ("1", "on", "true", "yes"):
        return None
    if _rl_instance is None:
        _rl_instance = RLAnythingOrchestrator()
    return _rl_instance


def _rl_bridge_on_turn(
    thread_id: str,
    turn_id: int,
    satisfaction: Optional[int],
    reason: Optional[str],
    reflection_on: bool,
) -> None:
    """assistant ターン完了時に RLAnything へスコアを送信。"""
    rl = _get_rl()
    if rl is None:
        return
    try:
        task_id = f"phase1_{thread_id}"
        # タスクがまだ開始されていなければ開始
        if task_id not in rl.observer.get_active_tasks():
            rl.begin_task(task_id, f"phase1 conversation {thread_id}")

        # satisfaction → 中間スコア (1-5 → 0.0-1.0)
        if satisfaction is not None:
            score = max(0.0, min(1.0, (satisfaction - 1) / 4.0))
            rl.score_intermediate(task_id, score, reason or "")
    except Exception:
        pass  # 観測専用 — 本線に影響させない

# thread_id -> 次に使う turn_id（user 受信で +1 してから assistant に同じ値を使う）
_turn_by_thread: dict[str, int] = {}
# thread_id -> テーマID（Phase2 メモ用。最初の user 発話から算出）
_theme_by_thread: dict[str, str] = {}


def _append_phase2_memo_if_enabled(
    thread_id: str,
    turn_id: int,
    satisfaction: Optional[int],
    reason: Optional[str],
) -> None:
    """PHASE2_MEMO_APPEND=on のとき、振り返りを phase2 メモに追記する。"""
    if os.environ.get("PHASE2_MEMO_APPEND", "").strip().lower() not in ("1", "on", "true", "yes"):
        return
    try:
        from phase2_reflection_memo import (
            load_jsonl,
            theme_id_from_conv,
            append_memo,
        )

        theme_id = _theme_by_thread.get(thread_id, "")
        if not theme_id:
            conv_path = os.environ.get("PHASE1_CONVERSATION_LOG", "phase1_conversation.log")
            conv = load_jsonl(conv_path)
            theme_by_thread = theme_id_from_conv(conv)
            theme_id = theme_by_thread.get(thread_id, "")
            if theme_id:
                _theme_by_thread[thread_id] = theme_id
        if theme_id and (satisfaction is not None or (reason or "").strip()):
            append_memo(
                theme_id=theme_id,
                thread_id=thread_id,
                turn_id=turn_id,
                satisfaction=satisfaction,
                reason=reason or "",
            )
    except Exception:
        pass  # Phase2 未利用時は無視


def phase1_enabled() -> bool:
    """env: PHASE1_REFLECTION=on|off。on のときのみ True（振り返りLLM呼び出しあり）。"""
    if not PHASE1_AVAILABLE:
        return False
    return os.environ.get("PHASE1_REFLECTION", "").strip().lower() in ("1", "on", "true", "yes")


def phase1_experiment_active() -> bool:
    """実験ログを記録するか。on でも off でも記録（OFF 3往復で condition=off を取るため）。"""
    if not PHASE1_AVAILABLE:
        return False
    v = os.environ.get("PHASE1_REFLECTION", "").strip().lower()
    return v in ("1", "on", "true", "yes", "off", "0", "false", "no")


def get_thread_id_from_request(request) -> Optional[str]:
    """
    リクエストから thread_id を取得。Body の thread_id またはヘッダ X-Thread-Id。
    無ければ None（呼び出し側で create_thread_id() してレスポンスに含める）。
    """
    if not request:
        return None
    tid = None
    if request.is_json and request.json:
        tid = request.json.get("thread_id")
    if not tid and hasattr(request, "headers"):
        tid = request.headers.get("X-Thread-Id")
    return (tid or "").strip() or None


def create_thread_id() -> str:
    """新規スレッド用 UUID。クライアントが次回以降リクエストに含める。"""
    return str(uuid.uuid4())


def next_turn_id(thread_id: str) -> int:
    """
    セッション管理層：user メッセージ受信で呼ぶ。返した値をこのターンの user/assistant 両方に使う（ペアリング型）。
    """
    global _turn_by_thread
    if thread_id not in _turn_by_thread:
        _turn_by_thread[thread_id] = 0
    _turn_by_thread[thread_id] += 1
    return _turn_by_thread[thread_id]


def log_turn_user(
    thread_id: str,
    turn_id: int,
    content_preview: str,
    request_id: Optional[str] = None,
) -> None:
    """ユーザー発話を会話ログに1行。LLM 呼び出しの「前」に呼ぶ。request_id で再起動後も突合可能。"""
    if not PHASE1_AVAILABLE:
        return
    # Phase2: 1ターン目の user 発話から theme_id をキャッシュ（後続のメモ追記でファイルIOを避ける）
    if (
        turn_id == 1
        and thread_id not in _theme_by_thread
        and os.environ.get("PHASE2_MEMO_APPEND", "").strip().lower() in ("1", "on", "true", "yes")
    ):
        try:
            from phase2_reflection_memo import theme_id_from_first_user_content

            theme_id = theme_id_from_first_user_content(content_preview or "")
            if theme_id:
                _theme_by_thread[thread_id] = theme_id
        except Exception:
            pass
    append_conversation_log(thread_id, turn_id, "user", content_preview, request_id=request_id)


def log_turn_assistant(
    thread_id: str,
    turn_id: int,
    user_msg_preview: str,
    assistant_preview: str,
    model: str,
    system_prompt: str = "",
    temp: Optional[float] = None,
    top_p: Optional[float] = None,
    max_tokens: Optional[int] = None,
    reflection_on: bool = False,
    satisfaction: Optional[int] = None,
    reason: Optional[str] = None,
    request_id: Optional[str] = None,
    reflection_status: Optional[str] = None,
    user_msg_len: Optional[int] = None,
    run_id: Optional[str] = None,
) -> None:
    """
    assistant 応答を会話ログに1行出し、振り返りログを1行出す（ON 時は satisfaction/reason 必須、OFF 時は null）。
    応答内容は変更しない（観測のみ）。反省文はユーザーに見せない。
    reflection_status: "on" | "off" | "failed_parse" | "failed_call" で後から検証可能。
    """
    if not PHASE1_AVAILABLE:
        return
    params = FIXED_INFERENCE_PARAMS
    t = params["temp"] if temp is None else temp
    p = params["top_p"] if top_p is None else top_p
    m = params["max_tokens"] if max_tokens is None else max_tokens
    append_conversation_log(
        thread_id, turn_id, "assistant", assistant_preview, request_id=request_id
    )
    status = (
        reflection_status if reflection_status is not None else ("on" if reflection_on else "off")
    )
    if reflection_on and satisfaction is not None and reason is not None:
        log_reflection_on(
            thread_id=thread_id,
            turn_id=turn_id,
            user_msg_preview=user_msg_preview,
            model=model,
            satisfaction=satisfaction,
            reason=reason,
            system_prompt=system_prompt,
            temp=t,
            top_p=p,
            max_tokens=m,
            request_id=request_id,
            reflection_status=status,
            user_msg_len=user_msg_len,
            run_id=run_id,
        )
        # Phase2: 同一テーマメモにリアルタイム追記（PHASE2_MEMO_APPEND=on 時）
        _append_phase2_memo_if_enabled(thread_id, turn_id, satisfaction, reason)
        # RLAnything: satisfaction スコアをブリッジ
        _rl_bridge_on_turn(thread_id, turn_id, satisfaction, reason, reflection_on=True)
    else:
        log_reflection_off(
            thread_id=thread_id,
            turn_id=turn_id,
            user_msg_preview=user_msg_preview,
            model=model,
            system_prompt=system_prompt,
            temp=t,
            top_p=p,
            max_tokens=m,
            request_id=request_id,
            reflection_status=status,
            user_msg_len=user_msg_len,
            run_id=run_id,
        )
