#!/usr/bin/env python3
"""
ManaOS Training Client
LoRA学習・モデル管理を実行
"""

import base64
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional


class ManaOSTrainingClient:
    """学習クライアント"""

    def __init__(self):
        self.modal_service_path = "/root/runpod_integration/modal_lora_training.py"

    def check_modal_auth(self) -> bool:
        """Modal認証確認"""
        from pathlib import Path
        modal_config = Path.home() / ".modal.toml"
        return modal_config.exists()

    def train_lora(
        self,
        image_paths: List[str],
        trigger_word: str,
        output_name: str,
        steps: int = 1000,
        learning_rate: float = 1e-4,
        batch_size: int = 1,
        resolution: int = 512
    ) -> Dict[str, Any]:
        """
        LoRAモデルを学習

        Args:
            image_paths: 学習用画像のパスのリスト
            trigger_word: トリガーワード
            output_name: 出力モデル名
            steps: 学習ステップ数
            learning_rate: 学習率
            batch_size: バッチサイズ
            resolution: 画像解像度

        Returns:
            結果辞書
        """
        if not self.check_modal_auth():
            return {
                "success": False,
                "error": "Modal認証が必要です"
            }

        # 画像をBase64エンコード
        images_base64 = []
        for img_path in image_paths:
            img_path_obj = Path(img_path)
            if not img_path_obj.exists():
                continue

            with open(img_path_obj, 'rb') as f:
                img_bytes = f.read()
            images_base64.append(base64.b64encode(img_bytes).decode())

        if not images_base64:
            return {
                "success": False,
                "error": "有効な画像が見つかりません"
            }

        try:
            # Modal関数を直接呼び出す
            import modal
            app = modal.App.lookup("manaos-lora-training", create_if_missing=False)

            with app.run():
                result_data = app.train_lora.remote(
                    images_base64=images_base64,
                    trigger_word=trigger_word,
                    output_name=output_name,
                    steps=steps,
                    learning_rate=learning_rate,
                    batch_size=batch_size,
                    resolution=resolution
                )

            return result_data

        except Exception as e:
            return {
                "success": False,
                "error": f"Modal実行エラー: {e}"
            }

    def list_trained_models(self) -> Dict[str, Any]:
        """学習済みモデル一覧を取得"""
        if not self.check_modal_auth():
            return {
                "success": False,
                "error": "Modal認証が必要です"
            }

        try:
            import modal
            app = modal.App.lookup("manaos-lora-training", create_if_missing=False)

            with app.run():
                result_data = app.list_trained_models.remote()

            return result_data

        except Exception as e:
            return {
                "success": False,
                "error": f"Modal実行エラー: {e}"
            }

    def generate_with_lora(
        self,
        prompt: str,
        lora_model_name: str,
        output_path: Optional[str] = None,
        steps: int = 30,
        guidance_scale: float = 7.5
    ) -> Dict[str, Any]:
        """
        学習済みLoRAモデルを使用して画像生成

        Args:
            prompt: プロンプト（トリガーワードを含む）
            lora_model_name: 使用するLoRAモデル名
            output_path: 出力先パス
            steps: 生成ステップ数
            guidance_scale: ガイダンススケール

        Returns:
            結果辞書
        """
        if not self.check_modal_auth():
            return {
                "success": False,
                "error": "Modal認証が必要です"
            }

        try:
            import modal
            app = modal.App.lookup("manaos-lora-training", create_if_missing=False)

            with app.run():
                result_data = app.generate_with_lora.remote(
                    prompt=prompt,
                    lora_model_name=lora_model_name,
                    steps=steps,
                    guidance_scale=guidance_scale
                )

            if result_data.get('success'):
                # 出力パスを決定
                if not output_path:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    output_path = f"/root/generated_images/lora_{timestamp}.png"

                Path(output_path).parent.mkdir(parents=True, exist_ok=True)

                # Base64から画像を復元
                image_bytes = base64.b64decode(result_data['image_base64'])
                with open(output_path, 'wb') as f:
                    f.write(image_bytes)

                return {
                    "success": True,
                    "path": output_path,
                    "prompt": prompt,
                    "lora_model": lora_model_name
                }
            else:
                return result_data

        except Exception as e:
            return {
                "success": False,
                "error": f"Modal実行エラー: {e}"
            }


if __name__ == "__main__":
    # テスト
    client = ManaOSTrainingClient()

    # 学習済みモデル一覧を取得
    print("📚 学習済みモデル一覧:")
    result = client.list_trained_models()
    if result.get('success'):
        models = result.get('models', [])
        if models:
            for model in models:
                print(f"  - {model['name']}")
        else:
            print("  （モデルなし）")
    else:
        print(f"❌ エラー: {result.get('error')}")








