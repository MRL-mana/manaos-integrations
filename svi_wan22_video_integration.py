"""
SVI × Wan 2.2 動画生成統合モジュール
ComfyUIを使用した無限長動画生成機能
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


class SVIWan22VideoIntegration:
    """SVI × Wan 2.2動画生成統合クラス"""
    
    def __init__(self, base_url: str = "http://localhost:8188"):
        """
        初期化
        
        Args:
            base_url: ComfyUIサーバーのベースURL
        """
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.client_id = str(time.time())
        self.workflow_template_path = Path(__file__).parent / "svi_wan22_workflow_template.json"
    
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
            # 日本語文字（ひらがな、カタカナ、漢字）が含まれていない場合は英語と判断
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
            
            # conversationタスクタイプで翻訳を実行（軽量で高速）
            result = router.route(
                task_type="conversation",
                prompt=translation_prompt
            )
            
            english_prompt = result.get("response", "").strip()
            
            # 余分な説明文を削除（「英語プロンプト:」などのプレフィックスを削除）
            if ":" in english_prompt:
                # 「:」以降のテキストを取得
                parts = english_prompt.split(":", 1)
                if len(parts) > 1:
                    english_prompt = parts[1].strip()
            
            # 空の場合は元のプロンプトを返す
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
            # エラー時は元のプロンプトを返す
            return japanese_prompt
    
    def create_timestamped_prompt_json(
        self,
        prompts: Union[str, List[Dict[str, Any]]],
        video_length_seconds: int = 5
    ) -> Dict[str, Any]:
        """
        タイムスタンプ付きプロンプトJSONを作成
        
        Args:
            prompts: プロンプト（文字列またはタイムスタンプ付きリスト）
            video_length_seconds: 動画の長さ（秒）
            
        Returns:
            タイムスタンプ付きプロンプトJSON
        """
        if isinstance(prompts, str):
            # 単一プロンプトの場合、最初のフレームに設定
            return {
                "0": prompts,
                str(video_length_seconds * 8): prompts  # 8fpsを想定
            }
        elif isinstance(prompts, list):
            # タイムスタンプ付きプロンプトリスト
            result = {}
            for item in prompts:
                if isinstance(item, dict):
                    timestamp = item.get("timestamp", 0)
                    prompt = item.get("prompt", "")
                    result[str(timestamp)] = prompt
                else:
                    # 文字列の場合は順番に配置
                    result[str(len(result) * 8)] = str(item)
            return result
        else:
            return {"0": str(prompts)}
    
    def create_svi_wan22_workflow(
        self,
        start_image_path: str,
        prompt: str,
        video_length_seconds: int = 5,
        steps: int = 6,
        motion_strength: float = 1.3,
        sage_attention: bool = True,
        extend_enabled: bool = False,
        timestamped_prompts: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        SVI × Wan 2.2ワークフローを作成
        
        Args:
            start_image_path: 開始画像のパス
            prompt: プロンプト（日本語可）
            video_length_seconds: 動画の長さ（秒）
            steps: ステップ数（6-12推奨）
            motion_strength: モーション強度（1.3-1.5推奨）
            sage_attention: Sage Attentionを有効にするか
            extend_enabled: Extend機能を有効にするか
            timestamped_prompts: タイムスタンプ付きプロンプト（オプション）
            
        Returns:
            ワークフローJSON
        """
        # プロンプトを英語に翻訳
        english_prompt = self.translate_prompt_to_english(prompt)
        
        # タイムスタンプ付きプロンプトを作成
        if timestamped_prompts is None:
            timestamped_prompts = self.create_timestamped_prompt_json(
                english_prompt,
                video_length_seconds
            )
        
        # フレーム数を計算（8fpsを想定）
        num_frames = video_length_seconds * 8
        
        # ワークフローテンプレートを読み込み（存在する場合）
        workflow = {}
        if self.workflow_template_path.exists():
            try:
                with open(self.workflow_template_path, 'r', encoding='utf-8') as f:
                    workflow = json.load(f)
                logger.info("ワークフローテンプレートを読み込みました")
            except Exception as e:
                logger.warning(f"テンプレート読み込みエラー: {e}。デフォルトワークフローを使用します。")
        
        # テンプレートが存在しない場合、基本的なワークフロー構造を作成
        if not workflow:
            workflow = {
                "1": {
                    "inputs": {
                        "image": start_image_path,
                        "upload": "image"
                    },
                    "class_type": "LoadImage",
                    "_meta": {"title": "Load Start Image"}
                },
                "2": {
                    "inputs": {
                        "text": json.dumps(timestamped_prompts),
                        "clip": ["4", 0]
                    },
                    "class_type": "CLIPTextEncode",
                    "_meta": {"title": "CLIP Text Encode (Prompt)"}
                },
                "3": {
                    "inputs": {
                        "steps": steps,
                        "motion_strength": motion_strength,
                        "num_frames": num_frames,
                        "sage_attention": sage_attention,
                        "extend": extend_enabled,
                        "model": ["4", 0],
                        "image": ["1", 0],
                        "prompt": ["2", 0]
                    },
                    "class_type": "SVIWan22VideoGenerate",
                    "_meta": {"title": "SVI × Wan 2.2 Video Generation"}
                },
                "4": {
                    "inputs": {
                        "model_name": "wan2.2.safetensors"
                    },
                    "class_type": "CheckpointLoaderSimple",
                    "_meta": {"title": "Load Wan 2.2 Model"}
                },
                "5": {
                    "inputs": {
                        "filename_prefix": "SVI_Wan22",
                        "video": ["3", 0]
                    },
                    "class_type": "SaveVideo",
                    "_meta": {"title": "Save Video"}
                }
            }
        
        return workflow
    
    def generate_video(
        self,
        start_image_path: str,
        prompt: str,
        video_length_seconds: int = 5,
        steps: int = 6,
        motion_strength: float = 1.3,
        sage_attention: bool = True,
        extend_enabled: bool = False,
        timestamped_prompts: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        動画を生成
        
        Args:
            start_image_path: 開始画像のパス
            prompt: プロンプト（日本語可）
            video_length_seconds: 動画の長さ（秒）
            steps: ステップ数（6-12推奨）
            motion_strength: モーション強度（1.3-1.5推奨）
            sage_attention: Sage Attentionを有効にするか
            extend_enabled: Extend機能を有効にするか
            timestamped_prompts: タイムスタンプ付きプロンプト（オプション）
            
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
            
            workflow = self.create_svi_wan22_workflow(
                start_image_path=uploaded_image_name,  # アップロードされた画像名を使用
                prompt=prompt,
                video_length_seconds=video_length_seconds,
                steps=steps,
                motion_strength=motion_strength,
                sage_attention=sage_attention,
                extend_enabled=extend_enabled,
                timestamped_prompts=timestamped_prompts
            )
            
            payload = {
                "prompt": workflow,
                "client_id": self.client_id
            }
            
            response = self.session.post(
                f"{self.base_url}/prompt",
                json=payload,
                timeout=60
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
    
    def extend_video(
        self,
        previous_video_path: str,
        prompt: str,
        extend_seconds: int = 5,
        steps: int = 6,
        motion_strength: float = 1.3
    ) -> Optional[str]:
        """
        既存の動画を延長
        
        Args:
            previous_video_path: 前の動画のパス
            prompt: 延長部分のプロンプト
            extend_seconds: 延長する秒数
            steps: ステップ数
            motion_strength: モーション強度
            
        Returns:
            実行ID（成功時）、None（失敗時）
        """
        try:
            workflow = {
                "1": {
                    "inputs": {
                        "video": previous_video_path,
                        "upload": "video"
                    },
                    "class_type": "LoadVideo",
                    "_meta": {"title": "Load Previous Video"}
                },
                "2": {
                    "inputs": {
                        "text": prompt,
                        "clip": ["4", 0]
                    },
                    "class_type": "CLIPTextEncode",
                    "_meta": {"title": "CLIP Text Encode (Extend Prompt)"}
                },
                "3": {
                    "inputs": {
                        "steps": steps,
                        "motion_strength": motion_strength,
                        "extend_frames": extend_seconds * 8,
                        "extend": True,
                        "model": ["4", 0],
                        "video": ["1", 0],
                        "prompt": ["2", 0]
                    },
                    "class_type": "SVIWan22VideoExtend",
                    "_meta": {"title": "Extend Video"}
                },
                "4": {
                    "inputs": {
                        "model_name": "wan2.2.safetensors"
                    },
                    "class_type": "CheckpointLoaderSimple",
                    "_meta": {"title": "Load Wan 2.2 Model"}
                },
                "5": {
                    "inputs": {
                        "filename_prefix": "SVI_Wan22_Extended",
                        "video": ["3", 0]
                    },
                    "class_type": "SaveVideo",
                    "_meta": {"title": "Save Extended Video"}
                }
            }
            
            payload = {
                "prompt": workflow,
                "client_id": self.client_id
            }
            
            response = self.session.post(
                f"{self.base_url}/prompt",
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            result = response.json()
            return result.get("prompt_id")
        except Exception as e:
            logger.error(f"動画延長エラー: {e}")
            return None
    
    def create_story_video(
        self,
        start_image_path: str,
        story_prompts: List[Dict[str, Any]],
        segment_length_seconds: int = 5,
        steps: int = 6,
        motion_strength: float = 1.3
    ) -> List[Optional[str]]:
        """
        ストーリー性のある長編動画を作成
        
        Args:
            start_image_path: 開始画像のパス
            story_prompts: ストーリープロンプトのリスト
                [{"timestamp": 0, "prompt": "笑顔"}, {"timestamp": 5, "prompt": "悲しい顔"}, ...]
            segment_length_seconds: 各セグメントの長さ（秒）
            steps: ステップ数
            motion_strength: モーション強度
            
        Returns:
            実行IDのリスト
        """
        execution_ids = []
        current_image_path = start_image_path
        
        for i, story_item in enumerate(story_prompts):
            timestamp = story_item.get("timestamp", i * segment_length_seconds)
            prompt = story_item.get("prompt", "")
            
            # 各セグメントを生成
            execution_id = self.generate_video(
                start_image_path=current_image_path if i == 0 else None,
                prompt=prompt,
                video_length_seconds=segment_length_seconds,
                steps=steps,
                motion_strength=motion_strength,
                timestamped_prompts={str(timestamp): prompt}
            )
            
            execution_ids.append(execution_id)
            
            # 次のセグメントの開始画像として、前のセグメントの最後のフレームを使用
            # （実際の実装では、生成された動画から最後のフレームを抽出する必要がある）
        
        return execution_ids
    
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
    svi = SVIWan22VideoIntegration()
    
    if not svi.is_available():
        print("ComfyUIが利用できません。ComfyUIサーバーが起動しているか確認してください。")
        return
    
    print("SVI × Wan 2.2 動画生成統合テスト")
    print("=" * 50)
    
    # キュー状態を確認
    queue_status = svi.get_queue_status()
    print(f"キュー状態: {queue_status}")
    
    # サンプル動画生成
    print("\n動画生成を開始...")
    print("注意: 実際のワークフローノードがComfyUIにインストールされている必要があります。")
    
    # テスト用の開始画像パス（実際のパスに置き換える必要がある）
    test_image_path = "test_start_image.png"
    
    if Path(test_image_path).exists():
        prompt_id = svi.generate_video(
            start_image_path=test_image_path,
            prompt="a beautiful landscape, mountains, sunset, highly detailed",
            video_length_seconds=5,
            steps=6,
            motion_strength=1.3
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


