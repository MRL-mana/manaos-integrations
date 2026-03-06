"""
collect_ng_cases.py
────────────────────────────────────────────────────────────
V1.1.7 運用監視: logs/ng_cases/*.jsonl からNG事例を集計・分析する。

使い方:
    python collect_ng_cases.py             # サマリー表示
    python collect_ng_cases.py --top 10    # NG上位10件表示
    python collect_ng_cases.py --since 2026-03-07  # 日付フィルタ
    python collect_ng_cases.py --export nogo_candidates.jsonl  # retrain用エクスポート
"""
from __future__ import annotations
import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

NG_LOG_DIR = Path(__file__).parent / "logs" / "ng_cases"


def load_ng_cases(since: str | None = None) -> list[dict]:
    cases: list[dict] = []
    if not NG_LOG_DIR.exists():
        return cases
    for f in sorted(NG_LOG_DIR.glob("ng_cases_*.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                c = json.loads(line)
                if since and c.get("ts", "") < since:
                    continue
                cases.append(c)
            except json.JSONDecodeError:
                pass
    return cases


def summarize(cases: list[dict]) -> None:
    if not cases:
        print("NG cases: 0 件 (運用良好)")
        return

    total = len(cases)
    by_date = Counter(c.get("ts", "")[:10] for c in cases)
    by_tmpl = Counter(c.get("template_id") or "unknown" for c in cases)

    # hai 判定: gold にはい/いいえ含まず、pred に含む
    hai_cases = [
        c for c in cases
        if not (c.get("gold", "").startswith(("はい", "いいえ")))
        and (c.get("pred", "").startswith(("はい", "いいえ")))
    ]
    # repeat 判定: pred に同一3語フレーズ
    repeat_cases = []
    for c in cases:
        pred = c.get("pred", "")
        words = pred.split()
        found = False
        for i in range(len(words) - 3):
            phrase = " ".join(words[i:i+3])
            if pred.count(phrase) >= 2:
                found = True
                break
        if found:
            repeat_cases.append(c)

    print(f"\n{'='*50}")
    print(f"  V1.1.7 運用NG集計")
    print(f"  期間: {min(by_date)} ~ {max(by_date)}" if by_date else "")
    print(f"{'='*50}")
    print(f"  total NG         : {total}")
    print(f"  hai/いいえ誤出力 : {len(hai_cases)}")
    print(f"  repeat 冗長出力  : {len(repeat_cases)}")
    print()
    print("  日別 NG:")
    for d, n in sorted(by_date.items()):
        bar = "█" * n
        print(f"    {d} : {bar} ({n})")
    print()
    print(f"  template別 NG (top5):")
    for tmpl, n in by_tmpl.most_common(5):
        print(f"    {tmpl:30s}: {n}")
    print()

    # V1.1.8 開始条件
    ng_threshold = 5
    if total >= ng_threshold:
        print(f"  [HINT] NG={total} >= {ng_threshold}件 → V1.1.8 開始条件を満たしています")
        print(f"    → nogo_A_inject_and_retrain.ps1 を実行してretrainデータを生成")
    else:
        remain = ng_threshold - total
        print(f"  [INFO] まだ観察継続。あと {remain} 件たまったら V1.1.8 候補")
    print(f"{'='*50}\n")


def show_top(cases: list[dict], n: int) -> None:
    print(f"\n最新 NG {min(n, len(cases))} 件:\n")
    for c in cases[-n:]:
        print(f"  [{c.get('ts','')[:16]}] pair={c.get('pair_id','?')} tmpl={c.get('template_id','?')}")
        print(f"    GOLD: {c.get('gold','')}")
        print(f"    PRED: {c.get('pred','')}")
        print()


def export_for_retrain(cases: list[dict], out_path: str) -> None:
    """nogo_A 用 retrain 候補として JSONL エクスポート"""
    p = Path(out_path)
    written = 0
    with p.open("w", encoding="utf-8") as f:
        for c in cases:
            record = {
                "pair_id":     c.get("pair_id"),
                "template_id": c.get("template_id"),
                "prompt":      c.get("prompt"),
                "gold":        c.get("gold"),
                "pred":        c.get("pred"),
                "ts":          c.get("ts"),
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            written += 1
    print(f"[EXPORT] {written} 件 → {p}")


def main():
    parser = argparse.ArgumentParser(description="V1.1.7 NG集計ツール")
    parser.add_argument("--since", default=None, help="集計開始日 (YYYY-MM-DD)")
    parser.add_argument("--top", type=int, default=0, help="最新N件の詳細表示")
    parser.add_argument("--export", default=None, help="retrain用に JSONL エクスポート")
    args = parser.parse_args()

    cases = load_ng_cases(since=args.since)
    summarize(cases)

    if args.top > 0:
        show_top(cases, args.top)

    if args.export:
        export_for_retrain(cases, args.export)


if __name__ == "__main__":
    main()
