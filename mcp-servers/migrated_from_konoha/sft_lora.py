#!/usr/bin/env python3
"""
QLoRA SFT学習（Supervised Fine-Tuning）
LoRA adapter を学習してモデルを調整
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
        TrainingArguments,
        Trainer,
        DataCollatorForLanguageModeling
    )
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from peft.tuners.lora import LoraLayer
    import bitsandbytes as bnb
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False


def load_sft_data(data_path: str) -> List[Dict]:
    """SFTデータを読み込み"""
    data = []
    with open(data_path, 'r', encoding='utf-8') as f:
        for line in f:
            data.append(json.loads(line))
    return data


def format_prompt(instruction: str, input_text: str = "", response: str = "") -> str:
    """プロンプトフォーマット"""
    if input_text:
        return f"### 指示:\n{instruction}\n\n### 入力:\n{input_text}\n\n### 応答:\n{response}"
    else:
        return f"### 指示:\n{instruction}\n\n### 応答:\n{response}"


class SFTDataset(torch.utils.data.Dataset):
    """SFTデータセット"""

    def __init__(self, data: List[Dict], tokenizer, max_length: int = 512):
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.data = []

        for item in data:
            instruction = item.get("instruction", "")
            input_text = item.get("input", "")
            response = item.get("response", "")

            prompt = format_prompt(instruction, input_text, response)
            encoded = tokenizer(
                prompt,
                truncation=True,
                max_length=max_length,
                padding="max_length",
                return_tensors="pt"
            )
            self.data.append({
                "input_ids": encoded["input_ids"].squeeze(),
                "attention_mask": encoded["attention_mask"].squeeze()
            })

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        return self.data[idx]


def train_sft_lora(
    base_model: str,
    data_path: str,
    output_dir: str,
    rank: int = 16,
    lora_alpha: int = 32,
    lora_dropout: float = 0.05,
    batch_size: int = 4,
    num_epochs: int = 3,
    learning_rate: float = 2e-4,
    max_length: int = 512,
    use_4bit: bool = True
):
    """QLoRA SFT学習"""

    print("🚀 QLoRA SFT学習開始...")
    print(f"   ベースモデル: {base_model}")
    print(f"   データ: {data_path}")
    print(f"   出力: {output_dir}")
    print(f"   Rank: {rank}, Alpha: {lora_alpha}")

    if not TRANSFORMERS_AVAILABLE:
        print("\n❌ 必要なパッケージがインストールされていません")
        print("   インストール: pip install transformers peft bitsandbytes accelerate")
        return

    # データ読み込み
    data = load_sft_data(data_path)
    print(f"   ✅ データ読み込み: {len(data)}件")

    # トークナイザー読み込み
    print("📦 トークナイザー読み込み中...")
    tokenizer = AutoTokenizer.from_pretrained(base_model)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # モデル読み込み（4bit量子化）
    print("📦 モデル読み込み中（4bit量子化）...")
    bnb_config = None
    if use_4bit:
        bnb_config = bnb.config.BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True
        )

    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True
    )

    # QLoRA設定
    model = prepare_model_for_kbit_training(model)

    lora_config = LoraConfig(
        r=rank,
        lora_alpha=lora_alpha,
        target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
        lora_dropout=lora_dropout,
        bias="none",
        task_type="CAUSAL_LM"
    )

    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # データセット作成
    print("📊 データセット作成中...")
    dataset = SFTDataset(data, tokenizer, max_length=max_length)

    # 学習設定
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=num_epochs,
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=4,
        learning_rate=learning_rate,
        fp16=True,
        logging_steps=10,
        save_steps=100,
        save_total_limit=3,
        optim="paged_adamw_32bit",
        warmup_steps=100,
        report_to="none"
    )

    # Trainer作成
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        data_collator=DataCollatorForLanguageModeling(
            tokenizer=tokenizer,
            mlm=False
        )
    )

    # 学習実行
    print("\n🎯 学習開始...")
    trainer.train()

    # 保存
    print(f"\n💾 モデル保存中: {output_dir}")
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)

    # 設定保存
    config = {
        "base_model": base_model,
        "data_path": data_path,
        "output_dir": output_dir,
        "rank": rank,
        "lora_alpha": lora_alpha,
        "lora_dropout": lora_dropout,
        "batch_size": batch_size,
        "num_epochs": num_epochs,
        "learning_rate": learning_rate,
        "data_count": len(data),
        "max_length": max_length
    }

    config_file = Path(output_dir) / "training_config.json"
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"✅ 学習完了！出力: {output_dir}")


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description="QLoRA SFT学習")
    parser.add_argument("--base", required=True, help="ベースモデル名")
    parser.add_argument("--data", required=True, help="SFTデータファイル")
    parser.add_argument("--out", required=True, help="出力ディレクトリ")
    parser.add_argument("--rank", type=int, default=16, help="LoRA rank")
    parser.add_argument("--alpha", type=int, default=32, help="LoRA alpha")
    parser.add_argument("--batch-size", type=int, default=4, help="バッチサイズ")
    parser.add_argument("--epochs", type=int, default=3, help="エポック数")
    args = parser.parse_args()

    train_sft_lora(
        base_model=args.base,
        data_path=args.data,
        output_dir=args.out,
        rank=args.rank,
        lora_alpha=args.alpha,
        batch_size=args.batch_size,
        num_epochs=args.epochs
    )


if __name__ == "__main__":
    main()

