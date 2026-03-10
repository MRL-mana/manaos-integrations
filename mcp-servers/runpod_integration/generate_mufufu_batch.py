#!/usr/bin/env python3
"""
マナ好みのムフフ画像を大量生成してギャラリーに保存
RunPod統合版
"""

import sys
from pathlib import Path
from datetime import datetime
import json

# ManaOS統合パス
sys.path.insert(0, '/root/runpod_integration')
sys.path.insert(0, '/root')

from manaos_modal_client import ManaOSModalClient

# RunPod Serverless（オプション）
try:
    from manaos_unified_system.services.runpod_serverless_client import RunPodServerlessClient
    RUNPOD_SERVERLESS_AVAILABLE = True
except ImportError:
    RUNPOD_SERVERLESS_AVAILABLE = False
    print("⚠️ RunPod Serverlessは利用できません（オプション）")

# ギャラリー保存先
GALLERY_DIR = Path("/root/trinity_workspace/generated_images")
GALLERY_DIR.mkdir(parents=True, exist_ok=True)

# マナ好みのプロンプト（ムフフモード）
MUFUFU_PROMPTS = [
    "beautiful young woman, elegant and graceful, wearing a flowing dress, soft lighting, high quality, detailed",
    "cute anime-style character, kawaii expression, colorful outfit, vibrant background, high quality",
    "gorgeous female portrait, artistic style, beautiful features, professional photography, 8k quality",
    "adorable girl, sweet smile, casual outfit, natural setting, high resolution",
    "elegant lady, sophisticated pose, fashionable dress, studio lighting, premium quality",
    "charming young woman, gentle expression, stylish clothing, dreamy atmosphere, detailed",
    "pretty girl, cheerful look, cute outfit, bright background, high quality",
    "beautiful female character, anime style, expressive eyes, detailed artwork, 4k",
    "lovely woman, graceful pose, elegant dress, soft colors, professional quality",
    "cute character, happy expression, colorful design, vibrant style, high resolution",
]

# ネガティブプロンプト（ムフフモード用）
MUFUFU_NEGATIVE = "nsfw, nude, explicit, inappropriate, low quality, blurry, distorted, ugly, bad anatomy"

def generate_with_modal(prompt: str, index: int) -> dict:
    """Modal.comで画像生成"""
    client = ManaOSModalClient()

    result = client.generate_image(
        prompt=prompt,
        negative_prompt=MUFUFU_NEGATIVE,
        steps=30,
        output_path=None  # 自動生成
    )

    if result.get('success'):
        # ギャラリーにコピー
        source_path = Path(result['path'])
        gallery_path = GALLERY_DIR / f"mufufu_modal_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{index:03d}.png"

        import shutil

        # ソースファイルが存在するか確認
        if not source_path.exists():
            # ディレクトリが存在しない場合は作成
            source_path.parent.mkdir(parents=True, exist_ok=True)
            # 別の可能性のあるパスを確認
            alt_paths = [
                Path("/root/generated_images") / source_path.name,
                Path("/tmp") / source_path.name,
                source_path
            ]
            found = False
            for alt_path in alt_paths:
                if alt_path.exists():
                    source_path = alt_path
                    found = True
                    break

            if not found:
                return {"success": False, "error": f"生成されたファイルが見つかりません: {result['path']}"}

        shutil.copy2(source_path, gallery_path)
        result['gallery_path'] = str(gallery_path)
        return result

    return result

def generate_with_runpod_serverless(prompt: str, index: int) -> dict:
    """RunPod Serverlessで画像生成"""
    if not RUNPOD_SERVERLESS_AVAILABLE:
        return {"success": False, "error": "RunPod Serverless is not available"}

    client = RunPodServerlessClient()  # type: ignore[possibly-unbound]

    result = client.generate_image(
        prompt=prompt,
        model="stable_diffusion",
        width=1024,
        height=768,
        steps=30,
        negative_prompt=MUFUFU_NEGATIVE,
        save_to_network_storage=False
    )

    if result.get('status') == 'completed':
        output = result.get('output', {})

        # 画像パスの取得（複数の可能性を考慮）
        image_path = None
        if isinstance(output, dict):
            image_path = output.get('image_path') or output.get('saved_path') or output.get('path')

        # Base64エンコードされた画像がある場合
        if not image_path and isinstance(output, dict) and 'image_base64' in output:
            import base64
            from PIL import Image
            import io

            image_data = base64.b64decode(output['image_base64'])
            image = Image.open(io.BytesIO(image_data))
            gallery_path = GALLERY_DIR / f"mufufu_runpod_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{index:03d}.png"
            image.save(gallery_path)
            return {"success": True, "gallery_path": str(gallery_path)}

        # ファイルパスがある場合
        if image_path:
            source_path = Path(image_path)
            gallery_path = GALLERY_DIR / f"mufufu_runpod_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{index:03d}.png"

            import shutil
            if source_path.exists():
                shutil.copy2(source_path, gallery_path)
                return {"success": True, "gallery_path": str(gallery_path)}
            else:
                # パスが存在しない場合、outputをそのまま返す
                return {"success": True, "gallery_path": None, "output": output}

    return {"success": False, "error": result.get('error', 'Unknown error'), "result": result}

def main():
    print("🎨 マナ好みのムフフ画像大量生成開始！")
    print("=" * 60)
    print(f"生成数: {len(MUFUFU_PROMPTS)}枚")
    print(f"保存先: {GALLERY_DIR}")
    print()

    results = []

    # Modal.comで生成（優先）
    print("📊 Phase 1（Modal.com）で生成中...")
    for i, prompt in enumerate(MUFUFU_PROMPTS[:5], 1):
        print(f"\n[{i}/{len(MUFUFU_PROMPTS[:5])}] 生成中: {prompt[:50]}...")
        result = generate_with_modal(prompt, i)

        if result.get('success'):
            print(f"✅ 成功: {result.get('gallery_path')}")
            results.append({
                "method": "Modal.com",
                "prompt": prompt,
                "gallery_path": result.get('gallery_path'),
                "success": True
            })
        else:
            print(f"❌ 失敗: {result.get('error')}")
            results.append({
                "method": "Modal.com",
                "prompt": prompt,
                "success": False,
                "error": result.get('error')
            })

    # RunPod Serverlessで生成（残り、またはModal.comで全部生成）
    if RUNPOD_SERVERLESS_AVAILABLE:
        print("\n📊 RunPod Serverlessで生成中...")
        for i, prompt in enumerate(MUFUFU_PROMPTS[5:], 6):
            print(f"\n[{i}/{len(MUFUFU_PROMPTS)}] 生成中: {prompt[:50]}...")
            result = generate_with_runpod_serverless(prompt, i)

            if result.get('success'):
                print(f"✅ 成功: {result.get('gallery_path')}")
                results.append({
                    "method": "RunPod Serverless",
                    "prompt": prompt,
                    "gallery_path": result.get('gallery_path'),
                    "success": True
                })
            else:
                print(f"❌ 失敗: {result.get('error')}")
                results.append({
                    "method": "RunPod Serverless",
                    "prompt": prompt,
                    "success": False,
                    "error": result.get('error')
                })
    else:
        # RunPod Serverlessが使えない場合は、Modal.comで全部生成
        print("\n📊 Modal.comで残りも生成中...")
        for i, prompt in enumerate(MUFUFU_PROMPTS[5:], 6):
            print(f"\n[{i}/{len(MUFUFU_PROMPTS)}] 生成中: {prompt[:50]}...")
            result = generate_with_modal(prompt, i)

            if result.get('success'):
                print(f"✅ 成功: {result.get('gallery_path')}")
                results.append({
                    "method": "Modal.com",
                    "prompt": prompt,
                    "gallery_path": result.get('gallery_path'),
                    "success": True
                })
            else:
                print(f"❌ 失敗: {result.get('error')}")
                results.append({
                    "method": "Modal.com",
                    "prompt": prompt,
                    "success": False,
                    "error": result.get('error')
                })

    # 結果サマリー
    print("\n" + "=" * 60)
    print("📊 生成結果サマリー")
    print("=" * 60)

    success_count = sum(1 for r in results if r.get('success'))
    print(f"✅ 成功: {success_count}/{len(results)}枚")
    print(f"❌ 失敗: {len(results) - success_count}/{len(results)}枚")

    # 結果をJSONで保存
    result_file = GALLERY_DIR / f"generation_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n💾 結果を保存: {result_file}")
    print(f"📁 ギャラリー: {GALLERY_DIR}")
    print("\n🎉 完了！ギャラリーで確認してください！")

if __name__ == "__main__":
    main()

