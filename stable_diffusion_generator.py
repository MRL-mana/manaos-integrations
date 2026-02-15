"""
Stable Diffusion画像生成器
diffusersライブラリを使用した画像生成
"""

from manaos_logger import get_logger, get_service_logger
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import torch
from PIL import Image

logger = get_service_logger("stable-diffusion-generator")
try:
    from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
    from diffusers.utils import export_to_gif
    DIFFUSERS_AVAILABLE = True
except ImportError:
    DIFFUSERS_AVAILABLE = False
    logger.warning("diffusersライブラリが利用できません。pip install diffusers を実行してください。")


class StableDiffusionGenerator:
    """Stable Diffusion画像生成器"""
    
    def __init__(
        self,
        model_id: str = "runwayml/stable-diffusion-v1-5",
        device: Optional[str] = None,
        torch_dtype: Optional[torch.dtype] = None
    ):
        """
        初期化
        
        Args:
            model_id: Hugging FaceモデルID
            device: デバイス（Noneの場合は自動検出）
            torch_dtype: データ型（Noneの場合は自動選択）
        """
        if not DIFFUSERS_AVAILABLE:
            raise ImportError("diffusersライブラリが必要です。pip install diffusers を実行してください。")
        
        self.model_id = model_id
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        
        # データ型の自動選択
        if torch_dtype is None:
            if self.device == "cuda":
                # CUDAの場合はfloat16を使用（メモリ節約）
                self.torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
            else:
                self.torch_dtype = torch.float32
        else:
            self.torch_dtype = torch_dtype
        
        logger.info(f"StableDiffusionGeneratorを初期化: {model_id} on {self.device}")
        
        # パイプラインをロード
        try:
            logger.info(f"パイプラインをロード中: {model_id}...")
            self.pipeline = StableDiffusionPipeline.from_pretrained(
                model_id,
                torch_dtype=self.torch_dtype,
                safety_checker=None,  # セーフティチェッカーを無効化（オプション）
                requires_safety_checker=False
            )
            logger.info("パイプラインをデバイスに移動中...")
            self.pipeline = self.pipeline.to(self.device)
            
            # スケジューラーを設定（高速化）
            logger.info("スケジューラーを設定中...")
            self.pipeline.scheduler = DPMSolverMultistepScheduler.from_config(
                self.pipeline.scheduler.config
            )
            
            # メモリ最適化
            if self.device == "cuda":
                logger.info("CUDAメモリ最適化を有効化...")
                self.pipeline.enable_attention_slicing()
                self.pipeline.enable_vae_slicing()
            
            logger.info(f"パイプラインのロード完了: {model_id}")
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            logger.error(f"パイプラインのロードエラー: {e}")
            logger.error(f"詳細: {error_detail}")
            raise RuntimeError(f"パイプラインのロードに失敗しました: {e}") from e
    
    def generate(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 512,
        height: int = 512,
        num_inference_steps: int = 50,
        guidance_scale: float = 7.5,
        seed: Optional[int] = None,
        num_images: int = 1,
        output_dir: Optional[str] = None,
        save_metadata: bool = True
    ) -> List[Image.Image]:
        """
        画像を生成
        
        Args:
            prompt: プロンプト
            negative_prompt: ネガティブプロンプト
            width: 画像の幅
            height: 画像の高さ
            num_inference_steps: 推論ステップ数
            guidance_scale: ガイダンススケール
            seed: 乱数シード
            num_images: 生成する画像数
            output_dir: 出力ディレクトリ（Noneの場合は保存しない）
            save_metadata: メタデータを保存するか
        
        Returns:
            生成された画像のリスト
        """
        try:
            # シードを設定
            generator = None
            if seed is not None:
                generator = torch.Generator(device=self.device)
                generator.manual_seed(seed)
            
            logger.info(f"画像生成開始: {prompt[:50]}...")
            
            # 画像生成
            with torch.autocast(self.device):
                images = self.pipeline(
                    prompt=prompt,
                    negative_prompt=negative_prompt if negative_prompt else None,
                    width=width,
                    height=height,
                    num_inference_steps=num_inference_steps,
                    guidance_scale=guidance_scale,
                    generator=generator,
                    num_images_per_prompt=num_images
                ).images
            
            logger.info(f"画像生成完了: {len(images)}枚")
            
            # 保存
            if output_dir:
                output_path = Path(output_dir)
                output_path.mkdir(parents=True, exist_ok=True)
                
                for i, image in enumerate(images):
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"sd_{timestamp}_{i+1:02d}.png"
                    filepath = output_path / filename
                    image.save(filepath)
                    
                    # メタデータを保存
                    if save_metadata:
                        metadata_file = output_path / f"{filename}.json"
                        metadata = {
                            "prompt": prompt,
                            "negative_prompt": negative_prompt,
                            "width": width,
                            "height": height,
                            "num_inference_steps": num_inference_steps,
                            "guidance_scale": guidance_scale,
                            "seed": seed,
                            "model_id": self.model_id,
                            "generated_at": datetime.now().isoformat()
                        }
                        import json
                        with open(metadata_file, "w", encoding="utf-8") as f:
                            json.dump(metadata, f, ensure_ascii=False, indent=2)
                    
                    logger.info(f"画像を保存: {filepath}")
            
            return images
            
        except Exception as e:
            logger.error(f"画像生成エラー: {e}")
            raise
    
    def unload(self):
        """モデルをアンロード（メモリ解放）"""
        if hasattr(self, 'pipeline'):
            del self.pipeline
            if self.device == "cuda":
                torch.cuda.empty_cache()
            logger.info("モデルをアンロードしました")


# 使用例
if __name__ == "__main__":
    generator = StableDiffusionGenerator()
    
    images = generator.generate(
        prompt="a beautiful landscape, mountains, sunset",
        num_inference_steps=20,
        output_dir="generated_images"
    )
    
    print(f"生成された画像数: {len(images)}")
