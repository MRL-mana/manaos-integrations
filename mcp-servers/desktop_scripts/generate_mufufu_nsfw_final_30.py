# -*- coding: utf-8 -*-
"""リアル系NSFW画像30枚生成（最適化プロンプト）"""

import asyncio
from llama3_guru_image_generator import Llama3GuruImageGenerator

async def generate_mufufu_nsfw_final_30():
    print("=" * 60)
    print("リアル系NSFW画像30枚生成（最適化プロンプト）")
    print("=" * 60)
    
    generator = Llama3GuruImageGenerator()
    
    # NSFW向けモデル
    generator.sd_model_id = "SG161222/Realistic_Vision_V5.1_noVAE"
    
    # 接続確認
    print("\n[1] Llama 3接続確認...")
    if not await generator.check_llama_connection():
        print("[INFO] Llama 3への接続に失敗しましたが、デフォルトプロンプトで続行します")
    
    # 最適化されたNSFWプロンプト（77トークン以内、重要キーワード優先）
    base_prompts = [
        "mufufu, japanese woman, clear pure gal, completely naked, fully nude, exposed breasts, exposed pussy, having sex, sexual intercourse, missionary position, penetration, realistic, 4k, masterpiece",
        "mufufu, japanese girl, clear pure gal, completely nude, naked body, bare breasts, bare pussy, sex scene, doggy style, explicit, photorealistic, 4k, masterpiece",
        "mufufu, japanese woman, clear pure gal, naked, nude, exposed nipples, exposed genitals, making love, cowgirl position, explicit sex, realistic, 4k, masterpiece",
        "mufufu, japanese girl, clear pure gal, fully nude, no clothes, exposed body, sexual act, explicit intercourse, photorealistic, 4k, masterpiece",
        "mufufu, japanese woman, clear pure gal, completely naked, exposed breasts, exposed vagina, sex, penetration, explicit, realistic, 4k, masterpiece",
    ]
    
    negative_prompt = "blurry, low quality, distorted, ugly, bad anatomy, bad proportions, deformed, disfigured, poorly drawn, cartoon, anime, illustration, painting, drawing, sketch, 2d, fake, artificial, censored, clothed, wearing clothes, dressed, bikini, underwear, bra, panties"
    
    # 30枚生成（各プロンプトから6枚ずつ）
    print("\n[2] 画像生成開始...")
    print(f"     合計30枚を生成します（リアル系NSFW - 最適化プロンプト）")
    print(f"     モデル: {generator.sd_model_id}")
    
    try:
        generator.initialize_sd(disable_safety_checker=True)  # ローカル環境用に安全フィルターを無効化
        
        all_images = []
        total = 30
        current = 0
        
        # 各ベースプロンプトから6枚ずつ生成
        for i, base_prompt in enumerate(base_prompts, 1):
            print(f"\n[{i}/5] プロンプトセット {i}: {base_prompt[:70]}...")
            
            for j in range(6):
                current += 1
                print(f"  [{current}/{total}] 生成中...")
                
                try:
                    images = generator.sd_generator.generate(  # type: ignore[union-attr]
                        prompt=base_prompt,
                        negative_prompt=negative_prompt,
                        width=512,
                        height=512,
                        num_inference_steps=50,  # NSFWはさらに多めに
                        guidance_scale=7.5,
                        seed=None,  # ランダムシードでバリエーション
                        output_dir="mufufu_nsfw_final_30",
                        num_images_per_prompt=1
                    )
                    all_images.extend(images)
                    print(f"      [OK] 生成完了")
                except Exception as e:
                    print(f"      [ERROR] エラー: {e}")
                    continue
        
        print(f"\n[OK] 画像生成完了！")
        print(f"     合計 {len(all_images)} 枚生成されました")
        print(f"     保存先: mufufu_nsfw_final_30/")
        
    except Exception as e:
        print(f"[ERROR] エラー: {e}")
        import traceback
        traceback.print_exc()
    finally:
        generator.cleanup()

if __name__ == "__main__":
    asyncio.run(generate_mufufu_nsfw_final_30())




