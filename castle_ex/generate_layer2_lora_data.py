#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Layer2 専用 LoRA 用データを設計通りに量産し、JSONL 出力。
使い方:
  python castle_ex/generate_layer2_lora_data.py --out castle_ex_dataset_layer2_lora.jsonl
  python castle_ex/generate_layer2_lora_data.py --out castle_ex_dataset_layer2_lora.jsonl --split  # train/eval も作成
"""

import json
import argparse
from pathlib import Path

# リポジトリルート or castle_ex から実行どちらでも可
try:
    from castle_ex.castle_ex_data_generator import CastleEXDataGenerator
except ImportError:
    from castle_ex_data_generator import CastleEXDataGenerator


def main():
    parser = argparse.ArgumentParser(description="Layer2 LoRA 用データ量産（設計通り）")
    parser.add_argument(
        "--out",
        type=str,
        default="castle_ex_dataset_layer2_lora.jsonl",
        help="出力 JSONL パス",
    )
    parser.add_argument(
        "--n-attribute",
        type=int,
        default=400,
        help="l2_attribute 件数（デフォルト: 400）",
    )
    parser.add_argument(
        "--n-comparison",
        type=int,
        default=400,
        help="l2_comparison 件数（デフォルト: 400）",
    )
    parser.add_argument(
        "--n-part-whole",
        type=int,
        default=150,
        help="l2_part_whole 件数（デフォルト: 150）",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="乱数シード",
    )
    parser.add_argument(
        "--split",
        action="store_true",
        help="train/eval に分割する（pair_id で同一グループを同じ側に）",
    )
    args = parser.parse_args()

    gen = CastleEXDataGenerator(random_seed=args.seed)
    data = gen.generate_layer2_lora_bulk(
        n_attribute=args.n_attribute,
        n_comparison=args.n_comparison,
        n_part_whole=args.n_part_whole,
    )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as f:
        for item in data:
            line = {
                "layer": item["layer"],
                "axes": item["axes"],
                "positive": item["positive"],
                "messages": item["messages"],
            }
            if item.get("type"):
                line["type"] = item["type"]
            if item.get("template_id"):
                line["template_id"] = item["template_id"]
            if item.get("pair_id"):
                line["pair_id"] = item["pair_id"]
            f.write(json.dumps(line, ensure_ascii=False) + "\n")

    print(f"[OK] Layer2 LoRA 用データ: {out_path} ({len(data)}件)")
    by_tid = {}
    for item in data:
        tid = item.get("template_id", "?")
        by_tid[tid] = by_tid.get(tid, 0) + 1
    for tid, n in sorted(by_tid.items()):
        print(f"  {tid}: {n}件")

    if args.split:
        try:
            try:
                from castle_ex.castle_ex_dataset_splitter import split_dataset
            except ImportError:
                from castle_ex_dataset_splitter import split_dataset
            base = out_path.stem
            out_dir = out_path.parent
            train_file, eval_file = split_dataset(
                str(out_path),
                train_ratio=0.9,
                eval_ratio=0.1,
                output_dir=str(out_dir),
                group_by="pair_id",
            )
            print(f"[OK] 分割: {train_file}, {eval_file}")
        except Exception as e:
            print(f"[WARN] 分割スキップ: {e}")


if __name__ == "__main__":
    main()
