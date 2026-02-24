#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Layer2 LoRA の簡易スモークテストスクリプト。

目的:
- LoRA が正しくロードできるか
- 生成がエラーなく動くか（DynamicCache まわりも含む）
- Layer2 っぽい問いで挙動がそれっぽくなっていそうか、目視でざっくり確認する
"""

import json
import random
import sys
from pathlib import Path

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel

# Windows コンソールの文字化け・エラー対策
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def load_jsonl(path: str):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def phi3_format(messages):
    """
    ざっくり Phi-3 チャット風に整形。
    （必要なら学習時フォーマットに合わせて調整してOK）
    """
    out = []
    for m in messages:
        role = m["role"]
        content = m["content"]
        if role == "user":
            out.append(f"User: {content}")
        else:
            out.append(f"Assistant: {content}")
    # 生成は Assistant の続きとして出させる
    out.append("Assistant:")
    return "\n".join(out)


@torch.inference_mode()
def generate_one(model, tokenizer, prompt: str, max_new_tokens: int = 64) -> str:
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

    # DynamicCache / Phi3 互換のため:
    # - use_cache=False
    # - do_sample=False（安定）
    gen = model.generate(
        **inputs,
        max_new_tokens=max_new_tokens,
        do_sample=False,
        temperature=1.0,
        top_p=1.0,
        repetition_penalty=1.15,
        no_repeat_ngram_size=3,
        use_cache=False,
        pad_token_id=tokenizer.eos_token_id,
        eos_token_id=tokenizer.eos_token_id,
    )
    text = tokenizer.decode(gen[0], skip_special_tokens=True)

    # プロンプト部分の繰り返しを除去（単純版）
    if text.startswith(prompt):
        text = text[len(prompt) :]
    return text.strip()


def main():
    # ★パスは環境に合わせて調整
    BASE_MODEL = r"D:\castle_ex_training\castle_ex_v1_1"  # v1.1 本体
    LORA_DIR = r"D:\castle_ex_training\lora_castle_ex_layer2_v1_1_1"  # 学習済み LoRA
    # eval JSONL はリポジトリ直下のものを使う
    EVAL_JSONL = str(Path("castle_ex_dataset_v1_1_eval.jsonl").resolve())

    N = 12  # テストする件数

    print(f"Eval JSONL: {EVAL_JSONL}")
    if not Path(EVAL_JSONL).exists():
        print("ERROR: eval jsonl が見つかりません。パスを確認してください。")
        return 1

    print("Loading tokenizer...")
    tok = AutoTokenizer.from_pretrained(BASE_MODEL, use_fast=True)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    print("Loading base model...")
    base = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        torch_dtype="auto",
        device_map="auto",
    )

    print("Loading LoRA...")
    model = PeftModel.from_pretrained(base, LORA_DIR)
    model.eval()

    # DynamicCache 周りの事故を避けるため use_cache はオフ
    try:
        model.config.use_cache = False
    except Exception:
        pass

    # eval から Layer2 を優先で拾う
    items = []
    for item in load_jsonl(EVAL_JSONL):
        if item.get("layer") == 2:
            items.append(item)

    if not items:
        print("Layer2 のアイテムが見つからなかったので、全体からランダムにサンプルします。")
        items = list(load_jsonl(EVAL_JSONL))

    if not items:
        print("ERROR: eval データが空です。")
        return 1

    random.shuffle(items)
    samples = items[:N]

    print(f"\nPicked {len(samples)} samples.\n")

    for i, item in enumerate(samples, 1):
        msgs = item["messages"]
        user_q = next((m["content"] for m in msgs if m["role"] == "user"), "")
        gold = next((m["content"] for m in msgs if m["role"] == "assistant"), "")

        prompt = phi3_format([{"role": "user", "content": user_q}])
        pred = generate_one(model, tok, prompt, max_new_tokens=96)

        print("=" * 100)
        print(f"[{i}] Q: {user_q}")
        print(f"    GOLD: {gold}")
        print(f"    PRED: {pred}")

    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

