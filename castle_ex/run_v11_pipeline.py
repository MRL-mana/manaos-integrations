#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v1.1 パイプライン: Layer2 +240 生成 → バリデータ → v1.0 とマージ → stratified split。
実行: python -m castle_ex.run_v11_pipeline [--seed 42] [--out-dir .]
"""

import json
import sys
from pathlib import Path

# プロジェクトルートを path に追加
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def main():
    import argparse

    parser = argparse.ArgumentParser(description="v1.1 Layer2 +240 生成 → 検証 → マージ → 分割")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out-dir", type=str, default=str(REPO_ROOT))
    parser.add_argument(
        "--skip-merge", action="store_true", help="Layer2 のみ生成・検証（マージ・分割しない）"
    )
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1) v1.1 Layer2 +240 生成
    from castle_ex.castle_ex_data_generator import CastleEXDataGenerator

    gen = CastleEXDataGenerator(random_seed=args.seed)
    layer2_data = gen.generate_layer_2_v11(count_per_template=80)
    layer2_file = out_dir / "castle_ex_dataset_v1_1_layer2.jsonl"
    with open(layer2_file, "w", encoding="utf-8") as f:
        for item in layer2_data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"[1] v1.1 Layer2 生成: {len(layer2_data)}件 → {layer2_file}")

    # 2) バリデータ（invalid 0 確認）
    from castle_ex.castle_ex_data_validator import CastleEXDataValidator

    validator = CastleEXDataValidator()
    result = validator.validate_file(str(layer2_file))
    invalid = result["stats"]["invalid"]
    if invalid > 0:
        print(f"[2] バリデータ: 無効 {invalid}件 → 学習に進まず停止")
        return 1
    print("[2] バリデータ: invalid 0 OK")

    if args.skip_merge:
        print("[OK] --skip-merge のためここで終了")
        return 0

    # 3) v1.0 train から Layer2 を除き、v1.1 Layer2 を追加してマージ
    v10_train = REPO_ROOT / "castle_ex_dataset_v1_0_train.jsonl"
    merged_file = out_dir / "castle_ex_dataset_v1_1.jsonl"
    if not v10_train.exists():
        print(f"[3] {v10_train} が無いため v1.1 Layer2 のみで構成します。")
        merged_data = layer2_data
    else:
        with open(v10_train, "r", encoding="utf-8") as f:
            v10_items = [json.loads(line) for line in f if line.strip()]
        v10_no_l2 = [item for item in v10_items if item.get("layer") != 2]
        merged_data = v10_no_l2 + layer2_data
        print(
            f"[3] マージ: v1.0 train (Layer2除く) {len(v10_no_l2)}件 + v1.1 Layer2 {len(layer2_data)}件 = {len(merged_data)}件"
        )
    with open(merged_file, "w", encoding="utf-8") as f:
        for item in merged_data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"    → {merged_file}")

    # 4) stratified split（group_by pair_id で同一ペアが train/eval に分離しない）
    from castle_ex.castle_ex_dataset_splitter import split_dataset

    split_dataset(
        str(merged_file),
        train_ratio=0.9,
        eval_ratio=0.1,
        output_dir=str(out_dir),
        seed_hash="castle_ex_v1_1",
        group_by="pair_id",
    )
    train_file = out_dir / (merged_file.stem + "_train.jsonl")
    eval_file = out_dir / (merged_file.stem + "_eval.jsonl")
    print(f"[4] 分割完了: {train_file}, {eval_file}")

    print("\n[OK] v1.1 パイプライン完了。次のステップ:")
    print(
        "  追加学習: train_castle_ex_full.py --train-data ... --eval-data ... --resume-from-checkpoint <v1.0最終>"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
