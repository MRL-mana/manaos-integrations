#!/usr/bin/env python3
"""
Trinity AI Optimized Batch Image Generator
高性能バッチ画像生成システム
"""

import os
import json
import time
import threading
import queue
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import psutil
import torch
from diffusers import StableDiffusionPipeline
from transformers import CLIPTextModel, CLIPTokenizer
from diffusers import UNet2DConditionModel, AutoencoderKL
from PIL import Image
import numpy as np
from typing import List, Dict, Tuple
import logging

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OptimizedBatchGenerator:
    def __init__(self, model_dir="/mnt/storage500/civitai_models", max_workers=2):
        self.model_dir = model_dir
        self.max_workers = max_workers
        self.models = self._load_model_metadata()
        self.pipeline = None
        self.current_model_name = None
        self.generation_queue = queue.Queue()
        self.results = []
        
    def _load_model_metadata(self):
        """モデルメタデータを読み込む"""
        models = []
        for f in os.listdir(self.model_dir):
            if f.endswith(".json"):
                try:
                    with open(os.path.join(self.model_dir, f), 'r') as fp:
                        metadata = json.load(fp)
                        model_path = os.path.join(self.model_dir, metadata.get("filename", "").replace(".json", ".safetensors"))
                        if os.path.exists(model_path):
                            models.append({
                                "name": metadata.get("name", os.path.splitext(f)[0]),
                                "type": metadata.get("type", "unknown"),
                                "size": os.path.getsize(model_path) / (1024 * 1024), # MB
                                "path": model_path,
                                "description": metadata.get("description", "N/A")
                            })
                except Exception as e:
                    logger.warning(f"モデルメタデータの読み込みエラー {f}: {e}")
        return models

    def load_model(self, model_name):
        """指定されたモデルを読み込む"""
        model_info = next((m for m in self.models if m["name"] == model_name), None)
        if not model_info:
            logger.error(f"モデル '{model_name}' が見つかりません。")
            return False

        logger.info(f"📥 モデル読み込み中: {model_name}")
        logger.info(f"   サイズ: {model_info['size']:.1f}MB")

        try:
            # CLIPTextModelとUNet2DConditionModelを明示的に読み込む
            text_encoder = CLIPTextModel.from_pretrained("openai/clip-vit-large-patch14")
            tokenizer = CLIPTokenizer.from_pretrained("openai/clip-vit-large-patch14")
            unet = UNet2DConditionModel.from_pretrained("runwayml/stable-diffusion-v1-5", subfolder="unet")
            vae = AutoencoderKL.from_pretrained("stabilityai/sd-vae-ft-mse")

            self.pipeline = StableDiffusionPipeline.from_single_file(
                str(model_info["path"]),
                torch_dtype=torch.float32,
                use_safetensors=True,
                text_encoder=text_encoder,
                tokenizer=tokenizer,
                unet=unet,
                vae=vae,
                safety_checker=None
            )

            # CPU最適化
            self.pipeline = self.pipeline.to("cpu")
            self.pipeline.enable_attention_slicing()

            self.current_model_name = model_name
            logger.info(f"✅ モデル読み込み完了: {model_name}")
            return True
        except Exception as e:
            logger.error(f"❌ モデル読み込みエラー: {e}")
            self.pipeline = None
            self.current_model_name = None
            return False

    def generate_single_image(self, prompt: str, width: int = 512, height: int = 512, 
                            num_inference_steps: int = 20, seed: int = None) -> Tuple[str, float]:  # type: ignore
        """単一画像を生成する"""
        if not self.pipeline:
            raise RuntimeError("モデルが読み込まれていません。")

        if seed is not None:
            torch.manual_seed(seed)

        start_time = time.time()
        try:
            image = self.pipeline(
                prompt,
                width=width,
                height=height,
                num_inference_steps=num_inference_steps
            ).images[0]
            
            generation_time = time.time() - start_time
            
            # 画像を保存
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = "/root/trinity_workspace/generated_images"
            os.makedirs(output_dir, exist_ok=True)
            filename = f"batch_{self.current_model_name}_{timestamp}_{seed or 'random'}.png"
            filepath = os.path.join(output_dir, filename)
            image.save(filepath)
            
            return filepath, generation_time
        except Exception as e:
            logger.error(f"❌ 画像生成エラー: {e}")
            return None, 0  # type: ignore

    def generate_batch(self, prompts: List[str], width: int = 512, height: int = 512,
                      num_inference_steps: int = 20, seeds: List[int] = None) -> Dict:  # type: ignore
        """バッチ画像生成を実行する"""
        if not self.pipeline:
            raise RuntimeError("モデルが読み込まれていません。")

        logger.info(f"🚀 バッチ生成開始: {len(prompts)}枚")
        logger.info(f"   ワーカー数: {self.max_workers}")
        logger.info(f"   サイズ: {width}x{height}")

        results = {
            "total": len(prompts),
            "success": 0,
            "failed": 0,
            "files": [],
            "total_time": 0,
            "average_time": 0
        }

        start_time = time.time()

        # スレッドプールで並列生成
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            
            for i, prompt in enumerate(prompts):
                seed = seeds[i] if seeds and i < len(seeds) else None
                future = executor.submit(
                    self.generate_single_image,
                    prompt, width, height, num_inference_steps, seed  # type: ignore
                )
                futures.append((i, future))

            # 結果を収集
            for i, future in futures:
                try:
                    filepath, gen_time = future.result(timeout=600)  # 10分タイムアウト
                    if filepath:
                        results["success"] += 1
                        results["files"].append({
                            "index": i,
                            "filepath": filepath,
                            "generation_time": gen_time,
                            "prompt": prompts[i]
                        })
                        logger.info(f"✅ 画像 {i+1}/{len(prompts)} 生成完了: {gen_time:.1f}秒")
                    else:
                        results["failed"] += 1
                        logger.error(f"❌ 画像 {i+1}/{len(prompts)} 生成失敗")
                except Exception as e:
                    results["failed"] += 1
                    logger.error(f"❌ 画像 {i+1}/{len(prompts)} 生成エラー: {e}")

        total_time = time.time() - start_time
        results["total_time"] = total_time
        results["average_time"] = total_time / len(prompts) if prompts else 0

        logger.info(f"🎉 バッチ生成完了: {results['success']}/{results['total']} 成功")
        logger.info(f"   総時間: {total_time:.1f}秒")
        logger.info(f"   平均時間: {results['average_time']:.1f}秒/枚")

        return results

    def generate_style_variations(self, base_prompt: str, styles: List[str], 
                                width: int = 512, height: int = 512) -> Dict:
        """スタイルバリエーションを生成する"""
        prompts = [f"{base_prompt}, {style}" for style in styles]
        return self.generate_batch(prompts, width, height)

    def generate_size_variations(self, prompt: str, sizes: List[Tuple[int, int]]) -> Dict:
        """サイズバリエーションを生成する"""
        results = {"total": len(sizes), "success": 0, "failed": 0, "files": []}
        
        for i, (width, height) in enumerate(sizes):
            try:
                filepath, gen_time = self.generate_single_image(prompt, width, height)
                if filepath:
                    results["success"] += 1
                    results["files"].append({
                        "size": f"{width}x{height}",
                        "filepath": filepath,
                        "generation_time": gen_time
                    })
                    logger.info(f"✅ サイズ {width}x{height} 生成完了: {gen_time:.1f}秒")
                else:
                    results["failed"] += 1
            except Exception as e:
                results["failed"] += 1
                logger.error(f"❌ サイズ {width}x{height} 生成エラー: {e}")

        return results

    def get_system_status(self):
        """システム状態を取得する"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "cpu_percent": cpu_percent,
            "memory_total": memory.total / (1024**3),
            "memory_available": memory.available / (1024**3),
            "memory_percent": memory.percent,
            "disk_total": disk.total / (1024**3),
            "disk_free": disk.free / (1024**3),
            "disk_percent": (disk.used / disk.total) * 100
        }

    def optimize_workers(self):
        """最適なワーカー数を計算する"""
        status = self.get_system_status()
        
        # CPU使用率とメモリ使用率に基づいて最適なワーカー数を決定
        if status["cpu_percent"] < 50 and status["memory_percent"] < 70:
            optimal_workers = min(4, psutil.cpu_count())  # type: ignore
        elif status["cpu_percent"] < 80 and status["memory_percent"] < 85:
            optimal_workers = min(2, psutil.cpu_count())  # type: ignore
        else:
            optimal_workers = 1
            
        self.max_workers = optimal_workers
        logger.info(f"🔧 最適ワーカー数: {optimal_workers}")
        return optimal_workers

def main():
    """メイン実行関数"""
    print("🚀 Trinity AI Optimized Batch Generator")
    print("=" * 60)
    
    generator = OptimizedBatchGenerator()
    
    # システム状態表示
    status = generator.get_system_status()
    print(f"💻 システム状態:")
    print(f"   CPU: {status['cpu_percent']:.1f}%")
    print(f"   メモリ: {status['memory_percent']:.1f}% ({status['memory_available']:.1f}GB 利用可能)")
    print(f"   ディスク: {status['disk_percent']:.1f}% ({status['disk_free']:.1f}GB 空き)")
    
    # 最適ワーカー数計算
    optimal_workers = generator.optimize_workers()
    
    # 利用可能なモデル表示
    print(f"\n🎨 利用可能なモデル:")
    for model in generator.models:
        print(f"   📦 {model['name']} ({model['size']:.1f}MB)")
    
    # 動作確認済みモデルを読み込む
    if generator.models:
        model_name = generator.models[0]["name"]  # 最初のモデルを使用
        print(f"\n📥 モデル読み込み中: {model_name}")
        if generator.load_model(model_name):
            print("✅ モデル読み込み完了")
            
            # バッチ生成デモ
            print(f"\n🎨 バッチ生成デモ開始")
            prompts = [
                "a beautiful anime girl, high quality, detailed",
                "a futuristic city, cyberpunk style, neon lights",
                "a serene forest, fantasy art, magical atmosphere",
                "a cute cat, kawaii style, adorable",
                "a professional business person, corporate style"
            ]
            
            results = generator.generate_batch(prompts)
            print(f"\n🎉 バッチ生成完了:")
            print(f"   成功: {results['success']}/{results['total']}")
            print(f"   総時間: {results['total_time']:.1f}秒")
            print(f"   平均時間: {results['average_time']:.1f}秒/枚")
            
            # スタイルバリエーションデモ
            print(f"\n🎭 スタイルバリエーションデモ")
            styles = ["anime style", "realistic", "oil painting", "watercolor", "digital art"]
            style_results = generator.generate_style_variations(
                "a beautiful girl", styles
            )
            print(f"   スタイルバリエーション: {style_results['success']}/{style_results['total']} 成功")
            
        else:
            print("❌ モデルの読み込みに失敗しました。")
    else:
        print("❌ 利用可能なモデルがありません。")

if __name__ == "__main__":
    main()

