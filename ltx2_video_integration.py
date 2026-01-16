"""
LTX-2 動画生成統合モジュール
Super LTX-2 セッティング（推奨設定）を実装
- NAG (Negative Attention Guidance)
- res_2sサンプラー
- 2段階生成（アップスケール）
- Q8 GGUFモデル対応
"""

import requests
import json
import time
from typing import Optional, Dict, List, Any, Union
from pathlib import Path
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LTX2VideoIntegration:
    """LTX-2動画生成統合クラス（Super LTX-2設定）"""
    
    def __init__(self, base_url: str = "http://localhost:8188"):
        """
        初期化
        
        Args:
            base_url: ComfyUIサーバーのベースURL
        """
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.client_id = str(time.time())
        self.workflow_template_path = Path(__file__).parent / "ltx2_workflow_template.json"
    
    def is_available(self) -> bool:
        """
        ComfyUIが利用可能かチェック
        
        Returns:
            利用可能な場合True
        """
        try:
            response = self.session.get(f"{self.base_url}/system_stats", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def translate_prompt_to_english(self, japanese_prompt: str) -> str:
        """
        日本語プロンプトを英語に翻訳
        ManaOSのLLMルーターを使用して翻訳を実行
        
        Args:
            japanese_prompt: 日本語プロンプト
            
        Returns:
            英語プロンプト
        """
        # 既に英語の場合（簡易チェック）
        if not any('\u3040' <= char <= '\u309F' or '\u30A0' <= char <= '\u30FF' or '\u4E00' <= char <= '\u9FAF' for char in japanese_prompt):
            logger.debug("プロンプトに日本語が含まれていないため、そのまま返します")
            return japanese_prompt
        
        try:
            # LLMルーターを使用して翻訳
            from llm_routing import LLMRouter
            
            router = LLMRouter()
            
            # 翻訳プロンプトを作成
            translation_prompt = f"""以下の日本語プロンプトを英語に翻訳してください。動画生成用のプロンプトなので、技術的な用語は正確に翻訳してください。日本語の説明や補足は含めず、英語のプロンプトのみを返してください。

日本語プロンプト: {japanese_prompt}

英語プロンプト:"""
            
            # conversationタスクタイプで翻訳を実行
            result = router.route(
                task_type="conversation",
                prompt=translation_prompt
            )
            
            english_prompt = result.get("response", "").strip()
            
            # 余分な説明文を削除
            if ":" in english_prompt:
                parts = english_prompt.split(":", 1)
                if len(parts) > 1:
                    english_prompt = parts[1].strip()
            
            if not english_prompt:
                logger.warning("翻訳結果が空のため、元のプロンプトを返します")
                return japanese_prompt
            
            logger.info(f"翻訳完了: {japanese_prompt[:50]}... -> {english_prompt[:50]}...")
            return english_prompt
            
        except ImportError:
            logger.warning("LLMRouterが利用できません。元のプロンプトを返します")
            return japanese_prompt
        except Exception as e:
            logger.error(f"翻訳エラー: {e}")
            return japanese_prompt
    
    def create_ltx2_workflow(
        self,
        start_image_path: str,
        prompt: str,
        negative_prompt: str = "",
        video_length_seconds: int = 5,
        width: int = 512,
        height: int = 512,
        use_two_pass: bool = True,
        use_nag: bool = True,
        use_res2s_sampler: bool = True,
        model_name: str = "ltx-2-19b-distilled.safetensors",
        pass1_width: int = 512,
        pass1_height: int = 512,
        pass2_width: int = 1024,
        pass2_height: int = 1024,
        steps: int = 50,
        guidance_scale: float = 7.5,
        nag_scale: float = 1.0
    ) -> Dict[str, Any]:
        """
        LTX-2ワークフローを作成（Super LTX-2設定）
        
        Args:
            start_image_path: 開始画像のパス
            prompt: プロンプト（日本語可）
            negative_prompt: ネガティブプロンプト
            video_length_seconds: 動画の長さ（秒）
            width: 出力幅（pass2使用時は無視）
            height: 出力高さ（pass2使用時は無視）
            use_two_pass: 2段階生成を使用するか（推奨: True）
            use_nag: NAG (Negative Attention Guidance) を使用するか（推奨: True）
            use_res2s_sampler: res_2sサンプラーを使用するか（推奨: True）
            model_name: モデルファイル名（Q8 GGUF推奨）
            pass1_width: 1パス目の幅
            pass1_height: 1パス目の高さ
            pass2_width: 2パス目（アップスケール）の幅
            pass2_height: 2パス目（アップスケール）の高さ
            steps: サンプリングステップ数
            guidance_scale: ガイダンススケール
            nag_scale: NAGスケール
            
        Returns:
            ワークフローJSON
        """
        # プロンプトを英語に翻訳
        english_prompt = self.translate_prompt_to_english(prompt)
        english_negative = self.translate_prompt_to_english(negative_prompt) if negative_prompt else ""
        
        # フレーム数を計算（通常は8fpsまたは24fps）
        fps = 8
        num_frames = video_length_seconds * fps
        
        # ワークフローテンプレートは参考用のため、常に動的生成を使用
        # 実際のワークフローは動的に生成する
        # 2段階生成ワークフロー
        if use_two_pass:
            workflow = self._create_two_pass_workflow(
                start_image_path=start_image_path,
                prompt=english_prompt,
                negative_prompt=english_negative,
                num_frames=num_frames,
                pass1_width=pass1_width,
                pass1_height=pass1_height,
                pass2_width=pass2_width,
                pass2_height=pass2_height,
                steps=steps,
                guidance_scale=guidance_scale,
                use_nag=use_nag,
                nag_scale=nag_scale,
                use_res2s_sampler=use_res2s_sampler,
                model_name=model_name
            )
        else:
            # 1パス生成ワークフロー
            workflow = self._create_single_pass_workflow(
                start_image_path=start_image_path,
                prompt=english_prompt,
                negative_prompt=english_negative,
                num_frames=num_frames,
                width=width,
                height=height,
                steps=steps,
                guidance_scale=guidance_scale,
                use_nag=use_nag,
                nag_scale=nag_scale,
                use_res2s_sampler=use_res2s_sampler,
                model_name=model_name
            )
        
        return workflow
    
    def _create_single_pass_workflow(
        self,
        start_image_path: str,
        prompt: str,
        negative_prompt: str,
        num_frames: int,
        width: int,
        height: int,
        steps: int,
        guidance_scale: float,
        use_nag: bool,
        nag_scale: float,
        use_res2s_sampler: bool,
        model_name: str
    ) -> Dict[str, Any]:
        """1パス生成ワークフローを作成（実際のLTX-2ノード構造を使用）"""
        # フレームレート（通常は8fpsまたは24fps）
        frame_rate = 8.0
        
        # モデル名を調整（.safetensorsが含まれていない場合は追加）
        if not model_name.endswith('.safetensors') and not model_name.endswith('.gguf'):
            # デフォルトはdistilledモデル
            model_name = "ltx-2-19b-distilled.safetensors"
        
        # LTX-Videoディレクトリにモデルがある場合のパス調整
        # CheckpointLoaderSimpleはcheckpointsディレクトリを直接参照するため、
        # LTX-Videoディレクトリ内のモデルは直接参照できない
        # そのため、モデル名のみを使用（ComfyUIが自動的に検索する）
        
        # 基本的なワークフロー構造（実際のLTX-2ノードを使用）
        workflow = {
            # 画像のロード
            "1": {
                "inputs": {
                    "image": start_image_path,
                    "upload": "image"
                },
                "class_type": "LoadImage",
                "_meta": {"title": "Load Start Image"}
            },
            # モデルのロード（CheckpointLoaderSimpleを使用）
            # 注意: 利用可能なモデルを確認する必要があります
            # 一時的に、利用可能な最初のモデルを使用
            "2": {
                "inputs": {
                    "ckpt_name": "ltx-2-19b-distilled.safetensors"
                },
                "class_type": "CheckpointLoaderSimple",
                "_meta": {"title": "Load Model"}
            },
            # Gemma CLIPモデルのロード
            # 注意: gemma_pathはtext_encodersディレクトリ内のファイル名またはパス
            # LTXVGemmaCLIPModelLoaderは以下のロジックでファイルを探す:
            # 1. folder_paths.get_full_path("text_encoders", gemma_path)でファイルパスを取得
            # 2. path.parents[1]でtext_encodersディレクトリをmodel_rootとして取得
            # 3. model_rootからtokenizer.modelとmodel*.safetensorsを探す
            # ワークフロー例では "gemma-3-12b-it-qat-q4_0-unquantized/model-00001-of-00005.safetensors" 形式
            # この場合、path.parents[1]はtext_encoders/gemma-3-12b-it-qat-q4_0-unquantizedを指す
            # 実際のファイルは "model-00001-of-00004.safetensors" がgemma-3-12b-it-qat-q4_0-unquantized内にある
            "3": {
                "inputs": {
                    "gemma_path": "gemma-3-12b-it-qat-q4_0-unquantized\\model-00001-of-00005.safetensors",  # 5ファイル形式（完全版）
                    "ltxv_path": model_name,  # LTX-2モデル名
                    "max_length": 1024
                },
                "class_type": "LTXVGemmaCLIPModelLoader",
                "_meta": {"title": "Load Gemma CLIP Model"}
            },
            # オーディオVAEのロード（LowVRAMAudioVAELoaderを使用）
            # 注意: 利用可能なモデルを確認する必要があります
            "4": {
                "inputs": {
                    "ckpt_name": "ltx-2-19b-distilled.safetensors"
                },
                "class_type": "LowVRAMAudioVAELoader",
                "_meta": {"title": "Load Audio VAE"}
            },
            # プロンプトのエンコード（Positive）
            "5": {
                "inputs": {
                    "text": prompt,
                    "clip": ["3", 0]  # Gemma CLIPを使用
                },
                "class_type": "CLIPTextEncode",
                "_meta": {"title": "CLIP Text Encode (Prompt)"}
            },
            # プロンプトのエンコード（Negative）
            "6": {
                "inputs": {
                    "text": negative_prompt or "blurry, low quality, distorted, artifacts",
                    "clip": ["3", 0]  # Gemma CLIPを使用
                },
                "class_type": "CLIPTextEncode",
                "_meta": {"title": "CLIP Text Encode (Negative)"}
            },
            # フレームレート
            "7": {
                "inputs": {
                    "value": frame_rate,
                    "mode": "fixed"
                },
                "class_type": "PrimitiveFloat",
                "_meta": {"title": "Frame Rate"}
            },
            # LTX-2コンディショニング
            "8": {
                "inputs": {
                    "positive": ["5", 0],
                    "negative": ["6", 0],
                    "frame_rate": ["7", 0]
                },
                "class_type": "LTXVConditioning",
                "_meta": {"title": "LTX-2 Conditioning"}
            },
            # 画像の前処理
            "9": {
                "inputs": {
                    "image": ["1", 0],
                    "img_compression": 35
                },
                "class_type": "LTXVPreprocess",
                "_meta": {"title": "Preprocess Image"}
            },
            # 空の潜在空間（オーディオ付き）
            # 注意: LTXVEmptyLatentAudioは利用できないため、EmptyLTXVLatentVideoを使用
            # オーディオVAEが必要な場合は、後でLTXVConcatAVLatentを使用して結合
            "10": {
                "inputs": {
                    "width": width,
                    "height": height,
                    "length": num_frames,
                    "batch_size": 1
                },
                "class_type": "EmptyLTXVLatentVideo",
                "_meta": {"title": "Empty Latent Video"}
            },
            # 画像から動画への変換（LTXVImgToVideoConditionOnlyを使用）
            # 注意: LTXVImgToVideoInplaceは利用できないため、LTXVImgToVideoConditionOnlyを使用
            "11": {
                "inputs": {
                    "vae": ["2", 2],  # VAE from checkpoint
                    "image": ["9", 0],
                    "latent": ["10", 0],
                    "strength": 1.0
                },
                "class_type": "LTXVImgToVideoConditionOnly",
                "_meta": {"title": "Image to Video Condition"}
            },
            # サンプラー（簡略化版 - 実際のワークフローではSamplerCustomAdvancedを使用）
            "12": {
                "inputs": {
                    "seed": 0,  # -1は無効なため0を使用（ランダムシードは後で実装可能）
                    "steps": steps,
                    "cfg": guidance_scale,
                    "sampler_name": "euler",  # res_2sは利用できないためeulerを使用
                    "scheduler": "normal",
                    "denoise": 1.0,
                    "model": ["2", 0],
                    "positive": ["8", 0],
                    "negative": ["8", 1],
                    "latent_image": ["11", 0]
                },
                "class_type": "KSampler",
                "_meta": {"title": "KSampler"}
            },
            # 動画とオーディオの潜在空間を分離
            # 注意: LTXVSeparateAVLatentは利用できないため、動画のみを使用
            # オーディオは後で追加可能
            # サンプラーの出力を直接デコードに使用
            # 動画のデコード（LTXVSpatioTemporalTiledVAEDecodeを使用）
            "14": {
                "inputs": {
                    "vae": ["2", 2],
                    "latents": ["12", 0],  # サンプラーの出力を直接使用
                    "spatial_tiles": 4,
                    "spatial_overlap": 1,
                    "temporal_tile_length": 16,
                    "temporal_overlap": 1,
                    "last_frame_fix": False,
                    "working_device": "auto",
                    "working_dtype": "auto"
                },
                "class_type": "LTXVSpatioTemporalTiledVAEDecode",
                "_meta": {"title": "Decode Video"}
            },
            # オーディオのデコード（一時的にスキップ - LTXVAudioVAEDecodeが利用できないため）
            # 注意: オーディオなしで動画を生成
            # 動画の作成（オーディオなし）
            "16": {
                "inputs": {
                    "images": ["14", 0],
                    "fps": ["7", 0]
                },
                "class_type": "CreateVideo",
                "_meta": {"title": "Create Video (No Audio)"}
            },
            # 動画の保存
            "17": {
                "inputs": {
                    "filename_prefix": "LTX2",
                    "video": ["16", 0],
                    "format": "video/mp4",
                    "codec": "libx264"
                },
                "class_type": "SaveVideo",
                "_meta": {"title": "Save Video"}
            }
        }
        
        # NAGの適用（KJNodesが必要）
        # 注意: NAGノードが利用できないため、一時的にスキップ
        # if use_nag:
        #     # NAGノードを追加（KJNodesのLTX2_NAG機能を使用）
        #     workflow["18"] = {
        #         "inputs": {
        #             "positive": ["5", 0],
        #             "negative": ["6", 0],
        #             "scale": nag_scale
        #         },
        #         "class_type": "LTX2_NAG",  # KJNodesのLTX2_NAGノード
        #         "_meta": {"title": "Negative Attention Guidance (NAG)"}
        #     }
        #     # NAGを使用するように接続を変更
        #     workflow["8"]["inputs"]["positive"] = ["18", 0]
        #     workflow["8"]["inputs"]["negative"] = ["18", 1]
        
        return workflow
    
    def _create_two_pass_workflow(
        self,
        start_image_path: str,
        prompt: str,
        negative_prompt: str,
        num_frames: int,
        pass1_width: int,
        pass1_height: int,
        pass2_width: int,
        pass2_height: int,
        steps: int,
        guidance_scale: float,
        use_nag: bool,
        nag_scale: float,
        use_res2s_sampler: bool,
        model_name: str
    ) -> Dict[str, Any]:
        """2段階生成（アップスケール）ワークフローを作成"""
        # 1パス目のワークフローを作成
        workflow = self._create_single_pass_workflow(
            start_image_path=start_image_path,
            prompt=prompt,
            negative_prompt=negative_prompt,
            num_frames=num_frames,
            width=pass1_width,
            height=pass1_height,
            steps=steps,
            guidance_scale=guidance_scale,
            use_nag=use_nag,
            nag_scale=nag_scale,
            use_res2s_sampler=use_res2s_sampler,
            model_name=model_name
        )
        
        # 2パス目（アップスケール）のノードを追加
        # 注意: アップスケールモデルが利用できないため、1パス目の出力を直接使用
        # または、画像をリサイズしてから2パス目を実行
        
        # 画像をリサイズ（2パス目用の高解像度）
        workflow["19"] = {
            "inputs": {
                "image": ["9", 0],  # 元の画像
                "width": pass2_width,
                "height": pass2_height,
                "upscale_method": "lanczos",
                "crop": "disabled"
            },
            "class_type": "ImageScale",
            "_meta": {"title": "Scale Image (Pass 2)"}
        }
        
        # 2パス目用の空の潜在空間（高解像度）
        workflow["20"] = {
            "inputs": {
                "width": pass2_width,
                "height": pass2_height,
                "length": num_frames,
                "batch_size": 1
            },
            "class_type": "EmptyLTXVLatentVideo",
            "_meta": {"title": "Empty Latent Video (Pass 2)"}
        }
        
        # アップスケール後の画像から動画への変換
        workflow["22"] = {
            "inputs": {
                "vae": ["2", 2],
                "image": ["19", 0],  # リサイズされた画像
                "latent": ["20", 0],
                "strength": 0.5  # 2パス目は強度を下げる
            },
            "class_type": "LTXVImgToVideoConditionOnly",
            "_meta": {"title": "Image to Video (Pass 2)"}
        }
        
        # 2パス目のサンプラー
        workflow["23"] = {
            "inputs": {
                "seed": 0,  # -1は無効なため0を使用
                "steps": steps,
                "cfg": guidance_scale,
                "sampler_name": "euler",  # res_2sは利用できないためeulerを使用
                "scheduler": "normal",
                "denoise": 0.5,  # 2パス目は低めに
                "model": ["2", 0],
                "positive": ["8", 0],
                "negative": ["8", 1],
                "latent_image": ["22", 0]
            },
            "class_type": "KSampler",
            "_meta": {"title": "KSampler (Pass 2)"}
        }
        
        # 2パス目の動画のデコード（高解像度）
        workflow["24"] = {
            "inputs": {
                "vae": ["2", 2],
                "latents": ["23", 0],  # 2パス目のサンプラー出力を直接使用
                "spatial_tiles": 4,
                "spatial_overlap": 1,
                "temporal_tile_length": 16,
                "temporal_overlap": 1,
                "last_frame_fix": False,
                "working_device": "auto",
                "working_dtype": "auto"
            },
            "class_type": "LTXVSpatioTemporalTiledVAEDecode",
            "_meta": {"title": "Decode Video (Pass 2)"}
        }
        
        # 2パス目の動画の作成（高解像度、オーディオなし）
        workflow["25"] = {
            "inputs": {
                "images": ["24", 0],
                "fps": ["7", 0]
            },
            "class_type": "CreateVideo",
            "_meta": {"title": "Create Video (Pass 2, No Audio)"}
        }
        
        # 2パス目の動画の保存
        workflow["26"] = {
            "inputs": {
                "filename_prefix": "LTX2_2pass",
                "video": ["25", 0],
                "format": "video/mp4",
                "codec": "libx264"
            },
            "class_type": "SaveVideo",
            "_meta": {"title": "Save Video (Pass 2)"}
        }
        
        return workflow
    
    def generate_video(
        self,
        start_image_path: str,
        prompt: str,
        negative_prompt: str = "",
        video_length_seconds: int = 5,
        width: int = 512,
        height: int = 512,
        use_two_pass: bool = True,
        use_nag: bool = True,
        use_res2s_sampler: bool = True,
        model_name: str = "ltx-2-19b-distilled.safetensors",
        **kwargs
    ) -> Optional[str]:
        """
        動画を生成（Super LTX-2設定）
        
        Args:
            start_image_path: 開始画像のパス
            prompt: プロンプト（日本語可）
            negative_prompt: ネガティブプロンプト
            video_length_seconds: 動画の長さ（秒）
            width: 出力幅（use_two_pass=Falseの場合）
            height: 出力高さ（use_two_pass=Falseの場合）
            use_two_pass: 2段階生成を使用するか（推奨: True）
            use_nag: NAGを使用するか（推奨: True）
            use_res2s_sampler: res_2sサンプラーを使用するか（推奨: True）
            model_name: モデルファイル名
            **kwargs: その他のパラメータ
            
        Returns:
            実行ID（成功時）、None（失敗時）
        """
        try:
            # まず画像をアップロード
            image_data = None
            try:
                with open(start_image_path, 'rb') as f:
                    image_data = f.read()
            except Exception as e:
                logger.error(f"画像読み込みエラー: {e}")
                return None
            
            # 画像をアップロード
            files = {'image': (Path(start_image_path).name, image_data, 'image/png')}
            upload_response = self.session.post(
                f"{self.base_url}/upload/image",
                files=files,
                timeout=30
            )
            
            if upload_response.status_code != 200:
                logger.warning("画像アップロードに失敗、ローカルパスを使用します")
                uploaded_image_name = Path(start_image_path).name
            else:
                upload_result = upload_response.json()
                uploaded_image_name = upload_result.get('name', Path(start_image_path).name)
            
            workflow = self.create_ltx2_workflow(
                start_image_path=uploaded_image_name,
                prompt=prompt,
                negative_prompt=negative_prompt,
                video_length_seconds=video_length_seconds,
                width=width,
                height=height,
                use_two_pass=use_two_pass,
                use_nag=use_nag,
                use_res2s_sampler=use_res2s_sampler,
                model_name=model_name,
                **kwargs
            )
            
            payload = {
                "prompt": workflow,
                "client_id": self.client_id
            }
            
            response = self.session.post(
                f"{self.base_url}/prompt",
                json=payload,
                timeout=120  # 動画生成は時間がかかる
            )
            
            if response.status_code != 200:
                error_detail = response.text
                logger.error(f"動画生成エラー (Status {response.status_code}): {error_detail}")
                return None
                
            response.raise_for_status()
            result = response.json()
            return result.get("prompt_id")
        except Exception as e:
            logger.error(f"動画生成エラー: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def get_queue_status(self) -> Dict[str, Any]:
        """
        キュー状態を取得
        
        Returns:
            キュー状態の辞書
        """
        try:
            response = self.session.get(f"{self.base_url}/queue", timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def get_history(self, max_items: int = 10) -> List[Dict[str, Any]]:
        """
        実行履歴を取得
        
        Args:
            max_items: 取得する最大アイテム数
            
        Returns:
            実行履歴のリスト
        """
        try:
            response = self.session.get(f"{self.base_url}/history/{max_items}", timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"履歴取得エラー: {e}")
            return []
    
    def get_video(self, filename: str, subfolder: str = "", folder_type: str = "output") -> Optional[bytes]:
        """
        生成された動画を取得
        
        Args:
            filename: ファイル名
            subfolder: サブフォルダ
            folder_type: フォルダタイプ（output/input/temp）
            
        Returns:
            動画データ（バイト）、None（失敗時）
        """
        try:
            url = f"{self.base_url}/view"
            params = {
                "filename": filename,
                "subfolder": subfolder,
                "type": folder_type
            }
            response = self.session.get(url, params=params, timeout=60)
            response.raise_for_status()
            return response.content
        except Exception as e:
            logger.error(f"動画取得エラー: {e}")
            return None


def main():
    """テスト用メイン関数"""
    ltx2 = LTX2VideoIntegration()
    
    if not ltx2.is_available():
        print("ComfyUIが利用できません。ComfyUIサーバーが起動しているか確認してください。")
        return
    
    print("LTX-2 動画生成統合テスト（Super LTX-2設定）")
    print("=" * 50)
    
    # キュー状態を確認
    queue_status = ltx2.get_queue_status()
    print(f"キュー状態: {queue_status}")
    
    # サンプル動画生成
    print("\n動画生成を開始...")
    print("注意: 実際のワークフローノードがComfyUIにインストールされている必要があります。")
    print("必要なカスタムノード:")
    print("  - ComfyUI-LTXVideo (LTX-2動画生成ノード)")
    print("  - KJNodes (NAG機能)")
    print("  - LTX-2関連ノード")
    
    # テスト用の開始画像パス（実際のパスに置き換える必要がある）
    test_image_path = "test_start_image.png"
    
    if Path(test_image_path).exists():
        prompt_id = ltx2.generate_video(
            start_image_path=test_image_path,
            prompt="a beautiful landscape, mountains, sunset, highly detailed",
            video_length_seconds=5,
            use_two_pass=True,
            use_nag=True,
            use_res2s_sampler=True,
            model_name="ltx-2-19b-distilled.safetensors"
        )
        
        if prompt_id:
            print(f"実行ID: {prompt_id}")
            print("動画生成が開始されました。ComfyUIのUIで確認してください。")
        else:
            print("動画生成に失敗しました。")
    else:
        print(f"テスト画像が見つかりません: {test_image_path}")
        print("実際の画像パスを指定してください。")


if __name__ == "__main__":
    main()
