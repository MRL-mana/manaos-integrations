#!/usr/bin/env python3
"""
ManaOS Video Generation Client
Modal.com/RunPod Serverlessで動画生成を実行
"""

import base64
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List


class ManaOSVideoClient:
    """動画生成クライアント"""

    def __init__(self):
        self.modal_service_path = "/root/runpod_integration/modal_video_generation.py"

    def check_modal_auth(self) -> bool:
        """Modal認証確認"""
        from pathlib import Path
        modal_config = Path.home() / ".modal.toml"
        return modal_config.exists()

    def generate_video_from_image(
        self,
        image_path: str,
        output_path: Optional[str] = None,
        num_frames: int = 14,
        num_inference_steps: int = 25,
        fps: int = 7
    ) -> Dict[str, Any]:
        """
        画像から動画を生成

        Args:
            image_path: 元画像のパス
            output_path: 出力先パス（Noneの場合は自動生成）
            num_frames: 生成フレーム数
            num_inference_steps: 推論ステップ数
            fps: フレームレート

        Returns:
            結果辞書
        """
        if not self.check_modal_auth():
            return {
                "success": False,
                "error": "Modal認証が必要です"
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

            # Modal関数を直接呼び出す
            try:
                import modal
                app = modal.App.lookup("manaos-video-generation", create_if_missing=False)

                with app.run():
                    result_data = app.generate_video_from_image.remote(
                        image_base64=image_base64,
                        num_frames=num_frames,
                        num_inference_steps=num_inference_steps,
                        fps=fps
                    )

                if result_data.get('success'):
                    # 出力パスを決定
                    if not output_path:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        output_path = f"/root/generated_images/video_{timestamp}.mp4"

                    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

                    # Base64から動画を復元
                    video_bytes = base64.b64decode(result_data['video_base64'])
                    with open(output_path, 'wb') as f:
                        f.write(video_bytes)

                    return {
                        "success": True,
                        "path": output_path,
                        "num_frames": result_data.get('num_frames'),
                        "fps": result_data.get('fps'),
                        "duration": result_data.get('duration'),
                        "size": result_data.get('size')
                    }
                else:
                    return {
                        "success": False,
                        "error": result_data.get('error', 'Unknown error')
                    }

            except Exception as e:
                return {
                    "success": False,
                    "error": f"Modal実行エラー: {e}"
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def generate_gif_from_images(
        self,
        image_paths: List[str],
        output_path: Optional[str] = None,
        duration: float = 0.5,
        loop: int = 0
    ) -> Dict[str, Any]:
        """
        複数の画像からGIFを生成

        Args:
            image_paths: 画像パスのリスト
            output_path: 出力先パス
            duration: 各フレームの表示時間
            loop: ループ回数

        Returns:
            結果辞書
        """
        if not self.check_modal_auth():
            return {
                "success": False,
                "error": "Modal認証が必要です"
            }

        try:
            # 画像をBase64エンコード
            image_base64_list = []
            for img_path in image_paths:
                img_path_obj = Path(img_path)
                if not img_path_obj.exists():
                    continue

                with open(img_path_obj, 'rb') as f:
                    img_bytes = f.read()
                image_base64_list.append(base64.b64encode(img_bytes).decode())

            if not image_base64_list:
                return {
                    "success": False,
                    "error": "有効な画像が見つかりません"
                }

            # Modal関数を直接呼び出す
            try:
                import modal
                app = modal.App.lookup("manaos-video-generation", create_if_missing=False)

                with app.run():
                    result_data = app.generate_gif_from_images.remote(
                        image_base64_list=image_base64_list,
                        duration=duration,
                        loop=loop
                    )

                if result_data.get('success'):
                    # 出力パスを決定
                    if not output_path:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        output_path = f"/root/generated_images/gif_{timestamp}.gif"

                    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

                    # Base64からGIFを復元
                    gif_bytes = base64.b64decode(result_data['gif_base64'])
                    with open(output_path, 'wb') as f:
                        f.write(gif_bytes)

                    return {
                        "success": True,
                        "path": output_path,
                        "num_frames": result_data.get('num_frames'),
                        "size": result_data.get('size')
                    }
                else:
                    return {
                        "success": False,
                        "error": result_data.get('error', 'Unknown error')
                    }

            except Exception as e:
                return {
                    "success": False,
                    "error": f"Modal実行エラー: {e}"
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


if __name__ == "__main__":
    # テスト
    client = ManaOSVideoClient()

    # テスト画像を探す
    test_image = Path("/root/trinity_workspace/generated_images/mufufu_runpod_20251105_192550_010.png")

    if test_image.exists():
        print(f"🎬 動画生成テスト: {test_image}")
        print("⚠️  注意: 動画生成には時間がかかります（約5-10分）")
        print("   まずはGIF生成をテストします...")

        # GIF生成テスト（複数の画像から）
        gallery_dir = Path("/root/trinity_workspace/generated_images")
        test_images = sorted(gallery_dir.glob('mufufu_runpod_*.png'),
                            key=lambda x: x.stat().st_mtime,
                            reverse=True)[:5]

        if len(test_images) >= 3:
            result = client.generate_gif_from_images(
                [str(img) for img in test_images],
                duration=0.5
            )

            if result.get('success'):
                print(f"✅ GIF生成成功: {result['path']}")
                print(f"   フレーム数: {result['num_frames']}")
            else:
                print(f"❌ 失敗: {result.get('error')}")
    else:
        print("⚠️  テスト画像が見つかりません")








