#!/usr/bin/env python3
"""
🎨 NSFW画像生成（RunPod Serverless版）
RunPod Serverlessを使用して高品質なNSFW画像を生成
"""

import requests
import sys
import os
from pathlib import Path
from datetime import datetime
import json
import base64
import random
import time

sys.path.insert(0, '/root/scripts')


# RunPod Serverless設定（Vaultから読み込み）

def load_runpod_config():
    """RunPod設定をVaultから読み込む"""
    api_key = os.getenv("RUNPOD_API_KEY", "")
    endpoint_id = os.getenv("RUNPOD_SERVERLESS_ENDPOINT_ID", "")

    # Vaultから読み込みを試行
    try:
        vault_file = Path("/root/.mana_vault/runpod/config.json")
        if vault_file.exists():
            with open(vault_file, 'r') as f:
                config = json.load(f)
                if not api_key:
                    api_key = config.get('runpod_api_key', '')
                if not endpoint_id:
                    serverless = config.get('serverless', {})
                    endpoint_url = serverless.get('endpoint_url', '')
                    if endpoint_url:
                        # URLからIDを抽出: https://api.runpod.ai/v2/{id}/run
                        import re
                        match = re.search(r'/v2/([^/]+)/run', endpoint_url)
                        if match:
                            endpoint_id = match.group(1)
                    if not endpoint_id:
                        endpoint_id = serverless.get('endpoint_id', '')
    except Exception as e:
        print(f"⚠️  Vault読み込みエラー: {e}")

    # デフォルト値
    if not endpoint_id:
        endpoint_id = "2a66wyfmetultk"

    return api_key, endpoint_id


RUNPOD_API_KEY, RUNPOD_ENDPOINT_ID = load_runpod_config()
RUNPOD_API_URL = f"https://api.runpod.ai/v2/{RUNPOD_ENDPOINT_ID}/run"
RUNPOD_AVAILABLE = bool(RUNPOD_API_KEY)

# ギャラリー保存先
GALLERY_DIR = Path("/root/trinity_workspace/generated_images")
GALLERY_DIR.mkdir(parents=True, exist_ok=True)

# NSFWプロンプト（日本人・清楚系ギャル・アダルト系）
NSFW_PROMPTS = {
    "nsfw_sexy": [
        "beautiful japanese girl, innocent pure face, clear skin, beautiful eyes, cute expression, naked, perfect body, sensual pose, erotic expression, high quality, detailed, realistic, masterpiece, best quality, ultra detailed, perfect anatomy, kawaii, pure, innocent",
        "gorgeous japanese woman, pure innocent face, clear skin, beautiful eyes, cute expression, nude, attractive body, seductive pose, alluring expression, high quality, detailed, realistic, masterpiece, best quality, ultra detailed, perfect anatomy, kawaii, pure",
        "sexy japanese girl, innocent cute face, clear skin, beautiful eyes, cute expression, naked, perfect figure, erotic pose, sensual expression, high quality, detailed art, realistic, masterpiece, best quality, ultra detailed, perfect anatomy, kawaii, pure"
    ],
    "nsfw_alluring": [
        "beautiful japanese girl, innocent pure face, clear skin, beautiful eyes, cute expression, topless, perfect breasts, sensual pose, erotic expression, high quality, detailed, realistic, masterpiece, best quality, ultra detailed, perfect anatomy, kawaii, pure",
        "gorgeous japanese woman, pure innocent face, clear skin, beautiful eyes, cute expression, topless, attractive breasts, seductive pose, alluring expression, high quality, detailed, realistic, masterpiece, best quality, ultra detailed, perfect anatomy, kawaii, pure"
    ],
    "nsfw_erotic": [
        "beautiful japanese girl, innocent pure face, clear skin, beautiful eyes, cute expression, naked, perfect body, erotic pose, sensual expression, high quality, detailed, realistic, masterpiece, best quality, ultra detailed, perfect anatomy, kawaii, pure, innocent",
        "gorgeous japanese woman, pure innocent face, clear skin, beautiful eyes, cute expression, nude, attractive body, seductive pose, erotic expression, high quality, detailed, realistic, masterpiece, best quality, ultra detailed, perfect anatomy, kawaii, pure"
    ],
    "nsfw_fellatio": [
        "beautiful japanese girl performing fellatio, innocent pure face, clear skin, beautiful eyes, cute expression, erotic expression, sensual pose, naked, high quality, detailed, realistic, masterpiece, best quality, ultra detailed, perfect anatomy, kawaii, pure, innocent",
        "gorgeous japanese woman performing oral sex, pure innocent face, clear skin, beautiful eyes, cute expression, erotic expression, seductive pose, nude, high quality, detailed, realistic, masterpiece, best quality, ultra detailed, perfect anatomy, kawaii, pure",
        "cute japanese girl giving blowjob, innocent pure face, clear skin, beautiful eyes, cute expression, naked, erotic pose, high quality, detailed, realistic, masterpiece, best quality, ultra detailed, perfect anatomy, kawaii, pure, innocent"
    ],
    "nsfw_sex": [
        "beautiful japanese girl having sex, innocent pure face, clear skin, beautiful eyes, cute expression, naked, erotic pose, sensual expression, high quality, detailed, realistic, masterpiece, best quality, ultra detailed, perfect anatomy, kawaii, pure, innocent",
        "gorgeous japanese woman having intercourse, pure innocent face, clear skin, beautiful eyes, cute expression, nude, erotic pose, seductive expression, high quality, detailed, realistic, masterpiece, best quality, ultra detailed, perfect anatomy, kawaii, pure",
        "cute japanese girl having sex, innocent pure face, clear skin, beautiful eyes, cute expression, naked, erotic pose, high quality, detailed, realistic, masterpiece, best quality, ultra detailed, perfect anatomy, kawaii, pure, innocent"
    ],
    "nsfw_exposed": [
        "beautiful japanese girl, innocent pure face, clear skin, beautiful eyes, cute expression, fully exposed, naked, revealing pose, erotic expression, high quality, detailed, realistic, masterpiece, best quality, ultra detailed, perfect anatomy, kawaii, pure, innocent",
        "gorgeous japanese woman, pure innocent face, clear skin, beautiful eyes, cute expression, completely exposed, nude, seductive pose, alluring expression, high quality, detailed, realistic, masterpiece, best quality, ultra detailed, perfect anatomy, kawaii, pure"
    ],
    "nsfw_ecchi": [
        "beautiful japanese girl, innocent pure face, clear skin, beautiful eyes, cute expression, revealing outfit, erotic pose, sensual expression, high quality, detailed, realistic, masterpiece, best quality, ultra detailed, perfect anatomy, kawaii, pure, innocent",
        "gorgeous japanese woman, pure innocent face, clear skin, beautiful eyes, cute expression, sexy outfit, seductive pose, alluring expression, high quality, detailed, realistic, masterpiece, best quality, ultra detailed, perfect anatomy, kawaii, pure"
    ]
}

# ネガティブプロンプト（顔の品質重視）
NSFW_NEGATIVE = "bad quality, low resolution, blurry, distorted, ugly, deformed, bad anatomy, bad face, deformed face, ugly face, bad facial features, distorted face, asymmetrical face, blurry face, low quality face, violence, blood, gore, scary, horror, monster, demon, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username"

# サイズプリセット
SIZE_PRESETS = {
    "square": (768, 768),
    "portrait": (512, 768),
    "landscape": (768, 512)
}

# 利用可能なモデル（RunPod Serverlessで使用可能なモデル）
AVAILABLE_MODELS = [
    "runwayml/stable-diffusion-v1-5",
    "stabilityai/stable-diffusion-2-1",
    "stabilityai/stable-diffusion-xl-base-1.0",
    "CompVis/stable-diffusion-v1-4",
    "runwayml/stable-diffusion-inpainting",
    "stabilityai/sdxl-turbo",
]


def save_image_from_base64(image_base64, filename):
    """Base64画像を保存"""
    try:
        from PIL import Image
        import io
        import numpy as np

        # Base64デコード
        image_data = base64.b64decode(image_base64)
        print(f"   🔍 デコード後サイズ: {len(image_data)} bytes")

        # 画像として開く
        image = Image.open(io.BytesIO(image_data))
        print(f"   🔍 画像サイズ: {image.size}, モード: {image.mode}")

        # 画像が単色でないか確認
        arr = np.array(image)
        unique_colors = len(
            np.unique(arr.reshape(-1, arr.shape[2] if len(arr.shape) > 2 else 1), axis=0))
        print(f"   🔍 ユニークな色数: {unique_colors}")

        if unique_colors == 1:
            print(
                f"   ⚠️  警告: 画像が単色です！RGB{tuple(arr[0, 0]) if len(arr.shape) > 2 else arr[0]}")
            print(f"   ⚠️  Base64データが正しくない可能性があります")

        gallery_path = GALLERY_DIR / filename
        image.save(gallery_path)
        print(f"   ✅ 保存完了: {gallery_path}")
        return str(gallery_path)
    except Exception as e:
        print(f"⚠️  画像保存エラー: {e}")
        import traceback
        traceback.print_exc()
        return None


def register_to_gallery(image_path, style, prompt, model_name="RunPod Serverless"):
    """ギャラリーに登録"""
    try:
        import sqlite3

        db_path = "/mnt/storage500/gallery/gallery.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        filename = Path(image_path).name

        cursor.execute('''
            INSERT OR IGNORE INTO images (
                filename, prompt, model, file_path, file_type, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            filename,
            prompt,
            model_name,
            str(image_path),
            "generated",
            datetime.now().isoformat()
        ))

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"⚠️  ギャラリー登録エラー: {e}")
        return False


def main():
    # 生成枚数（コマンドライン引数から取得）
    total_count = int(sys.argv[1]) if len(sys.argv) > 1 else 30

    print(f"🎨 高品質NSFW画像{total_count}枚生成開始（RunPod Serverless）！")
    print("=" * 60)
    print(f"⏳ RunPod Serverlessのため高速で高品質な画像を生成します")
    print("=" * 60)

    if not RUNPOD_AVAILABLE:
        print("❌ RunPod APIキーが設定されていません")
        print("   RUNPOD_API_KEY環境変数を設定してください")
        return

    print(f"🔑 RunPod Endpoint: {RUNPOD_ENDPOINT_ID}")
    print(f"🌐 API URL: {RUNPOD_API_URL}")

    # NSFWスタイルリスト
    nsfw_styles = list(NSFW_PROMPTS.keys())
    print(f"\n🎭 NSFWスタイル: {len(nsfw_styles)}種類")
    for style in nsfw_styles:
        print(f"   - {style}")

    # 使用モデルリスト
    print(f"\n📦 使用モデル: {len(AVAILABLE_MODELS)}種類")
    for model in AVAILABLE_MODELS:
        print(f"   - {model}")

    print(f"\n📸 {total_count}枚生成開始...")
    print("=" * 60)

    results = []
    total_start = time.time()

    for i in range(total_count):
        print(f"\n{'='*60}")
        print(f"📸 {i+1}/{total_count} 枚目生成中...")
        print(f"{'='*60}")

        # スタイル、サイズ、モデルをランダム選択
        style = random.choice(nsfw_styles)
        prompt = random.choice(NSFW_PROMPTS[style])
        size_name = random.choice(list(SIZE_PRESETS.keys()))
        width, height = SIZE_PRESETS[size_name]
        model = AVAILABLE_MODELS[i % len(AVAILABLE_MODELS)]  # 順番に使用

        print(f"   スタイル: {style}")
        print(f"   サイズ: {size_name} ({width}x{height})")
        print(f"   モデル: {model}")
        print(f"   プロンプト: {prompt[:60]}...")

        try:
            # RunPod Serverless APIで画像生成
            start_time = time.time()

            # リクエストペイロード（エンドポイント仕様に合わせる）
            # SDXLモデルの場合はサイズとステップ数を調整
            is_sdxl = "xl" in model.lower() or "sdxl" in model.lower()
            if is_sdxl:
                # SDXLは1024x1024推奨、ステップ数も多めに
                width = max(width, 1024)
                height = max(height, 1024)
                steps = 40
            else:
                steps = 30

            payload = {
                "input": {
                    "task": "image_generation",
                    "prompt": prompt,
                    "negative_prompt": NSFW_NEGATIVE,
                    "width": width,
                    "height": height,
                    "num_inference_steps": steps,
                    "guidance_scale": 7.5,
                    "model": model
                }
            }

            # ジョブ送信（runsyncを使用して同期実行）
            headers = {
                "Authorization": f"Bearer {RUNPOD_API_KEY}",
                "Content-Type": "application/json"
            }

            # runsyncエンドポイントを使用（同期実行、結果を直接取得）
            runsync_url = RUNPOD_API_URL.replace('/run', '/runsync')

            print(f"   📤 RunPod APIに送信中... (runsync)")
            response = requests.post(
                runsync_url, json=payload, headers=headers, timeout=300)

            if response.status_code != 200:
                print(f"❌ APIエラー: {response.status_code}")
                print(f"   レスポンス: {response.text[:500]}")
                results.append({
                    "number": i + 1,
                    "style": style,
                    "model": model,
                    "error": f"APIエラー: {response.status_code}",
                    "success": False
                })
                continue

            # runsyncの場合は直接結果が返ってくる
            result_data = response.json()

            # runsyncのレスポンス形式を確認
            if "output" in result_data:
                output = result_data.get("output", {})
            elif "id" in result_data:
                # 非同期実行の場合（フォールバック）
                job_id = result_data.get("id")
                print(f"   ⚠️  非同期実行にフォールバック (ID: {job_id})")
                # ポーリング処理（既存のコードを使用）
                status_url = f"https://api.runpod.ai/v2/{RUNPOD_ENDPOINT_ID}/status/{job_id}"
                max_wait = 300
                wait_time = 0

                while wait_time < max_wait:
                    status_response = requests.get(
                        status_url, headers=headers, timeout=30)
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        job_status = status_data.get("status", "UNKNOWN")

                        if job_status == "COMPLETED":
                            output = status_data.get("output", {})
                            break
                        elif job_status == "FAILED":
                            error_msg = status_data.get(
                                "error", "Unknown error")
                            print(f"❌ ジョブ失敗: {error_msg}")
                            results.append({
                                "number": i + 1,
                                "style": style,
                                "model": model,
                                "error": error_msg,
                                "success": False
                            })
                            break
                    time.sleep(2)
                    wait_time += 2
                    if wait_time % 10 == 0:
                        print(f"   ⏳ 待機中... ({wait_time}秒経過)")

                if wait_time >= max_wait:
                    print(f"❌ タイムアウト")
                    results.append({
                        "number": i + 1,
                        "style": style,
                        "model": model,
                        "error": "タイムアウト",
                        "success": False
                    })
                    continue
            else:
                print(f"❌ 予期しないレスポンス形式")
                print(f"   レスポンス: {result_data}")
                results.append({
                    "number": i + 1,
                    "style": style,
                    "model": model,
                    "error": "予期しないレスポンス形式",
                    "success": False
                })
                continue

            # 出力がネストされている場合の処理
            if isinstance(output, dict) and "output" in output:  # type: ignore[possibly-unbound]
                actual_output = output.get("output", {})
            else:
                actual_output = output  # type: ignore[possibly-unbound]

            # デバッグ: 出力内容を確認
            print(
                f"   🔍 デバッグ: output keys = {list(actual_output.keys()) if isinstance(actual_output, dict) else 'not dict'}")
            if isinstance(actual_output, dict):
                print(f"   🔍 デバッグ: success = {actual_output.get('success')}")
                print(
                    f"   🔍 デバッグ: error = {actual_output.get('error', 'N/A')}")
                print(
                    f"   🔍 デバッグ: image_base64存在 = {'image_base64' in actual_output}")
                if 'image_base64' in actual_output:
                    img_b64_len = len(actual_output['image_base64'])
                    print(f"   🔍 デバッグ: image_base64長さ = {img_b64_len} bytes")
                    # Base64データの最初の部分を確認
                    img_b64_preview = actual_output['image_base64'][:100]
                    print(
                        f"   🔍 デバッグ: image_base64プレビュー = {img_b64_preview}...")

            # Base64エンコードされた画像を取得
            if isinstance(actual_output, dict) and 'image_base64' in actual_output:
                filename = f"mufufu_runpod_nsfw_{style}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                gallery_path = save_image_from_base64(
                    actual_output['image_base64'], filename)

                if gallery_path:
                    # ギャラリーに登録
                    register_to_gallery(
                        gallery_path, style, prompt)

                    elapsed = time.time() - start_time
                    print(f"✅ 成功: {gallery_path}")
                    print(f"   ⏱️  生成時間: {elapsed:.1f}秒")

                    results.append({
                        "number": i + 1,
                        "style": style,
                        "model": model,
                        "filepath": gallery_path,
                        "elapsed": elapsed,
                        "success": True
                    })
                    break
                else:
                    print(f"❌ 画像保存失敗")
                    results.append({
                        "number": i + 1,
                        "style": style,
                        "model": model,
                        "error": "画像保存失敗",
                        "success": False
                    })
                    break
            else:
                print(f"⚠️  画像データが見つかりません")
                print(f"   出力: {actual_output}")
                results.append({
                    "number": i + 1,
                    "style": style,
                    "model": model,
                    "error": "画像データが見つかりません",
                    "output": actual_output,
                    "success": False
                })

        except Exception as e:
            print(f"❌ エラー: {str(e)}")
            import traceback
            traceback.print_exc()
            results.append({
                "number": i + 1,
                "style": style,
                "model": model,
                "error": str(e),
                "success": False
            })

        # 進捗表示
        if (i + 1) % 5 == 0:
            elapsed_total = time.time() - total_start
            avg_time = elapsed_total / (i + 1)
            remaining = avg_time * (total_count - i - 1)
            print(f"\n📊 進捗: {i+1}/{total_count} 枚完了")
            print(f"   平均生成時間: {avg_time:.1f}秒/枚")
            print(f"   残り時間（目安）: {remaining/60:.1f}分")

    total_elapsed = time.time() - total_start

    print(f"\n{'='*60}")
    print(f"🎉 {total_count}枚生成完了！")
    print(f"{'='*60}")
    print(f"⏱️  総時間: {total_elapsed/60:.1f}分")
    print(f"✅ 成功: {len([r for r in results if r.get('success')])}枚")
    print(f"❌ 失敗: {len([r for r in results if not r.get('success')])}枚")

    # モデル別生成数
    print(f"\n📊 モデル別生成数:")
    model_counts = {}
    for r in results:
        if r.get('success'):
            m = r.get('model', 'unknown')
            model_counts[m] = model_counts.get(m, 0) + 1
    for m, count in sorted(model_counts.items()):
        print(f"   {m}: {count}枚")

    # 結果をJSONで保存
    result_file = GALLERY_DIR / \
        f"runpod_nsfw_generation_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n💾 結果を保存: {result_file}")
    print(f"📁 ギャラリー: {GALLERY_DIR}")
    print(f"🌐 ギャラリーURL: http://100.93.120.33:5559/")
    print("\n🎉 完了！ギャラリーで確認してください！")


if __name__ == "__main__":
    main()
