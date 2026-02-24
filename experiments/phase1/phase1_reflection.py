#!/usr/bin/env python3
"""
フェーズ1 自己観察実験：振り返り ON/OFF 用テンプレート。
振り返り1問のプロンプト・JSONLログ追記・system_hash/params_hash まで。LLM呼び出しは呼び出し側で行う。

thread_id: セッション開始時に1回だけ決める（UUID 生成して保持 or 外部から渡す）。途中で変えない。
turn_id: assistant の出力単位で振る（ペアリング型）。user(turn_id=1) → assistant(turn_id=1) → ...
"""

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# -----------------------------------------------------------------------------
# 固定パラメータ（ON/OFFで変えない）
# -----------------------------------------------------------------------------
FIXED_INFERENCE_PARAMS = {
    "temp": 0.7,
    "top_p": 0.9,
    "max_tokens": 2048,
}

# 振り返り用の1問プロンプト
REFLECTION_PROMPT = """あなたの直後の返答を振り返り、ユーザーの満足度を1〜5で推定してください。

【満足度の基準】
1: 明らかに不満（無関係・誤答・無視）
2: やや不満（質問に部分的にしか応えていない）
3: どちらとも（一般的な返答で十分だが特別な価値はない）
4: やや満足（質問に応え、会話を続けやすい）
5: 明らかに満足（的確で具体的、次のアクションが明確）

曖昧な質問（「Brief question」等）には、助けようとした姿勢を公正に評価してください。過度に厳しくせず、中立的に。

形式: 1行目に1〜5の数字のみ、2行目に理由を1文で。
例:
4
曖昧な質問にも丁寧に具体的な説明を提供しており、会話継続につながる。"""


def compute_system_hash(system_prompt: str) -> str:
    """システムプロンプトの同一性検証用。sha256の先頭16文字。"""
    return hashlib.sha256(system_prompt.encode("utf-8")).hexdigest()[:16]


def compute_params_hash(
    temp: float, top_p: float, max_tokens: int, seed: Optional[int] = None
) -> str:
    """推論設定の同一性検証用。temp/top_p/max_tokens/seed を連結して hash。"""
    parts = f"{temp:.4f}_{top_p:.4f}_{max_tokens}_{seed if seed is not None else 'none'}"
    return hashlib.sha256(parts.encode("utf-8")).hexdigest()[:16]


def compute_prompt_hash(text: str) -> str:
    """後方互換用。システムプロンプト等の同一性検証。sha256の先頭16文字。"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def parse_reflection_answer(response_text: str) -> tuple[Optional[int], str]:
    """
    振り返り用LLM応答から満足度(1-5)と理由をパースする。
    形式: 1行目が数字のみ、2行目以降が理由。パース失敗時は (None, "").
    """
    if not response_text or not response_text.strip():
        return None, ""
    lines = response_text.strip().splitlines()
    satisfaction = None
    for line in lines:
        s = line.strip()
        if not s:
            continue
        if s.isdigit() and 1 <= int(s) <= 5:
            satisfaction = int(s)
            break
    reason = " ".join(l.strip() for l in lines[1:] if l.strip()).strip()[:500]
    return satisfaction, reason


def _git_head() -> Optional[str]:
    """現在の git commit hash（短縮）。リポジトリ外なら None。"""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
            cwd=Path(__file__).resolve().parent,
        )
        if out.returncode == 0 and out.stdout:
            return out.stdout.strip()
    except Exception:
        pass
    return None


def append_reflection_log(
    condition: str,
    thread_id: str,
    turn_id: int,
    role: str,
    user_msg_preview: str,
    model: str,
    temp: float,
    top_p: float,
    max_tokens: int,
    system_hash: str,
    params_hash: str,
    satisfaction: Optional[int] = None,
    reason: Optional[str] = None,
    log_path: Optional[str] = None,
    run_id: Optional[str] = None,
    git_commit: Optional[str] = None,
    seed: Optional[int] = None,
    request_id: Optional[str] = None,
    reflection_status: Optional[str] = None,
    user_msg_len: Optional[int] = None,
) -> None:
    """phase1_reflection.log に JSONL 1行を追記。OFF時も condition=off で1行出す（satisfaction/reason=null）。"""
    log_path = log_path or os.environ.get("PHASE1_REFLECTION_LOG", "phase1_reflection.log")
    ts = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")
    preview = (user_msg_preview or "")[:30]
    record = {
        "ts": ts,
        "condition": condition,
        "thread_id": thread_id,
        "turn_id": turn_id,
        "role": role,
        "satisfaction": satisfaction,
        "reason": (reason or "").strip() if reason is not None else None,
        "user_msg_preview": preview,
        "model": model,
        "temp": temp,
        "top_p": top_p,
        "max_tokens": max_tokens,
        "system_hash": system_hash,
        "params_hash": params_hash,
        "prompt_hash": system_hash,
    }
    if run_id is not None:
        record["run_id"] = run_id
    if request_id is not None:
        record["request_id"] = request_id
    if reflection_status is not None:
        record["reflection_status"] = reflection_status
    if user_msg_len is not None:
        record["user_msg_len"] = user_msg_len
    if git_commit is not None:
        record["git_commit"] = git_commit
    elif condition == "on":
        h = _git_head()
        if h:
            record["git_commit"] = h
    if seed is not None:
        record["seed"] = seed
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def append_conversation_log(
    thread_id: str,
    turn_id: int,
    role: str,
    content_preview: str,
    log_path: Optional[str] = None,
    request_id: Optional[str] = None,
) -> None:
    """会話ログをJSONLで追記。thread_id/turn_id で振り返りログと結合。request_id でプロセス再起動後も突合可能。"""
    log_path = log_path or os.environ.get("PHASE1_CONVERSATION_LOG", "phase1_conversation.log")
    ts = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")
    record = {
        "ts": ts,
        "thread_id": thread_id,
        "turn_id": turn_id,
        "role": role,
        "content_preview": (content_preview or "")[:200],
    }
    if request_id is not None:
        record["request_id"] = request_id
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


# -----------------------------------------------------------------------------
# 薄いラッパ（呼び出し側ミス激減：hash 生成を中でやる）
# -----------------------------------------------------------------------------


def log_reflection_on(
    thread_id: str,
    turn_id: int,
    user_msg_preview: str,
    model: str,
    satisfaction: int,
    reason: str,
    system_prompt: str,
    temp: float,
    top_p: float,
    max_tokens: int,
    log_path: Optional[str] = None,
    run_id: Optional[str] = None,
    seed: Optional[int] = None,
    request_id: Optional[str] = None,
    reflection_status: str = "on",
    user_msg_len: Optional[int] = None,
) -> None:
    """振り返り ON 用ラッパ。system_hash / params_hash を中で生成して append_reflection_log に流す。"""
    system_hash = compute_system_hash(system_prompt)
    params_hash = compute_params_hash(temp, top_p, max_tokens, seed)
    append_reflection_log(
        condition="on",
        thread_id=thread_id,
        turn_id=turn_id,
        role="assistant",
        user_msg_preview=user_msg_preview,
        model=model,
        temp=temp,
        top_p=top_p,
        max_tokens=max_tokens,
        system_hash=system_hash,
        params_hash=params_hash,
        satisfaction=satisfaction,
        reason=reason,
        log_path=log_path,
        run_id=run_id,
        seed=seed,
        request_id=request_id,
        reflection_status=reflection_status,
        user_msg_len=user_msg_len,
    )


def log_reflection_off(
    thread_id: str,
    turn_id: int,
    user_msg_preview: str,
    model: str,
    system_prompt: str,
    temp: float,
    top_p: float,
    max_tokens: int,
    log_path: Optional[str] = None,
    run_id: Optional[str] = None,
    seed: Optional[int] = None,
    request_id: Optional[str] = None,
    reflection_status: str = "off",
    user_msg_len: Optional[int] = None,
) -> None:
    """振り返り OFF 用ラッパ。OFFでも1行出す（satisfaction=null, reason=null）。hash は中で生成。"""
    system_hash = compute_system_hash(system_prompt)
    params_hash = compute_params_hash(temp, top_p, max_tokens, seed)
    append_reflection_log(
        condition="off",
        thread_id=thread_id,
        turn_id=turn_id,
        role="assistant",
        user_msg_preview=user_msg_preview,
        model=model,
        temp=temp,
        top_p=top_p,
        max_tokens=max_tokens,
        system_hash=system_hash,
        params_hash=params_hash,
        satisfaction=None,
        reason=None,
        log_path=log_path,
        run_id=run_id,
        seed=seed,
        request_id=request_id,
        reflection_status=reflection_status,
        user_msg_len=user_msg_len,
    )


# -----------------------------------------------------------------------------
# 呼び出し側の想定フロー（疑似コード）
# -----------------------------------------------------------------------------
# thread_id = str(uuid.uuid4())  # セッション開始時に1回だけ
# turn_id はセッション管理層が管理。user メッセージ受信で turn_id += 1、その turn_id を assistant 出力にも使う。
# system_prompt = "..."  # 固定文字列
# params = FIXED_INFERENCE_PARAMS
#
# response = llm.generate(..., temperature=params["temp"], top_p=params["top_p"], ...)
# append_conversation_log(thread_id, turn_id, "assistant", response)
#
# if REFLECTION_ENABLED:
#     satisfaction, reason = parse_reflection_answer(llm.generate(REFLECTION_PROMPT + "\n\n" + response[:500], ...))
#     log_reflection_on(thread_id, turn_id, user_msg_preview, model, satisfaction, reason,
#                      system_prompt, params["temp"], params["top_p"], params["max_tokens"])
# else:
#     log_reflection_off(thread_id, turn_id, user_msg_preview, model,
#                        system_prompt, params["temp"], params["top_p"], params["max_tokens"])
