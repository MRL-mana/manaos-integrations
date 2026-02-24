#!/usr/bin/env python3
"""
Phase2 第三層 PoC: 振り返りメモをテーマ単位で格納・参照する。
テーマID = 1ターン目ユーザー発話の上位3語（phase1_aggregate と同じルール）。
将来ベクトルDB／知識グラフへ差し替え可能なインターフェースにする。
"""

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

MEMO_LOG = os.environ.get("PHASE2_REFLECTION_MEMO_LOG", "phase2_reflection_memos.jsonl")
STOPWORDS_PATH = os.environ.get(
    "PHASE1_STOPWORDS",
    str(Path(__file__).resolve().parent / "phase1_stopwords.txt"),
)

_DEFAULT_STOP = {
    "の",
    "に",
    "は",
    "を",
    "た",
    "が",
    "で",
    "と",
    "し",
    "れ",
    "さ",
    "ある",
    "いる",
    "する",
    "こと",
    "それ",
    "あれ",
    "これ",
    "です",
    "ます",
}


def _load_stopwords(path: str) -> set[str]:
    p = Path(path)
    if not p.exists():
        return _DEFAULT_STOP
    stop = set()
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            stop.add(line)
    return stop if stop else _DEFAULT_STOP


def _tokenize(text: str, stop: set[str]) -> list[str]:
    if not text:
        return []
    text_lower = text.lower()
    tokens = re.findall(r"[a-z0-9]+|[ぁ-んー]+|[ァ-ヶー]+|[一-龥]+", text_lower)
    out = []
    for t in tokens:
        if t in stop or len(t) <= 1 or t.isdigit():
            continue
        out.append(t)
        if len(out) >= 10:
            break
    return out


def load_jsonl(path: str) -> list[dict]:
    out = []
    p = Path(path)
    if not p.exists():
        return out
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


def theme_id_from_conv(
    conv_list: list[dict], stopwords_path: str = STOPWORDS_PATH
) -> dict[str, str]:
    """
    会話ログから thread_id -> theme_id（word1/word2/word3）を算出。
    phase1_aggregate と同じルール（1ターン目ユーザー発話の上位3語）。
    """
    stop = _load_stopwords(stopwords_path)
    first_preview: dict[str, str] = {}
    for r in conv_list:
        if r.get("role") != "user":
            continue
        tid = r.get("thread_id", "")
        if tid not in first_preview:
            first_preview[tid] = r.get("content_preview", "")
    result: dict[str, str] = {}
    for tid, preview in first_preview.items():
        words = _tokenize(preview, stop)[:3]
        if len(words) >= 3:
            result[tid] = "/".join(words)
    return result


def append_memo(
    theme_id: str,
    thread_id: str,
    turn_id: int,
    satisfaction: Optional[int],
    reason: str,
    memo_log: str = MEMO_LOG,
) -> None:
    """メモを1行追記する。"""
    record = {
        "theme_id": theme_id,
        "thread_id": thread_id,
        "turn_id": turn_id,
        "satisfaction": satisfaction,
        "reason": (reason or "")[:500],
        "ts": datetime.now(tz=timezone.utc).isoformat(),
    }
    p = Path(memo_log)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def get_memos_for_theme(theme_id: str, memo_log: str = MEMO_LOG) -> list[dict]:
    """テーマIDでメモを検索し、新しい順で返す。"""
    records = load_jsonl(memo_log)
    matched = [r for r in records if r.get("theme_id") == theme_id]
    matched.sort(key=lambda r: r.get("ts", ""), reverse=True)
    return matched


def theme_id_from_first_user_content(preview: str, stopwords_path: str = STOPWORDS_PATH) -> str:
    """1件のユーザー発話プレビューからテーマID（word1/word2/word3）を算出。"""
    stop = _load_stopwords(stopwords_path)
    words = _tokenize(preview, stop)[:3]
    return "/".join(words) if len(words) >= 3 else ""


def get_memo_context_for_messages(
    messages: list[dict],
    max_memos: int = 5,
    memo_log: str = MEMO_LOG,
) -> str:
    """
    メッセージリストの「最初のユーザー発話」からテーマIDを算出し、
    同一テーマの過去振り返りメモを取得して注入用テキストを返す。
    メモがなければ空文字。
    """
    first_user_content = ""
    for m in messages:
        if m.get("role") == "user":
            first_user_content = (m.get("content") or "")[:500]
            break
    theme_id = theme_id_from_first_user_content(first_user_content)
    if not theme_id:
        return ""
    memos = get_memos_for_theme(theme_id, memo_log)[:max_memos]
    if not memos:
        return ""
    lines = ["【同一テーマの過去振り返り】"]
    for m in memos:
        sat = m.get("satisfaction", "?")
        reason = (m.get("reason") or "")[:120]
        lines.append(f"満足度{sat}: {reason}")
    return "\n".join(lines)
