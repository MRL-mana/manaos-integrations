#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CASTLE-EX LoRA 学習スクリプト（Layer2専用 v1.1 → v1.1.1）
PEFTを使用したLoRA学習による部分的パラメータ更新
"""

import sys
import os
import argparse
import logging
import datetime
from pathlib import Path

# 事前にCUDAを無効化するオプションを拾い、torch import前に適用
if "--no-cuda" in sys.argv:
    os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
    os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"

# Windows環境対策
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except (AttributeError, ValueError, TypeError):
        pass

    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
    os.environ.setdefault("TQDM_DISABLE", "1")
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

try:
    import torch
    from transformers import (
        AutoTokenizer,
        AutoModelForCausalLM,
        TrainingArguments,
        Trainer,
        TrainerCallback,
        DataCollatorForLanguageModeling,
    )
    from peft import LoraConfig, get_peft_model, PeftModel
    from datasets import load_dataset
except ImportError as e:
    print(f"[ERROR] 必要なライブラリがインストールされていません: {e}")
    print("[INFO] 以下のコマンドでインストールしてください:")
    print("  pip install peft datasets accelerate bitsandbytes")
    sys.exit(1)

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("training_lora.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
    force=True,
)
logger = logging.getLogger(__name__)


class ProgressLoggingCallback(TrainerCallback):
    def __init__(self, progress_logger: logging.Logger, progress_log_path: Path | None = None):
        super().__init__()
        self._logger = progress_logger
        self._progress_log_path = progress_log_path

    def _append_progress_file(self, line: str) -> None:
        if self._progress_log_path is None:
            return
        try:
            self._progress_log_path.parent.mkdir(parents=True, exist_ok=True)
            with self._progress_log_path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            # ファイル書き込み失敗は学習を止めない
            return

    def on_log(self, args, state, control, logs=None, **kwargs):  # type: ignore[override]
        if not logs:
            return

        step = getattr(state, "global_step", None)
        selected_keys = ["loss", "eval_loss", "learning_rate", "grad_norm"]
        parts = []
        if step is not None:
            parts.append(f"step={step}")
        for key in selected_keys:
            if key in logs:
                parts.append(f"{key}={logs[key]}")
        if parts:
            msg = "progress: " + ", ".join(parts)
            self._logger.info(msg)
            self._append_progress_file(f"{datetime.datetime.now().isoformat()} {msg}")
            for handler in self._logger.handlers:
                if hasattr(handler, "flush"):
                    handler.flush()


class StopFileCallback(TrainerCallback):
    def __init__(self, stop_file: Path, stop_logger: logging.Logger):
        super().__init__()
        self._stop_file = stop_file
        self._logger = stop_logger

    def on_train_begin(self, args, state, control, **kwargs):  # type: ignore[override]
        if self._stop_file.exists():
            self._logger.warning(f"STOPファイルが既に存在します: {self._stop_file}")
            self._logger.warning("次のstep終端で保存して停止します（必要ならSTOPファイルを削除してください）")

    def on_step_end(self, args, state, control, **kwargs):  # type: ignore[override]
        if not self._stop_file.exists():
            return control

        step = getattr(state, "global_step", "?")
        self._logger.warning(f"STOPファイル検知: step={step} -> 保存して停止します")

        # このstepで強制的に保存してから止める
        control.should_save = True
        control.should_training_stop = True

        # 再開時に即停止しないよう、STOPファイルは削除する
        try:
            self._stop_file.unlink(missing_ok=True)
            self._logger.info(f"STOPファイルを削除しました: {self._stop_file}")
        except Exception as e:
            self._logger.warning(f"STOPファイル削除に失敗: {type(e).__name__}: {e}")

        for handler in self._logger.handlers:
            if hasattr(handler, "flush"):
                handler.flush()
        return control


def parse_args():
    """コマンドライン引数パース"""
    parser = argparse.ArgumentParser(description="CASTLE-EX LoRA学習")
    
    # 必須引数
    parser.add_argument(
        "--base-model",
        type=str,
        required=True,
        help="ベースモデルのパス（v1.1フルFT済みモデル）",
    )
    parser.add_argument(
        "--train-data",
        type=str,
        required=True,
        help="学習データ（JSONL形式）",
    )
    parser.add_argument(
        "--eval-data",
        type=str,
        required=True,
        help="評価データ（JSONL形式）",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        required=True,
        help="LoRAモデル出力ディレクトリ",
    )
    
    # LoRA設定
    parser.add_argument(
        "--lora-r",
        type=int,
        default=16,
        help="LoRA rank（デフォルト: 16）",
    )
    parser.add_argument(
        "--lora-alpha",
        type=int,
        default=32,
        help="LoRA alpha（デフォルト: 32）",
    )
    parser.add_argument(
        "--lora-dropout",
        type=float,
        default=0.05,
        help="LoRA dropout（デフォルト: 0.05）",
    )
    parser.add_argument(
        "--target-modules",
        type=str,
        default="q_proj,k_proj,v_proj,o_proj",
        help="LoRA適用対象モジュール（カンマ区切り、デフォルト: q_proj,k_proj,v_proj,o_proj）",
    )
    
    # 学習設定
    parser.add_argument(
        "--max-length",
        type=int,
        default=512,
        help="最大トークン長（デフォルト: 512）",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=2,
        help="バッチサイズ（デフォルト: 2）",
    )
    parser.add_argument(
        "--gradient-accumulation-steps",
        type=int,
        default=8,
        help="勾配累積ステップ（デフォルト: 8）",
    )
    parser.add_argument(
        "--learning-rate",
        type=float,
        default=2e-4,
        help="学習率（デフォルト: 2e-4）",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=2000,
        help="最大学習ステップ（デフォルト: 2000）",
    )
    parser.add_argument(
        "--save-steps",
        type=int,
        default=100,
        help="チェックポイント保存間隔（デフォルト: 100）",
    )
    parser.add_argument(
        "--eval-steps",
        type=int,
        default=100,
        help="評価実行間隔（デフォルト: 100）",
    )
    parser.add_argument(
        "--fp16",
        action="store_true",
        default=True,
        help="FP16学習を有効化（デフォルト: True）",
    )
    parser.add_argument(
        "--no-fp16",
        action="store_true",
        help="FP16学習を無効化",
    )
    parser.add_argument(
        "--resume-from-checkpoint",
        type=str,
        default=None,
        help="チェックポイントから再開（'auto'で最新を自動検出、またはcheckpoint-XXXパスを指定）",
    )
    parser.add_argument(
        "--no-cuda",
        action="store_true",
        help="CUDAを無効化してCPUのみで実行",
    )
    parser.add_argument(
        "--attn-implementation",
        type=str,
        default="eager",
        choices=["eager", "sdpa", "flash_attention_2"],
        help="Attention実装（SM 120対応を維持するたeager推奨）",
    )

    
    args = parser.parse_args()
    
    # fp16フラグの処理
    if args.no_fp16:
        args.fp16 = False
    if args.no_cuda:
        # CPU強制実行：複数の環境変数と明示的な設定
        os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
        os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
        # pytorchのCUDA使用を完全に無効化
        import torch
        if hasattr(torch.cuda, 'is_available'):
            torch.cuda.is_available = lambda: False
        args.fp16 = False  # CPU実行ではfp16を無効化
    
    return args


def format_messages_phi3(messages):
    """Phi3 チャット形式に変換（v1.1 と同一）"""
    parts = []
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "user":
            parts.append(f"<|user|>\n{content}<|end|>\n")
        elif role == "assistant":
            parts.append(f"<|assistant|>\n{content}<|end|>\n")
    return "".join(parts)


def tokenize_function(tokenizer, max_length):
    """トークン化関数（Phi3形式・v1.1 と同一）。labels は DataCollator が付与。"""
    def tokenize(example):
        text = format_messages_phi3(example["messages"])
        tokenized = tokenizer(
            text,
            truncation=True,
            max_length=max_length,
            padding="max_length",
            return_attention_mask=True,
            return_tensors=None,
        )
        # labels は DataCollatorForLanguageModeling が input_ids から作成するためここでは付けない
        # （付けるとバッチ時に list のネストでエラーになる）
        return tokenized
    return tokenize


def main():
    args = parse_args()
    
    logger.info("=" * 60)
    logger.info("CASTLE-EX LoRA 学習開始")
    logger.info("=" * 60)
    logger.info(f"ベースモデル: {args.base_model}")
    logger.info(f"学習データ: {args.train_data}")
    logger.info(f"評価データ: {args.eval_data}")
    logger.info(f"出力先: {args.output_dir}")
    logger.info(f"LoRA設定: r={args.lora_r}, alpha={args.lora_alpha}, dropout={args.lora_dropout}")
    logger.info(f"対象モジュール: {args.target_modules}")
    logger.info(f"学習設定: lr={args.learning_rate}, max_steps={args.max_steps}, batch_size={args.batch_size}")
    logger.info("-" * 60)
    
    # 1. トークナイザーロード
    logger.info("トークナイザーをロード中...")
    tokenizer = AutoTokenizer.from_pretrained(args.base_model, use_fast=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        logger.info("pad_tokenを設定しました")
    
    # 2. データセット準備
    logger.info("データセットをロード中...")
    train_dataset = load_dataset("json", data_files=args.train_data)["train"]
    eval_dataset = load_dataset("json", data_files=args.eval_data)["train"]
    
    logger.info(f"学習データ件数: {len(train_dataset)}")
    logger.info(f"評価データ件数: {len(eval_dataset)}")
    
    # トークン化
    logger.info("データをトークン化中...")
    tokenize_fn = tokenize_function(tokenizer, args.max_length)
    # 入力に含まれるメタ情報をすべて削除し、トークン化結果のみを残す
    cols_to_remove_train = train_dataset.column_names
    cols_to_remove_eval = eval_dataset.column_names

    logger.info("学習データトークン化開始...")
    train_dataset = train_dataset.map(
        tokenize_fn,
        remove_columns=cols_to_remove_train,
    )
    logger.info(f"学習データトークン化完了: {len(train_dataset)} samples")
    logger.info("評価データトークン化開始...")
    eval_dataset = eval_dataset.map(
        tokenize_fn,
        remove_columns=cols_to_remove_eval,
    )
    logger.info(f"評価データトークン化完了: {len(eval_dataset)} samples")
    
    # 3. ベースモデルロード
    logger.info("ベースモデルをロード中...")
    
    # Windowsでのページファイル不足(1455)回避のため、GPU利用時は軽量ロードを優先
    model_dtype = (
        torch.float16
        if (torch.cuda.is_available() and not args.no_cuda and args.fp16)
        else torch.float32
    )
    logger.info(f"モデルロードdtype: {model_dtype}")

    base_model = AutoModelForCausalLM.from_pretrained(
        args.base_model,
        torch_dtype=model_dtype,
        trust_remote_code=True,
        low_cpu_mem_usage=True,
        attn_implementation=args.attn_implementation,
    )
    
    # GPUに移動（device_mapを使わずに明示的に移動）
    if torch.cuda.is_available() and not args.no_cuda:
        logger.info("モデルをGPUに移動中...")
        base_model = base_model.to("cuda")
        logger.info(f"GPU移動完了: {torch.cuda.get_device_name(0)}")
    
    logger.info(f"モデルロード完了: {base_model.config.model_type}")
    logger.info(f"Attention実装: {args.attn_implementation}")
    logger.info(f"モデルデバイス: {next(base_model.parameters()).device}")
    
    # 4. LoRA設定
    logger.info("LoRA設定を適用中...")
    target_modules_list = [m.strip() for m in args.target_modules.split(",")]
    
    lora_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        target_modules=target_modules_list,
        bias="none",
        task_type="CAUSAL_LM",
    )
    
    # PEFTモデル作成
    model = get_peft_model(base_model, lora_config)
    logger.info("LoRA適用完了")
    model.print_trainable_parameters()
    
    # 5. Data Collator
    data_collator = DataCollatorForLanguageModeling(tokenizer, mlm=False)
    
    # 6. 学習設定（確定レシピ: batch_size=2, fp16 when GPU）
    use_fp16 = args.fp16 and torch.cuda.is_available() and not args.no_cuda
    training_kwargs = dict(
        output_dir=args.output_dir,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        learning_rate=args.learning_rate,
        max_steps=args.max_steps,
        save_steps=args.save_steps,
        eval_steps=args.eval_steps,
        eval_strategy="steps",
        save_strategy="steps",
        logging_steps=50,
        logging_dir=args.output_dir + "/logs",
        fp16=use_fp16,
        report_to="none",
        remove_unused_columns=False,
        load_best_model_at_end=False,
        save_total_limit=3,
        dataloader_num_workers=0,
        dataloader_pin_memory=False,
        optim="adamw_torch",
    )
    # CPU強制実行時: use_cpu を設定（transformers >= 4.36）
    if args.no_cuda:
        try:
            training_kwargs["use_cpu"] = True
        except Exception:
            pass
    training_args = TrainingArguments(**training_kwargs)

    output_dir_path = Path(args.output_dir)
    stop_file = output_dir_path / "STOP_TRAINING"
    progress_file = output_dir_path / "progress.log"
    
    # 7. Trainer初期化
    logger.info("Trainerを初期化中...")
    logger.info(f"実行環境: {'CPU only' if args.no_cuda else 'Auto (GPU if available)'}")
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        data_collator=data_collator,
        callbacks=[ProgressLoggingCallback(logger, progress_file), StopFileCallback(stop_file, logger)],
    )
    
    # 8. 学習実行
    logger.info("=" * 60)
    logger.info("学習を開始します...")
    logger.info("=" * 60)
    logger.info(f"トレーニング開始時刻: {datetime.datetime.now()}")
    logger.info(f"総ステップ数: {args.max_steps}")
    logger.info(f"チェックポイント保存間隔: {args.save_steps}ステップ")
    logger.info("最初のステップが遅い場合があります（初期化処理）")
    logger.info(f"途中停止したい場合は STOPファイルを作成: {stop_file}")
    
    # チェックポイントから再開の処理
    resume_from_checkpoint = None
    if args.resume_from_checkpoint:
        if args.resume_from_checkpoint.lower() == "auto":
            # 最新のcheckpointを自動検出
            output_path = Path(args.output_dir)
            checkpoints = sorted([d for d in output_path.iterdir() if d.is_dir() and d.name.startswith("checkpoint-")], 
                                key=lambda x: int(x.name.split("-")[1]) if x.name.split("-")[1].isdigit() else -1)
            if checkpoints:
                latest = checkpoints[-1]
                trainer_state = latest / "trainer_state.json"
                if trainer_state.exists():
                    resume_from_checkpoint = str(latest)
                    logger.info(f"有効なチェックポイントを自動検出: {resume_from_checkpoint}")
                else:
                    logger.warning(f"checkpoint-XXX/trainer_state.json が見つかりません: {latest}")
            else:
                logger.warning("再開可能なチェックポイントが見つかりません")
        else:
            requested = Path(args.resume_from_checkpoint)
            if requested.exists() and (requested / "trainer_state.json").exists():
                resume_from_checkpoint = str(requested)
                logger.info(f"指定されたチェックポイントから再開: {resume_from_checkpoint}")
            else:
                logger.warning(f"指定されたチェックポイントが無効です: {requested}")
    
    # ログをフラッシュ
    for handler in logger.handlers:
        if hasattr(handler, 'flush'):
            handler.flush()
    
    def _save_checkpoint_on_stop():
        """Ctrl+C 時などに現在のステップをチェックポイントとして保存"""
        step = trainer.state.global_step
        if step <= 0:
            logger.warning("保存可能なステップがありません")
            return
        ckpt_dir = os.path.join(args.output_dir, f"checkpoint-{step}")
        os.makedirs(ckpt_dir, exist_ok=True)
        logger.info(f"中断時のチェックポイントを保存中: {ckpt_dir}")
        trainer.save_model(ckpt_dir)
        tokenizer.save_pretrained(ckpt_dir)
        trainer.state.save_to_json(os.path.join(ckpt_dir, "trainer_state.json"))
        if trainer.optimizer is not None and hasattr(trainer.optimizer, "state_dict"):
            torch.save(trainer.optimizer.state_dict(), os.path.join(ckpt_dir, "optimizer.pt"))
        if hasattr(trainer, "lr_scheduler") and trainer.lr_scheduler is not None:
            torch.save(trainer.lr_scheduler.state_dict(), os.path.join(ckpt_dir, "scheduler.pt"))
        logger.info(f"保存完了: {ckpt_dir} (step {step})")

    try:
        trainer.train(resume_from_checkpoint=resume_from_checkpoint)
        logger.info("学習が正常に完了しました")
    except KeyboardInterrupt:
        logger.warning("キーボード割り込みで中断されました。現在の状態を保存します...")
        try:
            _save_checkpoint_on_stop()
        except Exception as e:
            logger.error(f"チェックポイント保存に失敗: {e}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"学習中にエラーが発生しました: {type(e).__name__}: {e}", exc_info=True)
        raise
    
    # 9. モデル保存
    logger.info("LoRAモデルを保存中...")
    trainer.save_model(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    
    logger.info("=" * 60)
    logger.info("LoRA学習が完了しました")
    logger.info(f"出力先: {args.output_dir}")
    logger.info("=" * 60)
    logger.info("")
    logger.info("次のステップ:")
    logger.info("1. 評価実行:")
    logger.info(f"   python -m castle_ex.castle_ex_evaluator_fixed \\")
    logger.info(f"     --eval-data castle_ex_dataset_v1_1_eval.jsonl \\")
    logger.info(f"     --model-type transformers \\")
    logger.info(f"     --model {args.base_model} \\")
    logger.info(f"     --lora {args.output_dir} \\")
    logger.info(f"     --output evaluation_v1_1_1_layer2_lora.json")
    logger.info("")


if __name__ == "__main__":
    main()
