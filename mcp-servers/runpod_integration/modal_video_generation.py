#!/usr/bin/env python3
"""
Modal.com GPU Service - 動画生成（Stable Video Diffusion）
画像から動画を生成
"""

import modal

# Modalアプリケーション定義
stub = modal.App("manaos-video-generation")

# GPU付きイメージの定義
image = (
    modal.Image.debian_slim()
    .pip_install(
        "torch",
        "torchvision",
        "diffusers",
        "transformers",
        "accelerate",
        "safetensors",
        "pillow",
        "numpy",
        "opencv-python-headless",
        "imageio",
        "imageio-ffmpeg"
    )
)

# 永続ボリューム（モデルキャッシュ用）
volume = modal.Volume.from_name("manaos-model-cache", create_if_missing=True)

@stub.function(
    image=image,
    gpu="A10G",  # NVIDIA A10G GPU（動画生成にはより強力なGPUが必要）
    timeout=1200,  # 20分タイムアウト
    volumes={"/cache": volume}
)
def generate_video_from_image(
    image_base64: str,
    num_frames: int = 14,
    num_inference_steps: int = 25,
    fps: int = 7
):
    """
    画像から動画を生成（Stable Video Diffusion）

    Args:
        image_base64: 元画像のBase64エンコード文字列
        num_frames: 生成フレーム数（最大14）
        num_inference_steps: 推論ステップ数
        fps: フレームレート

    Returns:
        生成された動画のバイナリデータ（Base64）
    """
    from io import BytesIO
    from PIL import Image
    import base64
    import torch
    from diffusers import StableVideoDiffusionPipeline
    import numpy as np
    import imageio

    try:
        # Base64から画像を復元
        image_bytes = base64.b64decode(image_base64)
        input_image = Image.open(BytesIO(image_bytes)).convert("RGB")

        # モデルロード
        model_id = "stabilityai/stable-video-diffusion-img2vid-xt"
        pipe = StableVideoDiffusionPipeline.from_pretrained(
            model_id,
            torch_dtype=torch.float16,
            variant="fp16",
            cache_dir="/cache"
        )
        pipe = pipe.to("cuda")

        # 画像をリサイズ（モデル要件: 1024x576）
        input_image = input_image.resize((1024, 576))

        # 動画生成
        frames = pipe(
            input_image,
            decode_chunk_size=2,
            num_frames=num_frames,
            num_inference_steps=num_inference_steps,
            motion_bucket_id=127
        ).frames[0]

        # フレームをnumpy配列に変換
        video_frames = [np.array(frame) for frame in frames]

        # 動画ファイルに保存（MP4）
        buffer = BytesIO()
        imageio.mimwrite(
            buffer,
            video_frames,
            format='mp4',
            fps=fps,
            codec='libx264',
            quality=8
        )
        buffer.seek(0)
        video_bytes = buffer.read()

        # Base64エンコード
        video_base64 = base64.b64encode(video_bytes).decode()

        return {
            "success": True,
            "video_base64": video_base64,
            "size": len(video_bytes),
            "num_frames": num_frames,
            "fps": fps,
            "duration": num_frames / fps
        }

    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }


@stub.function(
    image=image,
    gpu="T4",  # 軽量版はT4で可能
    timeout=600,
    volumes={"/cache": volume}
)
def generate_gif_from_images(
    image_base64_list: list,
    duration: float = 0.5,
    loop: int = 0
):
    """
    複数の画像からGIFアニメーションを生成

    Args:
        image_base64_list: 画像のBase64エンコード文字列のリスト
        duration: 各フレームの表示時間（秒）
        loop: ループ回数（0=無限）

    Returns:
        GIFのバイナリデータ（Base64）
    """
    from io import BytesIO
    from PIL import Image
    import base64
    import imageio

    try:
        # Base64から画像を復元
        images = []
        for img_base64 in image_base64_list:
            img_bytes = base64.b64decode(img_base64)
            img = Image.open(BytesIO(img_bytes)).convert("RGB")
            images.append(img)

        # GIF生成
        buffer = BytesIO()
        imageio.mimsave(
            buffer,
            [np.array(img) for img in images],
            format='gif',
            duration=duration,
            loop=loop
        )
        buffer.seek(0)
        gif_bytes = buffer.read()

        # Base64エンコード
        gif_base64 = base64.b64encode(gif_bytes).decode()

        return {
            "success": True,
            "gif_base64": gif_base64,
            "size": len(gif_bytes),
            "num_frames": len(images),
            "duration": duration
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@stub.local_entrypoint()
def main():
    """ローカルテスト用"""
    print("🚀 ManaOS Video Generation Service - Ready")
    print("✅ Service ready!")


if __name__ == "__main__":
    main()








