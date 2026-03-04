# -*- coding: utf-8 -*-
"""
簡易LoRA訓練スクリプト（diffusers + PEFT使用）
データセット準備済みの場合に使用
"""

import os
import argparse
import torch
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from PIL import Image
from pathlib import Path
import numpy as np
from tqdm import tqdm
import json
from datetime import datetime
from functools import partial

# diffusersライブラリ
from diffusers import StableDiffusionPipeline, DDPMScheduler, UNet2DConditionModel
from diffusers.optimization import get_scheduler
from diffusers.training_utils import EMAModel

# accelerate
from accelerate import Accelerator
from accelerate.logging import get_logger

logger = get_logger(__name__)


class DreamBoothDataset(Dataset):
    """DreamBooth形式のデータセット"""
    
    def __init__(
        self,
        instance_data_root,
        tokenizer,
        size=512,
        center_crop=False,
        instance_prompt="",
    ):
        self.size = size
        self.center_crop = center_crop
        self.tokenizer = tokenizer
        
        # 画像ファイルを取得
        self.instance_data_root = Path(instance_data_root)
        self.instance_images_path = sorted([
            f for f in self.instance_data_root.glob("*.png")
            if f.is_file()
        ])
        self.num_instance_images = len(self.instance_images_path)
        self.instance_prompt = instance_prompt
        
        logger.info(f"Found {self.num_instance_images} images")
    
    def __len__(self):
        return self.num_instance_images
    
    def __getitem__(self, index):
        example = {}
        instance_image = Image.open(self.instance_images_path[index % self.num_instance_images])
        if not instance_image.mode == "RGB":
            instance_image = instance_image.convert("RGB")
        
        # キャプションを読み込み
        caption_file = self.instance_images_path[index % self.num_instance_images].with_suffix('.txt')
        if caption_file.exists():
            with open(caption_file, 'r', encoding='utf-8') as f:
                prompt = f.read().strip()
        else:
            prompt = self.instance_prompt
        
        example["instance_images"] = instance_image
        example["instance_prompt_ids"] = self.tokenizer(
            prompt,
            truncation=True,
            padding="max_length",
            max_length=self.tokenizer.model_max_length,
            return_tensors="pt",
        ).input_ids
        
        return example


def save_checkpoint(unet, accelerator, output_dir, step, epoch):
    """チェックポイントを保存（Acceleratorを使用して全状態を保存）"""
    accelerator.wait_for_everyone()
    if accelerator.is_main_process:
        checkpoint_dir = Path(output_dir) / f"checkpoint-step-{step}"
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        # Acceleratorで全状態を保存
        accelerator.save_state(str(checkpoint_dir))
        
        # 訓練状態メタデータを保存
        state = {
            "epoch": epoch,
            "global_step": step,
        }
        state_file = checkpoint_dir / "training_state.json"
        import json
        with open(state_file, "w") as f:
            json.dump(state, f, indent=2)
        
        # 最新チェックポイントを記録
        latest_file = Path(output_dir) / "latest_checkpoint.txt"
        with open(latest_file, "w") as f:
            f.write(str(checkpoint_dir.name))
        
        logger.info(f"Checkpoint saved to {checkpoint_dir} (epoch {epoch+1}, step {step})")


def collate_fn(examples, tokenizer, with_prior_preservation=False):
    """バッチ処理用のコレート関数"""
    input_ids = [example["instance_prompt_ids"] for example in examples]
    images = [example["instance_images"] for example in examples]
    
    # 画像を正規化（-1から1の範囲に）
    pixel_values_list = []
    for image in images:
        img_array = np.array(image).astype(np.float32) / 255.0
        img_tensor = torch.from_numpy(img_array).permute(2, 0, 1)
        pixel_values_list.append(img_tensor)
    pixel_values = torch.stack(pixel_values_list)
    pixel_values = (pixel_values - 0.5) / 0.5  # -1 to 1
    pixel_values = pixel_values.to(memory_format=torch.contiguous_format).float()
    
    input_ids = torch.cat(input_ids, dim=0)
    
    batch = {
        "input_ids": input_ids,
        "pixel_values": pixel_values,
    }
    return batch


def main(args):
    """メイン訓練関数"""
    
    # Acceleratorを初期化（mixed_precisionは"no"にして、手動でautocastを使用）
    # これにより、FP16の勾配スケーリングの問題を回避
    accelerator = Accelerator(
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        mixed_precision="no",  # 手動でautocastを使用するため"no"に設定
    )
    
    # ロガーの設定
    if accelerator.is_local_main_process:
        logger.setLevel("INFO")
    
    # シードの設定
    if args.seed is not None:
        torch.manual_seed(args.seed)
    
    # モデルを読み込み
    logger.info("Loading pretrained model...")
    pipeline = StableDiffusionPipeline.from_pretrained(
        args.pretrained_model_name_or_path,
        torch_dtype=torch.float16 if args.mixed_precision == "fp16" else torch.float32,
    )
    
    # モデルコンポーネントを取得
    tokenizer = pipeline.tokenizer
    text_encoder = pipeline.text_encoder
    vae = pipeline.vae
    unet = pipeline.unet
    noise_scheduler = DDPMScheduler.from_config(pipeline.scheduler.config)
    
    # VAEとtext_encoderを適切なデバイスと型に設定
    dtype = torch.float16 if args.mixed_precision == "fp16" else torch.float32
    vae_dtype = torch.float32  # VAEはfloat32を使用
    vae = vae.to(dtype=vae_dtype)
    text_encoder = text_encoder.to(dtype=dtype)
    
    # PEFTを使用してLoRAを適用
    try:
        from peft import LoraConfig, get_peft_model
        
        # LoRA設定
        lora_config = LoraConfig(
            r=args.lora_rank,
            lora_alpha=args.lora_alpha,
            target_modules=["to_k", "to_q", "to_v", "to_out.0"],
            lora_dropout=args.lora_dropout,
        )
        
        unet = get_peft_model(unet, lora_config)
        unet.print_trainable_parameters()
        
        # xformersを有効化（高速化とメモリ効率化）
        try:
            unet.enable_xformers_memory_efficient_attention()
            logger.info("xformers enabled for faster training")
        except Exception as e:
            logger.info(f"xformers not available: {e}")
        
        logger.info("LoRA applied successfully")
    except ImportError:
        logger.warning("peft not installed. Install with: pip install peft")
        logger.warning("Training full UNet (not LoRA)")
    
    # VAEとtext_encoderは訓練しない
    vae.requires_grad_(False)
    text_encoder.requires_grad_(False)
    unet.requires_grad_(True)
    
    # データセットを作成
    train_dataset = DreamBoothDataset(
        instance_data_root=args.instance_data_dir,
        tokenizer=tokenizer,
        size=args.resolution,
        center_crop=args.center_crop,
        instance_prompt=args.instance_prompt,
    )
    
    # collate_fnをpartialで定義（Windowsのmultiprocessing対応）
    collate_fn_partial = partial(collate_fn, tokenizer=tokenizer, with_prior_preservation=False)
    
    train_dataloader = DataLoader(
        train_dataset,
        batch_size=args.train_batch_size,
        shuffle=True,
        collate_fn=collate_fn_partial,  # partial関数を使用（Windowsのmultiprocessing対応）
        num_workers=args.num_workers,  # データローディングの並列化（GPU計算中に次のバッチを準備）
        pin_memory=True if torch.cuda.is_available() else False,  # GPU使用時はメモリピニングで高速化
    )
    
    # オプティマイザー
    optimizer = torch.optim.AdamW(
        unet.parameters(),
        lr=args.learning_rate,
        betas=(args.adam_beta1, args.adam_beta2),
        weight_decay=args.adam_weight_decay,
        eps=args.adam_epsilon,
    )
    
    # 学習率スケジューラー
    lr_scheduler = get_scheduler(
        args.lr_scheduler,
        optimizer=optimizer,
        num_warmup_steps=args.lr_warmup_steps,
        num_training_steps=len(train_dataloader) * args.num_train_epochs,
    )
    
    # Acceleratorで準備（VAEとtext_encoderも含める）
    # optimizerはacceleratorで準備しない（GradScalerの問題を回避するため）
    vae = accelerator.prepare(vae)
    text_encoder = accelerator.prepare(text_encoder)
    unet, train_dataloader, lr_scheduler = accelerator.prepare(
        unet, train_dataloader, lr_scheduler
    )
    # optimizerは手動で管理（acceleratorで準備しない）
    
    # 訓練ステップ数
    num_update_steps_per_epoch = len(train_dataloader) // args.gradient_accumulation_steps
    max_train_steps = args.num_train_epochs * num_update_steps_per_epoch
    
    logger.info("Starting training...")
    logger.info(f"  Num examples: {len(train_dataset)}")
    logger.info(f"  Num epochs: {args.num_train_epochs}")
    logger.info(f"  Instantaneous batch size per device: {args.train_batch_size}")
    logger.info(f"  Total train batch size: {args.train_batch_size * accelerator.num_processes * args.gradient_accumulation_steps}")
    logger.info(f"  Gradient Accumulation steps: {args.gradient_accumulation_steps}")
    logger.info(f"  Total optimization steps: {max_train_steps}")
    
    # チェックポイントからの再開
    starting_epoch = 0
    global_step = 0
    if args.resume_from_checkpoint:
        checkpoint_path = Path(args.resume_from_checkpoint)
        if checkpoint_path.exists():
            logger.info(f"Resuming training from checkpoint: {checkpoint_path}")
            
            # 訓練状態メタデータを先にロード
            state_file = checkpoint_path / "training_state.json"
            if state_file.exists():
                import json
                with open(state_file, "r") as f:
                    state = json.load(f)
                starting_epoch = state.get("epoch", 0)
                global_step = state.get("global_step", 0)
                logger.info(f"Will resume from epoch {starting_epoch}, step {global_step}")
            
            # Acceleratorで全状態をロード（モデル、オプティマイザー、スケジューラーなど）
            try:
                logger.info("Loading checkpoint state...")
                accelerator.load_state(str(checkpoint_path))
                logger.info(f"Successfully loaded checkpoint state")
            except Exception as e:
                logger.warning(f"Failed to load full checkpoint state: {e}")
                logger.warning("Will try to load model weights only...")
                
                # モデルの重みだけをロード
                try:
                    import safetensors.torch
                    model_file = checkpoint_path / "model_2.safetensors"
                    if model_file.exists():
                        state_dict = safetensors.torch.load_file(str(model_file))
                        # LoRAの重みだけを抽出
                        lora_state_dict = {}
                        for key, value in state_dict.items():
                            if "lora" in key.lower():
                                lora_state_dict[key] = value
                        
                        if lora_state_dict:
                            # UNetにLoRAを適用
                            from peft import LoraConfig, get_peft_model
                            lora_config = LoraConfig(
                                r=args.lora_rank,
                                lora_alpha=args.lora_alpha,
                                target_modules=["to_k", "to_q", "to_v", "to_out.0"],
                                lora_dropout=args.lora_dropout,
                            )
                            unet = get_peft_model(unet, lora_config)
                            unet.load_state_dict(lora_state_dict, strict=False)
                            logger.info("Loaded LoRA weights from checkpoint")
                        else:
                            logger.warning("No LoRA weights found in checkpoint")
                    else:
                        logger.warning(f"Model file not found: {model_file}")
                except Exception as e2:
                    logger.error(f"Failed to load model weights: {e2}")
                    logger.warning("Starting training from scratch")
    
    # 訓練ループ
    progress_bar = tqdm(range(max_train_steps), disable=not accelerator.is_local_main_process, initial=global_step)
    progress_bar.set_description("Steps")
    
    for epoch in range(starting_epoch, args.num_train_epochs):
        unet.train()
        train_loss = 0.0
        
        for step, batch in enumerate(train_dataloader):
            # Mixed precision用のautocastコンテキスト
            use_autocast = args.mixed_precision == "fp16" and accelerator.device.type == "cuda"
            
            with torch.autocast(device_type=accelerator.device.type, dtype=torch.float16, enabled=use_autocast):
                # VAEでエンコード（float32に変換）
                pixel_values = batch["pixel_values"].to(dtype=torch.float32)
                latents = vae.encode(pixel_values).latent_dist.sample()
                latents = latents * vae.config.scaling_factor
                latents = latents.to(dtype=dtype)
                
                # ノイズを追加
                noise = torch.randn_like(latents)
                timesteps = torch.randint(0, noise_scheduler.config.num_train_timesteps, (latents.shape[0],), device=latents.device)
                noisy_latents = noise_scheduler.add_noise(latents, noise, timesteps)
                
                # テキストエンコーディング
                encoder_hidden_states = text_encoder(batch["input_ids"])[0]
                
                # 予測
                model_pred = unet(noisy_latents, timesteps, encoder_hidden_states).sample
                
                # 損失（float32で計算）
                loss = F.mse_loss(model_pred.float(), noise.float(), reduction="mean")
            
            # バックプロパゲーション（勾配蓄積を考慮）
            loss = loss / args.gradient_accumulation_steps
            loss.backward()  # accelerator.backward()の代わりに直接backward()を使用
            
            # 勾配蓄積のチェック
            if (step + 1) % args.gradient_accumulation_steps == 0:
                # 勾配クリッピング（オプション、CUDAエラー回避のため条件付き）
                if args.max_grad_norm > 0:
                    try:
                        # 勾配が存在するパラメータのみをクリッピング
                        params_with_grad = [p for p in unet.parameters() if p.grad is not None]
                        if params_with_grad:
                            torch.nn.utils.clip_grad_norm_(params_with_grad, args.max_grad_norm)
                    except Exception as e:
                        # CUDAエラーが発生した場合は勾配クリッピングをスキップ
                        logger.warning(f"勾配クリッピングでエラーが発生しました（スキップ）: {e}")
                
                optimizer.step()
                lr_scheduler.step()
                optimizer.zero_grad()
            
            if accelerator.sync_gradients:
                progress_bar.update(1)
                global_step += 1
                train_loss += loss.detach().item()
            
            logs = {"loss": loss.detach().item(), "lr": lr_scheduler.get_last_lr()[0]}
            progress_bar.set_postfix(**logs)
            
            # ログを強制的にフラッシュ（バッファリング問題を回避）
            if global_step % 10 == 0:
                import sys
                sys.stdout.flush()
                sys.stderr.flush()
            
            # チェックポイント保存（指定されたステップごと）
            if args.save_steps and global_step > 0 and global_step % args.save_steps == 0:
                save_checkpoint(unet, accelerator, args.output_dir, global_step, epoch)
            
            if global_step >= max_train_steps:
                break
        
        # チェックポイント保存（エポックごと）
        if (epoch + 1) % args.save_epochs == 0 or epoch == args.num_train_epochs - 1:
            save_checkpoint(unet, accelerator, args.output_dir, global_step, epoch)
        
        if global_step >= max_train_steps:
            break
    
    # モデルを保存
    accelerator.wait_for_everyone()
    if accelerator.is_main_process:
        logger.info("Saving model...")
        
        unet = accelerator.unwrap_model(unet)
        
        # LoRAの重みを保存
        if hasattr(unet, "save_pretrained"):
            unet.save_pretrained(args.output_dir)
            logger.info(f"Model saved to {args.output_dir}")
        else:
            logger.warning("Could not save model (PEFT model not detected)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simple LoRA Training")
    
    parser.add_argument("--pretrained_model_name_or_path", type=str, default="runwayml/stable-diffusion-v1-5",
                       help="Path to pretrained model")
    parser.add_argument("--instance_data_dir", type=str, required=True,
                       help="Path to instance images directory")
    parser.add_argument("--output_dir", type=str, default="./lora_output",
                       help="Output directory")
    parser.add_argument("--instance_prompt", type=str, default="woman, portrait, beautiful face",
                       help="Instance prompt (used if caption file not found)")
    
    parser.add_argument("--resolution", type=int, default=512,
                       help="Image resolution")
    parser.add_argument("--center_crop", action="store_true",
                       help="Center crop images")
    parser.add_argument("--train_batch_size", type=int, default=1,
                       help="Batch size")
    parser.add_argument("--gradient_accumulation_steps", type=int, default=1,
                       help="Gradient accumulation steps")
    parser.add_argument("--learning_rate", type=float, default=1e-4,
                       help="Learning rate")
    parser.add_argument("--lr_scheduler", type=str, default="constant",
                       help="LR scheduler")
    parser.add_argument("--lr_warmup_steps", type=int, default=0,
                       help="LR warmup steps")
    parser.add_argument("--num_train_epochs", type=int, default=100,
                       help="Number of epochs")
    parser.add_argument("--max_grad_norm", type=float, default=1.0,
                       help="Max gradient norm")
    parser.add_argument("--save_steps", type=int, default=None,
                       help="Save checkpoint every N steps (default: save every epoch). Use 1 to save every batch.")
    parser.add_argument("--save_epochs", type=int, default=10,
                       help="Save checkpoint every N epochs (default: 10)")
    parser.add_argument("--resume_from_checkpoint", type=str, default=None,
                       help="Path to checkpoint directory to resume training from")
    
    parser.add_argument("--mixed_precision", type=str, default="fp16", choices=["no", "fp16", "bf16"],
                       help="Mixed precision")
    parser.add_argument("--seed", type=int, default=None,
                       help="Random seed")
    
    # LoRAパラメータ
    parser.add_argument("--lora_rank", type=int, default=4,
                       help="LoRA rank")
    parser.add_argument("--lora_alpha", type=int, default=32,
                       help="LoRA alpha")
    parser.add_argument("--lora_dropout", type=float, default=0.0,
                       help="LoRA dropout")
    
    # データローディング最適化
    parser.add_argument("--num_workers", type=int, default=0,
                       help="DataLoaderのworker数 (0=シングルスレッド, 2-4推奨)")
    
    # Adamパラメータ
    parser.add_argument("--adam_beta1", type=float, default=0.9,
                       help="Adam beta1")
    parser.add_argument("--adam_beta2", type=float, default=0.999,
                       help="Adam beta2")
    parser.add_argument("--adam_weight_decay", type=float, default=0.01,
                       help="Adam weight decay")
    parser.add_argument("--adam_epsilon", type=float, default=1e-8,
                       help="Adam epsilon")
    
    args = parser.parse_args()
    
    # デフォルトのsave_epochsを設定（save_stepsが指定されていない場合）
    if args.save_steps is None and not hasattr(args, 'save_epochs_set'):
        # デフォルトで10エポックごとに保存
        pass
    
    main(args)

