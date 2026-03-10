# -*- coding: utf-8 -*-
"""マナ好みのムフフ画像30枚生成"""

import asyncio
from llama3_guru_image_generator import Llama3GuruImageGenerator

async def generate_mufufu_30():
    print("=" * 60)
    print("マナ好みのムフフ画像30枚生成")
    print("=" * 60)
    
    generator = Llama3GuruImageGenerator()
    
    # 接続確認
    print("\n[1] Llama 3接続確認...")
    if not await generator.check_llama_connection():
        print("[INFO] Llama 3への接続に失敗しましたが、デフォルトプロンプトで続行します")
    
    # マナ好みのプロンプトバリエーション
    base_prompts = [
        "mufufu, cute girl, anime style, highly detailed, 4k, masterpiece, best quality, beautiful eyes, soft smile",
        "mufufu, kawaii girl, anime art style, highly detailed, 4k, masterpiece, best quality, cute expression, fluffy hair",
        "mufufu, adorable girl, anime character, highly detailed, 4k, masterpiece, best quality, bright eyes, cheerful smile",
        "mufufu, sweet girl, anime illustration, highly detailed, 4k, masterpiece, best quality, gentle expression, elegant pose",
        "mufufu, lovely girl, anime style, highly detailed, 4k, masterpiece, best quality, cute outfit, charming smile",
    ]
    
    negative_prompt = "blurry, low quality, distorted, ugly, bad anatomy, bad proportions, deformed, disfigured, poorly drawn"
    
    # 30枚生成（各プロンプトから6枚ずつ）
    print("\n[2] 画像生成開始...")
    print(f"     合計30枚を生成します")
    
    try:
        generator.initialize_sd()
        
        all_images = []
        total = 30
        current = 0
        
        # 各ベースプロンプトから6枚ずつ生成
        for i, base_prompt in enumerate(base_prompts, 1):
            print(f"\n[{i}/5] プロンプトセット {i}: {base_prompt[:50]}...")
            
            for j in range(6):
                current += 1
                print(f"  [{current}/{total}] 生成中...")
                
                try:
                    images = generator.sd_generator.generate(  # type: ignore[union-attr]
                        prompt=base_prompt,
                        negative_prompt=negative_prompt,
                        width=512,
                        height=512,
                        num_inference_steps=25,  # 少し高品質に
                        guidance_scale=7.5,
                        seed=None,  # ランダムシードでバリエーション
                        output_dir="mufufu_images_30",
                        num_images_per_prompt=1
                    )
                    all_images.extend(images)
                    print(f"      [OK] 生成完了")
                except Exception as e:
                    print(f"      [ERROR] エラー: {e}")
                    continue
        
        print(f"\n[OK] 画像生成完了！")
        print(f"     合計 {len(all_images)} 枚生成されました")
        print(f"     保存先: mufufu_images_30/")
        
    except Exception as e:
        print(f"[ERROR] エラー: {e}")
        import traceback
        traceback.print_exc()
    finally:
        generator.cleanup()

if __name__ == "__main__":
    asyncio.run(generate_mufufu_30())

