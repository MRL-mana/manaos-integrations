#!/usr/bin/env python3
"""
RunPod Serverlessで生成した画像をギャラリーに保存するスクリプト
"""

import sys
import base64
from pathlib import Path
from datetime import datetime

sys.path.insert(0, '/root/archive/dummy_systems/20251106')
from runpod_serverless_client import RunPodServerlessClient

GALLERY_DIR = Path('/root/trinity_workspace/generated_images')
GALLERY_DIR.mkdir(parents=True, exist_ok=True)

def save_runpod_image_to_gallery(prompt: str = None, result: dict = None):
    """
    RunPod Serverlessで生成した画像をギャラリーに保存

    Args:
        prompt: プロンプト（新規生成する場合）
        result: 既存の生成結果（保存のみの場合）
    """
    client = RunPodServerlessClient()

    # 新規生成の場合
    if prompt and not result:
        print(f'🎨 画像生成中: {prompt[:50]}...')
        result = client.generate_image(
            prompt=prompt,
            model='stable_diffusion',
            width=1024,
            height=768,
            steps=25,
            negative_prompt='nsfw, low quality',
            save_to_network_storage=True
        )

    if result and result.get('status') == 'completed':
        output = result.get('output', {})
        image_base64 = output.get('image_base64', '')

        if image_base64:
            # Base64をデコードして保存
            try:
                image_data = base64.b64decode(image_base64)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                prompt_short = output.get('prompt', 'image')[:30].replace(' ', '_').replace(',', '')
                filename = f'runpod_{timestamp}_{prompt_short}.png'
                save_path = GALLERY_DIR / filename

                with open(save_path, 'wb') as f:
                    f.write(image_data)

                print(f'✅ 画像を保存しました: {save_path.name}')
                print(f'   パス: {save_path}')
                print(f'   サイズ: {len(image_data):,} bytes')
                return str(save_path)
            except Exception as e:
                print(f'❌ 保存エラー: {e}')
                return None
        else:
            print('⚠️ Base64データが見つかりません')
            print(f'   出力キー: {list(output.keys())}')
            return None
    else:
        error_msg = result.get('error', 'Unknown error') if result else 'No result'
        print(f'❌ 生成エラー: {error_msg}')
        return None

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='RunPod画像をギャラリーに保存')
    parser.add_argument('--prompt', type=str, help='生成プロンプト')
    args = parser.parse_args()

    if args.prompt:
        save_runpod_image_to_gallery(prompt=args.prompt)
    else:
        print('💡 使い方:')
        print('   python3 save_runpod_image_to_gallery.py --prompt "beautiful landscape"')
        print()
        print('📁 ギャラリー: /root/trinity_workspace/generated_images')
        print('🌐 ギャラリーサーバー: http://localhost:5556')



