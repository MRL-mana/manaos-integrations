#!/usr/bin/env python3
"""
Modal.com GPU Service - 画像超解像（Real-ESRGAN）
生成した画像を高解像度化
"""

import modal

# Modalアプリケーション定義
stub = modal.App("manaos-image-upscale")

# GPU付きイメージの定義
image = (
    modal.Image.debian_slim()
    .pip_install(
        "torch",
        "torchvision",
        "basicsr",
        "facexlib",
        "gfpgan",
        "realesrgan",
        "pillow",
        "numpy",
        "opencv-python-headless"
    )
)

# 永続ボリューム（モデルキャッシュ用）
volume = modal.Volume.from_name("manaos-model-cache", create_if_missing=True)

@stub.function(
    image=image,
    gpu="T4",  # NVIDIA T4 GPU
    timeout=600,  # 10分タイムアウト
    volumes={"/cache": volume}
)
def upscale_image(image_base64: str, scale: int = 4, model_name: str = "realesrgan-x4plus"):
    """
    画像を超解像（拡大）

    Args:
        image_base64: 元画像のBase64エンコード文字列
        scale: 拡大倍率（2, 4など）
        model_name: 使用モデル（"realesrgan-x4plus", "realesrgan-x4plus-anime"など）

    Returns:
        拡大された画像のバイナリデータ（Base64）
    """
    from io import BytesIO
    from PIL import Image
    import base64

    try:
        # Base64から画像を復元
        image_bytes = base64.b64decode(image_base64)
        from realesrgan import RealESRGANer
        from basicsr.archs.rrdbnet_arch import RRDBNet
        import torch

        # 画像読み込み
        input_image = Image.open(BytesIO(image_bytes))

        # モデル設定
        if model_name == "realesrgan-x4plus":
            model = RRDBNet(num_in_frame=3, num_out_frame=3, num_feat=64,
                          num_block=23, num_grow_ch=32, scale=4)
            model_path = "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth"
        elif model_name == "realesrgan-x4plus-anime":
            model = RRDBNet(num_in_frame=3, num_out_frame=3, num_feat=64,
                          num_block=6, num_grow_ch=32, scale=4)
            model_path = "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth"
        else:
            model = RRDBNet(num_in_frame=3, num_out_frame=3, num_feat=64,
                          num_block=23, num_grow_ch=32, scale=4)
            model_path = "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth"

        # Real-ESRGAN初期化
        upsampler = RealESRGANer(
            scale=scale,
            model_path=model_path,
            model=model,
            tile=400,
            tile_pad=10,
            pre_pad=0,
            half=True if torch.cuda.is_available() else False
        )

        # 画像をnumpy配列に変換
        import numpy as np
        img_array = np.array(input_image.convert("RGB"))

        # 超解像処理
        output, _ = upsampler.enhance(img_array, outscale=scale)

        # PIL Imageに変換
        output_image = Image.fromarray(output)

        # バイナリに変換
        buffer = BytesIO()
        output_image.save(buffer, format="PNG")
        buffer.seek(0)
        image_bytes_output = buffer.read()

        # Base64エンコード
        image_base64 = base64.b64encode(image_bytes_output).decode()

        return {
            "success": True,
            "image_base64": image_base64,
            "size": len(image_bytes_output),
            "original_size": input_image.size,
            "upscaled_size": output_image.size,
            "scale": scale
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@stub.function(
    image=image,
    gpu="T4",
    timeout=300,
    volumes={"/cache": volume}
)
def simple_upscale(image_base64: str, scale: int = 2):
    """
    シンプルな画像拡大（PIL使用、軽量版）

    Args:
        image_base64: 元画像のBase64エンコード文字列
        scale: 拡大倍率

    Returns:
        拡大された画像のバイナリデータ（Base64）
    """
    from io import BytesIO
    from PIL import Image
    import base64

    try:
        # Base64から画像を復元
        image_bytes = base64.b64decode(image_base64)
        # 画像読み込み
        input_image = Image.open(BytesIO(image_bytes))
        original_size = input_image.size

        # 拡大（LANCZOS補間）
        new_size = (original_size[0] * scale, original_size[1] * scale)
        output_image = input_image.resize(new_size, Image.Resampling.LANCZOS)

        # バイナリに変換
        buffer = BytesIO()
        output_image.save(buffer, format="PNG")
        buffer.seek(0)
        image_bytes_output = buffer.read()

        # Base64エンコード
        image_base64 = base64.b64encode(image_bytes_output).decode()

        return {
            "success": True,
            "image_base64": image_base64,
            "size": len(image_bytes_output),
            "original_size": original_size,
            "upscaled_size": output_image.size,
            "scale": scale,
            "method": "PIL_LANCZOS"
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@stub.local_entrypoint()
def main():
    """ローカルテスト用"""
    print("🚀 ManaOS Image Upscale Service - Health Check")
    print("✅ Service ready!")


if __name__ == "__main__":
    main()

