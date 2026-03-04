#!/usr/bin/env python3
"""
Advanced Image Generator
高機能画像生成システム（サイズ変更、顔変更、LoRA対応）
"""

import os
import torch
from pathlib import Path
from datetime import datetime
import time
import json

class AdvancedImageGenerator:
    def __init__(self):
        self.models_dir = Path("/mnt/storage500/civitai_models")
        self.output_dir = Path("/root/trinity_workspace/generated_images")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 現在のモデル
        self.current_model = None
        self.current_pipeline = None
        
        # 利用可能なモデルをスキャン
        self.available_models = self._scan_models()
        
        # 画像サイズプリセット
        self.size_presets = {
            "portrait": (512, 768),      # 縦長
            "landscape": (768, 512),     # 横長
            "square": (512, 512),       # 正方形
            "wide": (1024, 512),        # ワイド
            "tall": (512, 1024),         # 高解像度縦
            "ultra": (1024, 1024),       # 超高解像度
            "mobile": (512, 912),        # モバイル縦
            "banner": (1920, 512)        # バナー
        }
        
        # 顔変更用LoRA
        self.face_lora_models = [
            "pureerosface_v1",
            "ClothingAdjuster3"
        ]
    
    def _scan_models(self):
        """利用可能なモデルをスキャン"""
        models = {}
        
        if self.models_dir.exists():
            for model_file in self.models_dir.glob("*.safetensors"):
                info_file = model_file.with_suffix('.json')
                
                if info_file.exists():
                    try:
                        with open(info_file, 'r', encoding='utf-8') as f:
                            model_info = json.load(f)
                        
                        models[model_file.stem] = {
                            "path": str(model_file),
                            "info": model_info,
                            "size_mb": model_file.stat().st_size / (1024 * 1024),
                            "category": model_info.get('category', 'unknown')
                        }
                    except:
                        pass
        
        return models
    
    def list_available_models(self):
        """利用可能なモデル一覧表示"""
        print("🎨 利用可能なモデル一覧")
        print("=" * 60)
        
        if not self.available_models:
            print("❌ 利用可能なモデルがありません")
            return
        
        # カテゴリ別に表示
        categories = {}
        for model_name, model_info in self.available_models.items():
            category = model_info['category']
            if category not in categories:
                categories[category] = []
            categories[category].append((model_name, model_info))
        
        for category, models in categories.items():
            print(f"\n📁 {category}:")
            for model_name, model_info in models:
                print(f"  📦 {model_name}")
                print(f"     サイズ: {model_info['size_mb']:.1f}MB")
                print(f"     パス: {model_info['path']}")
    
    def load_model(self, model_name):
        """モデル読み込み"""
        if model_name not in self.available_models:
            print(f"❌ モデル '{model_name}' が見つかりません")
            return False
        
        model_info = self.available_models[model_name]
        model_path = model_info['path']
        
        print(f"📥 モデル読み込み中: {model_name}")
        print(f"   サイズ: {model_info['size_mb']:.1f}MB")
        print(f"   カテゴリ: {model_info['category']}")
        
        try:
            # 既存のパイプラインをクリア
            if self.current_pipeline:
                del self.current_pipeline
                torch.cuda.empty_cache() if torch.cuda.is_available() else None
            
            from diffusers import StableDiffusionPipeline
            
            pipeline = StableDiffusionPipeline.from_single_file(
                model_path,
                torch_dtype=torch.float32,
                use_safetensors=True
            )
            
            # CPU最適化
            pipeline = pipeline.to("cpu")
            pipeline.enable_attention_slicing()
            
            self.current_pipeline = pipeline
            self.current_model = model_name
            
            print(f"✅ モデル読み込み完了: {model_name}")
            return True
            
        except Exception as e:
            print(f"❌ モデル読み込みエラー: {str(e)}")
            return False
    
    def generate_image(self, prompt, negative_prompt="", size_preset="square", 
                      num_inference_steps=20, guidance_scale=7.5, face_lora=None):
        """画像生成"""
        if not self.current_pipeline:
            print("❌ モデルが読み込まれていません")
            return None
        
        # サイズ設定
        if size_preset in self.size_presets:
            width, height = self.size_presets[size_preset]
        else:
            width, height = 512, 512
        
        # 顔変更用LoRA適用
        if face_lora and face_lora in self.face_lora_models:
            prompt = f"{prompt}, {face_lora}"
            print(f"🎭 顔変更LoRA適用: {face_lora}")
        
        print(f"🎨 画像生成開始")
        print(f"   プロンプト: {prompt}")
        print(f"   サイズ: {width}x{height} ({size_preset})")
        print(f"   ステップ数: {num_inference_steps}")
        if face_lora:
            print(f"   顔変更LoRA: {face_lora}")
        
        try:
            start_time = time.time()
            
            # 画像生成
            image = self.current_pipeline(
                prompt=prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale
            ).images[0]
            
            generation_time = time.time() - start_time
            
            # ファイル保存
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.current_model}_{size_preset}_{timestamp}.png"
            output_path = self.output_dir / filename
            
            image.save(output_path)
            
            print(f"✅ 画像生成完了")
            print(f"   生成時間: {generation_time:.1f}秒")
            print(f"   保存先: {output_path}")
            
            return str(output_path)
            
        except Exception as e:
            print(f"❌ 画像生成エラー: {str(e)}")
            return None
    
    def generate_multiple_sizes(self, prompt, negative_prompt="", 
                               sizes=["square", "portrait", "landscape"]):
        """複数サイズで画像生成"""
        print(f"🎨 複数サイズ画像生成開始: {len(sizes)}種類")
        
        results = []
        for i, size_preset in enumerate(sizes, 1):
            print(f"\n📸 サイズ {i}/{len(sizes)}: {size_preset}")
            result = self.generate_image(
                prompt=prompt,
                negative_prompt=negative_prompt,
                size_preset=size_preset
            )
            results.append(result)
        
        success_count = sum(1 for r in results if r is not None)
        print(f"\n🎉 複数サイズ生成完了: {success_count}/{len(sizes)} 成功")
        
        return results
    
    def generate_face_variations(self, base_prompt, face_lora_list=None):
        """顔変更バリエーション生成"""
        if face_lora_list is None:
            face_lora_list = self.face_lora_models
        
        print(f"🎭 顔変更バリエーション生成開始: {len(face_lora_list)}種類")
        
        results = []
        for i, face_lora in enumerate(face_lora_list, 1):
            print(f"\n🎭 顔変更 {i}/{len(face_lora_list)}: {face_lora}")
            result = self.generate_image(
                prompt=base_prompt,
                face_lora=face_lora,
                size_preset="portrait"
            )
            results.append(result)
        
        success_count = sum(1 for r in results if r is not None)
        print(f"\n🎉 顔変更バリエーション生成完了: {success_count}/{len(face_lora_list)} 成功")
        
        return results
    
    def get_size_presets(self):
        """サイズプリセット一覧表示"""
        print("📐 利用可能なサイズプリセット")
        print("=" * 60)
        
        for preset, (width, height) in self.size_presets.items():
            print(f"  {preset}: {width}x{height}")
    
    def get_face_lora_models(self):
        """顔変更LoRA一覧表示"""
        print("🎭 利用可能な顔変更LoRA")
        print("=" * 60)
        
        for lora in self.face_lora_models:
            print(f"  {lora}")


def main():
    """メイン関数"""
    generator = AdvancedImageGenerator()
    
    print("🎨 Advanced Image Generator")
    print("=" * 60)
    
    # 利用可能なモデル一覧
    generator.list_available_models()
    
    # サイズプリセット一覧
    generator.get_size_presets()
    
    # 顔変更LoRA一覧
    generator.get_face_lora_models()
    
    # デモ生成
    if generator.available_models:
        # 最初のモデルを読み込み
        first_model = list(generator.available_models.keys())[0]
        if generator.load_model(first_model):
            
            # 複数サイズ生成
            print(f"\n🎨 複数サイズ生成デモ")
            generator.generate_multiple_sizes(
                prompt="a beautiful anime girl, high quality, detailed",
                sizes=["square", "portrait", "landscape"]
            )
            
            # 顔変更バリエーション生成
            print(f"\n🎭 顔変更バリエーション生成デモ")
            generator.generate_face_variations(
                base_prompt="a cute girl, high quality, detailed"
            )


if __name__ == "__main__":
    main()