#!/usr/bin/env python3
"""
Ultimate Model System
完全統合されたAI画像生成システム
"""

import os
import json
import torch
from pathlib import Path
from datetime import datetime
import time
import psutil
import subprocess

class UltimateModelSystem:
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
        
        # 生成統計
        self.generation_stats = {
            "total_generations": 0,
            "successful_generations": 0,
            "failed_generations": 0,
            "total_time": 0,
            "average_time": 0
        }
    
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
    
    def load_working_model(self):
        """動作確認済みモデルを読み込み"""
        # majicmixRealistic_v7が動作確認済み
        working_model = "majicmixRealistic_v7"
        
        if working_model not in self.available_models:
            print(f"❌ 動作確認済みモデル '{working_model}' が見つかりません")
            return False
        
        model_info = self.available_models[working_model]
        model_path = model_info['path']
        
        print(f"📥 動作確認済みモデル読み込み中: {working_model}")
        print(f"   タイプ: {model_info['type']}")
        print(f"   サイズ: {model_info['size_mb']:.1f}MB")
        
        try:
            # 既存のパイプラインをクリア
            if self.current_pipeline:
                del self.current_pipeline
                torch.cuda.empty_cache() if torch.cuda.is_available() else None
            
            # 動作確認済みの読み込み方法
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
            self.current_model = working_model
            
            print(f"✅ 動作確認済みモデル読み込み完了: {working_model}")
            return True
            
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
            
            # 統計更新
            self.generation_stats["total_generations"] += 1
            self.generation_stats["successful_generations"] += 1
            self.generation_stats["total_time"] += generation_time
            self.generation_stats["average_time"] = (
                self.generation_stats["total_time"] / 
                self.generation_stats["successful_generations"]
            )
            
            print(f"✅ 画像生成完了")
            print(f"   生成時間: {generation_time:.1f}秒")
            print(f"   保存先: {output_path}")
            
            return str(output_path)
            
        except Exception as e:
            print(f"❌ 画像生成エラー: {str(e)}")
            self.generation_stats["total_generations"] += 1
            self.generation_stats["failed_generations"] += 1
            return None
    
    def generate_multiple_images(self, prompts, **kwargs):
        """複数画像生成"""
        results = []
        
        print(f"🎨 複数画像生成開始: {len(prompts)}枚")
        
        for i, prompt in enumerate(prompts, 1):
            print(f"\n📸 画像 {i}/{len(prompts)} 生成中...")
            result = self.generate_image(prompt, **kwargs)
            results.append(result)
        
        success_count = sum(1 for r in results if r is not None)
        print(f"\n🎉 複数画像生成完了: {success_count}/{len(prompts)} 成功")
        
        return results
    
    def get_system_status(self):
        """システム状態表示"""
        print("💻 システム状態")
        print("=" * 60)
        print(f"メモリ: {self.system_info['memory_gb']:.1f}GB (利用可能: {self.system_info['available_memory_gb']:.1f}GB)")
        print(f"CPU: {self.system_info['cpu_cores']} cores, {self.system_info['cpu_threads']} threads")
        print(f"現在のモデル: {self.current_model if self.current_model else 'なし'}")
        print(f"利用可能モデル数: {len(self.available_models)}")
        
        # 生成統計
        print(f"\n📊 生成統計:")
        print(f"   総生成数: {self.generation_stats['total_generations']}")
        print(f"   成功数: {self.generation_stats['successful_generations']}")
        print(f"   失敗数: {self.generation_stats['failed_generations']}")
        if self.generation_stats['successful_generations'] > 0:
            print(f"   平均時間: {self.generation_stats['average_time']:.1f}秒")
    
    def list_generated_images(self):
        """生成された画像一覧表示"""
        print("🖼️ 生成された画像一覧")
        print("=" * 60)
        
        image_files = list(self.output_dir.glob("*.png"))
        
        if not image_files:
            print("❌ 生成された画像がありません")
            return
        
        # 最新順でソート
        image_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        for i, image_file in enumerate(image_files, 1):
            size_mb = image_file.stat().st_size / (1024 * 1024)
            mtime = datetime.fromtimestamp(image_file.stat().st_mtime)
            print(f"{i:2d}. {image_file.name}")
            print(f"    サイズ: {size_mb:.1f}MB")
            print(f"    作成日時: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
    
    def create_web_gallery(self):
        """Webギャラリー作成"""
        print("🌐 Webギャラリー作成中...")
        
        gallery_html = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Trinity AI Image Gallery</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
        }}
        h1 {{
            text-align: center;
            color: #333;
            margin-bottom: 30px;
            font-size: 2.5em;
        }}
        .gallery {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        .image-card {{
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 10px 20px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        }}
        .image-card:hover {{
            transform: translateY(-5px);
        }}
        .image-card img {{
            width: 100%;
            height: 300px;
            object-fit: cover;
        }}
        .image-info {{
            padding: 15px;
            background: #f8f9fa;
        }}
        .image-name {{
            font-weight: bold;
            color: #333;
            margin-bottom: 5px;
        }}
        .image-details {{
            font-size: 0.9em;
            color: #666;
        }}
        .stats {{
            background: #e9ecef;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .stats h3 {{
            margin-top: 0;
            color: #333;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🎨 Trinity AI Image Gallery</h1>
        
        <div class="stats">
            <h3>📊 生成統計</h3>
            <p>総生成数: {self.generation_stats['total_generations']}</p>
            <p>成功数: {self.generation_stats['successful_generations']}</p>
            <p>失敗数: {self.generation_stats['failed_generations']}</p>
            <p>平均生成時間: {self.generation_stats['average_time']:.1f}秒</p>
        </div>
        
        <div class="gallery">
"""
        
        # 画像ファイルを追加
        image_files = list(self.output_dir.glob("*.png"))
        image_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        for image_file in image_files:
            size_mb = image_file.stat().st_size / (1024 * 1024)
            mtime = datetime.fromtimestamp(image_file.stat().st_mtime)
            
            gallery_html += f"""
            <div class="image-card">
                <img src="{image_file.name}" alt="{image_file.name}">
                <div class="image-info">
                    <div class="image-name">{image_file.name}</div>
                    <div class="image-details">
                        サイズ: {size_mb:.1f}MB<br>
                        作成日時: {mtime.strftime('%Y-%m-%d %H:%M:%S')}
                    </div>
                </div>
            </div>
"""
        
        gallery_html += """
        </div>
    </div>
</body>
</html>
"""
        
        # HTMLファイル保存
        gallery_path = self.output_dir / "gallery.html"
        with open(gallery_path, 'w', encoding='utf-8') as f:
            f.write(gallery_html)
        
        print(f"✅ Webギャラリー作成完了: {gallery_path}")
        return str(gallery_path)
    
    def run_demo(self):
        """デモ実行"""
        print("🚀 Trinity AI Ultimate Model System デモ")
        print("=" * 60)
        
        # システム状態表示
        self.get_system_status()
        
        # 動作確認済みモデル読み込み
        if not self.load_working_model():
            print("❌ モデル読み込みに失敗しました")
            return
        
        # デモ画像生成
        demo_prompts = [
            "a beautiful anime girl, high quality, detailed, masterpiece",
            "a futuristic cityscape, cyberpunk style, neon lights, high quality",
            "a cute cat sitting on a windowsill, soft lighting, detailed"
        ]
        
        print(f"\n🎨 デモ画像生成開始: {len(demo_prompts)}枚")
        
        results = self.generate_multiple_images(
            demo_prompts,
            width=512,
            height=512,
            num_inference_steps=20
        )
        
        # 生成された画像一覧
        print(f"\n🖼️ 生成された画像一覧:")
        self.list_generated_images()
        
        # Webギャラリー作成
        gallery_path = self.create_web_gallery()
        
        print(f"\n🎉 デモ完了!")
        print(f"Webギャラリー: {gallery_path}")
        print(f"画像ディレクトリ: {self.output_dir}")


def main():
    """メイン関数"""
    system = UltimateModelSystem()
    system.run_demo()


if __name__ == "__main__":
    main()


