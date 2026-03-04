#!/usr/bin/env python3
"""
「日本人清楚系ギャル　女子高校生　性行為」をベースに、刺激的な要素を自動追加して100ステップで生成
"""

import sys
import os
sys.path.insert(0, '/home/mana/scripts')

import torch
from diffusers import StableDiffusionPipeline, StableDiffusionXLPipeline
from pathlib import Path
from datetime import datetime
import random
import gc
import time
from PIL import Image

# ベースプロンプト（日本人清楚系ギャル + ムフフ要素を明確に指定）
BASE_PROMPT = "Japanese gal, clear and pure type gal, large eyes, double eyelids, long eyelashes, aegyo-sal, small nose, plump lips, coral pink lips, oval face, fair skin, smooth skin, long straight black hair, bangs, fringe, 18 years old, adult, young adult, nude, naked, sex, explicit, erotic, seductive, 性行為, 裸, セックス, フェラ"

# エッチな自動追加要素のリスト
AUTO_ADDITIONS = [
    # 性的要素（エッチ）- 優先的に追加される
    "nude, naked, 裸, 裸体",
    "sex, explicit, セックス, 性行為",
    "oral sex, フェラ, フェラチオ, blowjob",
    "sex scene, 性行為シーン, intimate scene",
    "erotic, エロティック, seductive, セクシー",
    "sensual, alluring, 官能的, 魅惑的",
    "explicit content, 露骨な内容",
    "naked body, 裸体, exposed",
    "breasts, おっぱい, nipples, 乳首",
    "pussy, まんこ, vagina, 女性器",
    "ass, お尻, buttocks, 尻",
    "spread legs, open legs, 脚を開く",
    "on top, riding, 騎乗位",
    "from behind, doggy style, バック",
    "missionary position, 正常位",
    "creampie, 中出し, cum inside",
    "facial, 顔射, cum on face",
    "threesome, 3P, multiple partners",
    "アナル, anal",
    "パイズリ, paizuri",
    "手コキ, handjob",
    "正常位, missionary position",
    "騎乗位, cowgirl position",
    "バック, doggy style",
    "3P, threesome",
    "中出し, creampie",
    "顔射, facial",
    "痴女, slut",
    "露出, exhibitionism",
    "拘束, bondage",
    "SM, BDSM",
    # 品質・見た目（日本人清楚系ギャル強調 - 画像の特徴を反映）
    "best quality, masterpiece, 8k, ultra detailed",
    "perfect face, beautiful face, oval face",
    "large eyes, big eyes, double eyelids, long eyelashes, aegyo-sal, tear bags",
    "small nose, delicate nose, upturned nose",
    "plump lips, full lips, coral pink lips, pink lips, glossy lips",
    "flawless skin, smooth skin, clear skin, fair skin, porcelain skin",
    "perfect body, ideal proportions, slim body, well-proportioned",
    "cute, kawaii, beautiful, gorgeous",
    "young adult, 18+, mature appearance",
    # 日本人清楚系ギャル特徴（画像の特徴を反映）
    "Japanese gal style, clear type gal, pure type gal",
    "long straight black hair, glossy black hair, bangs, fringe, side-swept bangs",
    "Japanese face, Asian face, Japanese features",
    "clear and pure, elegant, refined, sophisticated",
    "stylish, fashionable, trendy, modern",
    "healthy, vibrant, energetic, cheerful",
    "well-groomed, neat, tidy, clean appearance",
    "innocent expression, charming expression, seductive expression",
    # ポーズ・シーン（エッチ）
    "seductive pose",
    "explicit content",
    "intimate scene",
    "passionate",
    "erotic pose",
    "alluring, seductive",
    "sensual pose",
    "spread legs",
    "open legs",
    "on top",
    "from behind",
    "close-up",
    "detailed genitals",
    "wet, dripping",
    "cum, semen",
    "orgasm, climax",
    "moaning, expression",
]

MANA_NEGATIVE_PROMPT = (
    "worst quality, low quality, normal quality, lowres, "
    "bad anatomy, bad hands, bad face, bad eyes, bad lips, bad teeth, "
    "ugly face, deformed face, disfigured face, distorted face, "
    "asymmetric face, asymmetric eyes, crooked face, "
    "mutation, mutated face, extra face, duplicate face, "
    "fused face, malformed face, missing face parts, "
    "blurry face, blurry eyes, out of focus face, "
    "long neck, extra neck, double chin, bad proportions, "
    "gross proportions, bad body, poorly drawn face, "
    "poorly drawn eyes, cloned face, cloned eyes, "
    "watermark, text, username, signature, logo, "
    "multiple people, two faces, three faces, crowd, "
    "distant shot, far away, "
    "western, caucasian, blonde hair, blue eyes, "
    "clothed, clothes, clothing, dress, shirt, bra, underwear, "
    "non-Japanese, non-Asian, foreign face, western face, "
    "messy hair, unkempt, disheveled, "
    "loli, lolita, child, children, kid, kids, toddler, baby, infant, "
    "underage, minor, school uniform, elementary school, middle school, "
    "preteen, pre-teen, childish, childlike, juvenile, "
    "flat chest, small breasts, petite body, tiny body, "
    "younger than 18, under 18, 17 years old, 16 years old, 15 years old"
)

def is_sdxl_model_by_name(model_path):
    """ファイル名からSDXLモデルかどうかを判定"""
    filename = Path(model_path).name.lower()
    # SDXLモデルのキーワード（より厳密に）
    sdxl_keywords = ['sdxl', 'xl-', '-xl', 'flux']
    # SDXLではないモデルのキーワード（除外）
    # cyberrealisticPonyは"pony"を含むがSDXLとして正しく動作しないため除外
    non_sdxl_keywords = ['majicmix', 'lux', 'realisian', 'realistic', 'cyberrealistic', 'pony']
    
    # 除外キーワードが含まれている場合はSDXLではない
    if any(keyword in filename for keyword in non_sdxl_keywords):
        return False
    
    # SDXLキーワードが含まれている場合はSDXL
    return any(keyword in filename for keyword in sdxl_keywords)

def generate_auto_prompt(base_prompt, num_additions=None):
    """ベースプロンプトに自動で刺激的な要素を追加"""
    if num_additions is None:
        # 4〜10個の要素をランダムに追加（より多く追加して刺激的に）
        num_additions = random.randint(4, 10)
    
    # ランダムに要素を選択
    selected_additions = random.sample(AUTO_ADDITIONS, min(num_additions, len(AUTO_ADDITIONS)))
    
    # プロンプトを組み立て
    prompt = base_prompt
    for addition in selected_additions:
        prompt += f", {addition}"
    
    return prompt

def load_combined_model(base_model_path, lora_path=None, device="cuda"):
    """ベースモデルとLoRAを組み合わせて読み込み"""
    is_sdxl = is_sdxl_model_by_name(base_model_path)
    
    if is_sdxl:
        pipeline = StableDiffusionXLPipeline.from_single_file(
            base_model_path,
            torch_dtype=torch.float16 if device == "cuda" else torch.float32,
            safety_checker=None,
            requires_safety_checker=False,
            use_safetensors=True
        )
    else:
        pipeline = StableDiffusionPipeline.from_single_file(
            base_model_path,
            torch_dtype=torch.float16 if device == "cuda" else torch.float32,
            safety_checker=None,
            requires_safety_checker=False
        )
    
    pipeline = pipeline.to(device)
    
    # SDXLモデルの検証（text_encoder_2がNoneの場合はSDXLではない）
    if is_sdxl:
        if hasattr(pipeline, 'text_encoder_2') and pipeline.text_encoder_2 is None:
            print(f"   ⚠️ text_encoder_2がNoneのため、SDXLとして扱いません（SD 1.5モデルの可能性）")
            is_sdxl = False  # SDXLとして扱わない
    
    # GPU最適化
    if device == "cuda":
        pipeline.enable_attention_slicing()
        if hasattr(pipeline, 'enable_vae_slicing'):
            pipeline.enable_vae_slicing()
        if hasattr(pipeline, 'enable_vae_tiling'):
            pipeline.enable_vae_tiling()
    
    # tokenizerがNoneでないことを確認（LoRA読み込み前）
    if hasattr(pipeline, 'tokenizer') and pipeline.tokenizer is None:
        from transformers import CLIPTokenizer
        if is_sdxl:
            # SDXLの場合はtokenizer_2も必要
            pipeline.tokenizer = CLIPTokenizer.from_pretrained('openai/clip-vit-large-patch14')
            if hasattr(pipeline, 'tokenizer_2') and pipeline.tokenizer_2 is None:
                from transformers import CLIPTokenizer
                pipeline.tokenizer_2 = CLIPTokenizer.from_pretrained('laion/CLIP-ViT-bigG-14-laion2B-39B-b160k')
        else:
            pipeline.tokenizer = CLIPTokenizer.from_pretrained('openai/clip-vit-large-patch14')
    
    # text_encoderがNoneでないことを確認（SDXLの場合）
    if is_sdxl:
        if hasattr(pipeline, 'text_encoder') and pipeline.text_encoder is None:
            print(f"   ⚠️ text_encoderがNoneです。SDXLとして扱いません")
            is_sdxl = False
    
    # LoRA読み込み（試行）- PEFTを使わない方法
    if lora_path and os.path.exists(lora_path):
        try:
            # PEFTを使わない方法でLoRAを読み込み
            if hasattr(pipeline, 'load_lora_weights'):
                try:
                    # まず通常の方法を試す（PEFT不要の場合）
                    pipeline.load_lora_weights(lora_path)
                except Exception as e1:
                    # PEFTが必要な場合はスキップ
                    if "PEFT" in str(e1) or "peft" in str(e1).lower():
                        print(f"   ⚠️ LoRA読み込みスキップ（PEFTが必要）: {e1}")
                    else:
                        raise e1
        except Exception as e:
            print(f"   ⚠️ LoRA読み込み失敗（続行）: {e}")
    
    # tokenizerがNoneでないことを確認（LoRA読み込み後）
    if hasattr(pipeline, 'tokenizer') and pipeline.tokenizer is None:
        from transformers import CLIPTokenizer
        pipeline.tokenizer = CLIPTokenizer.from_pretrained('openai/clip-vit-large-patch14')
        if is_sdxl and hasattr(pipeline, 'tokenizer_2') and pipeline.tokenizer_2 is None:
            from transformers import CLIPTokenizer
            pipeline.tokenizer_2 = CLIPTokenizer.from_pretrained('laion/CLIP-ViT-bigG-14-laion2B-39B-b160k')
    
    return pipeline, is_sdxl

def generate_with_auto_prompt_100steps(num_images=50):
    """自動プロンプト生成で100ステップ画像生成"""
    print(f"\n🎨 自動プロンプト生成開始（100ステップ）({num_images}枚)")
    print(f"   ベースプロンプト: {BASE_PROMPT}")
    print("=" * 60)
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cuda":
        print(f"✅ GPU利用可能: {torch.cuda.get_device_name(0)}")
    else:
        print("⚠️ GPUが利用できません。CPUモードで実行します。")
    
    # モデルパス（cyberrealisticPonyは問題があるため一時的に除外）
    base_models = [
        {
            "path": "/mnt/c/mana_workspace/storage500/civitai_models/majicmixLux_v3.safetensors",
            "name": "majicmix-lux"
        },
        {
            "path": "/mnt/c/mana_workspace/storage500/civitai_models/realisian_v60.safetensors",
            "name": "realisian"
        },
        {
            "path": "/mnt/c/mana_workspace/storage500/civitai_models/majicmixRealistic_v7.safetensors",
            "name": "majicmixrealistic-v7"
        },
        # cyberrealisticPonyはSDXLとして誤検出され、text_encoder_2がNoneになる問題があるため一時的に除外
        # {
        #     "path": "/mnt/c/mana_workspace/storage500/civitai_models/cyberrealisticPony_v150.safetensors",
        #     "name": "cyberrealistic-pony"
        # },
    ]
    
    lora_path = "/mnt/c/mana_workspace/storage500/civitai_models/ZiTD3tailed4nime.safetensors"
    
    # 存在確認
    available_base_models = [m for m in base_models if os.path.exists(m["path"])]
    if not available_base_models:
        print("❌ ベースモデルが見つかりません")
        return False
    
    use_lora = os.path.exists(lora_path)
    
    output_dir = Path("/home/mana/storage500/generated_images")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    generated_count = 0
    failed_count = 0
    
    current_pipeline = None
    current_model_name = None
    current_is_sdxl = False
    
    # ステップ数: 100ステップ（高品質）
    num_inference_steps = 100
    
    for i in range(num_images):
        # ランダムにベースモデルを選択
        model_config = random.choice(available_base_models)
        base_model_path = model_config["path"]
        model_name = model_config["name"]
        
        # LoRAを使用するかランダムに決定（50%の確率）
        use_lora_this_time = use_lora and random.random() < 0.5
        
        # 自動プロンプト生成
        prompt = generate_auto_prompt(BASE_PROMPT)
        
        # トークン数チェック（77トークン制限）- 確実に77以下にする
        try:
            from transformers import CLIPTokenizer
            tokenizer = CLIPTokenizer.from_pretrained('openai/clip-vit-large-patch14')
            if tokenizer and hasattr(tokenizer, 'encode'):
                # まず現在のプロンプトのトークン数をチェック
                tokens = tokenizer.encode(prompt, truncation=False, return_tensors=None)
                token_count = len(tokens) if isinstance(tokens, list) else tokens.shape[1] if hasattr(tokens, 'shape') else 0
                
                # 75トークンを超える場合は簡略化（性的要素は保持）
                max_retries = 5
                retry_count = 0
                original_token_count = token_count
                
                # 性的要素を含む最小限のプロンプト
                minimal_sexual_prompt = "Japanese gal, clear and pure type gal, large eyes, double eyelids, small nose, plump lips, oval face, fair skin, long straight black hair, bangs, 18 years old, adult, nude, naked, sex, explicit, erotic, 性行為, 裸, セックス"
                
                while token_count > 75 and retry_count < max_retries:  # 75に余裕を持たせる
                    if retry_count == 0:
                        # 1回目: 追加要素を減らす（性的要素を優先して2個）
                        sexual_items = random.sample([a for a in AUTO_ADDITIONS[:18] if any(kw in a.lower() for kw in ['nude', 'naked', 'sex', 'explicit', 'erotic', '裸', 'セックス', '性行為'])], 2)
                        prompt = f"{BASE_PROMPT}, {', '.join(sexual_items)}"
                    elif retry_count == 1:
                        # 2回目: 性的要素1個のみ
                        sexual_items = random.sample([a for a in AUTO_ADDITIONS[:18] if any(kw in a.lower() for kw in ['nude', 'naked', 'sex', 'explicit', 'erotic', '裸', 'セックス', '性行為'])], 1)
                        prompt = f"{BASE_PROMPT}, {sexual_items[0]}"
                    elif retry_count == 2:
                        # 3回目: ベースプロンプトの性的要素を保持した簡略版
                        prompt = minimal_sexual_prompt
                    elif retry_count == 3:
                        # 4回目: さらに簡略化（顔の特徴 + 性的要素）
                        prompt = "Japanese gal, large eyes, double eyelids, small nose, plump lips, oval face, fair skin, long straight black hair, bangs, 18 years old, nude, naked, sex, explicit, erotic, 性行為"
                    else:
                        # 5回目: 最小限（顔 + 性的要素のみ）
                        prompt = "Japanese gal, large eyes, double eyelids, small nose, plump lips, 18 years old, nude, naked, sex, explicit, 性行為"
                    
                    tokens = tokenizer.encode(prompt, truncation=False, return_tensors=None)
                    token_count = len(tokens) if isinstance(tokens, list) else tokens.shape[1] if hasattr(tokens, 'shape') else 0
                    retry_count += 1
                
                # それでも長い場合は強制的にtruncationを使用（性的要素を優先）
                if token_count > 77:
                    # まずプロンプトを簡略化してからtruncation
                    if token_count > 100:
                        prompt = minimal_sexual_prompt
                        tokens = tokenizer.encode(prompt, truncation=False, return_tensors=None)
                        token_count = len(tokens) if isinstance(tokens, list) else tokens.shape[1] if hasattr(tokens, 'shape') else 0
                    
                    if token_count > 77:
                        tokens = tokenizer.encode(prompt, truncation=True, max_length=77, return_tensors=None)
                        token_count = len(tokens) if isinstance(tokens, list) else tokens.shape[1] if hasattr(tokens, 'shape') else 0
                        prompt = tokenizer.decode(tokens, skip_special_tokens=True)
                        print(f"   ⚠️ トークン数が多すぎたため、truncationで77トークンに切り詰めました（{original_token_count}→{token_count}）")
                    else:
                        print(f"   ✅ トークン数を調整しました（{original_token_count}→{token_count}）")
                elif original_token_count > 75:
                    print(f"   ✅ トークン数を調整しました（{original_token_count}→{token_count}）")
        except Exception as e:
            # トークン数チェックに失敗した場合は最小限のプロンプトを使用
            prompt = "Japanese gal, 18 years old, adult"
            print(f"   ⚠️ トークン数チェック失敗: {e}")
        
        print(f"\n📸 {i+1}/{num_images} 枚目生成中...")
        print(f"   ベースモデル: {Path(base_model_path).name}")
        if use_lora_this_time:
            print(f"   LoRA: {Path(lora_path).name} (組み合わせ)")
        else:
            print(f"   LoRA: なし (ベースモデルのみ)")
        print(f"   📝 プロンプト: {prompt[:80]}...")
        print(f"   ⚙️ ステップ数: {num_inference_steps} (100ステップ)")
        
        # モデルが変わったら再読み込み
        if current_model_name != model_name or current_pipeline is None:
            if current_pipeline:
                del current_pipeline
                gc.collect()
                if device == "cuda":
                    torch.cuda.empty_cache()
            
            try:
                current_pipeline, current_is_sdxl = load_combined_model(
                    base_model_path,
                    lora_path if use_lora_this_time else None,
                    device
                )
                current_model_name = model_name
            except Exception as e:
                print(f"   ❌ モデル読み込み失敗: {e}")
                failed_count += 1
                continue
        
        # リトライ機能付きで画像生成
        max_retries = 2
        retry_count = 0
        image_generated = False
        
        while retry_count <= max_retries and not image_generated:
            try:
                start_time = time.time()
                
                # 解像度設定
                if current_is_sdxl:
                    width = 768
                    height = 1024
                else:
                    width = 512
                    height = 768
                
                # 生成（60ステップ）
                generator = torch.Generator(device=current_pipeline.device)
                seed = random.randint(0, 2**32)
                generator.manual_seed(seed)
                
                # tokenizerがNoneでないことを確認（生成前に再チェック）
                if hasattr(current_pipeline, 'tokenizer') and current_pipeline.tokenizer is None:
                    from transformers import CLIPTokenizer
                    current_pipeline.tokenizer = CLIPTokenizer.from_pretrained('openai/clip-vit-large-patch14')
                
                # SDXLの場合はtokenizer_2とtext_encoderも確認
                if current_is_sdxl:
                    if hasattr(current_pipeline, 'tokenizer_2') and current_pipeline.tokenizer_2 is None:
                        from transformers import CLIPTokenizer
                        current_pipeline.tokenizer_2 = CLIPTokenizer.from_pretrained('laion/CLIP-ViT-bigG-14-laion2B-39B-b160k')
                    
                    # text_encoderがNoneの場合はSDXLとして扱わない（誤検出の可能性）
                    if hasattr(current_pipeline, 'text_encoder') and current_pipeline.text_encoder is None:
                        print(f"   ⚠️ text_encoderがNoneのため、SDXLとして扱わずにスキップします")
                        failed_count += 1
                        continue
                    if hasattr(current_pipeline, 'text_encoder_2') and current_pipeline.text_encoder_2 is None:
                        print(f"   ⚠️ text_encoder_2がNoneのため、SDXLとして扱わずにスキップします")
                        failed_count += 1
                        continue
                
                call_kwargs = {
                    "prompt": prompt,
                    "negative_prompt": MANA_NEGATIVE_PROMPT,
                    "num_inference_steps": num_inference_steps,  # 60ステップ
                    "guidance_scale": 7.0,  # 7.5→7.0に調整（品質向上）
                    "width": width,
                    "height": height,
                    "generator": generator,
                }
                
                # SDXLモデルの場合
                if current_is_sdxl:
                    if hasattr(current_pipeline.unet.config, 'addition_embed_type'):
                        call_kwargs["added_cond_kwargs"] = {}
                
                image = current_pipeline(**call_kwargs).images[0]
                
                # 画像の整合性チェック
                if image is None or image.size[0] == 0 or image.size[1] == 0:
                    raise ValueError("生成された画像が無効です")
                
                # ファイル名生成
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                lora_tag = "with_lora" if use_lora_this_time else "base_only"
                filename = f"mana_mufufu_100steps_{model_name}_{lora_tag}_{timestamp}_{seed}.png"
                filepath = output_dir / filename
                
                # 高品質で保存（PNG直接保存、JPEG変換は行わない）
                # 画像を直接PNGとして保存（品質を最大限に保つ）
                image.save(filepath, "PNG", optimize=False)
                
                # メタデータを削除（必要に応じて）
                try:
                    from PIL.ExifTags import TAGS
                    # メタデータをクリア
                    image.info.clear()
                    # 再度保存（メタデータなし）
                    image.save(filepath, "PNG", optimize=False)
                except:
                    pass  # メタデータ削除に失敗しても続行
                
                # 保存後の整合性チェック（Google Drive同期問題対策）
                # 1. ファイルが存在するか
                if not filepath.exists():
                    raise ValueError("画像ファイルの保存に失敗しました（ファイルが存在しません）")
                
                # 2. ファイルサイズが0でないか
                file_size = filepath.stat().st_size
                if file_size == 0:
                    raise ValueError("画像ファイルの保存に失敗しました（ファイルサイズが0）")
                
                # 3. ファイルサイズの妥当性チェック（100KB未満は異常）
                if file_size < 100 * 1024:
                    raise ValueError(f"画像ファイルサイズが異常に小さいです: {file_size} bytes")
                
                # 4. ファイルが完全に書き込まれたことを確認（Google Drive同期対策）
                # ファイルを開いて読み込めることを確認
                try:
                    verify_image = Image.open(filepath)
                    verify_image.verify()  # 画像の整合性を検証
                    verify_image.close()
                except Exception as e:
                    raise ValueError(f"画像ファイルの整合性チェックに失敗しました: {e}")
                
                # 5. ファイルが完全に書き込まれるまで少し待機（Google Drive同期対策）
                # ファイルサイズが安定するまで待つ（最大2秒）
                for _ in range(20):
                    time.sleep(0.1)
                    new_size = filepath.stat().st_size
                    if new_size == file_size:
                        break  # ファイルサイズが安定した
                    file_size = new_size
                else:
                    print(f"   ⚠️ ファイルサイズが安定しませんでしたが、続行します")
                
                # 6. 最終的な整合性チェック
                final_size = filepath.stat().st_size
                if final_size < 100 * 1024:
                    raise ValueError(f"最終チェック: 画像ファイルサイズが異常に小さいです: {final_size} bytes")
                
                elapsed = time.time() - start_time
                generated_count += 1
                image_generated = True
                if retry_count > 0:
                    print(f"   ✅ {generated_count}枚目完了（リトライ成功）: {filename} ({elapsed:.1f}秒)")
                else:
                    print(f"   ✅ {generated_count}枚目完了: {filename} ({elapsed:.1f}秒)")
                
            except Exception as e:
                retry_count += 1
                if retry_count <= max_retries:
                    print(f"   ⚠️ 生成失敗（リトライ {retry_count}/{max_retries}）: {e}")
                    time.sleep(1)  # リトライ前に少し待機
                else:
                    failed_count += 1
                    print(f"   ❌ 生成失敗（リトライ上限）: {e}")
                    import traceback
                    traceback.print_exc()
        
        # メモリクリア
        gc.collect()
        if device == "cuda":
            torch.cuda.empty_cache()
        
        time.sleep(0.5)
    
    # クリーンアップ
    if current_pipeline:
        del current_pipeline
        gc.collect()
        if device == "cuda":
            torch.cuda.empty_cache()
    
    print(f"\n🎉 自動プロンプト生成完了（100ステップ）！")
    print(f"   ✅ 成功: {generated_count}枚")
    print(f"   ❌ 失敗: {failed_count}枚")
    print(f"📁 保存先: {output_dir}")
    
    return True

if __name__ == "__main__":
    num_images = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    generate_with_auto_prompt_100steps(num_images)

