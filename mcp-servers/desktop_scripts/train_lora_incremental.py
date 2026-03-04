# -*- coding: utf-8 -*-
"""
インクリメンタルLoRA訓練スクリプト
30枚ずつ段階的に訓練していく方式
"""

import os
import argparse
import shutil
from pathlib import Path
import json
from datetime import datetime

def split_dataset(source_dir, batch_size=30):
    """
    データセットをバッチに分割
    各バッチには画像と対応するキャプションファイルを含む
    """
    source_path = Path(source_dir)
    if not source_path.exists():
        raise ValueError(f"データセットディレクトリが存在しません: {source_dir}")
    
    # すべての画像ファイルを取得（.png, .jpg, .jpeg）
    image_files = sorted([
        f for f in source_path.glob("*.png")
        if f.is_file()
    ])
    
    total_images = len(image_files)
    print(f"総画像数: {total_images}枚")
    
    # バッチごとに分割
    batches = []
    for i in range(0, total_images, batch_size):
        batch_images = image_files[i:i+batch_size]
        batches.append(batch_images)
        print(f"バッチ {len(batches)}: {len(batch_images)}枚 (画像 {i+1}-{min(i+batch_size, total_images)})")
    
    return batches

def create_batch_dataset(batch_images, batch_num, work_dir):
    """バッチ用の一時データセットディレクトリを作成"""
    batch_dir = Path(work_dir) / f"batch_{batch_num:03d}"
    batch_dir.mkdir(parents=True, exist_ok=True)
    
    # 画像とキャプションファイルをコピー
    for img_path in batch_images:
        # 画像をコピー
        shutil.copy2(img_path, batch_dir / img_path.name)
        
        # キャプションファイルがあればコピー
        caption_path = img_path.with_suffix('.txt')
        if caption_path.exists():
            shutil.copy2(caption_path, batch_dir / caption_path.name)
    
    print(f"バッチ {batch_num} のデータセットを作成: {batch_dir} ({len(batch_images)}枚)")
    return batch_dir

def get_latest_checkpoint(output_dir):
    """最新のチェックポイントを取得"""
    output_path = Path(output_dir)
    if not output_path.exists():
        return None
    
    # checkpoint-step-XXX ディレクトリを探す
    checkpoints = sorted([
        d for d in output_path.iterdir()
        if d.is_dir() and d.name.startswith("checkpoint-step-")
    ], key=lambda x: int(x.name.split("-")[-1]), reverse=True)
    
    if checkpoints:
        return checkpoints[0]
    return None

def main():
    parser = argparse.ArgumentParser(description="インクリメンタルLoRA訓練")
    parser.add_argument(
        "--source_data_dir",
        type=str,
        required=True,
        help="元のデータセットディレクトリ",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        required=True,
        help="出力ディレクトリ",
    )
    parser.add_argument(
        "--batch_size",
        type=int,
        default=30,
        help="1バッチあたりの画像数（デフォルト: 30）",
    )
    parser.add_argument(
        "--start_batch",
        type=int,
        default=1,
        help="開始バッチ番号（デフォルト: 1）",
    )
    parser.add_argument(
        "--end_batch",
        type=int,
        default=None,
        help="終了バッチ番号（デフォルト: 全バッチ）",
    )
    parser.add_argument(
        "--work_dir",
        type=str,
        default="incremental_training_work",
        help="作業用ディレクトリ（デフォルト: incremental_training_work）",
    )
    parser.add_argument(
        "--pretrained_model_name_or_path",
        type=str,
        default="runwayml/stable-diffusion-v1-5",
        help="事前訓練済みモデル",
    )
    parser.add_argument(
        "--num_train_epochs",
        type=int,
        default=50,
        help="各バッチのエポック数",
    )
    parser.add_argument(
        "--save_steps",
        type=int,
        default=500,
        help="チェックポイント保存間隔（ステップ）",
    )
    parser.add_argument(
        "--save_epochs",
        type=int,
        default=10,
        help="チェックポイント保存間隔（エポック）",
    )
    parser.add_argument(
        "--train_batch_size",
        type=int,
        default=1,
        help="訓練バッチサイズ",
    )
    parser.add_argument(
        "--learning_rate",
        type=float,
        default=1e-4,
        help="学習率（デフォルト: 1e-4、安定性重視）",
    )
    parser.add_argument(
        "--lora_rank",
        type=int,
        default=8,
        help="LoRA rank",
    )
    parser.add_argument(
        "--lora_alpha",
        type=int,
        default=16,
        help="LoRA alpha",
    )
    parser.add_argument(
        "--num_workers",
        type=int,
        default=0,
        help="DataLoaderのnum_workers",
    )
    parser.add_argument(
        "--mixed_precision",
        type=str,
        default="no",
        choices=["no", "fp16", "bf16"],
        help="Mixed precision training（デフォルト: no、安定性重視）",
    )
    parser.add_argument(
        "--resolution",
        type=int,
        default=512,
        help="画像解像度",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="ランダムシード",
    )
    parser.add_argument(
        "--cleanup_batch_dirs",
        action="store_true",
        help="各バッチ訓練後に一時ディレクトリを削除",
    )
    
    args = parser.parse_args()
    
    # データセットをバッチに分割
    print("=" * 60)
    print("データセットをバッチに分割中...")
    print("=" * 60)
    batches = split_dataset(args.source_data_dir, args.batch_size)
    total_batches = len(batches)
    
    print(f"\n総バッチ数: {total_batches}")
    print(f"1バッチあたり: {args.batch_size}枚（最後のバッチは {len(batches[-1])}枚）")
    
    # 開始/終了バッチを決定
    start_batch = args.start_batch
    end_batch = args.end_batch if args.end_batch else total_batches
    
    print(f"\n訓練範囲: バッチ {start_batch} ～ {end_batch}")
    print("=" * 60)
    
    # 作業ディレクトリを作成
    work_dir = Path(args.work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    
    # 出力ディレクトリを作成
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 訓練履歴を保存
    training_log = {
        "start_time": datetime.now().isoformat(),
        "source_data_dir": str(args.source_data_dir),
        "output_dir": str(args.output_dir),
        "batch_size": args.batch_size,
        "total_batches": total_batches,
        "batches": []
    }
    
    # 各バッチを訓練
    checkpoint_to_resume = None
    
    for batch_num in range(start_batch, end_batch + 1):
        batch_idx = batch_num - 1  # 0-based index
        if batch_idx >= len(batches):
            print(f"\nバッチ {batch_num} は存在しません（総バッチ数: {total_batches}）")
            break
        
        print("\n" + "=" * 60)
        print(f"バッチ {batch_num}/{total_batches} の訓練を開始")
        print("=" * 60)
        
        batch_images = batches[batch_idx]
        
        # バッチ用データセットを作成
        batch_dataset_dir = create_batch_dataset(batch_images, batch_num, work_dir)
        
        # 訓練コマンドを構築
        train_cmd = [
            "python", "-u", "Scripts/train_lora_quick.py",
            f"--pretrained_model_name_or_path={args.pretrained_model_name_or_path}",
            f"--instance_data_dir={batch_dataset_dir}",
            f"--output_dir={args.output_dir}",
            f"--num_train_epochs={args.num_train_epochs}",
            f"--save_steps={args.save_steps}",
            f"--save_epochs={args.save_epochs}",
            f"--train_batch_size={args.train_batch_size}",
            f"--learning_rate={args.learning_rate}",
            f"--lora_rank={args.lora_rank}",
            f"--lora_alpha={args.lora_alpha}",
            f"--num_workers={args.num_workers}",
            f"--mixed_precision={args.mixed_precision}",
            f"--resolution={args.resolution}",
            f"--seed={args.seed}",
        ]
        
        # チェックポイントから再開（最初のバッチ以外）
        if checkpoint_to_resume:
            train_cmd.append(f"--resume_from_checkpoint={checkpoint_to_resume}")
            print(f"チェックポイントから再開: {checkpoint_to_resume}")
        
        # 訓練を実行
        import subprocess
        print(f"\n訓練コマンド:")
        print(" ".join(train_cmd))
        print()
        
        result = subprocess.run(train_cmd, cwd=Path.cwd())
        
        if result.returncode != 0:
            print(f"\n[ERROR] バッチ {batch_num} の訓練に失敗しました（終了コード: {result.returncode}）")
            training_log["batches"].append({
                "batch_num": batch_num,
                "status": "failed",
                "images_count": len(batch_images),
            })
            break
        
        # 最新のチェックポイントを取得
        checkpoint_to_resume = get_latest_checkpoint(args.output_dir)
        if checkpoint_to_resume:
            print(f"\n[OK] バッチ {batch_num} の訓練が完了")
            print(f"最新チェックポイント: {checkpoint_to_resume}")
        else:
            print(f"\n[WARNING] バッチ {batch_num} の訓練は完了しましたが、チェックポイントが見つかりません")
        
        # バッチ情報をログに記録
        training_log["batches"].append({
            "batch_num": batch_num,
            "status": "completed",
            "images_count": len(batch_images),
            "checkpoint": str(checkpoint_to_resume) if checkpoint_to_resume else None,
        })
        
        # 一時ディレクトリを削除（オプション）
        if args.cleanup_batch_dirs:
            print(f"一時データセットディレクトリを削除: {batch_dataset_dir}")
            shutil.rmtree(batch_dataset_dir, ignore_errors=True)
    
    # 訓練履歴を保存
    training_log["end_time"] = datetime.now().isoformat()
    log_file = output_dir / "incremental_training_log.json"
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(training_log, f, indent=2, ensure_ascii=False)
    
    print("\n" + "=" * 60)
    print("インクリメンタル訓練が完了しました")
    print(f"訓練履歴: {log_file}")
    if checkpoint_to_resume:
        print(f"最終チェックポイント: {checkpoint_to_resume}")
    print("=" * 60)

if __name__ == "__main__":
    main()






