#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CASTLE-EX 完全学習スクリプト（Transformers直接使用）
現在の環境（Python 3.10.6 + PyTorch + Transformers）で学習を実行
"""

import sys
import json
import os
import shutil
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import argparse

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except (AttributeError, ValueError, TypeError):
        pass

    # Windows での tqdm / progress bar 起因クラッシュ回避（Errno 22 対策）
    # - huggingface-hub の進捗バー無効化
    # - tqdm を環境変数でも無効化
    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
    os.environ.setdefault("TQDM_DISABLE", "1")

    # プロキシエラー回避: オフラインモードとプロキシ無効化
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    # プロキシ設定を無効化（Windows環境でのプロキシエラー回避）
    if "http_proxy" in os.environ:
        del os.environ["http_proxy"]
    if "https_proxy" in os.environ:
        del os.environ["https_proxy"]
    if "HTTP_PROXY" in os.environ:
        del os.environ["HTTP_PROXY"]
    if "HTTPS_PROXY" in os.environ:
        del os.environ["HTTPS_PROXY"]
    os.environ.setdefault("NO_PROXY", "*")

try:
    import torch
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        TrainingArguments,
        Trainer,
        DataCollatorForLanguageModeling,
        BitsAndBytesConfig,
    )
    from datasets import Dataset

    TRANSFORMERS_AVAILABLE = True
except ImportError as e:
    TRANSFORMERS_AVAILABLE = False
    IMPORT_ERROR = str(e)

# transformers 側の progress bar を可能なら無効化（バージョン差異に備えて try/except）
try:
    from transformers.utils import logging as hf_logging

    hf_logging.disable_progress_bar()
except Exception:
    pass

# ログ設定
log_file_path = Path("training.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(str(log_file_path), encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
    force=True,  # 既存のハンドラを上書き
)
logger = logging.getLogger(__name__)


def load_schedule(schedule_file: str = "castle_ex_schedule_v1_0.json") -> Optional[Dict]:
    """学習スケジュールを読み込む"""
    schedule_path = Path(schedule_file)
    if not schedule_path.exists():
        print(f"[警告] 学習スケジュールファイルが見つかりません: {schedule_file}")
        return None

    with open(schedule_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_dataset_jsonl(jsonl_file: str) -> List[Dict]:
    """JSONLファイルからデータセットを読み込む"""
    data = []
    with open(jsonl_file, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
                data.append(item)
            except json.JSONDecodeError as e:
                print(f"[警告] 行{line_num}でJSON解析エラー: {e}")

    return data


def format_messages_for_training(item: Dict, tokenizer) -> str:
    """messages形式のデータを学習用テキストに変換"""
    messages = item.get("messages", [])
    if not messages:
        return ""

    # Phi-3形式のチャットテンプレートを使用
    # または、シンプルな形式でフォーマット
    formatted_parts = []

    # システムメッセージがある場合は最初に配置
    system_content = None
    for msg in messages:
        if msg.get("role") == "system":
            system_content = msg.get("content", "")
            break

    if system_content:
        formatted_parts.append(f"<|system|>\n{system_content}<|end|>\n")

    # ユーザーとアシスタントの対話をフォーマット
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")

        if role == "system":
            continue  # 既に処理済み
        elif role == "user":
            formatted_parts.append(f"<|user|>\n{content}<|end|>\n")
        elif role == "assistant":
            formatted_parts.append(f"<|assistant|>\n{content}<|end|>\n")

    return "".join(formatted_parts)


def preprocess_dataset(data: List[Dict], tokenizer, max_length: int = 2048):
    """データセットを前処理"""
    processed = []

    for idx, item in enumerate(data):
        if idx % 100 == 0:
            print(f"  前処理中: {idx}/{len(data)}件", end="\r")

        text = format_messages_for_training(item, tokenizer)
        if not text:
            continue

        # トークン化（labels は DataCollator が input_ids から作るので渡さない）
        encoded = tokenizer(
            text,
            truncation=True,
            max_length=max_length,
            padding=False,
            return_tensors=None,
        )
        input_ids = encoded["input_ids"]
        attention_mask = encoded.get("attention_mask", [1] * len(input_ids))
        processed.append(
            {
                "input_ids": input_ids,
                "attention_mask": attention_mask,
            }
        )

    print(f"  前処理完了: {len(processed)}/{len(data)}件")
    return processed


def check_environment():
    """環境確認"""
    print("=" * 60)
    print("環境確認")
    print("=" * 60)

    print(f"Python: {sys.version.split()[0]}")

    if not TRANSFORMERS_AVAILABLE:
        print(f"[エラー] Transformersが利用できません: {IMPORT_ERROR}")
        return False

    print(f"PyTorch: {torch.__version__}")
    print(f"Transformers: 利用可能")

    if torch.cuda.is_available():
        print(f"CUDA: 利用可能 ({torch.cuda.get_device_name(0)})")
        print(f"CUDA Device Count: {torch.cuda.device_count()}")
    else:
        print("CUDA: 利用不可（CPUモード）")

    return True


def _checkpoint_step(checkpoint_dir: Path) -> int:
    """checkpoint-XXXX からステップ番号を抽出（失敗時は-1）"""
    try:
        parts = checkpoint_dir.name.split("-")
        if len(parts) >= 2 and parts[1].isdigit():
            return int(parts[1])
    except Exception:
        pass
    return -1


def _is_valid_trainer_checkpoint(checkpoint_dir: Path) -> bool:
    """
    Trainerのresumeに必要な最低条件を満たすか判定。
    現場で起きている「checkpointはあるが trainer_state.json が無い」ケースを弾く。
    """
    try:
        return (checkpoint_dir / "trainer_state.json").exists()
    except Exception:
        return False


def find_latest_valid_checkpoint(output_dir: Path) -> Optional[Path]:
    """trainer_state.json を持つ checkpoint-* のうち最新を返す（なければNone）"""
    candidates = [p for p in output_dir.glob("checkpoint-*") if p.is_dir()]
    valid = [p for p in candidates if _is_valid_trainer_checkpoint(p)]
    if not valid:
        return None
    return max(valid, key=_checkpoint_step)


def check_disk_space(path: Path, required_gb: float = 5.0) -> Tuple[bool, float, float]:
    """
    ディスク容量をチェック

    Args:
        path: チェックするパス
        required_gb: 必要な容量（GB、デフォルト: 5GB）

    Returns:
        (is_sufficient, free_gb, total_gb)
    """
    try:
        stat = shutil.disk_usage(path)
        free_gb = stat.free / (1024**3)
        total_gb = stat.total / (1024**3)
        is_sufficient = free_gb >= required_gb
        return is_sufficient, free_gb, total_gb
    except Exception as e:
        logger.warning(f"ディスク容量チェック失敗: {e}")
        return True, 0.0, 0.0  # チェック失敗時は警告のみ


def test_write_access(path: Path) -> bool:
    """
    書き込みアクセステスト

    Args:
        path: テストするパス

    Returns:
        書き込み可能かどうか
    """
    try:
        test_file = path / ".write_test"
        test_file.write_text("test", encoding="utf-8")
        test_file.unlink()
        return True
    except Exception as e:
        logger.error(f"書き込みテスト失敗: {e}")
        return False


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description="CASTLE-EX 完全学習スクリプト")
    parser.add_argument(
        "--model",
        type=str,
        default="microsoft/Phi-3-mini-4k-instruct",
        help="ベースモデル（デフォルト: microsoft/Phi-3-mini-4k-instruct）",
    )
    parser.add_argument(
        "--model-revision",
        type=str,
        default=None,
        help="HuggingFaceのmodel revision（commit hash / tag）。固定すると再現性が上がります。",
    )
    parser.add_argument(
        "--train-data",
        type=str,
        default="castle_ex_dataset_v1_0_train.jsonl",
        help="訓練データファイル",
    )
    parser.add_argument(
        "--eval-data",
        type=str,
        default="castle_ex_dataset_v1_0_eval.jsonl",
        help="評価データファイル",
    )
    parser.add_argument(
        "--no-eval",
        action="store_true",
        help="評価を無効化（eval_datasetを作らず、eval_strategy=no）。DynamicCache系エラー回避用。",
    )
    parser.add_argument(
        "--output-dir", type=str, default="./outputs/castle_ex_v1_0", help="出力ディレクトリ"
    )
    parser.add_argument("--epochs", type=int, default=25, help="エポック数（デフォルト: 25）")
    parser.add_argument(
        "--max-steps",
        type=int,
        default=-1,
        help="最大ステップ数（指定時はepochsを無視、v1.1検証用に1000〜2000など）",
    )
    parser.add_argument("--batch-size", type=int, default=2, help="バッチサイズ（デフォルト: 2）")
    parser.add_argument(
        "--learning-rate", type=float, default=2.0e-5, help="学習率（デフォルト: 2.0e-5）"
    )
    parser.add_argument(
        "--max-length", type=int, default=2048, help="最大シーケンス長（デフォルト: 2048）"
    )
    parser.add_argument(
        "--check-only", action="store_true", help="環境確認のみ実行（学習は実行しない）"
    )
    parser.add_argument(
        "--resume-from-checkpoint",
        type=str,
        default=None,
        help='チェックポイントから再開（パスを指定、または"auto"で自動検出）',
    )
    parser.add_argument(
        "--save-steps",
        type=int,
        default=100,
        help="チェックポイント保存間隔（steps、デフォルト: 100）",
    )
    parser.add_argument(
        "--save-total-limit",
        type=int,
        default=3,
        help="保持するチェックポイント上限（古いものを自動削除、デフォルト: 3）",
    )
    parser.add_argument(
        "--logging-steps", type=int, default=25, help="ログ出力間隔（steps、デフォルト: 25）"
    )
    parser.add_argument(
        "--eval-steps", type=int, default=100, help="評価実行間隔（steps、デフォルト: 100）"
    )
    parser.add_argument(
        "--load-best-model-at-end",
        action="store_true",
        help="eval loss最小のモデルを最後に読み込む（save_steps と eval_steps の整合が必要）",
    )
    parser.add_argument(
        "--attn-implementation",
        type=str,
        default="eager",
        choices=["eager", "sdpa", "flash_attention_2"],
        help="Attention実装（illegal memory access回避のためeager推奨）",
    )
    parser.add_argument(
        "--no-gradient-checkpointing",
        action="store_true",
        help="Gradient Checkpointingを無効化（illegal memory access切り分け用）",
    )

    args = parser.parse_args()

    print("CASTLE-EX 完全学習スクリプト")
    print("=" * 60)
    logger.info("CASTLE-EX 完全学習スクリプト開始")

    # 環境確認
    if not check_environment():
        error_msg = "必要なライブラリがインストールされていません"
        print(f"\n[エラー] {error_msg}")
        print("以下のコマンドでインストールしてください:")
        print("  pip install transformers datasets accelerate")
        logger.error(error_msg)
        return 1

    # ファイル確認
    train_file = Path(args.train_data)
    if not train_file.exists():
        error_msg = f"訓練データが見つかりません: {train_file}"
        print(f"\n[エラー] {error_msg}")
        logger.error(error_msg)
        return 1

    eval_file = None
    if args.no_eval:
        print("\n[情報] --no-eval が指定されたため、評価を無効化します")
    else:
        candidate = Path(args.eval_data)
        if not candidate.exists():
            print(f"\n[警告] 評価データが見つかりません: {candidate}")
            eval_file = None
        else:
            eval_file = candidate

    # 学習スケジュール読み込み
    schedule = load_schedule()
    if schedule:
        print(f"\n学習スケジュール: {schedule['total_epochs']}エポック")
        print(f"Phase 1 (Epoch 1-3): ウォームアップ")
        print(f"Phase 2 (Epoch 4-10): 因果と統合へ寄せる")
        print(f"Phase 3 (Epoch 11-25): 実戦")

    if args.check_only:
        print("\n[OK] 環境確認完了")
        return 0

    print("\n" + "=" * 60)
    print("データセット読み込み")
    print("=" * 60)

    # データセット読み込み
    print(f"訓練データを読み込み中: {train_file}")
    logger.info(f"訓練データ読み込み開始: {train_file}")
    train_data = load_dataset_jsonl(str(train_file))
    print(f"  読み込み完了: {len(train_data)}件")
    logger.info(f"訓練データ読み込み完了: {len(train_data)}件")

    if eval_file:
        print(f"評価データを読み込み中: {eval_file}")
        eval_data = load_dataset_jsonl(str(eval_file))
        print(f"  読み込み完了: {len(eval_data)}件")
    else:
        eval_data = None

    print("\n" + "=" * 60)
    print("モデルとトークナイザーの読み込み")
    print("=" * 60)

    print(f"モデル: {args.model}")
    print("読み込み中...")

    try:
        print("トークナイザーを読み込み中...")
        tokenizer = AutoTokenizer.from_pretrained(
            args.model,
            trust_remote_code=True,
            revision=args.model_revision,
            local_files_only=True,  # プロキシエラー回避: ローカルキャッシュのみ使用
        )
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        print("[OK] トークナイザー読み込み完了")

        print("モデルを読み込み中...")
        # VRAM節約のため、低リソース設定を使用
        # FP16はTrainingArgumentsで処理するため、モデルロード時はFP32にしておく
        try:
            model = AutoModelForCausalLM.from_pretrained(
                args.model,
                torch_dtype=torch.float32,  # TrainingArgumentsのfp16で自動的にFP16に変換
                trust_remote_code=True,
                low_cpu_mem_usage=False,  # checkpoint再開時のmeta tensor問題回避
                attn_implementation=args.attn_implementation,
                revision=args.model_revision,
                local_files_only=True,  # プロキシエラー回避: ローカルキャッシュのみ使用
            )
            # GPUに移動（device_mapを使わずに明示的に移動）
            if torch.cuda.is_available():
                model = model.to("cuda")
        except TypeError:
            # Transformersのバージョン差異でattn_implementationが無い場合
            model = AutoModelForCausalLM.from_pretrained(
                args.model,
                torch_dtype=torch.float32,
                trust_remote_code=True,
                low_cpu_mem_usage=False,  # checkpoint再開時のmeta tensor問題回避
                revision=args.model_revision,
                local_files_only=True,  # プロキシエラー回避: ローカルキャッシュのみ使用
            )
            # GPUに移動
            if torch.cuda.is_available():
                model = model.to("cuda")
        print("[OK] モデル読み込み完了")

        # Gradient Checkpointingを有効化（VRAM節約）
        if not args.no_gradient_checkpointing and hasattr(model, "gradient_checkpointing_enable"):
            model.gradient_checkpointing_enable()
            print("[OK] Gradient Checkpointingを有効化しました（VRAM節約）")
        elif args.no_gradient_checkpointing:
            print("[情報] Gradient Checkpointingを無効化しました（切り分け用）")

        if torch.cuda.is_available():
            gpu_memory = torch.cuda.memory_allocated(0) / 1024**3
            gpu_total = torch.cuda.get_device_properties(0).total_memory / 1024**3
            print(f"GPUメモリ使用量: {gpu_memory:.2f}GB / {gpu_total:.2f}GB")
            logger.info(f"GPUメモリ使用量: {gpu_memory:.2f}GB / {gpu_total:.2f}GB")
    except Exception as e:
        error_msg = f"モデルの読み込みに失敗しました: {e}"
        print(f"[エラー] {error_msg}")
        logger.exception(error_msg)
        import traceback

        traceback.print_exc()
        return 1

    print("\n" + "=" * 60)
    print("データセット前処理")
    print("=" * 60)

    print("訓練データを前処理中...")
    train_processed = preprocess_dataset(train_data, tokenizer, args.max_length)
    print(f"  前処理完了: {len(train_processed)}件")

    if eval_data:
        print("評価データを前処理中...")
        eval_processed = preprocess_dataset(eval_data, tokenizer, args.max_length)
        print(f"  前処理完了: {len(eval_processed)}件")
    else:
        eval_processed = None

    # Datasetオブジェクトに変換
    print("\nデータセットオブジェクトを作成中...")
    train_dataset = Dataset.from_list(train_processed)
    print(f"  訓練データセット: {len(train_dataset)}件")

    if eval_processed:
        eval_dataset = Dataset.from_list(eval_processed)
        print(f"  評価データセット: {len(eval_dataset)}件")
    else:
        eval_dataset = None
        print("  評価データセット: なし")

    print("\n" + "=" * 60)
    print("学習設定")
    print("=" * 60)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ディスク容量チェック
    print("\n[ディスク容量チェック]")
    is_sufficient, free_gb, total_gb = check_disk_space(output_dir, required_gb=5.0)
    print(f"  空き容量: {free_gb:.2f}GB / {total_gb:.2f}GB")
    if not is_sufficient:
        print(f"  [WARN] 空き容量が5GB未満です（現在: {free_gb:.2f}GB）")
        print("  checkpoint保存時に失敗する可能性があります")
        print("  推奨: 最低5GB以上の空き容量を確保してください")
        print("  [NG] ディスク容量不足のため学習を中止します（非対話モード）")
        logger.error("ディスク容量不足のため学習を中止しました（非対話モード）")
        return 1
    else:
        print("  [OK] ディスク容量は十分です")

    # 書き込みテスト
    print("\n[書き込みテスト]")
    if test_write_access(output_dir):
        print("  [OK] 書き込みテスト成功")
        logger.info(f"書き込みテスト成功: {output_dir}")
    else:
        print(f"  [NG] 書き込みテスト失敗: {output_dir}")
        logger.error(f"書き込みテスト失敗: {output_dir}")
        return 1

    # VRAM節約のための設定
    # RTX 5080 (15.9GB) では batch_size=2, max_length=2048 は厳しい
    # より安全な設定に調整
    effective_batch_size = args.batch_size * 4  # gradient_accumulation_steps=4
    print(f"実効バッチサイズ: {effective_batch_size}")

    # load_best_model_at_end を使う場合は save_steps が eval_steps の倍数である必要がある
    load_best_model_at_end = bool(eval_dataset) and bool(args.load_best_model_at_end)
    eval_steps = args.eval_steps if eval_dataset else None
    if load_best_model_at_end and eval_steps:
        if args.save_steps % eval_steps != 0:
            print(
                "[警告] load_best_model_at_end=True のため、eval_steps を save_steps に合わせます"
            )
            print(
                f"       save_steps={args.save_steps}, eval_steps={eval_steps} -> eval_steps={args.save_steps}"
            )
            eval_steps = args.save_steps

    _max_steps = args.max_steps if args.max_steps > 0 else -1
    training_args = TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=args.epochs,
        max_steps=_max_steps,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        gradient_accumulation_steps=8,  # メモリ不足対策: 4→8に増加
        learning_rate=args.learning_rate,
        warmup_steps=100,
        logging_steps=args.logging_steps,
        save_steps=args.save_steps,
        save_total_limit=args.save_total_limit,
        eval_steps=eval_steps,
        eval_strategy="steps" if eval_dataset else "no",  # evaluation_strategy -> eval_strategy
        save_strategy="steps",
        load_best_model_at_end=load_best_model_at_end,
        metric_for_best_model="loss" if load_best_model_at_end else None,
        greater_is_better=False if load_best_model_at_end else None,
        fp16=torch.cuda.is_available(),
        bf16=False,
        dataloader_num_workers=0,  # Windowsでの互換性のため
        report_to="tensorboard",
        logging_dir=str(output_dir / "logs"),
        gradient_checkpointing=(not args.no_gradient_checkpointing),  # VRAM節約 / 切り分け
        optim="adamw_torch",  # メモリ効率の良いオプティマイザ
        disable_tqdm=True,  # Windowsコンソール出力エラー回避（tqdmのOSError: [Errno 22] Invalid argument対策）
    )

    print(f"出力ディレクトリ: {output_dir}")
    print(f"エポック数: {args.epochs}")
    if _max_steps > 0:
        print(f"最大ステップ数: {_max_steps}（epochsは無視）")
    print(f"バッチサイズ: {args.batch_size}")
    print(f"学習率: {args.learning_rate}")
    print(f"最大シーケンス長: {args.max_length}")
    print(f"保存間隔(save_steps): {args.save_steps}")
    print(f"ログ間隔(logging_steps): {args.logging_steps}")
    if eval_dataset:
        print(f"評価間隔(eval_steps): {eval_steps}")
    print(f"attn_implementation: {args.attn_implementation}")
    print(f"gradient_checkpointing: {not args.no_gradient_checkpointing}")
    print(f"load_best_model_at_end: {load_best_model_at_end}")

    # DataCollator
    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False,
    )

    print("\n" + "=" * 60)
    print("学習開始")
    print("=" * 60)

    # チェックポイントから再開するか確認
    resume_from_checkpoint = None
    if args.resume_from_checkpoint:
        if args.resume_from_checkpoint.lower() == "auto":
            latest_valid = find_latest_valid_checkpoint(output_dir)
            if latest_valid:
                resume_from_checkpoint = str(latest_valid)
                print(f"[情報] 有効なチェックポイントを自動検出: {resume_from_checkpoint}")
                print("      （trainer_state.json が存在するcheckpointのみ対象）")
                print("      チェックポイントから再開します")
            else:
                print("[情報] 有効なチェックポイントが見つかりません。初めから学習を開始します。")
        else:
            requested = Path(args.resume_from_checkpoint)
            if not requested.exists():
                print(f"[エラー] 指定されたチェックポイントが見つかりません: {requested}")
                print("       -> --resume-from-checkpoint auto を推奨します")
                return 1
            if not _is_valid_trainer_checkpoint(requested):
                print(
                    f"[エラー] 指定されたチェックポイントが不完全です（trainer_state.jsonがありません）: {requested}"
                )
                print("       -> 不完全checkpointは再開できません")
                print(
                    "       -> --resume-from-checkpoint auto または trainer_state.json のあるcheckpointを指定してください"
                )
                return 1
            resume_from_checkpoint = str(requested)
            print(f"[情報] 指定されたチェックポイントから再開: {resume_from_checkpoint}")
    else:
        # デフォルト動作: 有効なcheckpointがあればそこから再開
        latest_valid = find_latest_valid_checkpoint(output_dir)
        if latest_valid:
            resume_from_checkpoint = str(latest_valid)
            print(f"[情報] 有効なチェックポイントを自動検出: {resume_from_checkpoint}")
            print("      （trainer_state.json が存在するcheckpointのみ対象）")
            print("      チェックポイントから再開します")

    if resume_from_checkpoint:
        print(f"      再開先: {resume_from_checkpoint}")
        logger.info(f"チェックポイントから再開: {resume_from_checkpoint}")
    else:
        print("[情報] チェックポイントが見つかりません。初めから学習を開始します。")
        logger.info("チェックポイントなし。初めから学習を開始")

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        data_collator=data_collator,
    )

    try:
        logger.info(
            f"学習開始: output_dir={output_dir}, resume_from_checkpoint={resume_from_checkpoint}"
        )
        # tqdmエラー対策: 環境変数でtqdmを無効化
        import os

        os.environ["TQDM_DISABLE"] = "1"

        print(f"[INFO] 学習を開始します（checkpoint-800から再開）")
        logger.info("trainer.train()を呼び出します")

        # エラーハンドリングを強化
        try:
            print("[DEBUG] trainer.train()を呼び出します...")
            logger.info("trainer.train()を呼び出します（詳細ログ）")
            trainer.train(resume_from_checkpoint=resume_from_checkpoint)
            print("[DEBUG] trainer.train()が正常に完了しました")
            logger.info("trainer.train()が正常に完了しました")
        except KeyboardInterrupt:
            print("\n[INFO] 学習が中断されました（KeyboardInterrupt）")
            logger.info("学習が中断されました（KeyboardInterrupt）")
            raise
        except SystemExit as e:
            print(f"\n[INFO] システム終了: {e}")
            logger.info(f"システム終了: {e}")
            raise
        except Exception as train_error:
            error_msg = f"trainer.train()でエラーが発生しました: {type(train_error).__name__}: {train_error}"
            print(f"\n[エラー] {error_msg}")
            logger.exception(error_msg)
            import traceback

            tb_str = traceback.format_exc()
            print(f"\n[トレースバック]\n{tb_str}")
            logger.error(f"トレースバック:\n{tb_str}")
            # エラー詳細をファイルに保存
            error_log_path = output_dir / "training_error.log"
            with open(error_log_path, "w", encoding="utf-8") as f:
                f.write(f"エラー発生時刻: {datetime.now()}\n")
                f.write(f"エラータイプ: {type(train_error).__name__}\n")
                f.write(f"エラーメッセージ: {train_error}\n")
                f.write(f"\nトレースバック:\n{tb_str}\n")
            print(f"[INFO] エラー詳細を保存しました: {error_log_path}")
            raise

        print("\n[OK] 学習完了")
        logger.info("学習完了")

        # モデルを保存
        print(f"\nモデルを保存中: {output_dir}")
        logger.info(f"モデル保存開始: {output_dir}")
        trainer.save_model()
        tokenizer.save_pretrained(str(output_dir))
        print("[OK] モデル保存完了")
        logger.info("モデル保存完了")

        # 保存後のディスク容量を再チェック
        is_sufficient, free_gb, _ = check_disk_space(output_dir, required_gb=1.0)
        logger.info(f"保存後ディスク容量: {free_gb:.2f}GB (十分: {is_sufficient})")

    except Exception as e:
        error_msg = f"学習中にエラーが発生しました: {e}"
        print(f"\n[エラー] {error_msg}")
        logger.exception(error_msg)
        import traceback

        traceback.print_exc()
        return 1

    print("\n" + "=" * 60)
    print("学習完了")
    print("=" * 60)
    print(f"\n学習済みモデル: {output_dir}")
    print("\n次のステップ:")
    print("  1. 評価を実行:")
    print(f"     python castle_ex_evaluator_fixed.py \\")
    print(f"       --eval-data {args.eval_data} \\")
    print(f"       --output evaluation_v1_0.json \\")
    print(f"       --model-type transformers \\")
    print(f"       --model {output_dir}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
