#!/usr/bin/env python3
"""
CivitAI AI Generator
ダウンロードしたCivitAIモデルを使用したAI画像生成
"""

import os
import json
import torch
from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
from PIL import Image
import time
from pathlib import Path
from datetime import datetime

class CivitAIAIGenerator:
    def __init__(self):
        self.models_dir = Path("/root/civitai_models")
        self.output_dir = Path("/root/mana-workspace/outputs/images")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # ダウンロード済みモデル情報
        self.available_models = self._load_available_models()
        
        # 現在のパイプライン
        self.pipeline = None
        self.current_model = None
    
    def _load_available_models(self):
        """利用可能なモデルを読み込み"""
        models = []
        
        for json_file in self.models_dir.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    model_info = json.load(f)
                    models.append(model_info)
            except Exception as e:
                print(f"❌ モデル情報読み込みエラー: {json_file} - {str(e)}")
        
        return models
    
    def list_available_models(self):
        """利用可能なモデル一覧表示"""
        if not self.available_models:
            print("📭 利用可能なモデルがありません")
            return
        
        print(f"🎨 利用可能なCivitAIモデル: {len(self.available_models)}件")
        print("=" * 80)
        
        for i, model in enumerate(self.available_models, 1):
            print(f"\n{i}. {model['name']}")
            print(f"   🆔 ID: {model['id']}")
            print(f"   📦 バージョン: {model['version']}")
            print(f"   🏷️ タイプ: {model['type']}")
            print(f"   🎯 ベースモデル: {model['base_model']}")
            print(f"   📁 ファイル: {model['filename']}")
            print(f"   🏷️ タグ: {', '.join(model['tags'][:5])}")
    
    def load_model(self, model_name_or_index):
        """モデルを読み込み"""
        try:
            # インデックスまたは名前でモデルを選択
            if isinstance(model_name_or_index, int):
                if 0 <= model_name_or_index < len(self.available_models):
                    model_info = self.available_models[model_name_or_index]
                else:
                    print(f"❌ 無効なインデックス: {model_name_or_index}")
                    return False
            else:
                # 名前で検索
                model_info = None
                for model in self.available_models:
                    if model_name_or_index.lower() in model['name'].lower():
                        model_info = model
                        break
                
                if model_info is None:
                    print(f"❌ モデルが見つかりません: {model_name_or_index}")
                    return False
            
            model_path = self.models_dir / model_info['filename']
            
            if not model_path.exists():
                print(f"❌ モデルファイルが見つかりません: {model_path}")
                return False
            
            print(f"🔄 モデル読み込み中: {model_info['name']}")
            print(f"📁 パス: {model_path}")
            
            # パイプラインを読み込み（Checkpointモデルのみ）
            if model_info['type'] == 'Checkpoint':
                self.pipeline = StableDiffusionPipeline.from_single_file(
                    str(model_path),
                    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                    use_safetensors=True
                )
            else:
                print(f"❌ このモデルタイプはサポートされていません: {model_info['type']}")
                print("💡 Checkpointモデルのみサポートしています")
                return False
            
            # CPU最適化
            if not torch.cuda.is_available():
                self.pipeline = self.pipeline.to("cpu")
                # CPU環境での最適化
                self.pipeline.enable_attention_slicing()
                # enable_sequential_cpu_offload はCPU環境では不要
            
            # スケジューラーを設定
            self.pipeline.scheduler = DPMSolverMultistepScheduler.from_config(
                self.pipeline.scheduler.config
            )
            
            self.current_model = model_info
            print(f"✅ モデル読み込み完了: {model_info['name']}")
            return True
            
        except Exception as e:
            print(f"❌ モデル読み込みエラー: {str(e)}")
            return False
    
    def generate_image(self, prompt, negative_prompt="", width=512, height=512, 
                      num_inference_steps=20, guidance_scale=7.5, num_images=1):
        """画像生成"""
        if self.pipeline is None:
            print("❌ モデルが読み込まれていません")
            return None
        
        try:
            print(f"🎨 画像生成中...")
            print(f"📝 プロンプト: {prompt}")
            print(f"🚫 ネガティブ: {negative_prompt}")
            print(f"📐 サイズ: {width}x{height}")
            print(f"🔄 ステップ数: {num_inference_steps}")
            
            start_time = time.time()
            
            # 画像生成
            images = self.pipeline(
                prompt=prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
                num_images_per_prompt=num_images
            ).images
            
            generation_time = time.time() - start_time
            print(f"⏱️ 生成時間: {generation_time:.1f}秒")
            
            # 画像を保存
            saved_paths = []
            for i, image in enumerate(images):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                model_name = self.current_model['name'].replace(' ', '_').replace('/', '_')  # type: ignore[index]
                filename = f"civitai_{model_name}_{timestamp}_{i+1}.png"
                filepath = self.output_dir / filename
                
                image.save(filepath)
                saved_paths.append(str(filepath))
                print(f"💾 保存完了: {filename}")
            
            return saved_paths
            
        except Exception as e:
            print(f"❌ 画像生成エラー: {str(e)}")
            return None
    
    def generate_with_style(self, prompt, style="realistic", **kwargs):
        """スタイル指定で画像生成"""
        style_prompts = {
            "realistic": "photorealistic, high quality, detailed, 8k, masterpiece",
            "anime": "anime style, manga, japanese animation, colorful",
            "artistic": "artistic, painting, oil painting, masterpiece",
            "fantasy": "fantasy art, magical, mystical, ethereal",
            "portrait": "portrait, close-up, detailed face, professional photography"
        }
        
        style_negative = {
            "realistic": "cartoon, anime, drawing, sketch, low quality, blurry",
            "anime": "realistic, photorealistic, 3d, low quality",
            "artistic": "photorealistic, 3d, low quality, blurry",
            "fantasy": "realistic, photorealistic, low quality",
            "portrait": "full body, landscape, low quality, blurry"
        }
        
        if style in style_prompts:
            enhanced_prompt = f"{prompt}, {style_prompts[style]}"
            negative_prompt = style_negative.get(style, "")
        else:
            enhanced_prompt = prompt
            negative_prompt = ""
        
        return self.generate_image(enhanced_prompt, negative_prompt, **kwargs)
    
    def batch_generate(self, prompts, model_index=0, **kwargs):
        """バッチ画像生成"""
        if not self.load_model(model_index):
            return None
        
        results = []
        for i, prompt in enumerate(prompts, 1):
            print(f"\n🎨 バッチ生成 {i}/{len(prompts)}: {prompt}")
            result = self.generate_image(prompt, **kwargs)
            if result:
                results.extend(result)
        
        return results


def main():
    """メイン関数"""
    generator = CivitAIAIGenerator()
    
    print("🎨 CivitAI AI Generator for Trinity")
    print("=" * 60)
    
    # 利用可能なモデル一覧
    generator.list_available_models()
    
    if not generator.available_models:
        print("❌ 利用可能なモデルがありません")
        print("💡 まず civitai_model_downloader.py を実行してください")
        return
    
    # Checkpointモデルを探して読み込み
    checkpoint_models = [i for i, model in enumerate(generator.available_models) if model['type'] == 'Checkpoint']
    
    if not checkpoint_models:
        print("❌ Checkpointモデルが見つかりません")
        return
    
    print(f"\n🔄 Checkpointモデル読み込み中...")
    if not generator.load_model(checkpoint_models[0]):
        print("❌ モデル読み込みに失敗しました")
        return
    
    # サンプル画像生成
    print(f"\n🎨 サンプル画像生成中...")
    
    sample_prompts = [
        "1girl, beautiful face, detailed eyes, long hair, portrait",
        "fantasy landscape, magical forest, ethereal lighting",
        "anime character, colorful, detailed, high quality"
    ]
    
    for i, prompt in enumerate(sample_prompts, 1):
        print(f"\n📝 プロンプト {i}: {prompt}")
        result = generator.generate_with_style(prompt, "realistic")
        if result:
            print(f"✅ 生成完了: {len(result)}枚")
        else:
            print(f"❌ 生成失敗")
    
    print(f"\n🎉 CivitAI画像生成完了！")
    print(f"📁 出力ディレクトリ: {generator.output_dir}")


if __name__ == "__main__":
    main()
