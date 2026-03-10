#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Layer 2 の誤答だけを抽出して短く表示（v1.1 設計用）。
使い方: python castle_ex/export_layer2_errors.py
"""
import json
import sys
from pathlib import Path

# プロジェクトルートを path に追加
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from castle_ex.castle_ex_evaluator_fixed import (
    format_prompt_phi3,  # type: ignore[attr-defined]
    CastleEXEvaluator,  # type: ignore[attr-defined]
)


def load_model_predictor(model_path: str):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(
        model_path, trust_remote_code=True, local_files_only=True
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        trust_remote_code=True,
        local_files_only=True,
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
    )
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = model.to(device)  # type: ignore
    model.eval()
    max_new_tokens = 512

    def _predict(prompt: str) -> str:
        inputs = tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=2048,
            padding=False,
        )
        input_len = inputs["input_ids"].shape[1]
        inputs = {k: v.to(device) for k, v in inputs.items()}
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                num_return_sequences=1,
                pad_token_id=tokenizer.eos_token_id,
                do_sample=False,
                use_cache=False,
            )
        generated_ids = outputs[0][input_len:]
        text = tokenizer.decode(generated_ids, skip_special_tokens=False)
        if "<|end|>" in text:
            text = text.split("<|end|>")[0]
        return text.strip()

    return _predict


def main():
    eval_path = Path(__file__).resolve().parent.parent / "castle_ex_dataset_v1_0_eval.jsonl"
    model_path = r"D:\castle_ex_training\castle_ex_v1_0"

    with open(eval_path, "r", encoding="utf-8") as f:
        all_items = [json.loads(line) for line in f if line.strip()]

    layer2_items = [item for item in all_items if item.get("layer") == 2]
    print(f"Layer 2 件数: {len(layer2_items)}")

    predictor = load_model_predictor(model_path)
    evaluator = CastleEXEvaluator(model_predictor=predictor, prompt_format="phi3")
    errors = []

    for i, item in enumerate(layer2_items):
        prompt = format_prompt_phi3(item)
        gold = None
        for msg in reversed(item.get("messages", [])):
            if msg.get("role") == "assistant":
                gold = msg.get("content", "")
                break
        if not gold:
            continue
        pred = predictor(prompt)
        is_correct, score = evaluator.evaluate_response(gold, pred)
        if not is_correct:
            user_content = ""
            for msg in item.get("messages", []):
                if msg.get("role") == "user":
                    user_content = msg.get("content", "")[:120]
                    break
            errors.append(
                {
                    "user_snippet": user_content,
                    "gold": gold,
                    "pred": pred,
                    "axes": item.get("axes", []),
                    "positive": item.get("positive", True),
                    "error_type": item.get("error_type"),
                }
            )

    print(f"Layer 2 誤答数: {len(errors)} / {len(layer2_items)}\n")
    print("=" * 60)
    print("Layer 2 誤答サンプル（短く、5件）")
    print("=" * 60)
    for i, e in enumerate(errors[:5]):
        print(f"\n--- 誤答 {i+1} ---")
        print(f"問い(抜粋): {e['user_snippet']}")
        print(f"正解: {e['gold']}")
        print(f"予測: {e['pred']}")
        print(f"axes: {e['axes']} | pos: {e['positive']} | error_type: {e.get('error_type')}")


if __name__ == "__main__":
    main()
