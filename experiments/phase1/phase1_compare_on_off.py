#!/usr/bin/env python3
"""
フェーズ1 ON/OFF 比較集計。
phase1_runs/ 内の on/off スナップショット、または指定パスから集計して差分を表示する。

例:
    python phase1_compare_on_off.py
    python phase1_compare_on_off.py --on-conv runs/...on_conversation.log --on-refl ... --off-conv ... --off-refl ...
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUNS_DIR = ROOT / "phase1_runs"
STOPWORDS_PATH = ROOT / "phase1_stopwords.txt"

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


def _load_stopwords() -> set[str]:
    if not STOPWORDS_PATH.exists():
        return _DEFAULT_STOP
    s = set()
    with open(STOPWORDS_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                s.add(line)
    return s or _DEFAULT_STOP


STOP = _load_stopwords()


def _tokenize(text: str) -> list[str]:
    if not text:
        return []
    text_lower = text.lower()
    tokens = re.findall(r"[a-z0-9]+|[ぁ-んー]+|[ァ-ヶー]+|[一-龥]+", text_lower)
    out = []
    for t in tokens:
        if t in STOP or len(t) <= 1 or t.isdigit():
            continue
        out.append(t)
        if len(out) >= 10:
            break
    return out


def load_jsonl(path: Path) -> list[dict]:
    out = []
    if not path.exists():
        return out
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


def compute_metrics(conv: list[dict], refl: list[dict]) -> dict:
    """継続率・テーマ再訪・満足度を算出。"""
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
    revisit_theme_count = sum(1 for c in theme_count.values() if c > 1)

    satisfaction_avg = 0.0
    satisfaction_n = 0
    for r in refl:
        s = r.get("satisfaction")
        if isinstance(s, (int, float)) and 1 <= s <= 5:
            satisfaction_avg += s
            satisfaction_n += 1
    if satisfaction_n:
        satisfaction_avg /= satisfaction_n

    return {
        "conv_lines": len(conv),
        "refl_lines": len(refl),
        "continued": continued,
        "total_turns": total_turns,
        "continuation_rate": continuation_rate,
        "revisit_theme_count": revisit_theme_count,
        "satisfaction_avg": satisfaction_avg,
        "satisfaction_n": satisfaction_n,
    }


def _conv_to_refl_path(conv: Path) -> Path:
    """conversation.log パスから reflection.log パスを導出。"""
    name = conv.name.replace("_conversation.log", "_reflection.log")
    return conv.parent / name


def _find_latest_pair(condition: str) -> tuple[Path | None, Path | None]:
    """phase1_runs/ 内で最新の on/off スナップショットを探す。"""
    if not RUNS_DIR.exists():
        return None, None
    pat = f"*_{condition}_*_conversation.log"
    matches = sorted(RUNS_DIR.glob(pat), key=lambda p: p.stat().st_mtime, reverse=True)
    if not matches:
        return None, None
    conv = matches[0]
    refl = _conv_to_refl_path(conv)
    return (conv, refl) if refl.exists() else (conv, None)


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase1 ON/OFF 比較集計")
    parser.add_argument("--on-conv", type=Path, help="ON 会話ログパス")
    parser.add_argument("--on-refl", type=Path, help="ON 振り返りログパス")
    parser.add_argument("--off-conv", type=Path, help="OFF 会話ログパス")
    parser.add_argument("--off-refl", type=Path, help="OFF 振り返りログパス")
    parser.add_argument("--runs-dir", type=Path, default=RUNS_DIR, help="runs ディレクトリ")
    args = parser.parse_args()

    def resolve_pair(
        conv: Path | None, refl: Path | None, cond: str
    ) -> tuple[Path | None, Path | None]:
        if conv and refl:
            return conv, refl
        if conv and not refl:
            r = _conv_to_refl_path(conv)
            return conv, r if r.exists() else None
        c, r = _find_latest_pair(cond)
        return c, r

    on_conv, on_refl = resolve_pair(args.on_conv, args.on_refl, "on")
    off_conv, off_refl = resolve_pair(args.off_conv, args.off_refl, "off")

    if not on_conv or not on_refl:
        print(
            "ON ログが見つかりません。--on-conv / --on-refl を指定するか phase1_runs/ に on スナップショットを置いてください。"
        )
        sys.exit(1)
    if not off_conv or not off_refl:
        print(
            "OFF ログが見つかりません。--off-conv / --off-refl を指定するか phase1_runs/ に off スナップショットを置いてください。"
        )
        sys.exit(1)

    conv_on = load_jsonl(on_conv)
    refl_on = load_jsonl(on_refl)
    conv_off = load_jsonl(off_conv)
    refl_off = load_jsonl(off_refl)

    m_on = compute_metrics(conv_on, refl_on)
    m_off = compute_metrics(conv_off, refl_off)

    print("=== Phase1 ON/OFF 比較 ===")
    print()
    print("| 指標              | OFF           | ON            |")
    print("|-------------------|---------------|---------------|")
    print(f"| 会話ログ行数      | {m_off['conv_lines']:>13} | {m_on['conv_lines']:>13} |")
    print(f"| 振り返りログ行数  | {m_off['refl_lines']:>13} | {m_on['refl_lines']:>13} |")
    cr_off = (
        f"{m_off['continuation_rate']:.2%}" if m_off["continuation_rate"] is not None else "N/A"
    )
    cr_on = f"{m_on['continuation_rate']:.2%}" if m_on["continuation_rate"] is not None else "N/A"
    print(f"| 会話継続率        | {cr_off:>13} | {cr_on:>13} |")
    print(
        f"| 同一テーマ再訪    | {m_off['revisit_theme_count']:>13} | {m_on['revisit_theme_count']:>13} |"
    )
    sat_off = (
        f"{m_off['satisfaction_avg']:.2f} (n={m_off['satisfaction_n']})"
        if m_off["satisfaction_n"]
        else "N/A"
    )
    sat_on = (
        f"{m_on['satisfaction_avg']:.2f} (n={m_on['satisfaction_n']})"
        if m_on["satisfaction_n"]
        else "N/A"
    )
    print(f"| 満足度平均        | {sat_off:>13} | {sat_on:>13} |")
    print()
    print(f"ON:  {on_conv.name}")
    print(f"OFF: {off_conv.name}")


if __name__ == "__main__":
    main()
