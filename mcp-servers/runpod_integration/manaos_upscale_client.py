#!/usr/bin/env python3
"""
ManaOS Image Upscale Client
Modal.com/RunPod Serverlessで画像超解像を実行
"""

import subprocess
import json
import base64
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional


class ManaOSUpscaleClient:
    """画像超解像クライアント"""

    def __init__(self):
        self.modal_service_path = "/root/runpod_integration/modal_image_upscale.py"

    def check_modal_auth(self) -> bool:
        """Modal認証確認"""
        try:
            result = subprocess.run(
                ["modal", "token", "show"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except subprocess.SubprocessError:
            # ~/.modal.toml を直接確認
            modal_config = Path.home() / ".modal.toml"
            if modal_config.exists():
                return True
            return False

    def upscale_image(
        self,
        image_path: str,
        output_path: Optional[str] = None,
        scale: int = 4,
        method: str = "realesrgan"  # "realesrgan" or "simple"
    ) -> Dict[str, Any]:
        """
        画像を超解像

        Args:
            image_path: 元画像のパス
            output_path: 出力先パス（Noneの場合は自動生成）
            scale: 拡大倍率（2, 4など）
            method: 使用手法（"realesrgan" or "simple"）

        Returns:
            結果辞書
        """
        if not self.check_modal_auth():
            return {
                "success": False,
                "error": "Modal認証が必要です。`modal token set` を実行してください。"
            }

        image_path_obj = Path(image_path)
        if not image_path_obj.exists():
            return {
                "success": False,
                "error": f"画像ファイルが見つかりません: {image_path}"
            }

        try:
            # 画像をBase64エンコード
            with open(image_path_obj, 'rb') as f:
                image_bytes = f.read()

            image_base64 = base64.b64encode(image_bytes).decode()

            # Modal関数を実行
            if method == "realesrgan":
                function_name = "upscale_image"
            else:
                function_name = "simple_upscale"

            # 一時ファイルにBase64を保存
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump({
                    "image_base64": image_base64,
                    "scale": scale
                }, f)
                temp_json_path = f.name

            # Modal関数を実行（subprocess経由）
            # Modalの引数はJSON形式で渡す必要がある
            import tempfile
            import json

            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump({
                    "image_base64": image_base64,
                    "scale": scale
                }, f)
                temp_json_path = f.name

            # Modal関数を直接呼び出す（Python SDK使用）
            try:
                import modal
                app = modal.App.lookup("manaos-image-upscale", create_if_missing=False)

                with app.run():
                    if method == "realesrgan":
                        result_data = app.upscale_image.remote(
                            image_base64=image_base64,
                            scale=scale
                        )
                    else:
                        result_data = app.simple_upscale.remote(
                            image_base64=image_base64,
                            scale=scale
                        )

                # 一時ファイル削除
                Path(temp_json_path).unlink(missing_ok=True)

                if result_data.get('success'):
                    # 出力パスを決定
                    if not output_path:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        output_path = f"/root/generated_images/upscaled_{timestamp}.png"

                    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

                    # Base64から画像を復元
                    upscaled_bytes = base64.b64decode(result_data['image_base64'])
                    with open(output_path, 'wb') as f:
                        f.write(upscaled_bytes)

                    return {
                        "success": True,
                        "path": output_path,
                        "original_size": result_data.get('original_size'),
                        "upscaled_size": result_data.get('upscaled_size'),
                        "scale": result_data.get('scale')
                    }
                else:
                    return {
                        "success": False,
                        "error": result_data.get('error', 'Unknown error')
                    }

            except Exception:
                # フォールバック: subprocess経由
                cmd = [
                    "modal", "run",
                    f"{self.modal_service_path}::{function_name}",
                    "--image-base64", image_base64,
                    "--scale", str(scale)
                ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600
            )

            # 一時ファイル削除
            Path(temp_json_path).unlink(missing_ok=True)

            if result.returncode == 0:
                # 出力からJSONを抽出
                import re
                json_match = re.search(r'\{[^{}]*"image_base64"[^{}]*\}', result.stdout, re.DOTALL)

                if json_match:
                    try:
                        data = json.loads(json_match.group())

                        if data.get('success'):
                            # 出力パスを決定
                            if not output_path:
                                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                output_path = f"/root/generated_images/upscaled_{timestamp}.png"

                            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

                            # Base64から画像を復元
                            upscaled_bytes = base64.b64decode(data['image_base64'])
                            with open(output_path, 'wb') as f:
                                f.write(upscaled_bytes)

                            return {
                                "success": True,
                                "path": output_path,
                                "original_size": data.get('original_size'),
                                "upscaled_size": data.get('upscaled_size'),
                                "scale": data.get('scale')
                            }
                        else:
                            return {
                                "success": False,
                                "error": data.get('error', 'Unknown error')
                            }
                    except Exception as e:
                        return {
                            "success": False,
                            "error": f"JSON解析エラー: {e}"
                        }
                else:
                    return {
                        "success": False,
                        "error": "Modal出力から画像データを取得できませんでした"
                    }
            else:
                return {
                    "success": False,
                    "error": result.stderr or result.stdout
                }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "処理がタイムアウトしました"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


if __name__ == "__main__":
    # テスト
    client = ManaOSUpscaleClient()

    # テスト画像を探す
    test_image = Path("/root/trinity_workspace/generated_images/mufufu_runpod_20251105_192550_010.png")

    if test_image.exists():
        print(f"🎨 画像超解像テスト: {test_image}")
        result = client.upscale_image(
            str(test_image),
            scale=2,
            method="simple"  # 軽量版でテスト
        )

        if result.get('success'):
            print(f"✅ 成功: {result['path']}")
            print(f"   元サイズ: {result['original_size']}")
            print(f"   拡大サイズ: {result['upscaled_size']}")
        else:
            print(f"❌ 失敗: {result.get('error')}")
    else:
        print("⚠️  テスト画像が見つかりません")

