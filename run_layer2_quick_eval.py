from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for obj in rows:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def _latest_checkpoint(output_dir: Path) -> Tuple[int, Path] | None:
    if not output_dir.exists():
        return None
    checkpoints = []
    for p in output_dir.iterdir():
        if not p.is_dir():
            continue
        if not p.name.startswith("checkpoint-"):
            continue
        try:
            step = int(p.name.replace("checkpoint-", ""))
        except ValueError:
            continue
        checkpoints.append((step, p))
    if not checkpoints:
        return None
    return sorted(checkpoints, key=lambda x: x[0])[-1]


def main() -> int:
    parser = argparse.ArgumentParser(description="CASTLE-EX Layer2 quick eval (subset of eval JSONL)")
    parser.add_argument(
        "--base-model",
        default=r"D:\castle_ex_training\castle_ex_v1_1",
        help="Base model path (default: D:\\castle_ex_training\\castle_ex_v1_1)",
    )
    parser.add_argument(
        "--output-dir",
        default=r"D:\castle_ex_training\lora_castle_ex_layer2_v1_1_2",
        help="LoRA training output dir containing checkpoint-* (default: v1_1_2)",
    )
    parser.add_argument(
        "--checkpoint-step",
        type=int,
        default=0,
        help="Evaluate a specific checkpoint step (e.g. 3500). 0 means latest.",
    )
    parser.add_argument(
        "--eval-data",
        default="castle_ex_dataset_v1_1_eval.jsonl",
        help="Eval JSONL (default: castle_ex_dataset_v1_1_eval.jsonl)",
    )
    parser.add_argument(
        "--reports-dir",
        default="Reports",
        help="Output directory for results (default: Reports)",
    )
    parser.add_argument(
        "--max-new-tokens",
        type=int,
        default=64,
        help="Generation max_new_tokens (default: 64)",
    )
    parser.add_argument(
        "--device-map",
        default="auto",
        help="transformers device-map (default: auto)",
    )
    parser.add_argument(
        "--python",
        default="py",
        help="Python launcher command (default: py)",
    )
    parser.add_argument(
        "--python-version",
        default="3.10",
        help="Python version for launcher (default: 3.10)",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent
    eval_path = (repo_root / args.eval_data).resolve()
    if not eval_path.exists():
        raise SystemExit(f"eval-data not found: {eval_path}")

    output_dir = Path(args.output_dir)
    if args.checkpoint_step > 0:
        lora_path = output_dir / f"checkpoint-{args.checkpoint_step}"
        if not lora_path.exists():
            raise SystemExit(f"checkpoint not found: {lora_path}")
        step = args.checkpoint_step
    else:
        latest = _latest_checkpoint(output_dir)
        if latest is None:
            raise SystemExit(f"no checkpoints found in: {output_dir}")
        step, lora_path = latest

    all_rows = _read_jsonl(eval_path)
    layer2_rows = [r for r in all_rows if int(r.get("layer", -1)) == 2]
    if not layer2_rows:
        raise SystemExit("no layer=2 rows found in eval-data")

    reports_dir = (repo_root / args.reports_dir).resolve()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    subset_path = reports_dir / f"castle_ex_layer2_eval_subset.jsonl"
    out_json = reports_dir / f"castle_ex_layer2_quick_eval_checkpoint-{step}_{ts}.json"

    _write_jsonl(subset_path, layer2_rows)

    evaluator = (repo_root / "castle_ex" / "castle_ex_evaluator_fixed.py").resolve()
    if not evaluator.exists():
        raise SystemExit(f"evaluator not found: {evaluator}")

    cmd = [
        args.python,
        f"-{args.python_version}",
        str(evaluator),
        "--model",
        args.base_model,
        "--lora",
        str(lora_path),
        "--eval-data",
        str(subset_path),
        "--output",
        str(out_json),
        "--max-new-tokens",
        str(args.max_new_tokens),
        "--device-map",
        args.device_map,
    ]

    print(f"[layer2-quick] eval_data={eval_path}")
    print(f"[layer2-quick] layer2_n={len(layer2_rows)} subset={subset_path}")
    print(f"[layer2-quick] lora={lora_path}")
    print(f"[layer2-quick] out={out_json}")
    print("[layer2-quick] running evaluator...")

    proc = subprocess.run(cmd, cwd=str(repo_root))
    return int(proc.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
