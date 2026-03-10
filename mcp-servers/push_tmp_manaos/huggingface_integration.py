"""
Hugging Face統合サービス（ManaOS統合版）
モデル検索・ダウンロード・画像生成をManaOSに統合
"""

from manaos_logger import get_logger, get_service_logger
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

logger = get_service_logger("huggingface-integration")
# Hugging Face統合

# 親ディレクトリをパスに追加
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

# .cursorディレクトリも追加
cursor_dir = parent_dir / ".cursor"
if cursor_dir.exists() and str(cursor_dir) not in sys.path:
    sys.path.insert(0, str(cursor_dir))

try:
    from huggingface_helper import HuggingFaceHelper
    HF_AVAILABLE = True
except ImportError as e:
    HF_AVAILABLE = False
    HuggingFaceHelper = None
    logger.warning(f"HuggingFaceHelperが利用できません: {e}")

try:
    from stable_diffusion_generator import StableDiffusionGenerator
    SD_AVAILABLE = True
except ImportError:
    try:
        # .cursorディレクトリからインポート
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "stable_diffusion_generator",
            cursor_dir / "stable_diffusion_generator.py"
        )
        if spec and spec.loader:
            stable_diffusion_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(stable_diffusion_module)
            StableDiffusionGenerator = stable_diffusion_module.StableDiffusionGenerator
            SD_AVAILABLE = True
        else:
            SD_AVAILABLE = False
            StableDiffusionGenerator = None
    except Exception as e:
        SD_AVAILABLE = False
        StableDiffusionGenerator = None
        logger.warning(f"StableDiffusionGeneratorが利用できません: {e}")

if not HF_AVAILABLE:
    logger.warning("Hugging Face統合が利用できません")

# 画像ストック機能
try:
    from image_stock import ImageStock
    IMAGE_STOCK_AVAILABLE = True
except ImportError:
    IMAGE_STOCK_AVAILABLE = False
    logger.warning("画像ストック機能が利用できません")


class HuggingFaceManaOSIntegration:
    """Hugging Face統合サービス（ManaOS統合版）"""
    
    def __init__(self, output_dir: str = "generated_images"):
        """
        初期化
        
        Args:
            output_dir: 画像出力ディレクトリ
        """
        if not HF_AVAILABLE or HuggingFaceHelper is None:
            raise ImportError("Hugging Face統合が利用できません。必要なライブラリをインストールしてください。")
        
        self.helper = HuggingFaceHelper()
        self.sd_available = SD_AVAILABLE
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 画像ストック
        self.stock = ImageStock() if IMAGE_STOCK_AVAILABLE else None  # type: ignore[possibly-unbound]
        
        # モデルキャッシュ
        self.model_cache: Dict[str, Any] = {}
        self.generators: Dict[str, StableDiffusionGenerator] = {}  # type: ignore[valid-type]
        
        # モデル管理設定
        self.cache_dir = Path(os.getenv("HF_CACHE_DIR", ".hf_cache"))
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._load_model_cache()
        
        logger.info("Hugging Face統合サービスを初期化しました")
    
    def _load_model_cache(self):
        """モデルキャッシュを読み込み"""
        cache_file = self.cache_dir / "model_cache.json"
        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    self.model_cache = json.load(f)
                logger.info(f"モデルキャッシュを読み込みました: {len(self.model_cache)}件")
            except Exception as e:
                logger.warning(f"キャッシュ読み込みエラー: {e}")
    
    def _save_model_cache(self):
        """モデルキャッシュを保存"""
        cache_file = self.cache_dir / "model_cache.json"
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(self.model_cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"キャッシュ保存エラー: {e}")
    
    def update_model_cache(self, model_id: str, info: Dict[str, Any]):
        """
        モデルキャッシュを更新
        
        Args:
            model_id: モデルID
            info: モデル情報
        """
        self.model_cache[model_id] = {
            "info": info,
            "last_updated": datetime.now().isoformat()
        }
        self._save_model_cache()
    
    def get_cached_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """
        キャッシュからモデル情報を取得
        
        Args:
            model_id: モデルID
            
        Returns:
            モデル情報（キャッシュがない場合はNone）
        """
        if model_id in self.model_cache:
            return self.model_cache[model_id].get("info")
        return None
    
    def search_models(
        self,
        query: str,
        task: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        モデルを検索
        
        Args:
            query: 検索クエリ
            task: タスクタイプ（例: "text-to-image"）
            limit: 結果数
            
        Returns:
            モデル情報のリスト
        """
        try:
            results = self.helper.search_models(query, task=task, limit=limit)
            logger.info(f"モデル検索完了: {len(results)}件")
            return results
        except Exception as e:
            logger.error(f"モデル検索エラー: {e}")
            return []
    
    def get_model_info(
        self,
        model_id: str,
        use_cache: bool = True,
        force_refresh: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        モデル情報を取得（キャッシュ対応）
        
        Args:
            model_id: モデルID
            use_cache: キャッシュを使用するか
            force_refresh: 強制更新するか
            
        Returns:
            モデル情報
        """
        # キャッシュから取得
        if use_cache and not force_refresh:
            cached_info = self.get_cached_model_info(model_id)
            if cached_info:
                logger.info(f"キャッシュからモデル情報を取得: {model_id}")
                return cached_info
        
        # Hugging Face Hubから取得
        try:
            info = self.helper.get_model_info(model_id)
            if info:
                logger.info(f"モデル情報取得完了: {model_id}")
                # キャッシュを更新
                self.update_model_cache(model_id, info)
            return info
        except Exception as e:
            logger.error(f"モデル情報取得エラー: {e}")
            # エラー時はキャッシュから返す
            if use_cache:
                cached_info = self.get_cached_model_info(model_id)
                if cached_info:
                    logger.info(f"エラー時、キャッシュからモデル情報を返します: {model_id}")
                    return cached_info
            return None
    
    def download_model(
        self,
        model_id: str,
        output_dir: Optional[str] = None
    ) -> Optional[Path]:
        """
        モデルをダウンロード
        
        Args:
            model_id: モデルID
            output_dir: 出力ディレクトリ
            
        Returns:
            ダウンロード先のパス
        """
        try:
            path = self.helper.download_model(model_id, output_dir=output_dir)
            logger.info(f"モデルダウンロード完了: {model_id}")
            return path
        except Exception as e:
            logger.error(f"モデルダウンロードエラー: {e}")
            return None
    
    def get_generator(
        self,
        model_id: str,
        device: Optional[str] = None
    ):
        """
        画像生成器を取得（キャッシュ付き）
        
        Args:
            model_id: モデルID
            device: デバイス（Noneの場合は自動検出）
            
        Returns:
            StableDiffusionGeneratorインスタンス（またはNone）
        """
        if not self.sd_available or StableDiffusionGenerator is None:
            logger.error("StableDiffusionGeneratorが利用できません")
            return None
        
        cache_key = f"{model_id}_{device or 'auto'}"
        
        if cache_key in self.generators:
            logger.info(f"キャッシュから生成器を取得: {model_id}")
            return self.generators[cache_key]
        
        try:
            logger.info(f"生成器を初期化: {model_id}")
            generator = StableDiffusionGenerator(
                model_id=model_id,
                device=device
            )
            self.generators[cache_key] = generator
            logger.info(f"生成器の初期化が完了: {model_id}")
            return generator
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            logger.error(f"生成器初期化エラー: {e}")
            logger.error(f"詳細: {error_detail}")
            return None
    
    def generate_image(
        self,
        prompt: str,
        negative_prompt: str = "",
        model_id: str = "runwayml/stable-diffusion-v1-5",
        width: int = 512,
        height: int = 512,
        num_inference_steps: int = 50,
        guidance_scale: float = 7.5,
        seed: Optional[int] = None,
        auto_stock: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        画像を生成
        
        Args:
            prompt: プロンプト
            negative_prompt: ネガティブプロンプト
            model_id: モデルID
            width: 画像の幅
            height: 画像の高さ
            num_inference_steps: 推論ステップ数
            guidance_scale: ガイダンススケール
            seed: 乱数シード
            auto_stock: 自動ストックするか
            **kwargs: その他のパラメータ
            
        Returns:
            生成結果
        """
        try:
            # 生成器を取得
            generator = self.get_generator(model_id)
            if not generator:
                return {
                    "success": False,
                    "error": f"生成器の初期化に失敗しました: {model_id}"
                }
            
            # 画像生成
            logger.info(f"画像生成開始: {prompt[:50]}...")
            images = generator.generate(
                prompt=prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
                seed=seed,
                output_dir=str(self.output_dir),
                save_metadata=True
            )
            
            if not images:
                return {
                    "success": False,
                    "error": "画像の生成に失敗しました"
                }
            
            # 結果を整理
            result_images = []
            for i, image in enumerate(images):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"hf_{timestamp}_{i+1:02d}.png"
                filepath = self.output_dir / filename
                image.save(filepath)
                
                image_info = {
                    "path": str(filepath),
                    "filename": filename,
                    "index": i + 1
                }
                result_images.append(image_info)
                
                # 自動ストック
                if auto_stock and self.stock:
                    try:
                        stock_info = self.stock.store(
                            image_path=filepath,
                            prompt=prompt,
                            negative_prompt=negative_prompt,
                            model=model_id,
                            parameters={
                                "width": width,
                                "height": height,
                                "num_inference_steps": num_inference_steps,
                                "guidance_scale": guidance_scale,
                                "seed": seed
                            }
                        )
                        image_info["stock_info"] = stock_info
                    except Exception as e:
                        logger.warning(f"ストックエラー: {e}")
            
            return {
                "success": True,
                "images": result_images,
                "model_id": model_id,
                "prompt": prompt,
                "count": len(result_images)
            }
            
        except Exception as e:
            logger.error(f"画像生成エラー: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def generate_batch(
        self,
        prompts: List[str],
        model_id: str = "runwayml/stable-diffusion-v1-5",
        **kwargs
    ) -> Dict[str, Any]:
        """
        バッチ画像生成
        
        Args:
            prompts: プロンプトのリスト
            model_id: モデルID
            **kwargs: その他のパラメータ
            
        Returns:
            生成結果
        """
        results = []
        total = len(prompts)
        
        for idx, prompt in enumerate(prompts, 1):
            logger.info(f"[{idx}/{total}] 画像生成: {prompt[:50]}...")
            result = self.generate_image(
                prompt=prompt,
                model_id=model_id,
                **kwargs
            )
            results.append({
                "prompt": prompt,
                "result": result
            })
        
        return {
            "success": True,
            "results": results,
            "total": total,
            "success_count": sum(1 for r in results if r["result"].get("success"))
        }
    
    def list_popular_models(
        self,
        task: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        人気モデル一覧を取得
        
        Args:
            task: タスクタイプ
            limit: 結果数
            
        Returns:
            モデル情報のリスト
        """
        try:
            return self.helper.list_popular_models(task=task, limit=limit)
        except Exception as e:
            logger.error(f"人気モデル取得エラー: {e}")
            return []
    
    def get_recommended_models(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        推奨モデル一覧を取得
        
        Returns:
            タスク別の推奨モデル辞書
        """
        return self.helper.get_recommended_models()
    
    def cleanup(self):
        """リソースのクリーンアップ"""
        for generator in self.generators.values():
            try:
                generator.cleanup()
            except Exception:
                pass
        self.generators.clear()
        logger.info("リソースをクリーンアップしました")


# ManaOS統合用の簡易API
def create_hf_service(output_dir: str = "generated_images") -> HuggingFaceManaOSIntegration:
    """
    Hugging Face統合サービスを作成
    
    Args:
        output_dir: 画像出力ディレクトリ
        
    Returns:
        HuggingFaceManaOSIntegrationインスタンス
    """
    return HuggingFaceManaOSIntegration(output_dir=output_dir)


# 使用例
if __name__ == "__main__":
    integration = HuggingFaceManaOSIntegration()
    
    # モデル検索
    print("=" * 60)
    print("モデル検索")
    print("=" * 60)
    results = integration.search_models("stable diffusion", task="text-to-image", limit=5)
    for model in results:
        print(f"- {model['id']} ({model['downloads']:,} downloads)")
    
    # 画像生成
    print("\n" + "=" * 60)
    print("画像生成")
    print("=" * 60)
    result = integration.generate_image(
        prompt="a beautiful landscape with mountains and a lake, sunset, highly detailed, 4k",
        negative_prompt="blurry, low quality, distorted",
        width=512,
        height=512,
        num_inference_steps=30
    )
    
    if result["success"]:
        print(f"✓ {result['count']}枚の画像を生成しました")
        for img in result["images"]:
            print(f"  - {img['path']}")
    else:
        print(f"✗ エラー: {result.get('error')}")
    
    # クリーンアップ
    integration.cleanup()

