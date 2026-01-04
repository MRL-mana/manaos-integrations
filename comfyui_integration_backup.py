"""
ComfyUI統合モジュール
Stable Diffusionワークフローエディタとの統合
"""

import requests
import json
import time
from typing import Optional, Dict, List, Any
from pathlib import Path


class ComfyUIIntegration:
    """ComfyUI統合クラス"""
    
    def __init__(self, base_url: str = "http://localhost:8188"):
        """
        初期化
        
        Args:
            base_url: ComfyUIサーバーのベースURL
        """
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.client_id = str(time.time())
    
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
    
    def submit_workflow(self, workflow: Dict[str, Any], prompt: str = "") -> Optional[str]:
        """
        ワークフローを送信
        
        Args:
            workflow: ComfyUIワークフローJSON
            prompt: プロンプト（オプション）
            
        Returns:
            実行ID（成功時）、None（失敗時）
        """
        try:
            payload = {
                "prompt": workflow,
                "client_id": self.client_id
            }
            
            if prompt:
                payload["extra_data"] = {"extra_pnginfo": {"prompt": prompt}}
            
            response = self.session.post(
                f"{self.base_url}/prompt",
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            return result.get("prompt_id")
        except Exception as e:
            print(f"ワークフロー送信エラー: {e}")
            return None
    
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
            print(f"履歴取得エラー: {e}")
            return []
    
    def get_image(self, filename: str, subfolder: str = "", folder_type: str = "output") -> Optional[bytes]:
        """
        生成された画像を取得
        
        Args:
            filename: ファイル名
            subfolder: サブフォルダ
            folder_type: フォルダタイプ（output/input/temp）
            
        Returns:
            画像データ（バイト）、None（失敗時）
        """
        try:
            url = f"{self.base_url}/view"
            params = {
                "filename": filename,
                "subfolder": subfolder,
                "type": folder_type
            }
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.content
        except Exception as e:
            print(f"画像取得エラー: {e}")
            return None
    
    def create_simple_workflow(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 512,
        height: int = 512,
        steps: int = 20,
        cfg_scale: float = 7.0,
        seed: int = -1
    ) -> Dict[str, Any]:
        """
        シンプルなワークフローを作成
        
        Args:
            prompt: プロンプト
            negative_prompt: ネガティブプロンプト
            width: 画像幅
            height: 画像高さ
            steps: ステップ数
            cfg_scale: CFGスケール
            seed: シード（-1でランダム）
            
        Returns:
            ワークフローJSON
        """
        # シンプルなComfyUIワークフロー構造
        workflow = {
            "1": {
                "inputs": {
                    "text": prompt,
                    "clip": ["4", 0]
                },
                "class_type": "CLIPTextEncode",
                "_meta": {"title": "CLIP Text Encode (Prompt)"}
            },
            "2": {
                "inputs": {
                    "text": negative_prompt or "blurry, low quality, distorted",
                    "clip": ["4", 0]
                },
                "class_type": "CLIPTextEncode",
                "_meta": {"title": "CLIP Text Encode (Negative)"}
            },
            "3": {
                "inputs": {
                    "seed": seed,
                    "steps": steps,
                    "cfg": cfg_scale,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "denoise": 1.0,
                    "model": ["4", 0],
                    "positive": ["1", 0],
                    "negative": ["2", 0],
                    "latent_image": ["5", 0]
                },
                "class_type": "KSampler",
                "_meta": {"title": "KSampler"}
            },
            "4": {
                "inputs": {
                    "ckpt_name": "v1-5-pruned-emaonly.safetensors"
                },
                "class_type": "CheckpointLoaderSimple",
                "_meta": {"title": "Load Checkpoint"}
            },
            "5": {
                "inputs": {
                    "width": width,
                    "height": height,
                    "batch_size": 1
                },
                "class_type": "EmptyLatentImage",
                "_meta": {"title": "Empty Latent Image"}
            },
            "6": {
                "inputs": {
                    "samples": ["3", 0],
                    "vae": ["4", 2]
                },
                "class_type": "VAEDecode",
                "_meta": {"title": "VAE Decode"}
            },
            "7": {
                "inputs": {
                    "filename_prefix": "ComfyUI",
                    "images": ["6", 0]
                },
                "class_type": "SaveImage",
                "_meta": {"title": "Save Image"}
            }
        }
        
        return workflow
    
    def generate_image(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 512,
        height: int = 512,
        steps: int = 20,
        cfg_scale: float = 7.0,
        seed: int = -1
    ) -> Optional[str]:
        """
        画像を生成
        
        Args:
            prompt: プロンプト
            negative_prompt: ネガティブプロンプト
            width: 画像幅
            height: 画像高さ
            steps: ステップ数
            cfg_scale: CFGスケール
            seed: シード
            
        Returns:
            実行ID（成功時）、None（失敗時）
        """
        workflow = self.create_simple_workflow(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            steps=steps,
            cfg_scale=cfg_scale,
            seed=seed
        )
        
        return self.submit_workflow(workflow, prompt)


def main():
    """テスト用メイン関数"""
    comfyui = ComfyUIIntegration()
    
    if not comfyui.is_available():
        print("ComfyUIが利用できません。ComfyUIサーバーが起動しているか確認してください。")
        return
    
    print("ComfyUI統合テスト")
    print("=" * 50)
    
    # キュー状態を確認
    queue_status = comfyui.get_queue_status()
    print(f"キュー状態: {queue_status}")
    
    # シンプルな画像生成
    print("\n画像生成を開始...")
    prompt_id = comfyui.generate_image(
        prompt="a beautiful landscape, mountains, sunset, highly detailed",
        width=512,
        height=512,
        steps=20
    )
    
    if prompt_id:
        print(f"実行ID: {prompt_id}")
        print("画像生成が開始されました。ComfyUIのUIで確認してください。")
    else:
        print("画像生成に失敗しました。")


if __name__ == "__main__":
    main()





















