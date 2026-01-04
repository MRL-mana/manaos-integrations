"""
画像生成統合（自動ストック機能付き）
生成された画像を自動でストック
Hugging Face統合対応
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from PIL import Image

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 画像ストック機能をインポート
try:
    from image_stock import ImageStock
    IMAGE_STOCK_AVAILABLE = True
except ImportError:
    IMAGE_STOCK_AVAILABLE = False
    logger.warning("画像ストック機能が利用できません")

# Hugging Face統合をインポート
try:
    from huggingface_integration import HuggingFaceManaOSIntegration
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False
    logger.warning("Hugging Face統合が利用できません")


class ImageGenerationIntegration:
    """画像生成統合（自動ストック機能付き・Hugging Face統合対応）"""
    
    def __init__(self, output_dir: str = "generated_images"):
        """
        初期化
        
        Args:
            output_dir: 画像出力ディレクトリ
        """
        self.stock = ImageStock() if IMAGE_STOCK_AVAILABLE else None
        self.hf_integration = HuggingFaceManaOSIntegration(output_dir=output_dir) if HF_AVAILABLE else None
    
    def generate_and_stock(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        model: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        use_hf: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        画像を生成して自動ストック
        
        Args:
            prompt: プロンプト
            negative_prompt: ネガティブプロンプト
            model: モデル名（Hugging FaceモデルID）
            parameters: 生成パラメータ
            use_hf: Hugging Face統合を使用するか
            **kwargs: その他のパラメータ
        
        Returns:
            生成結果とストック情報
        """
        # Hugging Face統合を使用
        if use_hf and self.hf_integration:
            try:
                logger.info(f"[ImageGeneration] Hugging Faceで画像生成: {prompt}")
                
                # パラメータを展開
                model_id = model or "runwayml/stable-diffusion-v1-5"
                width = parameters.get("width", 512) if parameters else kwargs.get("width", 512)
                height = parameters.get("height", 512) if parameters else kwargs.get("height", 512)
                num_inference_steps = parameters.get("num_inference_steps", 50) if parameters else kwargs.get("num_inference_steps", 50)
                guidance_scale = parameters.get("guidance_scale", 7.5) if parameters else kwargs.get("guidance_scale", 7.5)
                seed = parameters.get("seed") if parameters else kwargs.get("seed")
                
                # 画像生成（自動ストック付き）
                result = self.hf_integration.generate_image(
                    prompt=prompt,
                    negative_prompt=negative_prompt or "",
                    model_id=model_id,
                    width=width,
                    height=height,
                    num_inference_steps=num_inference_steps,
                    guidance_scale=guidance_scale,
                    seed=seed,
                    auto_stock=True
                )
                
                if result.get("success"):
                    images = result.get("images", [])
                    if images:
                        return {
                            "success": True,
                            "image_path": images[0]["path"],
                            "images": images,
                            "stock_info": images[0].get("stock_info"),
                            "model": model_id
                        }
                
                return {
                    "success": False,
                    "error": result.get("error", "画像生成に失敗しました")
                }
                
            except Exception as e:
                logger.error(f"Hugging Face画像生成エラー: {e}")
                return {
                    "success": False,
                    "error": str(e)
                }
        
        # フォールバック（既存の実装）
        logger.info(f"[ImageGeneration] 画像生成: {prompt}")
        generated_image_path = None
        
        # ストック
        if self.stock and generated_image_path:
            try:
                stock_info = self.stock.store(
                    image_path=Path(generated_image_path),
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    model=model,
                    parameters=parameters
                )
                
                return {
                    "success": True,
                    "image_path": generated_image_path,
                    "stock_info": stock_info
                }
            except Exception as e:
                logger.error(f"ストックエラー: {e}")
                return {
                    "success": True,
                    "image_path": generated_image_path,
                    "stock_info": None,
                    "error": str(e)
                }
        
        return {
            "success": False,
            "error": "画像生成機能が利用できません"
        }
    
    def search_stock(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        model: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        ストックされた画像を検索
        
        Args:
            query: 検索クエリ
            category: カテゴリ
            model: モデル名
            limit: 取得件数
        
        Returns:
            検索結果のリスト
        """
        if not self.stock:
            logger.warning("画像ストック機能が利用できません")
            return []
        
        return self.stock.search(
            query=query,
            category=category,
            model=model,
            limit=limit
        )
    
    def get_stock_statistics(self) -> Dict[str, Any]:
        """ストック統計情報を取得"""
        if not self.stock:
            return {}
        
        return self.stock.get_statistics()


# 使用例
if __name__ == "__main__":
    integration = ImageGenerationIntegration()
    
    # 画像生成とストック
    result = integration.generate_and_stock(
        prompt="a beautiful landscape",
        model="stable-diffusion-v1-5"
    )
    print(f"生成結果: {result}")
    
    # 検索
    results = integration.search_stock(query="landscape", limit=10)
    print(f"検索結果: {len(results)}件")
    
    # 統計情報
    stats = integration.get_stock_statistics()
    print(f"統計: {stats}")


















