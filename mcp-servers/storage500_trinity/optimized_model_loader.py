#!/usr/bin/env python3
"""
Optimized Model Loader
CLIPTextModel問題を解決した最適化モデルローダー
"""

import os
import json
import torch
from pathlib import Path
from datetime import datetime
import time
import psutil

class OptimizedModelLoader:
    def __init__(self):
        self.models_dir = Path("/root/civitai_models")
        self.output_dir = Path("/root/trinity_workspace/generated_images")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 利用可能なモデルをスキャン
        self.available_models = self._scan_models()
        
        # 現在のモデル
        self.current_model = None
        self.current_pipeline = None
        
        # システム情報
        self.system_info = self._get_system_info()
    
    def _scan_models(self):
        """利用可能なモデルをスキャン"""
        models = {}
        
        for model_file in self.models_dir.glob("*.safetensors"):
            info_file = model_file.with_suffix('.json')
            
            if info_file.exists():
                try:
                    with open(info_file, 'r', encoding='utf-8') as f:
                        model_info = json.load(f)
                    
                    # モデル分類
                    model_type = self._classify_model(model_file.name, model_info)
                    
                    models[model_file.stem] = {
                        "path": str(model_file),
                        "info": model_info,
                        "type": model_type,
                        "size_mb": model_file.stat().st_size / (1024 * 1024)
                    }
                except Exception as e:
                    print(f"⚠️ モデル情報読み込みエラー: {model_file.name} - {str(e)}")
        
        return models
    
    def _classify_model(self, filename, model_info):
        """モデルを分類"""
        name_lower = filename.lower()
        info_name = model_info.get('name', '').lower()
        
        # WAN 2.2系
        if any(keyword in name_lower or keyword in info_name for keyword in 
               ['wan', 'waifu', 'anime', 'majicmix']):
            return "wan_2_2"
        
        # SDXL系
        elif any(keyword in name_lower or keyword in info_name for keyword in 
                 ['sdxl', 'xl', 'realistic', 'real']):
            return "sdxl"
        
        # Fast系
        elif any(keyword in name_lower or keyword in info_name for keyword in 
                 ['fast', 'tiny', 'small', 'light', 'lora']):
            return "fast"
        
        # デフォルト
        else:
            return "unknown"
    
    def _get_system_info(self):
        """システム情報取得"""
        memory = psutil.virtual_memory()
        return {
            "memory_gb": memory.total / (1024**3),
            "available_memory_gb": memory.available / (1024**3),
            "cpu_cores": psutil.cpu_count(logical=False),
            "cpu_threads": psutil.cpu_count(logical=True)
        }
    
    def load_model_with_clip_fix(self, model_path, model_type="unknown"):
        """CLIPTextModel問題を解決したモデル読み込み"""
        try:
            from diffusers import StableDiffusionPipeline, StableDiffusionXLPipeline
            from transformers import CLIPTextModel, CLIPTextModelWithProjection
            
            print(f"🔧 CLIPTextModel問題を解決中...")
            
            # モデルタイプに応じた読み込み
            if model_type == "sdxl":
                # SDXL用のCLIPTextModel
                text_encoder = CLIPTextModel.from_pretrained("stabilityai/stable-diffusion-xl-base-1.0", subfolder="text_encoder")
                text_encoder_2 = CLIPTextModelWithProjection.from_pretrained("stabilityai/stable-diffusion-xl-base-1.0", subfolder="text_encoder_2")
                
                pipeline = StableDiffusionXLPipeline.from_single_file(
                    model_path,
                    text_encoder=text_encoder,
                    text_encoder_2=text_encoder_2,
                    torch_dtype=torch.float32,
                    use_safetensors=True
                )
            else:
                # 通常のSD用のCLIPTextModel
                text_encoder = CLIPTextModel.from_pretrained("runwayml/stable-diffusion-v1-5", subfolder="text_encoder")
                
                pipeline = StableDiffusionPipeline.from_single_file(
                    model_path,
                    text_encoder=text_encoder,
                    torch_dtype=torch.float32,
                    use_safetensors=True
                )
            
            # CPU最適化
            pipeline = pipeline.to("cpu")
            pipeline.enable_attention_slicing()
            
            print(f"✅ モデル読み込み完了（CLIPTextModel問題解決済み）")
            return pipeline
            
        except Exception as e:
            print(f"❌ モデル読み込みエラー: {str(e)}")
            return None
    
    def load_model(self, model_name):
        """モデル読み込み"""
        if model_name not in self.available_models:
            print(f"❌ モデル '{model_name}' が見つかりません")
            return False
        
        model_info = self.available_models[model_name]
        model_path = model_info['path']
        model_type = model_info['type']
        
        print(f"📥 モデル読み込み中: {model_name}")
        print(f"   タイプ: {model_type}")
        print(f"   パス: {model_path}")
        
        try:
            # 既存のパイプラインをクリア
            if self.current_pipeline:
                del self.current_pipeline
                torch.cuda.empty_cache() if torch.cuda.is_available() else None
            
            # CLIPTextModel問題を解決した読み込み
            self.current_pipeline = self.load_model_with_clip_fix(model_path, model_type)
            
            if self.current_pipeline:
                self.current_model = model_name
                print(f"✅ モデル読み込み完了: {model_name}")
                return True
            else:
                print(f"❌ モデル読み込み失敗: {model_name}")
                return False
            
        except Exception as e:
            print(f"❌ モデル読み込みエラー: {str(e)}")
            return False
    
    def generate_image(self, prompt, negative_prompt="", width=512, height=512, 
                      num_inference_steps=20, guidance_scale=7.5):
        """画像生成"""
        if not self.current_pipeline:
            print("❌ モデルが読み込まれていません")
            return None
        
        print(f"🎨 画像生成開始")
        print(f"   プロンプト: {prompt}")
        print(f"   サイズ: {width}x{height}")
        print(f"   ステップ数: {num_inference_steps}")
        
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
            filename = f"{self.current_model}_{timestamp}.png"
            output_path = self.output_dir / filename
            
            image.save(output_path)
            
            print(f"✅ 画像生成完了")
            print(f"   生成時間: {generation_time:.1f}秒")
            print(f"   保存先: {output_path}")
            
            return str(output_path)
            
        except Exception as e:
            print(f"❌ 画像生成エラー: {str(e)}")
            return None
    
    def benchmark_all_models(self):
        """全モデルのベンチマーク"""
        print("🚀 全モデルベンチマーク開始（CLIPTextModel問題解決版）")
        print("=" * 60)
        
        benchmark_results = {}
        test_prompt = "a beautiful landscape, high quality, detailed"
        
        for model_name, model_info in self.available_models.items():
            print(f"\n📊 ベンチマーク: {model_name}")
            print(f"   タイプ: {model_info['type']}")
            print(f"   サイズ: {model_info['size_mb']:.1f}MB")
            
            # モデル読み込み
            if not self.load_model(model_name):
                print(f"❌ {model_name} の読み込みに失敗")
                benchmark_results[model_name] = {
                    "type": model_info['type'],
                    "size_mb": model_info['size_mb'],
                    "generation_time": None,
                    "success": False,
                    "output_path": None
                }
                continue
            
            # 生成テスト
            start_time = time.time()
            output_path = self.generate_image(
                prompt=test_prompt,
                width=512,
                height=512,
                num_inference_steps=20
            )
            total_time = time.time() - start_time
            
            if output_path:
                benchmark_results[model_name] = {
                    "type": model_info['type'],
                    "size_mb": model_info['size_mb'],
                    "generation_time": total_time,
                    "success": True,
                    "output_path": output_path
                }
                print(f"✅ ベンチマーク完了: {total_time:.1f}秒")
            else:
                benchmark_results[model_name] = {
                    "type": model_info['type'],
                    "size_mb": model_info['size_mb'],
                    "generation_time": None,
                    "success": False,
                    "output_path": None
                }
                print(f"❌ ベンチマーク失敗")
        
        # 結果サマリー
        print(f"\n📊 ベンチマーク結果サマリー")
        print("=" * 60)
        
        success_count = 0
        for model_name, result in benchmark_results.items():
            if result['success']:
                print(f"✅ {model_name}: {result['generation_time']:.1f}秒")
                success_count += 1
            else:
                print(f"❌ {model_name}: 失敗")
        
        print(f"\n🎉 成功: {success_count}/{len(benchmark_results)} モデル")
        
        return benchmark_results
    
    def get_system_status(self):
        """システム状態表示"""
        print("💻 システム状態")
        print("=" * 60)
        print(f"メモリ: {self.system_info['memory_gb']:.1f}GB (利用可能: {self.system_info['available_memory_gb']:.1f}GB)")
        print(f"CPU: {self.system_info['cpu_cores']} cores, {self.system_info['cpu_threads']} threads")
        print(f"現在のモデル: {self.current_model if self.current_model else 'なし'}")
        print(f"利用可能モデル数: {len(self.available_models)}")
    
    def list_available_models(self):
        """利用可能なモデル一覧表示"""
        print("🎨 利用可能なモデル一覧")
        print("=" * 60)
        
        if not self.available_models:
            print("❌ 利用可能なモデルがありません")
            return
        
        for model_name, model_info in self.available_models.items():
            print(f"\n📦 {model_name}:")
            print(f"   タイプ: {model_info['type']}")
            print(f"   サイズ: {model_info['size_mb']:.1f}MB")
            print(f"   パス: {model_info['path']}")
            
            if 'info' in model_info and 'name' in model_info['info']:
                print(f"   名前: {model_info['info']['name']}")


def main():
    """メイン関数"""
    loader = OptimizedModelLoader()
    
    print("🎨 Optimized Model Loader 起動")
    print("=" * 60)
    
    # システム状態表示
    loader.get_system_status()
    
    # 利用可能モデル一覧
    loader.list_available_models()
    
    # ベンチマーク実行
    loader.benchmark_all_models()


if __name__ == "__main__":
    main()


