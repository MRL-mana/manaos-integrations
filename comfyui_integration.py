"""
ComfyUI統合モジュール（改善版）
Stable Diffusionワークフローエディタとの統合
ベースクラスを使用して統一モジュールを活用
"""

import requests
import json
import time
from typing import Optional, Dict, List, Any
from pathlib import Path

# ベースクラスのインポート
from base_integration import BaseIntegration


class ComfyUIIntegration(BaseIntegration):
    """ComfyUI統合クラス（改善版）"""
    
    def __init__(self, base_url: str = "http://localhost:8188"):
        """
        初期化
        
        Args:
            base_url: ComfyUIサーバーのベースURL
        """
        super().__init__("ComfyUI")
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "ManaOS-ComfyUI-Integration/1.0"
        })
        self.client_id = str(time.time())
    
    def _initialize_internal(self) -> bool:
        """
        内部初期化
        
        Returns:
            初期化成功かどうか
        """
        try:
            # 接続テスト
            timeout = self.get_timeout("api_call")
            response = self.session.get(
                f"{self.base_url}/system_stats",
                timeout=timeout
            )
            return response.status_code == 200
        except Exception as e:
            self.error_handler.handle_exception(
                e,
                context={"base_url": self.base_url, "action": "initialize"},
                user_message="ComfyUIの初期化に失敗しました"
            )
            return False
    
    def _check_availability_internal(self) -> bool:
        """
        内部の利用可能性チェック
        
        Returns:
            利用可能かどうか
        """
        try:
            timeout = self.get_timeout("api_call")
            response = self.session.get(
                f"{self.base_url}/system_stats",
                timeout=timeout
            )
            return response.status_code == 200
        except Exception as e:
            self.error_handler.handle_exception(
                e,
                context={"base_url": self.base_url, "action": "check_availability"},
                user_message="ComfyUIへの接続に失敗しました"
            )
            return False
    
    def get_queue_status(self) -> Dict[str, Any]:
        """
        キュー状態を取得
        
        Returns:
            キュー状態の辞書
        """
        try:
            timeout = self.get_timeout("api_call")
            response = self.session.get(
                f"{self.base_url}/queue",
                timeout=timeout
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            error = self.error_handler.handle_exception(
                e,
                context={"base_url": self.base_url, "action": "get_queue_status"},
                user_message="キュー状態の取得に失敗しました"
            )
            return {"error": error.user_message or error.message}
    
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
            
            timeout = self.get_timeout("workflow_execution")
            response = self.session.post(
                f"{self.base_url}/prompt",
                json=payload,
                timeout=timeout
            )
            response.raise_for_status()
            result = response.json()
            return result.get("prompt_id")
        except Exception as e:
            error = self.error_handler.handle_exception(
                e,
                context={"base_url": self.base_url, "action": "submit_workflow"},
                user_message="ワークフローの送信に失敗しました"
            )
            self.logger.error(f"ワークフロー送信エラー: {error.message}")
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
            timeout = self.get_timeout("api_call")
            response = self.session.get(
                f"{self.base_url}/history/{max_items}",
                timeout=timeout
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            error = self.error_handler.handle_exception(
                e,
                context={"base_url": self.base_url, "action": "get_history"},
                user_message="実行履歴の取得に失敗しました"
            )
            self.logger.error(f"実行履歴取得エラー: {error.message}")
            return []
    
    def generate_image(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 512,
        height: int = 512,
        model: str = "sd_xl_base_1.0.safetensors"
    ) -> Optional[str]:
        """
        画像を生成
        
        Args:
            prompt: プロンプト
            negative_prompt: ネガティブプロンプト
            width: 画像幅
            height: 画像高さ
            model: 使用するモデル
            
        Returns:
            プロンプトID（成功時）、None（失敗時）
        """
        try:
            # 簡易ワークフロー（実際の実装では完全なワークフローが必要）
            workflow = {
                "1": {
                    "inputs": {
                        "text": prompt,
                        "clip": ["4", 0]
                    },
                    "class_type": "CLIPTextEncode"
                },
                "4": {
                    "inputs": {
                        "ckpt_name": model
                    },
                    "class_type": "CheckpointLoaderSimple"
                }
            }
            
            return self.submit_workflow(workflow, prompt)
        except Exception as e:
            error = self.error_handler.handle_exception(
                e,
                context={"prompt": prompt[:50], "action": "generate_image"},
                user_message="画像生成に失敗しました"
            )
            self.logger.error(f"画像生成エラー: {error.message}")
            return None

