# -*- coding: utf-8 -*-
"""リアル系NSFW画像30枚生成（明示的プロンプト + NSFWモデル）"""

import asyncio
from llama3_guru_image_generator import Llama3GuruImageGenerator

async def generate_mufufu_nsfw_explicit_30():
    print("=" * 60)
    print("リアル系NSFW画像30枚生成（明示的プロンプト + NSFWモデル）")
    print("=" * 60)
    
    generator = Llama3GuruImageGenerator()
    
    # NSFW向けモデルに変更
    generator.sd_model_id = "SG161222/Realistic_Vision_V5.1_noVAE"  # NSFW対応のリアル系モデル
    
    # 接続確認
    print("\n[1] Llama 3接続確認...")
    if not await generator.check_llama_connection():
        print("[INFO] Llama 3への接続に失敗しましたが、デフォルトプロンプトで続行します")
    
    # より明示的なNSFWプロンプト
    base_prompts = [
        "mufufu, japanese woman, clear pure gal style, completely naked, fully nude, no clothes, exposed breasts, exposed genitals, realistic portrait, beautiful woman, professional photography, highly detailed, 4k, masterpiece, natural lighting, soft smile, elegant expression, sexual intercourse, making love, explicit",
        "mufufu, japanese girl, clear pure gal, completely nude, full nudity, naked body, exposed, photorealistic, beautiful woman, professional portrait, highly detailed, 4k, masterpiece, studio lighting, gentle expression, high quality, sex scene, explicit content",
        "mufufu, japanese woman, clear pure gal style, naked, nude, no clothing, bare, exposed, realistic photo, attractive woman, professional photography, highly detailed, 4k, masterpiece, natural skin texture, warm smile, cinematic lighting, sexual act, explicit",
        "mufufu, japanese girl, clear pure gal, completely naked, fully nude, exposed body, photorealistic portrait, beautiful woman, professional shot, highly detailed, 4k, masterpiece, soft natural lighting, charming expression, ultra realistic, sexual intercourse, explicit",
        "mufufu, japanese woman, clear pure gal style, nude, naked, no clothes, bare skin, realistic photography, beautiful woman, professional portrait, highly detailed, 4k, masterpiece, perfect skin, elegant pose, high resolution, sex, making love, explicit content",
    ]
    
    negative_prompt = "blurry, low quality, distorted, ugly, bad anatomy, bad proportions, deformed, disfigured, poorly drawn, cartoon, anime, illustration, painting, drawing, sketch, 2d, fake, artificial, censored, clothed, wearing clothes, dressed"
    
    # 30枚生成（各プロンプトから6枚ずつ）
    print("\n[2] 画像生成開始...")
    print(f"     合計30枚を生成します（リアル系NSFW - 明示的プロンプト）")
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
                    images = generator.sd_generator.generate(
                        prompt=base_prompt,
                        negative_prompt=negative_prompt,
                        width=512,
                        height=512,
                        num_inference_steps=40,  # NSFWは少し多めに
                        guidance_scale=7.5,
                        seed=None,  # ランダムシードでバリエーション
                        output_dir="mufufu_nsfw_explicit_30",
                        num_images_per_prompt=1
                    )
                    all_images.extend(images)
                    print(f"      [OK] 生成完了")
                except Exception as e:
                    print(f"      [ERROR] エラー: {e}")
                    continue
        
        print(f"\n[OK] 画像生成完了！")
        print(f"     合計 {len(all_images)} 枚生成されました")
        print(f"     保存先: mufufu_nsfw_explicit_30/")
        
    except Exception as e:
        print(f"[ERROR] エラー: {e}")
        import traceback
        traceback.print_exc()
    finally:
        generator.cleanup()

if __name__ == "__main__":
    asyncio.run(generate_mufufu_nsfw_explicit_30())




