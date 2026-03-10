# -*- coding: utf-8 -*-
"""簡易LoRA訓練スクリプト（diffusersベース）"""

import os
import argparse
import torch
from torch.utils.data import Dataset
from PIL import Image
from pathlib import Path
from diffusers import StableDiffusionPipeline, UNet2DConditionModel
from diffusers import DDPMScheduler
from diffusers.optimization import get_scheduler
from accelerate import Accelerator
from accelerate.logging import get_logger
from tqdm.auto import tqdm
import json
from datetime import datetime

logger = get_logger(__name__)


class LoRADataset(Dataset):
    """LoRA訓練用データセット"""
    
    def __init__(
        self,
        data_root,
        tokenizer,
        size=512,
        repeats=1,
        center_crop=False,
    ):
        self.data_root = Path(data_root)
        self.tokenizer = tokenizer
        self.size = size
        self.center_crop = center_crop
        
        # 画像ファイルを取得
        self.image_paths = sorted([
            f for f in self.data_root.glob("*.png")
            if f.is_file()
        ])
        
        # 繰り返し
        self.image_paths = self.image_paths * repeats
        
        logger.info(f"Dataset size: {len(self.image_paths)} images")
    
    def __len__(self):
        return len(self.image_paths)
    
    def __getitem__(self, idx):
        image_path = self.image_paths[idx]
        
        # 画像を読み込み
        image = Image.open(image_path).convert("RGB")
        
        # リサイズとクロップ
        image = image.resize((self.size, self.size), Image.Resampling.LANCZOS)
        if self.center_crop:
            crop_size = min(image.size)
            left = (image.size[0] - crop_size) // 2
            top = (image.size[1] - crop_size) // 2
            image = image.crop((left, top, left + crop_size, top + crop_size))
            image = image.resize((self.size, self.size), Image.Resampling.LANCZOS)
        
        # キャプションファイルを読み込み
        caption_path = image_path.with_suffix('.txt')
        if caption_path.exists():
            with open(caption_path, 'r', encoding='utf-8') as f:
                caption = f.read().strip()
        else:
            caption = ""
        
        # トークン化
        text_inputs = self.tokenizer(
            caption,
            padding="max_length",
            max_length=self.tokenizer.model_max_length,
            truncation=True,
            return_tensors="pt",
        )
        
        return {
            "pixel_values": (torch.tensor(list(image.getdata())).reshape(self.size, self.size, 3).permute(2, 0, 1).float() / 127.5 - 1.0),
            "input_ids": text_inputs.input_ids.flatten(),
        }


def collate_fn(examples):
    """バッチ処理用のコレート関数"""
    pixel_values = torch.stack([example["pixel_values"] for example in examples])
    pixel_values = pixel_values.to(memory_format=torch.contiguous_format).float()
    
    input_ids = torch.stack([example["input_ids"] for example in examples])
    
    return {
        "pixel_values": pixel_values,
        "input_ids": input_ids,
    }


def train_lora(
    pretrained_model_name_or_path: str = "runwayml/stable-diffusion-v1-5",
    train_data_dir: str = "./lora_dataset_mana_favorite",
    output_dir: str = "./lora_output",
    resolution: int = 512,
    train_batch_size: int = 1,
    num_train_epochs: int = 100,
    learning_rate: float = 1e-4,
    lr_scheduler: str = "constant",
    lr_warmup_steps: int = 0,
    use_8bit_adam: bool = False,
    adam_beta1: float = 0.9,
    adam_beta2: float = 0.999,
    adam_weight_decay: float = 0.01,
    max_train_steps: int = None,  # type: ignore
    gradient_accumulation_steps: int = 1,
    seed: int = 42,
    mixed_precision: str = "fp16",
):
    """LoRA訓練のメイン関数"""
    
    accelerator = Accelerator(
        gradient_accumulation_steps=gradient_accumulation_steps,
        mixed_precision=mixed_precision,
    )
    
    # ロガーの設定
    if accelerator.is_local_main_process:
        logger.setLevel("INFO")
    
    # シードの設定
    torch.manual_seed(seed)
    
    # モデルを読み込み
    logger.info("Loading model...")
    pipe = StableDiffusionPipeline.from_pretrained(
        pretrained_model_name_or_path,
        torch_dtype=torch.float16 if mixed_precision == "fp16" else torch.float32,
    )
    
    # UNetのみ訓練対象にする
    unet = pipe.unet
    vae = pipe.vae
    text_encoder = pipe.text_encoder
    tokenizer = pipe.tokenizer
    noise_scheduler = DDPMScheduler.from_config(pipe.scheduler.config)
    
    # PEFTを使用してLoRAを適用
    try:
        from peft import LoraConfig, get_peft_model, TaskType
        
        lora_config = LoraConfig(
            r=4,  # LoRA rank
            lora_alpha=32,  # LoRA alpha
            target_modules=["to_k", "to_q", "to_v", "to_out.0"],
            task_type=TaskType.FEATURE_EXTRACTION,
        )
        
        unet = get_peft_model(unet, lora_config)
        logger.info("LoRA applied to UNet")
    except ImportError:
        logger.warning("peft not installed, training full UNet (not LoRA)")
        logger.warning("Install peft: pip install peft")
    
    # VAEとtext_encoderは訓練しない
    vae.requires_grad_(False)
    text_encoder.requires_grad_(False)
    
    # データセットを作成
    train_dataset = LoRADataset(
        data_root=train_data_dir,
        tokenizer=tokenizer,
        size=resolution,
        repeats=1,
        center_crop=False,
    )
    
    train_dataloader = torch.utils.data.DataLoader(
        train_dataset,
        batch_size=train_batch_size,
        shuffle=True,
        collate_fn=collate_fn,
        num_workers=0,  # Windowsでは0に設定
    )
    
    # オプティマイザーを設定
    if use_8bit_adam:
        try:
            import bitsandbytes as bnb
            optimizer_class = bnb.optim.AdamW8bit  # type: ignore[misc]
        except ImportError:
            logger.warning("bitsandbytes not installed, using standard AdamW")
            optimizer_class = torch.optim.AdamW
    else:
        optimizer_class = torch.optim.AdamW
    
    optimizer = optimizer_class(
        unet.parameters(),
        lr=learning_rate,
        betas=(adam_beta1, adam_beta2),
        weight_decay=adam_weight_decay,
    )
    
    # 学習率スケジューラー
    lr_scheduler = get_scheduler(
        lr_scheduler,
        optimizer=optimizer,
        num_warmup_steps=lr_warmup_steps,
        num_training_steps=len(train_dataloader) * num_train_epochs,
    )
    
    # Acceleratorで準備
    unet, optimizer, train_dataloader, lr_scheduler = accelerator.prepare(
        unet, optimizer, train_dataloader, lr_scheduler
    )
    
    # 訓練ステップ数を計算
    num_update_steps_per_epoch = len(train_dataloader) // gradient_accumulation_steps
    if max_train_steps is None:
        max_train_steps = num_train_epochs * num_update_steps_per_epoch
    num_train_epochs = (max_train_steps // num_update_steps_per_epoch) + 1
    
    logger.info("Starting training...")
    logger.info(f"  Num examples: {len(train_dataset)}")
    logger.info(f"  Num Epochs: {num_train_epochs}")
    logger.info(f"  Instantaneous batch size per device: {train_batch_size}")
    logger.info(f"  Total train batch size: {train_batch_size * accelerator.num_processes * gradient_accumulation_steps}")
    logger.info(f"  Gradient Accumulation steps: {gradient_accumulation_steps}")
    logger.info(f"  Total optimization steps: {max_train_steps}")
    
    # 訓練ループ
    global_step = 0
    progress_bar = tqdm(range(max_train_steps), disable=not accelerator.is_local_main_process)
    progress_bar.set_description("Steps")
    
    for epoch in range(num_train_epochs):
        unet.train()
        train_loss = 0.0
        
        for step, batch in enumerate(train_dataloader):
            with accelerator.accumulate(unet):
                # 潜在変数に変換
                latents = vae.encode(batch["pixel_values"]).latent_dist.sample()
                latents = latents * vae.config.scaling_factor
                
                # ノイズを追加
                noise = torch.randn_like(latents)
                timesteps = torch.randint(0, noise_scheduler.config.num_train_timesteps, (latents.shape[0],), device=latents.device)
                noisy_latents = noise_scheduler.add_noise(latents, noise, timesteps)
                
                # テキストエンコーディング
                encoder_hidden_states = text_encoder(batch["input_ids"])[0]
                
                # 予測
                model_pred = unet(noisy_latents, timesteps, encoder_hidden_states).sample
                
                # 損失を計算
                loss = torch.nn.functional.mse_loss(model_pred.float(), noise.float(), reduction="mean")
                
                # バックプロパゲーション
                accelerator.backward(loss)
                optimizer.step()
                lr_scheduler.step()  # type: ignore
                optimizer.zero_grad()
            
            # ログ
            train_loss += loss.detach().item()
            progress_bar.update(1)
            global_step += 1
            
            if global_step >= max_train_steps:
                break
            
            if accelerator.is_main_process and global_step % 100 == 0:
                logger.info(f"Step {global_step}, Loss: {loss.item():.4f}")
        
        if global_step >= max_train_steps:
            break
    
    # モデルを保存
    accelerator.wait_for_everyone()
    if accelerator.is_main_process:
        logger.info("Saving model...")
        unet = accelerator.unwrap_model(unet)
        
        # LoRAの重みのみを保存
        if hasattr(unet, 'save_pretrained'):
            unet.save_pretrained(output_dir)
        else:
            # PEFTモデルの場合
            if hasattr(unet, 'save_pretrained'):
                unet.save_pretrained(output_dir)
            else:
                # フォールバック: フルモデルを保存
                pipe.unet = unet
                pipe.save_pretrained(output_dir)
        
        logger.info(f"Model saved to {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Simple LoRA Training Script")
    
    parser.add_argument("--pretrained_model", type=str, default="runwayml/stable-diffusion-v1-5",
                       help="Pretrained model name or path")
    parser.add_argument("--train_data_dir", type=str, default="./lora_dataset_mana_favorite",
                       help="Training data directory")
    parser.add_argument("--output_dir", type=str, default="./lora_output",
                       help="Output directory")
    parser.add_argument("--resolution", type=int, default=512,
                       help="Image resolution")
    parser.add_argument("--batch_size", type=int, default=1,
                       help="Batch size")
    parser.add_argument("--epochs", type=int, default=100,
                       help="Number of epochs")
    parser.add_argument("--learning_rate", type=float, default=1e-4,
                       help="Learning rate")
    parser.add_argument("--mixed_precision", type=str, default="fp16",
                       choices=["no", "fp16", "bf16"],
                       help="Mixed precision")
    
    args = parser.parse_args()
    
    train_lora(
        pretrained_model_name_or_path=args.pretrained_model,
        train_data_dir=args.train_data_dir,
        output_dir=args.output_dir,
        resolution=args.resolution,
        train_batch_size=args.batch_size,
        num_train_epochs=args.epochs,
        learning_rate=args.learning_rate,
        mixed_precision=args.mixed_precision,
    )


if __name__ == "__main__":
    main()


















