#!/usr/bin/env python3
"""
フェーズ1 自己観察実験：振り返りログ・会話ログから継続率・同一テーマ再訪を集計。ワンコマンドで実行。

同一テーマ再訪：フェーズ1では「テーマ数（ユニーク）」＝複数スレッドで出現したユニークテーマの個数。
フェーズ2で回数（頻度）を見る。
"""

import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

REFLECTION_LOG = os.environ.get("PHASE1_REFLECTION_LOG", "phase1_reflection.log")
CONVERSATION_LOG = os.environ.get("PHASE1_CONVERSATION_LOG", "phase1_conversation.log")
STOPWORDS_PATH = os.environ.get(
    "PHASE1_STOPWORDS",
    str(Path(__file__).resolve().parent / "phase1_stopwords.txt"),
)

# デフォルトストップワード（ファイルがない場合）
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
    """1行1語。# 始まりと空行は無視。コード直書きより事故らない。"""
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


STOP = _load_stopwords(STOPWORDS_PATH)


def _tokenize(text: str) -> list[str]:
    """
    テーマID用トークン化。ルール固定で揺れを防ぐ。
    - 英字は小文字化
    - 数字のみのトークンは捨てる
    - 記号は除去（正規表現でひらがな/カタカナ/漢字/英数字の塊のみ）
    - ストップワード除去、len>1 のみ、上位10語まで
    """
    if not text:
        return []
    text_lower = text.lower()
    tokens = re.findall(r"[a-z0-9]+|[ぁ-んー]+|[ァ-ヶー]+|[一-龥]+", text_lower)
    out = []
    for t in tokens:
        if t in STOP or len(t) <= 1:
            continue
        if t.isdigit():
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


def main() -> None:
    conv = load_jsonl(CONVERSATION_LOG)
    refl = load_jsonl(REFLECTION_LOG)

    # 継続率：同じ thread_id で、assistant ターン後に user 発話が1回以上あるか
    # turn_id はペアリング型（user/assistant が同じ turn_id）
    by_thread = defaultdict(list)
    for r in conv:
        by_thread[r["thread_id"]].append((r["turn_id"], r.get("role", "")))
    for k, v in by_thread.items():
        by_thread[k] = sorted(v, key=lambda x: x[0])

    continued = 0
    total_turns = 0
    for thread_id, rows in by_thread.items():
        turn_ids = [t for t, role in rows if role == "assistant"]
        for tid in turn_ids:
            total_turns += 1
            next_user = any(t > tid and role == "user" for t, role in rows)
            if next_user:
                continued += 1

    continuation_rate = (continued / total_turns) if total_turns > 0 else None

    # 同一テーマ再訪：テーマ数（ユニーク）＝複数スレッドで出現したユニークテーマの個数
    # 1ターン目ユーザー発話の上位3語をテーマID、完全一致でカウント
    first_turn_user_preview: dict[str, str] = {}
    for r in conv:
        if r.get("role") != "user":
            continue
        tid = r["thread_id"]
        if tid not in first_turn_user_preview:
            first_turn_user_preview[tid] = r.get("content_preview", "")
    theme_ids: dict[str, list[str]] = {}
    for tid, preview in first_turn_user_preview.items():
        words = _tokenize(preview)[:3]
        theme_ids[tid] = words
    theme_count: dict[tuple, int] = defaultdict(int)
    for words in theme_ids.values():
        if len(words) >= 3:
            theme_count[tuple(words)] += 1
    # 複数スレッドで出現したテーマの個数（ユニーク）
    revisit_theme_count = sum(1 for c in theme_count.values() if c > 1)

    # Phase2: テーマ出現回数分布（頻度）
    theme_freq = [(words, c) for words, c in theme_count.items() if len(words) >= 3 and c >= 1]
    theme_freq.sort(key=lambda x: -x[1])

    # 出力
    print("=== フェーズ1 集計 ===")
    print(f"会話ログ: {CONVERSATION_LOG} ({len(conv)} 行)")
    print(f"振り返りログ: {REFLECTION_LOG} ({len(refl)} 行)")
    print()
    if total_turns == 0:
        print("会話継続率: N/A（assistantターンが0件）")
    else:
        print(f"会話継続率: {continued}/{total_turns} = {continuation_rate:.2%}")
    print(
        "同一テーマ再訪（テーマ数＝ユニーク）: " f"{revisit_theme_count} テーマが複数スレッドで出現"
    )
    if theme_freq:
        print("テーマ出現回数分布:")
        for words, c in theme_freq[:20]:
            label = "/".join(words)
            print(f"  {label} -> {c} スレッド")
    print()

    # condition 別（振り返りログがある場合。satisfaction=null は除外）
    if refl:
        by_cond = defaultdict(list)
        for r in refl:
            by_cond[r["condition"]].append(r.get("satisfaction"))
        for cond, sats in by_cond.items():
            valid = [s for s in sats if isinstance(s, (int, float)) and 1 <= s <= 5]
            avg = sum(valid) / len(valid) if valid else 0
            print(f"condition={cond}: 満足度平均 {avg:.2f} (n={len(valid)})")


if __name__ == "__main__":
    main()
    sys.exit(0)
