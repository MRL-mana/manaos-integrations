#!/usr/bin/env python3
"""
マナ好みのムフフ画像を大量生成（シンプル版）
Modal.comのみ使用
"""

import sys
from pathlib import Path
from datetime import datetime
import json
import shutil

sys.path.insert(0, '/root/runpod_integration')
sys.path.insert(0, '/root')

from manaos_modal_client import ManaOSModalClient

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

def main():
    print("🎨 マナ好みのムフフ画像大量生成開始！")
    print("=" * 60)
    print(f"生成数: {len(MUFUFU_PROMPTS)}枚")
    print(f"保存先: {GALLERY_DIR}")
    print()

    client = ManaOSModalClient()
    results = []

    # Modal.comで生成
    print("📊 Modal.comで生成中...")
    for i, prompt in enumerate(MUFUFU_PROMPTS, 1):
        print(f"\n[{i}/{len(MUFUFU_PROMPTS)}] 生成中: {prompt[:50]}...")

        result = client.generate_image(
            prompt=prompt,
            negative_prompt=MUFUFU_NEGATIVE,
            steps=30,
            output_path=None
        )

        if result.get('success'):
            # ギャラリーにコピー
            source_path = Path(result['path'])
            gallery_path = GALLERY_DIR / f"mufufu_modal_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{i:03d}.png"

            # ファイルが存在するか確認
            if source_path.exists():
                shutil.copy2(source_path, gallery_path)
                print(f"✅ 成功: {gallery_path}")
                results.append({
                    "method": "Modal.com",
                    "prompt": prompt,
                    "gallery_path": str(gallery_path),
                    "success": True
                })
            else:
                # ファイルが見つからない場合
                alt_path = Path("/root/generated_images") / source_path.name
                if alt_path.exists():
                    shutil.copy2(alt_path, gallery_path)
                    print(f"✅ 成功（代替パス）: {gallery_path}")
                    results.append({
                        "method": "Modal.com",
                        "prompt": prompt,
                        "gallery_path": str(gallery_path),
                        "success": True
                    })
                else:
                    print(f"⚠️  ファイルが見つかりません: {result['path']}")
                    results.append({
                        "method": "Modal.com",
                        "prompt": prompt,
                        "success": False,
                        "error": f"ファイルが見つかりません: {result['path']}"
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








