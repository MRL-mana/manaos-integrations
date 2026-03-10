#!/usr/bin/env python3
"""
DPO学習（Direct Preference Optimization）
好みペアから学習して挙動を調整
"""

import os
import sys
import json
import argparse
import torch
from pathlib import Path
from typing import List, Dict

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent

# オプショナルインポート
try:
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        TrainingArguments
    )
    from peft import PeftModel, LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from trl import DPOTrainer, DPOTrainingArguments
    from datasets import Dataset
    import bitsandbytes as bnb
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False


def load_dpo_data(data_path: str) -> List[Dict]:
    """DPOデータを読み込み"""
    data = []
    with open(data_path, 'r', encoding='utf-8') as f:
        for line in f:
            item = json.loads(line)
            # DPO形式: {"prompt": "...", "chosen": "...", "rejected": "..."}
            data.append(item)
    return data


def format_dpo_prompt(instruction: str, input_text: str = "") -> str:
    """DPOプロンプトフォーマット"""
    if input_text:
        return f"### 指示:\n{instruction}\n\n### 入力:\n{input_text}\n\n### 応答:\n"
    else:
        return f"### 指示:\n{instruction}\n\n### 応答:\n"


def train_dpo(
    base_model: str,
    adapter_path: str,
    data_path: str,
    output_dir: str,
    beta: float = 0.1,
    batch_size: int = 4,
    num_epochs: int = 1,
    learning_rate: float = 1e-5,
    use_4bit: bool = True
):
    """DPO学習"""

    print("🚀 DPO学習開始...")
    print(f"   ベースモデル: {base_model}")
    print(f"   アダプター: {adapter_path}")
    print(f"   データ: {data_path}")
    print(f"   出力: {output_dir}")
    print(f"   Beta: {beta}")

    if not TRANSFORMERS_AVAILABLE:
        print("\n❌ 必要なパッケージがインストールされていません")
        print("   インストール: pip install transformers peft trl accelerate")
        return

    # データ読み込み
    data = load_dpo_data(data_path)
    print(f"   ✅ データ読み込み: {len(data)}件")

    # トークナイザー読み込み
    print("📦 トークナイザー読み込み中...")
    tokenizer = AutoTokenizer.from_pretrained(base_model)  # type: ignore[possibly-unbound]
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # モデル読み込み（4bit量子化）
    print("📦 モデル読み込み中（4bit量子化）...")
    bnb_config = None
    if use_4bit:
        bnb_config = bnb.config.BitsAndBytesConfig(  # type: ignore[attr-defined, possibly-unbound]
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True
        )

    model = AutoModelForCausalLM.from_pretrained(  # type: ignore[possibly-unbound]
        base_model,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True
    )

    # SFT adapter読み込み
    if adapter_path and Path(adapter_path).exists():
        print(f"📦 SFT adapter読み込み中: {adapter_path}")
        model = PeftModel.from_pretrained(model, adapter_path)  # type: ignore[possibly-unbound]
        model = model.merge_and_unload()  # adapterをマージ

    # DPO用にrefモデルも作成
    ref_model = AutoModelForCausalLM.from_pretrained(  # type: ignore[possibly-unbound]
        base_model,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True
    )
    if adapter_path and Path(adapter_path).exists():
        ref_model = PeftModel.from_pretrained(ref_model, adapter_path)  # type: ignore[possibly-unbound]
        ref_model = ref_model.merge_and_unload()

    # データセット準備
    print("📊 データセット作成中...")
    # DPO形式に変換
    dpo_data = []
    for item in data:
        prompt = item.get("prompt", "")
        chosen = item.get("chosen", "")
        rejected = item.get("rejected", "")

        if not prompt or not chosen or not rejected:
            # フォールバック: instruction/input形式
            instruction = item.get("instruction", "")
            input_text = item.get("input", "")
            prompt = format_dpo_prompt(instruction, input_text)
            chosen = item.get("response", "")
            rejected = item.get("rejected_response", "")

        dpo_data.append({
            "prompt": prompt,
            "chosen": chosen,
            "rejected": rejected
        })

    dataset = Dataset.from_list(dpo_data)  # type: ignore[possibly-unbound]

    # DPO学習設定
    training_args = DPOTrainingArguments(  # type: ignore[possibly-unbound]
        output_dir=output_dir,
        num_train_epochs=num_epochs,
        per_device_train_batch_size=batch_size,
        learning_rate=learning_rate,
        fp16=True,
        logging_steps=10,
        save_steps=100,
        save_total_limit=3,
        warmup_steps=50,
        report_to="none",
        beta=beta
    )

    # DPO Trainer作成
    dpo_trainer = DPOTrainer(  # type: ignore[possibly-unbound]
        model=model,
        ref_model=ref_model,
        args=training_args,
        train_dataset=dataset,
        tokenizer=tokenizer,
        beta=beta
    )

    # 学習実行
    print("\n🎯 DPO学習開始...")
    dpo_trainer.train()

    # 保存
    print(f"\n💾 モデル保存中: {output_dir}")
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)

    # 設定保存
    config = {
        "base_model": base_model,
        "adapter_path": adapter_path,
        "data_path": data_path,
        "output_dir": output_dir,
        "beta": beta,
        "batch_size": batch_size,
        "num_epochs": num_epochs,
        "learning_rate": learning_rate,
        "data_count": len(data)
    }

    config_file = Path(output_dir) / "dpo_config.json"
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"✅ DPO学習完了！出力: {output_dir}")


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description="DPO学習")
    parser.add_argument("--base", required=True, help="ベースモデル名")
    parser.add_argument("--adapter", required=True, help="SFT adapterパス")
    parser.add_argument("--data", required=True, help="DPOデータファイル")
    parser.add_argument("--out", required=True, help="出力ディレクトリ")
    parser.add_argument("--beta", type=float, default=0.1, help="DPO beta")
    parser.add_argument("--batch-size", type=int, default=4, help="バッチサイズ")
    parser.add_argument("--epochs", type=int, default=1, help="エポック数")
    args = parser.parse_args()

    train_dpo(
        base_model=args.base,
        adapter_path=args.adapter,
        data_path=args.data,
        output_dir=args.out,
        beta=args.beta,
        batch_size=args.batch_size,
        num_epochs=args.epochs
    )


if __name__ == "__main__":
    main()

