import os
from pathlib import Path
from typing import Dict, List
import torch
from diffusers import StableDiffusionPipeline
from diffusers import EulerDiscreteScheduler  # scheduler互換性向上
try:
    from diffusers import StableDiffusionXLPipeline  # type: ignore
except Exception:  # pragma: no cover
    StableDiffusionXLPipeline = None  # fallback if not available

MODELS_DIRS = [
    "/mnt/storage500/model_downloads",
    "/mnt/storage500/civitai_models",
]

class ModelLoadError(Exception):
    pass

class ModelManager:
    def __init__(self, device: str = "cpu"):
        self.device = device
        self.model_cache: Dict[str, object] = {}
        self.lora_cache: Dict[str, object] = {}
        self.lora_dir = "/mnt/storage500/civitai_models"

    def index_models(self) -> List[Dict[str, str]]:
        items = []
        for d in MODELS_DIRS:
            p = Path(d)
            if not p.exists():
                continue
            for f in p.glob("*.safetensors"):
                items.append({
                    "name": f.name,
                    "path": str(f),
                    "dir": d,
                })
        return items

    def _load_single_file(self, path: str):
        # 可能ならSDXLパイプラインを優先（ファイル名ヒューリスティック）
        filename = os.path.basename(path)
        name_lower = filename.lower()
        # uwazumimix、illなどもSDXL判定
        prefer_xl = (('xl' in name_lower) or ('sdxl' in name_lower) or ('1024' in name_lower) or ('uwazumimix' in name_lower)) and (StableDiffusionXLPipeline is not None)
        pipe = None
        if prefer_xl:
            try:
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"Loading as SDXL: {path}")
                # SDXLパイプラインはsafety_checker引数をサポートしていない
                pipe = StableDiffusionXLPipeline.from_single_file(
                    path,
                    torch_dtype=torch.float32,
                    load_safety_checker=False,
                    use_safetensors=True,
                    requires_safety_checker=False,
                )
                logger.info(f"SDXL loading successful: {path}")
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"SDXL loading failed, falling back to SD: {path} - {e}")
                pipe = None
        if pipe is None:
            pipe = StableDiffusionPipeline.from_single_file(
                path,
                torch_dtype=torch.float32,
                load_safety_checker=False,
                use_safetensors=True,
                safety_checker=None,
                requires_safety_checker=False,
            )
        pipe = pipe.to(self.device)
        # scheduler互換性: 問題のあるschedulerをEulerDiscreteSchedulerに変更
        if hasattr(pipe, 'scheduler') and pipe.scheduler is not None:
            try:
                # 現在のscheduler設定を取得
                scheduler_type = type(pipe.scheduler).__name__
                # DEISMultistepSchedulerなど問題のあるschedulerなら変更
                if 'Multistep' in scheduler_type or 'DEIS' in scheduler_type:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.info(f"Replacing scheduler from {scheduler_type} to EulerDiscreteScheduler")
                    pipe.scheduler = EulerDiscreteScheduler.from_config(pipe.scheduler.config)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Scheduler replacement failed: {e}")
        # メモリ効率化
        pipe.enable_attention_slicing(1)  # スライスサイズを1に設定（メモリ使用量最小）
        if hasattr(pipe, 'enable_vae_slicing'):
            pipe.enable_vae_slicing()
        if hasattr(pipe, 'enable_vae_tiling'):
            pipe.enable_vae_tiling()
        # NSFW検出を完全に無効化
        if hasattr(pipe, 'safety_checker') and pipe.safety_checker is not None:
            pipe.safety_checker = None
        if hasattr(pipe, 'feature_extractor') and pipe.feature_extractor is not None:
            pipe.feature_extractor = None
        return pipe

    def get_pipeline(self, model_name_or_path: str):
        key = model_name_or_path
        if key in self.model_cache:
            return self.model_cache[key]
        # resolve path
        if os.path.isabs(model_name_or_path) and os.path.exists(model_name_or_path):
            path = model_name_or_path
        else:
            # search by filename
            path = None
            for m in self.index_models():
                if m["name"] == model_name_or_path:
                    path = m["path"]
                    break
        if not path:
            raise ModelLoadError("model not found")
        pipe = self._load_single_file(path)
        # simple LRU (size 3)
        if len(self.model_cache) >= 3:
            self.model_cache.pop(next(iter(self.model_cache)))
        self.model_cache[key] = pipe
        return pipe

    def load_lora(self, pipe, lora_name: str, weight: float = 0.8):
        """LoRAを読み込んでパイプラインに適用"""
        try:
            # LoRAファイルを検索
            lora_path = None
            if os.path.isabs(lora_name) and os.path.exists(lora_name):
                lora_path = lora_name
            else:
                # LoRAディレクトリを検索
                lora_dir_path = Path(self.lora_dir)
                if lora_dir_path.exists():
                    # ファイル名で検索（部分一致も可）
                    for f in lora_dir_path.glob("*"):
                        if lora_name.lower() in f.name.lower() and f.suffix in ['.safetensors', '.ckpt', '.pt']:
                            lora_path = str(f)
                            break
                    # 見つからない場合は拡張子なしでも検索
                    if not lora_path:
                        for f in lora_dir_path.glob("*"):
                            if lora_name.lower() in f.name.lower():
                                lora_path = str(f)
                                break

            if not lora_path or not os.path.exists(lora_path):
                raise ModelLoadError(f"LoRA not found: {lora_name}")

            # LoRAを読み込み（diffusersのload_lora_weightsを使用）
            try:
                # ファイルパスを直接指定（.safetensors形式）
                # diffusers 0.21.0以降では weight パラメータがサポートされている
                if hasattr(pipe, 'load_lora_weights'):
                    # 直接ファイルパスを指定して読み込み
                    pipe.load_lora_weights(lora_path, weight=weight)
                else:
                    raise ModelLoadError("Pipeline does not support LoRA loading")
            except AttributeError:
                # load_lora_weightsが使えない場合（古いdiffusersなど）
                try:
                    # フォールバック: fuse_lora_weightsを使う（weightは後で調整）
                    # 一旦読み込んでから重みを調整
                    state_dict = torch.load(lora_path, map_location="cpu")
                    # 手動で適用（簡易実装）
                    raise ModelLoadError("LoRA loading requires diffusers>=0.21.0")
                except Exception as e:
                    raise ModelLoadError(f"Failed to load LoRA: {e}")
            except Exception as e:
                # その他のエラー
                raise ModelLoadError(f"Failed to load LoRA: {e}")

            return pipe
        except ModelLoadError:
            raise
        except Exception as e:
            raise ModelLoadError(f"LoRA load error: {e}")
